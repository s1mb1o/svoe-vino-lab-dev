"""Merge a manual wine into an existing wine in one database transaction.

Keep test-photo annotations and image bytes. The catalogue and testset references
move to the destination. Delete the source catalogue row. Saved runs and annotation
provenance stay unchanged. A filename collision keeps both photos.
"""
from contextlib import closing
import sqlite3

import labdb
import manual_wines
import testsets
import wine_vintages


class MergeError(Exception):
    """A merge is not allowed. `code` is the HTTP status."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def source_slug(value):
    """Validate the manual source, including the reserved-place guard."""
    try:
        return manual_wines.check_slug(value)
    except manual_wines.WineError as exc:
        raise MergeError(exc.code, str(exc)) from exc


def _wine(conn, slug):
    row = conn.execute("SELECT wine_slug, COALESCE(name_patched, name) AS name, state "
                       "FROM wine_catalog WHERE wine_slug = ?", (slug,)).fetchone()
    if row is None:
        raise MergeError(404, "no wine with the slug %s" % slug)
    return dict(row)


def _target(conn, source, value):
    if not isinstance(value, str) or not value.strip():
        raise MergeError(400, "the request holds no destination wine_slug")
    target = value.strip()
    try:
        target.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise MergeError(400, "the destination wine_slug is not valid text") from exc
    if target == source:
        raise MergeError(400, "the source and destination wines are the same")
    if target in manual_wines.RESERVED_SLUGS:
        raise MergeError(400, "the destination wine_slug is reserved")
    return _wine(conn, target)


def _preview(conn, source):
    wine = _wine(conn, source)
    sets = [dict(row) for row in conn.execute(
        "SELECT set_name AS name, COUNT(*) AS photos FROM test_photo WHERE place = ? "
        "GROUP BY set_name ORDER BY set_name", (source,))]
    return {"source": wine, "photos": sum(row["photos"] for row in sets),
            "testsets": sets, "catalogue_images": conn.execute(
                "SELECT COUNT(*) FROM wine_image WHERE wine_slug = ?", (source,))
            .fetchone()[0]}


def preview(db_path, slug):
    """Return the current source counts and the available destination wines."""
    source = source_slug(slug)
    with closing(labdb.connect(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN")
        result = _preview(conn, source)
        result["targets"] = [dict(row) for row in conn.execute(
            "SELECT wine_slug AS slug, COALESCE(name_patched, name) AS name, state "
            "FROM wine_catalog WHERE wine_slug <> ? ORDER BY name, wine_slug", (source,))]
        return result


def _transfer_rows(conn, table, source, target):
    """Transfer a table keyed by wine_slug. Keep an existing destination value."""
    columns = [row[1] for row in conn.execute('PRAGMA table_info("%s")' % table)]
    names = ", ".join('"%s"' % name for name in columns)
    values = ", ".join("?" if name == "wine_slug" else '"%s"' % name
                       for name in columns)
    conn.execute('INSERT INTO "%s" (%s) SELECT %s FROM "%s" WHERE wine_slug = ? '
                 'ON CONFLICT DO NOTHING' % (table, names, values, table), (target, source))
    conn.execute('DELETE FROM "%s" WHERE wine_slug = ?' % table, (source,))


def _images(conn, source, target):
    has_main = conn.execute("SELECT 1 FROM wine_image WHERE wine_slug = ? "
                            "AND image_type = 'main'", (target,)).fetchone() is not None
    for row in conn.execute("SELECT * FROM wine_image WHERE wine_slug = ? "
                            "ORDER BY rowid", (source,)).fetchall():
        kind = row["image_type"]
        if kind in ("main", "main_patched") and (has_main or conn.execute(
                "SELECT 1 FROM wine_image WHERE wine_slug = ? AND image_type = ?",
                (target, kind)).fetchone()):
            kind = "full_front"
        conn.execute("INSERT INTO wine_image (wine_slug, image_type, sha256, "
                     "source_name, match_method) VALUES (?, ?, ?, ?, ?) "
                     "ON CONFLICT DO NOTHING",
                     (target, kind, row["sha256"], row["source_name"], row["match_method"]))
    conn.execute("DELETE FROM wine_image WHERE wine_slug = ?", (source,))


def _variants(conn, source, target):
    affected = set()
    for row in conn.execute("SELECT set_name, group_no FROM test_variant "
                            "WHERE wine_slug = ?", (source,)).fetchall():
        name, group = row
        affected.add(name)
        existing = conn.execute("SELECT group_no FROM test_variant WHERE set_name = ? "
                                "AND wine_slug = ?", (name, target)).fetchone()
        if existing is None:
            conn.execute("INSERT INTO test_variant VALUES (?, ?, ?)", (name, target, group))
        elif existing[0] != group:
            # Two names of one identity connect their existing variant groups.
            conn.execute("UPDATE test_variant SET group_no = ? WHERE set_name = ? "
                         "AND group_no = ?", (existing[0], name, group))
    conn.execute("DELETE FROM test_variant WHERE wine_slug = ?", (source,))
    return affected


def _similar(conn, source, target):
    rows = conn.execute("SELECT * FROM wine_similar WHERE wine_slug_a = ? "
                        "OR wine_slug_b = ?", (source, source)).fetchall()
    conn.execute("DELETE FROM wine_similar WHERE wine_slug_a = ? OR wine_slug_b = ?",
                 (source, source))
    for row in rows:
        a = target if row["wine_slug_a"] == source else row["wine_slug_a"]
        b = target if row["wine_slug_b"] == source else row["wine_slug_b"]
        if a != b:
            conn.execute("INSERT INTO wine_similar VALUES (?, ?, ?) ON CONFLICT DO NOTHING",
                         (*sorted((a, b)), row["created_at"]))


def merge(db_path, body):
    """Transfer all source references, then delete the source. Roll back on any error."""
    if not isinstance(body, dict):
        raise MergeError(400, "the body MUST be a JSON object")
    source = source_slug(body.get("slug"))
    with closing(labdb.connect(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN IMMEDIATE")
        try:
            result = _preview(conn, source)
            target = _target(conn, source, body.get("to"))["wine_slug"]
            affected = {row["name"] for row in result["testsets"]}
            renamed = 0
            for row in conn.execute("SELECT set_name, file_name FROM test_photo "
                                    "WHERE place = ? ORDER BY set_name, file_name",
                                    (source,)).fetchall():
                name = testsets.free_name(conn, row["set_name"], target, row["file_name"],
                                          tag="merged")
                renamed += name != row["file_name"]
                # Only the key changes. The comment foreign key cascades to the new key.
                conn.execute("UPDATE test_photo SET place = ?, file_name = ? "
                             "WHERE set_name = ? AND place = ? AND file_name = ?",
                             (target, name, row["set_name"], source, row["file_name"]))
            affected.update(row[0] for row in conn.execute(
                "SELECT DISTINCT set_name FROM test_photo WHERE reassign_to = ?", (source,)))
            conn.execute("UPDATE test_photo SET reassign_to = ? WHERE reassign_to = ?",
                         (target, source))
            affected.update(_variants(conn, source, target))
            _images(conn, source, target)
            conn.execute("UPDATE wine_comment SET wine_slug = ? WHERE wine_slug = ?",
                         (target, source))
            for table in ("wine_code", "wine_atlas_binding", "wine_favorite",
                          "wine_tag", "wine_beverage_type"):
                _transfer_rows(conn, table, source, target)
            _similar(conn, source, target)
            wine_vintages.reassign(conn, source, target)
            # Import refusals describe the deleted source card, not the destination card.
            conn.execute("DELETE FROM website_refusal WHERE wine_slug = ?", (source,))
            conn.execute("DELETE FROM wine_catalog WHERE wine_slug = ?", (source,))
            conn.execute("UPDATE wine_catalog SET modified_at = "
                         "strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE wine_slug = ?", (target,))
            for name in affected:
                conn.execute("UPDATE test_set SET edited_at = ? WHERE set_name = ?",
                             (testsets.now_local(), name))
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
    return {"ok": True, "from": source, "to": target, "photos": result["photos"],
            "testsets": result["testsets"], "catalogue_images": result["catalogue_images"],
            "renamed_files": renamed, "removed": True, "rebuild_embeddings": True}
