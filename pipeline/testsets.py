"""The test sets of the lab database: the reads and the writes of the Testset page.

The tables are `test_set`, `test_photo`, `test_wine_note`, `test_excluded`, and
`test_variant`. The database is the source of the labels: the page writes here, and
`export_testset.py` writes the JSON files of a set from the rows. The owner chose this on
2026-09-25T12:40:00+0300. Read `docs/plans/24_testset-page.md`.

One label entry of `review-labels.json` is one row of `test_photo`. `ENTRY_FIELDS` names
the column of each JSON field and the test of a value that the column keeps exactly. A
field with another value, and a field that no column names, goes into the JSON object
`extra`. So the export gives the same entry back.

A function that writes runs in the transaction of the caller. It sets `ts` of the entry
and `test_set.edited_at`. The other fields of the entry do not change, as `_entry` of
`scripts/review_server.py` does. When no field of the entry is left, `ts` becomes NULL,
and the export writes no entry. A write to a wine of each state is allowed.

`move_photo` gives a photo another place. The right sidebar of the Testset page is the
Drawer (`__drawer__`): a photo there waits for a wine, it stays there between launches,
and no run uses it. The NULL place (`__null__`) is the row "No Match" of the table: a run
uses its photos, and the right answer is no match. The owner chose the sidebar on
2026-09-25T18:05:36+0300 and the two places on 2026-09-26T00:29:00 (plan 36). A move
clears the label, because the label
judged the old place, and writes the old place into `moved_from`. The other fields stay.

`upload_photo` adds a file that the page gets from a drop of the file manager (the macOS
Finder) onto the sidebar or onto a wine row. The owner chose this on
2026-09-25T18:25:10+0300. The new photo has no label. A new image keeps the name of its
file. An image that the set holds already keeps the file name of the set: a place holds
one image once, and another place MAY hold it again, for example for the label
`negative`.
"""
import hashlib
import io
import json
import math
import os
import re
import time

from PIL import Image

import comments
import imagestore

LABELS = ("positive", "negative", "unusable", "variant")
# The virtual NULL wine, the row "No Match" of the page: a photo of this place matches no
# card of the catalogue, and a run uses it. Such a photo takes `positive` (confirmed) or
# `unusable` alone, as in the old tool.
NULL_SLUG = "__null__"
NULL_NAME = "No Match"
NULL_LABELS = ("positive", "unusable")
# The Drawer, the right sidebar of the page: a photo of this place waits for a wine, and no
# run uses it. It takes no label (plan 36, owner answer of 2026-09-26T00:29:00+0300).
DRAWER_SLUG = "__drawer__"
DRAWER_NAME = "Drawer"
TEXT_MAX = comments.TEXT_MAX
REASON_MAX = 1000
# The form of `ts`, as the old tool writes it: the local time with its offset.
TS_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
# `NN_confNNN.<ext>`: the rank and the confidence of a photo that the pipeline found.
NAME_RE = re.compile(r"^(\d+)_conf(\d+)\.")
RANK_RE = re.compile(r"^(\d+)_")
# The EXIF orientations that turn the image by 90 degrees.
TURNED = frozenset({5, 6, 7, 8})
# The states of a wine that get a row of the page when the set holds no photo of it.
LISTED_STATES = ("Active", "Disabled")


def _text(value):
    return isinstance(value, str) and value != ""


def _comment(value):
    return _text(value) and len(value) <= TEXT_MAX


def _label(value):
    return isinstance(value, str) and value in LABELS


def _number(value):
    return isinstance(value, float) and math.isfinite(value)


def _object(value):
    return isinstance(value, dict)


def _true(value):
    return value is True


# (JSON field, column, the test of a value that the column keeps exactly).
ENTRY_FIELDS = (
    ("label", "label", _label),
    ("delete", "marked_delete", _true),
    ("comment", "comment", _comment),
    ("ts", "ts", _text),
    ("proposed", "proposed", _label),
    ("by", "proposed_by", _text),
    ("confidence", "confidence", _number),
    ("source_url", "source_url", _text),
    ("moved_from", "moved_from", _text),
    ("copied_from", "copied_from", _text),
    ("reassign_to", "reassign_to", _text),
    ("prefilled_from", "prefilled_from", _object),
)
BOX_COLUMNS = ("box_left", "box_top", "box_right", "box_bottom")
ENTRY_COLUMNS = tuple(column for _, column, _ in ENTRY_FIELDS) + ("extra",) + BOX_COLUMNS
# The fields of the note of a wine: (JSON field, column, test).
NOTE_FIELDS = (("comment", "comment", _comment), ("ts", "ts", _text))


class TestsetError(Exception):
    """A request of the Testset page is not valid. `code` is the HTTP status."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def now_local():
    """Return the present local time in the form of `ts`."""
    return time.strftime(TS_FORMAT)


def oriented_size(path):
    """Return (width, height) of the image at `path` after its EXIF orientation. The
    browser shows a photo after the orientation, so the box of the page uses this size.
    Raise `OSError` when Pillow cannot read the file."""
    with Image.open(path) as image:
        width, height = image.size
        if image.getexif().get(0x0112) in TURNED:
            return height, width
    return width, height


def check_box(value, size):
    """Return `value` as a tuple of four integers when it is a box inside `size`, else
    None. `size` is (width, height) after the orientation, or None when it is not
    known."""
    if not (isinstance(value, list) and len(value) == 4
            and all(isinstance(v, int) and not isinstance(v, bool) for v in value)):
        return None
    left, top, right, bottom = value
    if size is None or not (0 <= left < right <= size[0] and 0 <= top < bottom <= size[1]):
        return None
    return tuple(value)


def _split(entry, fields):
    """Return (column -> value, the extra fields) of one JSON object."""
    known = {key: (column, test) for key, column, test in fields}
    values, extra = {}, {}
    for key, value in entry.items():
        if key in known and known[key][1](value):
            values[known[key][0]] = value
        else:
            extra[key] = value
    return values, extra


def _extra_text(extra):
    return json.dumps(extra, ensure_ascii=False) if extra else None


def entry_columns(entry, size=None):
    """Return the columns of `ENTRY_COLUMNS` of one label entry.

    `size` is the size of the photo after its EXIF orientation, or None. A box goes into
    its columns only when it lies inside that size; else it goes into `extra`.
    """
    fields = {key: value for key, value in entry.items() if key != "box"}
    values, extra = _split(fields, ENTRY_FIELDS)
    row = dict.fromkeys(ENTRY_COLUMNS)
    row.update(values)
    row["marked_delete"] = 1 if values.get("marked_delete") else 0
    if row["prefilled_from"] is not None:
        row["prefilled_from"] = json.dumps(row["prefilled_from"], ensure_ascii=False)
    if "box" in entry:
        box = check_box(entry["box"], size)
        if box is None:
            extra["box"] = entry["box"]
        else:
            row.update(zip(BOX_COLUMNS, box))
    row["extra"] = _extra_text(extra)
    return row


def entry_of(row):
    """Return the JSON label entry of one row of `test_photo`: a dict, empty when the row
    holds no field."""
    entry = {}
    for key, column, _ in ENTRY_FIELDS:
        value = row[column]
        if column == "marked_delete":
            if value:
                entry[key] = True
        elif value is not None:
            entry[key] = json.loads(value) if column == "prefilled_from" else value
    if row["box_left"] is not None:
        entry["box"] = [row[column] for column in BOX_COLUMNS]
    if row["extra"]:
        entry.update(json.loads(row["extra"]))
    return entry


def note_columns(note):
    """Return (comment, ts, extra) of the note of one wine."""
    values, extra = _split(note, NOTE_FIELDS)
    return values.get("comment"), values.get("ts"), _extra_text(extra)


def note_of(comment, ts, extra):
    """Return the JSON note of one wine, empty when the row holds no field."""
    note = {key: value for key, value in (("comment", comment), ("ts", ts))
            if value is not None}
    if extra:
        note.update(json.loads(extra))
    return note


def _has_field(row):
    """Tell whether one row of `test_photo` holds a field other than `ts`."""
    return any(row[column] is not None for column in ENTRY_COLUMNS
               if column not in ("ts", "marked_delete")) or bool(row["marked_delete"])


def photo_rank(name):
    """The order of the photos of one place: the rank of the name, then the name."""
    match = RANK_RE.match(name)
    return (int(match.group(1)), name) if match else (9999, name)


def photo_conf(name):
    """The confidence of the name `NN_confNNN.<ext>`, or None."""
    match = NAME_RE.match(name)
    return int(match.group(2)) if match else None


PHOTO_QUERY = ("SELECT p.place, p.file_name, p.sha256, i.folder, i.extension, i.width, "
               "i.height, %s FROM test_photo p JOIN image i ON i.sha256 = p.sha256 "
               "WHERE p.set_name = ?" % ", ".join("p." + c for c in ENTRY_COLUMNS))


def photo_rows(conn, set_name, place=None, file_name=None):
    """Return the rows of the photos of one set as dicts, or of one photo."""
    sql, args = PHOTO_QUERY, [set_name]
    if place is not None:
        sql += " AND p.place = ? AND p.file_name = ?"
        args += [place, file_name]
    keys = ("place", "file_name", "sha256", "folder", "extension", "width",
            "height") + ENTRY_COLUMNS
    return [dict(zip(keys, row)) for row in conn.execute(sql, args)]


def photo_view(row):
    """Return one photo for the page: its file, its image, and its JSON entry."""
    return {"file": row["file_name"], "sha256": row["sha256"],
            "url": "/images/%s/%s.%s" % (row["folder"], row["sha256"], row["extension"]),
            "width": row["width"], "height": row["height"],
            "conf": photo_conf(row["file_name"]), "entry": entry_of(row)}


def counts(conn, set_name):
    """Return the counts of one set, with the keys of `count_state` of the old tool, and
    `photos` and `boxes`."""
    (photos, positive, negative, unusable, variant, reassigned, copied, deleting,
     commented, proposed, no_match, no_match_pending, boxes, drawer) = conn.execute(
        "SELECT count(*), "
        "count(*) FILTER (WHERE label = 'positive'), "
        "count(*) FILTER (WHERE label = 'negative'), "
        "count(*) FILTER (WHERE label = 'unusable'), "
        "count(*) FILTER (WHERE label = 'variant'), "
        "count(*) FILTER (WHERE reassign_to IS NOT NULL), "
        "count(*) FILTER (WHERE json_extract(extra, '$.copy_to') IS NOT NULL), "
        "count(*) FILTER (WHERE marked_delete = 1), "
        "count(*) FILTER (WHERE comment IS NOT NULL), "
        "count(*) FILTER (WHERE proposed IS NOT NULL AND label IS NULL), "
        "count(*) FILTER (WHERE place = ?), "
        "count(*) FILTER (WHERE reassign_to = ?), "
        "count(*) FILTER (WHERE box_left IS NOT NULL), "
        "count(*) FILTER (WHERE place = ?) "
        "FROM test_photo WHERE set_name = ?",
        (NULL_SLUG, NULL_SLUG, DRAWER_SLUG, set_name)).fetchone()
    notes = conn.execute("SELECT count(*) FROM test_wine_note WHERE set_name = ? "
                         "AND comment IS NOT NULL", (set_name,)).fetchone()[0]
    return {"positive": positive, "negative": negative, "unusable": unusable,
            "variant": variant, "labelled": positive + negative + unusable + variant,
            "reassigned": reassigned, "copied": copied, "deleting": deleting,
            "commented": commented, "proposed": proposed, "wine_notes": notes,
            "no_match": no_match, "no_match_pending": no_match_pending,
            "photos": photos, "boxes": boxes, "drawer": drawer}


def set_names(conn):
    """Return the names of the sets in the order of their first import."""
    return [name for (name,) in conn.execute("SELECT set_name FROM test_set ORDER BY rowid")]


def _sets(conn):
    """Return each set with its counts for the set selector of the page."""
    stats = {name: (photos, labelled) for name, photos, labelled in conn.execute(
        "SELECT set_name, count(*), count(label) FROM test_photo GROUP BY set_name")}
    return [{"name": name, "photos": stats.get(name, (0, 0))[0],
             "labelled": stats.get(name, (0, 0))[1], "source_dir": source, "edited_at": edited}
            for name, source, edited in conn.execute(
                "SELECT set_name, source_dir, edited_at FROM test_set ORDER BY rowid")]


def groups(conn, set_name):
    """Return group id -> {id, slugs} of the variant groups of one set."""
    out = {}
    for slug, number in conn.execute("SELECT wine_slug, group_no FROM test_variant "
                                     "WHERE set_name = ? ORDER BY group_no, wine_slug",
                                     (set_name,)):
        gid = "g%03d" % number
        out.setdefault(gid, {"id": gid, "slugs": []})["slugs"].append(slug)
    return out


def _wine_row(slug, wine, card, photos):
    """Return the row of one wine for the page. `wine` is None for a place that
    `wine_catalog` does not hold."""
    name, producer, category, color, region, grapes, state = wine or ("",) * 6 + (None,)
    confs = [p["conf"] for p in photos if p["conf"] is not None]
    card = card or {}
    return {"slug": slug, "name": name or "", "producer": producer or "",
            "category": category or "", "color": color or "", "region": region or "",
            "grapes": grapes or "", "state": state, "in_catalog": wine is not None,
            "bottle_url": card.get("_patch_image_url") or card.get("main_image_url"),
            "patched": bool(card.get("_patch_url")), "photos": photos,
            "min_conf": min(confs) if confs else None, "catalog_only": not photos}


def set_view(conn, set_name, card_images):
    """Return the answer of `GET /api/testset` for one set, or for the first set when
    `set_name` is None. `card_images(conn)` is `lab_server.card_images`.

    The rows follow the answer of the owner of 2026-09-25T17:01:44+0300 (Q1): a row for
    each `Active` and `Disabled` wine, and a row for each place that holds a photo of the
    set, also when its wine is `Removed` or is not in `wine_catalog`. The NULL row
    ("No Match") stands first, the Drawer row second (plan 36). The other rows are in
    slug order; the page sorts them.
    """
    names = set_names(conn)
    if set_name is None:
        if not names:
            raise TestsetError(404, "the database holds no test set; import one with "
                                    "`python3 pipeline/import_testsets.py --db <db>`")
        set_name = names[0]
    if set_name not in names:
        raise TestsetError(404, "no test set %r" % set_name)
    wines = {row[0]: row[1:] for row in conn.execute(
        "SELECT wine_slug, name, producer, category, color, region, grapes, state "
        "FROM wine_catalog")}
    by_place = {}
    for row in sorted(photo_rows(conn, set_name),
                      key=lambda r: (r["place"], photo_rank(r["file_name"]))):
        by_place.setdefault(row["place"], []).append(photo_view(row))
    cards = card_images(conn)
    excluded = {slug: (reason, ts) for slug, reason, ts in conn.execute(
        "SELECT wine_slug, reason, ts FROM test_excluded WHERE set_name = ?", (set_name,))}
    notes = {slug: comment for slug, comment in conn.execute(
        "SELECT wine_slug, comment FROM test_wine_note WHERE set_name = ?", (set_name,))}
    variant = groups(conn, set_name)
    group_of = {slug: gid for gid, group in variant.items() for slug in group["slugs"]}
    slugs = {slug for slug, wine in wines.items() if wine[-1] in LISTED_STATES}
    slugs.update(place for place in by_place if place not in (NULL_SLUG, DRAWER_SLUG))
    null = _wine_row(NULL_SLUG, None, None, by_place.get(NULL_SLUG, []))
    null.update(name=NULL_NAME, null_row=True, catalog_only=False)
    drawer = _wine_row(DRAWER_SLUG, None, None, by_place.get(DRAWER_SLUG, []))
    drawer.update(name=DRAWER_NAME, drawer_row=True, catalog_only=False)
    rows = [null, drawer] + [_wine_row(slug, wines.get(slug), cards.get(slug),
                                       by_place.get(slug, [])) for slug in sorted(slugs)]
    for row in rows:
        reason, ts = excluded.get(row["slug"], (None, None))
        row.update(excluded=row["slug"] in excluded, exclude_reason=reason or "",
                   group=group_of.get(row["slug"]), note=notes.get(row["slug"]) or "")
    edited_at, source_dir = conn.execute(
        "SELECT edited_at, source_dir FROM test_set WHERE set_name = ?", (set_name,)).fetchone()
    return {"sets": _sets(conn), "set": set_name, "edited_at": edited_at,
            "source_dir": source_dir, "rows": rows, "counts": counts(conn, set_name),
            "groups": variant, "labels": list(LABELS), "null_labels": list(NULL_LABELS)}


def _check_set(conn, set_name):
    if not isinstance(set_name, str) or conn.execute(
            "SELECT 1 FROM test_set WHERE set_name = ?", (set_name,)).fetchone() is None:
        raise TestsetError(404, "no test set %r" % (set_name,))


def _check_place(place, file_name):
    if not isinstance(place, str) or not place:
        raise TestsetError(400, "the request holds no `place`")
    if not isinstance(file_name, str) or not file_name:
        raise TestsetError(400, "the request holds no `file`")


def _edited(conn, set_name, now):
    conn.execute("UPDATE test_set SET edited_at = ? WHERE set_name = ?", (now, set_name))


def _write_photo(conn, set_name, place, file_name, keys, change):
    """Change one photo, in the transaction of the caller. `change(row)` returns the new
    values (column -> value) and MAY refuse the change with `TestsetError`. `keys` are the
    JSON fields that the change sets: they leave `extra`. Return the answer: the photo and
    the counts of the set."""
    _check_set(conn, set_name)
    _check_place(place, file_name)
    found = photo_rows(conn, set_name, place, file_name)
    if not found:
        raise TestsetError(404, "the set %s has no photo %s/%s" % (set_name, place, file_name))
    row = found[0]
    values = change(row)
    extra = json.loads(row["extra"]) if row["extra"] else {}
    for key in tuple(keys) + ("ts",):
        extra.pop(key, None)
    row.update(values)
    row["extra"] = _extra_text(extra)
    now = now_local()
    row["ts"] = now if _has_field(row) else None
    conn.execute("UPDATE test_photo SET %s WHERE set_name = ? AND place = ? AND file_name = ?"
                 % ", ".join("%s = ?" % column for column in ENTRY_COLUMNS),
                 [row[column] for column in ENTRY_COLUMNS] + [set_name, place, file_name])
    _edited(conn, set_name, now)
    return {"ok": True, "set": set_name, "place": place, "file": file_name,
            "photo": photo_view(row), "counts": counts(conn, set_name)}


def set_label(conn, set_name, place, file_name, label):
    """Set or clear (`label` None or "") the label of one photo."""
    label = label or None
    if label is not None and label not in LABELS:
        raise TestsetError(400, "`label` MUST be one of %s, or null" % ", ".join(LABELS))
    if place == NULL_SLUG and label is not None and label not in NULL_LABELS:
        raise TestsetError(400, "a photo of the NULL wine takes %s alone"
                           % " or ".join(NULL_LABELS))
    if place == DRAWER_SLUG and label is not None:
        raise TestsetError(400, "a photo of the Drawer takes no label; move it to a wine "
                                "or to No Match first")
    return _write_photo(conn, set_name, place, file_name, ("label",),
                        lambda row: {"label": label})


def set_delete(conn, set_name, place, file_name, on):
    """Mark one photo for deletion (`on` true), or take the mark away. No file moves."""
    if not isinstance(on, bool):
        raise TestsetError(400, "`delete` MUST be true or false")
    return _write_photo(conn, set_name, place, file_name, ("delete",),
                        lambda row: {"marked_delete": int(on)})


def clean_note(text, what):
    """Return the stored form of a comment or a note, or None for an empty text."""
    if text is None or (isinstance(text, str) and not text.strip()):
        return None
    try:
        return comments.clean_text(text)
    except comments.CommentError as exc:
        raise TestsetError(400, str(exc).replace("the comment", what))


def set_comment(conn, set_name, place, file_name, text):
    """Set the comment of one photo. An empty text removes it."""
    comment = clean_note(text, "the comment")
    return _write_photo(conn, set_name, place, file_name, ("comment",),
                        lambda row: {"comment": comment})


def set_box(conn, set_name, place, file_name, box):
    """Set the box of the main object of one photo, or remove it (`box` None).

    The box is in the pixels of the photo after its EXIF orientation. The size comes
    from the stored file of the image store of the database of `conn`."""
    if box is not None and not (isinstance(box, list) and len(box) == 4 and all(
            isinstance(v, int) and not isinstance(v, bool) for v in box)):
        raise TestsetError(400, "`box` MUST be [left, top, right, bottom] in integer "
                                "pixels, or null")

    def change(row):
        if box is None:
            return dict.fromkeys(BOX_COLUMNS)
        db_path = conn.execute("PRAGMA database_list").fetchone()[2]
        path = os.path.join(imagestore.folder_of(db_path, row["folder"]),
                            "%s.%s" % (row["sha256"], row["extension"]))
        try:
            size = oriented_size(path)
        except OSError as exc:
            raise TestsetError(409, "cannot read the size of the photo: %s" % exc)
        good = check_box(box, size)
        if good is None:
            raise TestsetError(400, "the box %s is not inside the photo of %d x %d pixels"
                               % (box, size[0], size[1]))
        return dict(zip(BOX_COLUMNS, good))

    return _write_photo(conn, set_name, place, file_name, ("box",), change)


def free_name(conn, set_name, place, name, tag="moved"):
    """Return a file name that the place of the set does not hold: `name`, else
    `<stem>_<tag><N><ext>`, as `free_name` of the old tool."""
    def taken(candidate):
        return conn.execute("SELECT 1 FROM test_photo WHERE set_name = ? AND place = ? AND "
                            "file_name = ?", (set_name, place, candidate)).fetchone()
    if not taken(name):
        return name
    stem, ext = os.path.splitext(name)
    number = 2
    while taken("%s_%s%d%s" % (stem, tag, number, ext)):
        number += 1
    return "%s_%s%d%s" % (stem, tag, number, ext)


def move_photo(conn, set_name, place, file_name, to):
    """Move one photo to the place `to`: a wine slug of the page, `NULL_SLUG`, or
    `DRAWER_SLUG`.

    The label becomes NULL and `moved_from` gets the old place. A file name that the
    target holds gets the suffix `_moved<N>`. The bytes of the photo do not move: the
    image store keeps one file for each SHA-256."""
    _check_set(conn, set_name)
    _check_place(place, file_name)
    if not isinstance(to, str) or not to:
        raise TestsetError(400, "the request holds no `to`")
    if to == place:
        raise TestsetError(400, "the photo is already in the place %s" % to)
    if not _known_slug(conn, set_name, to):
        raise TestsetError(404, "no wine with the slug %s" % to)
    found = photo_rows(conn, set_name, place, file_name)
    if not found:
        raise TestsetError(404, "the set %s has no photo %s/%s" % (set_name, place, file_name))
    row = found[0]
    name = free_name(conn, set_name, to, file_name)
    extra = json.loads(row["extra"]) if row["extra"] else {}
    for key in ("label", "moved_from", "ts"):
        extra.pop(key, None)
    now = now_local()
    row.update(place=to, file_name=name, label=None, moved_from=place,
               extra=_extra_text(extra), ts=now)
    conn.execute("UPDATE test_photo SET place = ?, file_name = ?, label = NULL, "
                 "moved_from = ?, extra = ?, ts = ? WHERE set_name = ? AND place = ? AND "
                 "file_name = ?", (to, name, place, row["extra"], now, set_name, place,
                                   file_name))
    _edited(conn, set_name, now)
    return {"ok": True, "set": set_name, "from": place, "to": to, "file": file_name,
            "photo": dict(photo_view(row), place=to), "counts": counts(conn, set_name)}


def _known_slug(conn, set_name, slug):
    """Tell whether `slug` is a row of the page: a wine of the catalogue, a place of the
    set, the NULL wine, or the Drawer."""
    return (slug in (NULL_SLUG, DRAWER_SLUG)
            or conn.execute("SELECT 1 FROM wine_catalog WHERE wine_slug = ?",
                            (slug,)).fetchone() is not None
            or conn.execute("SELECT 1 FROM test_photo WHERE set_name = ? AND place = ? "
                            "LIMIT 1", (set_name, slug)).fetchone() is not None)


def _check_slug(conn, set_name, slug):
    _check_set(conn, set_name)
    if not isinstance(slug, str) or not slug:
        raise TestsetError(400, "the request holds no `slug`")
    if not _known_slug(conn, set_name, slug):
        raise TestsetError(404, "no wine with the slug %s" % slug)


def set_wine_note(conn, set_name, slug, text):
    """Set the note of a whole wine in one set. An empty text removes it."""
    _check_slug(conn, set_name, slug)
    comment = clean_note(text, "the note")
    row = conn.execute("SELECT extra FROM test_wine_note WHERE set_name = ? AND "
                       "wine_slug = ?", (set_name, slug)).fetchone()
    extra = json.loads(row[0]) if row and row[0] else {}
    extra.pop("comment", None)
    extra.pop("ts", None)
    now = now_local()
    if comment is None and not extra:
        conn.execute("DELETE FROM test_wine_note WHERE set_name = ? AND wine_slug = ?",
                     (set_name, slug))
    else:
        conn.execute("INSERT INTO test_wine_note (set_name, wine_slug, comment, ts, extra) "
                     "VALUES (?, ?, ?, ?, ?) ON CONFLICT (set_name, wine_slug) DO UPDATE "
                     "SET comment = excluded.comment, ts = excluded.ts, extra = excluded.extra",
                     (set_name, slug, comment, now, _extra_text(extra)))
    _edited(conn, set_name, now)
    return {"ok": True, "set": set_name, "slug": slug, "note": comment or "",
            "counts": counts(conn, set_name)}


def set_excluded(conn, set_name, slug, excluded, reason):
    """Exclude one slug of one set from the benchmark, or include it again. An exclusion
    needs a reason of at most `REASON_MAX` characters."""
    _check_slug(conn, set_name, slug)
    if not isinstance(excluded, bool):
        raise TestsetError(400, "`excluded` MUST be true or false")
    now = now_local()
    entry = None
    if excluded:
        text = reason.strip() if isinstance(reason, str) else ""
        if not text:
            raise TestsetError(400, "a reason is needed to exclude a slug")
        if len(text) > REASON_MAX:
            raise TestsetError(400, "the reason is longer than %d characters" % REASON_MAX)
        conn.execute("INSERT INTO test_excluded (set_name, wine_slug, reason, ts) "
                     "VALUES (?, ?, ?, ?) ON CONFLICT (set_name, wine_slug) DO UPDATE "
                     "SET reason = excluded.reason, ts = excluded.ts",
                     (set_name, slug, text, now))
        entry = {"reason": text, "ts": now}
    else:
        conn.execute("DELETE FROM test_excluded WHERE set_name = ? AND wine_slug = ?",
                     (set_name, slug))
    _edited(conn, set_name, now)
    return {"ok": True, "set": set_name, "slug": slug, "excluded": excluded,
            "entry": entry, "counts": counts(conn, set_name)}


# The limits of an upload: the limits of `patches.py` and of the old tool.
UPLOAD_MAX = 20 * 1024 * 1024
UPLOAD_PIXELS = 100_000_000
# The Pillow format of an upload -> the extension of the stored file. These are the
# extensions that `import_testset.py` reads from a set directory.
UPLOAD_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp", "GIF": "gif", "BMP": "bmp"}
# The folder of the image store for a test photo: `import_testset.FOLDER`.
UPLOAD_FOLDER = "testset"
UPLOAD_STEM_MAX = 120
UPLOAD_STEM = "upload"


def read_upload(data):
    """Return (extension, width, height) of the bytes of an upload. Pillow reads the type
    from the bytes, not from the file name. Raise `TestsetError`."""
    if not data:
        raise TestsetError(400, "the body holds no image")
    if len(data) > UPLOAD_MAX:
        raise TestsetError(413, "the image is larger than %d bytes" % UPLOAD_MAX)
    try:
        with Image.open(io.BytesIO(data)) as image:
            image_format, size = image.format, image.size
            if size[0] * size[1] > UPLOAD_PIXELS:
                raise TestsetError(413, "the image has %d x %d pixels; the limit is %d "
                                        "pixels" % (size[0], size[1], UPLOAD_PIXELS))
            image.load()
    except (OSError, ValueError, SyntaxError) as exc:
        raise TestsetError(400, "Pillow cannot read the image: %s" % exc)
    if image_format not in UPLOAD_FORMATS:
        raise TestsetError(400, "the image is %s; a photo MUST be JPEG, PNG, WebP, GIF, or "
                                "BMP" % image_format)
    return (UPLOAD_FORMATS[image_format],) + size


def upload_name(name, extension):
    """Return the file name of a new image: the stem of `name` with no path part, and
    `extension`. A character other than a letter, a digit, or ` ._()-` becomes `_`, as
    `store_inbox_image` of the old tool does."""
    leaf = os.path.basename((name or "").replace("\\", "/"))
    stem = "".join(ch if ch.isalnum() or ch in " ._()-" else "_"
                   for ch in os.path.splitext(leaf)[0]).strip(" .")
    stem = stem[:UPLOAD_STEM_MAX].rstrip(" .") or UPLOAD_STEM
    return "%s.%s" % (stem, extension)


def upload_photo(conn, set_name, place, data, name):
    """Add the image `data` to the place `place` of the set: a wine slug of the page,
    `NULL_SLUG`, or `DRAWER_SLUG`. `name` is the file name that the browser sends.

    An image that the place holds already is refused with HTTP 409. An image that another
    place of the set holds gets the file name of that photo. A file name that the place
    holds for another image gets the suffix `_upload<N>`. The bytes go to the image store
    unless the table `image` holds them already."""
    _check_set(conn, set_name)
    if not isinstance(place, str) or not place:
        raise TestsetError(400, "the request holds no `place`")
    if not _known_slug(conn, set_name, place):
        raise TestsetError(404, "no wine with the slug %s" % place)
    extension, width, height = read_upload(data)
    digest = hashlib.sha256(data).hexdigest()
    same = conn.execute("SELECT place, file_name FROM test_photo WHERE set_name = ? AND "
                        "sha256 = ? ORDER BY place, file_name", (set_name, digest)).fetchall()
    for other_place, other_file in same:
        if other_place == place:
            raise TestsetError(409, "the place %s holds this image already as %s"
                               % (place, other_file))
    file_name = free_name(conn, set_name, place,
                          same[0][1] if same else upload_name(name, extension), "upload")
    if conn.execute("SELECT 1 FROM image WHERE sha256 = ?", (digest,)).fetchone() is None:
        db_path = conn.execute("PRAGMA database_list").fetchone()[2]
        folder = imagestore.folder_of(db_path, UPLOAD_FOLDER)
        os.makedirs(folder, exist_ok=True)
        try:
            imagestore.store_bytes(data, os.path.join(folder, "%s.%s" % (digest, extension)),
                                   digest)
        except imagestore.StoreError as exc:
            raise TestsetError(409, str(exc))
        conn.execute("INSERT INTO image (sha256, folder, extension, width, height) "
                     "VALUES (?, ?, ?, ?, ?)", (digest, UPLOAD_FOLDER, extension, width, height))
    conn.execute("INSERT INTO test_photo (set_name, place, file_name, sha256) "
                 "VALUES (?, ?, ?, ?)", (set_name, place, file_name, digest))
    _edited(conn, set_name, now_local())
    row = photo_rows(conn, set_name, place, file_name)[0]
    return {"ok": True, "set": set_name, "place": place, "file": file_name,
            "photo": dict(photo_view(row), place=place), "counts": counts(conn, set_name)}
