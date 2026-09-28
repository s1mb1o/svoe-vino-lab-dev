"""The test sets of the lab database: the reads and the writes of the Testset page.

The tables are `test_set`, `test_photo`, `test_photo_comment`, and `test_variant`. The
database is the source of the labels: the page writes here, and `export_testset.py` writes
the JSON files of a set from the rows. The owner chose this on 2026-09-25T12:40:00+0300.
Read `docs/plans/24_testset-page.md`.

One label entry of `review-labels.json` is one row of `test_photo`. `ENTRY_FIELDS` names
the column of each JSON field and the test of a value that the column keeps exactly. A
field with another value, and a field that no column names, goes into the JSON object
`extra`. So the export gives the same entry back.

One photo MAY have more than one comment: the rows of `test_photo_comment`, in time order.
The JSON field `comments` of an entry holds them. The comments of a whole wine are the
rows of `wine_comment` (`comments.py`); they belong to no set. The owner chose this on
2026-09-26T18:08:34+0300 (plan 51). The exclusion of a slug went away with the same
answer.

The tags of a photo are the tags of its image: the rows of `image_tag`
(`image_tags.py`, plan 66). The key is the SHA-256, so each photo of each set that holds
the same bytes shows the same tags. The owner chose this on 2026-09-27T23:53:00+0300. A tag
write sets `test_set.edited_at` of the set of the request; `ts` of the entry does not
change.

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
import datetime
import hashlib
import io
import json
import math
import os
import re
import time

from PIL import Image

import comments
import image_tags
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
# The form of `ts`, as the old tool writes it: the local time with its offset.
TS_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
# The form of `created_at` of a comment: `comments.now_utc`.
UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
UTC_RE = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
# The keys of one comment in the JSON field `comments` of an entry.
COMMENT_KEYS = ("created_at", "source", "text")
# A wine note of the old tool that starts with the tag of a hunt agent came from a script
# (plan 51). The tags are those of the hunt of 2026-09-16.
AGENT_TAG_RE = re.compile(r"^(irec-\d|hunter-\d|cigar-r\d)")
# The text of the comment that keeps the reason of an old exclusion (plan 51).
EXCLUDED_PREFIX = "Excluded from the benchmark: "
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


class TestsetError(Exception):
    """A request of the Testset page is not valid. `code` is the HTTP status."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def now_local():
    """Return the present local time in the form of `ts`."""
    return time.strftime(TS_FORMAT)


def utc_of(ts):
    """Return the local time `ts` (the form of `TS_FORMAT`) as a UTC time in the form of
    `created_at`, or None when `ts` is not in that form."""
    if not isinstance(ts, str):
        return None
    try:
        moment = datetime.datetime.strptime(ts, TS_FORMAT)
    except ValueError:
        return None
    if moment.tzinfo is None:
        return None
    return moment.astimezone(datetime.timezone.utc).strftime(UTC_FORMAT)


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


def _comment_item(value):
    """Tell whether `value` is one comment of the JSON field `comments`."""
    return (isinstance(value, dict) and set(value) == set(COMMENT_KEYS)
            and isinstance(value["created_at"], str) and bool(UTC_RE.match(value["created_at"]))
            and value["source"] in comments.SOURCES and _storable(value["text"]))


def entry_comments(entry, now=None):
    """Return (the entry with no comment field, the comments of the entry).

    A comment is `{"created_at", "source", "text"}`. The field `comments` gives its
    comments when each item is valid; else the field stays in the entry and so goes to
    `extra`. The old field `comment` of the old tool gives one comment: its time is `ts`
    of the entry in UTC, else `now`; its source is `script` when the entry has `by` (an
    agent proposal), else `user`. The comments are in time order."""
    rest, found = dict(entry), []
    items = rest.get("comments")
    if isinstance(items, list) and items and all(_comment_item(item) for item in items):
        found += [{key: item[key] for key in COMMENT_KEYS} for item in items]
        del rest["comments"]
    if _storable(rest.get("comment")):
        text = rest.pop("comment")
        found.append({"created_at": utc_of(rest.get("ts")) or now or comments.now_utc(),
                      "source": "script" if _text(rest.get("by")) else "user", "text": text})
    found.sort(key=lambda item: item["created_at"])
    return rest, found


def _storable(text):
    """Tell whether `text` fits the column `text` of a comment table as it is."""
    return _comment(text) and not any(0xD800 <= ord(char) <= 0xDFFF for char in text)


def note_source(text):
    """Return the source of a wine note of the old tool: `script` for the tag of a hunt
    agent at the start, else `user` (plan 51)."""
    return "script" if AGENT_TAG_RE.match(text) else "user"


def wine_note_comment(note, now):
    """Return the wine comment of one note of the map `wines` of the old tool, or None
    when the note holds no text. The rules are those of the schema file of plan 51."""
    text = note.get("comment") if isinstance(note, dict) else None
    if not _storable(text):
        return None
    return {"created_at": utc_of(note.get("ts")) or now, "source": note_source(text),
            "text": text}


def exclusion_comment(record, now):
    """Return the wine comment of one entry of `excluded-slugs.json` of the old tool, or
    None when it holds no reason. An entry is `{reason, ts}` or the short form `reason`."""
    if isinstance(record, str):
        reason, ts = record, None
    elif isinstance(record, dict):
        reason, ts = record.get("reason"), record.get("ts")
    else:
        return None
    # `strip(" ")` is `trim` of SQLite, as the schema file uses it.
    reason = reason.strip(" ") if isinstance(reason, str) else ""
    if not reason or not _storable(EXCLUDED_PREFIX + reason):
        return None
    return {"created_at": utc_of(ts) or now, "source": "user", "text": EXCLUDED_PREFIX + reason}


def comment_view(comment_id, created_at, source, text):
    """Return one comment of a photo as the page and the export show it."""
    return {"id": comment_id, "created_at": created_at, "source": source, "text": text}


def photo_comments(conn, set_name, place=None, file_name=None):
    """Return (place, file name) -> the comments of each photo of one set, or of one
    photo, in time order. A photo with no comment has no key."""
    sql = ("SELECT place, file_name, id, created_at, source, text FROM test_photo_comment "
           "WHERE set_name = ?")
    args = [set_name]
    if place is not None:
        sql += " AND place = ? AND file_name = ?"
        args += [place, file_name]
    out = {}
    for row_place, row_file, *row in conn.execute(sql + " ORDER BY created_at, id", args):
        out.setdefault((row_place, row_file), []).append(comment_view(*row))
    return out


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


def photo_view(row, notes=(), tags=()):
    """Return one photo for the page: its file, its image, its JSON entry, its comments
    (`notes`, the list of `photo_comments`), and the tags of its image (`tags`)."""
    return {"file": row["file_name"], "sha256": row["sha256"],
            "url": "/images/%s/%s.%s" % (row["folder"], row["sha256"], row["extension"]),
            "width": row["width"], "height": row["height"],
            "conf": photo_conf(row["file_name"]), "entry": entry_of(row),
            "comments": list(notes), "tags": list(tags)}


def image_tags_of(conn, digest):
    """Return the list of the tags of one image."""
    return image_tags.tags(conn, (digest,)).get(digest, [])


def counts(conn, set_name):
    """Return the counts of one set, with the keys of `count_state` of the old tool, and
    `photos` and `boxes`. `commented` counts the photos with a comment."""
    (photos, positive, negative, unusable, variant, reassigned, copied, deleting,
     proposed, no_match, no_match_pending, boxes, drawer) = conn.execute(
        "SELECT count(*), "
        "count(*) FILTER (WHERE label = 'positive'), "
        "count(*) FILTER (WHERE label = 'negative'), "
        "count(*) FILTER (WHERE label = 'unusable'), "
        "count(*) FILTER (WHERE label = 'variant'), "
        "count(*) FILTER (WHERE reassign_to IS NOT NULL), "
        "count(*) FILTER (WHERE json_extract(extra, '$.copy_to') IS NOT NULL), "
        "count(*) FILTER (WHERE marked_delete = 1), "
        "count(*) FILTER (WHERE proposed IS NOT NULL AND label IS NULL), "
        "count(*) FILTER (WHERE place = ?), "
        "count(*) FILTER (WHERE reassign_to = ?), "
        "count(*) FILTER (WHERE box_left IS NOT NULL), "
        "count(*) FILTER (WHERE place = ?) "
        "FROM test_photo WHERE set_name = ?",
        (NULL_SLUG, NULL_SLUG, DRAWER_SLUG, set_name)).fetchone()
    commented = conn.execute("SELECT count(*) FROM (SELECT DISTINCT place, file_name FROM "
                             "test_photo_comment WHERE set_name = ?)", (set_name,)).fetchone()[0]
    return {"positive": positive, "negative": negative, "unusable": unusable,
            "variant": variant, "labelled": positive + negative + unusable + variant,
            "reassigned": reassigned, "copied": copied, "deleting": deleting,
            "commented": commented, "proposed": proposed,
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
    slug order; the page sorts them. `comments` of a row are the comments of the wine
    (`wine_comment`, plan 51); a row that `wine_catalog` does not hold has none.
    `tags` of a photo are the tags of its image, and `tag_names` lists each tag of
    `image_tag` with its number of images (plan 66).
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
    notes = photo_comments(conn, set_name)
    photos = photo_rows(conn, set_name)
    tag_map = image_tags.tags(conn, {row["sha256"] for row in photos})
    by_place = {}
    for row in sorted(photos, key=lambda r: (r["place"], photo_rank(r["file_name"]))):
        by_place.setdefault(row["place"], []).append(
            photo_view(row, notes.get((row["place"], row["file_name"]), ()),
                       tag_map.get(row["sha256"], ())))
    cards = card_images(conn)
    wine_notes = comments.comments(conn)
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
        row.update(group=group_of.get(row["slug"]), comments=wine_notes.get(row["slug"], []))
    edited_at, source_dir = conn.execute(
        "SELECT edited_at, source_dir FROM test_set WHERE set_name = ?", (set_name,)).fetchone()
    return {"sets": _sets(conn), "set": set_name, "edited_at": edited_at,
            "source_dir": source_dir, "rows": rows, "counts": counts(conn, set_name),
            "groups": variant, "labels": list(LABELS), "null_labels": list(NULL_LABELS),
            "tag_names": image_tags.names(conn)}


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
    row = _photo_row(conn, set_name, place, file_name)
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
    return _photo_answer(conn, set_name, place, file_name, row)


def _photo_answer(conn, set_name, place, file_name, row, **fields):
    """Return the answer of a write to one photo: the photo with its comments and its
    tags, and the counts of the set."""
    notes = photo_comments(conn, set_name, place, file_name).get((place, file_name), ())
    answer = {"ok": True, "set": set_name, "place": place, "file": file_name}
    answer.update(fields)
    answer.update(photo=photo_view(row, notes, image_tags_of(conn, row["sha256"])),
                  counts=counts(conn, set_name))
    return answer


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


def _photo_row(conn, set_name, place, file_name):
    """Return the row of one photo, or raise `TestsetError`."""
    _check_set(conn, set_name)
    _check_place(place, file_name)
    found = photo_rows(conn, set_name, place, file_name)
    if not found:
        raise TestsetError(404, "the set %s has no photo %s/%s" % (set_name, place, file_name))
    return found[0]


def add_photo_comment(conn, set_name, place, file_name, text, source=None):
    """Add one comment to one photo. `source` is `user` (the page sends none) or
    `script`. The write sets `test_set.edited_at`; `ts` of the entry does not change,
    because a comment has its own time."""
    row = _photo_row(conn, set_name, place, file_name)
    source = "user" if source is None else source
    try:
        comments.check_source(source)
        clean = comments.clean_text(text)
    except comments.CommentError as exc:
        raise TestsetError(400, str(exc))
    created_at = comments.now_utc()
    cursor = conn.execute("INSERT INTO test_photo_comment (set_name, place, file_name, "
                          "created_at, source, text) VALUES (?, ?, ?, ?, ?, ?)",
                          (set_name, place, file_name, created_at, source, clean))
    _edited(conn, set_name, now_local())
    return _photo_answer(conn, set_name, place, file_name, row,
                         comment=comment_view(cursor.lastrowid, created_at, source, clean))


def remove_photo_comment(conn, set_name, place, file_name, comment_id):
    """Remove one comment of one photo. `comment_id` is the `id` of the comment."""
    row = _photo_row(conn, set_name, place, file_name)
    if isinstance(comment_id, str) and comment_id.isascii() and comment_id.isdigit():
        comment_id = int(comment_id)
    if not isinstance(comment_id, int) or isinstance(comment_id, bool):
        raise TestsetError(400, "the request holds no valid comment `id`")
    removed = conn.execute("DELETE FROM test_photo_comment WHERE id = ? AND set_name = ? AND "
                           "place = ? AND file_name = ?",
                           (comment_id, set_name, place, file_name)).rowcount
    if not removed:
        raise TestsetError(404, "the photo %s/%s has no comment %d"
                           % (place, file_name, comment_id))
    _edited(conn, set_name, now_local())
    return _photo_answer(conn, set_name, place, file_name, row, removed=comment_id)


def _tag_answer(conn, set_name, place, file_name, row, **fields):
    """Return the answer of a tag write: the photo, the SHA-256 and the tags of its
    image, and `tag_names`. The page draws again each photo of the image."""
    _edited(conn, set_name, now_local())
    return _photo_answer(conn, set_name, place, file_name, row, sha256=row["sha256"],
                         tags=image_tags_of(conn, row["sha256"]),
                         tag_names=image_tags.names(conn), **fields)


def add_photo_tag(conn, set_name, place, file_name, tag):
    """Add one tag to the image of one photo (plan 66). Each photo that holds the same
    bytes gets the tag. A tag that the image has gives HTTP 409."""
    row = _photo_row(conn, set_name, place, file_name)
    try:
        added = image_tags.add(conn, row["sha256"], tag)
    except image_tags.TagError as exc:
        raise TestsetError(400, str(exc))
    except image_tags.DuplicateError as exc:
        raise TestsetError(409, str(exc))
    return _tag_answer(conn, set_name, place, file_name, row, added=added)


def remove_photo_tag(conn, set_name, place, file_name, tag):
    """Remove one tag of the image of one photo (plan 66). A tag that the image does not
    have gives HTTP 404."""
    row = _photo_row(conn, set_name, place, file_name)
    try:
        clean = image_tags.normal(tag)
    except image_tags.TagError as exc:
        raise TestsetError(400, str(exc))
    if not image_tags.remove(conn, row["sha256"], clean):
        raise TestsetError(404, "the image of %s/%s has no tag %s" % (place, file_name, clean))
    return _tag_answer(conn, set_name, place, file_name, row, removed=clean)


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
    # The comments of the photo follow it. With `PRAGMA foreign_keys = ON`, the key of
    # `test_photo_comment` (`ON UPDATE CASCADE`) moved them already; this update covers a
    # connection with the pragma off.
    conn.execute("UPDATE test_photo_comment SET place = ?, file_name = ? WHERE set_name = ? "
                 "AND place = ? AND file_name = ?", (to, name, set_name, place, file_name))
    _edited(conn, set_name, now)
    notes = photo_comments(conn, set_name, to, name).get((to, name), ())
    return {"ok": True, "set": set_name, "from": place, "to": to, "file": file_name,
            "photo": dict(photo_view(row, notes, image_tags_of(conn, row["sha256"])), place=to),
            "counts": counts(conn, set_name)}


def _known_slug(conn, set_name, slug):
    """Tell whether `slug` is a row of the page: a wine of the catalogue, a place of the
    set, the NULL wine, or the Drawer."""
    return (slug in (NULL_SLUG, DRAWER_SLUG)
            or conn.execute("SELECT 1 FROM wine_catalog WHERE wine_slug = ?",
                            (slug,)).fetchone() is not None
            or conn.execute("SELECT 1 FROM test_photo WHERE set_name = ? AND place = ? "
                            "LIMIT 1", (set_name, slug)).fetchone() is not None)


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
    # An image that the database holds already MAY have tags (plan 66).
    return {"ok": True, "set": set_name, "place": place, "file": file_name,
            "photo": dict(photo_view(row, (), image_tags_of(conn, digest)), place=place),
            "counts": counts(conn, set_name)}


# A set that the page makes (plan 57). The name rule is the `CHECK` of
# `test_set.set_name` (schema 016). `source_dir` MUST NOT be empty; no directory holds such
# a set, so the column names the page.
SET_NAME_RE = re.compile(r"[0-9a-z_-]+")
NEW_SOURCE = "the page /testset"


def create_set(conn, name):
    """Make the empty test set `name` in the caller's transaction (plan 57). Return
    {"ok": True, "set": name}. A bad name gives HTTP 400, a present name HTTP 409. The set
    gets `edited_at`, so `import_testset.py` does not overwrite it without `--force`."""
    if not isinstance(name, str) or not SET_NAME_RE.fullmatch(name):
        raise TestsetError(400, "a set name MUST hold 0-9, a-z, _ and - alone")
    if conn.execute("SELECT 1 FROM test_set WHERE set_name = ?", (name,)).fetchone():
        raise TestsetError(409, "the test set %s exists already" % name)
    conn.execute("INSERT INTO test_set (set_name, source_dir, edited_at) VALUES (?, ?, ?)",
                 (name, NEW_SOURCE, now_local()))
    return {"ok": True, "set": name}
