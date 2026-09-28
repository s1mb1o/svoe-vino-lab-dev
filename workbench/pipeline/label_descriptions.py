"""The label descriptions of the images: the tables `image_label_description` and
`image_label_description_failure`. Read `docs/plans/61_label-descriptions.md`.

One row is one label description of one linked image: the answer of
`label_rules.DESCRIBE_PROMPT` (stage 3 of the watcher `describe_images.py`), or a copy
that the owner edited on `/dataset`. An image can have many rows. The latest row (the
newest `created_at`, then the higher `id`) is the effective description. The watcher
sends no request for an image that has a row.

`repair` gives obvious key drift of an answer the key of the prompt. The watcher and
`label_rules.describe` use it. The module imports the standard library and the lab
modules `comments` and `labdb` alone: `label_rules` imports it, and the embedding virtual
environment has no `jsonschema`.

The lab server and the watcher use these functions. A function that writes runs in the
transaction of the caller.
"""
import json

import comments
import labdb

# The keys of an answer of `label_rules.DESCRIBE_PROMPT`, in the order of the prompt.
KEYS = ("texts", "numbers", "vintage", "colours", "design", "marks", "bottle")
# The obvious key drift of an answer: an alias -> the key of the prompt. A key of the
# prompt stands for itself, so a key that differs by the letter case alone gets repaired
# too. The aliases come from the 382 cluster descriptions of 2026-09-27 (`text`,
# `number`) and from the spelling of the prompt (`colours`).
ALIASES = {"text": "texts", "number": "numbers", "colour": "colours", "colors": "colours",
           "color": "colours", "mark": "marks", "vintage_year": "vintage"}
ALIASES.update((key, key) for key in KEYS)
# The image types of `wine_image` whose images get a label description: the types of
# plan 26.
IMAGE_TYPES = tuple(labdb.IMAGE_FOLDERS)
# The largest JSON text of a manual description, in bytes of UTF-8.
MAX_MANUAL_BYTES = 64 * 1024
# The VLM columns of a row, in the order of the table.
VLM_COLUMNS = ("vlm_name", "vlm_endpoint", "vlm_model", "vlm_served_model", "max_tokens",
               "thinking", "input_sha256", "vlm_request", "vlm_reply")
COLUMNS = ("id", "sha256", "description", "created_by", "created_at") + VLM_COLUMNS
JSON_COLUMNS = ("description", "vlm_request", "vlm_reply")


def _marks(values):
    return ", ".join("?" for _ in values)


def dumps(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def repair(value):
    """Return (the repaired object, the renames) of one answer.

    A top-level key that is an alias of a key of the prompt (ALIASES, in any letter case)
    gets the key of the prompt, when the object does not hold that key already. The
    values do not change, and the keys keep their order. `renames` lists each
    `[old key, new key]`. A value that is not an object comes back as it is, with no
    renames.
    """
    if not isinstance(value, dict):
        return value, []
    out, renames = {}, []
    for key, item in value.items():
        target = ALIASES.get(key.lower())
        if target and target != key and target not in value and target not in out:
            out[target] = item
            renames.append([key, target])
        else:
            out[key] = item
    return out, renames


# The input file of each linked image: its `package` cut, else the original. This is
# the rule of `label_rules.card_pictures` for stage 1 of the cluster rules. `link` is the
# newest link of the image.
TARGET = (
    "SELECT l.sha256, coalesce(p.sha256, l.sha256), "
    "CASE WHEN p.sha256 IS NULL THEN 'original' ELSE 'package' END, i.folder, i.extension "
    "FROM (SELECT sha256, max(rowid) AS link FROM wine_image WHERE image_type IN (%s) "
    "GROUP BY sha256) l "
    "LEFT JOIN image_derivative p ON p.source_sha256 = l.sha256 AND p.kind = 'package' "
    "JOIN image i ON i.sha256 = coalesce(p.sha256, l.sha256) "
    % _marks(IMAGE_TYPES))


def pending(conn, max_attempts, limit=None):
    """Return the targets that wait for stage 3: (sha256, input_sha256, input_kind,
    folder, extension). `input_kind` is `package` or `original`. A target waits when its
    image has no row and fewer than `max_attempts` counted failures. The newest link comes
    first."""
    sql = (TARGET + "LEFT JOIN image_label_description_failure f ON f.sha256 = l.sha256 "
           "WHERE NOT EXISTS (SELECT 1 FROM image_label_description d "
           "WHERE d.sha256 = l.sha256) AND coalesce(f.attempts, 0) < ? ORDER BY l.link DESC")
    params = IMAGE_TYPES + (max_attempts,)
    if limit is not None:
        sql += " LIMIT ?"
        params += (limit,)
    return conn.execute(sql, params).fetchall()


def target(conn, sha256):
    """Return the target of one linked image, also when it has a row, or None."""
    return conn.execute(TARGET + "WHERE l.sha256 = ?", IMAGE_TYPES + (sha256,)).fetchone()


def _row(row):
    item = dict(zip(COLUMNS, row))
    for key in JSON_COLUMNS:
        if item[key] is not None:
            item[key] = json.loads(item[key])
    if item["thinking"] is not None:
        item["thinking"] = bool(item["thinking"])
    return item


def rows(conn, sha256):
    """Return the rows of one image, the latest first."""
    return [_row(row) for row in conn.execute(
        "SELECT %s FROM image_label_description WHERE sha256 = ? "
        "ORDER BY created_at DESC, id DESC" % ", ".join(COLUMNS), (sha256,))]


def latest(conn, sha256):
    """Return the latest row of one image, the effective description, or None."""
    row = conn.execute("SELECT %s FROM image_label_description WHERE sha256 = ? "
                       "ORDER BY created_at DESC, id DESC LIMIT 1" % ", ".join(COLUMNS),
                       (sha256,)).fetchone()
    return _row(row) if row else None


def failure(conn, sha256):
    """Return the failures of stage 3 of one image as a dict (`attempts`, `error`,
    `updated_at`), or None."""
    row = conn.execute("SELECT attempts, error, updated_at FROM "
                       "image_label_description_failure WHERE sha256 = ?", (sha256,)).fetchone()
    return dict(zip(("attempts", "error", "updated_at"), row)) if row else None


def record_vlm(conn, sha256, description, vlm, now=None):
    """Store a VLM label description when the image has no row at this moment. `vlm`
    holds the VLM columns (VLM_COLUMNS); `vlm_request` and `vlm_reply` are dicts. Return
    the id of the new row, or None when the image has a row already: a manual row that
    the owner saved during the call stays the latest. A new row removes the failure row
    of the image."""
    now = now or comments.now_utc()
    values = [vlm[key] for key in VLM_COLUMNS]
    values[VLM_COLUMNS.index("thinking")] = int(bool(vlm["thinking"]))
    for key in ("vlm_request", "vlm_reply"):
        values[VLM_COLUMNS.index(key)] = dumps(vlm[key])
    cursor = conn.execute(
        "INSERT INTO image_label_description (sha256, description, created_by, created_at, "
        "%s) SELECT ?, ?, 'vlm', ?, %s WHERE NOT EXISTS (SELECT 1 FROM "
        "image_label_description WHERE sha256 = ?)"
        % (", ".join(VLM_COLUMNS), _marks(VLM_COLUMNS)),
        [sha256, dumps(description), now] + values + [sha256])
    if cursor.rowcount != 1:
        return None
    conn.execute("DELETE FROM image_label_description_failure WHERE sha256 = ?", (sha256,))
    return cursor.lastrowid


def record_failure(conn, sha256, error, count=True, now=None):
    """Store the failure of one call of stage 3. `count` adds one to `attempts`; a
    failure of the service (an outage) does not count. An image with a row does not
    change."""
    now = now or comments.now_utc()
    conn.execute(
        "INSERT INTO image_label_description_failure (sha256, attempts, error, updated_at) "
        "SELECT ?, ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM image_label_description "
        "WHERE sha256 = ?) ON CONFLICT (sha256) DO UPDATE SET "
        "attempts = attempts + excluded.attempts, error = excluded.error, "
        "updated_at = excluded.updated_at",
        (sha256, 1 if count else 0, error, now, sha256))


def reset_failed(conn):
    """Set the failure count of stage 3 to 0 for each image. Return the count."""
    return conn.execute("UPDATE image_label_description_failure SET attempts = 0 "
                        "WHERE attempts > 0").rowcount


def add_manual(conn, sha256, description, now=None):
    """Store a label description that the owner wrote or edited. It becomes the latest
    row. Return its id. The caller checks that `description` is a JSON object."""
    now = now or comments.now_utc()
    return conn.execute(
        "INSERT INTO image_label_description (sha256, description, created_by, created_at) "
        "VALUES (?, ?, 'manual', ?)", (sha256, dumps(description), now)).lastrowid


def remove(conn, row_id):
    """Remove one row. Return the sha256 of its image, or None when no row has this id.
    When the image has no row after the removal, its failure row goes too, so the image
    waits for stage 3 again (owner answer of 2026-09-27)."""
    found = conn.execute("SELECT sha256 FROM image_label_description WHERE id = ?",
                         (row_id,)).fetchone()
    if found is None:
        return None
    sha256 = found[0]
    conn.execute("DELETE FROM image_label_description WHERE id = ?", (row_id,))
    conn.execute("DELETE FROM image_label_description_failure WHERE sha256 = ? AND NOT "
                 "EXISTS (SELECT 1 FROM image_label_description WHERE sha256 = ?)",
                 (sha256, sha256))
    return sha256


def counts(conn, max_attempts):
    """Return the counts of stage 3 of the linked images: `labels_linked`, `labels_done`
    (the image has a row), `labels_failed` (no row and `max_attempts` failures), and
    `labels_pending` (the rest)."""
    linked, done, failed = conn.execute(
        "SELECT count(*), coalesce(sum(EXISTS (SELECT 1 FROM image_label_description d "
        "WHERE d.sha256 = l.sha256)), 0), coalesce(sum(NOT EXISTS (SELECT 1 FROM "
        "image_label_description d WHERE d.sha256 = l.sha256) AND f.attempts >= ?), 0) "
        "FROM (SELECT DISTINCT sha256 FROM wine_image WHERE image_type IN (%s)) l "
        "LEFT JOIN image_label_description_failure f ON f.sha256 = l.sha256"
        % _marks(IMAGE_TYPES), (max_attempts,) + IMAGE_TYPES).fetchone()
    return {"labels_linked": linked, "labels_done": done, "labels_failed": failed,
            "labels_pending": linked - done - failed}


def view(conn, sha256, max_attempts):
    """Return the label descriptions of one image for the dialog of `/dataset`:
    `sha256`, `rows` (the latest first), `latest_id`, `failure`, and `max_attempts`."""
    found = rows(conn, sha256)
    return {"sha256": sha256, "rows": found, "latest_id": found[0]["id"] if found else None,
            "failure": failure(conn, sha256), "max_attempts": max_attempts}
