"""Store independent observations and generation-fenced background jobs."""

import json
import time
from datetime import datetime, timezone

import comments

VERSION = "attributes-v1"
CACHE_VERSION = "cached-text-v1"
FIELDS = (
    "grape",
    "sweetness",
    "colour",
    "vintage",
    "reserve",
    "barrel",
    "kosher",
    "organic",
    "unfiltered",
    "limited_edition",
)
STATES = ("observed", "not_visible", "unreadable", "unknown")
TARGET_SQL = """SELECT DISTINCT w.sha256,coalesce(d.sha256,w.sha256) AS input_sha256,
 i.folder,i.extension FROM wine_image w JOIN wine_catalog c ON c.wine_slug=w.wine_slug
 LEFT JOIN image_derivative d ON d.source_sha256=w.sha256 AND d.kind='package'
 JOIN image i ON i.sha256=coalesce(d.sha256,w.sha256)
 WHERE w.image_type IN ('main','main_patched') AND c.state!='Removed'"""
_DISCOVERY = {}
_HEARTBEAT = {}


def available(conn):
    return (
        conn.execute(
            "SELECT 1 FROM sqlite_schema WHERE name='image_attribute_job'"
        ).fetchone()
        is not None
    )


def database_key(conn):
    return conn.execute("PRAGMA database_list").fetchone()[2]


def settings(conn):
    if not available(conn):
        return {"active_version": VERSION, "worker_active": False, "paused": False}
    version, at, paused = conn.execute(
        "SELECT active_version,heartbeat_at,paused FROM image_attribute_settings WHERE id=1"
    ).fetchone()
    age = (
        (
            datetime.now(timezone.utc)
            - datetime.fromisoformat(at.replace("Z", "+00:00"))
        ).total_seconds()
        if at
        else float("inf")
    )
    return {
        "active_version": version,
        "heartbeat_at": at,
        "worker_active": age < 90,
        "paused": bool(paused),
    }


def heartbeat(conn, version, force=False):
    """The watcher alone selects the active extraction key. API reads use this key."""
    db = database_key(conn)
    now = time.monotonic()
    if (
        not force
        and _HEARTBEAT.get(db, (None, 0))[0] == version
        and now - _HEARTBEAT[db][1] < 15
    ):
        return
    previous = conn.execute(
        "SELECT active_version FROM image_attribute_settings WHERE id=1"
    ).fetchone()[0]
    if previous != version:
        # Preserve already requested work when a worker starts with another recipe.
        at = comments.now_utc()
        conn.execute(
            "INSERT INTO image_attribute_job (sha256,input_sha256,extractor_version,mode,state,requested_at,updated_at) "
            "SELECT sha256,input_sha256,?,mode,'pending',requested_at,? FROM image_attribute_job WHERE extractor_version=? AND state IN ('pending','running') "
            "ON CONFLICT DO UPDATE SET mode=CASE WHEN excluded.mode='image' THEN 'image' ELSE image_attribute_job.mode END, "
            "state='pending',generation=generation+1,attempts=0,error=NULL,updated_at=excluded.updated_at",
            (version, at, previous),
        )
        conn.execute(
            "UPDATE image_attribute_job SET state='failed',error='Moved to active extractor',generation=generation+1 WHERE extractor_version=? AND state IN ('pending','running')",
            (previous,),
        )
    conn.execute(
        "UPDATE image_attribute_settings SET active_version=?,heartbeat_at=? WHERE id=1",
        (version, comments.now_utc()),
    )
    _HEARTBEAT[db] = (version, now)
    if len(_HEARTBEAT) > 128:
        _HEARTBEAT.pop(next(iter(_HEARTBEAT)))


def targets(conn):
    return [
        dict(zip(("sha256", "input_sha256", "folder", "extension"), row))
        for row in conn.execute(TARGET_SQL)
    ]


def key(item):
    return item["sha256"], item["input_sha256"], item.get("version", VERSION)


def empty():
    return {f: {"state": "unknown", "values": [], "evidence": ""} for f in FIELDS}


def validate(facts):
    if not isinstance(facts, dict) or set(facts) != set(FIELDS):
        raise ValueError("facts MUST contain exactly the supported attributes")
    for field, fact in facts.items():
        if not isinstance(fact, dict) or set(fact) != {"state", "values", "evidence"}:
            raise ValueError("each attribute MUST have state, values, and evidence")
        values = fact["values"]
        if (
            fact["state"] not in STATES
            or not isinstance(values, list)
            or len(values) > 20
            or any(
                not isinstance(v, str) or not v.strip() or len(v) > 200 for v in values
            )
            or not isinstance(fact["evidence"], str)
            or len(fact["evidence"]) > 2000
        ):
            raise ValueError("invalid attribute: " + field)
        if fact["state"] == "observed" and (not values or not fact["evidence"].strip()):
            raise ValueError("an observed value MUST have printed evidence: " + field)
        if fact["state"] != "observed" and values:
            raise ValueError("an unobserved attribute MUST have no values: " + field)
    return facts


def discover(conn, version=None, force=False, interval=30):
    """Use one bounded-frequency set operation. Old observations never auto-requeue."""
    if not available(conn):
        return 0
    version = version or settings(conn)["active_version"]
    db = database_key(conn)
    now = time.monotonic()
    if (
        not force
        and _DISCOVERY.get(db, (None, 0))[0] == version
        and now - _DISCOVERY[db][1] < interval
    ):
        return 0
    at = comments.now_utc()
    cursor = conn.execute(
        "WITH targets AS (" + TARGET_SQL + ") INSERT INTO image_attribute_job "
        "(sha256,input_sha256,extractor_version,mode,state,requested_at,updated_at) "
        "SELECT t.sha256,t.input_sha256,?,CASE WHEN b.sha256 IS NULL THEN 'image' ELSE 'cached' END,'pending',?,? "
        "FROM targets t LEFT JOIN image_attribute_baseline b ON b.sha256=t.sha256 AND b.input_sha256=t.input_sha256 "
        "WHERE NOT EXISTS (SELECT 1 FROM image_attribute_job j WHERE j.sha256=t.sha256 AND j.input_sha256=t.input_sha256 AND j.extractor_version=?) "
        "AND NOT EXISTS (SELECT 1 FROM image_attribute_facts f WHERE f.sha256=t.sha256 AND f.input_sha256=t.input_sha256) "
        "ON CONFLICT DO NOTHING",
        (version, at, at, version),
    )
    changed = conn.execute("SELECT changes()").fetchone()[0]
    _DISCOVERY[db] = (version, now)
    if len(_DISCOVERY) > 128:
        _DISCOVERY.pop(next(iter(_DISCOVERY)))
    return changed if cursor else 0


def pending(conn, limit=1, busy=(), version=None):
    if not available(conn) or settings(conn)["paused"]:
        return []
    version = version or settings(conn)["active_version"]
    conn.execute(
        "UPDATE image_attribute_job SET state=CASE WHEN attempts>=3 THEN 'failed' ELSE 'pending' END, "
        "error='Worker lease expired',generation=generation+1 WHERE state='running' "
        "AND datetime(updated_at)<datetime('now','-15 minutes')"
    )
    busy = tuple(busy)
    exclude = (
        " AND j.sha256 NOT IN (" + ",".join("?" for _ in busy) + ")" if busy else ""
    )
    rows = conn.execute(
        "WITH targets AS ("
        + TARGET_SQL
        + ") SELECT t.sha256,t.input_sha256,t.folder,t.extension,j.generation,j.mode "
        "FROM image_attribute_job j JOIN targets t ON j.sha256=t.sha256 AND j.input_sha256=t.input_sha256 "
        "WHERE j.extractor_version=? AND j.state='pending'"
        + exclude
        + " ORDER BY j.requested_at,j.sha256 LIMIT ?",
        (version, *busy, limit),
    ).fetchall()
    return [
        dict(
            zip(
                ("sha256", "input_sha256", "folder", "extension", "generation", "mode"),
                row,
            ),
            version=version,
        )
        for row in rows
    ]


def claim(conn, item):
    cursor = conn.execute(
        "UPDATE image_attribute_job SET state='running',attempts=attempts+1,updated_at=? "
        "WHERE sha256=? AND input_sha256=? AND extractor_version=? AND generation=? AND state='pending'",
        (comments.now_utc(), *key(item), item["generation"]),
    )
    return cursor.rowcount == 1


def finish(
    conn,
    item,
    facts=None,
    source="vlm",
    model=None,
    error=None,
    counted=True,
    max_attempts=3,
):
    row = conn.execute(
        "SELECT generation,state,attempts FROM image_attribute_job WHERE sha256=? AND input_sha256=? AND extractor_version=?",
        key(item),
    ).fetchone()
    if not row or row[:2] != (item["generation"], "running"):
        return False
    at = comments.now_utc()
    if error is not None:
        state = "failed" if counted and row[2] >= max_attempts else "pending"
        conn.execute(
            "UPDATE image_attribute_job SET state=?,error=?,updated_at=?,attempts=attempts-? WHERE sha256=? AND input_sha256=? AND extractor_version=?",
            (state, str(error)[:1000], at, int(not counted), *key(item)),
        )
    else:
        validate(facts)
        observation_version = CACHE_VERSION if source == "description" else key(item)[2]
        cursor = conn.execute(
            "INSERT INTO image_attribute_facts (sha256,input_sha256,extractor_version,facts,source,model,created_at) VALUES (?,?,?,?,?,?,?)",
            (
                item["sha256"],
                item["input_sha256"],
                observation_version,
                json.dumps(facts, ensure_ascii=False),
                source,
                model,
                at,
            ),
        )
        conn.execute(
            "UPDATE image_attribute_job SET state='ready',facts_id=?,error=NULL,updated_at=? WHERE sha256=? AND input_sha256=? AND extractor_version=?",
            (cursor.lastrowid, at, *key(item)),
        )
    return True


def enqueue(conn, sha=None, scope="missing", version=None):
    version = version or settings(conn)["active_version"]
    items = targets(conn)
    if sha is not None:
        items = [t for t in items if t["sha256"] == sha]
        if not items:
            raise ValueError("image is not a current main or patch image")
    current = views(conn, version) if sha is None and scope == "missing" else {}
    queued = 0
    for item in items:
        item["version"] = version
        row = conn.execute(
            "SELECT state,mode FROM image_attribute_job WHERE sha256=? AND input_sha256=? AND extractor_version=?",
            key(item),
        ).fetchone()
        if row and row[0] in ("pending", "running") and row[1] == "image":
            continue
        view = current.get(item["sha256"])
        if view and view["state"] == "ready" and view["source"] == "vlm":
            continue
        if (
            view
            and view["state"] == "ready"
            and all(
                f["state"] in ("observed", "not_visible")
                for f in view["facts"].values()
            )
        ):
            continue
        at = comments.now_utc()
        conn.execute(
            "INSERT INTO image_attribute_job (sha256,input_sha256,extractor_version,mode,state,requested_at,updated_at) "
            "VALUES (?,?,?,'image','pending',?,?) ON CONFLICT DO UPDATE SET mode='image',state='pending',generation=generation+1,attempts=0,error=NULL,requested_at=excluded.requested_at,updated_at=excluded.updated_at",
            (*key(item), at, at),
        )
        queued += 1
    return queued


def views(conn, version=None):
    """Read current identities and only referenced or latest observations. No writes."""
    if not available(conn):
        return {}
    version = version or settings(conn)["active_version"]
    jobs = {
        (a, b): (state, error, fid)
        for a, b, state, error, fid in conn.execute(
            "SELECT sha256,input_sha256,state,error,facts_id FROM image_attribute_job WHERE extractor_version=?",
            (version,),
        )
    }
    rows = conn.execute(
        "SELECT id,sha256,input_sha256,extractor_version,facts,source,model,created_at FROM image_attribute_facts "
        "WHERE id IN (SELECT facts_id FROM image_attribute_job WHERE extractor_version=?) "
        "OR id IN (SELECT max(id) FROM image_attribute_facts GROUP BY sha256,input_sha256) ORDER BY id DESC",
        (version,),
    ).fetchall()
    observations = {
        row[0]: dict(
            zip(
                (
                    "sha256",
                    "input_sha256",
                    "version",
                    "facts",
                    "source",
                    "model",
                    "created_at",
                ),
                row[1:],
            )
        )
        for row in rows
    }
    by_sha = {}
    for obs in observations.values():
        by_sha.setdefault(obs["sha256"], []).append(obs)
    out = {}
    for item in targets(conn):
        state, error, fid = jobs.get(
            (item["sha256"], item["input_sha256"]), ("not_queued", None, None)
        )
        obs = observations.get(fid)
        if not obs:
            exact = [
                o
                for o in by_sha.get(item["sha256"], [])
                if o["input_sha256"] == item["input_sha256"]
            ]
            obs = (
                next((o for o in exact if o["version"] == version), None)
                or next(
                    (
                        o
                        for o in exact
                        if o["source"] == "description"
                        and o["version"] == CACHE_VERSION
                    ),
                    None,
                )
                or (
                    exact[0]
                    if exact
                    else next(iter(by_sha.get(item["sha256"], [])), None)
                )
            )
        valid = bool(
            obs
            and obs["input_sha256"] == item["input_sha256"]
            and (
                obs["version"] == version
                or obs["source"] == "description"
                and obs["version"] == CACHE_VERSION
            )
        )
        if state == "not_queued" and valid:
            state = "ready"
        elif state == "not_queued" and obs:
            state = "older_extractor"
        out[item["sha256"]] = {
            **item,
            "state": state,
            "error": error,
            "facts": json.loads(obs["facts"]) if obs else empty(),
            "source": obs["source"] if obs else None,
            "model": obs["model"] if obs else None,
            "created_at": obs["created_at"] if obs else None,
            "stale": bool(obs and (state != "ready" or not valid)),
        }
    return out
