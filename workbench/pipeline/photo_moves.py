"""Move one photo of a wine between its additional photos and the role `main` or
`main_patched` (plan 95).

The lab server calls `move` for `POST /api/dataset-photo-move`. The owner asked for the
moves on 2026-09-30 and chose the swap. Read `docs/plans/95_new-from-atlas.md`.

Rules:
- One side of a move is `additional`. The other side is `main` or `patched`.
- Additional to a role: the additional row of the photo goes. The photo becomes the row
  of the role. The old photo of the role becomes an additional photo of the type
  `DEMOTED_TYPE`, after the other additional photos (swap).
- A role to additional: the photo becomes an additional photo of the type
  `DEMOTED_TYPE`. The role is then empty.
- A photo that is an additional photo and holds the role too only loses the other row.
- The role `main` and `main_patched` and the type `full_front` each need the cuts of a
  full photo: the package cut and the label cut of a full photo. `move` makes a missing
  cut before its write transaction, so a slow SAM3 does not hold the write lock. SAM3
  does not answer: the photo moves with no new cut, and the answer holds a warning.
- The file stays in its folder: `image.folder` belongs to the file, not to the type.
- The `source_name` of a photo stays. The new row gets the match method `manual`.
"""
import alternatives
import derive
import patches

ADDITIONAL = "additional"
# The side of a move -> the type of `wine_image`.
ROLES = {"main": "main", "patched": "main_patched"}
DEMOTED_TYPE = "full_front"
MATCH_METHOD = "manual"
NO_CUT = ("The photo moved with no processed file. The card shows it as it is; the "
          "button ↻ of the additional photo processes it again.")


def _role_row(conn, slug, image_type):
    return conn.execute("SELECT sha256, source_name FROM wine_image WHERE wine_slug = ? "
                        "AND image_type = ?", (slug, image_type)).fetchone()


def _additional_row(conn, slug, digest):
    return conn.execute(
        "SELECT image_type, source_name FROM wine_image WHERE wine_slug = ? AND "
        "sha256 = ? AND image_type IN (%s)" % ", ".join("?" for _ in alternatives.TYPES),
        (slug, digest) + alternatives.TYPES).fetchone()


def _read_state(conn, slug, digest, role):
    """Return the rows that a move reads: the role row, the additional row of `digest`,
    and the additional row of the photo of the role."""
    held = _role_row(conn, slug, role)
    extra = _additional_row(conn, slug, digest)
    held_extra = _additional_row(conn, slug, held[0]) if held else None
    return held, extra, held_extra


def _full_cuts(conn, db_path, digest, segmenter, warnings):
    """Return the processing results that make `digest` a full photo: its package cut
    and the label cut of a full photo."""
    folder, extension = conn.execute("SELECT folder, extension FROM image WHERE "
                                     "sha256 = ?", (digest,)).fetchone()
    path = patches.file_path(db_path, folder, digest, extension)
    notes = []
    package = alternatives.process_image(conn, db_path, digest, path, "full", segmenter,
                                         notes)
    if (package.unavailable or package.unreadable or package.errors
            or not (package.links or package.present)):
        warnings.append(NO_CUT)
    label = alternatives.full_label_cut(conn, db_path, digest, path, segmenter, notes)
    warnings.extend(notes)
    return [package, label]


def _check(slug, digest, source, target):
    if not isinstance(slug, str) or not slug:
        raise patches.PatchError(400, "the request holds no wine slug")
    if not isinstance(digest, str) or not digest:
        raise patches.PatchError(400, "the request holds no sha256")
    sides = {source, target}
    if ADDITIONAL not in sides or len(sides) != 2 or not sides - {ADDITIONAL} <= set(ROLES):
        raise patches.PatchError(400, "a move goes from `additional` to `main` or "
                                      "`patched`, or back")


def move(conn, db_path, slug, digest, source, target, segmenter=None):
    """Move the photo `digest` of the wine `slug` from `source` to `target`. Return a
    dict: `sha256`, `from`, `to`, `swapped` (the SHA-256 of the old photo of the role
    that became an additional photo, or None), and `warnings`.

    `conn` is a write connection with `isolation_level` None. `segmenter` is the SAM3
    client; None means `derive.Sam3Client()`.
    """
    _check(slug, digest, source, target)
    if conn.execute("SELECT 1 FROM wine_catalog WHERE wine_slug = ?",
                    (slug,)).fetchone() is None:
        raise patches.PatchError(404, "no wine with the slug %s" % slug)
    to_role = source == ADDITIONAL
    role = ROLES[target if to_role else source]
    before = _read_state(conn, slug, digest, role)
    held, extra, held_extra = before
    if to_role and extra is None:
        raise patches.PatchError(404, "the wine %s has no additional photo %s"
                                 % (slug, digest))
    if not to_role and (held is None or held[0] != digest):
        raise patches.PatchError(404, "the wine %s has no %s photo %s"
                                 % (slug, source, digest))

    # The photos that end as a full photo with a new row.
    full = []
    if to_role and not (held and held[0] == digest):
        full.append(digest)
    swapped = held[0] if to_role and held and held[0] != digest else None
    if swapped and held_extra is None:
        full.append(swapped)
    if not to_role and extra is None:
        full.append(digest)
    warnings, results = [], []
    client = None
    for item in full:
        if not alternatives.has_current_cuts(conn, item, "full"):
            client = client or segmenter or derive.Sam3Client()
            results.extend(_full_cuts(conn, db_path, item, client, warnings))

    conn.execute("BEGIN IMMEDIATE")
    try:
        if _read_state(conn, slug, digest, role) != before:
            raise patches.PatchError(409, "the photos of %s changed meanwhile" % slug)
        insert = ("INSERT INTO wine_image (wine_slug, image_type, sha256, source_name, "
                  "match_method) VALUES (?, ?, ?, ?, ?)")
        if to_role:
            conn.execute("DELETE FROM wine_image WHERE wine_slug = ? AND sha256 = ? AND "
                         "image_type = ?", (slug, digest, extra[0]))
            if held is None or held[0] != digest:
                conn.execute("DELETE FROM wine_image WHERE wine_slug = ? AND "
                             "image_type = ?", (slug, role))
                conn.execute(insert, (slug, role, digest, extra[1], MATCH_METHOD))
                if held is not None and held_extra is None:
                    conn.execute(insert, (slug, DEMOTED_TYPE, held[0], held[1],
                                          MATCH_METHOD))
        else:
            conn.execute("DELETE FROM wine_image WHERE wine_slug = ? AND image_type = ?",
                         (slug, role))
            if extra is None:
                conn.execute(insert, (slug, DEMOTED_TYPE, digest, held[1], MATCH_METHOD))
        for derivatives in results:
            alternatives.write_processed_rows(conn, derivatives)
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    return {"sha256": digest, "from": source, "to": target, "swapped": swapped,
            "warnings": warnings}
