"""The details of the images: the table `image_detail`.

Stage 2 of the watcher `describe_images.py` sends the detail prompt of each eligible image
to the VLM, with the cut of the image, and stores the valid answer here. One row describes
one original. Read `docs/plans/29_image-details.md`.

An image is eligible when `wine_image` links it to a wine, its `subject_scope` is
`full_package` or `label_closeup`, and its `package_type` has a name in NAMES. The wanted
inputs of an image are the prompt kind, the `package_type`, and the file that the VLM
gets. A row whose inputs differ from the wanted inputs is stale, and the image waits again.

A function that writes runs in the transaction of the caller.
"""
import json

import comments
import labdb

# The readable name and the plural of each package type in the prompts. The key of the
# package prompt is the package type itself. `other` and `unknown` have no name: such an
# image gets no detail.
NAMES = {
    "bottle": ("bottle", "bottles"),
    "can": ("can", "cans"),
    "keg": ("keg", "kegs"),
    "bag": ("bag", "bags"),
    "bag_in_box": ("bag-in-box package", "bag-in-box packages"),
    "tetra_pak": ("Tetra Pak carton", "Tetra Pak cartons"),
    "barrel": ("barrel", "barrels"),
    "decanter": ("decanter", "decanters"),
    "box": ("box", "boxes"),
}
# The prompt kind of each subject scope. Another scope gets no detail.
PROMPT_KINDS = {"full_package": "package", "label_closeup": "label"}
# The image types of `wine_image` whose images get a detail: the types of plan 26.
IMAGE_TYPES = tuple(labdb.IMAGE_FOLDERS)

COLUMNS = ("prompt_kind", "package_type", "input_sha256", "created_at", "updated_at",
           "vlm_at", "vlm_name", "vlm_model", "answer", "vlm_error", "vlm_attempts")


def _marks(values):
    return ", ".join("?" for _ in values)


# The wanted inputs of each eligible image, with the newest link. A full package gets its
# `package` cut; a label close-up gets its `label` cut, else its `package` cut. With no
# cut, the VLM gets the original.
WANTED = (
    "SELECT d.sha256 AS sha256, "
    "CASE d.subject_scope WHEN 'full_package' THEN 'package' ELSE 'label' END "
    "AS prompt_kind, d.package_type AS package_type, "
    "CASE d.subject_scope WHEN 'full_package' THEN coalesce(p.sha256, d.sha256) "
    "ELSE coalesce(l.sha256, p.sha256, d.sha256) END AS input_sha256, w.link AS link "
    "FROM (SELECT sha256, max(rowid) AS link FROM wine_image "
    "WHERE image_type IN (%s) GROUP BY sha256) w "
    "JOIN image_description d ON d.sha256 = w.sha256 "
    "LEFT JOIN image_derivative p ON p.source_sha256 = d.sha256 AND p.kind = 'package' "
    "LEFT JOIN image_derivative l ON l.source_sha256 = d.sha256 AND l.kind = 'label' "
    "WHERE d.subject_scope IN (%s) AND d.package_type IN (%s)"
    % (_marks(IMAGE_TYPES), _marks(PROMPT_KINDS), _marks(NAMES)))
WANTED_PARAMS = IMAGE_TYPES + tuple(PROMPT_KINDS) + tuple(NAMES)
# The stored row has the wanted inputs.
SAME = ("t.prompt_kind = w.prompt_kind AND t.package_type = w.package_type "
        "AND t.input_sha256 = w.input_sha256")
# A target: the original, the inputs, and the store place of the input file.
TARGET = ("SELECT w.sha256, w.prompt_kind, w.package_type, w.input_sha256, i.folder, "
          "i.extension FROM (%s) w JOIN image i ON i.sha256 = w.input_sha256 "
          "LEFT JOIN image_detail t ON t.sha256 = w.sha256 " % WANTED)


def _row(row):
    item = dict(zip(COLUMNS, row))
    if item["answer"] is not None:
        item["answer"] = json.loads(item["answer"])
    return item


def detail(conn, sha256):
    """Return the row of one original, or None."""
    row = conn.execute("SELECT %s FROM image_detail WHERE sha256 = ?" % ", ".join(COLUMNS),
                       (sha256,)).fetchone()
    return _row(row) if row else None


def pending(conn, max_attempts, limit=None):
    """Return the targets that wait for a detail: (sha256, prompt_kind, package_type,
    input_sha256, folder, extension). A target waits with no row, with a stale row, or
    with no answer and fewer than `max_attempts` failures. The newest link comes first."""
    sql = (TARGET + "WHERE t.sha256 IS NULL OR NOT (%s) "
           "OR (t.vlm_at IS NULL AND t.vlm_attempts < ?) ORDER BY w.link DESC" % SAME)
    params = WANTED_PARAMS + (max_attempts,)
    if limit is not None:
        sql += " LIMIT ?"
        params += (limit,)
    return conn.execute(sql, params).fetchall()


def target(conn, sha256):
    """Return the target of one original, also when its detail is done, or None when the
    image is not eligible."""
    return conn.execute(TARGET + "WHERE w.sha256 = ?", WANTED_PARAMS + (sha256,)).fetchone()


def is_done(conn, item):
    """Tell whether the row of a target holds an answer for the inputs of the target."""
    return conn.execute(
        "SELECT 1 FROM image_detail WHERE sha256 = ? AND prompt_kind = ? AND "
        "package_type = ? AND input_sha256 = ? AND vlm_at IS NOT NULL",
        tuple(item[:4])).fetchone() is not None


def _prepare(conn, item, now):
    """Make the row of a target. When the stored inputs differ from the inputs of the
    target, store the new inputs and clear the answer and the failure count."""
    sha256, kind, package_type, input_sha256 = item[:4]
    conn.execute("INSERT INTO image_detail (sha256, prompt_kind, package_type, input_sha256, "
                 "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?) "
                 "ON CONFLICT (sha256) DO NOTHING",
                 (sha256, kind, package_type, input_sha256, now, now))
    conn.execute("UPDATE image_detail SET prompt_kind = ?, package_type = ?, input_sha256 = ?, "
                 "vlm_at = NULL, vlm_name = NULL, vlm_model = NULL, answer = NULL, "
                 "vlm_error = NULL, vlm_attempts = 0, updated_at = ? WHERE sha256 = ? AND "
                 "(prompt_kind != ? OR package_type != ? OR input_sha256 != ?)",
                 (kind, package_type, input_sha256, now, sha256, kind, package_type,
                  input_sha256))


def record_answer(conn, item, answer, name, model, now=None):
    """Store a valid VLM answer for the inputs of a target."""
    now = now or comments.now_utc()
    _prepare(conn, item, now)
    conn.execute("UPDATE image_detail SET answer = ?, vlm_at = ?, vlm_name = ?, "
                 "vlm_model = ?, vlm_error = NULL, updated_at = ? WHERE sha256 = ?",
                 (json.dumps(answer, ensure_ascii=False, separators=(",", ":")), now, name,
                  model, now, item[0]))


def record_failure(conn, item, error, count=True, now=None):
    """Store the failure of one call for the inputs of a target. `count` adds one to
    `vlm_attempts`; a failure of the service does not count. A row with an answer for
    these inputs does not change."""
    now = now or comments.now_utc()
    _prepare(conn, item, now)
    conn.execute("UPDATE image_detail SET vlm_error = ?, vlm_attempts = vlm_attempts + ?, "
                 "updated_at = ? WHERE sha256 = ? AND vlm_at IS NULL",
                 (error, 1 if count else 0, now, item[0]))


def reset_failed(conn):
    """Set `vlm_attempts` to 0 for each row with no answer. Return the count."""
    return conn.execute("UPDATE image_detail SET vlm_attempts = 0 "
                        "WHERE vlm_at IS NULL AND vlm_attempts > 0").rowcount


def counts(conn, max_attempts):
    """Return the counts of the eligible images: `details_eligible`, `details_done` (an
    answer for the wanted inputs), `details_failed` (`max_attempts` failures for the
    wanted inputs), and `details_pending` (the rest)."""
    eligible, done, failed = conn.execute(
        "SELECT count(*), coalesce(sum(t.sha256 IS NOT NULL AND (%s) AND t.vlm_at IS NOT "
        "NULL), 0), coalesce(sum(t.sha256 IS NOT NULL AND (%s) AND t.vlm_at IS NULL AND "
        "t.vlm_attempts >= ?), 0) FROM (%s) w LEFT JOIN image_detail t ON t.sha256 = w.sha256"
        % (SAME, SAME, WANTED), (max_attempts,) + WANTED_PARAMS).fetchone()
    return {"details_eligible": eligible, "details_done": done, "details_failed": failed,
            "details_pending": eligible - done - failed}


def failed(conn, max_attempts):
    """Return the images that `counts` counts in `details_failed`, the newest failure
    first. Each item is a dict: `sha256` (the original), `wine_slug` (of the newest link),
    `prompt_kind`, `package_type`, `input_sha256`, `input_url` (the file that the VLM got,
    on the lab server), `vlm_attempts`, `vlm_error`, and `updated_at`."""
    rows = conn.execute(
        "SELECT w.sha256, s.wine_slug, t.prompt_kind, t.package_type, t.input_sha256, "
        "i.folder, i.extension, t.vlm_attempts, t.vlm_error, t.updated_at FROM (%s) w "
        "JOIN image_detail t ON t.sha256 = w.sha256 "
        "JOIN image i ON i.sha256 = t.input_sha256 JOIN wine_image s ON s.rowid = w.link "
        "WHERE %s AND t.vlm_at IS NULL AND t.vlm_attempts >= ? "
        "ORDER BY t.updated_at DESC, w.link DESC" % (WANTED, SAME),
        WANTED_PARAMS + (max_attempts,)).fetchall()
    return [{"sha256": sha256, "wine_slug": slug, "prompt_kind": kind,
             "package_type": package_type, "input_sha256": input_sha256,
             "input_url": "/images/%s/%s.%s" % (folder, input_sha256, extension),
             "vlm_attempts": attempts, "vlm_error": error, "updated_at": updated}
            for (sha256, slug, kind, package_type, input_sha256, folder, extension, attempts,
                 error, updated) in rows]
