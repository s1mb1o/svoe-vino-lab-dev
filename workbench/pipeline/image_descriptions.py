"""The descriptions of the images: the table `image_description`.

One row describes one image file. The owner sets values by hand on `/dataset`; the
watcher `describe_images.py` fills the values that are not set with a VLM. The VLM never
overwrites a value that is set. Read `docs/plans/26_image-description.md`.

The lab server and the watcher use these functions. A function that writes runs in the
transaction of the caller.

The watcher writes its state into STATUS_PATH at each step. The indicator of `/dataset`
reads it through `watcher_status`.
"""
import datetime
import json
import os
import re
import tempfile

import comments
import image_details
import label_descriptions
import labdb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The state of the watcher. A unit test sets this to a temporary file.
STATUS_PATH = os.path.join(ROOT, "work", "describe_images.status.json")
# The states that the watcher writes. `stopped` also stands for a missing file or a
# process that is gone.
STATES = ("working", "idle", "waiting", "stopped")
# The first line of an entry of the watcher log: the UTC time and a word, for an image
# the first 12 digits of its sha256. `detail_failures` sends the last LOG_LIMIT entries
# of each image.
LOG_LINE = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ (\S+)")
LOG_LIMIT = 20
# The read of `log_tail` starts at most this number of bytes before the end of the log.
TAIL_BYTES = 256 * 1024

# The fields of a description, in the order of the table, and the values of each field.
# Schema 024 added `presentation_mode` after `vlm_attempts`.
FIELDS = ("package_type", "subject_scope", "package_view", "content_roles",
          "presentation_mode")
VALUES = {
    "package_type": ("bottle", "can", "keg", "bag", "bag_in_box", "tetra_pak", "barrel",
                     "decanter", "box", "other", "unknown"),
    "subject_scope": ("full_package", "label_closeup", "multiple_packages", "unknown"),
    "package_view": ("front", "back", "unknown"),
    "content_roles": ("front_label", "back_label", "unknown"),
    "presentation_mode": ("on_package", "flat_surface", "other", "unknown"),
}
# The image types of `wine_image` whose images get a description: main, patched, and
# additional.
IMAGE_TYPES = tuple(labdb.IMAGE_FOLDERS)

COLUMNS = FIELDS + ("created_by", "created_at", "updated_at", "vlm_at", "vlm_name",
                    "vlm_model", "vlm_answer", "vlm_error", "vlm_attempts")


class DescriptionError(ValueError):
    """A value is not a value of its field."""


def check_value(field, value):
    """Return `value` when it is a value of `field`, or None. Raise DescriptionError.

    `content_roles` is a list of 1 to 2 different roles; `unknown` stands alone.
    """
    if field not in VALUES:
        raise DescriptionError("unknown field %s" % field)
    if value is None:
        return None
    if field != "content_roles":
        if value not in VALUES[field]:
            raise DescriptionError("%s MUST be one of %s" % (field, ", ".join(VALUES[field])))
        return value
    if (not isinstance(value, list) or not 1 <= len(value) <= 2
            or len(set(value)) != len(value)
            or any(role not in VALUES[field] for role in value)
            or ("unknown" in value and len(value) > 1)):
        raise DescriptionError("content_roles MUST be a list of 1 to 2 different values "
                               "of %s; unknown stands alone" % ", ".join(VALUES[field]))
    return value


def _row(row):
    item = dict(zip(COLUMNS, row))
    for key in ("content_roles", "vlm_answer"):
        if item[key] is not None:
            item[key] = json.loads(item[key])
    return item


def descriptions(conn):
    """Return sha256 -> the description of each image that has a row."""
    return {row[0]: _row(row[1:]) for row in conn.execute(
        "SELECT sha256, %s FROM image_description" % ", ".join(COLUMNS))}


def description(conn, sha256):
    """Return the description of one image, or None."""
    row = conn.execute("SELECT %s FROM image_description WHERE sha256 = ?"
                       % ", ".join(COLUMNS), (sha256,)).fetchone()
    return _row(row) if row else None


def is_linked(conn, sha256):
    """Tell whether `wine_image` links the image to a wine, with a type of IMAGE_TYPES."""
    return conn.execute(
        "SELECT 1 FROM wine_image WHERE sha256 = ? AND image_type IN (%s) LIMIT 1"
        % ", ".join("?" for _ in IMAGE_TYPES), (sha256,) + IMAGE_TYPES).fetchone() is not None


def set_values(conn, sha256, values, now=None):
    """Set the fields of `values` by hand, and return the description.

    A field that `values` does not hold stays as it is. None clears a field. A missing
    row is made with `created_by = 'manual'`. The caller checks the values with
    `check_value`.
    """
    now = now or comments.now_utc()
    conn.execute("INSERT INTO image_description (sha256, created_by, created_at, updated_at) "
                 "VALUES (?, 'manual', ?, ?) ON CONFLICT (sha256) DO NOTHING",
                 (sha256, now, now))
    fields = [field for field in FIELDS if field in values]
    stored = [json.dumps(values[f], separators=(",", ":"))
              if f == "content_roles" and values[f] is not None else values[f] for f in fields]
    conn.execute("UPDATE image_description SET %s updated_at = ? WHERE sha256 = ?"
                 % "".join("%s = ?, " % field for field in fields),
                 stored + [now, sha256])
    return description(conn, sha256)


def preset(description_row):
    """Return the fields of a description that are set, in the order of FIELDS."""
    if not description_row:
        return {}
    return {field: description_row[field] for field in FIELDS
            if description_row[field] is not None}


def pending(conn, max_attempts, limit=None):
    """Return (sha256, folder, extension) of each linked image that waits for the VLM:
    no row, or a row with no VLM fill and fewer than `max_attempts` failures. The image
    with the newest link comes first."""
    sql = ("SELECT i.sha256, i.folder, i.extension FROM wine_image w "
           "JOIN image i ON i.sha256 = w.sha256 "
           "LEFT JOIN image_description d ON d.sha256 = i.sha256 "
           "WHERE w.image_type IN (%s) "
           "AND (d.sha256 IS NULL OR (d.vlm_at IS NULL AND d.vlm_attempts < ?)) "
           "GROUP BY i.sha256 ORDER BY MAX(w.rowid) DESC"
           % ", ".join("?" for _ in IMAGE_TYPES))
    params = IMAGE_TYPES + (max_attempts,)
    if limit is not None:
        sql += " LIMIT ?"
        params += (limit,)
    return conn.execute(sql, params).fetchall()


def _ensure_vlm_row(conn, sha256, now):
    conn.execute("INSERT INTO image_description (sha256, created_by, created_at, updated_at) "
                 "VALUES (?, 'vlm', ?, ?) ON CONFLICT (sha256) DO NOTHING", (sha256, now, now))


def record_vlm(conn, sha256, answer, name, model, now=None):
    """Store a valid VLM answer. Fill only the fields that are not set at this moment.
    Return True when the row took the answer, False when the VLM had filled it already."""
    now = now or comments.now_utc()
    _ensure_vlm_row(conn, sha256, now)
    roles = json.dumps(answer["content_roles"], separators=(",", ":"))
    cursor = conn.execute(
        "UPDATE image_description SET "
        "package_type = COALESCE(package_type, ?), "
        "subject_scope = COALESCE(subject_scope, ?), "
        "package_view = COALESCE(package_view, ?), "
        "content_roles = COALESCE(content_roles, ?), "
        "presentation_mode = COALESCE(presentation_mode, ?), "
        "vlm_at = ?, vlm_name = ?, vlm_model = ?, vlm_answer = ?, vlm_error = NULL, "
        "updated_at = ? WHERE sha256 = ? AND vlm_at IS NULL",
        (answer["package_type"], answer["subject_scope"], answer["package_view"], roles,
         answer["presentation_mode"], now, name, model,
         json.dumps(answer, separators=(",", ":")), now, sha256))
    return cursor.rowcount == 1


def record_failure(conn, sha256, error, count=True, now=None):
    """Store the failure of one VLM call. `count` adds one to `vlm_attempts`; a failure
    of the service (an outage) does not count. A filled row does not change."""
    now = now or comments.now_utc()
    _ensure_vlm_row(conn, sha256, now)
    conn.execute("UPDATE image_description SET vlm_error = ?, "
                 "vlm_attempts = vlm_attempts + ?, updated_at = ? "
                 "WHERE sha256 = ? AND vlm_at IS NULL",
                 (error, 1 if count else 0, now, sha256))


def reset_failed(conn):
    """Set `vlm_attempts` to 0 for each row that the VLM has not filled. Return the count."""
    return conn.execute("UPDATE image_description SET vlm_attempts = 0 "
                        "WHERE vlm_at IS NULL AND vlm_attempts > 0").rowcount


def counts(conn, max_attempts):
    """Return the counts of the linked images: `linked`, `described` (the VLM filled the
    row), `failed` (`max_attempts` failures, no fill), and `pending` (the rest)."""
    linked, described, failed = conn.execute(
        "SELECT count(*), count(d.vlm_at), "
        "coalesce(sum(d.vlm_at IS NULL AND d.vlm_attempts >= ?), 0) "
        "FROM (SELECT DISTINCT sha256 FROM wine_image WHERE image_type IN (%s)) l "
        "LEFT JOIN image_description d ON d.sha256 = l.sha256"
        % ", ".join("?" for _ in IMAGE_TYPES), (max_attempts,) + IMAGE_TYPES).fetchone()
    return {"linked": linked, "described": described, "failed": failed,
            "pending": linked - described - failed}


def write_status(status, path=None):
    """Write the state of the watcher at once (a temporary file and a rename). A failed
    write is ignored: the state is for the indicator alone."""
    path = path or STATUS_PATH
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        handle, temporary = tempfile.mkstemp(prefix=".status.", dir=os.path.dirname(path))
        with os.fdopen(handle, "w", encoding="utf-8") as fh:
            json.dump(status, fh)
        os.replace(temporary, path)
    except OSError:
        pass


def read_status(path=None):
    """Return the state that the watcher wrote, or None."""
    try:
        with open(path or STATUS_PATH, encoding="utf-8") as fh:
            status = json.load(fh)
    except (OSError, ValueError):
        return None
    return status if isinstance(status, dict) else None


def _alive(pid):
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def max_attempts_of(status):
    """Return `max_attempts` of the state that the watcher wrote, else 3."""
    max_attempts = status.get("max_attempts")
    if not isinstance(max_attempts, int) or max_attempts < 1:
        max_attempts = 3
    return max_attempts


def _seconds_between(text, now):
    """Return the whole seconds from the UTC time `text` (the form of `comments.now_utc`)
    to `now`, or None when `text` is not such a time."""
    try:
        then = datetime.datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        return None
    return int((now - then.replace(tzinfo=datetime.timezone.utc)).total_seconds())


def call_view(conn, sha256, stage):
    """Return one image of a VLM call of the watcher, for the dialog of `/dataset` (plan
    49): `sha256`, `stage`, `slug` (the first link), `prompt_kind` and `package_type` of
    a detail, `url` (the file that the VLM gets, on the lab server), and `attempts` and
    `error` of the row for these inputs. A value that is not found is None. A call of the
    stage `label` (plan 61) adds `input_kind` (`package` or `original`)."""
    view = {"sha256": sha256, "stage": stage, "slug": None, "prompt_kind": None,
            "package_type": None, "url": None, "attempts": 0, "error": None}
    row = conn.execute("SELECT wine_slug FROM wine_image WHERE sha256 = ? ORDER BY rowid "
                       "LIMIT 1", (sha256,)).fetchone()
    view["slug"] = row[0] if row else None
    if stage == "label":
        target = label_descriptions.target(conn, sha256)
        if target is None:
            return view
        _, input_sha256, input_kind, folder, extension = target
        view.update(input_kind=input_kind,
                    url="/images/%s/%s.%s" % (folder, input_sha256, extension))
        failure = label_descriptions.failure(conn, sha256)
        if failure:
            view.update(attempts=failure["attempts"], error=failure["error"])
        return view
    if stage == "detail":
        target = image_details.target(conn, sha256)
        if target is None:
            return view
        _, kind, package_type, input_sha256, folder, extension = target
        view.update(prompt_kind=kind, package_type=package_type,
                    url="/images/%s/%s.%s" % (folder, input_sha256, extension))
        row = image_details.detail(conn, sha256)
        if row and (row["prompt_kind"], row["package_type"], row["input_sha256"]) == (
                kind, package_type, input_sha256):
            view.update(attempts=row["vlm_attempts"], error=row["vlm_error"])
        return view
    image = conn.execute("SELECT folder, extension FROM image WHERE sha256 = ?",
                         (sha256,)).fetchone()
    if image:
        view["url"] = "/images/%s/%s.%s" % (image[0], sha256, image[1])
    row = description(conn, sha256)
    if row:
        view.update(attempts=row["vlm_attempts"], error=row["vlm_error"])
    return view


def log_tail(log_path, count):
    """Return the last `count` lines of the watcher log `log_path`, oldest first (plan
    49). The read starts at most TAIL_BYTES before the end. The first line of such a read
    can be a part of a line, so it is dropped. A file that cannot be read gives no line."""
    try:
        with open(log_path, "rb") as fh:
            size = fh.seek(0, os.SEEK_END)
            fh.seek(max(0, size - TAIL_BYTES))
            data = fh.read()
    except OSError:
        return []
    lines = data.decode("utf-8", "replace").splitlines()
    if size > TAIL_BYTES:
        lines = lines[1:]
    return lines[-count:]


def watcher_status(conn, path=None):
    """Return the state of the watcher and the counts, for `GET
    /api/image-description-status`. A missing file, a state that is not known, or a
    process that is gone gives the state `stopped`. `stage` (`class`, `detail`, or
    `label`) names the stage of a `working` watcher; the `details_*` counts are the
    counts of plan 29, the `labels_*` counts and `labels_vlm` belong to stage 3 (plan 61).

    Plan 49: `running` holds a `call_view` of each call that runs, with `started_at` and
    `seconds` (its age). The state `waiting` adds `waiting_since`, `backoff_seconds`,
    `retry_at`, `retry_in_seconds`, and `error_image` (the image of the failed call)."""
    status = read_status(path) or {}
    state = status.get("state")
    if state not in STATES or not _alive(status.get("pid")):
        state = "stopped"
    max_attempts = max_attempts_of(status)
    answer = {"state": state, "pid": status.get("pid") if state != "stopped" else None,
              "max_attempts": max_attempts}
    for key in ("vlm", "model", "endpoint", "timeout_seconds", "workers", "started_at",
                "updated_at", "seconds_per_image", "last", "labels_vlm"):
        answer[key] = status.get(key)
    now = datetime.datetime.now(datetime.timezone.utc)
    answer["running"] = []
    for call in (status.get("running") or []) if state != "stopped" else []:
        if isinstance(call, dict) and isinstance(call.get("sha256"), str):
            view = call_view(conn, call["sha256"], call.get("stage"))
            view.update(started_at=call.get("started_at"),
                        seconds=_seconds_between(call.get("started_at"), now))
            answer["running"].append(view)
    waiting = state == "waiting"
    for key in ("waiting_since", "backoff_seconds", "retry_at"):
        answer[key] = status.get(key) if waiting else None
    late = _seconds_between(answer["retry_at"], now)
    answer["retry_in_seconds"] = max(0, -late) if late is not None else None
    error_sha256 = status.get("error_sha256") if waiting else None
    answer["error_image"] = (call_view(conn, error_sha256, status.get("error_stage"))
                             if isinstance(error_sha256, str) else None)
    answer["error"] = status.get("error") if state == "waiting" else None
    answer["sha256"] = status.get("sha256") if state == "working" else None
    answer["stage"] = status.get("stage") if state == "working" else None
    answer["slug"] = None
    if answer["sha256"]:
        row = conn.execute("SELECT wine_slug FROM wine_image WHERE sha256 = ? ORDER BY rowid "
                           "LIMIT 1", (answer["sha256"],)).fetchone()
        answer["slug"] = row[0] if row else None
    answer.update(counts(conn, max_attempts))
    answer.update(image_details.counts(conn, max_attempts))
    answer.update(label_descriptions.counts(conn, max_attempts))
    return answer


def log_entries(log_path, sha256s, limit=LOG_LIMIT):
    """Return a dict: each sha256 of `sha256s` -> the last `limit` entries of the watcher
    log that name its image, oldest first. An entry starts with a line of the form
    `<UTC time> <the first 12 digits of the sha256> ...`; each line that follows with no
    time belongs to it, for example the text of a cut answer. A file that cannot be read
    gives no entry."""
    wanted = {sha256[:12]: sha256 for sha256 in sha256s}
    found = {sha256: [] for sha256 in sha256s}
    if not wanted:
        return found
    entry = None
    try:
        with open(log_path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.rstrip("\n")
                match = LOG_LINE.match(line)
                if match:
                    sha256 = wanted.get(match.group(1))
                    entry = [line] if sha256 else None
                    if entry is not None:
                        found[sha256].append(entry)
                elif entry is not None:
                    entry.append(line)
    except OSError:
        return {sha256: [] for sha256 in sha256s}
    return {sha256: ["\n".join(lines) for lines in entries[-limit:]]
            for sha256, entries in found.items()}


def detail_failures(conn, log_path, path=None):
    """Return the answer of `GET /api/image-detail-failures`: the images of
    `image_details.failed`, each with `log`, its entries of the watcher log `log_path`.
    `max_attempts` is the value of the running watcher, else 3."""
    max_attempts = max_attempts_of(read_status(path) or {})
    failures = image_details.failed(conn, max_attempts)
    logs = log_entries(log_path, [item["sha256"] for item in failures])
    for item in failures:
        item["log"] = logs[item["sha256"]]
    return {"max_attempts": max_attempts, "log_file": os.path.relpath(log_path, ROOT),
            "failures": failures}
