#!/usr/bin/env python3
"""Manual labelling tool for the `my/` photo set.

The tool starts a local HTTP server and opens a browser.
The browser shows one table row per wine.
Column 1 holds the catalogue bottle photo of the wine from the strapi dump.
The next columns hold the candidate photos in `my/<slug>/`.

Each candidate photo gets one of three labels:

- `positive`: the photo shows the wine of this slug.
- `negative`: the photo shows a different wine. The photo stays in the set as a
  negative sample of this slug. A negative sample is a wanted result, not waste.
- `unusable`: the photo is not usable at all. It shows no bottle, it cannot be
  read, or it is a duplicate. The photo does not belong in the set.

A photo with no label is not reviewed yet.
Every click is written to `review-labels.json` at once.
The file is read again at the next start.

`config.yaml` holds one entry per dataset under the key `dataset`. `--dataset NAME`
chooses one. Without the option the tool uses the dataset named `default`.

Run:
    python3 scripts/review_server.py
    python3 scripts/review_server.py --port 8154 --no-browser
    python3 scripts/review_server.py --dataset second
"""
import argparse
import base64
import hashlib
import html
import io
import ipaddress
import json
import mimetypes
import os
import re
import shutil
import socket
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Every path comes from `config.yaml`. Read the file for the meaning of each key.
# `bind_paths` sets them all. It runs here, and it runs again when `--dataset`
# names another dataset, because these names are read all over this file.
MY = TRASH = LABEL_FILE = CATALOG = PATCH_DIR = BOTTLE_CROPPED_DIR = None
BOTTLE_LABEL_DIR = BOTTLE_LABEL_BOX_DIR = None
VARIANTS_FILE = MANUAL_GROUPS_FILE = EXCLUDED_FILE = RUNS_DIR = None


def bind_paths():
    """Take every path of this file from the dataset that `common` holds now."""
    global MY, TRASH, LABEL_FILE, CATALOG, PATCH_DIR, BOTTLE_CROPPED_DIR
    global BOTTLE_LABEL_DIR, BOTTLE_LABEL_BOX_DIR
    global VARIANTS_FILE, MANUAL_GROUPS_FILE, EXCLUDED_FILE, RUNS_DIR
    MY = common.PHOTO_DIR
    # A deleted photo is moved here, not unlinked. The reviewer can get it back.
    TRASH = common.TRASH_DIR
    LABEL_FILE = common.LABEL_FILE
    CATALOG = common.CATALOG_FILE
    # Corrected catalogue photos. Every dataset reads the same directory.
    PATCH_DIR = common.PATCH_DIR
    # The catalogue photos without their empty border. Every dataset reads the
    # same directory. An unset key shows the photos with their border.
    BOTTLE_CROPPED_DIR = common.BOTTLE_CROPPED_DIR
    # The label crops of the catalogue photos. Every dataset reads the same two
    # directories. An unset key takes the selector out of the page.
    BOTTLE_LABEL_DIR = common.BOTTLE_LABEL_DIR
    BOTTLE_LABEL_BOX_DIR = common.BOTTLE_LABEL_BOX_DIR
    VARIANTS_FILE = common.VARIANT_GROUPS_FILE
    MANUAL_GROUPS_FILE = common.MANUAL_GROUPS_FILE
    EXCLUDED_FILE = common.EXCLUDED_SLUGS_FILE
    RUNS_DIR = common.RUNS_DIR


bind_paths()
DEFAULT_PORT = 8154

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
LABELS = ("positive", "negative", "unusable", "variant")
# The virtual wine that collects the photos that match NO card of the catalogue.
# It is a reserved slug, not a card. `<photo_dir>/__null__/` holds its photos, and
# the table draws one row for it with a placeholder in place of a bottle photo.
# A photo that lies there carries one statement: no card of the catalogue shows
# this wine. The place IS the statement; no label is needed for it.
# `scripts/match_run.py` reads such a photo as a rejection case.
NULL_SLUG = "__null__"
NULL_NAME = "NULL \u2014 no match in the catalogue"
# The labels that a photo of the NULL wine MAY carry. `positive` confirms the
# statement of the place. `negative` and `variant` judge a photo against a wine,
# and NULL is not a wine.
NULL_LABELS = ("positive", "unusable")
COMMENT_MAX = 4000
# The OpenAPI document of this server. `/openapi.yaml`, `/openapi.json`, and
# `/docs` read it. It is written by hand; it is not generated from the code.
SPEC_FILE = os.path.join(ROOT, "docs", "openapi.yaml")
# The version of Swagger UI that `/docs` loads from the CDN. It is pinned, so
# a new release of Swagger UI cannot change the page without a commit here.
SWAGGER_UI = "5.33.0"
EXCLUDE_REASON_MAX = 1000
NAME_RE = re.compile(r"^(\d+)_conf(\d+)\.")
RANK_RE = re.compile(r"^(\d+)_")
UPLOAD_MAX = 20 * 1024 * 1024
FETCH_TIMEOUT = 25
# The same string that the pipeline uses. A plain Python agent is refused by many
# picture hosts.
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
UPLOAD_TYPES = {
    "image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
    "image/gif": ".gif", "image/bmp": ".bmp",
}

_lock = threading.Lock()
_state = {"labels": {}, "wines": {}}
_rows = []
# slug -> the path of a corrected catalogue photo. `common.PATCH_DIR` holds the
# files. A patch REPLACES the catalogue photo of that slug: `/img/bottle` serves
# it, and every view marks the image `patched`. `load_patches` fills this map at
# start and at every `/api/reload`, so a new patch file needs no restart.
_patches = {}
# slug -> the path of the cropped catalogue photo. `common.BOTTLE_CROPPED_DIR`
# holds the files. A crop is the patch or the catalogue photo with its empty
# border cut away, so it holds the same picture. `bottle_path` answers the crop
# first. The mark `patched` does not change: it still states that the picture
# comes from a patch. `load_crops` fills this map at start and at every
# `/api/reload`.
_crops = {}
# slug -> the path of a label crop. `common.BOTTLE_LABEL_DIR` and
# `common.BOTTLE_LABEL_BOX_DIR` hold the files. A label crop does NOT replace the
# catalogue photo, unlike a patch: it is the label of the SAME photo, cut out
# with SAM3. `/img/bottle?slug=<slug>&kind=label` serves it, and the page holds a
# selector for the three kinds. A wine with no crop keeps its package picture.
# `load_label_crops` fills both maps at start and at every `/api/reload`.
_labels = {}
_label_boxes = {}
# slug -> {"reason": str, "ts": str}. The photos of such a slug are out of the
# benchmark. `excluded-slugs.json` holds the map.
_excluded = {}


# ---------------------------------------------------------------- data loading


def load_catalog():
    """Return slug -> catalogue record. An absent file gives an empty map."""
    out = {}
    if not os.path.exists(CATALOG):
        print(f"warning: catalogue not found: {CATALOG}", file=sys.stderr)
        return out
    with open(CATALOG, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            out[rec["slug"]] = rec
    return out


def load_patches():
    """Read `patch_dir` again and answer slug -> corrected catalogue photo.

    A broken `patch_dir` MUST NOT stop the tool, because the patches are a
    correction of the catalogue and not the work of the reviewer. The function
    prints the error and answers an empty map.
    """
    try:
        return common.load_patches()
    except common.ConfigError as exc:
        print("warning: %s" % exc, file=sys.stderr)
        return {}


def load_crops():
    """Read `bottle_cropped_dir` again and answer slug -> cropped catalogue photo.

    A broken directory MUST NOT stop the tool, for the reason of `load_patches`.
    The function prints the error and answers an empty map, so the page shows
    the photos with their border.
    """
    try:
        return common.load_cropped_bottles()
    except common.ConfigError as exc:
        print("warning: %s" % exc, file=sys.stderr)
        return {}


def bottle_path(slug, catalog):
    """Return the catalogue bottle photo of `slug`, or None.

    `common.catalogue_picture` states the rule: the crop, then the patch, then
    the photo of the catalogue record. A patch is a correction of that record,
    so no view may show the photo it corrects.
    """
    return common.catalogue_picture(slug, catalog.get(slug), _crops, _patches)


# The three kinds of picture that `/img/bottle` serves. `package` is the
# catalogue photo, or the patch of that photo. `label` is the label cut out of
# that picture, as RGBA with the mask in the alpha channel. `labelbox` is the
# bounding box of the label alone, as RGB.
IMAGE_KINDS = ("package", "label", "labelbox")


def load_label_crops():
    """Read both label directories again and answer the two maps.

    A broken directory MUST NOT stop the tool. The label crops are a view of the
    catalogue photo and not the work of the reviewer. The function prints the
    error and answers an empty map for that directory.
    """
    out = []
    for path in (BOTTLE_LABEL_DIR, BOTTLE_LABEL_BOX_DIR):
        try:
            out.append(common.load_bottle_labels(path))
        except common.ConfigError as exc:
            print("warning: %s" % exc, file=sys.stderr)
            out.append({})
    return out[0], out[1]


def label_path(slug, kind):
    """Return the label crop of `slug` for `kind`, or None for another kind."""
    if kind == "label":
        return _labels.get(slug)
    if kind == "labelbox":
        return _label_boxes.get(slug)
    return None


def picture_path(slug, catalog, kind="package"):
    """Return the file that the page shows for `slug` and `kind`.

    A wine with no crop of that kind falls back to its package picture, so the
    table never holds a hole. The row states `has_label` and `has_label_box`, so
    the page can mark such a picture.
    """
    return label_path(slug, kind) or bottle_path(slug, catalog)


MANUAL_GROUPS_NOTE = (
    "Pairs of wine slugs that a reviewer joined by hand in the review tool. "
    "`scripts/08_variants.py` never writes this file, so a new run of that script "
    "keeps these pairs. `load_variants()` reads this file together with the "
    "generated groups of `variant-groups.json` and joins the two sets. A pair "
    "adds its two slugs to one group."
)


def load_manual_pairs():
    """Return the pairs that a reviewer joined by hand, as a list of records.

    A missing file gives an empty list. A broken file gives an empty list and a
    warning, so the tool still starts.
    """
    if not os.path.exists(MANUAL_GROUPS_FILE):
        return []
    try:
        with open(MANUAL_GROUPS_FILE, encoding="utf-8") as f:
            blob = json.load(f)
    except (OSError, ValueError) as exc:
        print(f"warning: cannot read {MANUAL_GROUPS_FILE}: {exc}", file=sys.stderr)
        return []
    out = []
    for p in blob.get("pairs") or []:
        a, b = (p.get("a") or "").strip(), (p.get("b") or "").strip()
        if a and b and a != b:
            out.append({"a": a, "b": b, "ts": p.get("ts") or ""})
    return out


def save_manual_pairs(pairs):
    """Write the file of the manual pairs. The write is atomic."""
    payload = {
        "version": 1,
        "updated": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "note": MANUAL_GROUPS_NOTE,
        "count": len(pairs),
        "pairs": pairs,
    }
    tmp = MANUAL_GROUPS_FILE + ".tmp"
    os.makedirs(os.path.dirname(MANUAL_GROUPS_FILE) or ".", exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, MANUAL_GROUPS_FILE)


def load_variants():
    """Return slug -> group id, and group id -> the record of the group.

    Two sources join here. `scripts/08_variants.py` writes the groups of
    `variant-groups.json`. The review tool writes the pairs of
    `manual-groups.json`. A group is a connected component over both sources, so
    a manual pair that names a slug of a generated group adds the other slug to
    that group.

    A component that holds a generated group keeps the id of that group. A
    component built from manual pairs alone gets an id `m<NNN>`, numbered by the
    first slug of the component, so the id does not move between two starts.

    A missing `variant-groups.json` is not an error. The tool then shows the
    manual groups alone, and every other wine as a row of its own.
    """
    raw_groups = []
    if os.path.exists(VARIANTS_FILE):
        try:
            with open(VARIANTS_FILE, encoding="utf-8") as f:
                blob = json.load(f)
        except (OSError, ValueError) as exc:
            print(f"warning: cannot read {VARIANTS_FILE}: {exc}", file=sys.stderr)
            blob = {}
        for g in blob.get("groups", []):
            gid = g.get("id")
            members = g.get("slugs") or []
            if not gid or len(members) < 2:
                continue
            raw_groups.append((gid, list(members), g.get("producer", ""),
                               g.get("name", "")))
    else:
        print(f"note: no variant groups: {VARIANTS_FILE}", file=sys.stderr)

    pairs = load_manual_pairs()
    if not raw_groups and not pairs:
        return {}, {}

    # The order in which a slug is first seen. It fixes the order of the members
    # of a group and the number of a manual group.
    order = {}
    for _gid, members, _pr, _nm in raw_groups:
        for sl in members:
            order.setdefault(sl, len(order))
    for p in pairs:
        for sl in (p["a"], p["b"]):
            order.setdefault(sl, len(order))

    parent = {sl: sl for sl in order}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    for _gid, members, _pr, _nm in raw_groups:
        for sl in members[1:]:
            union(members[0], sl)
    for p in pairs:
        union(p["a"], p["b"])

    # The generated group whose id and labels the component keeps. Two generated
    # groups never land in one component through the tool, because `/api/group`
    # refuses that write. A hand-edited file can still do it, and then the first
    # generated group of the component gives the id.
    label = {}
    for gid, members, pr, nm in raw_groups:
        root = find(members[0])
        label.setdefault(root, (gid, pr, nm))

    buckets = {}
    for sl in sorted(order, key=order.get):
        buckets.setdefault(find(sl), []).append(sl)

    by_slug, groups = {}, {}
    n = 0
    for root in sorted(buckets, key=lambda r: order[buckets[r][0]]):
        members = buckets[root]
        if len(members) < 2:
            continue
        if root in label:
            gid, pr, nm = label[root]
        else:
            n += 1
            gid, pr, nm = "m%03d" % n, "", ""
        groups[gid] = {"id": gid, "slugs": members, "producer": pr, "name": nm}
        for sl in members:
            by_slug[sl] = gid
    return by_slug, groups


def scan_photos(slug):
    """Return the candidate photo file names of one wine, best rank first."""
    d = os.path.join(MY, slug)
    names = []
    for fn in os.listdir(d):
        if fn.startswith("."):
            continue
        if os.path.splitext(fn)[1].lower() not in IMAGE_EXT:
            continue
        names.append(fn)

    def key(fn):
        m = RANK_RE.match(fn)
        return (int(m.group(1)), fn) if m else (9999, fn)

    return sorted(names, key=key)


def scan_inbox():
    """Return the image files that lie directly in `my/`, not in a wine directory.

    Such a file belongs to no wine yet. The review page shows it in the sideboard.
    The reviewer drags it to the wine that it shows, and `apply` moves the file
    into the directory of that wine.
    """
    names = []
    for fn in sorted(os.listdir(MY)):
        if fn.startswith("."):
            continue
        if os.path.splitext(fn)[1].lower() not in IMAGE_EXT:
            continue
        if os.path.isdir(os.path.join(MY, fn)):
            continue
        names.append(fn)
    return names


def build_rows(catalog, group_of=None):
    """Build one row per directory in `my/`.

    The function does not test that the bottle photo file is present.
    The strapi `uploads` directory holds about 15,800 files on an external
    volume. One `stat` call there costs a large fraction of a second, so 811
    calls block the start for minutes. The browser requests each bottle photo
    only when the row scrolls into view, and `/img/bottle` answers 404 when the
    file is absent.
    """
    group_of = group_of or {}
    rows = []
    for slug in sorted(os.listdir(MY)):
        d = os.path.join(MY, slug)
        if slug.startswith(".") or not os.path.isdir(d):
            continue
        # The NULL wine is not a card of the catalogue. `null_row` builds it, and
        # it is built whether the directory is present or not.
        if slug == NULL_SLUG:
            continue
        rows.append(build_row(slug, catalog, group_of))
    rows.append(null_row())
    return rows


def build_row(slug, catalog, group_of=None):
    """Build the row of one directory of `my/`.

    `build_rows` uses it for every directory. The upload uses it for a wine that
    gets its first photo now, so the new row matches the rows of the first scan.
    """
    group_of = group_of or {}
    rec = catalog.get(slug) or {}
    bottle = bottle_path(slug, catalog)
    photos = []
    for fn in scan_photos(slug):
        m = NAME_RE.match(fn)
        photos.append(
            {
                "file": fn,
                "conf": int(m.group(2)) if m else None,
            }
        )
    confs = [p["conf"] for p in photos if p["conf"] is not None]
    return (
        {
            "slug": slug,
            "name": rec.get("name") or "",
            "producer": rec.get("producer") or "",
            "category": rec.get("category") or "",
            "color": rec.get("color") or "",
            "region": rec.get("region") or "",
            "grapes": rec.get("grapes") or "",
            "page_url": rec.get("page_url") or "",
            "in_catalog": bool(rec),
            "has_bottle": bool(bottle),
            # The bottle photo is a correction from `patch_dir`, not the photo
            # of the catalogue record. Every view marks such an image `patched`.
            "patched": slug in _patches,
            # A label crop of this wine is present. The page shows the package
            # and marks the picture when the wine has no crop of the kind that
            # the selector asks for.
            "has_label": slug in _labels,
            "has_label_box": slug in _label_boxes,
            # How the catalogue established this bottle photo. The build
            # writes it. See svoe-wino-hackaton/docs/plans/01_photo-join-repair.md.
            "image_match": rec.get("image_match") or {},
            "group": group_of.get(slug),
            "photos": photos,
            "min_conf": min(confs) if confs else None,
        }
    )


def null_row():
    """Return the row of the virtual NULL wine.

    The row is present even when `<photo_dir>/__null__/` is not, because the table
    MUST always offer the drop target. `perform_moves` makes the directory when
    the first photo goes there.

    The row carries no catalogue record, no bottle photo, and no variant group. It
    carries `null_row`, and every view uses that field to draw it apart.
    """
    photos = []
    if os.path.isdir(os.path.join(MY, NULL_SLUG)):
        for fn in scan_photos(NULL_SLUG):
            m = NAME_RE.match(fn)
            photos.append({"file": fn, "conf": int(m.group(2)) if m else None})
    return {
        "slug": NULL_SLUG,
        "name": NULL_NAME,
        "producer": "",
        "category": "",
        "color": "",
        "region": "",
        "grapes": "",
        "page_url": "",
        "in_catalog": False,
        "has_bottle": False,
        "patched": False,
        "has_label": False,
        "has_label_box": False,
        "image_match": {},
        "group": None,
        "photos": photos,
        "min_conf": None,
        "null_row": True,
    }


def catalog_only_rows(catalog, review_slugs, groups=None):
    """Return one row per catalogue card that has no directory in `my/`.

    The review table is built from `my/`, so a catalogue card with no candidate
    photo has no row. Such a card is a gap of the photo set, and a gap is worth
    seeing. The row carries the catalogue fields, an empty photo list, and the
    mark `catalog_only`.

    These rows are not part of `_rows`. They never reach `prune_state`, the
    label state, or the counters of the review set. The client shows them only
    when the selected filter asks for them.
    """
    group_of = {}
    for gid, g in (groups or {}).items():
        for slug in g.get("slugs", []):
            group_of[slug] = gid
    rows = []
    for slug in sorted(catalog):
        if slug in review_slugs:
            continue
        rec = catalog[slug]
        rows.append({
            "slug": slug,
            "name": rec.get("name") or "",
            "producer": rec.get("producer") or "",
            "category": rec.get("category") or "",
            "color": rec.get("color") or "",
            "region": rec.get("region") or "",
            "grapes": rec.get("grapes") or "",
            "page_url": rec.get("page_url") or "",
            "in_catalog": True,
            "has_bottle": bool(bottle_path(slug, catalog)),
            "patched": slug in _patches,
            "has_label": slug in _labels,
            "has_label_box": slug in _label_boxes,
            "image_match": rec.get("image_match") or {},
            "group": group_of.get(slug),
            "photos": [],
            "min_conf": None,
            "catalog_only": True,
        })
    return rows


def load_state():
    """Read `review-labels.json`. A missing or broken file gives empty state."""
    if not os.path.exists(LABEL_FILE):
        return {"labels": {}, "wines": {}}
    try:
        with open(LABEL_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as exc:
        print(f"warning: cannot read {LABEL_FILE}: {exc}", file=sys.stderr)
        return {"labels": {}, "wines": {}}
    labels = data.get("labels")
    if not isinstance(labels, dict):
        labels = {}
    wines = data.get("wines")
    if not isinstance(wines, dict):
        wines = {}
    return {"labels": labels, "wines": wines}


def load_excluded():
    """Read the excluded slugs. A missing or broken file gives an empty map."""
    if not os.path.exists(EXCLUDED_FILE):
        return {}
    try:
        with open(EXCLUDED_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as exc:
        print(f"warning: cannot read {EXCLUDED_FILE}: {exc}", file=sys.stderr)
        return {}
    excluded = data.get("excluded")
    if not isinstance(excluded, dict):
        return {}
    out = {}
    for slug, entry in excluded.items():
        if isinstance(entry, str):          # a short form: slug -> reason
            entry = {"reason": entry}
        if not isinstance(entry, dict):
            continue
        out[slug] = {"reason": str(entry.get("reason") or ""),
                     "ts": str(entry.get("ts") or "")}
    return out


def save_excluded():
    """Write the excluded slugs. The caller MUST hold `_lock`."""
    payload = {
        "version": 1,
        "updated": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "note": (
            "Excluded slugs of svoe-vino-testset. The key of an entry is the wine "
            "slug. Field 'reason' states why the slug is excluded. Field 'ts' holds "
            "the time of the exclusion. The photos of an excluded slug MUST NOT be "
            "used for benchmarking. A slug that is not in this file is included. "
            "Purpose: some slugs of the catalogue hold an error, most often a wrong "
            "bottle photo. A wrong bottle photo shifts the metrics, because the "
            "reference of the slug does not show the wine. Such a slug is excluded "
            "instead of corrected, so the benchmark stays comparable."
        ),
        "count": len(_excluded),
        "excluded": _excluded,
    }
    tmp = EXCLUDED_FILE + ".tmp"
    os.makedirs(os.path.dirname(EXCLUDED_FILE) or ".", exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, EXCLUDED_FILE)


def prune_state(rows):
    """Drop labels for a slug or a photo that `my/` no longer holds.

    The photo set is rebuilt by the pipeline, so a stored label can name a
    file that is gone. Such an entry would inflate the counts. The function
    returns the number of dropped entries. The caller MUST hold `_lock`.
    """
    known = {r["slug"]: {p["file"] for p in r["photos"]} for r in rows}
    dropped = 0
    for slug in list(_state["labels"]):
        files = known.get(slug)
        if files is None:
            dropped += len(_state["labels"].pop(slug))
            continue
        for fn in list(_state["labels"][slug]):
            if fn not in files:
                del _state["labels"][slug][fn]
                dropped += 1
        if not _state["labels"][slug]:
            del _state["labels"][slug]
    for slug in list(_state["wines"]):
        if slug not in known:
            del _state["wines"][slug]
            dropped += 1
    return dropped


def save_state():
    """Write the label file. The caller MUST hold `_lock`."""
    payload = {
        "version": 2,
        "updated": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "note": (
            "Manual labels for the photos of svoe-vino-testset/my. "
            "The key of an entry is the slug, then the photo file name. "
            "label 'positive': the photo shows the wine of this slug. "
            "label 'negative': the photo shows a different wine, and the photo stays "
            "in the set as a negative sample of this slug. "
            "label 'unusable': the photo is not usable at all and does not belong in "
            "the set. label 'variant': the photo shows this wine in another bottle, "
            "such as another vintage or another package design. "
            "A photo with no entry is not reviewed yet. "
            "The slug '__null__' is the virtual NULL wine. A photo under that "
            "slug matches NO card of the catalogue. The place is the statement, "
            "so such a photo needs no label; 'positive' confirms it and "
            "'unusable' takes the photo out of the set. "
            "Field 'reassign_to' names the slug that the photo belongs to; "
            "scripts/09_apply_moves.py moves the file. "
            "Field 'copy_to' names a slug that the photo ALSO belongs to; the same "
            "script copies the file and leaves the source photo where it is. "
            "The copy carries no label and one comment that names the source slug. "
            "Field 'comment' holds a free text note of the reviewer about this "
            "photo and this slug. The map 'wines' holds one free text note about a "
            "whole wine, keyed by the slug."
        ),
        "counts": count_state(),
        "labels": _state["labels"],
        "wines": _state["wines"],
    }
    tmp = LABEL_FILE + ".tmp"
    os.makedirs(os.path.dirname(LABEL_FILE) or ".", exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, LABEL_FILE)


def count_state():
    counts = {k: 0 for k in LABELS}
    reassigned = copied = commented = deleting = 0
    for photos in _state["labels"].values():
        for entry in photos.values():
            label = entry.get("label")
            if label in counts:
                counts[label] += 1
            if entry.get("reassign_to"):
                reassigned += 1
            if entry.get("copy_to"):
                copied += 1
            if entry.get("delete"):
                deleting += 1
            if entry.get("comment"):
                commented += 1
    counts["labelled"] = sum(counts[k] for k in LABELS)
    counts["reassigned"] = reassigned
    counts["copied"] = copied
    counts["deleting"] = deleting
    counts["commented"] = commented
    counts["proposed"] = sum(
        1 for photos in _state["labels"].values() for e in photos.values()
        if e.get("proposed") and not e.get("label"))
    counts["wine_notes"] = sum(
        1 for w in _state["wines"].values() if (w or {}).get("comment"))
    # The photos that lie under the NULL wine: they match no card of the
    # catalogue. `no_match_pending` counts the photos that a reviewer sent there
    # and that `apply` has not moved yet.
    counts["no_match"] = sum(len(r["photos"]) for r in _rows if r.get("null_row"))
    counts["no_match_pending"] = sum(
        1 for photos in _state["labels"].values() for e in photos.values()
        if e.get("reassign_to") == NULL_SLUG)
    return counts


API_FILTERS = ("all", "unlabelled", "needs_positive", "has_proposal",
               "fully_labelled", "in_variant_group",
               "image_unresolved", "image_assumed", "image_confirmed",
               "image_manual", "image_shared", "no_candidate_photos")

# A catalogue card with no directory in `my/` has no candidate photo. Such a
# card is not part of the review set, so it stays out of the default list. These
# filters ask about the catalogue itself, so each one pulls those cards in.
CATALOG_SCOPE_FILTERS = frozenset((
    "no_candidate_photos", "image_unresolved", "image_assumed",
    "image_confirmed", "image_manual", "image_shared"))


def api_filter(view, mode):
    if mode == "unlabelled":
        return view["unlabelled"] > 0
    if mode == "needs_positive":
        return view["labels"]["positive"] == 0
    if mode == "has_proposal":
        return view["proposed"] > 0
    if mode == "fully_labelled":
        return view["photos_total"] > 0 and view["unlabelled"] == 0
    if mode == "in_variant_group":
        return bool(view["variant_group"])
    im = view.get("image_match") or {}
    if mode == "image_unresolved":
        return im.get("method") == "unresolved"
    if mode == "image_assumed":
        return im.get("confidence") == "assumed"
    if mode == "image_confirmed":
        return im.get("confidence") == "confirmed"
    if mode == "image_manual":
        return im.get("method") == "manual"
    if mode == "image_shared":
        return bool(im.get("shared_with"))
    if mode == "no_candidate_photos":
        return view["photos_total"] == 0
    return True


# ----------------------------------------------------------------- the API view


def photo_view(slug, photo, catalog):
    """Return everything that is known about one candidate photo."""
    entry = (_state["labels"].get(slug) or {}).get(photo["file"]) or {}
    return {
        "file": photo["file"],
        "path": os.path.join(MY, slug, photo["file"]),
        "url": "/img/photo?slug=%s&file=%s" % (
            urllib.parse.quote(slug), urllib.parse.quote(photo["file"])),
        "conf": photo["conf"],
        "label": entry.get("label"),
        "proposed": entry.get("proposed"),
        "by": entry.get("by"),
        "confidence": entry.get("confidence"),
        "source_url": entry.get("source_url"),
        "comment": entry.get("comment"),
        "reassign_to": entry.get("reassign_to"),
        "moved_from": entry.get("moved_from"),
        "copy_to": entry.get("copy_to"),
        "copied_from": entry.get("copied_from"),
    }


def wine_view(row, catalog, groups, full=False):
    """Return the record of one wine for the API."""
    rec = catalog.get(row["slug"]) or {}
    counts = {k: 0 for k in LABELS}
    proposed = 0
    for p in row["photos"]:
        entry = (_state["labels"].get(row["slug"]) or {}).get(p["file"]) or {}
        if entry.get("label") in counts:
            counts[entry["label"]] += 1
        if entry.get("proposed") and not entry.get("label"):
            proposed += 1
    labelled = sum(counts.values())
    out = {
        "slug": row["slug"],
        "name": row["name"], "producer": row["producer"],
        "category": row["category"], "color": row["color"],
        "region": row["region"], "grapes": row["grapes"],
        "page_url": row["page_url"],
        "description": rec.get("description", ""),
        "in_catalog": row["in_catalog"],
        # The file that `/img/bottle` serves. It is the patch when the wine has
        # one, and the photo of the catalogue record otherwise.
        "bottle_path": bottle_path(row["slug"], catalog),
        "bottle_url": ("/img/bottle?slug=" + urllib.parse.quote(row["slug"])
                       if row["has_bottle"] else None),
        "patched": bool(row.get("patched")),
        # The label cut out of the picture that `bottle_path` names. A wine with
        # no crop answers None here, and `/img/bottle?kind=label` falls back to
        # the package picture of that wine.
        "label_path": label_path(row["slug"], "label"),
        "label_box_path": label_path(row["slug"], "labelbox"),
        "has_label": bool(row.get("has_label")),
        "has_label_box": bool(row.get("has_label_box")),
        "image_match": row.get("image_match") or {},
        "catalog_only": bool(row.get("catalog_only")),
        # The virtual NULL wine. Its photos match no card of the catalogue.
        "null_row": bool(row.get("null_row")),
        "photos_total": len(row["photos"]),
        "labels": counts,
        "labelled": labelled,
        "unlabelled": len(row["photos"]) - labelled,
        "proposed": proposed,
        "wine_note": (_state["wines"].get(row["slug"]) or {}).get("comment", ""),
        "excluded": row["slug"] in _excluded,
        "exclude_reason": (_excluded.get(row["slug"]) or {}).get("reason", ""),
        "variant_group": None,
    }
    gid = row.get("group")
    if gid and gid in groups:
        siblings = [x for x in groups[gid]["slugs"] if x != row["slug"]]
        out["variant_group"] = {
            "id": gid,
            "siblings": [
                {"slug": x,
                 "name": (catalog.get(x) or {}).get("name", ""),
                 "bottle_path": bottle_path(x, catalog),
                 "patched": x in _patches,
                 "has_label": x in _labels,
                 "has_label_box": x in _label_boxes,
                 "bottle_url": "/img/bottle?slug=" + urllib.parse.quote(x)}
                for x in siblings
            ],
        }
    if full:
        out["photos"] = [photo_view(row["slug"], p, catalog) for p in row["photos"]]
    return out


# ------------------------------------------------------------- the image fetch


def sniff_image_type(body, url=""):
    """Return the media type of a picture from its first bytes.

    A picture host does not always send `Content-Type`, and it sometimes sends a
    wrong one. The first bytes of the file are the only reliable statement, so
    they decide. The extension of the address answers only when the bytes do not.
    """
    if body[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if body[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if body[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if body[:4] == b"RIFF" and body[8:12] == b"WEBP":
        return "image/webp"
    if body[:2] == b"BM":
        return "image/bmp"
    ext = os.path.splitext(urllib.parse.urlsplit(url).path)[1].lower()
    for ctype, known in UPLOAD_TYPES.items():
        if ext == known or (ext == ".jpeg" and known == ".jpg"):
            return ctype
    return ""


def check_remote_url(url):
    """Return the URL when it is safe to fetch, else raise ValueError.

    The browser hands over a URL when a picture is dragged from another tab. The
    server then fetches it. Only http and https are allowed, and the host MUST
    NOT be a local or a private address: a dragged link MUST NOT reach a service
    of this machine or of the local network.
    """
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise ValueError("only an http or https address can be fetched")
    host = parts.hostname
    if not host:
        raise ValueError("the address holds no host")
    try:
        infos = socket.getaddrinfo(host, parts.port or
                                   (443 if parts.scheme == "https" else 80))
    except OSError as exc:
        raise ValueError("cannot resolve %s: %s" % (host, exc))
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast):
            raise ValueError("the address points at a local host: %s" % ip)
    return url


def fetch_image(url):
    """Return (body, content type) of a remote picture."""
    if url.startswith("data:"):
        head, _, data = url.partition(",")
        ctype = head[5:].split(";")[0].strip().lower()
        if ";base64" in head:
            body = base64.b64decode(data)
        else:
            body = urllib.parse.unquote_to_bytes(data)
        return body, sniff_image_type(body) or ctype

    check_remote_url(url)
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    })
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
        ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        declared = resp.headers.get("Content-Length")
        if declared and int(declared) > UPLOAD_MAX:
            raise ValueError("the picture is larger than %d bytes" % UPLOAD_MAX)
        body = resp.read(UPLOAD_MAX + 1)
    if len(body) > UPLOAD_MAX:
        raise ValueError("the picture is larger than %d bytes" % UPLOAD_MAX)
    sniffed = sniff_image_type(body, url)
    if not sniffed:
        raise ValueError(
            "the address does not answer with a picture (server said %s)"
            % (ctype or "nothing"))
    return body, sniffed


# -------------------------------------------------------------- the suggestions


TOKEN_RE = re.compile(r"[^a-zа-яё0-9]+", re.I)


def tokens(text):
    return {t for t in TOKEN_RE.split((text or "").lower()) if len(t) > 1}


def suggest_targets(slug, catalog, group_of, groups, limit=5):
    """Return the slugs that a photo of this slug most likely belongs to.

    The photos of one producer look alike, and a search result often shows the
    right wine in the wrong bottle. The order is: a member of the variant group
    of this wine, then the same producer, then a wine whose name shares words.
    """
    rec = catalog.get(slug) or {}
    prod = (rec.get("producer") or "").strip().lower()
    name_t = tokens(rec.get("name"))
    grapes = (rec.get("grapes") or "").strip().lower()
    category = (rec.get("category") or "").strip().lower()
    slug_t = set(slug.split("-"))
    gid = group_of.get(slug)
    members = set((groups.get(gid) or {}).get("slugs") or []) if gid else set()

    scored = []
    for other, r in catalog.items():
        if other == slug:
            continue
        score = 0
        if other in members:
            score += 100
        if prod and (r.get("producer") or "").strip().lower() == prod:
            score += 40
        score += 12 * len(name_t & tokens(r.get("name")))
        if grapes and (r.get("grapes") or "").strip().lower() == grapes:
            score += 8
        if category and (r.get("category") or "").strip().lower() == category:
            score += 3
        score += 2 * len(slug_t & set(other.split("-")))
        if score > 0:
            scored.append((-score, other))
    scored.sort()
    out = []
    for neg, other in scored[:limit]:
        r = catalog.get(other) or {}
        out.append({
            "slug": other,
            "name": r.get("name") or "",
            "producer": r.get("producer") or "",
            "category": r.get("category") or "",
            "has_bottle": bool(bottle_path(other, catalog)),
            "has_label": other in _labels,
            "has_label_box": other in _label_boxes,
            "patched": other in _patches,
            "in_group": other in members,
            "score": -neg,
        })
    # The NULL wine stands last, after the wines that the photo may show. It is
    # always offered: a photo that shows no card of the catalogue belongs there,
    # and the dialog MUST NOT ask the reviewer to type a reserved slug.
    if slug != NULL_SLUG:
        out.append({
            "slug": NULL_SLUG,
            "name": NULL_NAME,
            "producer": "no card of the catalogue shows this wine",
            "category": "",
            "has_bottle": False,
            "patched": False,
            "in_group": False,
            "null_row": True,
            "score": 0,
        })
    return out


# ------------------------------------------------------------------ the moves


def move_note(old_slug, new_slug, comment):
    """Return the comment of a moved photo.

    The comment is kept and gets one line in front of it that states where the
    photo was and where it went. The label is not kept: it judged the old pair.
    """
    if new_slug == NULL_SLUG:
        head = "перенесён в NULL из %s: в каталоге нет подходящей карточки" % old_slug
    else:
        head = "до переноса в %s был в %s" % (new_slug, old_slug)
    if comment:
        return head + " с таким комментарием:\n" + comment
    return head


def plan_moves(labels):
    """Return (planned, done, bad) for every recorded `reassign_to`.

    `planned` holds (slug, file, to, src, dst_dir). `done` holds the moves whose
    file already sits in the target. `bad` holds the moves that cannot be made.
    """
    planned, done, bad = [], [], []
    for slug, photos in sorted(labels.items()):
        for fn, entry in sorted(photos.items()):
            to = (entry or {}).get("reassign_to")
            if not to:
                continue
            if (entry or {}).get("delete"):
                # The reviewer asked for both. Deletion wins; the move is dropped.
                continue
            src = os.path.join(MY, slug, fn)
            dst_dir = os.path.join(MY, to)
            if os.path.basename(to) != to:
                bad.append((slug, fn, to, "the target slug holds a path separator"))
            elif not os.path.exists(src):
                if os.path.exists(os.path.join(dst_dir, fn)):
                    done.append((slug, fn, to))
                else:
                    bad.append((slug, fn, to, "the source file is gone"))
            else:
                planned.append((slug, fn, to, src, dst_dir))
    return planned, done, bad


def free_name(directory, name, tag="moved"):
    """Return a file name that is not taken in the directory.

    `tag` names the action that brings the file here, so the new name states why
    it is not the name of the source file: `_moved2` for a move, `_copy2` for a
    copy.
    """
    if not os.path.exists(os.path.join(directory, name)):
        return name
    stem, ext = os.path.splitext(name)
    n = 2
    while os.path.exists(os.path.join(directory, "%s_%s%d%s" % (stem, tag, n, ext))):
        n += 1
    return "%s_%s%d%s" % (stem, tag, n, ext)


def perform_moves(planned, labels):
    """Move the files and carry the entries to the target slug.

    The entry of a moved photo loses its label, because the label judged the old
    pair and the photo MUST be reviewed again. The comment is kept and gets the
    line of `move_note` in front of it. The field `moved_from` records the move.
    The caller MUST hold `_lock`.
    """
    moved, renamed = [], []
    for slug, fn, to, src, dst_dir in planned:
        os.makedirs(dst_dir, exist_ok=True)
        name = free_name(dst_dir, fn)
        shutil.move(src, os.path.join(dst_dir, name))
        if name != fn:
            renamed.append((fn, name))

        entry = (labels.get(slug) or {}).pop(fn, None) or {}
        if not labels.get(slug):
            labels.pop(slug, None)
        new_entry = {
            "comment": move_note(slug, to, entry.get("comment", "")),
            "moved_from": slug,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }
        labels.setdefault(to, {})[name] = new_entry
        moved.append((slug, fn, to, name))
    return moved, renamed


# ------------------------------------------------------------- the inbox of `my/`


def inbox_note(new_slug):
    """Return the comment of a photo that comes from the inbox.

    The photo carries no label, because no reviewer has judged it against a wine
    yet. The comment states where it comes from.
    """
    if new_slug == NULL_SLUG:
        return ("перенесён в NULL из входящих my/: в каталоге нет подходящей "
                "карточки")
    return "\u043f\u0435\u0440\u0435\u043d\u0435\u0441\u0451\u043d \u0432 %s \u0438\u0437 \u0432\u0445\u043e\u0434\u044f\u0449\u0438\u0445 my/" % new_slug


def plan_inbox_moves(pairs, catalog):
    """Return (planned, bad) for the moves that the sideboard asks for.

    `pairs` holds `{"file": <name>, "to": <slug>}`. A pair is refused when a name
    holds a path separator, when the target is not a slug of the catalogue, when
    the source file is not in the inbox, or when the same file is named twice.

    `planned` holds (file, to, src, dst_dir). The caller MUST hold `_lock`.
    """
    planned, bad, seen = [], [], set()
    for pair in pairs:
        fn = (pair or {}).get("file") or ""
        to = (pair or {}).get("to") or ""
        if not fn or not to:
            bad.append((fn, to, "the file and the target slug are both required"))
        elif os.path.basename(fn) != fn or os.path.basename(to) != to:
            bad.append((fn, to, "a name holds a path separator"))
        elif fn in seen:
            bad.append((fn, to, "the file is named twice"))
        elif to not in catalog and to != NULL_SLUG:
            bad.append((fn, to, "the target is not a slug of the catalogue"))
        else:
            src = os.path.join(MY, fn)
            if not os.path.isfile(src):
                bad.append((fn, to, "the file is not in the inbox"))
            else:
                seen.add(fn)
                planned.append((fn, to, src, os.path.join(MY, to)))
    return planned, bad


def perform_inbox_moves(planned, labels):
    """Move each file of the inbox into the directory of its wine.

    The file keeps its name. A name that is taken in the target gets the suffix
    of `free_name`. The photo gets a new entry with the comment of `inbox_note`
    and no label: no reviewer has judged it against this wine yet.
    The caller MUST hold `_lock`.
    """
    moved, renamed = [], []
    for fn, to, src, dst_dir in planned:
        os.makedirs(dst_dir, exist_ok=True)
        name = free_name(dst_dir, fn)
        shutil.move(src, os.path.join(dst_dir, name))
        if name != fn:
            renamed.append((fn, name))
        labels.setdefault(to, {})[name] = {
            "comment": inbox_note(to),
            "moved_from": "my/",
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }
        moved.append((fn, to, name))
    return moved, renamed


# ----------------------------------------------------------------- the copies


def copy_note(old_slug):
    """Return the comment of a copied photo.

    One photo can show two wines: the same label on two bottles of a variant
    group. A copy states that. The copy carries no label and no comment of the
    source photo, because both judged the source photo against the source wine.
    The one line states where the picture came from.
    """
    return "копия фотографии из %s" % old_slug


def plan_copies(labels):
    """Return (planned, bad) for every recorded `copy_to`.

    `planned` holds (slug, file, to, src, dst_dir). `bad` holds the copies that
    cannot be made. A copy has no `done` state, because the source file stays
    where it is. `perform_copies` clears `copy_to` when the file is written, so
    a second run finds nothing to do.
    """
    planned, bad = [], []
    for slug, photos in sorted(labels.items()):
        for fn, entry in sorted(photos.items()):
            to = (entry or {}).get("copy_to")
            if not to:
                continue
            if (entry or {}).get("delete"):
                # The reviewer asked for both. Deletion wins; the copy is dropped.
                continue
            src = os.path.join(MY, slug, fn)
            dst_dir = os.path.join(MY, to)
            if os.path.basename(to) != to:
                bad.append((slug, fn, to, "the target slug holds a path separator"))
            elif not os.path.exists(src):
                bad.append((slug, fn, to, "the source file is gone"))
            else:
                planned.append((slug, fn, to, src, dst_dir))
    return planned, bad


def perform_copies(planned, labels):
    """Copy the files. The source photo, its label, and its comment stay.

    The copy is a new candidate photo of the target wine. It carries no label,
    because a label judges one photo against one wine, and the wine is another
    one now. Its comment is the line of `copy_note`, and the field `copied_from`
    names the source slug. The field `copy_to` of the source entry is cleared,
    so a second run does not write the file again.

    The copy keeps the file name of the source, which holds the confidence value
    of the source wine. That value says nothing about the target wine. The name
    gets the tag `_copy2` only when the name is already taken in the target.
    The caller MUST hold `_lock`.
    """
    copied, renamed = [], []
    for slug, fn, to, src, dst_dir in planned:
        os.makedirs(dst_dir, exist_ok=True)
        name = free_name(dst_dir, fn, tag="copy")
        shutil.copy2(src, os.path.join(dst_dir, name))
        if name != fn:
            renamed.append((fn, name))

        entry = (labels.get(slug) or {}).get(fn) or {}
        entry.pop("copy_to", None)
        if entry.keys() <= {"ts"}:
            (labels.get(slug) or {}).pop(fn, None)
            if not labels.get(slug):
                labels.pop(slug, None)
        labels.setdefault(to, {})[name] = {
            "comment": copy_note(slug),
            "copied_from": slug,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }
        copied.append((slug, fn, to, name))
    return copied, renamed


# ----------------------------------------------------------------- the checks
#
# A check reads the photo set and the labels and reports the places where the set
# states two things that cannot both be true. A check never writes. The reviewer
# chooses the checks in a dialog and the table then shows the wines that fail.
#
# To add a check: write a function `check_<name>(rows, labels, groups, catalog)`
# that answers a list of findings, and name it in `CHECKS`. A finding MUST hold `check`
# and `why`, and it SHOULD hold `photos` (a list of `{slug, file}`) or `slugs`
# (a list of slugs). The route builds the list of failing wines from those two
# fields, so a new check needs no change of the page.


def photo_digests(rows):
    """Return sha256 -> [(slug, file)] over every candidate photo of `rows`.

    The whole set is about 2,500 files and 510 MB, and one pass takes about 2.5
    seconds on the SSD. The result is not cached: a cache would have to follow
    every write of every file, and the pass is short enough to run on demand.
    A file that cannot be read is left out, not reported.
    """
    by_digest = {}
    for row in rows:
        for photo in row["photos"]:
            path = os.path.join(MY, row["slug"], photo["file"])
            try:
                with open(path, "rb") as fh:
                    digest = hashlib.sha256(fh.read()).hexdigest()
            except OSError:
                continue
            by_digest.setdefault(digest, []).append((row["slug"], photo["file"]))
    return by_digest


def check_shared_positive(rows, labels, groups, catalog):
    """Find one picture that carries the label `positive` for two or more wines.

    The label `positive` states that the picture shows this wine. One picture
    cannot show two wines, so two such labels on one picture are a defect of the
    set. Either one label is wrong, or the two catalogue cards are one wine.

    Two wines of one variant group are the same wine in two bottles. Such a pair
    is reported too, and the finding carries `same_group`, because the reviewer
    decides whether the group is right.

    Two pictures count as one picture when their bytes are equal. A re-encoded
    copy or a resized copy of the same picture has another digest, and this check
    does not find it.
    """
    group_of = {}
    for gid, group in (groups or {}).items():
        for slug in group.get("slugs", []):
            group_of[slug] = gid
    findings = []
    for digest, items in sorted(photo_digests(rows).items()):
        hit = sorted((slug, fn) for slug, fn in items
                     if ((labels.get(slug) or {}).get(fn) or {}).get("label")
                     == "positive")
        slugs = sorted({slug for slug, _ in hit})
        if len(slugs) < 2:
            continue
        gids = {group_of.get(slug) for slug in slugs}
        same_group = len(gids) == 1 and None not in gids
        findings.append({
            "check": "shared_positive",
            "why": "one picture is `positive` for %d wines" % len(slugs),
            "same_group": same_group,
            "group": sorted(gids)[0] if same_group else None,
            "digest": digest,
            "photos": [{"slug": slug, "file": fn} for slug, fn in hit],
        })
    return findings


# The matcher runs SigLIP2 with an input of 448 by 448 pixels. The preprocessor
# stretches the whole picture into that square. It does not keep the aspect ratio,
# and it does not crop. `SiglipImageProcessor` calls `resize(image, size=(448, 448))`
# in one step; `preprocessor_config.json` of `google/siglip2-so400m-patch14-384`
# holds `size` alone and no `crop_size`.
#
# The check reads the LONG side of the picture, not the short side. A photo of a
# bottle is tall and narrow, so its short side is small even when the photo is good:
# the bottle itself is narrow, and a wider frame would only hold more background.
# The long side measures how much of the picture belongs to the bottle. Over the
# 3,832 photos that the check reads today the short side matches 65 photos and the
# long side matches 0; 52 of the 65 are tall product shots such as 142 by 600
# pixels, which are correct photos.
#
# A picture with a long side under 448 is stretched up and holds no more detail than
# it had. A picture with a long side under 256 is below the half of that input, and
# the text of the label is then too small for the text step and for the OCR step of
# the pipeline.
#
# The downloader already refuses a picture with a side under `MIN_SIDE` (200), see
# `scripts/02_download.py`. A smaller picture in the set came in before that rule or
# by hand, so the set MUST be checked as well.
MODEL_INPUT_PX = 448
TOO_SMALL_PX = 256


def photo_sizes(rows, labels):
    """Return [(slug, file, width, height)] for the photos that a check reads.

    The label `unusable` stays out: such a photo is already out of the set. Every
    other photo is read, with a label and without one, because the size decides
    whether the photo can carry a label at all.

    `Image.open` reads the header of the file, not the pixels, so the pass over the
    whole set takes well under a second.
    """
    from PIL import Image
    out = []
    for row in rows:
        for photo in row["photos"]:
            entry = (labels.get(row["slug"]) or {}).get(photo["file"]) or {}
            if entry.get("label") == "unusable" or entry.get("delete"):
                continue
            path = os.path.join(MY, row["slug"], photo["file"])
            try:
                with Image.open(path) as im:
                    width, height = im.size
            except (OSError, ValueError):
                continue
            out.append((row["slug"], photo["file"], width, height))
    return out


def _size_findings(rows, labels, check, low, high):
    """Report every photo whose long side is at least `low` and under `high`."""
    try:
        sizes = photo_sizes(rows, labels)
    except ImportError:
        return [{"check": check, "why": "Pillow is not installed, so the size of a "
                                        "picture cannot be read", "photos": []}]
    findings = []
    for slug, fname, width, height in sizes:
        long_side = max(width, height)
        if not (low <= long_side < high):
            continue
        findings.append({
            "check": check,
            "why": "the photo is %d by %d pixels; the long side %d is under %d"
                   % (width, height, long_side, high),
            "tag": "%dx%d" % (width, height),
            "width": width,
            "height": height,
            "long_side": long_side,
            "photos": [{"slug": slug, "file": fname}],
        })
    findings.sort(key=lambda f: (f["long_side"], f["photos"][0]["slug"]))
    return findings


def check_photo_too_small(rows, labels, groups, catalog):
    """Find a photo whose long side is under 256 pixels.

    Such a photo holds less than the half of the input of the matcher. The model
    stretches it up and reads no detail that the file does not hold. The text of the
    label is then too small for the text step and for the OCR step.
    """
    return _size_findings(rows, labels, "photo_too_small", 0, TOO_SMALL_PX)


def check_photo_below_model_input(rows, labels, groups, catalog):
    """Find a photo whose long side is 256 to 447 pixels.

    The matcher stretches such a photo up to its input of 448 by 448 pixels. The
    photo is usable, and it carries less detail than the model can read.

    A photo under 256 pixels is reported by `photo_too_small` only, so the two lists
    never hold the same photo.
    """
    return _size_findings(rows, labels, "photo_below_model_input",
                          TOO_SMALL_PX, MODEL_INPUT_PX)


# --------------------------------------- the catalogue render in the candidates
#
# `my/` holds real-world photos only. The catalogue bottle photo of a wine is a
# studio render, and stage 5 keeps such a render out of the set. A render that
# reaches the candidate set anyway makes the benchmark easier than reality: the
# matcher then reads its own catalogue picture back, and it scores a match that no
# camera earned.
#
# The check compares every candidate photo of a wine with the catalogue bottle
# photo of THAT wine. It does not compare across wines.
#
# Two pictures count as duplicates when the bytes are equal, or when the content is
# equal and the size differs. The second case needs the pixels: a resized copy, a
# re-encoded copy, and a copy with another white margin all hold other bytes.
#
# The check reduces each picture to one signature. It composites the picture on
# white, converts it to grey, crops it to the bounding box of what is not
# background, and resizes that box to 32 by 32. The crop is the step that makes the
# signature independent of the margin and of the aspect ratio. The measure of two
# signatures is the mean absolute difference of the 1,024 values, on the scale 0 to
# 255. A value of 0 means that the two pictures are equal after the reduction.
#
# The threshold comes from a measurement of the set on 2026-09-18, 4,112 pairs of
# one candidate photo and one catalogue bottle photo. 66 pairs were compared by eye
# across the whole range. Every sampled pair under the measure 11 was the same
# picture, and clear false pairs start at about 16. The threshold 10 is set one step
# under the first uncertain case. On the set of that day the check reports 304 of
# the 4,112 pairs. A copy whose measure is over the threshold is not reported; the
# check misses it. The measurement is in `ResearchLog.md`.
#
# The crop matters: without it the same picture in another margin measures as much
# as 119. The plain measure found 143 of the same 4,112 pairs against 304 here.
#
# Measured on a made copy of one bottle photo: half size as JPEG 0.28, quarter size as
# PNG 0.35, the same size at JPEG quality 70 0.18, and a wider white margin 0.12.
#
# Limit: the check composites a transparent picture on WHITE. A render that was
# flattened on another colour measures far over the threshold, and the check does not
# find it. A shop page nearly always uses white.
SIGN_PX = 32
# A grey value this far under white counts as content, not as background.
SIGN_BG = 18
# A box under this size is not a bottle. Such a picture keeps its full frame.
SIGN_MIN_BOX = 8
DUPLICATE_MAD = 10.0
# Pillow releases the interpreter lock while it decodes, so threads help. Eight
# threads read the 4,112 files of the set in about 70 seconds against about 120
# seconds in one thread.
SIGN_WORKERS = 8


def photo_signature(path):
    """Return `(sha256, signature)` of one picture, or None.

    The file is read once. The digest answers the case `same bytes`, and the
    signature answers the case `same content, other size`. A file that cannot be
    read or cannot be decoded gives None, and the caller leaves it out.
    """
    from PIL import Image, ImageChops
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError:
        return None
    try:
        with Image.open(io.BytesIO(raw)) as im:
            # A JPEG decodes at a reduced scale. The other formats ignore this call.
            im.draft("RGB", (512, 512))
            im = im.convert("RGBA")
            flat = Image.new("RGBA", im.size, (255, 255, 255, 255))
            flat.alpha_composite(im)
            grey = flat.convert("L")
            mask = ImageChops.invert(grey).point(
                lambda v: 255 if v > SIGN_BG else 0)
            box = mask.getbbox()
            if (box and box[2] - box[0] >= SIGN_MIN_BOX
                    and box[3] - box[1] >= SIGN_MIN_BOX):
                grey = grey.crop(box)
            grey = grey.resize((SIGN_PX, SIGN_PX), Image.BILINEAR)
            return hashlib.sha256(raw).hexdigest(), grey.tobytes()
    except (OSError, ValueError, TypeError):
        return None


def signature_mad(one, two):
    """Return the mean absolute difference of two signatures, from 0 to 255."""
    return sum(abs(a - b) for a, b in zip(one, two)) / float(len(one))


def check_candidate_is_catalog_photo(rows, labels, groups, catalog):
    """Find a candidate photo that is the catalogue bottle photo of the same wine.

    The set holds real-world photos only, so such a photo is a defect: the matcher
    would read its own catalogue picture back. The photo is a candidate for the
    label `unusable`.

    A photo marked `unusable` and a photo marked for deletion stay out, as in the
    size checks: such a photo is already out of the set.

    A wine with no catalogue bottle photo is not checked.
    """
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        return [{"check": "candidate_is_catalog_photo",
                 "why": "Pillow is not installed, so the pixels of a picture "
                        "cannot be read", "photos": []}]
    jobs = []
    for row in rows:
        bottle = (catalog.get(row["slug"]) or {}).get("local_path")
        if not bottle:
            continue
        for photo in row["photos"]:
            entry = (labels.get(row["slug"]) or {}).get(photo["file"]) or {}
            if entry.get("label") == "unusable" or entry.get("delete"):
                continue
            jobs.append((row["slug"], photo["file"],
                         os.path.join(MY, row["slug"], photo["file"]), bottle))
    if not jobs:
        return []
    # One read per file. A bottle photo is named by every candidate of its wine,
    # and the set holds it once.
    paths = sorted({job[2] for job in jobs} | {job[3] for job in jobs})
    with ThreadPoolExecutor(SIGN_WORKERS) as pool:
        signs = dict(zip(paths, pool.map(photo_signature, paths)))
    findings = []
    for slug, fname, photo_path, bottle_path in jobs:
        cand = signs.get(photo_path)
        bott = signs.get(bottle_path)
        if cand is None or bott is None:
            continue
        if cand[0] == bott[0]:
            mad = 0.0
            why = ("the photo is the catalogue bottle photo of this wine; "
                   "the bytes are equal")
        else:
            mad = signature_mad(cand[1], bott[1])
            if mad >= DUPLICATE_MAD:
                continue
            why = ("the photo is the catalogue bottle photo of this wine in "
                   "another size or another encoding; the difference of the two "
                   "signatures is %.1f of 255, and the threshold is %.1f"
                   % (mad, DUPLICATE_MAD))
        findings.append({
            "check": "candidate_is_catalog_photo",
            "why": why,
            "same_bytes": cand[0] == bott[0],
            "difference": round(mad, 2),
            "tag": "catalogue render",
            "photos": [{"slug": slug, "file": fname}],
        })
    findings.sort(key=lambda f: (f["difference"], f["photos"][0]["slug"]))
    return findings


# The bottle photo of two wines.
#
# `check_catalog_photo_twin` compares the CATALOGUE bottle photo of one wine with
# the catalogue bottle photo of every other wine. It does not read a candidate
# photo. Two wines that carry one picture are a defect of the catalogue: the
# matcher cannot separate them by the image, and one of the two cards names the
# wrong bottle.
#
# The check runs in two stages, because the full compare of 2,093 pictures is
# 2,189,278 pairs.
#
# Stage one reads the grey 32 by 32 signature of `photo_signature` for every
# picture and compares every pair with numpy. It takes about 3 seconds. That
# signature is coarse: it holds no colour and it holds no text of the label, so
# two DIFFERENT wines of one producer line fall under 0.5 of 255. Stage one
# therefore does not decide; it only names the pairs that stage two reads.
#
# Stage two reads a colour 128 by 128 signature of the named pictures alone and
# measures again. Over the catalogue of 2026-09-17 the two populations separate
# with a wide gap: 29 pairs measure exactly 0.00, and every one of them is
# byte-identical; the next pair measures 0.069. The gap carries the meaning of
# the two tags below.
TWIN_PX = 128
TWIN_COARSE_MAD = 3.0
TWIN_MAD = 1.0
TWIN_SAME_MAD = 0.05
# 32 rows at a time hold the difference block at about 137 MB.
TWIN_CHUNK = 32


def bottle_fine_signature(path):
    """Return the colour signature of one bottle photo, or None.

    The crop is the crop of `photo_signature`: the picture is flattened on white,
    and the box of the bottle is cut out of it. The result keeps the colour and a
    higher resolution, so the text of the label and the colour of the wine reach
    the compare. `photo_signature` throws both away.
    """
    from PIL import Image, ImageChops
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError:
        return None
    try:
        with Image.open(io.BytesIO(raw)) as im:
            im.draft("RGB", (512, 512))
            im = im.convert("RGBA")
            flat = Image.new("RGBA", im.size, (255, 255, 255, 255))
            flat.alpha_composite(im)
            grey = flat.convert("L")
            mask = ImageChops.invert(grey).point(
                lambda v: 255 if v > SIGN_BG else 0)
            box = mask.getbbox()
            colour = flat.convert("RGB")
            if (box and box[2] - box[0] >= SIGN_MIN_BOX
                    and box[3] - box[1] >= SIGN_MIN_BOX):
                colour = colour.crop(box)
            return colour.resize((TWIN_PX, TWIN_PX), Image.BILINEAR).tobytes()
    except (OSError, ValueError, TypeError):
        return None


def _twin_pairs(slugs, signs):
    """Return [(a, b)] for every pair of `slugs` under `TWIN_COARSE_MAD`.

    `signs` holds the grey signature of each slug in the order of `slugs`. The
    compare runs on the upper triangle alone, so a pair is answered once.
    """
    import numpy as np
    matrix = np.frombuffer(b"".join(signs), dtype=np.uint8)
    matrix = matrix.reshape(len(slugs), -1).astype(np.int16)
    out = []
    for start in range(0, len(slugs), TWIN_CHUNK):
        block = matrix[start:start + TWIN_CHUNK]
        dist = np.abs(block[:, None, :] - matrix[None, :, :]).mean(axis=2)
        for row in range(block.shape[0]):
            dist[row, :start + row + 1] = 999.0
        for row, col in np.argwhere(dist < TWIN_COARSE_MAD):
            out.append((slugs[start + row], slugs[col]))
    return out


def _twin_clusters(edges):
    """Join the pairs of `edges` into clusters and return a list of slug lists.

    Two wines that carry one picture, and a third wine that carries the same
    picture, form one cluster of three. The reviewer reads the whole cluster at
    once, so the check reports the cluster and not the three pairs.
    """
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    out = {}
    for slug in parent:
        out.setdefault(find(slug), []).append(slug)
    return [sorted(v) for v in out.values()]


def check_catalog_photo_twin(rows, labels, groups, catalog):
    """Find two wines whose CATALOGUE bottle photo is the same or nearly the same.

    The check reads the catalogue photo alone. A candidate photo of `my/` is not
    read and does not change the result.

    A finding carries the whole cluster in `slugs`, the largest distance inside
    the cluster in `distance`, and one of two tags:

    `same pic`  the distance is under 0.05. The two cards carry one picture. The
                matcher cannot separate the two wines by the image, and one card
                names the wrong bottle. This is a defect.
    `twin`      the distance is from 0.05 to 1.0. The two pictures are different
                photographs of a bottle that looks nearly the same, as two wines
                of one producer line do. This is not a defect by itself, and the
                pair is a candidate for a variant group.
    """
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        return [{"check": "catalog_photo_twin", "bottle": True,
                 "why": "Pillow is not installed, so the pixels of a picture "
                        "cannot be read", "slugs": []}]
    try:
        import numpy  # noqa: F401
    except ImportError:
        return [{"check": "catalog_photo_twin", "bottle": True,
                 "why": "numpy is not installed, so the full compare of the "
                        "catalogue cannot run", "slugs": []}]

    known = {}
    for slug in sorted(catalog):
        path = (catalog.get(slug) or {}).get("local_path")
        if path and os.path.isfile(path):
            known[slug] = path
    if len(known) < 2:
        return []

    # One read per distinct file. Several cards may name one file on disk.
    paths = sorted(set(known.values()))
    with ThreadPoolExecutor(SIGN_WORKERS) as pool:
        coarse = dict(zip(paths, pool.map(photo_signature, paths)))
    slugs = [s for s in sorted(known) if coarse.get(known[s]) is not None]
    if len(slugs) < 2:
        return []
    digest = {s: coarse[known[s]][0] for s in slugs}
    edges = _twin_pairs(slugs, [coarse[known[s]][1] for s in slugs])
    if not edges:
        return []

    want = sorted({s for pair in edges for s in pair})
    fine_paths = sorted({known[s] for s in want})
    with ThreadPoolExecutor(SIGN_WORKERS) as pool:
        fine = dict(zip(fine_paths, pool.map(bottle_fine_signature, fine_paths)))
    measured = {}
    keep = []
    for a, b in edges:
        one, two = fine.get(known[a]), fine.get(known[b])
        if one is None or two is None:
            continue
        mad = 0.0 if known[a] == known[b] else signature_mad(one, two)
        if mad >= TWIN_MAD:
            continue
        measured[(a, b)] = mad
        keep.append((a, b))
    if not keep:
        return []

    findings = []
    for cluster in _twin_clusters(keep):
        inside = [mad for (a, b), mad in measured.items()
                  if a in cluster and b in cluster]
        worst = max(inside) if inside else 0.0
        same = worst < TWIN_SAME_MAD
        equal = len({digest[s] for s in cluster}) == 1
        if same:
            why = ("the catalogue bottle photo of %d wines is one picture%s; the "
                   "difference of the signatures is %.2f of 255, and the limit of "
                   "one picture is %.2f"
                   % (len(cluster), "; the bytes are equal" if equal else "",
                      worst, TWIN_SAME_MAD))
        else:
            why = ("the catalogue bottle photo of %d wines is nearly the same "
                   "picture; the difference of the signatures is %.2f of 255, and "
                   "the limit of the check is %.2f. Two wines of one producer line "
                   "look like this and are not a defect by themselves."
                   % (len(cluster), worst, TWIN_MAD))
        findings.append({
            "check": "catalog_photo_twin",
            "why": why,
            "bottle": True,
            "same_picture": same,
            "same_bytes": equal,
            "distance": round(worst, 3),
            "tag": "same pic" if same else "twin",
            "slugs": cluster,
        })
    findings.sort(key=lambda f: (f["distance"], f["slugs"][0]))
    return findings


CHECKS = (
    {
        "id": "shared_positive",
        "title": "one picture is positive for two wines",
        "help": ("Read every candidate photo and compare the bytes. A picture that "
                 "carries the label positive under two or more slugs is a defect: one "
                 "picture cannot show two wines. A pair inside one variant group is "
                 "reported too and is marked as such. A re-encoded copy of the same "
                 "picture has other bytes and is not found."),
        "run": check_shared_positive,
    },
    {
        "id": "photo_too_small",
        "title": "the photo is too small (long side under 256 px)",
        "help": ("Read the size of every photo that is not marked unusable. The "
                 "check reads the long side, because a photo of a bottle is tall "
                 "and narrow and its short side is small even when the photo is "
                 "good. The matcher runs SigLIP2 with an input of 448 by 448 "
                 "pixels, so a photo with a long side under 256 holds less than "
                 "the half of that input. The model stretches it up and reads no "
                 "detail that the file does not hold, and the text of the label is "
                 "too small for the text step and for the OCR step. Such a photo "
                 "is a candidate for the label unusable."),
        "run": check_photo_too_small,
    },
    {
        "id": "photo_below_model_input",
        "title": "the photo is smaller than the input of the matcher (long side 256 to 447 px)",
        "help": ("The same size read, for the band above. The matcher stretches such "
                 "a photo up to its input of 448 by 448 pixels. The photo is usable "
                 "and it carries less detail than the model can read. A photo with a "
                 "long side under 256 pixels is reported by the check above and is "
                 "not repeated here, so the two lists never hold the same photo."),
        "run": check_photo_below_model_input,
    },
    {
        "id": "candidate_is_catalog_photo",
        "title": "the candidate photo is the catalogue bottle photo of the wine",
        "help": ("The set holds real-world photos only, and the catalogue bottle "
                 "photo of a wine is a studio render. A candidate photo that is "
                 "that render makes the benchmark easier than reality: the matcher "
                 "reads its own catalogue picture back. The check compares every "
                 "candidate photo with the bottle photo of the SAME wine, never "
                 "with the bottle photo of another wine. Two pictures count as "
                 "duplicates when the bytes are equal, and also when the content is "
                 "equal and the size differs: the check crops each picture to the "
                 "bottle, reduces it to a grey 32 by 32 square, and compares the "
                 "1,024 values. A resized copy, a re-encoded copy, and a copy with "
                 "another white margin are all found. A render that was flattened on "
                 "a colour other than white is NOT found. A photo marked unusable and "
                 "a photo marked for deletion stay out. The run reads the pixels of "
                 "every photo and takes about 50 seconds."),
        "run": check_candidate_is_catalog_photo,
    },
    {
        "id": "catalog_photo_twin",
        "title": "two wines carry the same catalogue bottle photo",
        "help": ("Compare the CATALOGUE bottle photo of every wine with the "
                 "catalogue bottle photo of every other wine. A candidate photo "
                 "of my/ is not read by this check. Two wines that carry one "
                 "picture are a defect of the catalogue: the matcher cannot "
                 "separate them by the image, and one of the two cards names the "
                 "wrong bottle. The whole catalogue is read, including a card "
                 "that has no candidate photo yet. The compare runs in two "
                 "stages: a grey 32 by 32 signature names the near pairs of all "
                 "2.2 million pairs, and a colour 128 by 128 signature then "
                 "measures those pairs alone. A finding reports the whole "
                 "cluster and carries one of two tags. `same pic` means the "
                 "distance is under 0.05 and the two cards carry one picture; "
                 "this is a defect. `twin` means the distance is from 0.05 to "
                 "1.0 and the two pictures are different photographs of a bottle "
                 "that looks nearly the same, as two wines of one producer line "
                 "do; this is not a defect by itself and the pair is a candidate "
                 "for a variant group. The run reads the pixels of every "
                 "catalogue photo and takes about 40 seconds."),
        "run": check_catalog_photo_twin,
    },
)


def plan_deletes(labels):
    """Return (planned, gone) for every photo that carries `delete`.

    `planned` holds (slug, file, src). `gone` holds the entries whose file is
    already absent; the caller drops those entries without a file operation.
    """
    planned, gone = [], []
    for slug, photos in sorted(labels.items()):
        for fn, entry in sorted(photos.items()):
            if not (entry or {}).get("delete"):
                continue
            src = os.path.join(MY, slug, fn)
            if os.path.isfile(src):
                planned.append((slug, fn, src))
            else:
                gone.append((slug, fn))
    return planned, gone


def perform_deletes(planned, gone, labels):
    """Move each planned photo into `my/trash/<slug>/` and drop its entry.

    The photo is NOT unlinked. It is moved, so a wrong decision can be undone by
    hand. The entry is dropped in full: the file no longer sits in `my/`, so a
    label, a comment, or a proposal for it has no meaning any more.
    The caller MUST hold `_lock`.
    """
    deleted, failed = [], []
    for slug, fn, src in planned:
        dst_dir = os.path.join(TRASH, slug)
        try:
            os.makedirs(dst_dir, exist_ok=True)
            name = free_name(dst_dir, fn)
            shutil.move(src, os.path.join(dst_dir, name))
        except OSError as exc:
            failed.append((slug, fn, str(exc)))
            continue
        (labels.get(slug) or {}).pop(fn, None)
        if not labels.get(slug):
            labels.pop(slug, None)
        deleted.append((slug, fn, os.path.join(dst_dir, name)))
    for slug, fn in gone:
        (labels.get(slug) or {}).pop(fn, None)
        if not labels.get(slug):
            labels.pop(slug, None)
    return deleted, failed


# ------------------------------------------------------------------- the runs


def run_dirs():
    """Return the id of every run directory, the newest first."""
    if not os.path.isdir(RUNS_DIR):
        return []
    out = []
    for name in os.listdir(RUNS_DIR):
        if name.startswith(".") or not os.path.isdir(os.path.join(RUNS_DIR, name)):
            continue
        out.append(name)
    return sorted(out, reverse=True)


def run_path(run_id, name):
    """Return the path of one file of one run, or None.

    The function refuses a run id that holds a path separator or a parent
    reference, and a path that leaves `RUNS_DIR`.
    """
    if not run_id or os.path.basename(run_id) != run_id:
        return None
    base = os.path.realpath(RUNS_DIR)
    path = os.path.realpath(os.path.join(base, run_id, name))
    if not (path == base or path.startswith(base + os.sep)):
        return None
    return path


def run_head(run_id):
    """Return the short record of one run for the table of the runs."""
    meta = _read_json(run_path(run_id, "run.json")) or {}
    met = _read_json(run_path(run_id, "metrics.json")) or {}
    pos = met.get("positive") or {}
    neg = met.get("negative") or {}
    return {
        "id": run_id,
        "backend": (met.get("backend") or (meta.get("options") or {}).get("backend")
                    or "—"),
        "label": ((meta.get("backend") or {}) or {}).get("label", ""),
        "started": meta.get("started") or "",
        "finished": meta.get("finished") or "",
        "dry_run": bool((meta.get("options") or {}).get("dry_run")),
        "queries": (met.get("queries") or {}).get("total",
                                                  (meta.get("query_set") or {}).get("total")),
        "positive": pos.get("n"),
        "negative": neg.get("n"),
        "recall_at_1": pos.get("recall_at_1"),
        "match_share": pos.get("match_share", pos.get("recall_at_1")),
        "f1_at_1": ((pos.get("f1_at_1") or {}) or {}).get("f1"),
        "f1_at_5": ((pos.get("f1_at_5") or {}) or {}).get("f1"),
        "near_duplicate_confusion": pos.get("near_duplicate_confusion"),
        "within_sla_share": (met.get("latency_ms") or {}).get("within_sla_share"),
        "sla_ms": (met.get("latency_ms") or {}).get("sla_ms"),
        "recall_at_5": pos.get("recall_at_5"),
        "recall_at_10": pos.get("recall_at_10"),
        "false_match_at_1": neg.get("false_match_at_1"),
        "latency_median": (met.get("latency_ms") or {}).get("median"),
        "has_metrics": bool(met),
        "subset": met.get("subset") or None,
        # When the vectors that answered this run were last built.
        # `scripts/match_run.py` reads it from the backend at run creation. A
        # run made before that key existed has None, which the page prints as
        # "not recorded" rather than as an empty cell.
        "embeddings": meta.get("embeddings"),
    }


def _read_json(path):
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


# The orders that `/runs` offers for the photo rows. `manifest` is the order of
# `queries.tsv`, which is the order that the backend answered in.
ROW_SORTS = ("manifest", "worst", "rank", "latency_desc", "latency_asc",
             "score_desc", "score_asc", "path")


def _row_sort_key(rec, mode):
    """Return the sort key of one row for the order `mode`."""
    rank = rec.get("rank_of_truth")
    top = (rec.get("candidates") or [None])[0]
    score = (top or {}).get("score")
    lat = rec.get("latency_ms")
    path = rec.get("image_path") or ""
    if mode == "path":
        return (path,)
    if mode == "rank":
        # rank 1 first, then deeper, then the rows whose true slug never came back
        return (0, rank) if rank else (1, 0)
    if mode == "worst":
        # the most wrong first: a false match, then an absent truth, then a deep rank
        if rec.get("outcome") == "false_match_at_1":
            return (0, 0, path)
        if rec.get("label") in ("positive", "variant"):
            if rank is None:
                return (1, 0, path)
            if rank > 1:
                return (2, -rank, path)
            return (4, 0, path)
        return (3, 0, path)
    if mode in ("latency_desc", "latency_asc"):
        value = -1 if lat is None else lat
        return (-value,) if mode == "latency_desc" else (value,)
    if mode in ("score_desc", "score_asc"):
        # a row with no score stands last in both orders
        if score is None:
            return (1, 0.0)
        return (0, -score) if mode == "score_desc" else (0, score)
    return (rec.get("query_id") or "",)


# ------------------------------------------------------- the twin of a photo
#
# One photo file can stand in the set two times: `positive` for the wine that it
# shows, and `negative` for a wine that it does not show. The two rows hold the
# same `image_sha256`, because the bytes are equal. So a negative row can borrow
# the true slug of the photo from its positive twin, and the answer of the
# backend can be read in full: the true wine SHOULD stand above the wine that the
# negative label forbids.
#
# The index reads one run only. A photo whose twin was not in the run has no twin
# here. This keeps the report a report of that run and of nothing else.

_TWIN_CACHE = {}


def twin_index(run_id):
    """Return `image_sha256` -> {"positive": [slug...], "negative": [slug...]}.

    The lists hold the distinct slugs of the rows of this run whose photo holds
    these exact bytes. The label `variant` is left out: it groups the wine in
    another bottle and states no truth about the photo.

    The result is cached by the size and the time of `results.jsonl`. A run file
    does not change after the run, so the cache never goes stale.
    """
    path = run_path(run_id, "results.jsonl")
    if not path or not os.path.exists(path):
        return {}
    try:
        st = os.stat(path)
    except OSError:
        return {}
    key = (path, st.st_mtime_ns, st.st_size)
    hit = _TWIN_CACHE.get(run_id)
    if hit and hit[0] == key:
        return hit[1]
    index = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            sha, slug, label = (rec.get("image_sha256"), rec.get("slug"),
                                rec.get("label"))
            if not sha or not slug or label not in ("positive", "negative"):
                continue
            slot = index.setdefault(sha, {"positive": set(), "negative": set()})
            slot[label].add(slug)
    for slot in index.values():
        slot["positive"] = sorted(slot["positive"])
        slot["negative"] = sorted(slot["negative"])
    _TWIN_CACHE.clear()
    _TWIN_CACHE[run_id] = (key, index)
    return index


def first_rank(candidates, slug):
    """Return the first rank of `slug` in `candidates`, or None.

    A backend MAY answer one slug two times. The first place is the place that
    counts, which is the rule of `judge()` in `scripts/match_run.py`.
    """
    best = None
    for cand in candidates or ():
        if cand.get("slug") != slug:
            continue
        rank = cand.get("rank")
        if rank is None:
            continue
        if best is None or rank < best:
            best = rank
    return best


def add_twin(rec, index):
    """Add the field `twin` to one row of a run. Return the row.

    `twin` holds:

        slugs           the slugs that the positive twin of this photo names,
                        without the slug of this row
        rank            the first rank of the best of those slugs, or null
        forbidden_rank  the first rank of the slug of this row, or null. The row
                        MUST be negative; that slug is the wrong answer
        verdict         `above`   the true wine stands above the forbidden wine
                        `below`   the forbidden wine stands above the true wine
                        `no_forbidden` the forbidden wine never came back
                        `absent`  the true wine never came back
                        null      this row has no positive twin, or is not negative
        conflict        the set states two things that cannot both be true
        conflict_slugs  the slugs of that contradiction

    A photo can be positive for one wine only. Two positive slugs on one photo, or
    the same slug both positive and negative, is a defect of the set, not a result
    of the run. The field `conflict` marks it so the reviewer can repair the set.
    """
    rec["twin"] = None
    slot = index.get(rec.get("image_sha256") or "")
    if not slot:
        return rec
    positive, negative = slot["positive"], slot["negative"]
    both = sorted(set(positive) & set(negative))
    conflict = len(positive) > 1 or bool(both)
    slugs = [s for s in positive if s != rec.get("slug")]
    twin = {
        "slugs": slugs,
        "rank": None,
        "forbidden_rank": None,
        "verdict": None,
        "conflict": conflict,
        "conflict_slugs": {"positive": positive, "both": both} if conflict else None,
    }
    if rec.get("label") == "negative" and slugs:
        ranks = [r for r in (first_rank(rec.get("candidates"), s) for s in slugs)
                 if r is not None]
        twin["rank"] = min(ranks) if ranks else None
        twin["forbidden_rank"] = first_rank(rec.get("candidates"), rec.get("slug"))
        if twin["rank"] is None:
            twin["verdict"] = "absent"
        elif twin["forbidden_rank"] is None:
            twin["verdict"] = "no_forbidden"
        elif twin["rank"] < twin["forbidden_rank"]:
            twin["verdict"] = "above"
        else:
            twin["verdict"] = "below"
    rec["twin"] = twin
    return rec


def run_rows(run_id, mode="all", query="", limit=200, offset=0, sort="manifest"):
    """Return the rows of `results.jsonl` that the filter keeps, in the asked order."""
    path = run_path(run_id, "results.jsonl")
    if not path or not os.path.exists(path):
        return [], 0
    query = (query or "").strip().lower()
    index = twin_index(run_id)
    kept = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            add_twin(rec, index)
            if not _row_matches(rec, mode):
                continue
            if query and query not in (rec.get("image_path", "") + " " +
                                       (rec.get("predicted_slug") or "")).lower():
                continue
            kept.append(rec)
    total = len(kept)
    if sort and sort != "manifest" and sort in ROW_SORTS:
        kept.sort(key=lambda rec: _row_sort_key(rec, sort))
    return kept[offset:offset + limit], total


def _row_matches(rec, mode):
    """Answer whether the row passes the filter `mode`.

    The modes `negative_above_positive` and `twin_conflict` read the field `twin`,
    which `add_twin` writes. `run_rows` adds it before this call.
    """
    label, rank = rec.get("label"), rec.get("rank_of_truth")
    outcome = rec.get("outcome")
    if mode in ("all", ""):
        return True
    if mode == "error":
        return bool(rec.get("error"))
    if mode == "hit":
        return label in ("positive", "variant") and rank == 1
    if mode == "miss":
        return label in ("positive", "variant") and rank != 1
    if mode == "near":          # the truth is in the list but not at rank 1
        return label in ("positive", "variant") and rank is not None and rank > 1
    if mode == "absent":        # the truth never appeared
        return label in ("positive", "variant") and rank is None
    if mode == "rank_2_5":      # the truth is in the list, at rank 2 to 5
        return (label in ("positive", "variant") and rank is not None
                and 2 <= rank <= 5)
    # `after_5` and `after_10` read "not in R@5" and "not in R@10". A truth that
    # never came back counts as a failure at every depth, which is the rule of
    # `failed_before()` in `scripts/match_run.py`.
    if mode == "after_5":
        return label in ("positive", "variant") and (rank is None or rank > 5)
    if mode == "after_10":
        return label in ("positive", "variant") and (rank is None or rank > 10)
    # A `no_match` photo matches no card of the catalogue. The correct answer is
    # no answer, so every answer is a false match.
    if mode == "no_match":
        return label == "no_match"
    if mode == "no_match_answered":
        return label == "no_match" and outcome == "false_match_at_1"
    if mode == "false_match":
        return label == "negative" and outcome == "false_match_at_1"
    if mode == "negative_in_topk":
        return label == "negative" and rank is not None
    if mode == "negative":
        return label == "negative"
    twin = rec.get("twin") or {}
    if mode == "negative_above_positive":
        return label == "negative" and twin.get("verdict") == "below"
    if mode == "twin_conflict":
        return bool(twin.get("conflict"))
    return True


# ---------------------------------------------------------------- HTTP handler


def guess_type(path):
    t, _ = mimetypes.guess_type(path)
    return t or "application/octet-stream"


class Handler(BaseHTTPRequestHandler):
    server_version = "svoe-vino-review/1.0"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # quieter log
        if self.path.startswith("/api/"):
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    # -- helpers

    def _send(self, code, body, ctype, extra=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, code, obj):
        self._send(
            code,
            json.dumps(obj, ensure_ascii=False),
            "application/json; charset=utf-8",
            {"Cache-Control": "no-store"},
        )

    def _file(self, path, cache=True, revalidate=False):
        """Answer with the file of `path`.

        `revalidate` is for a URL whose file can change behind a stable name.
        The bottle of a slug is such a file: a patch REPLACES it, and the URL
        `/img/bottle?slug=<slug>` stays the same. Such an answer carries an
        `ETag` and `Cache-Control: no-cache`. `no-cache` does not stop the
        cache. It stops the use of a cached copy without a question to the
        server. The browser asks with `If-None-Match` and gets `304` while the
        file is the same, and the new file in the first answer after a patch.

        Without this header a new patch stays invisible for 24 hours, because
        `max-age=86400` lets the browser answer from its own cache and the URL
        gives it no reason to ask again.
        """
        if not path or not os.path.isfile(path):
            self._send(404, "not found", "text/plain; charset=utf-8")
            return
        etag = None
        if revalidate:
            try:
                st = os.stat(path)
                etag = '"%x-%x"' % (int(st.st_mtime), st.st_size)
            except OSError:
                etag = None
        if etag and self.headers.get("If-None-Match") == etag:
            self.send_response(304)
            self.send_header("Cache-Control", "no-cache")
            self.send_header("ETag", etag)
            self.end_headers()
            return
        try:
            with open(path, "rb") as f:
                body = f.read()
        except OSError as exc:
            self._send(500, f"cannot read: {exc}", "text/plain; charset=utf-8")
            return
        if etag:
            extra = {"Cache-Control": "no-cache", "ETag": etag}
        else:
            extra = {"Cache-Control":
                     "public, max-age=86400" if cache else "no-store"}
        self._send(200, body, guess_type(path), extra)

    # -- routes

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        route = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if route == "/":
            self._send(
                200, PAGE, "text/html; charset=utf-8", {"Cache-Control": "no-store"}
            )
        elif route == "/api/rows":
            with _lock:
                have = {r["slug"] for r in _rows}
                extra = catalog_only_rows(getattr(self.server, "catalog", {}), have,
                                          getattr(self.server, "groups", {}))
                self._json(200, {"rows": _rows + extra, "labels": _state["labels"],
                                 "wines": _state["wines"],
                                 "excluded": _excluded,
                                 "inbox": scan_inbox(),
                                 "groups": getattr(self.server, "groups", {}),
                                 "slugs": sorted(self.server.catalog)})
        elif route == "/api/patched":
            # The slugs whose catalogue photo comes from `patch_dir`. The runs
            # page holds a slug alone, not a row, so it reads this list to mark
            # a candidate image `patched`.
            self._json(200, {"dir": PATCH_DIR or "", "slugs": sorted(_patches)})
        elif route == "/api/checks":
            self._json(200, {"checks": [
                {k: c[k] for k in ("id", "title", "help")} for c in CHECKS]})
        elif route == "/api/state":
            with _lock:
                self._json(200, {"labels": _state["labels"], "wines": _state["wines"],
                                 "excluded": _excluded, "counts": count_state()})
        elif route == "/runs":
            self._send(200, PAGE_RUNS, "text/html; charset=utf-8",
                       {"Cache-Control": "no-store"})
        elif route == "/clusters":
            self._send(200, PAGE_CLUSTERS, "text/html; charset=utf-8",
                       {"Cache-Control": "no-store"})
        elif route == "/api/clusters":
            self._clusters_view()
        elif route == "/docs":
            self._send(200, PAGE_DOCS, "text/html; charset=utf-8",
                       {"Cache-Control": "no-store"})
        elif route == "/openapi.yaml":
            self._spec_yaml()
        elif route == "/openapi.json":
            self._spec_json()
        elif route == "/api/runs":
            self._json(200, {"runs": [run_head(r) for r in run_dirs()]})
        elif route == "/api/run":
            self._run_view(query)
        elif route == "/api/reload":
            self._reload()
        elif route == "/api/suggest":
            slug = (query.get("slug") or [""])[0]
            group_of = {sl: g["id"] for g in getattr(self.server, "groups", {}).values()
                        for sl in g["slugs"]}
            self._json(200, {"slug": slug, "targets": suggest_targets(
                slug, getattr(self.server, "catalog", {}), group_of,
                getattr(self.server, "groups", {}))})
        elif route.startswith("/api/v1/"):
            self._api_get(route[len("/api/v1/"):], query)
        elif route == "/img/bottle":
            # A patch can replace this file while the URL stays the same.
            # `kind` selects the package picture, the label crop, or the box
            # crop. A wine with no crop of that kind answers with its package
            # picture, so a view never holds a hole.
            slug = (query.get("slug") or [""])[0]
            kind = (query.get("kind") or ["package"])[0]
            self._file(self._picture_path(slug, kind), revalidate=True)
        elif route == "/img/photo":
            slug = (query.get("slug") or [""])[0]
            fn = (query.get("file") or [""])[0]
            self._file(self._photo_path(slug, fn))
        elif route == "/img/inbox":
            self._file(self._inbox_path((query.get("file") or [""])[0]))
        elif route == "/img/runphoto":
            run_id = (query.get("id") or [""])[0]
            fn = (query.get("file") or [""])[0]
            self._file(self._run_photo_path(run_id, fn))
        else:
            self._send(404, "not found", "text/plain; charset=utf-8")

    do_HEAD = do_GET

    def do_POST(self):
        parsed = urllib.parse.urlsplit(self.path)
        route = parsed.path
        if route == "/api/upload":
            self._upload(urllib.parse.parse_qs(parsed.query))
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8"))
        except ValueError:
            self._json(400, {"error": "bad json"})
            return

        if route == "/api/label":
            self._set_label(body)
        elif route == "/api/reassign":
            self._set_reassign(body)
        elif route == "/api/copy":
            self._set_copy(body)
        elif route == "/api/validate":
            self._validate(body)
        elif route == "/api/comment":
            self._set_comment(body)
        elif route == "/api/wine-comment":
            self._set_wine_comment(body)
        elif route == "/api/group":
            self._group(body)
        elif route == "/api/exclude":
            self._set_excluded(body)
        elif route == "/api/mark-delete":
            self._set_delete(body)
        elif route == "/api/apply-moves":
            self._apply_moves(body)
        elif route == "/api/fetch-image":
            self._fetch(body)
        elif route.startswith("/api/v1/"):
            self._api_post(route[len("/api/v1/"):], body)
        elif route == "/api/labels":
            self._set_many(body)
        else:
            self._json(404, {"error": "unknown route"})

    # -- route bodies

    def _spec_yaml(self):
        """Answer the OpenAPI document as it is written, in YAML."""
        if not os.path.isfile(SPEC_FILE):
            self._json(404, {"error": "docs/openapi.yaml is not present"})
            return
        try:
            with open(SPEC_FILE, "rb") as f:
                body = f.read()
        except OSError as exc:
            self._json(500, {"error": "cannot read the document: %s" % exc})
            return
        self._send(200, body, "application/yaml; charset=utf-8",
                   {"Cache-Control": "no-store"})

    def _spec_json(self):
        """Answer the OpenAPI document as JSON.

        The document is written in YAML, because the descriptions are long. Most
        tools ask for JSON, so this route converts it. PyYAML is always present: the
        tool reads `config.yaml` with it and cannot start without it.
        """
        if not os.path.isfile(SPEC_FILE):
            self._json(404, {"error": "docs/openapi.yaml is not present"})
            return
        try:
            with open(SPEC_FILE, encoding="utf-8") as f:
                spec = yaml.safe_load(f)
        except (OSError, ValueError, yaml.YAMLError) as exc:
            self._json(500, {"error": "cannot read the document: %s" % exc})
            return
        self._json(200, spec)

    def _clusters_view(self):
        """Answer the cluster file of `scripts/10_clusters.py` and one record per card.

        The route reads the file at each request, so a new build needs no restart.
        A card record holds the label counts of the dataset in use. The route writes
        nothing.
        """
        path = common.CLUSTERS_FILE
        if not os.path.isfile(path):
            self._json(200, {"exists": False, "file": path, "clusters": [],
                             "cards": {}, "hint": "python3 scripts/10_clusters.py"})
            return
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as exc:
            self._json(500, {"error": "cannot read %s: %s" % (path, exc)})
            return
        catalog = getattr(self.server, "catalog", {})
        with _lock:
            rows = {r["slug"]: r for r in _rows}
            labels = _state["labels"]
            cards = {}
            for cluster in data.get("clusters") or []:
                for slug in cluster.get("slugs") or []:
                    if slug in cards:
                        continue
                    rec = catalog.get(slug) or {}
                    row = rows.get(slug)
                    counts = {"positive": 0, "negative": 0, "variant": 0,
                              "unusable": 0, "unlabelled": 0}
                    for p in (row or {}).get("photos", []):
                        label = ((labels.get(slug) or {}).get(p["file"]) or {}).get("label")
                        counts[label if label in counts else "unlabelled"] += 1
                    cards[slug] = {
                        "name": rec.get("name") or "",
                        "producer": rec.get("producer") or "",
                        "category": rec.get("category") or "",
                        "grapes": rec.get("grapes") or "",
                        "page_url": rec.get("page_url") or "",
                        "in_catalog": bool(rec),
                        "patched": slug in _patches,
                        "has_label": slug in _labels,
                        "in_review": row is not None,
                        "excluded": slug in _excluded,
                        "photos": counts,
                    }
        self._json(200, {"exists": True, "file": path, "dataset": common.DATASET,
                         **data, "cards": cards})

    def _run_view(self, query):
        """Answer the metrics and the filtered rows of one run."""
        run_id = (query.get("id") or [""])[0]
        if not run_path(run_id, "run.json"):
            self._json(400, {"error": "bad run id"})
            return
        if run_id not in run_dirs():
            self._json(404, {"error": "unknown run"})
            return
        mode = (query.get("filter") or ["all"])[0]
        text = (query.get("q") or [""])[0]
        try:
            limit = max(1, min(int((query.get("limit") or ["200"])[0]), 1000))
            offset = max(0, int((query.get("offset") or ["0"])[0]))
        except ValueError:
            self._json(400, {"error": "limit and offset MUST be numbers"})
            return
        sort = (query.get("sort") or ["manifest"])[0]
        if sort not in ROW_SORTS:
            self._json(400, {"error": "sort MUST be one of %s" % ", ".join(ROW_SORTS)})
            return
        rows, total = run_rows(run_id, mode, text, limit, offset, sort)
        self._json(200, {
            "run": _read_json(run_path(run_id, "run.json")) or {},
            "metrics": _read_json(run_path(run_id, "metrics.json")) or {},
            "head": run_head(run_id),
            "filter": mode, "sort": sort,
            "total": total, "offset": offset, "limit": limit,
            "rows": rows,
        })

    def _rebuild_rows(self):
        """Read the groups again, build the rows again, and answer both."""
        global _rows, _patches, _crops, _labels, _label_boxes
        # A patch file that was added while the tool ran is read here, so the
        # reviewer needs no restart to see the corrected photo. A label crop and
        # a cropped photo that a new build wrote are read here for the same reason.
        _patches = load_patches()
        _crops = load_crops()
        _labels, _label_boxes = load_label_crops()
        group_of, groups = load_variants()
        self.server.groups = groups
        rows = build_rows(getattr(self.server, "catalog", {}), group_of)
        with _lock:
            _rows = rows
        return rows, groups

    def _reload(self):
        rows, _groups = self._rebuild_rows()
        with _lock:
            self._json(200, {"rows": rows, "labels": _state["labels"],
                             "wines": _state["wines"], "excluded": _excluded,
                             "inbox": scan_inbox()})

    def _group(self, body):
        """Join two wines into one variant group.

        The write is one pair in `manual-groups.json`. A group is a connected
        component over the generated groups and these pairs, so a wine that is in
        no group takes the group of the other wine.

        Two wines that are already in two groups are refused. A merge of two
        groups is a larger decision than this button states, and it cannot be
        undone by taking one pair away.
        """
        slug = (body.get("slug") or "").strip()
        target = (body.get("target") or "").strip()
        catalog = getattr(self.server, "catalog", {})
        if not slug or not target:
            self._json(400, {"error": "slug and target are required"})
            return
        if slug == target:
            self._json(400, {"error": "a wine cannot be grouped with itself"})
            return
        if slug not in catalog:
            self._json(400, {"error": "unknown slug: %s" % slug})
            return
        if target not in catalog:
            self._json(400, {"error": "unknown target slug: %s" % target})
            return
        groups = getattr(self.server, "groups", {})
        gof = {sl: g["id"] for g in groups.values() for sl in g["slugs"]}
        ga, gb = gof.get(slug), gof.get(target)
        if ga and ga == gb:
            self._json(200, {"ok": True, "changed": False, "group": ga,
                             "note": "the two wines are already in one group"})
            return
        if ga and gb:
            self._json(409, {"error":
                "both wines are already in a group: %s holds %d wines, %s holds "
                "%d. A merge of two groups is not allowed here." % (
                    ga, len(groups[ga]["slugs"]), gb, len(groups[gb]["slugs"]))})
            return
        pairs = load_manual_pairs()
        if not any({p["a"], p["b"]} == {slug, target} for p in pairs):
            pairs.append({"a": slug, "b": target,
                          "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
            save_manual_pairs(pairs)
        rows, groups = self._rebuild_rows()
        gid = next((g["id"] for g in groups.values() if slug in g["slugs"]), None)
        with _lock:
            self._json(200, {"ok": True, "changed": True, "group": gid,
                             "rows": rows, "labels": _state["labels"],
                             "wines": _state["wines"], "excluded": _excluded,
                             "groups": groups,
                             "slugs": sorted(catalog)})

    def _bottle_path(self, slug):
        return bottle_path(slug, getattr(self.server, "catalog", {}))

    def _picture_path(self, slug, kind):
        """The file of one slug for one kind. An unknown kind gives the package."""
        if kind not in IMAGE_KINDS:
            kind = "package"
        return picture_path(slug, getattr(self.server, "catalog", {}), kind)

    def _inbox_path(self, fn):
        """Return the path of one file of the inbox of `my/`, or None.

        The function refuses a name that holds a path separator or a parent
        reference, a name that is a directory, and a file that is not present.
        """
        if not fn or os.path.basename(fn) != fn:
            return None
        path = os.path.join(MY, fn)
        return path if os.path.isfile(path) else None

    def _run_photo_path(self, run_id, rel):
        """Return the path of one photo of a run of a plain directory, or None.

        `scripts/match_run.py --photos-dir DIR` matches the photos of a directory
        that stands outside `my/`. The run records that directory in `run.json`,
        in the field `options.photos_dir`, and `results.jsonl` holds the path of
        each photo against it.

        The function refuses a run id that holds a path separator, a run that
        names no directory, and a path that leaves that directory.
        """
        if not rel:
            return None
        meta = _read_json(run_path(run_id, "run.json")) or {}
        base = ((meta.get("options") or {}).get("photos_dir") or "").strip()
        if not base:
            return None
        base = os.path.realpath(base)
        path = os.path.realpath(os.path.join(base, rel))
        if not path.startswith(base + os.sep):
            return None
        return path if os.path.isfile(path) else None

    def _photo_path(self, slug, fn):
        """Return the path of one candidate photo, or None.

        The function returns None when the name holds a path separator or a
        parent reference, when the resolved path leaves `my/`, or when the file
        is not present. A label MUST name a photo that exists.
        """
        if not slug or not fn:
            return None
        if os.path.basename(slug) != slug or os.path.basename(fn) != fn:
            return None
        path = os.path.realpath(os.path.join(MY, slug, fn))
        if not path.startswith(os.path.realpath(MY) + os.sep):
            return None
        if not os.path.isfile(path):
            return None
        return path

    def _entry(self, slug, fn, field, value):
        """Set or clear one field of one photo entry. The caller MUST hold `_lock`.

        An entry can hold a `label`, a `reassign_to`, or both. Clearing one field
        MUST NOT drop the other, so the entry is edited in place and is removed
        only when no field is left.
        """
        photos = _state["labels"].setdefault(slug, {})
        entry = photos.get(fn) or {}
        if value in (None, ""):
            entry.pop(field, None)
        else:
            entry[field] = value
        if entry.keys() <= {"ts"}:
            photos.pop(fn, None)
        else:
            entry["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
            photos[fn] = entry
        if not photos:
            _state["labels"].pop(slug, None)

    def _apply(self, slug, fn, label):
        """Store or clear one label. The caller MUST hold `_lock`."""
        if label not in LABELS + (None, ""):
            raise ValueError(
                "label MUST be one of %s, or empty" % ", ".join(repr(x) for x in LABELS)
            )
        # A photo of the NULL wine is already judged by its place: it shows no
        # card of the catalogue. `positive` confirms that, and `unusable` takes
        # the photo out of the set. The other two labels judge a photo against a
        # wine, and NULL is not a wine.
        if slug == NULL_SLUG and label and label not in NULL_LABELS:
            raise ValueError(
                "a photo of the NULL wine takes %s alone" % " or ".join(NULL_LABELS))
        self._entry(slug, fn, "label", label)

    def _apply_reassign(self, slug, fn, to):
        """Record that the photo belongs to another slug. The file is not moved.

        `scripts/09_apply_moves.py` moves the files later, on one command.
        """
        # The NULL wine is a target although the catalogue does not hold it and
        # its directory may not be made yet.
        if (to and to != NULL_SLUG and to not in self.server.catalog
                and not os.path.isdir(os.path.join(MY, os.path.basename(to)))):
            raise ValueError("unknown target slug: %s" % to)
        if to == slug:
            raise ValueError("the target slug is the slug of the photo")
        self._entry(slug, fn, "reassign_to", to)

    def _apply_copy(self, slug, fn, to):
        """Record that the photo is a photo of another slug too.

        The source photo stays where it is, with its label and its comment. The
        file is not copied here. `POST /api/apply-moves` and
        `scripts/09_apply_moves.py` copy it later, on one command.
        """
        # A copy states that the photo shows a SECOND wine. NULL is not a wine,
        # so a copy to NULL states nothing. A photo that shows no card of the
        # catalogue is moved there, not copied there.
        if to == NULL_SLUG:
            raise ValueError("a photo cannot be copied to the NULL wine; move it")
        if to and to not in self.server.catalog and not os.path.isdir(
                os.path.join(MY, os.path.basename(to))):
            raise ValueError("unknown target slug: %s" % to)
        if to == slug:
            raise ValueError("the target slug is the slug of the photo")
        self._entry(slug, fn, "copy_to", to)

    def _apply_delete(self, slug, fn, on):
        """Mark or unmark one photo for deletion. The file is not touched here.

        `_apply_moves` moves every marked photo into `my/trash/` later, on one
        command. The caller MUST hold `_lock`.
        """
        self._entry(slug, fn, "delete", True if on else None)

    def _set_label(self, body):
        slug = body.get("slug") or ""
        fn = body.get("file") or ""
        label = body.get("label")
        if not self._photo_path(slug, fn):
            self._json(400, {"error": "unknown photo"})
            return
        try:
            with _lock:
                self._apply(slug, fn, label)
                save_state()
                counts = count_state()
        except (ValueError, OSError) as exc:
            self._json(400, {"error": str(exc)})
            return
        self._json(200, {"ok": True, "counts": counts})

    def _apply_comment(self, slug, fn, text):
        """Store or clear the comment of one photo."""
        if text and len(text) > COMMENT_MAX:
            raise ValueError("comment is longer than %d characters" % COMMENT_MAX)
        self._entry(slug, fn, "comment", text)

    def _set_comment(self, body):
        slug = body.get("slug") or ""
        fn = body.get("file") or ""
        text = body.get("text")
        text = text.strip() if isinstance(text, str) else ""
        if not self._photo_path(slug, fn):
            self._json(400, {"error": "unknown photo"})
            return
        try:
            with _lock:
                self._apply_comment(slug, fn, text)
                save_state()
                counts = count_state()
        except (ValueError, OSError) as exc:
            self._json(400, {"error": str(exc)})
            return
        self._json(200, {"ok": True, "counts": counts})

    def _set_wine_comment(self, body):
        """Store or clear the note about a whole wine, not about one photo."""
        slug = body.get("slug") or ""
        text = body.get("text")
        text = text.strip() if isinstance(text, str) else ""
        if not self._known_slug(slug):
            self._json(400, {"error": "unknown wine slug"})
            return
        if len(text) > COMMENT_MAX:
            self._json(400, {"error": "the note is longer than %d characters"
                                      % COMMENT_MAX})
            return
        try:
            with _lock:
                if text:
                    _state["wines"][slug] = {
                        "comment": text,
                        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    }
                else:
                    _state["wines"].pop(slug, None)
                save_state()
                counts = count_state()
        except OSError as exc:
            self._json(400, {"error": str(exc)})
            return
        self._json(200, {"ok": True, "counts": counts})

    def _set_excluded(self, body):
        """Exclude one wine slug, or take the exclusion away.

        Body: `{slug, excluded, reason}`. `excluded` is a boolean and defaults to
        true. `reason` states why the slug is excluded. The photos of an excluded
        slug MUST NOT be used for benchmarking.
        """
        slug = body.get("slug") or ""
        want = body.get("excluded")
        want = True if want is None else bool(want)
        reason = body.get("reason")
        reason = reason.strip() if isinstance(reason, str) else ""
        if not self._known_slug(slug):
            self._json(400, {"error": "unknown wine slug"})
            return
        if len(reason) > EXCLUDE_REASON_MAX:
            self._json(400, {"error": "the reason is longer than %d characters"
                                      % EXCLUDE_REASON_MAX})
            return
        if want and not reason:
            self._json(400, {"error": "a reason is needed to exclude a slug"})
            return
        try:
            with _lock:
                if want:
                    _excluded[slug] = {
                        "reason": reason,
                        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    }
                else:
                    _excluded.pop(slug, None)
                save_excluded()
                entry = _excluded.get(slug)
                count = len(_excluded)
        except OSError as exc:
            self._json(400, {"error": str(exc)})
            return
        self._json(200, {"ok": True, "slug": slug, "excluded": want,
                         "entry": entry, "count": count})

    def _set_delete(self, body):
        """Mark one photo for deletion, or take the mark away.

        Body: `{slug, file, delete}`. `delete` is a boolean and defaults to true.
        The answer carries the new counts, so the page can show the pending work.
        """
        slug = body.get("slug") or ""
        fn = body.get("file") or ""
        on = body.get("delete")
        on = True if on is None else bool(on)
        if not self._photo_path(slug, fn):
            self._json(400, {"error": "unknown photo"})
            return
        with _lock:
            self._apply_delete(slug, fn, on)
            save_state()
            counts = count_state()
        self._json(200, {"ok": True, "slug": slug, "file": fn,
                         "delete": on, "counts": counts})

    def _set_reassign(self, body):
        slug = body.get("slug") or ""
        fn = body.get("file") or ""
        to = (body.get("to") or "").strip()
        if not self._photo_path(slug, fn):
            self._json(400, {"error": "unknown photo"})
            return
        try:
            with _lock:
                self._apply_reassign(slug, fn, to)
                save_state()
                counts = count_state()
        except (ValueError, OSError) as exc:
            self._json(400, {"error": str(exc)})
            return
        self._json(200, {"ok": True, "counts": counts})

    def _set_copy(self, body):
        slug = body.get("slug") or ""
        fn = body.get("file") or ""
        to = (body.get("to") or "").strip()
        if not self._photo_path(slug, fn):
            self._json(400, {"error": "unknown photo"})
            return
        try:
            with _lock:
                self._apply_copy(slug, fn, to)
                save_state()
                counts = count_state()
        except (ValueError, OSError) as exc:
            self._json(400, {"error": str(exc)})
            return
        self._json(200, {"ok": True, "counts": counts})

    def _validate(self, body):
        """Run the chosen checks and answer the findings and the failing wines.

        The checks read the files of the whole photo set. A size check takes about
        three seconds, and `candidate_is_catalog_photo` reads the pixels and takes
        about 70 seconds. The lock is held only long enough to take the rows and the
        labels, so a label of the reviewer is not blocked while a check runs.
        """
        want = body.get("checks")
        known = {c["id"]: c for c in CHECKS}
        if want is None:
            want = list(known)
        if not isinstance(want, list) or not all(isinstance(x, str) for x in want):
            self._json(400, {"error": "checks MUST be a list of check ids"})
            return
        if not want:
            self._json(400, {"error": "no check was chosen"})
            return
        unknown = sorted({x for x in want if x not in known})
        if unknown:
            self._json(400, {"error": "unknown check: %s. The known checks are %s"
                             % (", ".join(unknown), ", ".join(sorted(known)))})
            return

        started = time.time()
        with _lock:
            rows = list(_rows)
            labels = {slug: dict(photos)
                      for slug, photos in _state["labels"].items()}
        groups = getattr(self.server, "groups", {})
        catalog = getattr(self.server, "catalog", {})
        findings = []
        for cid in want:
            findings.extend(known[cid]["run"](rows, labels, groups, catalog))
        slugs = sorted({p["slug"] for f in findings for p in f.get("photos", ())}
                       | {x for f in findings for x in f.get("slugs", ())})
        self._json(200, {
            "ok": True,
            "ran": want,
            "wines": len(rows),
            "photos": sum(len(r["photos"]) for r in rows),
            "seconds": round(time.time() - started, 2),
            "findings": findings,
            "slugs": slugs,
        })

    # ---- the API for an agent -------------------------------------------

    def _api_get(self, tail, query):
        catalog = getattr(self.server, "catalog", {})
        groups = getattr(self.server, "groups", {})
        one = (query.get("q") or [""])[0].strip().lower()

        if tail == "stats":
            with _lock:
                work = [r for r in _rows if not r.get("null_row")]
                self._json(200, {
                    "wines": len(work),
                    "photos": sum(len(r["photos"]) for r in work),
                    # The photos that match no card of the catalogue. They are no
                    # labelling work, so they stand apart from `photos`.
                    "no_match_photos": sum(len(r["photos"]) for r in _rows
                                           if r.get("null_row")),
                    "excluded_wines": sum(1 for r in _rows if r["slug"] in _excluded),
                    "excluded_photos": sum(len(r["photos"]) for r in _rows
                                           if r["slug"] in _excluded),
                    "counts": count_state(),
                    "variant_groups": len(groups),
                })
            return

        if tail == "wines":
            mode = (query.get("filter") or ["all"])[0]
            limit = max(1, min(int((query.get("limit") or ["50"])[0]), 500))
            offset = max(0, int((query.get("offset") or ["0"])[0]))
            # An excluded wine is out of the benchmark. The list leaves it out,
            # because an agent MUST NOT work on photos that nothing uses.
            keep_excluded = (query.get("include_excluded") or ["0"])[0] in (
                "1", "true", "yes")
            with _lock:
                # The NULL wine is no card of the catalogue and holds no labelling
                # work, so it stays out of the queues of an agent.
                # `GET /api/v1/wine/__null__` still answers.
                src = [r for r in _rows if not r.get("null_row")]
                if mode in CATALOG_SCOPE_FILTERS:
                    src += catalog_only_rows(catalog, {r["slug"] for r in _rows},
                                             groups)
                rows = [wine_view(r, catalog, groups) for r in src]
            if not keep_excluded:
                rows = [w for w in rows if not w["excluded"]]
            rows = [w for w in rows if api_filter(w, mode)]
            if one:
                rows = [w for w in rows if one in
                        (w["slug"] + " " + w["name"] + " " + w["producer"]).lower()]
            self._json(200, {"total": len(rows), "offset": offset,
                             "limit": limit, "wines": rows[offset:offset + limit]})
            return

        if tail.startswith("wine/"):
            slug = urllib.parse.unquote(tail[len("wine/"):]).rstrip("/")
            want_photos = slug.endswith("/photos")
            if want_photos:
                slug = slug[:-len("/photos")]
            with _lock:
                row = next((r for r in _rows if r["slug"] == slug), None)
                if row is None:
                    self._json(404, {"error": "unknown wine slug"})
                    return
                view = wine_view(row, catalog, groups, full=True)
            if want_photos:
                want = (query.get("label") or [""])[0]
                photos = view["photos"]
                if want:
                    photos = [p for p in photos if p["label"] == want]
                self._json(200, {"slug": slug, "photos": photos})
            else:
                self._json(200, view)
            return

        self._json(404, {"error": "unknown API path: %s" % tail})

    def _api_post(self, tail, body):
        if tail == "propose":
            self._propose(body)
        else:
            self._json(404, {"error": "unknown API path: %s" % tail})

    def _propose(self, body):
        """Add a photo that an agent found, as a proposal, not as a label."""
        slug = body.get("slug") or ""
        url = (body.get("url") or "").strip()
        proposed = body.get("proposed") or "positive"
        if not self._known_slug(slug):
            self._json(400, {"error": "unknown wine slug"})
            return
        if slug == NULL_SLUG:
            self._json(400, {"error": "the NULL wine takes no proposal; a reviewer "
                                      "moves a photo there"})
            return
        if proposed not in LABELS:
            self._json(400, {"error": "proposed MUST be one of %s"
                                      % ", ".join(LABELS)})
            return
        if not url:
            self._json(400, {"error": "no url"})
            return
        try:
            conf = float(body.get("confidence", 0) or 0)
        except (TypeError, ValueError):
            self._json(400, {"error": "confidence MUST be a number"})
            return
        if not 0 <= conf <= 1:
            self._json(400, {"error": "confidence MUST be between 0 and 1"})
            return
        try:
            data, ctype = fetch_image(url)
            name = os.path.basename(urllib.parse.urlsplit(url).path)
            fn, photos = self._store_image(slug, data, ctype, name, tag="agent")
        except ValueError as exc:
            self._json(400, {"error": str(exc)})
            return
        except Exception as exc:  # noqa: BLE001
            self._json(400, {"error": "%s: %s" % (type(exc).__name__, exc)})
            return
        with _lock:
            entry = {
                "proposed": proposed,
                "by": body.get("by") or "agent",
                "confidence": round(conf, 4),
                "source_url": body.get("source_url") or url,
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            }
            note = (body.get("comment") or "").strip()
            if note:
                entry["comment"] = note[:COMMENT_MAX]
            _state["labels"].setdefault(slug, {})[fn] = entry
            save_state()
            counts = count_state()
        self._json(200, {"ok": True, "slug": slug, "file": fn,
                         "photos": photos, "counts": counts})

    def _apply_moves(self, body=None):
        """Copy, move, and delete every marked photo, then rebuild the rows.

        The three actions run on one command, because the page offers one button.
        They run in this order, because a move takes the source file away and a
        copy reads it: copy, move, delete.

        The body MAY hold `inbox`: a list of `{"file": <name>, "to": <slug>}`.
        Each pair moves one file of the inbox of `my/` into the directory of that
        wine. The sideboard holds these pairs in the browser alone, so they come
        with the request and not from the label file. They run last, after the
        photos that already belong to a wine.
        A photo that carries both a `reassign_to` and a `delete` is deleted and is
        not moved; `plan_moves` drops it. A `delete` drops a `copy_to` in the same
        way.
        """
        global _rows
        try:
            with _lock:
                cp_planned, cp_bad = plan_copies(_state["labels"])
                copied, cp_renamed = perform_copies(cp_planned, _state["labels"])
                planned, done, bad = plan_moves(_state["labels"])
                moved, renamed = perform_moves(planned, _state["labels"])
                renamed = cp_renamed + renamed
                del_planned, del_gone = plan_deletes(_state["labels"])
                deleted, del_failed = perform_deletes(
                    del_planned, del_gone, _state["labels"])
                in_planned, in_bad = plan_inbox_moves(
                    ((body or {}).get("inbox") or []),
                    getattr(self.server, "catalog", {}))
                in_moved, in_renamed = perform_inbox_moves(
                    in_planned, _state["labels"])
                renamed = renamed + in_renamed
                save_state()
                counts = count_state()
        except (OSError, ValueError) as exc:
            self._json(500, {"error": str(exc)})
            return
        rows = build_rows(getattr(self.server, "catalog", {}),
                          load_variants()[0])
        with _lock:
            _rows = rows
            prune_state(_rows)
            save_state()
            counts = count_state()
            self._json(200, {
                "ok": True,
                "moved": [{"from": a, "file": b, "to": c, "as": d}
                          for a, b, c, d in moved],
                "already_done": len(done),
                "failed": [{"from": a, "file": b, "to": c, "why": w}
                           for a, b, c, w in bad],
                "copied": [{"from": a, "file": b, "to": c, "as": d}
                           for a, b, c, d in copied],
                "copy_failed": [{"from": a, "file": b, "to": c, "why": w}
                                for a, b, c, w in cp_bad],
                "renamed": [{"from": a, "to": b} for a, b in renamed],
                "deleted": [{"slug": a, "file": b, "to": c}
                            for a, b, c in deleted],
                "delete_failed": [{"slug": a, "file": b, "why": w}
                                  for a, b, w in del_failed],
                "delete_gone": len(del_gone),
                "inbox_moved": [{"file": a, "to": b, "as": c} for a, b, c in in_moved],
                "inbox_failed": [{"file": a, "to": b, "why": w}
                                 for a, b, w in in_bad],
                "inbox": scan_inbox(),
                "rows": _rows, "labels": _state["labels"], "counts": counts,
            })

    def _store_image(self, slug, body, ctype, name="", tag="manual"):
        """Write one picture into `my/<slug>/`. Return (file name, photo list)."""
        if not body or len(body) > UPLOAD_MAX:
            raise ValueError("the picture is empty or larger than %d bytes"
                             % UPLOAD_MAX)
        ctype = sniff_image_type(body, name) or ctype
        if ctype not in UPLOAD_TYPES:
            raise ValueError("not an image type: %s" % (ctype or "none"))
        ext = os.path.splitext(name)[1].lower().split("?")[0]
        if ext not in UPLOAD_TYPES.values():
            ext = UPLOAD_TYPES[ctype]

        with _lock:
            d = os.path.join(MY, slug)
            # A catalogue wine that gets its first photo has no directory yet.
            os.makedirs(d, exist_ok=True)
            ranks = [int(m.group(1)) for m in
                     (RANK_RE.match(f) for f in os.listdir(d)) if m]
            fn = free_name(d, "%02d_%s%s" % (max(ranks, default=0) + 1, tag, ext))
            tmp = os.path.join(d, "." + fn + ".part")
            try:
                with open(tmp, "wb") as f:
                    f.write(body)
                os.replace(tmp, os.path.join(d, fn))
            except OSError:
                if os.path.exists(tmp):
                    os.unlink(tmp)
                raise
            row = next((r for r in _rows if r["slug"] == slug), None)
            if row is None:
                # The wine held no photo until now, so it was a catalogue-only row
                # and not a row of the review set. It is a review wine from now on.
                groups = getattr(self.server, "groups", {})
                group_of = {sl: g["id"] for g in groups.values()
                            for sl in g["slugs"]}
                row = build_row(slug, getattr(self.server, "catalog", {}), group_of)
                _rows.append(row)
                _rows.sort(key=lambda r: r["slug"])
            else:
                row["photos"] = [
                    {"file": f, "conf": int(NAME_RE.match(f).group(2))
                     if NAME_RE.match(f) else None}
                    for f in scan_photos(slug)
                ]
            return fn, row["photos"]

    def _known_slug(self, slug):
        """Is this a wine of this tool?

        A directory in `my/` is one. A card of the catalogue is one too, although
        it holds no directory yet: a catalogue card with no candidate photo is a
        row of the table, and a picture MAY be dropped on it. The directory is
        made by the write.
        """
        if os.path.basename(slug) != slug or not slug or slug.startswith("."):
            return False
        return (slug == NULL_SLUG
                or os.path.isdir(os.path.join(MY, slug))
                or slug in getattr(self.server, "catalog", {}))

    def _upload(self, query):
        """Take one dropped file and add it to the photos of one wine."""
        slug = (query.get("slug") or [""])[0]
        name = (query.get("name") or [""])[0]
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip()
        length = int(self.headers.get("Content-Length") or 0)

        if not self._known_slug(slug):
            self._json(400, {"error": "unknown wine slug"})
            return
        if length <= 0 or length > UPLOAD_MAX:
            self._json(400, {"error": "the file is empty or larger than %d bytes"
                                      % UPLOAD_MAX})
            return
        body = self.rfile.read(length)
        try:
            fn, photos = self._store_image(slug, body, ctype, name)
        except (ValueError, OSError) as exc:
            self._json(400, {"error": str(exc)})
            return
        self._json(200, {"ok": True, "slug": slug, "file": fn, "photos": photos})

    def _fetch(self, body):
        """Take a picture address dragged from another tab and fetch it here.

        A drag from another browser tab hands over an address, not a file. The
        browser cannot read the bytes of another site, so the server fetches the
        picture.
        """
        slug = body.get("slug") or ""
        url = (body.get("url") or "").strip()
        if not self._known_slug(slug):
            self._json(400, {"error": "unknown wine slug"})
            return
        if not url:
            self._json(400, {"error": "no address"})
            return
        try:
            data, ctype = fetch_image(url)
            name = os.path.basename(urllib.parse.urlsplit(url).path)
            fn, photos = self._store_image(slug, data, ctype, name)
        except ValueError as exc:
            self._json(400, {"error": str(exc)})
            return
        except Exception as exc:  # noqa: BLE001 - any network or decode failure
            self._json(400, {"error": "%s: %s" % (type(exc).__name__, exc)})
            return
        self._json(200, {"ok": True, "slug": slug, "file": fn, "photos": photos,
                         "url": url})

    def _set_many(self, body):
        items = body.get("items") or []
        if not isinstance(items, list):
            self._json(400, {"error": "items MUST be a list"})
            return
        skipped = 0
        try:
            with _lock:
                for item in items:
                    slug = item.get("slug") or ""
                    fn = item.get("file") or ""
                    if not self._photo_path(slug, fn):
                        skipped += 1
                        continue
                    self._apply(slug, fn, item.get("label"))
                save_state()
                counts = count_state()
        except (ValueError, OSError) as exc:
            self._json(400, {"error": str(exc)})
            return
        self._json(200, {"ok": True, "counts": counts, "skipped": skipped})


# ---------------------------------------------------------------------- page

THEME_CSS = """:root {
  color-scheme: light dark;
  --bg: #f6f6f4;
  --panel: #ffffff;
  --panel-2: #efefec;
  --text: #17170f;
  --muted: #62625a;
  --line: #d8d8d2;
  --accent: #6b4a7a;
  --pos: #1f7a3d;
  --pos-bg: #d9f2e1;
  --neg: #1d5f9c;
  --neg-bg: #d9e8f7;
  --unu: #6a6a62;
  --unu-bg: #e4e4df;
  --var: #9a6b12;
  --var-bg: #f8ecd2;
  --grp-a: #ece4f4;
  --grp-b: #e2eeea;
  --exc: #b3261e;
  --exc-bg: #f7d9d6;
  --shadow: 0 1px 2px rgba(0,0,0,.08);
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #15151a;
    --panel: #1e1e25;
    --panel-2: #26262f;
    --text: #e9e9ee;
    --muted: #9a9aa6;
    --line: #34343f;
    --accent: #b28ec8;
    --pos: #5fd98a;
    --pos-bg: #17351f;
    --neg: #6db6f2;
    --neg-bg: #14283a;
    --unu: #8a8a95;
    --unu-bg: #2a2a30;
    --var: #e0b25c;
    --var-bg: #3a2f14;
    --grp-a: #272132;
    --grp-b: #1d2a28;
    --exc: #ff8a80;
    --exc-bg: #3a1614;
    --shadow: 0 1px 2px rgba(0,0,0,.5);
  }
}
"""

# The mark of a corrected catalogue photo. The review page and the runs page both
# show catalogue bottles, so the rule and the helper stand once here and are
# joined into each page. The colour is the colour of a variant, `--var`, in both
# the light and the dark palette.
PATCH_CSS = """
/* A catalogue photo that comes from `patch_dir` and not from the catalogue
   record. The mark sits ON the image, in the top right corner, because it
   states something about the picture and not about the wine. */
.pic { position: relative; display: block; line-height: 0; }
.pic > .patched {
  position: absolute; top: 3px; right: 3px; z-index: 1; pointer-events: none;
  font: 700 9px/1.25 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  letter-spacing: .03em; text-transform: uppercase; color: var(--var);
  background: var(--var-bg); border: 1px solid var(--var);
  border-radius: 4px; padding: 0 3px;
}
/* A label crop is RGBA and its alpha channel holds the mask. The page puts such
   a picture on white, so a white label edge stays visible in the dark theme. */
.pic img.onwhite, figure img.onwhite { background: #fff; }
/* The picture selector asks for a label crop, and this wine has none. The page
   shows the package picture and marks it. The mark sits in the BOTTOM right
   corner, so it stands beside the `patched` mark and not over it. */
.pic > .nolabel {
  position: absolute; bottom: 3px; right: 3px; z-index: 1; pointer-events: none;
  font: 700 9px/1.25 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  letter-spacing: .03em; text-transform: uppercase; color: var(--muted);
  background: var(--panel-2); border: 1px solid var(--line);
  border-radius: 4px; padding: 0 3px;
}
/* The pickers show a 34 px thumbnail. The word does not fit there, so the mark
   is a dot of the same colour. The tooltip still states what it means. */
.mv-item .pic { flex: none; }
.mv-item .pic > .patched {
  top: 1px; right: 1px; width: 9px; height: 9px; padding: 0;
  border-radius: 50%; font-size: 0; overflow: hidden;
}
.mv-item .pic > .nolabel {
  bottom: 1px; right: 1px; width: 9px; height: 9px; padding: 0;
  border-radius: 50%; font-size: 0; overflow: hidden;
}
"""

# `picHtml` puts one <img> in a positioned box, because an absolute mark needs a
# positioned parent. Every catalogue bottle passes through it.
PATCH_JS = """
const PATCH_TIP = "patched: this catalogue photo is a correction from patch_dir."
  + " The photo of the catalogue record is not used for this wine.";
const NOLABEL_TIP = "no label crop for this wine, so the package picture is shown."
  + " svoe-wino-hackaton/scripts/build_labels.py writes the crops.";
/* `noLabel` is optional. The runs page passes two arguments and gets the old
   behaviour. */
function picHtml(imgHtml, patched, noLabel) {
  return `<div class="pic">${imgHtml}${
    patched ? `<span class="patched" title="${PATCH_TIP}">patched</span>` : ""}${
    noLabel ? `<span class="nolabel" title="${NOLABEL_TIP}">no label</span>` : ""}</div>`;
}
"""


# The page that shows the OpenAPI document. It loads Swagger UI from a CDN, so it
# needs an internet connection. The tool itself does not.
PAGE_DOCS = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Svoe Vino review API</title>
<link rel="stylesheet"
      href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@__V__/swagger-ui.css">
<style>
:root { color-scheme: light dark; }
body { margin: 0; background: #f6f6f4; }
.swagger-ui .topbar { display: none; }
#nav {
  font: 14px/1.4 system-ui, sans-serif;
  padding: 10px 20px; border-bottom: 1px solid #d8d8d2;
}
#nav a { color: #6b4a7a; margin-right: 14px; }
@media (prefers-color-scheme: dark) {
  body { background: #15151a; }
  #nav { border-color: #34343f; }
  #nav a { color: #b28ec8; }
  /* Swagger UI ships no dark theme. The filter turns the light theme around. The
     code blocks are dark already, so a second filter turns those back. */
  #swagger-ui { filter: invert(88%) hue-rotate(180deg); }
  #swagger-ui .microlight { filter: invert(100%) hue-rotate(180deg); }
}
</style>
</head>
<body>
<div id="nav"><a href="/">Review</a><a href="/runs">Runs</a><a
  href="/clusters">Clusters</a><a href="/openapi.yaml">openapi.yaml</a><a href="/openapi.json">openapi.json</a></div>
<div id="swagger-ui"></div>
<script crossorigin
  src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@__V__/swagger-ui-bundle.js">
</script>
<script>
window.onload = function () {
  window.ui = SwaggerUIBundle({
    url: "/openapi.yaml",
    dom_id: "#swagger-ui",
    deepLinking: true,
    tryItOutEnabled: true,
    docExpansion: "list",
    defaultModelsExpandDepth: 0
  });
};
</script>
</body>
</html>
""".replace("__V__", SWAGGER_UI)


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Svoe Vino photo review</title>
<style>
""" + THEME_CSS + PATCH_CSS + r"""* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--text);
  font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
header {
  position: sticky; top: 0; z-index: 10;
  background: var(--panel); border-bottom: 1px solid var(--line);
  padding: 10px 16px; box-shadow: var(--shadow);
}
h1 { font-size: 15px; margin: 0 0 8px; font-weight: 650; letter-spacing: .01em; }
h1 .sub { color: var(--muted); font-weight: 400; }
.head-top { display: flex; align-items: baseline; gap: 14px; }
.head-top h1 { margin-right: auto; }
.nav { display: flex; gap: 6px; flex: none; }
.nav a {
  color: var(--muted); text-decoration: none; font-size: 13px; font-weight: 600;
  padding: 3px 10px; border: 1px solid var(--line); border-radius: 6px;
  background: var(--panel-2);
}
.nav a:hover { color: var(--text); border-color: var(--accent); }
.nav a.on { color: var(--text); border-color: var(--accent); background: var(--panel); }
.bar { display: flex; flex-wrap: wrap; gap: 8px 14px; align-items: center; }
.bar label { color: var(--muted); font-size: 12px; display: flex; gap: 5px; align-items: center; }
select, input[type=search] {
  background: var(--panel-2); color: var(--text); border: 1px solid var(--line);
  border-radius: 6px; padding: 4px 7px; font: inherit; font-size: 13px;
}
input[type=search] { min-width: 210px; }
.progress { margin-left: auto; display: flex; gap: 12px; align-items: center; font-size: 13px; }
.progress b { font-variant-numeric: tabular-nums; }
.meter { width: 150px; height: 7px; border-radius: 4px; background: var(--panel-2);
         border: 1px solid var(--line); overflow: hidden; }
.meter i { display: block; height: 100%; background: var(--accent); width: 0; }
.tag { padding: 1px 6px; border-radius: 999px; font-size: 11px; border: 1px solid var(--line); }
.tag.pos { color: var(--pos); background: var(--pos-bg); border-color: transparent; }
.tag.neg { color: var(--neg); background: var(--neg-bg); border-color: transparent; }
.tag.unu { color: var(--unu); background: var(--unu-bg); border-color: transparent; }
.tag.var { color: var(--var); background: var(--var-bg); border-color: transparent; }
.tag.grp { color: var(--accent); border-color: var(--accent); }
/* The tag `variant group of N` is a button: it shows the group alone. */
button.tag {
  font: inherit; font-size: 11px; line-height: 1.35; cursor: pointer;
  background: none; padding: 1px 6px;
}
button.tag.grp:hover { background: var(--accent); color: var(--panel); }
/* The table shows one variant group. The chip states it and takes it away. It
   stands with the other controls in the header, because that is where a reviewer
   looks for the filter that is on. */
#grp-clear {
  border: 1px solid var(--accent); background: none; color: var(--accent);
  border-radius: 999px; font: inherit; font-size: 12px; line-height: 1.2;
  padding: 3px 10px; cursor: pointer; white-space: nowrap;
}
#grp-clear:hover { background: var(--accent); color: var(--panel); }
#grp-clear[hidden] { display: none; }
#grp-clear b { font-variant-numeric: tabular-nums; }
#pending { display: flex; align-items: center; gap: 6px; font-size: 12px; }
#pending[hidden] { display: none; }
#pending b { color: var(--accent); }
#apply {
  font: inherit; font-size: 11px; font-weight: 650; padding: 3px 10px;
  border-radius: 6px; border: 1px solid var(--accent); cursor: pointer;
  background: var(--accent); color: #fff;
}
#apply:disabled { opacity: .5; cursor: default; }
tr.drop td { box-shadow: inset 0 0 0 2px var(--accent); }
tr.busy { opacity: .6; }

main { padding: 12px 16px 64px; padding-right: 244px; }
/* The sideboard stands over the page at the right edge. The header is sticky and
   spans the whole width, so it MUST keep the same room free; without it the
   sideboard covers the progress of the header. */
header { padding-right: 244px; }
body.side-off #side { display: none; }
body.side-off main, body.side-off header { padding-right: 16px; }
#validate {
  font: inherit; font-size: 12px; padding: 3px 10px; border-radius: 999px;
  border: 1px solid var(--line); background: var(--panel); color: var(--muted);
  cursor: pointer;
}
#validate:hover { border-color: var(--exc); color: var(--text); }
#validate.on { border-color: var(--exc); color: var(--exc); }
#side-toggle {
  font: inherit; font-size: 11px; padding: 3px 9px; border-radius: 6px;
  border: 1px solid var(--line); background: var(--panel-2); color: var(--muted);
  cursor: pointer; white-space: nowrap;
}
#side-toggle:hover { border-color: var(--accent); color: var(--text); }
#side-toggle.on { color: var(--accent); border-color: var(--accent); }
#side-toggle b { font-variant-numeric: tabular-nums; }
#export-csv {
  font: inherit; font-size: 11px; padding: 3px 9px; border-radius: 6px;
  border: 1px solid var(--line); background: var(--panel-2); color: var(--muted);
  cursor: pointer; white-space: nowrap;
}
#export-csv:hover { border-color: var(--accent); color: var(--text); }
#side-hide {
  float: right; font: inherit; font-size: 12px; line-height: 1; padding: 2px 6px;
  border-radius: 6px; border: 1px solid var(--line); background: var(--panel-2);
  color: var(--muted); cursor: pointer;
}
#side-hide:hover { border-color: var(--accent); color: var(--text); }
/* The sideboard: a holding area for the photos that wait for another wine. The
   list lives in the browser only. A reload empties it. */
#side {
  position: fixed; top: 0; right: 0; bottom: 0; width: 228px; z-index: 20;
  display: flex; flex-direction: column;
  background: var(--panel); border-left: 1px solid var(--line);
  box-shadow: -2px 0 8px rgba(0, 0, 0, .06);
}
#side .side-head {
  padding: 10px 12px 8px; border-bottom: 1px solid var(--line);
  font-size: 13px; font-weight: 650;
}
#side .side-head .n { color: var(--accent); }
#side .side-help { color: var(--muted); font-size: 11px; font-weight: 400; margin-top: 4px; }
#held { flex: 1; overflow-y: auto; padding: 10px; display: flex;
        flex-direction: column; gap: 8px; }
#held .empty { color: var(--muted); font-size: 12px; text-align: center; padding: 18px 6px; }
#side.over { background: var(--panel-2); }
#side.over #held { outline: 2px dashed var(--accent); outline-offset: -6px; border-radius: 8px; }
.held-card { width: 100%; }
.held-card .from {
  font-size: 10px; color: var(--muted); word-break: break-all; margin-top: 4px;
}
.held-card .back {
  width: 100%; margin-top: 4px; font-size: 11px;
  background: var(--panel); color: var(--text);
  border: 1px solid var(--line); border-radius: 6px; padding: 2px 6px; cursor: pointer;
}
.held-card .back:hover { border-color: var(--accent); }
/* A photo of the inbox: a file that lies directly in `my/` and belongs to no
   wine yet. The frame states that it is not a photo of any wine. */
.inbox-card { outline: 1px dashed var(--muted); outline-offset: 2px; }
.inbox-card.targeted { outline-color: var(--accent); }
.inbox-card .to { font-size: 10px; color: var(--accent); word-break: break-all;
                  margin-top: 2px; }
/* A row that is ready to take the dragged photo. */
tr.photo-drop > td { background: var(--panel-2) !important; }
tr.photo-drop { outline: 2px dashed var(--accent); outline-offset: -2px; }
.card.dragging { opacity: .4; }
table { border-collapse: separate; border-spacing: 0; width: 100%; }
tbody tr { background: var(--panel); }
/* The rows of one variant group stand next to each other and share a colour.
   Two colours are enough, because two groups are never adjacent by accident. */
tbody tr.grp-a { background: var(--grp-a); }
tbody tr.grp-b { background: var(--grp-b); }
tbody tr.grp-a + tr.grp-a td, tbody tr.grp-b + tr.grp-b td { border-top-style: dashed; }
/* An excluded wine is out of the benchmark. The red row states it at a glance,
   and the colour wins over the colour of a variant group. */
tbody tr.excl, tbody tr.excl.grp-a, tbody tr.excl.grp-b { background: var(--exc-bg); }
tbody tr.excl .bottle { opacity: .55; }
tbody tr + tr td { border-top: 1px solid var(--line); }
td { padding: 10px; vertical-align: top; }
td.wine { width: 320px; min-width: 300px; }
.wine-inner { display: flex; gap: 10px; }
.bottle {
  width: 84px; min-width: 84px; height: 140px; object-fit: contain;
  background: var(--panel-2); border: 1px solid var(--line); border-radius: 6px; padding: 3px;
}
.bottle.missing { display: flex; align-items: center; justify-content: center;
  color: var(--muted); font-size: 11px; text-align: center; }
/* The virtual NULL wine. It carries no bottle photo, because it is no wine: it
   collects the photos that match no card of the catalogue. */
.bottle.null-bottle { display: flex; align-items: center; justify-content: center;
  border-style: dashed; border-width: 2px; background: transparent;
  color: var(--muted); font-size: 18px; font-weight: 700; letter-spacing: .04em; }
tbody tr.null-row { background: var(--panel-2); }
tbody tr.null-row .meta .nm { color: var(--muted); }
tbody tr.null-row.photo-drop { outline: 2px solid var(--pos); }
.bottle-col { display: flex; flex-direction: column; gap: 5px; min-width: 84px; }
/* A catalogue card with no directory in `my/`. It carries no review work. */
tbody tr.cat-only { background: var(--panel-2); }
tbody tr.cat-only .meta .nm::after {
  content: "catalogue only"; margin-left: 8px; font-weight: 600; font-size: 10px;
  letter-spacing: .02em; color: var(--muted); border: 1px solid var(--line);
  border-radius: 999px; padding: 1px 6px; vertical-align: middle;
}
/* The badge states how the catalogue established this bottle photo. */
/* How the catalogue established the bottle photo. This is a statement, not a
   control, so it carries no border and no panel background. `Exclude` and
   `Group` stand right below it in the same column, and a box of the same width
   made the statement read as a third button. The colour of the text alone now
   carries the confidence. */
.imatch {
  width: 84px; box-sizing: border-box; text-align: center; cursor: help;
  font-size: 10px; line-height: 1.3; font-weight: 650; letter-spacing: .02em;
  border: 0; padding: 1px 3px; background: none; color: var(--muted);
}
.imatch.confirmed { color: var(--pos); }
.imatch.assumed   { color: var(--var); }
.imatch.manual    { color: var(--neg); }
.imatch.none      { color: var(--exc); }
.ishared {
  width: 84px; box-sizing: border-box; text-align: center; cursor: help;
  font-size: 10px; line-height: 1.3; color: var(--var); background: var(--var-bg);
  border: 1px solid var(--var); border-radius: 6px; padding: 1px 3px;
}
/* The badge of the check `catalog_photo_twin`. `same pic` states that the two
   cards carry one picture, which is a defect, and it takes the colour of a
   defect. `twin` states that the two pictures only look alike, which the
   reviewer judges, and it takes the colour of a variant. */
.itwin {
  width: 84px; box-sizing: border-box; text-align: center; cursor: help;
  font-size: 10px; line-height: 1.3; font-weight: 700; color: var(--var);
  background: var(--var-bg); border: 1px solid var(--var); border-radius: 6px;
  padding: 1px 3px;
}
.itwin.same { color: var(--exc); background: var(--exc-bg); border-color: var(--exc); }
.excl-btn {
  width: 84px; border: 1px solid var(--line); background: var(--panel-2);
  color: var(--muted); border-radius: 6px; font: inherit; font-size: 11px;
  line-height: 1.2; padding: 3px 4px; cursor: pointer;
}
.excl-btn:hover { border-color: var(--exc); color: var(--exc); }
.excl-btn.on {
  border-color: var(--exc); background: var(--exc); color: #fff; font-weight: 650;
}
.excl-btn.saving { border-style: dashed; }
.excl-why {
  width: 84px; color: var(--exc); font-size: 11px; line-height: 1.25;
  word-break: break-word;
}
/* The button that joins this wine to the variant group of another wine. */
.grp-btn {
  width: 84px; border: 1px solid var(--line); background: var(--panel-2);
  color: var(--muted); border-radius: 6px; font: inherit; font-size: 11px;
  line-height: 1.2; padding: 3px 4px; cursor: pointer;
}
.grp-btn:hover { border-color: var(--accent); color: var(--text); }
.grp-btn.on { border-color: var(--accent); color: var(--accent); font-weight: 650; }
.grp-btn.saving { border-style: dashed; }
#gp { position: fixed; inset: 0; background: rgba(0,0,0,.6); display: none;
      align-items: center; justify-content: center; z-index: 60; padding: 20px; }
#gp.open { display: flex; }
.gp-err { font-size: 11px; color: var(--exc); overflow-wrap: anywhere; }
.gp-err:empty { display: none; }
.meta { min-width: 0; }
.meta .nm { font-weight: 650; }
.meta .pr { color: var(--text); }
.meta .sm { color: var(--muted); font-size: 12px; word-break: break-all; }
.meta a { color: var(--accent); }
.copy {
  border: 1px solid var(--line); background: var(--panel-2); color: var(--muted);
  border-radius: 4px; font: inherit; font-size: 10px; line-height: 1.2;
  padding: 1px 4px; margin-left: 4px; cursor: pointer; vertical-align: baseline;
  font-weight: 400;
  /* The label of this button must stay out of a text selection. A selection of
     the name or of the slug is often pasted into a search field. */
  -webkit-user-select: none; user-select: none;
}
.copy:hover { border-color: var(--accent); color: var(--text); }
.copy.done { color: var(--pos); border-color: var(--pos); }
.wine-note {
  display: block; width: 100%; margin-top: 6px; resize: none;
  height: 26px; overflow: hidden;
  background: var(--panel-2); color: var(--text);
  border: 1px solid var(--line); border-radius: 6px; padding: 4px 6px;
  font: inherit; font-size: 12px; line-height: 1.35;
}
.wine-note::placeholder { color: var(--muted); }
.wine-note:focus, .wine-note.filled {
  height: 84px; overflow: auto; outline: none; border-color: var(--accent);
}
.wine-note.filled { background: var(--panel); }
.wine-note.saving { border-style: dashed; }
.cards { display: flex; flex-wrap: wrap; gap: 10px; }
.card {
  width: 172px; background: var(--panel-2); border: 1px solid var(--line);
  border-radius: 8px; padding: 6px;
}
.card.pos { border-color: var(--pos); background: var(--pos-bg); }
.card.neg { border-color: var(--neg); background: var(--neg-bg); }
.card.unu { border-color: var(--unu); background: var(--unu-bg); opacity: .55; }
.card.var { border-color: var(--var); background: var(--var-bg); }
.card.moved { outline: 2px dashed var(--accent); outline-offset: 2px; }
/* A card that is copied to another wine. The file is written by "apply"; this
   photo stays where it is, with its label. */
.card.copied { outline: 2px dotted var(--var); outline-offset: 2px; }
/* A card that a check reports. The last run of `validate` marked it. */
.card.bad { outline: 2px solid var(--exc); outline-offset: 2px; }
/* The pill of a check sits at the top left, where the pill of a proposal sits.
   The two never meet: a proposal is shown only for a photo with no label, and
   every check reported here reads a label. */
.bad-tag {
  position: absolute; top: 4px; left: 4px; z-index: 3;
  background: var(--exc); color: #fff; border-radius: 999px;
  font-size: 9px; line-height: 1; padding: 3px 7px; font-weight: 700;
  pointer-events: none;
}
/* The dialog of `validate`. One row per check, with its own explanation. */
#vd { position: fixed; inset: 0; background: rgba(0,0,0,.6); display: none;
      align-items: center; justify-content: center; z-index: 80; padding: 20px; }
#vd.open { display: flex; }
.vd-item {
  display: flex; gap: 10px; align-items: flex-start; width: 100%;
  padding: 10px; border: 1px solid var(--line); border-radius: 8px;
  background: var(--panel-2); cursor: pointer; text-align: left;
}
.vd-item + .vd-item { margin-top: 8px; }
.vd-item:hover { border-color: var(--accent); }
.vd-item input { margin-top: 2px; }
.vd-item b { font-size: 13px; }
.vd-item div { color: var(--muted); font-size: 12px; margin-top: 3px; }
#vd-note { color: var(--exc); font-size: 12px; }
/* A card marked for deletion. The file is still on disk until "apply" is pressed. */
.card.del { outline: 2px solid var(--neg); outline-offset: 2px; opacity: .45; }
.card.del img { filter: grayscale(1); }
.del-tag {
  position: absolute; top: 4px; right: 4px; z-index: 3;
  background: var(--neg); color: #fff; border-radius: 999px;
  font-size: 10px; line-height: 1; padding: 3px 7px; font-weight: 700;
  pointer-events: none;
}
/* The `del` pill takes the top-right corner. Move the comment badge clear of it,
   so the reviewer can still read the comment that "apply" is about to drop. */
.card.del .note-badge { right: 40px; }
/* The right-click menu of one photo. */
.ctxmenu {
  position: fixed; z-index: 60; min-width: 172px; padding: 4px;
  background: var(--panel-2); border: 1px solid var(--line);
  border-radius: 8px; box-shadow: 0 8px 24px rgba(0, 0, 0, .45);
  font-size: 13px;
}
.ctxmenu[hidden] { display: none; }
.ctxmenu button {
  display: block; width: 100%; text-align: left; padding: 7px 10px;
  background: none; border: 0; border-radius: 6px; color: inherit;
  font: inherit; cursor: pointer;
}
.ctxmenu button:hover { background: var(--line); }
.ctxmenu button.danger { color: var(--neg); }
.ctxmenu button.done { color: var(--pos); }
.ctxmenu .ctx-sep { height: 1px; background: var(--line); margin: 4px 0; }
.ctxmenu .ctx-head {
  padding: 4px 10px 6px; color: var(--muted); font-size: 11px;
  border-bottom: 1px solid var(--line); margin-bottom: 4px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
/* A photo that an agent proposed is not a label. It is marked apart, so the
   count of the pass stays a count of human decisions. */
.card.prop { border-style: dashed; border-color: var(--var); }
.prop-tag {
  position: absolute; top: 4px; left: 4px; z-index: 2;
  background: var(--var); color: #14100a; border-radius: 999px;
  font-size: 9px; font-weight: 700; padding: 1px 6px; letter-spacing: .02em;
}
.card img {
  width: 100%; height: 172px; object-fit: contain; display: block;
  background: var(--panel); border-radius: 5px; cursor: zoom-in;
}
.card .cap { font-size: 11px; color: var(--muted); margin: 4px 2px 5px;
             display: flex; justify-content: space-between; gap: 4px; }
.btns { display: flex; gap: 6px; }
.btns button {
  flex: 1; padding: 5px 0; font: inherit; font-weight: 700; font-size: 14px;
  border-radius: 6px; border: 1px solid var(--line); background: var(--panel);
  color: var(--muted); cursor: pointer;
}
.btns button:hover { border-color: var(--accent); color: var(--text); }
.btns button { font-size: 12px; }
.btns button.on.pos { background: var(--pos); border-color: var(--pos); color: #fff; }
.btns button.on.neg { background: var(--neg); border-color: var(--neg); color: #fff; }
.btns button.on.unu { background: var(--unu); border-color: var(--unu); color: #fff; }
.btns button.on.var { background: var(--var); border-color: var(--var); color: #fff; }
.move, .cpy {
  margin-top: 5px; width: 100%; padding: 4px 0; font: inherit; font-size: 11px;
  border-radius: 6px; border: 1px solid var(--line); background: var(--panel);
  color: var(--muted); cursor: pointer;
}
.move:hover, .cpy:hover { border-color: var(--accent); color: var(--text); }
.move.on { border-color: var(--accent); color: var(--accent); }
.cpy.on { border-color: var(--var); color: var(--var); }
.empty { color: var(--muted); font-style: italic; }
#count { color: var(--muted); font-size: 12px; margin: 0 0 8px; }
#ad { position: fixed; inset: 0; background: rgba(0,0,0,.6); display: none;
      align-items: center; justify-content: center; z-index: 70; padding: 20px; }
#ad.open { display: flex; }
body.dragging::after {
  content: "drop a file, or a picture dragged from another tab, on the row of a wine \2014 or anywhere to choose the wine";
  position: fixed; left: 50%; bottom: 18px; transform: translateX(-50%);
  background: var(--accent); color: #fff; padding: 6px 14px; border-radius: 999px;
  font-size: 12px; z-index: 80; pointer-events: none; box-shadow: var(--shadow);
}
#mv { position: fixed; inset: 0; background: rgba(0,0,0,.6); display: none;
      align-items: center; justify-content: center; z-index: 60; padding: 20px; }
#mv.open { display: flex; }
.mv-box {
  background: var(--panel); border: 1px solid var(--line); border-radius: 10px;
  box-shadow: 0 8px 30px rgba(0,0,0,.4); padding: 14px; width: 560px;
  max-width: 100%; max-height: 100%; overflow: auto;
  display: flex; flex-direction: column; gap: 9px;
}
.mv-h { font-size: 14px; font-weight: 650; }
.mv-ctx, .mv-sub { font-size: 11px; color: var(--muted); overflow-wrap: anywhere; }
.mv-list { display: flex; flex-direction: column; gap: 6px; }
.mv-item {
  display: flex; gap: 9px; align-items: center; text-align: left; cursor: pointer;
  background: var(--panel-2); border: 1px solid var(--line); border-radius: 8px;
  padding: 6px; font: inherit; color: var(--text);
}
.mv-item:hover { border-color: var(--accent); }
.mv-item.sel { border-color: var(--accent); box-shadow: inset 0 0 0 1px var(--accent); }
.mv-item img {
  width: 34px; height: 56px; object-fit: contain; border-radius: 4px;
  background: var(--panel); flex: none;
}
.mv-item .no-img { width: 34px; height: 56px; flex: none; }
.mv-item .t { min-width: 0; }
.mv-item .t b { font-weight: 650; }
.mv-item .t div { font-size: 11px; color: var(--muted); overflow-wrap: anywhere; }
.mv-any { display: flex; flex-direction: column; gap: 4px; font-size: 11px;
          color: var(--muted); }
.mv-any input {
  background: var(--panel-2); color: var(--text); border: 1px solid var(--line);
  border-radius: 6px; padding: 6px 8px; font: inherit; font-size: 13px;
}
.mv-foot { display: flex; gap: 8px; align-items: center; }
.mv-foot button {
  font: inherit; font-size: 12px; padding: 5px 12px; border-radius: 6px;
  border: 1px solid var(--line); background: var(--panel-2); color: var(--text);
  cursor: pointer;
}
.mv-foot button:hover { border-color: var(--accent); }
.mv-foot button.primary { background: var(--accent); border-color: var(--accent);
                          color: #fff; }
#lb {
  position: fixed; inset: 0; background: rgba(0,0,0,.88); display: none;
  align-items: center; justify-content: center; gap: 12px;
  z-index: 50; padding: 20px 20px 34px;
}
#lb.open { display: flex; }
/* The two images stay next to each other in the middle of the screen.
   Each figure shrinks to the width of its own image, so a wide monitor does
   not push the catalogue bottle and the candidate photo to opposite edges. */
.lb-inner {
  display: flex; gap: 8px; flex: 1 1 auto; min-width: 0; height: 100%;
  align-items: center; justify-content: center;
}
.lb-side {
  flex: 0 0 300px; max-width: 42vw; height: 100%; min-height: 0;
  display: flex; flex-direction: column; gap: 6px;
  background: var(--panel); border: 1px solid var(--line); border-radius: 8px;
  padding: 10px; box-shadow: var(--shadow);
}
.side-h { font-size: 13px; font-weight: 650; }
.side-ctx { font-size: 11px; color: var(--muted); overflow-wrap: anywhere; }
.lb-side textarea {
  flex: 1 1 auto; min-height: 120px; resize: none;
  background: var(--panel-2); color: var(--text);
  border: 1px solid var(--line); border-radius: 6px; padding: 7px;
  font: inherit; font-size: 13px; line-height: 1.4;
}
.lb-side textarea:focus { outline: 2px solid var(--accent); outline-offset: -1px; }
.side-foot { display: flex; align-items: center; gap: 8px; font-size: 11px; }
#cmt-state { color: var(--muted); flex: 1; }
#cmt-state.saved { color: var(--pos); }
#cmt-state.failed { color: var(--neg); }
#cmt-clear {
  font: inherit; font-size: 11px; padding: 3px 9px; cursor: pointer;
  background: var(--panel-2); color: var(--muted);
  border: 1px solid var(--line); border-radius: 6px;
}
#cmt-clear:hover { border-color: var(--accent); color: var(--text); }
.side-note { font-size: 10px; color: var(--muted); line-height: 1.35; }
.side-note b { color: var(--text); }
.card { position: relative; }
.note-badge {
  position: absolute; top: 4px; right: 4px; z-index: 2;
  width: 20px; height: 20px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  background: var(--accent); color: #fff; cursor: default;
  box-shadow: 0 1px 3px rgba(0,0,0,.35);
}
.note-badge svg { width: 12px; height: 12px; display: block; }
.note-pop {
  display: none; position: absolute; top: 24px; right: 0; z-index: 30;
  width: 250px; max-height: 240px; overflow: auto;
  background: var(--panel); color: var(--text);
  border: 1px solid var(--accent); border-radius: 7px;
  padding: 7px 8px; font-size: 11px; line-height: 1.45;
  white-space: pre-wrap; overflow-wrap: anywhere; text-align: left;
  box-shadow: 0 6px 20px rgba(0,0,0,.35);
}
/* The panel is a child of the badge, so it stays open while the pointer moves
   onto it and the text can be read and scrolled. */
.note-badge:hover .note-pop { display: block; }
.lb-fig {
  margin: 0; flex: 0 1 auto; min-width: 0; max-width: 49%; gap: 8px;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
}
.lb-fig[hidden] { display: none; }
.lb-fig img {
  max-width: 100%; max-height: calc(100vh - 116px); width: auto; object-fit: contain;
  border-radius: 6px; background: rgba(255,255,255,.06); cursor: default;
}
/* `width: 0` with `min-width: 100%` keeps the caption out of the width of the
   figure. A long wine name then wraps instead of moving the images apart. */
.lb-fig figcaption {
  color: #e9e9ee; font-size: 12px; text-align: center; width: 0; min-width: 100%;
  text-shadow: 0 1px 2px #000; overflow-wrap: anywhere;
}
.lb-fig figcaption b { color: #fff; }
#lb .hint {
  position: absolute; left: 0; right: 0; bottom: 10px; text-align: center;
  color: #9a9aa6; font-size: 11px;
}
#lb .hint b { color: #e9e9ee; }
#lb-status {
  position: absolute; top: 12px; left: 50%; transform: translateX(-50%);
  padding: 3px 16px; border-radius: 999px; border: 1px solid transparent;
  font-size: 13px; font-weight: 700; letter-spacing: .03em; white-space: nowrap;
}
#lb-status.none { color: #9a9aa6; border-color: #44444f; background: rgba(255,255,255,.05); }
#lb-status.pos { color: #0b2b15; background: #5fd98a; }
#lb-status.neg { color: #08243c; background: #6db6f2; }
#lb-status.unu { color: #1b1b20; background: #8a8a95; }
#lb-status.var { color: #2e2207; background: #e0b25c; }
@media (max-width: 980px) {
  #lb.open { flex-direction: column; }
  .lb-side { flex: 0 0 auto; max-width: 100%; width: 100%; height: auto; }
  .lb-side textarea { min-height: 70px; }
  .side-note { display: none; }
}
@media (max-width: 760px) {
  .lb-inner { flex-direction: column; gap: 10px; }
  .lb-fig { max-width: 100%; }
  .lb-fig img { max-height: calc(50vh - 70px); }
}
@media (max-width: 760px) {
  td.wine { width: auto; min-width: 0; }
  table, tbody, tr, td { display: block; width: 100%; }
  td { padding: 8px 10px; }
}
</style>
</head>
<body>
<header>
  <div class="head-top">
    <h1>Svoe Vino photo review <span class="sub" id="head-sub"></span></h1>
    <nav class="nav"><a class="on" href="/">Review</a><a href="/runs">Runs</a><a
      href="/clusters">Clusters</a></nav>
  </div>
  <div class="bar">
    <label>Sort
      <select id="sort">
        <option value="slug">slug A-Z</option>
        <option value="slug_desc">slug Z-A</option>
        <option value="name">wine name A-Z</option>
        <option value="producer">producer A-Z</option>
        <option value="photos_desc">photo count, most first</option>
        <option value="photos_asc">photo count, fewest first</option>
        <option value="conf_asc">confidence, lowest first</option>
        <option value="conf_desc">confidence, highest first</option>
        <option value="todo">unlabelled first</option>
        <option value="pos_desc">positive count, most first</option>
        <option value="neg_desc">negative count, most first</option>
        <option value="unu_desc">unusable count, most first</option>
        <option value="group">variant group first</option>
      </select>
    </label>
    <label>Show
      <select id="filter">
        <option value="all">all wines</option>
        <option value="todo">not fully labelled</option>
        <option value="untouched">no label yet</option>
        <option value="partial">partly labelled</option>
        <option value="done">fully labelled</option>
        <option value="has_pos">has a positive photo</option>
        <option value="no_pos">has no positive photo</option>
        <option value="has_neg">has a negative sample</option>
        <option value="has_unu">has an unusable photo</option>
        <option value="has_var">has a different-design photo</option>
        <option value="grouped">has a similar wine (variant group)</option>
        <option value="nophotos">no candidate photos (catalogue gap)</option>
        <option value="img_none">catalogue photo: unresolved</option>
        <option value="img_assumed">catalogue photo: by name only (assumed)</option>
        <option value="img_confirmed">catalogue photo: confirmed by the site</option>
        <option value="img_manual">catalogue photo: set by hand</option>
        <option value="img_shared">catalogue photo: shared with another card</option>
        <option value="moved">holds a photo moved to another slug</option>
        <option value="noted">holds a comment</option>
        <option value="proposal">holds a photo proposed by an agent</option>
        <option value="nobottle">no catalogue bottle photo</option>
        <option value="failed">failed a check (press validate first)</option>
        <option value="excluded">excluded from the benchmark</option>
        <option value="included">included in the benchmark</option>
      </select>
    </label>
    <label>Slugs
      <select id="slugsel" title="An excluded slug is out of the benchmark.">
        <option value="all">all</option>
        <option value="included">included</option>
        <option value="excluded">excluded</option>
      </select>
    </label>
    <label id="imgkind-wrap" hidden>Image
      <select id="imgkind" title="Which picture of the wine the table shows.
`package` is the catalogue photo, or its patch.
`label` is the label cut out of that photo with SAM3.
`label box` is the bounding box of the label alone.
A wine with no crop keeps its package picture and carries the mark `no label`.">
        <option value="package">package</option>
        <option value="label">label</option>
        <option value="labelbox">label box</option>
      </select>
    </label>
    <label>Find <input id="q" type="search" placeholder="slug, name, producer, region"></label>
    <button id="grp-clear" type="button" hidden
            title="the table shows one variant group; click to show every wine again"
            >variant group <b id="grp-clear-id"></b> &times;</button>
    <div class="progress">
      <span id="pending" hidden></span>
      <span id="stat"></span>
      <span class="meter"><i id="meter"></i></span>
      <button id="validate" type="button"
              title="check the photo set for defects">validate</button>
      <button id="export-csv" type="button"
              title="download the wines in the current table view">export CSV</button>
      <button id="side-toggle" type="button"
              title="show or hide the sideboard (key s)">sideboard <b id="side-n">0</b></button>
    </div>
  </div>
</header>
<main>
  <p id="count"></p>
  <table><tbody id="rows"></tbody></table>
</main>
<aside id="side">
  <div class="side-head"><button id="side-hide" type="button"
        title="hide the sideboard (key s)">&times;</button>Sideboard
    <span class="n" id="held-n">0</span>
    <div class="side-help">Drag a photo here to hold it. Drag it to a wine
      row to move it there. The move runs when you press apply.
      A photo that lies directly in <b>my/</b> stands here from the start, with a
      dashed frame. It belongs to no wine yet.</div>
  </div>
  <div id="held"></div>
</aside>
<datalist id="slug-list"></datalist>
<datalist id="my-slug-list"></datalist>
<div id="ad">
  <div class="mv-box">
    <div class="mv-h">Add photos to a wine</div>
    <div class="mv-ctx" id="ad-files"></div>
    <div class="mv-sub">Drop a file on the row of a wine to skip this question.
      The list holds the wines that already have a directory in `my/`.</div>
    <label class="mv-any">Wine slug
      <input id="ad-input" list="my-slug-list" autocomplete="off" spellcheck="false"
             placeholder="start typing a slug, a name, or a producer">
    </label>
    <div class="mv-list" id="ad-list"></div>
    <div class="mv-foot">
      <span style="flex:1"></span>
      <button id="ad-cancel" type="button">cancel</button>
      <button id="ad-ok" type="button" class="primary">add</button>
    </div>
  </div>
</div>
<div id="mv">
  <div class="mv-box">
    <div class="mv-h" id="mv-h">Move this photo to another wine</div>
    <div class="mv-ctx" id="mv-ctx"></div>
    <div class="mv-sub">Best matches. A wine of the variant group or of the same
      producer comes first.</div>
    <div class="mv-list" id="mv-list"></div>
    <label class="mv-any">Or type any slug
      <input id="mv-input" list="slug-list" autocomplete="off" spellcheck="false">
    </label>
    <div class="mv-foot">
      <button id="mv-clear" type="button">clear the move</button>
      <span style="flex:1"></span>
      <button id="mv-cancel" type="button">cancel</button>
      <button id="mv-ok" type="button" class="primary">move</button>
    </div>
  </div>
</div>
<div id="vd">
  <div class="mv-box">
    <div class="mv-h">Validate the photo set</div>
    <div class="mv-sub">Choose the checks to run. A check only reads; it changes
      nothing. The table then shows the wines that fail at least one check, and it
      holds that view until you change the filter.</div>
    <div class="mv-list" id="vd-list"></div>
    <div class="mv-foot">
      <span id="vd-note"></span>
      <span style="flex:1"></span>
      <button id="vd-cancel" type="button">cancel</button>
      <button id="vd-ok" type="button" class="primary">run</button>
    </div>
  </div>
</div>
<div id="gp">
  <div class="mv-box">
    <div class="mv-h">Group this wine with another wine</div>
    <div class="mv-ctx" id="gp-ctx"></div>
    <div class="mv-sub">One group holds the same wine in another bottle: another
      vintage, another alcohol value, or another package design. The wine that is
      in no group joins the group of the wine you name. Two wines that are each
      already in a group cannot be joined here.</div>
    <div class="mv-list" id="gp-list"></div>
    <label class="mv-any">Wine slug
      <input id="gp-input" list="slug-list" autocomplete="off" spellcheck="false"
             placeholder="start typing a slug">
    </label>
    <div class="gp-err" id="gp-err"></div>
    <div class="mv-foot">
      <span style="flex:1"></span>
      <button id="gp-cancel" type="button">cancel</button>
      <button id="gp-ok" type="button" class="primary">group</button>
    </div>
  </div>
</div>
<div id="lb">
  <div id="lb-status"></div>
  <div class="lb-inner">
    <figure class="lb-fig" id="lb-ref"><img alt=""><figcaption></figcaption></figure>
    <figure class="lb-fig" id="lb-cand"><img alt=""><figcaption></figcaption></figure>
  </div>
  <aside class="lb-side">
    <div class="side-h">Comment on this match</div>
    <div class="side-ctx" id="cmt-ctx"></div>
    <textarea id="cmt" spellcheck="false"
      placeholder="What is wrong or unclear about this photo for this wine? &#10;&#10;Example: same label, but the capsule is red, so this is the other vintage."></textarea>
    <div class="side-foot">
      <span id="cmt-state"></span>
      <button id="cmt-clear" type="button">clear</button>
    </div>
    <div class="side-note">The text is saved as you type. The keys 1-4, the arrows
      and <b>m</b>, <b>c</b> do not act while the cursor is in the field. Press Esc once to
      leave the field, and Esc again to close the view.</div>
  </aside>
  <div class="hint"><span id="lb-pos"></span>
    &larr; &rarr; photo of this wine &middot; &uarr; &darr; wine &middot;
    <b>1</b> positive &middot; <b>2</b> negative &middot; <b>3</b> unusable &middot;
    <b>4</b> other design &middot; <b>0</b> no match (NULL) &middot;
    <b>m</b> move &middot; <b>c</b> copy &middot;
    <b>s</b> sideboard &middot;
    right-click delete &middot; Esc close</div>
</div>
<div id="ctxmenu" class="ctxmenu" hidden></div>
<script>
""" + PATCH_JS + r"""
let ROWS = [], V = {}, TOTAL = 0;

/* The picture kind that every catalogue picture of this page shows: the package
   picture, the label crop, or the box crop. `bottle_label_dir` and
   `bottle_label_box_dir` of `config.yaml` name the crops, and
   `svoe-wino-hackaton/scripts/build_labels.py` writes them.

   The functions read the control and hold no state of their own, so a picker
   that draws outside `render` shows the same kind as the table. A wine with no
   crop of that kind keeps its package picture: the server falls back, and
   `noLabelMark` marks the picture. */
function imgKind() { const el = $("#imgkind"); return (el && el.value) || "package"; }
function imgSrc(slug) {
  const kind = imgKind();
  return `/img/bottle?slug=${encodeURIComponent(slug)}`
       + (kind === "package" ? "" : `&kind=${kind}`);
}
/* A label crop is RGBA and its alpha holds the mask, so it needs a white
   backdrop. A package picture needs none. */
function imgClass() { return imgKind() === "package" ? "" : " onwhite"; }
function imgKindWord() {
  const kind = imgKind();
  return kind === "label" ? "label" : kind === "labelbox" ? "label box" : "bottle";
}
function noLabelMark(r) {
  const kind = imgKind();
  if (!r || !r.has_bottle || kind === "package") return false;
  return kind === "label" ? !r.has_label : !r.has_label_box;
}
/* `ROWS` also holds the catalogue cards that have no candidate photo. They are
   not review work, so every counter of the review set uses this number. */
function reviewRows() { return ROWS.filter(r => !r.catalog_only && !isNullRow(r)); }
function reviewCount() { return reviewRows().length; }
/* Every row of the table: the catalogue, and any directory that the catalogue does
   not hold. `reviewCount` counts the wines that carry photos, which is the set that
   the labelling work covers. */
function tableCount() { return ROWS.filter(r => !isNullRow(r)).length; }
let VIEW = [];        // the rows as the table shows them now: filtered and sorted
let W = {};           // slug -> { comment, ts }: one note about a whole wine
/* slug -> { reason, ts }. An excluded slug holds an error, most often a wrong
   bottle photo. Its photos are NOT used for benchmarking. */
let EXC = {};
let GROUPS = {};      // group id -> { id, slugs, producer, name }
let SLUGS = [];       // every catalogue slug, for the move field
let LB = null;        // the place of the large view: { wine: index in VIEW, photo: index }
/* The sideboard. [{slug, file}] of the photos that the reviewer holds for a move.
   The list lives in this tab only: the server never learns about it and a reload
   empties it. A held photo keeps its label until a target is chosen and `apply`
   runs; `apply` then drops the label, as it does for every move. */
let HELD = [];
/* The inbox: the image files that lie directly in `my/` and belong to no wine
   yet. The server lists them; `to` is the wine that the reviewer dragged the
   photo to. The target lives in this tab alone, as the sideboard does: `apply`
   sends it, and the server then moves the file. */
let INBOX = [];
/* The result of the last run of `validate`. It lives in this tab: the server
   never keeps it and a reload empties it. `FAILED` maps a slug to the findings
   that name it, and the filter `failed a check` shows exactly those wines.
   `FAILED_PHOTO` maps "<slug>\n<file>" to the finding, so the card of the photo
   that a check reports can be marked. */
let CHECKS = [];
let FAILED = null;
let FAILED_PHOTO = new Map();
let FAILED_INFO = "";

const $ = s => document.querySelector(s);
const esc = s => (s == null ? "" : String(s)).replace(/[&<>"']/g,
  c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/* The three labels. `negative` is a wanted result: the photo shows a different
   wine and stays in the set as a negative sample of this slug. `unusable` is
   the only label that takes a photo out of the set. */
const SHORT = { positive: "pos", negative: "neg", unusable: "unu", variant: "var" };
const KEY_OF = { "1": "positive", "2": "negative", "3": "unusable", "4": "variant" };
/* The virtual NULL wine. A photo that lies under this slug matches NO card of
   the catalogue. The row stands first in the table and no filter takes it away,
   so the drop target is always there. */
const NULL_SLUG = "__null__";
/* The labels that a photo of the NULL wine takes. The server refuses the other
   two: they judge a photo against a wine, and NULL is not a wine. */
const NULL_LABELS = ["positive", "unusable"];
function isNullRow(r) { return !!(r && (r.null_row || r.slug === NULL_SLUG)); }
/* The photos that the labelling work covers. A photo of the NULL wine is judged
   by its place and needs no label, so it stays out of this number and out of the
   progress bar. */
function photoTotal() {
  return ROWS.reduce((n, r) => n + (isNullRow(r) ? 0 : r.photos.length), 0);
}
/* The photos that lie under the NULL wine now, and the photos that a reviewer
   sent there and `apply` has not moved yet. */
function noMatchCount() {
  const row = ROWS.find(isNullRow);
  let pending = 0;
  for (const photos of Object.values(V)) {
    for (const e of Object.values(photos)) {
      if (!e.delete && e.reassign_to === NULL_SLUG) pending++;
    }
  }
  for (const h of INBOX) if (h.to === NULL_SLUG) pending++;
  return { here: row ? row.photos.length : 0, pending };
}
const TITLE = {
  positive: "1 \u2014 this photo shows this wine",
  negative: "2 \u2014 a different wine; keep as a negative sample",
  unusable: "3 \u2014 not usable at all; leave out of the set",
  variant: "4 \u2014 this wine, different design (other vintage or package)",
};
const GLYPH = { positive: "V", negative: "N", unusable: "\u00d7", variant: "D" };

function labelOf(slug, file) {
  const r = V[slug] && V[slug][file];
  return r ? r.label : null;
}
function movedTo(slug, file) {
  const r = V[slug] && V[slug][file];
  return r ? r.reassign_to || null : null;
}
/* The slug that this photo is copied to, or null. A copy leaves the photo here:
   one picture can show two wines of one variant group. */
function copiedTo(slug, file) {
  const r = V[slug] && V[slug][file];
  return r ? r.copy_to || null : null;
}
/* True when the photo is marked for deletion. The file is still on disk: the
   mark becomes a move into `my/trash/` only when "apply" is pressed. */
function deleteMarked(slug, file) {
  const r = V[slug] && V[slug][file];
  return !!(r && r.delete);
}
function wineNote(slug) {
  return (W[slug] && W[slug].comment) || "";
}
function isExcluded(slug) { return !!EXC[slug]; }
/* The variant group of one row, or null. */
function grpOf(r) { return (r.group && GROUPS[r.group]) || null; }
function excludeReason(slug) { return (EXC[slug] && EXC[slug].reason) || ""; }
function proposalOf(slug, file) {
  const r = V[slug] && V[slug][file];
  return r && r.proposed && !r.label ? r : null;
}
function commentOf(slug, file) {
  const r = V[slug] && V[slug][file];
  return (r && r.comment) || "";
}
function tally(row) {
  const t = { positive: 0, negative: 0, unusable: 0, variant: 0, moved: 0,
              copied: 0, noted: 0, prop: 0, total: row.photos.length };
  for (const p of row.photos) {
    const l = labelOf(row.slug, p.file);
    if (l in SHORT) t[l]++;
    if (movedTo(row.slug, p.file)) t.moved++;
    if (copiedTo(row.slug, p.file)) t.copied++;
    if (commentOf(row.slug, p.file)) t.noted++;
    if (proposalOf(row.slug, p.file)) t.prop++;
  }
  t.labelled = t.positive + t.negative + t.unusable + t.variant;
  return t;
}

/* ---- the sideboard: shown or hidden ----
   The sideboard stands over the right edge of the page. The reviewer hides it to
   get the whole width back. The choice is kept in the browser, so it holds over a
   reload. A photo that the sideboard holds is NOT lost while it is hidden: the
   count stays on the button of the header. */
const SIDE_KEY = "svt.sideboard";

function sideShown() { return !document.body.classList.contains("side-off"); }

function setSide(on, remember) {
  document.body.classList.toggle("side-off", !on);
  $("#side-toggle").classList.toggle("on", on);
  $("#side-toggle").title = (on ? "hide" : "show") + " the sideboard (key s)";
  if (remember !== false) {
    try { localStorage.setItem(SIDE_KEY, on ? "1" : "0"); } catch (e) { /* private mode */ }
  }
}

function initSide() {
  let want = null;
  try { want = localStorage.getItem(SIDE_KEY); } catch (e) { /* private mode */ }
  setSide(want !== "0", false);       // the sideboard is shown until it is hidden
}

$("#side-toggle").addEventListener("click", () => setSide(!sideShown()));
$("#side-hide").addEventListener("click", () => setSide(false));

/* ---- the sideboard ---- */

function isHeld(slug, file) {
  return HELD.some(h => h.slug === slug && h.file === file);
}

function hold(slug, file) {
  if (!isHeld(slug, file)) HELD.push({ slug, file });
  render();
}

function unhold(slug, file) {
  HELD = HELD.filter(h => !(h.slug === slug && h.file === file));
}

/* Drop every held photo that the server no longer reports. A move that was carried
   out, a deletion, and a reload of the rows all end a photo. */
function pruneHeld() {
  const live = new Set();
  for (const r of ROWS) for (const p of r.photos) live.add(r.slug + "/" + p.file);
  HELD = HELD.filter(h => live.has(h.slug + "/" + h.file));
}

function renderHeld() {
  const n = HELD.length + INBOX.length;
  $("#held-n").textContent = n;
  $("#side-n").textContent = n;             // the button states it while hidden too
  if (!n) {
    $("#held").innerHTML = '<div class="empty">empty</div>';
    return;
  }
  /* The inbox stands first: such a photo belongs to no wine, so it waits for a
     decision, while a held photo already has a place to go back to. */
  const inbox = INBOX.map(h => {
    const src = `/img/inbox?file=${encodeURIComponent(h.file)}`;
    return `<div class="card held-card inbox-card ${h.to ? "targeted" : ""}"
                 draggable="true" data-inbox="1" data-file="${esc(h.file)}">
      <img loading="lazy" draggable="false" src="${src}" alt="" data-full="${src}">
      <div class="from" title="this file lies directly in my/ and belongs to no wine yet"
        >inbox &middot; ${esc(h.file)}</div>
      ${h.to ? `<div class="to">&rarr; ${esc(h.to)}</div>
        <button class="back" type="button" data-clear="1"
                title="take the target away; the photo stays in the inbox">clear</button>`
             : ""}
      </div>`;
  }).join("");
  $("#held").innerHTML = inbox + HELD.map(h => {
    const src = `/img/photo?slug=${encodeURIComponent(h.slug)}&file=${encodeURIComponent(h.file)}`;
    const l = labelOf(h.slug, h.file);
    return `<div class="card held-card ${SHORT[l] || ""}" draggable="true"
                 data-slug="${esc(h.slug)}" data-file="${esc(h.file)}">
      <img loading="lazy" draggable="false" src="${src}" alt="" data-full="${src}">
      <div class="from" title="the wine this photo comes from">${esc(h.slug)}</div>
      <button class="back" type="button" data-back="1"
              title="put this photo back in its wine">put back</button>
      </div>`;
  }).join("");
}

/* Take the list of the inbox from the server and keep the targets that the
   reviewer already chose. A file that the server no longer lists is gone: it was
   moved, or it was taken off the disk. */
function setInbox(files) {
  const chosen = new Map(INBOX.map(h => [h.file, h.to]));
  INBOX = (files || []).map(f => ({ file: f, to: chosen.get(f) || null }));
}

/* Record the wine of one photo of the inbox. Nothing is sent: `apply` sends it. */
function inboxTarget(file, to) {
  const h = INBOX.find(x => x.file === file);
  if (h) h.to = to;
  render();
}

/* The short label counts of one wine, for the row and for the header. */
function rowTags(t) {
  return (t.positive ? `<span class="tag pos">${t.positive} pos</span> ` : "") +
         (t.variant ? `<span class="tag var">${t.variant} design</span> ` : "") +
         (t.negative ? `<span class="tag neg">${t.negative} neg</span> ` : "") +
         (t.unusable ? `<span class="tag unu">${t.unusable} unusable</span> ` : "") +
         (t.moved ? `<span class="tag grp">${t.moved} moved</span> ` : "") +
         (t.copied ? `<span class="tag var">${t.copied} copied</span> ` : "") +
         (t.noted ? `<span class="tag grp">${t.noted} noted</span> ` : "") +
         (t.prop ? `<span class="tag var">${t.prop} proposed</span>` : "");
}

/* State how the catalogue established the bottle photo of one row.

   `image_match` comes from the catalogue build. An old catalogue has no such
   field, and then the badge states that the method is not recorded. */
const IMATCH_LABEL = {
  "csv-name-unique": "by name",
  "live-og-image": "from site",
  "manual": "by hand",
  "unresolved": "no photo",
};
function imatchBadge(im) {
  if (!im || !im.method) {
    return `<div class="imatch" title="${esc("this catalogue records no match method")
      }">method<br>unknown</div>`;
  }
  const cls = im.confidence === "confirmed" ? "confirmed"
            : im.confidence === "assumed" ? "assumed"
            : im.method === "manual" ? "manual" : "none";
  const tip = [
    "method: " + im.method,
    "confidence: " + (im.confidence || "-"),
    "candidates for the CSV photo name: " + (im.candidates === undefined ? "-" : im.candidates),
    im.source ? "source: " + im.source : "",
    im.checked_at ? "checked: " + im.checked_at : "",
    im.note ? "note: " + im.note : "",
  ].filter(Boolean).join("\n");
  return `<div class="imatch ${cls}" title="${esc(tip)}">${
    IMATCH_LABEL[im.method] || im.method}</div>`;
}

/* The badge of `catalog_photo_twin`, under the bottle photo of the row.

   That check reports the CATALOGUE photo, not a candidate photo, so its finding
   carries `slugs` and no `photos` and it cannot reach the badge of a card. The
   badge names the size of the cluster, and the tooltip names the other wines of
   it, so the whole cluster is read from any one of its rows. A row with no such
   finding draws nothing. */
function twinBadge(slug) {
  const f = ((FAILED && FAILED[slug]) || []).find(x => x.bottle && x.slugs);
  if (!f) return "";
  const others = f.slugs.filter(s => s !== slug);
  const lead = f.same_picture ? "the same picture is on:"
                             : "a picture that looks nearly the same is on:";
  const tip = [
    f.why,
    others.length ? lead + "\n" + others.join("\n") : "",
  ].filter(Boolean).join("\n");
  return `<div class="itwin${f.same_picture ? " same" : ""}" title="${esc(tip)}">${
    esc(f.tag)} \u00d7${f.slugs.length}</div>`;
}

/* A catalogue card with no directory in `my/` carries `catalog_only`. The table is
   built from the catalogue, so `all` lists every such card: every wine of the
   catalogue is a row, and a wine with no photo is a row with no photo.

   The other filters ask about photos and about labels. A card with no photo holds
   neither, so it stays out of them and the work lists hold the wines that carry
   photos alone. The filters below ask about the catalogue itself, so each one
   shows those cards as well. */
const CATALOG_SCOPE_FILTERS = new Set([
  "all",
  "nophotos", "img_none", "img_assumed", "img_confirmed", "img_manual", "img_shared",
  // An exclusion is a statement about the card, not about its photos. A card
  // with no directory in `my/` can be excluded too, so both entries show it.
  "excluded", "included",
  // `catalog_photo_twin` reads the whole catalogue, so it can report a card that
  // has no directory in `my/`. Such a card MUST reach the table, or the other
  // half of the cluster is not visible. The other checks read `my/` alone and
  // never report such a card, so this entry changes nothing for them.
  "failed"]);

function matchFilter(row, mode) {
  if (row.catalog_only && !CATALOG_SCOPE_FILTERS.has(mode)) return false;
  const t = tally(row);
  switch (mode) {
    case "todo": return t.labelled < t.total;
    case "untouched": return t.labelled === 0;
    case "partial": return t.labelled > 0 && t.labelled < t.total;
    case "done": return t.total > 0 && t.labelled === t.total;
    case "has_pos": return t.positive > 0;
    case "no_pos": return t.positive === 0;
    case "has_neg": return t.negative > 0;
    case "has_unu": return t.unusable > 0;
    case "has_var": return t.variant > 0;
    case "grouped": return !!row.group;
    case "moved": return t.moved > 0;
    case "noted": return t.noted > 0;
    case "proposal": return t.prop > 0;
    case "nobottle": return !row.has_bottle;
    case "nophotos": return row.photos.length === 0;
    // The wines that the last run of `validate` reported. With no run, the table
    // is empty and the count line states that.
    case "failed": return !!(FAILED && FAILED[row.slug]);
    case "img_none": return (row.image_match || {}).method === "unresolved";
    case "img_assumed": return (row.image_match || {}).confidence === "assumed";
    case "img_confirmed": return (row.image_match || {}).confidence === "confirmed";
    case "img_manual": return (row.image_match || {}).method === "manual";
    case "img_shared": return ((row.image_match || {}).shared_with || []).length > 0;
    // The same scope as the control `Slugs`. It stands here as well, because the
    // reviewer looks for the excluded wines in this list.
    case "excluded": return isExcluded(row.slug);
    case "included": return !isExcluded(row.slug);
    default: return true;
  }
}

/* Put the rows of one variant group next to each other. The order inside the
   group follows the chosen sort. A group takes the place of its first row. */
function clusterGroups(rows) {
  const byGroup = new Map();
  for (const r of rows) {
    if (!r.group) continue;
    if (!byGroup.has(r.group)) byGroup.set(r.group, []);
    byGroup.get(r.group).push(r);
  }
  if (!byGroup.size) return rows;
  const done = new Set(), out = [];
  for (const r of rows) {
    if (!r.group) { out.push(r); continue; }
    if (done.has(r.group)) continue;
    done.add(r.group);
    out.push(...byGroup.get(r.group));
  }
  return out;
}

/* The badge that marks a photo with a comment. It sits in the corner of the card
   and shows the whole text while the pointer is over it. */
function noteBadge(text) {
  if (!text) return "";
  return `<span class="note-badge" title="">
    <svg viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path
      d="M2 3.2A1.2 1.2 0 0 1 3.2 2h9.6A1.2 1.2 0 0 1 14 3.2v7.1a1.2 1.2 0 0 1-1.2
         1.2H6.6L3.4 14a.5.5 0 0 1-.8-.4v-2.1h-.4A1.2 1.2 0 0 1 2 10.3z"/></svg>
    <span class="note-pop">${esc(text)}</span></span>`;
}

function labelButtons(current, slug) {
  const names = slug === NULL_SLUG ? NULL_LABELS : Object.keys(SHORT);
  return names.map(name =>
    `<button class="${SHORT[name]} ${current === name ? "on" : ""}" data-l="${name}"
             title="${slug === NULL_SLUG && name === "positive"
                      ? "1 \u2014 confirmed: no card of the catalogue shows this wine"
                      : TITLE[name]}">${GLYPH[name]}</button>`).join("");
}

function sortRows(rows, mode) {
  const bySlug = (a, b) => a.slug.localeCompare(b.slug);
  const txt = k => (a, b) => (a[k] || "￿").localeCompare(b[k] || "￿") || bySlug(a, b);
  const num = (f, dir) => (a, b) => {
    const x = f(a), y = f(b);
    const ax = x === null ? (dir > 0 ? -Infinity : Infinity) : x;
    const ay = y === null ? (dir > 0 ? -Infinity : Infinity) : y;
    return (ax - ay) * dir || bySlug(a, b);
  };
  const out = rows.slice();
  switch (mode) {
    case "slug_desc": out.sort((a, b) => bySlug(b, a)); break;
    case "name": out.sort(txt("name")); break;
    case "producer": out.sort((a, b) => txt("producer")(a, b)); break;
    case "photos_desc": out.sort(num(r => r.photos.length, -1)); break;
    case "photos_asc": out.sort(num(r => r.photos.length, 1)); break;
    case "conf_asc": out.sort(num(r => r.min_conf, 1)); break;
    case "conf_desc": out.sort(num(r => r.min_conf, -1)); break;
    case "todo": out.sort((a, b) => {
        const ta = tally(a), tb = tally(b);
        const pa = ta.total ? ta.labelled / ta.total : 1;
        const pb = tb.total ? tb.labelled / tb.total : 1;
        return pa - pb || bySlug(a, b);
      }); break;
    case "pos_desc": out.sort(num(r => tally(r).positive, -1)); break;
    case "neg_desc": out.sort(num(r => tally(r).negative, -1)); break;
    case "unu_desc": out.sort(num(r => tally(r).unusable, -1)); break;
    case "group": out.sort((a, b) => (a.group ? 0 : 1) - (b.group ? 0 : 1) || bySlug(a, b)); break;
    default: out.sort(bySlug);
  }
  return out;
}

/* ---- export of the current table view ----

   The browser owns the exact view. It can include a text search, a slug scope,
   one variant group, and the result of `validate`, which lives in this tab only.
   Export `VIEW` instead of asking the server to rebuild a similar list.

   One CSV record describes one candidate photo. A wine with no candidate photo
   gets one record with empty photo fields, so a catalogue-gap filter does not
   produce an empty file. Wine fields and counts repeat for each candidate photo.
   This flat shape lets a spreadsheet filter photos without parsing a JSON cell. */
function csvCell(value) {
  if (value === null || value === undefined) value = "";
  else if (typeof value === "boolean") value = value ? "true" : "false";
  else if (typeof value === "number") value = String(value);
  else {
    value = String(value);
    // Stop a note, name, or other text from becoming a formula when a spreadsheet
    // opens the file. The apostrophe is the standard visible-value guard.
    if (/^[\t\r\n ]*[=+\-@]/.test(value)) value = "'" + value;
  }
  return `"${String(value).replace(/"/g, '""')}"`;
}

function currentViewCsv() {
  const columns = [
    "wine_position", "photo_position", "filter", "slug_scope", "search", "sort",
    "variant_group_scope", "slug", "name", "producer", "category", "color",
    "region", "grapes", "in_catalog", "catalog_only", "has_bottle",
    "image_match_method", "image_match_confidence", "image_shared_with",
    "variant_group", "excluded", "exclusion_reason", "photo_count",
    "labelled_count", "unlabelled_count", "positive_count", "negative_count",
    "unusable_count", "variant_count", "moved_count", "copied_count",
    "noted_count", "proposed_count", "min_confidence", "wine_note", "page_url",
    "failed_checks", "photo_file", "photo_confidence", "photo_label",
    "photo_comment", "photo_reassign_to", "photo_copy_to", "photo_delete",
    "photo_proposed", "photo_proposed_by", "photo_proposal_confidence",
    "photo_source_url", "photo_url",
  ];
  const view = {
    filter: $("#filter").value,
    slug_scope: $("#slugsel").value,
    search: $("#q").value.trim(),
    sort: $("#sort").value,
    variant_group_scope: GROUP_FILTER,
  };
  const lines = [columns.map(csvCell).join(",")];
  VIEW.forEach((r, wineIndex) => {
    const t = tally(r), im = r.image_match || {};
    const photos = r.photos.length ? r.photos : [null];
    const failed = [...new Set(((FAILED && FAILED[r.slug]) || [])
      .map(f => f.check).filter(Boolean))].join("; ");
    photos.forEach((p, photoIndex) => {
      const entry = p ? ((V[r.slug] || {})[p.file] || {}) : {};
      const proposal = p ? proposalOf(r.slug, p.file) : null;
      const values = [
        wineIndex + 1, p ? photoIndex + 1 : "", view.filter, view.slug_scope,
        view.search, view.sort, view.variant_group_scope, r.slug, r.name, r.producer,
        r.category, r.color, r.region, r.grapes, r.in_catalog, !!r.catalog_only,
        r.has_bottle, im.method, im.confidence, (im.shared_with || []).join("; "),
        r.group || "", isExcluded(r.slug), excludeReason(r.slug), t.total, t.labelled,
        t.total - t.labelled, t.positive, t.negative, t.unusable, t.variant, t.moved,
        t.copied, t.noted, t.prop, r.min_conf, wineNote(r.slug), r.page_url, failed,
        p ? p.file : "", p ? p.conf : "", entry.label || "", entry.comment || "",
        entry.reassign_to || "", entry.copy_to || "", p ? !!entry.delete : "",
        proposal ? proposal.proposed || "" : "", proposal ? proposal.by || "" : "",
        proposal ? proposal.confidence ?? "" : "",
        proposal ? proposal.source_url || "" : "",
        p ? new URL(photoSrc(r.slug, p.file), location.href).href : "",
      ];
      lines.push(values.map(csvCell).join(","));
    });
  });
  return lines.join("\r\n") + "\r\n";
}

function exportCurrentViewCsv() {
  // A byte-order mark makes spreadsheet programs detect the Cyrillic text as UTF-8.
  const blob = new Blob(["\ufeff", currentViewCsv()], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  const date = new Date().toISOString().slice(0, 10);
  a.href = url;
  a.download = `svoe-vino-review-${$("#filter").value}-${VIEW.length}-wines-${date}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

/* ---- the search ----

   A plain substring over the text of a row fails three ways in this catalogue.
   An accent: `Cotes` does not stand in `Côtes`. The order: `don cotes` does not
   stand in `Côtes du Don`. A small difference of spelling between the name and
   the slug: the slug of `Цимлянский` reads `tsimlyanskiy`, and a reader types
   `cimlyanskiy`.

   The search therefore folds the accents, takes the query apart into words, and
   asks for each word on its own, in any order. A word of four letters or more
   also matches a word of the text that stands one letter away from it. A word in
   Cyrillic is looked for in its Latin form too, because the slug is Latin.

   The table was checked against the catalogue on 2026-09-17: of the Cyrillic
   words of the wine names, 96.0 percent stand in the slug as the table writes
   them, 1.7 percent stand one letter away, and 2.3 percent do not match, because
   the slugs do not follow one rule (`czimlyanskoe` beside `tsimlyanskiy`). */
const TRANSLIT = {
  "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
  "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
  "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
  "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
  "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
};
// A word shorter than this MUST match without the one-letter rule. Three letters
// stand one letter away from too many other three-letter words.
const FUZZY_MIN = 4;

/* Lower case, and take the accents away. `NFD` takes `й` and `ё` apart as well,
   and the filter of the marks would then lose them, so both are put aside. */
function foldText(s) {
  s = (s || "").toLowerCase().replace(/ё/g, "\x01").replace(/й/g, "\x02");
  s = s.normalize("NFD").replace(/\p{Mn}+/gu, "");
  return s.replace(/\x01/g, "ё").replace(/\x02/g, "й");
}

function translit(s) {
  let out = "";
  for (const c of s) out += (c in TRANSLIT) ? TRANSLIT[c] : c;
  return out;
}

function wordsOf(s) {
  return foldText(s).split(/[^\p{L}\p{N}]+/u).filter(Boolean);
}

/* The slugs of the catalogue do not follow one rule. The letter `ц` stands as
   `ts` in `tsimlyanskiy` and as `cz` in `czimlyanskoe`, and a reader writes `c`.
   The ending of `чёрный` stands as `chyornyy` and as `chernyj`. The canonical
   form puts these spellings together, so one of them finds the others. It is
   used beside the plain word, never in its place. */
function canonWord(w) {
  return w.replace(/cz|ts/g, "c").replace(/kh/g, "h")
          .replace(/yo/g, "e").replace(/j/g, "y");
}

/* The words of one row, folded, and the same words in the canonical form. Both
   lists are built once and kept on the row. */
function rowWords(r) {
  if (!r.__words) {
    r.__words = [...new Set(wordsOf(
      [r.slug, r.name, r.producer, r.region, r.grapes].join(" ")))];
    r.__canon = [...new Set(r.__words.map(w => canonWord(translit(w))))];
  }
  return r.__words;
}

function rowCanon(r) {
  rowWords(r);
  return r.__canon;
}

/* Do the two words differ by one letter at most? One insertion, one deletion,
   or one replacement. */
function within1(a, b) {
  if (a === b) return true;
  if (Math.abs(a.length - b.length) > 1) return false;
  if (a.length > b.length) { const t = a; a = b; b = t; }
  let i = 0;
  while (i < a.length && a[i] === b[i]) i++;
  if (a.length === b.length) return a.slice(i + 1) === b.slice(i + 1);
  return a.slice(i) === b.slice(i + 1);
}

/* One entry per word of the query: the forms to look for, and the canonical
   form. A word in Cyrillic carries its Latin form as well, because the slug is
   Latin. */
function queryTerms(q) {
  return wordsOf(q).map(w => {
    const t = translit(w);
    return { forms: t === w ? [w] : [w, t], canon: canonWord(t) };
  });
}

/* Every word of the query MUST stand somewhere in the row. The order does not
   matter. A word stands in the row when a word of the row holds it, when it is
   one letter away from a word of the row, or when the canonical forms meet. */
function matchQuery(r, terms) {
  const ws = rowWords(r), cs = rowCanon(r);
  return terms.every(t =>
    t.forms.some(f => ws.some(w => w.includes(f))
                   || (f.length >= FUZZY_MIN && ws.some(w => within1(f, w))))
    || (t.canon.length >= FUZZY_MIN
        && cs.some(w => w.includes(t.canon) || within1(t.canon, w))));
}

/* The card strip of one row.

   `render` draws it for every row. A photo added by drag and drop draws it again
   for its own row alone, so the table is not filtered again and no row moves
   under the pointer. */
function cardsHtml(r) {
  // A photo in the sideboard leaves its row. `tally` is not touched, so the
  // counts of the row still state what the server holds.
  const shown = r.photos.filter(p => !isHeld(r.slug, p.file));
  if (!shown.length) {
    return `<span class="empty">${
        isNullRow(r) ? "no photo matches nothing yet \u2014 drag a photo here, or "
                     + "press 0 in the large view, to state that no card of the "
                     + "catalogue shows it"
        : r.catalog_only ? "no directory my/" + esc(r.slug)
                       + " \u2014 this card is a gap of the photo set"
        : r.photos.length ? "every photo is in the sideboard" : "no photos"}</span>`;
  }
  return shown.map(p => {
      const l = labelOf(r.slug, p.file), mv = movedTo(r.slug, p.file);
      const cp = copiedTo(r.slug, p.file);
      const bad = FAILED_PHOTO.get(r.slug + "\n" + p.file) || null;
      const note = commentOf(r.slug, p.file), pr = proposalOf(r.slug, p.file);
      const dl = deleteMarked(r.slug, p.file);
      const src = `/img/photo?slug=${encodeURIComponent(r.slug)}&file=${encodeURIComponent(p.file)}`;
      return `<div class="card ${SHORT[l] || ""} ${mv ? "moved" : ""} ${
                     cp ? "copied" : ""} ${bad ? "bad" : ""} ${note ? "noted" : ""}
                   ${pr ? "prop" : ""} ${dl ? "del" : ""}" draggable="true"
                   data-slug="${esc(r.slug)}" data-file="${esc(p.file)}">
        ${dl ? `<span class="del-tag" title="marked for deletion; press apply to move it to my/trash/">del</span>` : ""}
        ${pr ? `<span class="prop-tag" title="${esc(pr.by || "agent")} proposes ${
          esc(pr.proposed)}${pr.source_url ? "\nfrom " + esc(pr.source_url) : ""}">${
          esc(pr.proposed).slice(0, 3)} ${Math.round((pr.confidence || 0) * 100)}%</span>` : ""}
        ${noteBadge(note)}
        ${bad ? `<span class="bad-tag" title="${esc(badTitle(bad, r.slug))}">${
          bad.tag ? esc(bad.tag) : (bad.same_group ? "same group" : "") + " " +
          (bad.photos || []).length + " wines"}</span>` : ""}
        <img loading="lazy" draggable="false" src="${src}" alt="" data-full="${src}">
        <div class="cap"><span>${esc(p.file.split("_")[0] || "")}</span>
          <span>${p.conf === null ? "" : "conf " + p.conf}</span></div>
        <div class="btns">${labelButtons(l, r.slug)}</div>
        <button class="move ${mv ? "on" : ""}" data-move="1"
                title="${mv === NULL_SLUG
                  ? "this photo matches no card of the catalogue; press apply to move it to the NULL wine"
                  : "move this photo to another wine slug"}">${
          mv ? "\u2192 " + esc(mv === NULL_SLUG ? "NULL" : mv) : "\u2192 move"}</button>
        <button class="cpy ${cp ? "on" : ""}" data-cpy="1"
                title="copy this photo to another wine slug; this photo stays here">${
          cp ? "\u29c9 " + esc(cp) : "\u29c9 copy"}</button>
        </div>`;
  }).join("");
}

function render() {
  const mode = $("#sort").value, filt = $("#filter").value;
  const sel = $("#slugsel").value;
  const terms = queryTerms($("#q").value);
  /* The NULL wine takes no filter and no sort. It is the drop target for a photo
     that matches no card of the catalogue, and the target MUST always be there.
     It is put back in front of the view after the filters have run. */
  const nullRow = ROWS.find(isNullRow) || null;
  let rows = ROWS.filter(r => !isNullRow(r) && matchFilter(r, filt));
  if (sel === "excluded") rows = rows.filter(r => isExcluded(r.slug));
  else if (sel === "included") rows = rows.filter(r => !isExcluded(r.slug));
  if (terms.length) rows = rows.filter(r => matchQuery(r, terms));
  if (GROUP_FILTER) rows = rows.filter(r => r.group === GROUP_FILTER);
  rows = clusterGroups(sortRows(rows, mode));
  if (nullRow) rows.unshift(nullRow);
  VIEW = rows;            // the arrow keys follow this order

  // Give each variant group one of two background colours, in the order of view.
  const gclass = new Map();
  let gi = 0;
  for (const r of rows) {
    if (r.group && !gclass.has(r.group)) gclass.set(r.group, (gi++ % 2) ? "grp-b" : "grp-a");
  }

  const html = rows.map(r => {
    const t = tally(r);
    const im = r.image_match || {};
    const noPhoto = im.method === "unresolved"
      ? "no photo<br>unresolved"
      : (r.in_catalog ? "no bottle<br>photo" : "not in<br>catalogue");
    const img = r.has_bottle
      ? picHtml(`<img class="bottle${imgClass()}" loading="lazy" src="${imgSrc(r.slug)}"
             alt="" data-full="${imgSrc(r.slug)}">`, r.patched, noLabelMark(r))
      : `<div class="bottle missing">${noPhoto}</div>`;
    const badge = imatchBadge(im);
    const shared = (im.shared_with || []).length
      ? `<div class="ishared" title="${esc("the same file is on: " + im.shared_with.join(", ")
          + "\nthese cards cannot be separated by the image")}">shared ×${
          im.shared_with.length + 1}</div>`
      : "";
    const ex = isExcluded(r.slug), why = excludeReason(r.slug);
    const exclBtn = `<button class="excl-btn ${ex ? "on" : ""}" data-excl="${esc(r.slug)}"
        title="${ex ? "excluded: " + esc(why) + "\nclick to include this slug again"
                    : "exclude this slug from the benchmark; its photos are then not used"}">${
        ex ? "Excluded" : "Exclude"}</button>
      ${ex && why ? `<div class="excl-why" title="${esc(why)}">${esc(why)}</div>` : ""}`;
    /* The NULL wine carries no bottle photo, no image badge, and no variant
       group: it is no wine. It keeps the exclude button, because that button
       states whether its photos reach the benchmark. */
    const bottle = isNullRow(r)
      ? `<div class="bottle-col"><div class="bottle null-bottle"
           title="the virtual NULL wine: a photo here matches no card of the catalogue"
           >NULL</div>${exclBtn}</div>`
      : `<div class="bottle-col">${img}${badge}${shared}${twinBadge(r.slug)}
      ${exclBtn}
      <button class="grp-btn ${grpOf(r) ? "on" : ""}" data-group="${esc(r.slug)}"
        title="${grpOf(r)
          ? "in variant group " + esc(grpOf(r).id) + " of " + grpOf(r).slugs.length +
            " wines\nclick to add another wine to this group"
          : "group this wine with another wine of the same label"}">${
        grpOf(r) ? "Group " + grpOf(r).slugs.length : "Group"}</button>
      </div>`;
    const cards = cardsHtml(r);

    /* The copy button of the name gives the brand and the name in one string,
       because a search needs both. */
    const fullName = [r.producer, r.name].filter(Boolean).join(" ");
    const grp = r.group ? GROUPS[r.group] : null;
    return `<tr data-slug="${esc(r.slug)}" class="${r.group ? gclass.get(r.group) : ""} ${
      ex ? "excl" : ""} ${r.catalog_only ? "cat-only" : ""} ${
      isNullRow(r) ? "null-row" : ""}">
      <td class="wine"><div class="wine-inner">${bottle}<div class="meta">
        <div class="nm">${esc(r.name) || "<span class='empty'>unknown name</span>"}${
          r.name ? `<button class="copy" data-copy="${esc(fullName)}"
             title="copy the brand and the name to the clipboard">copy</button>` : ""}</div>
        <div class="pr">${esc(r.producer)}</div>
        <div class="sm">${isNullRow(r)
          ? "no card of the catalogue shows the wine of a photo in this row"
          : esc(r.category) + (r.region ? " &middot; " + esc(r.region) : "")}</div>
        <div class="sm">${esc(r.grapes)}</div>
        <div class="sm">${esc(r.slug)}<button class="copy" data-copy="${esc(r.slug)}"
             title="copy the slug to the clipboard">copy</button></div>
        ${grp ? `<div class="sm"><button class="tag grp" type="button"
          data-grp-show="${esc(grp.id)}"
          title="${GROUP_FILTER === grp.id
            ? "show every wine again"
            : "show only the " + grp.slugs.length + " wines of this variant group"}">${
          ""}variant group of ${grp.slugs.length}</button></div>` : ""}
        <div class="sm">${t.total} photo(s)
          ${rowTags(t)}</div>
        ${r.page_url ? `<div class="sm"><a href="${esc(r.page_url)}" target="_blank" rel="noopener">site page</a></div>` : ""}
        <textarea class="wine-note ${wineNote(r.slug) ? "filled" : ""}"
          data-wine="${esc(r.slug)}" spellcheck="false"
          placeholder="note about this wine">${esc(wineNote(r.slug))}</textarea>
      </div></div></td>
      <td><div class="cards">${cards}</div></td></tr>`;
  }).join("");

  $("#rows").innerHTML = html;
  const gf = GROUP_FILTER && GROUPS[GROUP_FILTER];
  $("#grp-clear").hidden = !gf;
  if (gf) $("#grp-clear-id").textContent = `${gf.id} of ${gf.slugs.length}`;
  $("#count").textContent =
    `${rows.length - (nullRow ? 1 : 0)} of ${tableCount()} wines shown` +
    (gf ? ` \u00b7 variant group ${gf.id}` : "") +
    (filt === "failed"
      ? " \u00b7 " + (FAILED ? FAILED_INFO : "no check was run yet; press validate")
      : "") +
    /* `Show` and `Slugs` state the same scope and can contradict each other. The
       table is then empty for a reason that the reader cannot see, so it is said. */
    ((filt === "excluded" && sel === "included") ||
     (filt === "included" && sel === "excluded")
      ? ` \u00b7 the control Slugs stands on ${sel} and takes every row away`
      : "");
  $("#export-csv").title = `download ${rows.length} shown wine(s) in this order`;
  renderHeld();
  stats();
  writeViewToUrl();
}

function stats() {
  const all = { positive: 0, negative: 0, unusable: 0, variant: 0, moved: 0 };
  let doneWines = 0;
  for (const r of ROWS) {
    if (isNullRow(r)) continue;          // no label work; it is counted apart
    const t = tally(r);
    all.positive += t.positive; all.negative += t.negative;
    all.unusable += t.unusable; all.variant += t.variant; all.moved += t.moved;
    if (t.total && t.labelled === t.total) doneWines++;
  }
  const labelled = all.positive + all.negative + all.unusable + all.variant;
  // How far the photo set reaches over the catalogue. `wines done` counts the
  // labelling of the wines that hold candidate photos; this one counts the wines
  // that hold a photo at all. A catalogue card with no photo is a gap of the set,
  // and the filter `no candidate photos (catalogue gap)` lists exactly those.
  const withPhoto = ROWS.filter(r => r.in_catalog && r.photos.length).length;
  const nm = noMatchCount();
  $("#stat").innerHTML = `labelled <b>${labelled}</b>/<b>${TOTAL}</b> photos &middot; ` +
    rowTags({ ...all, total: TOTAL }) + ` &middot; ` +
    `<b>${doneWines}</b>/<b>${reviewCount()}</b> wines done` +
    (nm.here || nm.pending
      ? ` &middot; <b>${nm.here}</b> <span class="muted" title="these photos match`
        + ` no card of the catalogue">no match</span>`
        + (nm.pending ? ` <span class="muted">(+${nm.pending} pending)</span>` : "")
      : "") +
    (SLUGS.length
      ? ` &middot; <b>${withPhoto}</b>/<b>${SLUGS.length}</b> catalogue wines`
        + ` <span class="muted">with a photo</span>`
      : "");
  $("#meter").style.width = TOTAL ? (100 * labelled / TOTAL).toFixed(1) + "%" : "0";

  let pending = 0, pendingCopy = 0, pendingDel = 0;
  for (const photos of Object.values(V)) {
    for (const e of Object.values(photos)) {
      // A deletion drops the move and the copy of the same photo.
      if (e.delete) { pendingDel++; continue; }
      if (e.reassign_to) pending++;
      if (e.copy_to) pendingCopy++;
    }
  }
  // A photo of the inbox with a wine is a move too, and `apply` carries it out.
  const pendingIn = INBOX.filter(h => h.to).length;
  pending += pendingIn;
  const box = $("#pending");
  box.hidden = pending === 0 && pendingCopy === 0 && pendingDel === 0;
  if (!box.hidden) {
    const parts = [];
    if (pending) parts.push(`<b>${pending}</b> move${pending > 1 ? "s" : ""}`);
    if (pendingCopy) parts.push(`<b>${pendingCopy}</b> cop${pendingCopy > 1 ? "ies" : "y"}`);
    if (pendingDel) parts.push(`<b>${pendingDel}</b> deletion${pendingDel > 1 ? "s" : ""}`);
    box.innerHTML = parts.join(", ") + ` pending ` +
      `<button id="apply" type="button" title="carry out the pending work now">apply</button>`;
  }
}

function cardOf(slug, file) {
  return $(`.card[data-slug="${CSS.escape(slug)}"][data-file="${CSS.escape(file)}"]`);
}

/* Store one label. The same label again clears it.
   The call comes from a button of the table or from a key of the large view. */
async function setLabel(slug, file, want) {
  const next = labelOf(slug, file) === want ? "" : want;
  const res = await fetch("/api/label", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ slug, file, label: next }),
  });
  if (!res.ok) { alert("save failed: " + res.status); return; }
  if (next) {
    (V[slug] = V[slug] || {})[file] = { label: next };
  } else if (V[slug]) {
    delete V[slug][file];
    if (!Object.keys(V[slug]).length) delete V[slug];
  }
  const card = cardOf(slug, file);
  if (card) {
    for (const name of Object.keys(SHORT)) {
      const on = next === name, cls = SHORT[name];
      card.classList.toggle(cls, on);
      card.querySelector("button." + cls).classList.toggle("on", on);
    }
  }
  const row = card ? card.closest("tr") : null;
  const r = ROWS.find(x => x.slug === slug);
  if (r && row) {
    const t = tally(r), sm = row.querySelectorAll(".meta .sm");
    const tgt = sm[sm.length - (r.page_url ? 2 : 1)];
    if (tgt) tgt.innerHTML = `${t.total} photo(s) ` + rowTags(t);
  }
  if (LB) {
    const lr = VIEW[LB.wine], lp = lr && lr.photos[LB.photo];
    if (lp && lr.slug === slug && lp.file === file) {
      renderLbStatus();
      fillFig("#lb-cand", candItem(lr, LB.photo));
    }
  }
  stats();
}

function fillFig(id, item) {
  const fig = $(id), img = fig.querySelector("img");
  if (!item) { fig.hidden = true; img.removeAttribute("src"); return; }
  // Set `src` only when it changes. A repeated set reloads the image and flickers.
  if (img.getAttribute("src") !== item.src) img.setAttribute("src", item.src);
  // A label crop is transparent outside the mask. It needs the white backdrop
  // here too, and a photo of the candidate never carries the flag.
  img.classList.toggle("onwhite", !!item.onwhite);
  fig.querySelector("figcaption").innerHTML = item.cap;
  fig.hidden = false;
}

function bottleItem(r) {
  if (!r || !r.has_bottle) return null;
  return {
    src: imgSrc(r.slug),
    onwhite: imgKind() !== "package",
    cap: `<b>catalogue ${imgKindWord()}</b>` +
         (noLabelMark(r) ? ` <span class="muted">no crop, package shown</span>` : "") +
         `<br>${esc(r.name || r.slug)}` +
         (r.producer ? `<br>${esc(r.producer)}` : "") +
         (r.group && GROUPS[r.group]
           ? `<br>variant group of ${GROUPS[r.group].slugs.length}` : ""),
  };
}

function candItem(r, pi) {
  const p = r.photos[pi];
  // A wine with no candidate photo shows the catalogue bottle alone. `fillFig`
  // hides a figure that gets no item.
  if (!p) return null;
  const t = tally(r);
  return {
    src: `/img/photo?slug=${encodeURIComponent(r.slug)}&file=${encodeURIComponent(p.file)}`,
    cap: `<b>candidate photo ${pi + 1} of ${r.photos.length}</b><br>${esc(p.file)}` +
         (p.conf === null ? "" : ` &middot; conf ${p.conf}`) +
         (movedTo(r.slug, p.file) ? `<br>moved to ${esc(movedTo(r.slug, p.file))}` : "") +
         `<br>this wine: ${t.labelled} of ${t.total} labelled` +
         (t.positive ? ` &middot; ${t.positive} pos` : "") +
         (t.negative ? ` &middot; ${t.negative} neg` : "") +
         (t.variant ? ` &middot; ${t.variant} design` : "") +
         (t.unusable ? ` &middot; ${t.unusable} unusable` : ""),
  };
}

/* Show the label of the photo that the large view holds now. */
function renderLbStatus() {
  const el = $("#lb-status");
  if (!LB) { el.textContent = ""; el.className = ""; return; }
  const r = VIEW[LB.wine], p = r.photos[LB.photo];
  if (!p) {
    el.textContent = "no candidate photo for this wine";
    el.className = "none";
    return;
  }
  const l = labelOf(r.slug, p.file);
  const mv = movedTo(r.slug, p.file), pr = proposalOf(r.slug, p.file);
  const cp = copiedTo(r.slug, p.file);
  el.textContent = (l === "positive" ? "positive \u2014 this wine"
                 : l === "negative" ? "negative sample \u2014 a different wine"
                 : l === "unusable" ? "unusable \u2014 not in the set"
                 : l === "variant" ? "this wine, different design"
                 : pr ? `${pr.by || "agent"} proposes ${pr.proposed} (${
                     Math.round((pr.confidence || 0) * 100)}%)`
                 : "not labelled") + (mv ? "  \u2192 " + mv : "")
                 + (cp ? "  \u29c9 " + cp : "");
  el.className = SHORT[l] || (pr ? "var" : "none");
}

/* Open the large view at one photo of one wine. The catalogue bottle stays at
   the left, so the eye compares the two labels without a scroll.
   `wi` is an index in VIEW, the order that the table shows now. */
function showLightbox(wi, pi) {
  if (wi < 0 || wi >= VIEW.length) return;
  const r = VIEW[wi];
  // A wine with no candidate photo still opens: the catalogue bottle is worth the
  // large view, and the filter `nophotos` shows exactly these wines. A wine with
  // neither a bottle nor a candidate photo holds nothing to show.
  if (!r.photos.length && !r.has_bottle) return;
  pi = r.photos.length ? Math.max(0, Math.min(pi, r.photos.length - 1)) : 0;
  LB = { wine: wi, photo: pi };

  fillFig("#lb-ref", bottleItem(r));
  fillFig("#lb-cand", candItem(r, pi));
  renderLbStatus();
  $("#lb-pos").textContent =
    `wine ${wi + 1} of ${VIEW.length} — ${r.slug} · `;
  setHash(r.photos.length ? `${r.slug}/${r.photos[pi].file}` : r.slug);
  loadComment(r, pi);
  $("#lb").classList.add("open");

  // Keep the table at the same wine, so the place is held when the view closes.
  const tr = $("#rows").children[wi];
  if (tr) tr.scrollIntoView({ block: "center" });
}

/* Move to the previous or the next wine. A wine that holds neither a candidate
   photo nor a catalogue bottle is stepped over: it has nothing to show. */
function stepWine(step) {
  if (!LB) return;
  let i = LB.wine + step;
  while (i >= 0 && i < VIEW.length
         && !VIEW[i].photos.length && !VIEW[i].has_bottle) i += step;
  if (i < 0 || i >= VIEW.length) return;
  showLightbox(i, 0);
}

function closeLightbox() {
  flushComment();
  CMT_AT = null;
  $("#lb").classList.remove("open");
  LB = null;
  setHash("");
}

async function copyFromButton(btn) {
  const text = btn.dataset.copy;
  try {
    await navigator.clipboard.writeText(text);
  } catch (e) {                       // clipboard API needs a secure context
    const ta = document.createElement("textarea");
    ta.value = text; document.body.appendChild(ta); ta.select();
    try { document.execCommand("copy"); } finally { ta.remove(); }
  }
  const old = btn.textContent;
  btn.textContent = "copied"; btn.classList.add("done");
  setTimeout(() => { btn.textContent = old; btn.classList.remove("done"); }, 900);
}

/* Carry out every recorded copy, move and deletion now. The server writes the
   files, drops the label of each moved photo, keeps its comment with a line that
   states where it was, and answers the rebuilt rows. */
async function applyMoves(btn) {
  let nMove = 0, nCopy = 0, nDel = 0;
  for (const photos of Object.values(V)) {
    for (const e of Object.values(photos)) {
      if (e.delete) { nDel++; continue; }
      if (e.reassign_to) nMove++;
      if (e.copy_to) nCopy++;
    }
  }
  const warn = [];
  if (nCopy) warn.push(
    `Copy ${nCopy} photo(s) to their target wine. This photo stays where it is, ` +
    `with its label. The copy carries no label, so it must be reviewed against ` +
    `the target wine. Its comment names the wine it came from.`);
  if (nMove) warn.push(
    `Move ${nMove} photo(s) to their target wine. Each moved photo loses its ` +
    `label and must be reviewed again. Its comment is kept and states where ` +
    `the photo was.`);
  if (nDel) warn.push(
    `DELETE ${nDel} photo(s). Each one is moved out of my/ into my/trash/ ` +
    `and loses its label, its comment and any proposal. It leaves the set.`);
  /* The inbox: a file that lies directly in `my/` and holds a wine now. The file
     keeps its name, and a name that is taken in the target gets a suffix. */
  const inbox = INBOX.filter(h => h.to).map(h => ({ file: h.file, to: h.to }));
  if (inbox.length) warn.push(
    `Move ${inbox.length} photo(s) of the inbox into the directory of their ` +
    `wine. Each one keeps its file name and carries no label, so it must be ` +
    `reviewed. Its comment states that it comes from the inbox.`);
  if (!warn.length) return;
  if (!window.confirm(`Carry out the pending work now?\n\n` + warn.join("\n\n"))) return;
  btn.disabled = true; btn.textContent = "working...";
  let out = {};
  try {
    const res = await fetch("/api/apply-moves", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ inbox }),
    });
    out = await res.json();
    if (!res.ok) throw new Error(out.error || res.status);
  } catch (e) {
    alert("apply failed: " + e.message);
    btn.disabled = false; btn.textContent = "apply";
    return;
  }
  ROWS = out.rows; V = out.labels || {}; W = out.wines || W;
  setInbox(out.inbox);
  pruneHeld();
  TOTAL = photoTotal();
  $("#head-sub").textContent = `${tableCount()} wines, ${TOTAL} candidate photos`;
  render();
  const deleted = out.deleted || [], delFailed = out.delete_failed || [];
  const copied = out.copied || [], copyFailed = out.copy_failed || [];
  const lines = out.moved.map(m => `${m.from}/${m.file} -> ${m.to}/${m.as}`);
  const fails = out.failed.map(f => `! ${f.from}/${f.file} -> ${f.to}: ${f.why}`);
  const cps = copied.map(c => `${c.from}/${c.file} => ${c.to}/${c.as}`);
  const cfails = copyFailed.map(c => `! ${c.from}/${c.file} => ${c.to}: ${c.why}`);
  const dels = deleted.map(d => `${d.slug}/${d.file} -> trash`);
  const dfails = delFailed.map(d => `! ${d.slug}/${d.file}: ${d.why}`);
  const report = [];
  if (copied.length || cfails.length) {
    report.push(`copied ${copied.length} photo(s)`, ...cps, ...cfails);
  }
  if (out.moved.length || fails.length) {
    if (report.length) report.push("");
    report.push(`moved ${out.moved.length} photo(s)`, ...lines, ...fails);
  }
  if (deleted.length || dfails.length) {
    if (report.length) report.push("");
    report.push(`deleted ${deleted.length} photo(s) into my/trash/`, ...dels, ...dfails);
  }
  const inMoved = out.inbox_moved || [], inFailed = out.inbox_failed || [];
  if (inMoved.length || inFailed.length) {
    if (report.length) report.push("");
    report.push(`moved ${inMoved.length} photo(s) out of the inbox`,
      ...inMoved.map(m => `my/${m.file} -> ${m.to}/${m.as}`),
      ...inFailed.map(f => `! my/${f.file} -> ${f.to}: ${f.why}`));
  }
  if (out.delete_gone) report.push(`${out.delete_gone} marked photo(s) were already gone`);
  alert(report.length ? report.join("\n") : "nothing to do");
}

/* ---- the right-click menu of one photo ---- */

/* Mark one photo for deletion, or take the mark away. The file stays on disk.
   "apply" moves every marked photo into `my/trash/`. */
async function markDelete(slug, file, on) {
  const res = await fetch("/api/mark-delete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ slug, file, delete: on }),
  });
  let out = {};
  try { out = await res.json(); } catch (e) { out = {}; }
  if (!res.ok) { alert("delete mark failed: " + (out.error || res.status)); return; }
  V[slug] = V[slug] || {};
  const entry = { ...(V[slug][file] || {}) };
  if (on) entry.delete = true; else delete entry.delete;
  if (Object.keys(entry).filter(k => k !== "ts").length) V[slug][file] = entry;
  else delete V[slug][file];
  render();
  if (LB) renderLbStatus();
}

function hideCtxMenu() {
  const m = $("#ctxmenu");
  m.hidden = true;
  m.innerHTML = "";
}

/* The address of one photo, as the table and the large view already build it. */
function photoSrc(slug, file) {
  return `/img/photo?slug=${encodeURIComponent(slug)}&file=${encodeURIComponent(file)}`;
}

/* Put text on the clipboard. The clipboard API needs a secure context. The
   address `127.0.0.1` is one. The fallback covers a page opened over a plain
   host name, where the API is absent. */
async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (e) {
    const ta = document.createElement("textarea");
    ta.value = text; document.body.appendChild(ta); ta.select();
    let ok = false;
    try { ok = document.execCommand("copy"); } finally { ta.remove(); }
    return ok;
  }
}

/* Read one photo and answer it as PNG. Every browser accepts `image/png` on the
   clipboard. A JPEG and a WEBP go through a canvas first. */
async function photoAsPng(src) {
  const res = await fetch(src);
  if (!res.ok) throw new Error("HTTP " + res.status);
  const blob = await res.blob();
  if (blob.type === "image/png") return blob;
  const bmp = await createImageBitmap(blob);
  const cv = document.createElement("canvas");
  cv.width = bmp.width; cv.height = bmp.height;
  cv.getContext("2d").drawImage(bmp, 0, 0);
  bmp.close();
  return await new Promise((ok, bad) =>
    cv.toBlob(b => b ? ok(b) : bad(new Error("the canvas is empty")), "image/png"));
}

/* Copy the picture itself. `ClipboardItem` receives the promise, not the blob.
   Safari drops the permission of the click while the fetch runs, and the promise
   form keeps it. */
async function copyImage(slug, file, btn) {
  if (!navigator.clipboard || !window.ClipboardItem) {
    ctxDone(btn, "no clipboard"); return;
  }
  try {
    await navigator.clipboard.write([
      new ClipboardItem({ "image/png": photoAsPng(photoSrc(slug, file)) }),
    ]);
    ctxDone(btn, "copied");
  } catch (e) {
    ctxDone(btn, "failed");
  }
}

/* Save the picture as a file. The address is same-origin, so the `download`
   attribute names the file and the browser saves it without opening a tab. The
   name carries the slug, because most wines hold a file named `01_conf095.jpg`
   and the plain name would collide in the download folder. */
function downloadImage(slug, file) {
  const a = document.createElement("a");
  a.href = photoSrc(slug, file);
  a.download = `${slug}__${file}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

/* Copy the full address of the picture, so another tab can open it. */
async function copyImageUrl(slug, file, btn) {
  const url = new URL(photoSrc(slug, file), location.href).href;
  ctxDone(btn, (await copyText(url)) ? "copied" : "failed");
}

/* State the result on the menu entry, then close the menu. */
function ctxDone(btn, text) {
  const old = btn.textContent;
  btn.textContent = text;
  btn.classList.add("done");
  setTimeout(() => {
    btn.textContent = old;
    btn.classList.remove("done");
    hideCtxMenu();
  }, 700);
}

/* Show the menu for one photo at the pointer. */
function showCtxMenu(x, y, slug, file) {
  const m = $("#ctxmenu");
  const marked = deleteMarked(slug, file);
  m.innerHTML =
    `<div class="ctx-head">${esc(file)}</div>` +
    `<button type="button" data-act="copy-image">Copy Image</button>` +
    `<button type="button" data-act="copy-url">Copy Image URL</button>` +
    `<button type="button" data-act="download">Download</button>` +
    `<div class="ctx-sep"></div>` +
    (slug === NULL_SLUG ? "" :
      (movedTo(slug, file) === NULL_SLUG
        ? `<button type="button" class="done" data-act="unnull">Keep this photo on this wine</button>`
        : `<button type="button" data-act="null">No match in the catalogue (NULL)</button>`)) +
    `<div class="ctx-sep"></div>` +
    (marked
      ? `<button type="button" data-act="undelete">Keep this photo</button>`
      : `<button type="button" class="danger" data-act="delete">Delete</button>`);
  m.dataset.slug = slug;
  m.dataset.file = file;
  m.hidden = false;
  // Place the menu inside the window.
  const r = m.getBoundingClientRect();
  const left = Math.min(x, window.innerWidth - r.width - 8);
  const top = Math.min(y, window.innerHeight - r.height - 8);
  m.style.left = Math.max(4, left) + "px";
  m.style.top = Math.max(4, top) + "px";
}

/* Find the photo under the pointer, in the table or in the large view. */
function photoAtEvent(ev) {
  const card = ev.target.closest(".card");
  if (card) return { slug: card.dataset.slug, file: card.dataset.file };
  if (LB && ev.target.closest("#lb-cand")) {
    const r = VIEW[LB.wine], p = r && r.photos[LB.photo];
    if (p) return { slug: r.slug, file: p.file };
  }
  return null;
}

document.addEventListener("contextmenu", ev => {
  const at = photoAtEvent(ev);
  if (!at) { hideCtxMenu(); return; }
  ev.preventDefault();
  showCtxMenu(ev.clientX, ev.clientY, at.slug, at.file);
});

document.addEventListener("click", ev => {
  const item = ev.target.closest("#ctxmenu button");
  if (!item) { hideCtxMenu(); return; }
  const m = $("#ctxmenu");
  const slug = m.dataset.slug, file = m.dataset.file;
  const act = item.dataset.act;
  // A copy keeps the menu open until `ctxDone` has stated the result.
  if (act === "copy-image") { copyImage(slug, file, item); return; }
  if (act === "copy-url") { copyImageUrl(slug, file, item); return; }
  if (act === "download") { hideCtxMenu(); downloadImage(slug, file); return; }
  hideCtxMenu();
  if (act === "delete") markDelete(slug, file, true);
  else if (act === "undelete") markDelete(slug, file, false);
  // The photo matches no card of the catalogue. `apply` moves the file to the
  // NULL wine, in the same way as every other move.
  else if (act === "null") moveTo(slug, file, NULL_SLUG);
  else if (act === "unnull") moveTo(slug, file, "");
}, true);

window.addEventListener("blur", hideCtxMenu);
window.addEventListener("resize", hideCtxMenu);
document.addEventListener("scroll", hideCtxMenu, true);

/* ---- drag and drop: add an image file to the photos of one wine ---- */
function hasFiles(ev) {
  return ev.dataTransfer && [...ev.dataTransfer.types].includes("Files");
}

/* A drag from another browser tab carries no file. It carries the address of the
   picture, as `text/uri-list`, as an `<img>` element in `text/html`, or as plain
   text. The server fetches the address, because the browser may not read the
   bytes of another site. */
const URL_TYPES = ["text/uri-list", "text/html", "text/plain"];
function hasDrop(ev) {
  if (!ev.dataTransfer) return false;
  const t = [...ev.dataTransfer.types];
  // A card of this page. Some browsers add `text/plain` to every drag, so the
  // test for the card MUST come first.
  if (t.includes(PHOTO_TYPE)) return false;
  return t.includes("Files") || URL_TYPES.some(x => t.includes(x));
}

function urlOfDrop(dt) {
  const uri = (dt.getData("text/uri-list") || "").split("\n")
    .map(x => x.trim()).find(x => x && !x.startsWith("#"));
  if (uri) return uri;
  const html = dt.getData("text/html") || "";
  const m = html.match(/<img[^>]+src\s*=\s*["']([^"']+)["']/i);
  if (m) return m[1];
  const text = (dt.getData("text/plain") || "").trim();
  if (/^(https?:|data:image\/)/i.test(text)) return text;
  return "";
}
function rowOfEvent(ev) {
  return (ev.target.closest && ev.target.closest("tr[data-slug]")) || null;
}

/* ---- the drag of a photo card ----

   The card carries the type `application/x-photo`. A picture dragged from another
   tab carries `Files` or a URL type, so the two paths never meet. The value is
   readable on `drop` only; `dragover` can read the type list alone. */
const PHOTO_TYPE = "application/x-photo";
let DRAG = null;        // { slug, file } while a card of this page is in the air

function hasPhoto(ev) {
  return !!ev.dataTransfer && [...ev.dataTransfer.types].includes(PHOTO_TYPE);
}

document.addEventListener("dragstart", ev => {
  const card = ev.target.closest && ev.target.closest(".card[data-file]");
  if (!card) return;
  /* A card of the inbox carries no slug: the file belongs to no wine yet. */
  DRAG = card.dataset.inbox
    ? { inbox: true, file: card.dataset.file }
    : { slug: card.dataset.slug, file: card.dataset.file };
  if (!sideShown()) setSide(true);      // the drop target MUST be on the screen
  ev.dataTransfer.setData(PHOTO_TYPE, JSON.stringify(DRAG));
  ev.dataTransfer.effectAllowed = "move";
  card.classList.add("dragging");
});
document.addEventListener("dragend", ev => {
  DRAG = null;
  document.querySelectorAll(".card.dragging")
    .forEach(c => c.classList.remove("dragging"));
  document.querySelectorAll("tr.photo-drop")
    .forEach(x => x.classList.remove("photo-drop"));
  $("#side").classList.remove("over");
});

/* The sideboard takes a card and holds it. Nothing is sent to the server. */
$("#side").addEventListener("dragover", ev => {
  if (!hasPhoto(ev)) return;
  ev.preventDefault();
  ev.dataTransfer.dropEffect = "move";
  $("#side").classList.add("over");
});
$("#side").addEventListener("dragleave", ev => {
  if (!$("#side").contains(ev.relatedTarget)) $("#side").classList.remove("over");
});
$("#side").addEventListener("drop", ev => {
  if (!hasPhoto(ev)) return;
  ev.preventDefault();
  $("#side").classList.remove("over");
  const d = readPhoto(ev);
  if (!d) return;
  /* A photo of the inbox is already here. The drop takes its target away. */
  if (d.inbox) inboxTarget(d.file, null);
  else hold(d.slug, d.file);
});

/* A wine row takes a card and records the move. */
document.addEventListener("dragover", ev => {
  if (!hasPhoto(ev)) return;
  const tr = rowOfEvent(ev);
  if (!tr) return;
  ev.preventDefault();
  ev.dataTransfer.dropEffect = "move";
  if (!tr.classList.contains("photo-drop")) {
    document.querySelectorAll("tr.photo-drop")
      .forEach(x => x.classList.remove("photo-drop"));
    tr.classList.add("photo-drop");
  }
});
document.addEventListener("dragleave", ev => {
  if (!hasPhoto(ev)) return;
  const tr = rowOfEvent(ev);
  if (tr && !tr.contains(ev.relatedTarget)) tr.classList.remove("photo-drop");
});
document.addEventListener("drop", async ev => {
  if (!hasPhoto(ev)) return;
  const tr = rowOfEvent(ev);
  if (!tr) return;
  ev.preventDefault();
  tr.classList.remove("photo-drop");
  const d = readPhoto(ev);
  if (!d) return;
  const to = tr.dataset.slug;
  /* A photo of the inbox: the row states the wine that the photo shows. The file
     is not moved now. `apply` sends the pair and the server moves the file. */
  if (d.inbox) { inboxTarget(d.file, to); return; }
  if (to === d.slug) {          // back on its own wine: the gesture "put it back"
    unhold(d.slug, d.file);
    render();
    return;
  }
  await moveTo(d.slug, d.file, to);
});

function readPhoto(ev) {
  try {
    const raw = ev.dataTransfer.getData(PHOTO_TYPE);
    if (raw) return JSON.parse(raw);
  } catch (e) { /* fall back on the value that `dragstart` kept */ }
  return DRAG;
}

/* Record the target of one photo. The file is not moved: `apply` moves it and
   drops the label, because the label judged the old pair. */
async function moveTo(slug, file, to) {
  try {
    const res = await fetch("/api/reassign", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ slug, file, to }),
    });
    const out = await res.json();
    if (!res.ok) throw new Error(out.error || res.status);
    (V[slug] = V[slug] || {})[file] =
      { ...((V[slug] || {})[file] || {}), reassign_to: to };
    unhold(slug, file);
    render();
  } catch (e) {
    alert("the move was not recorded: " + e.message);
  }
}

/* A file dropped anywhere else on the page MUST NOT make the browser open the
   file and leave the page. These two handlers only stop that default. */
window.addEventListener("dragover", ev => { if (hasDrop(ev)) ev.preventDefault(); });
window.addEventListener("drop", ev => { if (hasDrop(ev)) ev.preventDefault(); });

document.addEventListener("dragover", ev => {
  const tr = rowOfEvent(ev);
  if (!tr || !hasDrop(ev)) return;
  ev.preventDefault();
  ev.dataTransfer.dropEffect = "copy";
  if (!tr.classList.contains("drop")) {
    document.querySelectorAll("tr.drop").forEach(x => x.classList.remove("drop"));
    tr.classList.add("drop");
  }
});
document.addEventListener("dragleave", ev => {
  const tr = rowOfEvent(ev);
  if (tr && !tr.contains(ev.relatedTarget)) tr.classList.remove("drop");
});
document.addEventListener("drop", async ev => {
  if (!hasDrop(ev)) return;
  ev.preventDefault();
  document.body.classList.remove("dragging");
  const files = [...ev.dataTransfer.files];
  const url = files.length ? "" : urlOfDrop(ev.dataTransfer);
  if (!files.length && !url) return;
  const tr = rowOfEvent(ev);
  if (tr) {
    tr.classList.remove("drop");
    await addPhotos(tr.dataset.slug, files, tr, url);
  } else {
    askWine(files, url);       // dropped beside the table: ask for the slug
  }
});

/* Show a hint while a file is over the page, so the drop target is not a guess. */
window.addEventListener("dragenter", ev => {
  if (hasDrop(ev)) document.body.classList.add("dragging");
});
window.addEventListener("dragleave", ev => {
  if (!ev.relatedTarget) document.body.classList.remove("dragging");
});
window.addEventListener("dragend", () => document.body.classList.remove("dragging"));

/* ---- the dialog that names the wine for a dropped file ---- */
let AD_FILES = [], AD_URL = "";

function askWine(files, url) {
  const images = (files || []).filter(f => f.type.startsWith("image/"));
  if (!images.length && !url) { alert("Drop an image or a picture from a page."); return; }
  AD_FILES = images; AD_URL = url || "";
  $("#ad-files").textContent = url
    ? (url.startsWith("data:") ? "a picture from another tab" : url)
    : (images.length === 1 ? images[0].name
       : `${images.length} files: ` + images.map(f => f.name).join(", "));
  $("#ad-input").value = "";
  $("#ad-list").innerHTML = "";
  $("#ad").classList.add("open");
  $("#ad-input").focus();
}

function closeWine() {
  $("#ad").classList.remove("open"); AD_FILES = []; AD_URL = "";
}

/* Offer the wines whose slug, name, or producer holds what is typed. */
function adSuggest() {
  const q = $("#ad-input").value.trim().toLowerCase();
  if (q.length < 2) { $("#ad-list").innerHTML = ""; return; }
  const hits = reviewRows().filter(r =>
    (r.slug + " " + r.name + " " + r.producer).toLowerCase().includes(q)).slice(0, 5);
  $("#ad-list").innerHTML = hits.map(r => `
    <button class="mv-item" data-slug="${esc(r.slug)}">
      ${r.has_bottle
        ? picHtml(`<img loading="lazy" class="${imgClass().trim()}" src="${
            imgSrc(r.slug)}" alt="">`, r.patched, noLabelMark(r))
        : `<span class="no-img"></span>`}
      <span class="t"><b>${esc(r.name) || esc(r.slug)}</b>
        <div>${esc(r.producer)}</div><div>${esc(r.slug)}</div></span>
    </button>`).join("");
}

async function addToWine(slug) {
  if (!slug) { alert("Name the wine slug."); return; }
  if (!reviewRows().some(r => r.slug === slug)) {
    alert(`No directory my/${slug}. Pick a wine from the list.`);
    return;
  }
  const files = AD_FILES, url = AD_URL;
  closeWine();
  const tr = [...$("#rows").children].find(x => x.dataset.slug === slug);
  await addPhotos(slug, files, tr || null, url);
  if (tr) tr.scrollIntoView({ block: "center" });
}

$("#ad-input").addEventListener("input", adSuggest);
$("#ad-input").addEventListener("keydown", ev => {
  if (ev.key === "Enter") { ev.preventDefault(); addToWine($("#ad-input").value.trim()); }
});
$("#ad-list").addEventListener("click", ev => {
  const item = ev.target.closest(".mv-item");
  if (item) addToWine(item.dataset.slug);
});
$("#ad-ok").addEventListener("click", () => addToWine($("#ad-input").value.trim()));
$("#ad-cancel").addEventListener("click", closeWine);
$("#ad").addEventListener("click", ev => { if (ev.target.id === "ad") closeWine(); });

async function addPhotos(slug, files, tr, url) {
  const images = files.filter(f => f.type.startsWith("image/"));
  if (!images.length && !url) { alert("Drop an image or a picture from a page."); return; }
  if (tr) tr.classList.add("busy");
  const added = [];
  if (url) {
    try {
      const res = await fetch("/api/fetch-image", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slug, url }),
      });
      const out = await res.json();
      if (!res.ok) throw new Error(out.error || res.status);
      const row = ROWS.find(r => r.slug === slug);
      // The wine now holds a photo, so it is a review wine and no longer a
      // catalogue-only row. The filters and the counters MUST see it as one.
      if (row) { row.photos = out.photos; row.catalog_only = false; }
      added.push(out.file);
    } catch (e) {
      alert(`cannot fetch the picture:\n${url}\n\n${e.message}`);
    }
  }
  for (const f of images) {
    try {
      const res = await fetch(
        `/api/upload?slug=${encodeURIComponent(slug)}&name=${encodeURIComponent(f.name)}`,
        { method: "POST", headers: { "Content-Type": f.type }, body: f });
      const out = await res.json();
      if (!res.ok) throw new Error(out.error || res.status);
      const row = ROWS.find(r => r.slug === slug);
      // The wine now holds a photo, so it is a review wine and no longer a
      // catalogue-only row. The filters and the counters MUST see it as one.
      if (row) { row.photos = out.photos; row.catalog_only = false; }
      added.push(out.file);
    } catch (e) {
      alert(`cannot add ${f.name}: ${e.message}`);
    }
  }
  if (tr) tr.classList.remove("busy");
  if (added.length) {
    TOTAL = photoTotal();
    $("#head-sub").textContent = `${tableCount()} wines, ${TOTAL} candidate photos`;
    // The table is NOT drawn again. A wine that no longer matches the filter
    // would leave the table at once: under `no candidate photos (catalogue gap)`
    // the row would go away as soon as the first photo lands on it. The row is
    // brought up to date where it stands. A reload of the page filters again.
    refreshRow(slug);
  }
}

/* Draw the cards and the counts of one row again, without a `render`. */
function refreshRow(slug) {
  const row = ROWS.find(r => r.slug === slug);
  const el = [...$("#rows").children].find(x => x.dataset.slug === slug);
  if (!row || !el) return;
  const strip = el.querySelector(".cards");
  if (strip) strip.innerHTML = cardsHtml(row);
  // The wine holds a photo now, so it is no longer a gap of the photo set.
  el.classList.remove("cat-only");
  const t = tally(row);
  const tgt = [...el.querySelectorAll(".meta .sm")]
    .find(x => x.textContent.includes("photo(s)"));
  if (tgt) tgt.innerHTML = `${t.total} photo(s) ` + rowTags(t);
  stats();
}

/* ---- the move dialog and the copy dialog ----
   One dialog serves both actions. It offers the five wines that the photo most
   likely belongs to, with their catalogue bottle photo, and takes any other slug
   in a field.
   No file is touched here. The target is written to the label file, and the
   button `apply` in the header moves or copies the files.

   A move states that the photo belongs to another wine: the photo leaves this
   wine. A copy states that the photo shows two wines, which happens when one
   label is on two bottles of a variant group: the photo stays here, with its
   label, and the target wine gets its own file. */
let MV_AT = null;      // { slug, file, mode }, where mode is "move" or "copy"

async function askMove(card, slugArg, fileArg, modeArg) {
  const slug = card ? card.dataset.slug : slugArg;
  const file = card ? card.dataset.file : fileArg;
  if (!slug || !file) return;
  const mode = modeArg === "copy" ? "copy" : "move";
  MV_AT = { slug, file, mode };
  const cur = (mode === "copy" ? copiedTo(slug, file) : movedTo(slug, file)) || "";

  $("#mv-h").textContent = mode === "copy"
    ? "Copy this photo to another wine" : "Move this photo to another wine";
  $("#mv-ok").textContent = mode;
  $("#mv-clear").textContent = "clear the " + mode;
  $("#mv-ctx").textContent = `now: ${slug} / ${file}`;
  $("#mv-input").value = cur;
  $("#mv-list").innerHTML = `<div class="mv-sub">loading...</div>`;
  $("#mv").classList.add("open");
  $("#mv-input").focus();

  let targets = [];
  try {
    const res = await fetch(`/api/suggest?slug=${encodeURIComponent(slug)}`);
    targets = (await res.json()).targets || [];
  } catch (e) { /* the field still takes any slug */ }
  if (!MV_AT || MV_AT.slug !== slug || MV_AT.file !== file
      || MV_AT.mode !== mode) return;

  $("#mv-list").innerHTML = targets.length ? targets.map(t => `
    <button class="mv-item ${t.slug === cur ? "sel" : ""}" data-slug="${esc(t.slug)}">
      ${t.has_bottle
        ? picHtml(`<img loading="lazy" class="${imgClass().trim()}" src="${
            imgSrc(t.slug)}" alt="">`, t.patched, noLabelMark(t))
        : `<span class="no-img"></span>`}
      <span class="t">
        <b>${esc(t.name) || esc(t.slug)}</b>${t.in_group
          ? ` <span class="tag grp">variant group</span>` : ""}
        <div>${esc(t.producer)}${t.category ? " &middot; " + esc(t.category) : ""}</div>
        <div>${esc(t.slug)}</div>
      </span>
    </button>`).join("") : `<div class="mv-sub">no near match; type a slug below</div>`;
}

function closeMove() { $("#mv").classList.remove("open"); MV_AT = null; }

/* Write the target of the open dialog, or clear it when `to` is empty. The mode
   of the dialog chooses the route and the field: a move writes `reassign_to`,
   a copy writes `copy_to`. A photo can hold both. */
async function commitMove(to) {
  const at = MV_AT;
  if (!at) return;
  const copy = at.mode === "copy";
  const field = copy ? "copy_to" : "reassign_to";
  const res = await fetch(copy ? "/api/copy" : "/api/reassign", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ slug: at.slug, file: at.file, to }),
  });
  const out = await res.json();
  if (!res.ok) { alert(at.mode + " failed: " + (out.error || res.status)); return; }
  if (to) {
    (V[at.slug] = V[at.slug] || {})[at.file] =
      { ...((V[at.slug] || {})[at.file] || {}), [field]: to };
  } else if (V[at.slug] && V[at.slug][at.file]) {
    delete V[at.slug][at.file][field];
    if (!Object.keys(V[at.slug][at.file]).filter(k => k !== "ts").length) {
      delete V[at.slug][at.file];
      if (!Object.keys(V[at.slug]).length) delete V[at.slug];
    }
  }
  closeMove();
  render();
  if (LB) renderLbStatus();
}

$("#mv-list").addEventListener("click", ev => {
  const item = ev.target.closest(".mv-item");
  if (item) commitMove(item.dataset.slug);
});
$("#mv-ok").addEventListener("click", () => commitMove($("#mv-input").value.trim()));
$("#mv-clear").addEventListener("click", () => commitMove(""));
$("#mv-cancel").addEventListener("click", closeMove);
$("#mv").addEventListener("click", ev => { if (ev.target.id === "mv") closeMove(); });
$("#mv-input").addEventListener("keydown", ev => {
  if (ev.key === "Enter") { ev.preventDefault(); commitMove($("#mv-input").value.trim()); }
});

/* ---- validate ----
   A check reads the photo set and reports the places where the set states two
   things that cannot both be true. The server holds the list of checks, so a new
   check reaches this dialog without a change of the page.
   A check never writes. The result lives in this tab alone. */

function badTitle(f, slug) {
  const others = (f.photos || []).filter(p => p.slug !== slug)
    .map(p => p.slug + " / " + p.file);
  return f.why
    + (f.same_group ? "\nboth wines are in the variant group " + f.group : "")
    + (others.length ? "\nthe same picture is here:\n" + others.join("\n") : "");
}

/* Take the answer of `/api/validate` and build the two lookups of the page. */
function setFailed(out) {
  FAILED = {};
  FAILED_PHOTO = new Map();
  const findings = out.findings || [];
  for (const f of findings) {
    for (const p of f.photos || []) {
      (FAILED[p.slug] = FAILED[p.slug] || []).push(f);
      FAILED_PHOTO.set(p.slug + "\n" + p.file, f);
    }
    for (const x of f.slugs || []) (FAILED[x] = FAILED[x] || []).push(f);
  }
  const n = (out.slugs || []).length;
  FAILED_INFO = findings.length
    ? `${findings.length} finding(s) in ${n} wine(s) \u2014 ${out.photos} photo(s) ` +
      `read in ${out.seconds}s`
    : `no defect found \u2014 ${out.photos} photo(s) read in ${out.seconds}s`;
}

async function askValidate() {
  $("#vd-note").textContent = "";
  $("#vd").classList.add("open");
  if (!CHECKS.length) {
    $("#vd-list").innerHTML = `<div class="mv-sub">loading...</div>`;
    try {
      CHECKS = (await (await fetch("/api/checks")).json()).checks || [];
    } catch (e) { CHECKS = []; }
  }
  $("#vd-list").innerHTML = CHECKS.length ? CHECKS.map(c => `
    <label class="vd-item">
      <input type="checkbox" data-check="${esc(c.id)}" checked>
      <span class="t"><b>${esc(c.title)}</b><div>${esc(c.help)}</div></span>
    </label>`).join("") : `<div class="mv-sub">the server offers no check</div>`;
}

function closeValidate() { $("#vd").classList.remove("open"); }

/* Run the chosen checks. The whole photo set is read, which takes a few seconds,
   so the button states that the work runs. */
async function runValidate() {
  const want = [...document.querySelectorAll("#vd-list input[data-check]")]
    .filter(x => x.checked).map(x => x.dataset.check);
  if (!want.length) { $("#vd-note").textContent = "choose at least one check"; return; }
  const btn = $("#vd-ok");
  btn.disabled = true;
  btn.textContent = "checking...";
  $("#vd-note").textContent = "";
  let out = {};
  try {
    const res = await fetch("/api/validate", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ checks: want }),
    });
    out = await res.json();
    if (!res.ok) throw new Error(out.error || res.status);
  } catch (e) {
    $("#vd-note").textContent = "failed: " + e.message;
    btn.disabled = false;
    btn.textContent = "run";
    return;
  }
  btn.disabled = false;
  btn.textContent = "run";
  setFailed(out);
  closeValidate();
  // The table holds this view until the reviewer changes the filter.
  $("#filter").value = "failed";
  $("#validate").classList.add("on");
  render();
}

$("#validate").addEventListener("click", askValidate);
$("#vd-ok").addEventListener("click", runValidate);
$("#vd-cancel").addEventListener("click", closeValidate);
$("#vd").addEventListener("click", ev => { if (ev.target.id === "vd") closeValidate(); });

/* ---- the variant group of a whole wine ----

   The server keeps the hand-made pairs in `manual-groups.json` and joins them
   with the groups that `scripts/08_variants.py` generates. A wine that is in no
   group joins the group of the wine that the reviewer names. Two wines that are
   each already in a group are refused by the server, and the reason is stated in
   the dialog. */
let GP_AT = null;                       // the slug that the dialog acts on

/* Show only the wines of one variant group, or every wine again. The search and
   the two other filters are cleared, so every member of the group reaches the
   screen. The sort is kept, because the rows of one group stand together in
   every sort order. */
function showGroup(gid) {
  const want = GROUPS[gid] ? gid : "";
  if (want === GROUP_FILTER) return;
  GROUP_FILTER = want;
  if (want) {
    $("#q").value = "";
    $("#filter").value = "all";
    $("#slugsel").value = "all";
  }
  render();
  if (want) window.scrollTo({ top: 0 });
}

function closeGroup() { $("#gp").classList.remove("open"); GP_AT = null; }

async function askGroup(slug) {
  if (!slug) return;
  GP_AT = slug;
  const r = ROWS.find(x => x.slug === slug), g = r ? grpOf(r) : null;
  $("#gp-ctx").textContent = g
    ? `${slug}\nin group ${g.id} of ${g.slugs.length} wines: ` +
      g.slugs.filter(x => x !== slug).join(", ")
    : `${slug}\nin no group yet`;
  $("#gp-err").textContent = "";
  $("#gp-input").value = "";
  $("#gp-list").innerHTML = `<div class="mv-sub">loading...</div>`;
  $("#gp").classList.add("open");
  $("#gp-input").focus();

  let targets = [];
  try {
    const res = await fetch(`/api/suggest?slug=${encodeURIComponent(slug)}`);
    targets = (await res.json()).targets || [];
  } catch (e) { /* the field still takes any slug */ }
  if (GP_AT !== slug) return;
  targets = targets.filter(t => !g || !g.slugs.includes(t.slug));
  $("#gp-list").innerHTML = targets.length ? targets.map(t => `
    <button class="mv-item" data-slug="${esc(t.slug)}">
      ${t.has_bottle
        ? picHtml(`<img loading="lazy" class="${imgClass().trim()}" src="${
            imgSrc(t.slug)}" alt="">`, t.patched, noLabelMark(t))
        : `<span class="no-img"></span>`}
      <span class="t">
        <b>${esc(t.name) || esc(t.slug)}</b>${t.in_group
          ? ` <span class="tag grp">variant group</span>` : ""}
        <div>${esc(t.producer)}${t.category ? " &middot; " + esc(t.category) : ""}</div>
        <div>${esc(t.slug)}</div>
      </span>
    </button>`).join("") : `<div class="mv-sub">no near match; type a slug below</div>`;
}

async function commitGroup(target) {
  const slug = GP_AT;
  if (!slug) return;
  if (!target) { $("#gp-err").textContent = "name a wine slug"; return; }
  $("#gp-err").textContent = "";
  $("#gp-ok").classList.add("saving");
  let out = {}, res;
  try {
    res = await fetch("/api/group", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ slug, target }),
    });
    try { out = await res.json(); } catch (e) { out = {}; }
  } catch (e) {
    $("#gp-ok").classList.remove("saving");
    $("#gp-err").textContent = "the server did not answer";
    return;
  }
  $("#gp-ok").classList.remove("saving");
  if (!res.ok) {
    $("#gp-err").textContent = out.error || ("group failed: " + res.status);
    return;
  }
  if (out.changed === false) {
    $("#gp-err").textContent = out.note || "nothing changed";
    return;
  }
  // The server answers the rebuilt rows, because a group changes the order of
  // the table and the colour of the block.
  if (out.rows) {
    ROWS = out.rows;
    GROUPS = out.groups || GROUPS;
    V = out.labels || V;
    W = out.wines || W;
    EXC = out.excluded || EXC;
  }
  closeGroup();
  render();
}

$("#gp-list").addEventListener("click", ev => {
  const item = ev.target.closest(".mv-item");
  if (item) commitGroup(item.dataset.slug);
});
$("#gp-ok").addEventListener("click", () => commitGroup($("#gp-input").value.trim()));
$("#gp-cancel").addEventListener("click", closeGroup);
$("#gp").addEventListener("click", ev => { if (ev.target.id === "gp") closeGroup(); });
$("#gp-input").addEventListener("keydown", ev => {
  if (ev.key === "Enter") { ev.preventDefault(); commitGroup($("#gp-input").value.trim()); }
});

/* ---- the note about a whole wine ----
   The field stands in the wine column. It is one line high until it is used, and
   it opens while it holds a text or the cursor. The text is saved after a pause,
   and the table is NOT rendered again, so the cursor stays in the field. */
const WN_TIMERS = new Map();

async function saveWineNote(el) {
  const slug = el.dataset.wine, text = el.value.trim();
  if (wineNote(slug) === text) return;
  el.classList.add("saving");
  try {
    const res = await fetch("/api/wine-comment", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ slug, text }),
    });
    const out = await res.json();
    if (!res.ok) throw new Error(out.error || res.status);
  } catch (e) {
    el.classList.remove("saving");
    alert("the note is not saved: " + e.message);
    return;
  }
  if (text) W[slug] = { comment: text };
  else delete W[slug];
  el.classList.remove("saving");
  el.classList.toggle("filled", !!text);
}

document.addEventListener("input", ev => {
  const el = ev.target.closest && ev.target.closest(".wine-note");
  if (!el) return;
  clearTimeout(WN_TIMERS.get(el));
  WN_TIMERS.set(el, setTimeout(() => saveWineNote(el), 700));
});
document.addEventListener("blur", ev => {
  const el = ev.target.closest && ev.target.closest(".wine-note");
  if (!el) return;
  clearTimeout(WN_TIMERS.get(el));
  saveWineNote(el);
}, true);

/* ---- the exclusion of a whole slug ----
   A slug that holds an error, most often a wrong bottle photo, is taken out of
   the benchmark. The photos of such a slug are NOT used. The reason is asked at
   the click and is written to `excluded-slugs.json`. */
async function toggleExclude(btn) {
  const slug = btn.dataset.excl, was = isExcluded(slug);
  let reason = "";
  if (!was) {
    reason = (window.prompt(
      "Exclude " + slug + " from the benchmark.\n" +
      "State the error, for example \"wrong bottle photo in the catalogue\".",
      "wrong bottle photo in the catalogue") || "").trim();
    if (!reason) return;                 // the reviewer cancelled the question
  } else if (!window.confirm("Include " + slug + " in the benchmark again?")) {
    return;
  }
  btn.classList.add("saving");
  let out = {};
  try {
    const res = await fetch("/api/exclude", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ slug, excluded: !was, reason }),
    });
    out = await res.json();
    if (!res.ok) throw new Error(out.error || res.status);
  } catch (e) {
    btn.classList.remove("saving");
    alert("the exclusion is not saved: " + e.message);
    return;
  }
  if (was) delete EXC[slug];
  else EXC[slug] = out.entry || { reason };
  render();
}

/* ---- the comment panel of the large view ----
   The text is saved as it is typed, after a short pause. A move to another photo
   and a close of the view flush the pending text first, so nothing is lost. */
let CMT_AT = null;        // { slug, file } that the field belongs to
let CMT_TIMER = null;

function cmtState(text, cls) {
  const el = $("#cmt-state");
  el.textContent = text;
  el.className = cls || "";
}

async function saveComment(at, text) {
  if (!at) return;
  const cur = commentOf(at.slug, at.file);
  if (cur === text) { cmtState(text ? "saved" : "", text ? "saved" : ""); return; }
  cmtState("saving...");
  let out = {};
  try {
    const res = await fetch("/api/comment", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ slug: at.slug, file: at.file, text }),
    });
    out = await res.json();
    if (!res.ok) throw new Error(out.error || res.status);
  } catch (e) {
    cmtState("not saved: " + e.message, "failed");
    return;
  }
  const entry = (V[at.slug] = V[at.slug] || {})[at.file] || {};
  if (text) {
    entry.comment = text;
    V[at.slug][at.file] = entry;
  } else if (V[at.slug][at.file]) {
    delete V[at.slug][at.file].comment;
    if (!Object.keys(V[at.slug][at.file]).filter(k => k !== "ts").length) {
      delete V[at.slug][at.file];
      if (!Object.keys(V[at.slug]).length) delete V[at.slug];
    }
  }
  cmtState(text ? "saved" : "", text ? "saved" : "");
  markCard(at.slug, at.file);
}

/* Update the one card that the comment belongs to, without a full render. */
function markCard(slug, file) {
  const card = cardOf(slug, file);
  if (!card) return;
  const note = commentOf(slug, file);
  card.classList.toggle("noted", !!note);
  const old = card.querySelector(".note-badge");
  if (old) old.remove();
  if (note) card.insertAdjacentHTML("afterbegin", noteBadge(note));
  const row = card.closest("tr");
  const r = ROWS.find(x => x.slug === slug);
  if (r && row) {
    const t = tally(r), sm = row.querySelectorAll(".meta .sm");
    const tgt = [...sm].find(el => el.textContent.includes("photo(s)"));
    if (tgt) tgt.innerHTML = `${t.total} photo(s) ` + rowTags(t);
  }
}

function flushComment() {
  if (CMT_TIMER) { clearTimeout(CMT_TIMER); CMT_TIMER = null; }
  if (CMT_AT) saveComment(CMT_AT, $("#cmt").value.trim());
}

function loadComment(r, pi) {
  flushComment();
  const p = r.photos[pi];
  $("#cmt").disabled = !p;
  if (!p) {
    CMT_AT = null;
    $("#cmt").value = "";
    $("#cmt-ctx").textContent = `${r.slug} \u2014 no candidate photo`;
    cmtState("", "");
    return;
  }
  CMT_AT = { slug: r.slug, file: p.file };
  $("#cmt").value = commentOf(r.slug, p.file);
  $("#cmt-ctx").textContent = `${r.slug} / ${p.file}`;
  cmtState($("#cmt").value ? "saved" : "", $("#cmt").value ? "saved" : "");
}

$("#cmt").addEventListener("input", () => {
  cmtState("typing...");
  if (CMT_TIMER) clearTimeout(CMT_TIMER);
  const at = CMT_AT;
  CMT_TIMER = setTimeout(() => {
    CMT_TIMER = null;
    saveComment(at, $("#cmt").value.trim());
  }, 600);
});
$("#cmt").addEventListener("blur", flushComment);
$("#cmt-clear").addEventListener("click", () => {
  $("#cmt").value = "";
  flushComment();
  $("#cmt").focus();
});
window.addEventListener("beforeunload", flushComment);

/* The view of the table lives in the query string: the search and the three
   selects. The fragment keeps its own job, the open photo, so an address can
   state both. A control at its default value is left out, so a plain view keeps
   a plain address. */
const VIEW_PARAMS = [
  ["q", "#q", ""],
  ["filter", "#filter", "all"],
  ["sort", "#sort", "slug"],
  ["slugs", "#slugsel", "all"],
  ["img", "#imgkind", "package"],
];

/* One variant group, or "" for every wine. It has no control of its own: the
   tag `variant group of N` on a row switches it on, and the count line switches
   it off. It travels in the query string beside the controls. */
let GROUP_FILTER = "";

/* Write the controls into the query string. The fragment is kept as it is. */
function writeViewToUrl() {
  const p = new URLSearchParams();
  for (const [key, sel, dflt] of VIEW_PARAMS) {
    const v = $(sel).value.trim();
    if (v && v !== dflt) p.set(key, v);
  }
  if (GROUP_FILTER) p.set("group", GROUP_FILTER);
  const qs = p.toString();
  const want = location.pathname + (qs ? "?" + qs : "") + location.hash;
  if (want === location.pathname + location.search + location.hash) return;
  history.replaceState(null, "", want);
}

/* Set the controls from the query string. It runs once, before the first draw.
   An unknown value of a select is dropped, so a hand-typed address cannot put a
   select into a state that its options do not hold. */
function readViewFromUrl() {
  const p = new URLSearchParams(location.search);
  for (const [key, sel, dflt] of VIEW_PARAMS) {
    if (!p.has(key)) continue;
    const el = $(sel), v = p.get(key);
    if (el.tagName === "SELECT" &&
        ![...el.options].some(o => o.value === v)) continue;
    el.value = v;
  }
  // An unknown group id is dropped, as an unknown value of a select is.
  const gid = p.get("group") || "";
  GROUP_FILTER = GROUPS[gid] ? gid : "";
}

/* The address of the photo on screen is `#<slug>/<file name>`. The address is
   written with `replaceState`, so the arrow keys do not fill the history. */
let HASH_SELF = "";
function setHash(frag) {
  const want = frag ? "#" + frag.split("/").map(encodeURIComponent).join("/") : "";
  if (location.hash === want || (!want && !location.hash)) return;
  HASH_SELF = want;
  history.replaceState(null, "", want || location.pathname + location.search);
}

/* Open the photo that the address names. The filter and the search are cleared
   when the wine is not in the current view, so a pasted address always opens. */
function openFromHash() {
  const raw = location.hash.replace(/^#\/?/, "");
  if (!raw) return false;
  const cut = raw.indexOf("/");
  // `#<slug>` alone opens a wine that holds no candidate photo.
  const slug = decodeURIComponent(cut < 0 ? raw : raw.slice(0, cut));
  const file = cut < 0 ? "" : decodeURIComponent(raw.slice(cut + 1));
  // `all` lists every wine of the catalogue, so one scope shows every row. The
  // filter falls back to `all` when the present one leaves the wine out.
  const row = ROWS.find(r => r.slug === slug);
  if (!row) return false;
  if (!VIEW.some(r => r.slug === slug)) {
    $("#filter").value = "all";
    $("#q").value = "";
    render();
  }
  const wi = VIEW.findIndex(r => r.slug === slug);
  if (wi < 0) return false;
  const pi = VIEW[wi].photos.findIndex(p => p.file === file);
  showLightbox(wi, pi < 0 ? 0 : pi);
  return true;
}

window.addEventListener("hashchange", () => {
  if (location.hash === HASH_SELF) return;   // the change came from this page
  if (!openFromHash()) closeLightbox();
});

document.addEventListener("click", ev => {
  if (ev.target.id === "apply") { applyMoves(ev.target); return; }

  const copy = ev.target.closest(".copy");
  if (copy) { copyFromButton(copy); return; }

  if (ev.target.id === "grp-clear") { showGroup(""); return; }

  const gshow = ev.target.closest("[data-grp-show]");
  if (gshow) {                       // the same tag again shows every wine
    showGroup(gshow.dataset.grpShow === GROUP_FILTER ? "" : gshow.dataset.grpShow);
    return;
  }

  const gpb = ev.target.closest(".grp-btn");
  if (gpb) { askGroup(gpb.dataset.group); return; }

  const exb = ev.target.closest(".excl-btn");
  if (exb) { toggleExclude(exb); return; }

  const move = ev.target.closest(".move");
  if (move) { askMove(move.closest(".card")); return; }

  // `.cpy`, not `.copy`: `.copy` is the button that writes a name to the clipboard.
  const cpyb = ev.target.closest(".cpy");
  if (cpyb) { askMove(cpyb.closest(".card"), null, null, "copy"); return; }

  const clear = ev.target.closest("[data-clear]");
  if (clear) {
    inboxTarget(clear.closest(".card").dataset.file, null);
    return;
  }

  const back = ev.target.closest("[data-back]");
  if (back) {
    const c = back.closest(".card");
    unhold(c.dataset.slug, c.dataset.file);
    render();
    return;
  }

  const btn = ev.target.closest(".btns button");
  if (btn) {
    const c = btn.closest(".card");
    setLabel(c.dataset.slug, c.dataset.file, btn.dataset.l);
    return;
  }

  if (ev.target.closest("#lb")) {   // a click on an image or in the panel keeps it open
    if (!ev.target.matches(".lb-fig img") && !ev.target.closest(".lb-side")) {
      closeLightbox();
    }
    return;
  }

  const img = ev.target.closest("img[data-full]");
  if (!img) return;
  const tr = img.closest("tr");
  if (!tr) return;
  const wi = VIEW.findIndex(x => x.slug === tr.dataset.slug);
  if (wi < 0) return;
  const card = img.closest(".card");
  // A click on the bottle opens the same wine at its first photo.
  const pi = card ? VIEW[wi].photos.findIndex(p => p.file === card.dataset.file) : 0;
  showLightbox(wi, pi < 0 ? 0 : pi);
});

document.addEventListener("keydown", ev => {
  // A field takes every key. Esc leaves the field; a second Esc closes the view.
  const tag = ev.target && ev.target.tagName;
  if (tag === "TEXTAREA" || tag === "INPUT" || tag === "SELECT") {
    if (ev.key === "Escape") {
      if ($("#ad").classList.contains("open")) closeWine();
      else if ($("#gp").classList.contains("open")) closeGroup();
      else if ($("#mv").classList.contains("open")) closeMove();
      else ev.target.blur();
      ev.stopPropagation();
    }
    return;
  }
  if (ev.key === "Escape") {
    if (!$("#ctxmenu").hidden) hideCtxMenu();
    else if ($("#vd").classList.contains("open")) closeValidate();
    else if ($("#ad").classList.contains("open")) closeWine();
    else if ($("#gp").classList.contains("open")) closeGroup();
    else if ($("#mv").classList.contains("open")) closeMove();
    else closeLightbox();
    return;
  }
  if ($("#mv").classList.contains("open") || $("#ad").classList.contains("open")
      || $("#gp").classList.contains("open") || $("#vd").classList.contains("open")) {
    return;                                          // a dialog takes the keys
  }
  if ((ev.key === "s" || ev.key === "S") && !ev.metaKey && !ev.ctrlKey && !ev.altKey) {
    ev.preventDefault();
    setSide(!sideShown());
    return;
  }
  if (!LB || !$("#lb").classList.contains("open")) return;
  if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
  const step = { ArrowRight: 1, ArrowLeft: -1 }[ev.key];
  if (step !== undefined) { ev.preventDefault(); showLightbox(LB.wine, LB.photo + step); return; }
  const wstep = { ArrowDown: 1, ArrowUp: -1 }[ev.key];
  if (wstep !== undefined) { ev.preventDefault(); stepWine(wstep); return; }
  // "1" positive, "2" negative sample, "3" unusable, "4" this wine other design.
  // The same key again clears the label. "m" moves the photo to another slug,
  // "c" copies it to another slug and leaves this one where it is.
  // A wine with no candidate photo holds nothing to label and nothing to move.
  const lbPhoto = (VIEW[LB.wine].photos || [])[LB.photo];
  const askKey = { m: "move", M: "move", c: "copy", C: "copy" }[ev.key];
  if (askKey) {
    ev.preventDefault();
    if (!lbPhoto) return;
    const r = VIEW[LB.wine];
    askMove(cardOf(r.slug, lbPhoto.file), r.slug, lbPhoto.file, askKey);
    return;
  }
  // "0" states that no card of the catalogue shows this photo. The photo goes to
  // the NULL wine, in the same way as a move to another wine: `apply` moves the
  // file. The same key again clears the pending move.
  if (ev.key === "0") {
    ev.preventDefault();
    if (!lbPhoto) return;
    const r = VIEW[LB.wine];
    if (r.slug === NULL_SLUG) return;         // the photo is already there
    moveTo(r.slug, lbPhoto.file,
           movedTo(r.slug, lbPhoto.file) === NULL_SLUG ? "" : NULL_SLUG);
    return;
  }
  const want = KEY_OF[ev.key];
  if (want) {
    ev.preventDefault();
    if (!lbPhoto) return;
    setLabel(VIEW[LB.wine].slug, lbPhoto.file, want);
  }
});
for (const id of ["#sort", "#filter", "#slugsel", "#imgkind"]) {
  $(id).addEventListener("change", render);
}
// The button is marked only while the table shows the wines that a check reported.
$("#filter").addEventListener("change", () => {
  $("#validate").classList.toggle("on", $("#filter").value === "failed" && !!FAILED);
});
$("#export-csv").addEventListener("click", exportCurrentViewCsv);
let t = null;
$("#q").addEventListener("input", () => { clearTimeout(t); t = setTimeout(render, 180); });

(async function init() {
  const data = await (await fetch("/api/rows")).json();
  ROWS = data.rows; V = data.labels || {}; W = data.wines || {};
  EXC = data.excluded || {};
  setInbox(data.inbox);
  GROUPS = data.groups || {}; SLUGS = data.slugs || [];
  $("#slug-list").innerHTML = SLUGS.map(x => `<option value="${esc(x)}">`).join("");
  $("#my-slug-list").innerHTML =
    reviewRows().map(r => `<option value="${esc(r.slug)}">`).join("");
  initSide();
  // The selector appears only when a label crop is present. Without the two
  // directories of `config.yaml` every wine would fall back to its package
  // picture, and the choice would say nothing.
  $("#imgkind-wrap").hidden = !ROWS.some(r => r.has_label || r.has_label_box);
  TOTAL = photoTotal();
  $("#head-sub").textContent = `${tableCount()} wines, ${TOTAL} candidate photos`;
  readViewFromUrl();
  render();
  openFromHash();
})();
</script>
</body>
</html>
"""


# ------------------------------------------------------------ the page of the runs


PAGE_RUNS = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Svoe Vino match runs</title>
<style>
""" + THEME_CSS + PATCH_CSS + """
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--text);
  font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
header {
  position: sticky; top: 0; z-index: 10;
  background: var(--panel); border-bottom: 1px solid var(--line);
  padding: 10px 16px; box-shadow: var(--shadow);
}
h1 { font-size: 15px; margin: 0 0 8px; font-weight: 650; }
h1 .sub { color: var(--muted); font-weight: 400; }
.head-top { display: flex; align-items: baseline; gap: 14px; }
.head-top h1 { margin-right: auto; }
.nav { display: flex; gap: 6px; flex: none; }
.nav a {
  color: var(--muted); text-decoration: none; font-size: 13px; font-weight: 600;
  padding: 3px 10px; border: 1px solid var(--line); border-radius: 6px;
  background: var(--panel-2);
}
.nav a:hover { color: var(--text); border-color: var(--accent); }
.nav a.on { color: var(--text); border-color: var(--accent); background: var(--panel); }
h2 { font-size: 13px; margin: 18px 0 8px; font-weight: 650; }
a { color: var(--accent); }
main { padding: 12px 16px 64px; }
.bar { display: flex; flex-wrap: wrap; gap: 8px 14px; align-items: center; }
.bar label { color: var(--muted); font-size: 12px; display: flex; gap: 5px; align-items: center; }
select, input[type=search] {
  background: var(--panel-2); color: var(--text); border: 1px solid var(--line);
  border-radius: 6px; padding: 4px 7px; font: inherit; font-size: 13px;
}
input[type=search] { min-width: 210px; }
button {
  font: inherit; font-size: 12px; padding: 4px 10px; border-radius: 6px;
  border: 1px solid var(--line); background: var(--panel-2); color: var(--text);
  cursor: pointer;
}
button:hover { border-color: var(--accent); }
table { border-collapse: separate; border-spacing: 0; width: 100%; }
th { text-align: left; font-size: 12px; color: var(--muted); font-weight: 600;
     padding: 6px 10px; border-bottom: 1px solid var(--line); white-space: nowrap; }
td { padding: 8px 10px; vertical-align: top; }
tbody tr { background: var(--panel); }
tbody tr + tr td { border-top: 1px solid var(--line); }
#runs th[data-k] { cursor: pointer; user-select: none; }
#runs th[data-k]:hover { color: var(--text); }
#runs th.sorted { color: var(--accent); }
#runs th[data-k]::after { content: attr(data-dir); font-size: 9px; margin-left: 3px; }
#met .note { margin: 8px 0 10px; }
#met .warn { margin: 0 0 10px; padding: 7px 10px; border-radius: 6px;
             background: var(--var-bg); color: var(--text);
             border: 1px solid var(--var); }
.was { color: var(--var); }
#runs tbody tr { cursor: pointer; }
#runs tbody tr:hover { background: var(--panel-2); }
#runs tbody tr.on { background: var(--grp-a); }
.num { font-variant-numeric: tabular-nums; text-align: right; }
.muted { color: var(--muted); }
.empty { color: var(--muted); font-style: italic; }
.tag { padding: 1px 6px; border-radius: 999px; font-size: 11px; border: 1px solid var(--line); }
.tag.pos { color: var(--pos); background: var(--pos-bg); border-color: transparent; }
.tag.neg { color: var(--neg); background: var(--neg-bg); border-color: transparent; }
.tag.var { color: var(--var); background: var(--var-bg); border-color: transparent; }
.tag.unl { color: var(--muted); }
.tag.bad { color: #fff; background: var(--exc); border-color: transparent; }
.tag.ok { color: var(--pos); border-color: var(--pos); }
.tag.dry { color: var(--muted); }

/* the metric cards */
.cards { display: flex; flex-wrap: wrap; gap: 10px; }
.card {
  background: var(--panel); border: 1px solid var(--line); border-radius: 8px;
  padding: 8px 12px; min-width: 116px;
}
.card .k { color: var(--muted); font-size: 11px; }
.card .v { font-size: 20px; font-weight: 650; font-variant-numeric: tabular-nums; }
.card.bad .v { color: var(--exc); }
.card.good .v { color: var(--pos); }

/* the histogram of the rank of the true slug */
.hist { display: flex; gap: 6px; align-items: flex-end; height: 74px; margin-top: 4px; }
.hist .col { display: flex; flex-direction: column; justify-content: flex-end;
             align-items: center; gap: 3px; min-width: 42px; }
.hist .bar-i { width: 100%; background: var(--accent); border-radius: 3px 3px 0 0; min-height: 2px; }
.hist .col.absent .bar-i { background: var(--exc); }
.hist .lab { font-size: 10px; color: var(--muted); }
.hist .cnt { font-size: 11px; font-variant-numeric: tabular-nums; }

/* one result row */
.qcell { width: 190px; min-width: 190px; }
.qphoto {
  width: 170px; height: 170px; object-fit: contain; background: var(--panel-2);
  border: 1px solid var(--line); border-radius: 6px; padding: 3px;
}
.strip { display: flex; gap: 8px; flex-wrap: wrap; }
.cand {
  width: 104px; background: var(--panel-2); border: 2px solid transparent;
  border-radius: 8px; padding: 5px;
}
.cand.truth { border-color: var(--pos); background: var(--pos-bg); }
.cand.forbidden { border-color: var(--exc); background: var(--exc-bg); }
.cand.missing { border-style: dashed; border-color: var(--pos); background: transparent; }
/* the true wine of a negative photo, which a byte-equal positive photo names */
.cand.twin { border-style: dashed; border-color: var(--pos); background: var(--pos-bg); }
.cand.twin.missing { background: transparent; }
.cand.apart { margin-left: 26px; }
.cand img, .cand .nobottle {
  width: 92px; height: 116px; object-fit: contain; display: block;
  background: var(--panel); border: 1px solid var(--line); border-radius: 4px;
}
.cand .nobottle { display: flex; align-items: center; justify-content: center;
                  color: var(--muted); font-size: 10px; text-align: center; }
.cand .r { font-size: 11px; color: var(--muted); display: flex; justify-content: space-between; }
.cand .sl { font-size: 10px; word-break: break-all; line-height: 1.25; margin-top: 2px; }
.sm { font-size: 12px; color: var(--muted); word-break: break-all; }
#more { margin-top: 12px; }
#lb { position: fixed; inset: 0; background: rgba(0,0,0,.82); display: none;
      align-items: center; justify-content: center; z-index: 50; }
#lb.on { display: flex; }
#lb img { max-width: 92vw; max-height: 92vh; object-fit: contain; }
</style>
</head>
<body>
<header>
  <div class="head-top">
    <h1>Match runs <span class="sub" id="head-sub"></span></h1>
    <nav class="nav"><a href="/">Review</a><a class="on" href="/runs">Runs</a><a
      href="/clusters">Clusters</a></nav>
  </div>
  <div class="bar">
    <label>Show
      <select id="filter">
        <option value="all">every photo</option>
        <option value="miss">positive: the true slug is not at rank 1</option>
        <option value="near">positive: the true slug is at rank 2 or deeper</option>
        <option value="rank_2_5">positive: the true slug is at rank 2 to 5</option>
        <option value="after_5">positive: the true slug is not in the top 5</option>
        <option value="after_10">positive: the true slug is not in the top 10</option>
        <option value="absent">positive: the true slug never came back</option>
        <option value="hit">positive: correct at rank 1</option>
        <option value="false_match">negative: the slug came back at rank 1</option>
        <option value="negative_in_topk">negative: the slug is anywhere in the list</option>
        <option value="negative">every negative photo</option>
        <option value="no_match">no match: every photo that matches no card</option>
        <option value="no_match_answered">no match: the backend answered a card anyway</option>
        <option value="negative_above_positive">negative: the wrong wine stands above the true wine</option>
        <option value="twin_conflict">set defect: one photo is positive for two wines</option>
        <option value="error">the request failed</option>
      </select>
    </label>
    <label>Sort
      <select id="sort">
        <option value="manifest">the order of the run</option>
        <option value="worst">the most wrong first</option>
        <option value="rank">the rank of the true slug</option>
        <option value="score_desc">the score of the answer, highest first</option>
        <option value="score_asc">the score of the answer, lowest first</option>
        <option value="latency_desc">the slowest answer first</option>
        <option value="latency_asc">the fastest answer first</option>
        <option value="path">the photo path, A-Z</option>
      </select>
    </label>
    <label>Find <input id="q" type="search" placeholder="slug or predicted slug"></label>
    <span class="muted" id="count"></span>
  </div>
</header>
<main>
  <h2>Runs</h2>
  <p class="sm">Click a column to sort. Click it again to turn the order around.</p>
  <table id="runs"><thead><tr>
    <th data-k="id">run</th>
    <th data-k="backend">backend</th>
    <th data-k="started">started</th>
    <th data-k="queries" class="num">queries</th>
    <th data-k="match_share" class="num">match share</th>
    <th data-k="f1_at_1" class="num">F1@1</th>
    <th data-k="f1_at_5" class="num">F1@5</th>
    <th data-k="recall_at_5" class="num">R@5</th>
    <th data-k="false_match_at_1" class="num">false match @1</th>
    <th data-k="within_sla_share" class="num">within SLA</th>
    <th data-k="latency_median" class="num">median ms</th>
  </tr></thead><tbody id="runs-body"></tbody></table>

  <div id="detail" hidden>
    <h2 id="det-h">Metrics</h2>
    <div class="cards" id="met"></div>
    <div id="hists"></div>
    <h2>Photos</h2>
    <table id="res"><thead><tr>
      <th class="qcell">matched image</th>
      <th>candidates, the highest score first</th>
    </tr></thead><tbody id="res-body"></tbody></table>
    <button id="more" hidden>load more</button>
  </div>
</main>
<div id="lb"><img alt=""></div>
<script>
""" + PATCH_JS + """
const $ = s => document.querySelector(s);
const esc = s => (s == null ? "" : String(s)).replace(/[&<>"']/g,
  c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pct = v => v === null || v === undefined ? "\\u2014" : (100 * v).toFixed(1) + "%";
const numOr = v => v === null || v === undefined ? "\\u2014" : v;

let RUNS = [], CUR = null, OFFSET = 0, TOTAL = 0;
/* The slugs whose catalogue photo comes from `patch_dir`. A row of a run holds a
   slug alone and no catalogue record, so `init` reads the list from
   `/api/patched` and every candidate image asks this set. */
let PATCHED = new Set();
const isPatched = slug => PATCHED.has(slug);
/* The order of the table of the runs. The newest run stands first at the start. */
let RSORT = { key: "id", dir: -1 };
const LABEL_TAG = { positive: "pos", negative: "neg", variant: "var",
                    unlabelled: "unl" };

/* ---- the table of the runs ---- */
function sortedRuns() {
  const k = RSORT.key, dir = RSORT.dir;
  return RUNS.slice().sort((a, b) => {
    let x = a[k], y = b[k];
    // a run with no value for this column stands last, whatever the direction
    const nx = x === null || x === undefined, ny = y === null || y === undefined;
    if (nx && ny) return String(a.id).localeCompare(String(b.id)) * -1;
    if (nx) return 1;
    if (ny) return -1;
    if (typeof x === "number" && typeof y === "number") return (x - y) * dir;
    return String(x).localeCompare(String(y)) * dir;
  });
}

function renderRuns() {
  $("#runs-body").innerHTML = sortedRuns().map(r => `
    <tr data-id="${esc(r.id)}" class="${CUR === r.id ? "on" : ""}">
      <td>${esc(r.id)} ${r.dry_run ? '<span class="tag dry">dry run</span>' : ""}
        ${r.subset ? `<span class="tag var" title="a repeat of ${esc(r.subset.based_on)} at depth ${r.subset.rerun_depth}">repeat d${r.subset.rerun_depth}</span>` : ""}</td>
      <td>${esc(r.backend)}</td>
      <td class="sm">${esc((r.started || "").replace("T", " ").slice(0, 19))}</td>
      <td class="num">${numOr(r.queries)}</td>
      <td class="num">${pct(r.match_share)}</td>
      <td class="num">${r.f1_at_1 === null || r.f1_at_1 === undefined ? "\u2014" : r.f1_at_1.toFixed(3)}</td>
      <td class="num">${r.f1_at_5 === null || r.f1_at_5 === undefined ? "\u2014" : r.f1_at_5.toFixed(3)}</td>
      <td class="num">${pct(r.recall_at_5)}</td>
      <td class="num">${numOr(r.false_match_at_1)}</td>
      <td class="num">${pct(r.within_sla_share)}</td>
      <td class="num">${numOr(r.latency_median)}</td>
    </tr>`).join("");
  for (const th of document.querySelectorAll("#runs th[data-k]")) {
    const on = th.dataset.k === RSORT.key;
    th.classList.toggle("sorted", on);
    th.dataset.dir = on ? (RSORT.dir > 0 ? "\u25b2" : "\u25bc") : "";
  }
  $("#head-sub").textContent = `${RUNS.length} run(s)`;
}

/* ---- the metrics of one run ---- */
function card(k, v, cls) {
  return `<div class="card ${cls || ""}"><div class="k">${esc(k)}</div>
          <div class="v">${v}</div></div>`;
}

function histogram(title, hist, note) {
  const order = ["1", "2", "3", "4-10", ">10", "absent"];
  const keys = order.filter(k => hist && hist[k] !== undefined);
  if (!keys.length) return "";
  const max = Math.max(...keys.map(k => hist[k]));
  const cols = keys.map(k => `
    <div class="col ${k === "absent" ? "absent" : ""}">
      <div class="cnt">${hist[k]}</div>
      <div class="bar-i" style="height:${Math.round(60 * hist[k] / max)}px"></div>
      <div class="lab">${esc(k)}</div>
    </div>`).join("");
  return `<h2>${esc(title)}</h2><div class="sm">${esc(note || "")}</div>
          <div class="hist">${cols}</div>`;
}

function renderMetrics(met, head) {
  const pos = met.positive || {}, neg = met.negative || {}, lat = met.latency_ms || {};
  const dash = "\\u2014";
  const f1 = b => b && b.f1 !== null && b.f1 !== undefined ? b.f1.toFixed(3) : dash;
  const fix = v => v === null || v === undefined ? dash : v.toFixed(3);
  const share = pos.match_share === undefined ? pos.recall_at_1 : pos.match_share;
  const target = pos.target_match_share || 0.9;
  const margin = pos.score_margin || {};
  const sla = lat.sla_ms || 3000;
  /* The first row holds the numbers that the specification of the task names:
     the share of the matches with its target of 90 to 100 percent, the F1 of the
     top-1 and of the top-5 cards, the answer inside the SLA of 3 seconds, and the
     near-duplicate errors, which the specification calls the main source of the
     errors. */
  const spec = [
    card("match share", pct(share),
         share === null || share === undefined ? "" : (share >= target ? "good" : "bad")),
    card("F1 top-1", f1(pos.f1_at_1)),
    card("F1 top-5", f1(pos.f1_at_5)),
    card("within " + sla + " ms", pct(lat.within_sla_share),
         lat.within_sla_share === null || lat.within_sla_share === undefined ? ""
         : (lat.within_sla_share >= 0.9 ? "good" : "bad")),
    card("near-duplicate errors", numOr(pos.near_duplicate_confusion), "bad"),
    card("false match @1", numOr(neg.false_match_at_1), "bad"),
  ];
  const rest = [
    card("R@1", pct(pos.recall_at_1)),
    card("R@5", pct(pos.recall_at_5)),
    card("R@10", pct(pos.recall_at_10)),
    card("MRR", fix(pos.mrr)),
    card("score gap, correct", fix(margin.correct_median)),
    card("score gap, wrong", fix(margin.wrong_median)),
    card("positive photos", numOr(pos.n)),
    card("negative photos", numOr(neg.n)),
    card("median ms", numOr(lat.median)),
    card("errors", (pos.errors || 0) + (neg.errors || 0)),
  ];
  /* A run with no ground truth. Every share above is empty, and the note says
     why, so that a reader does not take a dash for a failure. */
  const unlB = met.unlabelled;
  const unlNote = !unlB ? "" :
    '<div class="sm warn">A run of a plain directory. The photos hold no ground ' +
    'truth, so every share is empty. ' + unlB.n + ' photo(s), ' + unlB.answered +
    ' with a candidate, ' + unlB.no_answer + ' with none, ' + unlB.errors +
    ' error(s). Median top score: ' + fix(unlB.top_score_median) +
    '. Median gap to the second candidate: ' + fix(unlB.score_margin_median) +
    '.</div>';
  const sub = met.subset;
  const subNote = !sub ? "" :
    '<div class="sm warn">A repeat run. It holds the ' + sub.n + ' photo(s) of <b>' +
    esc(sub.based_on) + '</b> that failed at depth ' + sub.rerun_depth + ', out of ' +
    sub.photos_in_earlier_run + '. The shares below cover those photos only; they are ' +
    'NOT the shares of the whole set. Correct at rank 1 now: <b>' + sub.recovered_at_1 +
    '</b>. Inside the depth now: <b>' + sub.recovered_at_depth + '</b>. Still failing: <b>' +
    sub.still_failing + '</b>.</div>';
  /* When the vectors that answered this run were built. Two runs of one
     backend id are otherwise indistinguishable although a rebuild moved every
     vector between them. An unknown age states its reason, so that "not
     reported" and "not known" never look the same. */
  const emb = head.embeddings;
  let embNote;
  if (!emb) {
    embNote = '<div class="sm note">Embeddings: not recorded. This run was made ' +
      'before the run file carried the age of the index.</div>';
  } else if (emb.built_at) {
    const when = String(emb.built_at).replace("T", " ").slice(0, 16);
    const bits = [];
    if (emb.pipeline) bits.push("pipeline " + esc(emb.pipeline));
    if (emb.index_file) bits.push("index " + esc(emb.index_file));
    if (emb.source === "mtime") bits.push("from the file mtime, not the build record");
    embNote = '<div class="sm note">Embeddings last built <b>' + esc(when) + '</b>' +
      (bits.length ? " (" + bits.join(", ") + ")" : "") + '.</div>';
  } else {
    embNote = '<div class="sm note">Embeddings age not reported: ' +
      esc(emb.reason || "no reason given") + '.</div>';
  }
  $("#met").innerHTML = embNote + unlNote + subNote +
    '<div class="cards">' + spec.join("") + '</div>' +
    '<div class="sm note">The task asks for a match share of 90 to 100 percent, an ' +
    'answer inside ' + sla + ' ms, and a noticeable gap between the first and the ' +
    'second candidate. A near-duplicate error answers a wine of the same variant ' +
    'group as the true one.</div>' +
    '<div class="cards">' + rest.join("") + '</div>';
  const k = met.top_k || 1;
  $("#hists").innerHTML =
    histogram("How far from R@1 (positive photos)", pos.rank_histogram,
      "The rank of the true slug in the answer. `absent` means that the true slug never came back.") +
    histogram("Where the slug of a negative photo landed", neg.slug_rank_histogram,
      "A negative photo shows a different wine. Only rank 1 is a proven error; " +
      "deeper ranks are a diagnostic. Scored to top-" + k + ".");
  $("#det-h").textContent = "Metrics of " + (head.id || "");
  $("#detail").hidden = false;
}

/* ---- one photo and its candidates ----

   A negative photo states one wine that the photo does NOT show. When a byte-equal
   photo stands in the same run as `positive` for another wine, that wine is the
   true wine of the photo. The true wine gets a dashed green frame and the wrong
   wine keeps the red frame. The true wine SHOULD stand above the wrong wine. */
function candCard(c, truth, forbidden, twins) {
  const isTruth = truth.includes(c.slug);
  const isBad = forbidden && c.slug === forbidden;
  const isTwin = !isBad && twins.includes(c.slug);
  const score = c.score === null || c.score === undefined ? "" : c.score.toFixed(3);
  return `<div class="cand ${isTruth ? "truth" : ""} ${isBad ? "forbidden" : ""} ${
      isTwin ? "twin" : ""}">
    ${picHtml(`<img loading="lazy" src="/img/bottle?slug=${encodeURIComponent(c.slug)}"
         alt="" data-full="/img/bottle?slug=${encodeURIComponent(c.slug)}"
         onerror="this.replaceWith(Object.assign(document.createElement('div'),
                  {className:'nobottle',textContent:'no bottle photo'}))">`,
       isPatched(c.slug))}
    <div class="r"><span>#${c.rank}</span><span>${score}</span></div>
    <div class="sl">${esc(c.slug)}</div></div>`;
}

function twinGhost(slug, apart) {
  return `<div class="cand twin missing ${apart ? "apart" : ""}">
    ${picHtml(`<img loading="lazy" src="/img/bottle?slug=${encodeURIComponent(slug)}" alt=""
         data-full="/img/bottle?slug=${encodeURIComponent(slug)}"
         onerror="this.replaceWith(Object.assign(document.createElement('div'),
                  {className:'nobottle',textContent:'no bottle photo'}))">`,
       isPatched(slug))}
    <div class="r"><span>true wine</span><span>&mdash;</span></div>
    <div class="sl">${esc(slug)}</div></div>`;
}

function rowHtml(r) {
  /* A run of `--photos-dir` holds photos with no ground truth. Their path is the
     path against that directory, not `<slug>/<file>`, and only `/img/runphoto`
     serves them, because `/img/photo` never leaves `my/`. */
  const unl = r.label === "unlabelled";
  const cut = r.image_path.lastIndexOf("/");
  const slug = unl ? "" : r.image_path.slice(0, cut);
  const file = cut < 0 ? r.image_path : r.image_path.slice(cut + 1);
  const src = unl
    ? `/img/runphoto?id=${encodeURIComponent(CUR)}&file=${encodeURIComponent(r.image_path)}`
    : `/img/photo?slug=${encodeURIComponent(slug)}&file=${encodeURIComponent(file)}`;
  const truth = r.truth || [];
  const forbidden = r.label === "negative" ? r.slug : null;
  const twin = r.twin || {};
  const twins = r.label === "negative" ? (twin.slugs || []) : [];
  const found = (r.candidates || []).some(c => truth.includes(c.slug));
  let strip = "";
  if (truth.length && !found) {          // the expected wine, which never came back
    strip += `<div class="cand truth missing">
      ${picHtml(`<img loading="lazy" src="/img/bottle?slug=${encodeURIComponent(truth[0])}" alt=""
           data-full="/img/bottle?slug=${encodeURIComponent(truth[0])}"
           onerror="this.replaceWith(Object.assign(document.createElement('div'),
                    {className:'nobottle',textContent:'no bottle photo'}))">`,
         isPatched(truth[0]))}
      <div class="r"><span>expected</span><span>\\u2014</span></div>
      <div class="sl">${esc(truth[0])}</div></div>`;
  }
  strip += (r.candidates || []).map(c => candCard(c, truth, forbidden, twins)).join("");
  // the true wine of a negative photo, which never came back. It stands after the
  // answer, apart from it, because it holds no rank in the answer.
  const gone = twins.filter(s => !(r.candidates || []).some(c => c.slug === s));
  strip += gone.map((s, i) => twinGhost(s, i === 0)).join("");
  if (!strip) strip = `<span class="empty">${esc(r.error || "no candidate came back")}</span>`;

  const tag = LABEL_TAG[r.label] || "";
  const rank = unl ? "no ground truth"
             : (r.rank_of_truth ? `rank ${r.rank_of_truth}` : "not in the list");
  /* No answer of an unlabelled photo is wrong, because no answer is known. */
  const bad = !unl && ((r.label === "negative" && r.outcome === "false_match_at_1") ||
                       (r.label !== "negative" && r.rank_of_truth !== 1));
  return `<tr>
    <td class="qcell">
      <img class="qphoto" loading="lazy" src="${src}" alt="" data-full="${src}"
           onload="const b = this.closest('td').querySelector('.qres');
                   if (b) b.textContent = ' \u00b7 ' + this.naturalWidth + ' \u00d7 '
                                          + this.naturalHeight;">
      <div class="sm"><span class="tag ${tag}">${esc(r.label)}</span>
        <span class="tag ${bad ? "bad" : "ok"}">${esc(r.outcome || "")}</span>${
        twin.verdict === "below"
          ? ` <span class="tag bad">negative_above_positive</span>` : ""}${
        twin.conflict ? ` <span class="tag bad">twin_conflict</span>` : ""}</div>
      ${unl ? "" : `<div class="sm">${esc(slug)}</div>`}
      <div class="sm">${esc(unl ? r.image_path : file)} &middot; ${esc(rank)} &middot; ${numOr(r.latency_ms)} ms<span
        class="qres"></span></div>
      ${twins.length ? `<div class="sm">true wine: ${esc(twins.join(", "))} &middot; ${
        twin.rank ? "rank " + twin.rank : "not in the list"}${
        twin.forbidden_rank ? " &middot; this slug: rank " + twin.forbidden_rank : ""
        }</div>` : ""}
      ${r.previous ? `<div class="sm was">before: ${
        r.previous.rank_of_truth ? "rank " + r.previous.rank_of_truth : "not in the list"
        } &middot; ${esc(r.previous.outcome || "")}</div>` : ""}
      ${r.error ? `<div class="sm" style="color:var(--exc)">${esc(r.error)}</div>` : ""}
    </td>
    <td><div class="strip">${strip}</div></td></tr>`;
}

/* ---- loading ---- */
async function loadRun(id, append) {
  CUR = id;
  if (!append) { OFFSET = 0; $("#res-body").innerHTML = ""; }
  const url = `/api/run?id=${encodeURIComponent(id)}&filter=${$("#filter").value}` +
              `&sort=${$("#sort").value}` +
              `&q=${encodeURIComponent($("#q").value.trim())}&offset=${OFFSET}&limit=100`;
  const data = await (await fetch(url)).json();
  if (data.error) { alert(data.error); return; }
  TOTAL = data.total;
  if (!append) renderMetrics(data.metrics || {}, data.head || {});
  $("#res-body").insertAdjacentHTML("beforeend", (data.rows || []).map(rowHtml).join(""));
  OFFSET += (data.rows || []).length;
  $("#count").textContent = `${OFFSET} of ${TOTAL} photo(s) shown`;
  $("#more").hidden = OFFSET >= TOTAL;
  renderRuns();
  location.hash = encodeURIComponent(id);
}

$("#runs-body").addEventListener("click", ev => {
  const tr = ev.target.closest("tr[data-id]");
  if (tr) loadRun(tr.dataset.id, false);
});
$("#more").addEventListener("click", () => loadRun(CUR, true));
$("#filter").addEventListener("change", () => CUR && loadRun(CUR, false));
$("#sort").addEventListener("change", () => CUR && loadRun(CUR, false));
document.querySelector("#runs thead").addEventListener("click", ev => {
  const th = ev.target.closest("th[data-k]");
  if (!th) return;
  const key = th.dataset.k;
  // the same column turns the order around; another column starts at its own end
  const down = (key === "id" || key === "started" || key === "backend") ? -1 : 1;
  RSORT = { key, dir: RSORT.key === key ? -RSORT.dir : down };
  renderRuns();
});
let t = null;
$("#q").addEventListener("input", () => {
  clearTimeout(t);
  t = setTimeout(() => CUR && loadRun(CUR, false), 250);
});
/* ---- the large view ---- */
/* `LBI` holds the row that the open image came from and the place of the image
   in that row. The arrow keys move from it: left and right inside the row, up
   and down to the same place in another row. A photo that stands outside a row
   opens with no `LBI`, so the arrow keys do nothing for it. */
let LBI = null;
/* The images of one row, in the order that the row shows them: the matched photo
   first, then the strip. A bottle photo that failed to load is no image any
   more, because `onerror` puts a text card in its place. Such a card is not a
   step of the move. */
const lbImgs = tr => Array.from(tr.querySelectorAll("img[data-full]"));

function openLb(tr, i) {
  const imgs = lbImgs(tr);
  if (!imgs.length) return;
  i = Math.max(0, Math.min(i, imgs.length - 1));
  LBI = { row: tr, i };
  $("#lb img").src = imgs[i].dataset.full;
  $("#lb").classList.add("on");
}

/* Move inside the row. The first image and the last image hold: the move does
   not turn around at an end. */
function stepLb(step) {
  if (LBI) openLb(LBI.row, LBI.i + step);
}

/* Move to the previous row or to the next row and keep the place. A place after
   the end of the new row holds at its last image. A row with no image is
   stepped over. The table scrolls to the row, so the place of the eye is held
   when the view closes. */
function stepLbRow(step) {
  if (!LBI) return;
  let tr = LBI.row;
  do { tr = step > 0 ? tr.nextElementSibling : tr.previousElementSibling; }
  while (tr && !lbImgs(tr).length);
  if (!tr) return;
  openLb(tr, LBI.i);
  tr.scrollIntoView({ block: "center" });
}

function closeLb() { $("#lb").classList.remove("on"); LBI = null; }

document.addEventListener("click", ev => {
  const img = ev.target.closest("img[data-full]");
  if (img) {
    const tr = img.closest("#res-body tr");
    if (tr) { openLb(tr, lbImgs(tr).indexOf(img)); return; }
    LBI = null;
    $("#lb img").src = img.dataset.full;
    $("#lb").classList.add("on");
    return;
  }
  if (ev.target.closest("#lb")) closeLb();
});
document.addEventListener("keydown", ev => {
  if (ev.key === "Escape") { closeLb(); return; }
  if (!LBI || !$("#lb").classList.contains("on")) return;
  if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
  const step = { ArrowRight: 1, ArrowLeft: -1 }[ev.key];
  if (step !== undefined) { ev.preventDefault(); stepLb(step); return; }
  const rstep = { ArrowDown: 1, ArrowUp: -1 }[ev.key];
  if (rstep !== undefined) { ev.preventDefault(); stepLbRow(rstep); }
});

(async function init() {
  try {
    PATCHED = new Set((await (await fetch("/api/patched")).json()).slugs || []);
  } catch (e) { /* the mark is a hint; its absence MUST NOT stop the page */ }
  RUNS = (await (await fetch("/api/runs")).json()).runs || [];
  renderRuns();
  const want = decodeURIComponent((location.hash || "").slice(1));
  const first = RUNS.find(r => r.id === want) ||
                RUNS.find(r => r.has_metrics && !r.dry_run);
  if (first) loadRun(first.id, false);
})();
</script>
</body>
</html>
"""


# The page of the catalogue clusters. It reads `GET /api/clusters`, which answers the
# file of `scripts/10_clusters.py`, and it writes nothing. A cluster is a group of
# catalogue cards that the matcher confuses, or can confuse. Read
# `docs/plans/04_catalog-clusters.md`.
PAGE_CLUSTERS = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Catalogue clusters</title>
<style>
""" + THEME_CSS + PATCH_CSS + r"""
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--text);
  font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
header {
  position: sticky; top: 0; z-index: 10;
  background: var(--panel); border-bottom: 1px solid var(--line);
  padding: 10px 16px; box-shadow: var(--shadow);
}
h1 { font-size: 15px; margin: 0 0 8px; font-weight: 650; }
h1 .sub { color: var(--muted); font-weight: 400; }
.head-top { display: flex; align-items: baseline; gap: 14px; flex-wrap: wrap; }
.head-top h1 { margin-right: auto; }
.nav { display: flex; gap: 6px; flex: none; }
.nav a {
  color: var(--muted); text-decoration: none; font-size: 13px; font-weight: 600;
  padding: 3px 10px; border: 1px solid var(--line); border-radius: 6px;
  background: var(--panel-2);
}
.nav a:hover { color: var(--text); border-color: var(--accent); }
.nav a.on { color: var(--text); border-color: var(--accent); background: var(--panel); }
a { color: var(--accent); }
main { padding: 12px 16px 64px; }
.bar { display: flex; flex-wrap: wrap; gap: 8px 14px; align-items: center; }
.bar label { color: var(--muted); font-size: 12px; display: flex; gap: 5px; align-items: center; }
select, input[type=search] {
  background: var(--panel-2); color: var(--text); border: 1px solid var(--line);
  border-radius: 6px; padding: 4px 7px; font: inherit; font-size: 13px;
}
input[type=search] { min-width: 210px; max-width: 100%; }
.muted { color: var(--muted); }
.empty { color: var(--muted); font-style: italic; padding: 24px 0; }
code {
  font: 12px ui-monospace, SFMono-Regular, Menlo, monospace; background: var(--panel-2);
  padding: 1px 4px; border-radius: 4px; word-break: break-all;
}
#about {
  background: var(--panel); border: 1px solid var(--line); border-radius: 8px;
  padding: 8px 12px; margin-bottom: 12px; font-size: 13px;
}
#about summary { cursor: pointer; font-weight: 600; }
#about p { margin: 8px 0; }
#about table { border-collapse: collapse; margin: 6px 0; }
#about th, #about td { padding: 2px 12px 2px 0; text-align: left; vertical-align: top;
                       font-size: 12px; }
#about th { color: var(--muted); font-weight: 600; }

/* one cluster */
.cl {
  background: var(--panel); border: 1px solid var(--line); border-radius: 10px;
  padding: 10px 12px; margin-bottom: 12px; scroll-margin-top: 110px;
}
.cl.hit { outline: 2px solid var(--accent); outline-offset: 2px; }
.cl-head { display: flex; flex-wrap: wrap; gap: 6px 10px; align-items: baseline;
           margin-bottom: 8px; }
.cid { font-weight: 700; font-variant-numeric: tabular-nums; color: var(--text);
       text-decoration: none; }
.cid:hover { color: var(--accent); }
.tag { padding: 1px 7px; border-radius: 999px; font-size: 11px; font-weight: 600; }
.tag.same-wine { color: var(--var); background: var(--var-bg); }
.tag.look-alike { color: var(--neg); background: var(--neg-bg); }
.tag.mixed { color: var(--accent); background: var(--grp-a); }
.chip { font-size: 11px; color: var(--muted); border: 1px solid var(--line);
        border-radius: 999px; padding: 0 6px; white-space: nowrap; }
.members { display: flex; flex-wrap: wrap; gap: 10px; }
.mem {
  width: 176px; background: var(--panel-2); border: 1px solid var(--line);
  border-radius: 8px; padding: 6px; position: relative;
}
.mem.hit { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent); }
.mem .no {
  position: absolute; top: 9px; left: 9px; z-index: 2; font-size: 11px; font-weight: 700;
  background: var(--panel); color: var(--text); border: 1px solid var(--line);
  border-radius: 4px; padding: 0 4px;
}
.mem img, .mem .nobottle {
  width: 162px; height: 200px; object-fit: contain; display: block;
  background: var(--panel); border: 1px solid var(--line); border-radius: 4px;
}
.mem .nobottle { display: flex; align-items: center; justify-content: center;
                 color: var(--muted); font-size: 11px; text-align: center; }
.mem .nm { font-weight: 600; font-size: 13px; margin-top: 4px; line-height: 1.25; }
.mem .pr, .mem .gr, .mem .ph { font-size: 11px; color: var(--muted); line-height: 1.3; }
.mem .sl { font-size: 10px; word-break: break-all; line-height: 1.25; margin-top: 2px; }
.mem .lk { font-size: 11px; margin-top: 3px; display: flex; gap: 8px; flex-wrap: wrap; }
.ph .p { color: var(--pos); }
.ph .n { color: var(--neg); }
.ph .x { color: var(--exc); }
.links-wrap { overflow-x: auto; margin-top: 10px; }
table.links { border-collapse: collapse; font-size: 12px; }
table.links th {
  text-align: left; color: var(--muted); font-weight: 600; padding: 3px 8px;
  border-bottom: 1px solid var(--line); white-space: nowrap;
}
table.links td { padding: 4px 8px; border-bottom: 1px solid var(--line);
                 vertical-align: middle; white-space: nowrap; }
table.links tr:last-child td { border-bottom: 0; }
.num { text-align: right; font-variant-numeric: tabular-nums; }
.pass { color: var(--text); font-weight: 650; }
.fail { color: var(--muted); }
.by { display: flex; gap: 4px; }
.by .chip { color: var(--text); border-color: var(--accent); }
.thumbs { display: flex; gap: 4px; }
.thumbs img {
  width: 38px; height: 38px; object-fit: cover; display: block;
  border: 1px solid var(--line); border-radius: 4px; background: var(--panel-2);
}
.mem img, .thumbs img { cursor: zoom-in; }
/* the image that the large view shows now, or showed last */
img.lb-cur { outline: 2px solid var(--accent); outline-offset: 1px; }

/* The large view. It is dark in both themes, as the large view of the review page
   is, because a photo reads best on a dark ground. */
#lb {
  position: fixed; inset: 0; z-index: 50; display: none;
  align-items: center; justify-content: center; gap: 10px;
  padding: 58px 12px 40px; background: rgba(0,0,0,.88);
}
#lb.on { display: flex; }
.lb-fig {
  margin: 0; flex: 0 1 auto; min-width: 0; max-width: calc(100vw - 140px);
  display: flex; flex-direction: column; align-items: center; gap: 8px;
}
.lb-fig img {
  display: block; max-width: 100%; max-height: calc(100vh - 170px);
  object-fit: contain; border-radius: 6px;
}
/* The previous image is hidden while the next one loads, so the caption never stands
   under the wrong picture. */
.lb-fig img.loading { visibility: hidden; }
.lb-fig figcaption {
  color: #e9e9ee; font-size: 12px; line-height: 1.45; text-align: center;
  max-width: 760px; overflow-wrap: anywhere;
}
.lb-fig figcaption b { color: #fff; }
.lb-fig figcaption a { color: #c9a8dc; }
.lb-fig figcaption .where { color: #9a9aa6; }
.lb-btn {
  font: 600 18px/1 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  color: #e9e9ee; background: rgba(255,255,255,.08);
  border: 1px solid rgba(255,255,255,.2); border-radius: 8px; cursor: pointer;
}
.lb-btn:hover:not(:disabled) { background: rgba(255,255,255,.2); }
.lb-btn:disabled { opacity: .3; cursor: default; }
.lb-step { flex: none; width: 44px; height: 64px; font-size: 28px; }
.lb-rows { position: absolute; top: 12px; left: 12px; display: flex; gap: 6px; }
.lb-rows .lb-btn, #lb-close { width: 38px; height: 34px; }
#lb-close { position: absolute; top: 12px; right: 12px; font-size: 22px; }
#lb .hint {
  position: absolute; left: 0; right: 0; bottom: 12px; text-align: center;
  color: #9a9aa6; font-size: 11px;
}
#lb .hint b { color: #e9e9ee; }

@media (max-width: 600px) {
  .mem { width: calc(50% - 5px); }
  .mem img, .mem .nobottle { width: 100%; height: 160px; }
  input[type=search] { min-width: 0; width: 100%; }
  .lb-step { width: 32px; height: 52px; font-size: 22px; }
  .lb-fig { max-width: calc(100vw - 100px); }
}
</style>
</head>
<body>
<header>
  <div class="head-top">
    <h1>Catalogue clusters <span class="sub" id="head-sub"></span></h1>
    <nav class="nav"><a href="/">Review</a><a href="/runs">Runs</a><a class="on"
      href="/clusters">Clusters</a></nav>
  </div>
  <div class="bar">
    <label>Kind
      <select id="kind">
        <option value="">every kind</option>
        <option value="same-wine">same wine</option>
        <option value="mixed">mixed</option>
        <option value="look-alike">look-alike</option>
      </select>
    </label>
    <label>Signal
      <select id="signal">
        <option value="">any signal</option>
        <option value="name">name</option>
        <option value="photo">photo</option>
        <option value="label">label</option>
        <option value="confusion">confusion</option>
      </select>
    </label>
    <label>Size
      <select id="size">
        <option value="2">2 cards or more</option>
        <option value="3">3 cards or more</option>
        <option value="5">5 cards or more</option>
      </select>
    </label>
    <label>Sort
      <select id="sort">
        <option value="confusions">most confused photos first</option>
        <option value="size">largest first</option>
        <option value="photo">closest photos first</option>
        <option value="producer">producer A-Z</option>
      </select>
    </label>
    <label>Image
      <select id="img">
        <option value="package">package</option>
        <option value="label">label</option>
      </select>
    </label>
    <label>Find <input id="q" type="search" placeholder="slug, name, or producer"></label>
    <span class="muted" id="count"></span>
  </div>
</header>
<main>
  <details id="about"><summary>What this page shows</summary>
    <div id="about-body"></div></details>
  <div id="list"><p class="empty">Loading the clusters…</p></div>
</main>
<div id="lb" role="dialog" aria-modal="true" aria-label="large view">
  <div class="lb-rows">
    <button id="lb-up" class="lb-btn" data-rstep="-1" title="previous cluster (Up)">&uarr;</button>
    <button id="lb-down" class="lb-btn" data-rstep="1" title="next cluster (Down)">&darr;</button>
  </div>
  <button id="lb-close" class="lb-btn" title="close (Esc)">&times;</button>
  <button id="lb-prev" class="lb-btn lb-step" data-step="-1" title="previous image (Left)">&lsaquo;</button>
  <figure class="lb-fig"><img id="lb-img" alt=""><figcaption id="lb-cap"></figcaption></figure>
  <button id="lb-next" class="lb-btn lb-step" data-step="1" title="next image (Right)">&rsaquo;</button>
  <div class="hint"><b>&larr; &rarr;</b> image in the cluster &middot;
    <b>&uarr; &darr;</b> previous or next cluster &middot; <b>Esc</b> close</div>
</div>
<script>
""" + PATCH_JS + r"""
const $ = s => document.querySelector(s);
const esc = s => (s == null ? "" : String(s)).replace(/[&<>"']/g,
  c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const num = v => v === null || v === undefined ? "—" : Number(v).toFixed(3);
const SIGNALS = ["name", "photo", "label", "confusion"];
const KIND_TEXT = { "same-wine": "same wine", "look-alike": "look-alike", "mixed": "mixed" };
let DATA = null, CARDS = {};

function signalCounts(c) {
  const out = {};
  for (const l of c.links) for (const s of l.by) out[s] = (out[s] || 0) + 1;
  return out;
}

function bestPhoto(c) {
  return Math.max(-1, ...c.links.map(l => l.photo === null ? -1 : l.photo));
}

function matches(c, q) {
  if (!q) return true;
  return c.slugs.some(s => {
    const k = CARDS[s] || {};
    return `${s} ${k.name || ""} ${k.producer || ""}`.toLowerCase().includes(q);
  });
}

/* The clusters that the controls select, in the selected order. */
function view() {
  const kind = $("#kind").value, sig = $("#signal").value, size = +$("#size").value;
  const q = $("#q").value.trim().toLowerCase();
  const list = DATA.clusters.filter(c => (!kind || c.kind === kind)
    && (!sig || c.signals.includes(sig)) && c.size >= size && matches(c, q));
  const order = {
    confusions: (a, b) => b.confusions - a.confusions || b.size - a.size,
    size: (a, b) => b.size - a.size || b.confusions - a.confusions,
    photo: (a, b) => bestPhoto(b) - bestPhoto(a),
    producer: (a, b) => (a.producers[0] || "").localeCompare(b.producers[0] || "", "ru"),
  }[$("#sort").value];
  return list.sort((a, b) => order(a, b) || a.id.localeCompare(b.id));
}

function photoCounts(k) {
  if (!k.in_review) return "no test photo";
  const p = k.photos || {};
  const parts = [
    p.positive ? `<span class="p">${p.positive} positive</span>` : "",
    p.negative ? `<span class="n">${p.negative} negative</span>` : "",
    p.variant ? `${p.variant} variant` : "",
    p.unlabelled ? `${p.unlabelled} unlabelled` : "",
  ].filter(Boolean);
  return parts.length ? parts.join(" · ") : "no labelled photo";
}

function memberHtml(slug, no, img) {
  const k = CARDS[slug] || {};
  const onLabel = img === "label";
  const src = `/img/bottle?slug=${encodeURIComponent(slug)}&kind=${img}`;
  const tag = `<img loading="lazy" src="${src}" alt="${esc(k.name || slug)}"${
    onLabel && k.has_label ? ' class="onwhite"' : ""} data-full="${src}"
    data-card="${esc(slug)}" data-no="${no}">`;
  // A plain click opens the large view. The link stays, so a click with a
  // modifier key still opens the picture in a new tab.
  const pic = k.in_catalog === false
    ? `<div class="nobottle">not in the catalogue</div>`
    : `<a href="${src}" target="_blank" rel="noopener" title="open the large view">${
        picHtml(tag, k.patched, onLabel && !k.has_label)}</a>`;
  return `<div class="mem" data-slug="${esc(slug)}">
    <span class="no">#${no}</span>${pic}
    <div class="nm">${esc(k.name || slug)}</div>
    <div class="pr">${esc(k.producer || "")}${k.category ? " · " + esc(k.category) : ""}</div>
    ${k.grapes ? `<div class="gr">${esc(k.grapes)}</div>` : ""}
    <div class="sl">${esc(slug)}</div>
    <div class="ph">${photoCounts(k)}${k.excluded ? ' · <span class="x">excluded</span>' : ""}</div>
    <div class="lk"><a href="/#${encodeURIComponent(slug)}">review</a>${k.page_url
      ? `<a href="${esc(k.page_url)}" target="_blank" rel="noopener">vino-svoe.ru</a>` : ""}</div>
  </div>`;
}

function linkRow(l, no) {
  const passed = s => l.by.includes(s) ? "pass" : "fail";
  const name = l.name === "same" ? `<td class="pass">same</td>`
    : l.name === "grapes-differ"
      ? `<td class="fail" title="one name key, and grapes that disagree">grapes differ</td>`
      : `<td class="fail">—</td>`;
  const thumbs = (l.photos || []).map(p => {
    const src = `/img/photo?slug=${encodeURIComponent(p.slug)}&file=${encodeURIComponent(p.file)}`;
    return `<a href="/#${encodeURIComponent(p.slug)}/${encodeURIComponent(p.file)}"
      title="${esc(`a positive photo of #${no[p.slug]} that the run ${p.run} answered as #${
      no[p.answered]}`)}"><img loading="lazy" alt="" src="${src}" data-full="${src}"
      data-of="${esc(p.slug)}" data-file="${esc(p.file)}" data-answered="${esc(p.answered)}"
      data-run="${esc(p.run)}" onerror="this.parentNode.remove()"></a>`;
  }).join("");
  return `<tr>
    <td title="${esc(l.a)}">#${no[l.a]}</td><td title="${esc(l.b)}">#${no[l.b]}</td>
    <td><div class="by">${l.by.map(s => `<span class="chip">${s}</span>`).join("")}</div></td>
    ${name}
    <td class="num ${passed("photo")}">${num(l.photo)}</td>
    <td class="num ${passed("label")}">${num(l.label)}</td>
    <td class="num ${passed("confusion")}">${l.a_as_b}</td>
    <td class="num ${passed("confusion")}">${l.b_as_a}</td>
    <td><div class="thumbs">${thumbs}</div></td>
  </tr>`;
}

function clusterHtml(c, img) {
  const no = {};
  c.slugs.forEach((s, i) => { no[s] = i + 1; });
  const counts = signalCounts(c);
  const chips = SIGNALS.filter(s => counts[s])
    .map(s => `<span class="chip" title="links that passed this signal">${s} ${counts[s]}</span>`)
    .join("");
  return `<section class="cl" id="cl-${esc(c.id)}" data-id="${esc(c.id)}">
    <div class="cl-head">
      <a class="cid" href="#${encodeURIComponent(c.slugs[0])}"
         title="the address of this cluster">${esc(c.id)}</a>
      <span class="tag ${esc(c.kind)}">${esc(KIND_TEXT[c.kind] || c.kind)}</span>
      <span class="muted">${c.size} cards · ${esc(c.producers.join(", "))}</span>
      ${chips}
      ${c.confusions ? `<span class="muted">${c.confusions} confused photo(s)</span>` : ""}
    </div>
    <div class="members">${c.slugs.map(s => memberHtml(s, no[s], img)).join("")}</div>
    <div class="links-wrap"><table class="links"><thead><tr>
      <th>card</th><th>card</th><th>passed</th><th>name</th>
      <th class="num">photo</th><th class="num">label</th>
      <th class="num" title="positive photos of the first card that a run answered as the second card">1st as 2nd</th>
      <th class="num" title="positive photos of the second card that a run answered as the first card">2nd as 1st</th>
      <th>confused photos</th>
    </tr></thead><tbody>${c.links.map(l => linkRow(l, no)).join("")}</tbody></table></div>
  </section>`;
}

function render() {
  closeLb();                  // the open image belongs to the blocks drawn before
  const list = view(), img = $("#img").value;
  const cards = list.reduce((n, c) => n + c.size, 0);
  $("#count").textContent =
    `${list.length} of ${DATA.clusters.length} clusters · ${cards} cards`;
  $("#list").innerHTML = list.length
    ? list.map(c => clusterHtml(c, img)).join("")
    : `<p class="empty">No cluster matches the controls.</p>`;
}

function aboutHtml() {
  const s = DATA.settings || {}, i = DATA.inputs || {}, n = DATA.counts || {};
  const links = n.links || {};
  const index = x => x
    ? `<code>${esc(x.file.split("/").pop())}</code>, ${x.cards} cards, built ${esc(x.built_at || "?")}`
    : "not used";
  const runs = (i.runs || []).map(r => `<tr><th><code>${esc(r.id)}</code></th><td>${
    r.used} of ${r.wrong_at_1} wrong answers used, ${r.stale} stale</td></tr>`).join("");
  return `<p>A cluster is a group of catalogue cards that the matcher confuses, or can
    confuse. A link joins two cards and records every signal that passed. A cluster is a
    connected group of links, and a card is in at most one cluster.</p>
  <table>
    <tr><th>name</th><td>the same producer, name and category after normalisation,
      and grapes that agree. ${links.name || 0} links.</td></tr>
    <tr><th>photo</th><td>the SigLIP 2 cosine of the two catalogue photos is at least
      ${esc(s.photo_threshold)}. ${links.photo || 0} links. ${index(i.photo_index)}.</td></tr>
    <tr><th>label</th><td>the SigLIP 2 cosine of the two label crops is at least
      ${esc(s.label_threshold)}. ${links.label || 0} links. ${index(i.label_index)}.</td></tr>
    <tr><th>confusion</th><td>at least ${esc(s.min_confusions)} positive photos, over both
      directions, that a run answered as the other card. ${links.confusion || 0} links.</td></tr>
  </table>
  <table>${runs}</table>
  <p><span class="tag same-wine">same wine</span> the name links alone join every card.
    <span class="tag mixed">mixed</span> name links and other links.
    <span class="tag look-alike">look-alike</span> no name link. A number in a link row
    is bold when that signal passed.</p>
  <p>The file <code>${esc(DATA.file)}</code> was built ${esc(DATA.built_at)}. Build it
    again with <code>python3 scripts/10_clusters.py</code>. This page reads the file at
    each load.</p>`;
}

/* `#<slug>` opens the cluster of that card. The controls are cleared when they hide
   that cluster, so a pasted address always opens. */
function openFromHash() {
  const slug = decodeURIComponent((location.hash || "").slice(1));
  if (!slug || !DATA) return;
  const c = DATA.clusters.find(x => x.slugs.includes(slug));
  if (!c) {
    $("#count").textContent = `${slug} is in no cluster`;
    return;
  }
  if (!view().includes(c)) {
    $("#kind").value = $("#signal").value = $("#q").value = "";
    $("#size").value = "2";
    render();
  }
  document.querySelectorAll(".hit").forEach(e => e.classList.remove("hit"));
  const el = document.getElementById("cl-" + c.id);
  el.classList.add("hit");
  const mem = [...el.querySelectorAll(".mem")].find(m => m.dataset.slug === slug);
  if (mem) mem.classList.add("hit");
  el.scrollIntoView({ block: "start" });
}

/* ---- the large view ---- */
/* `LB` holds the cluster that the open image comes from and the place of the image in
   that cluster. Left and right move inside the cluster: the cards first, then the
   confused photos, in the order of the page. Up and down move to the same place in the
   previous or the next cluster of the view. A place after the end of that cluster holds
   at its last image. The first and the last image hold: a move does not turn around. */
let LB = null;
const lbImgs = cl => Array.from(cl.querySelectorAll("img[data-full]"));

/* The next cluster of the view in the direction of `step` that holds an image. */
function lbNeighbour(cl, step) {
  let x = cl;
  do { x = step > 0 ? x.nextElementSibling : x.previousElementSibling; }
  while (x && !(x.classList.contains("cl") && lbImgs(x).length));
  return x;
}

function lbCaption(img, cl, i, n) {
  const d = img.dataset, shown = [...document.querySelectorAll("#list .cl")];
  const where = `<span class="where">image ${i + 1} of ${n} · ${esc(cl.dataset.id)}
    · cluster ${shown.indexOf(cl) + 1} of ${shown.length}</span>`;
  const no = slug => {
    const m = [...cl.querySelectorAll(".mem")].find(e => e.dataset.slug === slug);
    return m ? m.querySelector(".no").textContent : "";
  };
  if (d.card) {
    const k = CARDS[d.card] || {};
    return `<b>#${esc(d.no)} ${esc(k.name || d.card)}</b> · ${esc(k.producer || "")}${
      k.category ? " · " + esc(k.category) : ""}<br>${esc(d.card)} ·
      <a href="/#${encodeURIComponent(d.card)}" target="_blank" rel="noopener">review</a>
      <br>${where}`;
  }
  const of = CARDS[d.of] || {}, answered = CARDS[d.answered] || {};
  return `A positive photo of <b>${no(d.of)} ${esc(of.name || d.of)}</b> that a run answered
    as <b>${no(d.answered)} ${esc(answered.name || d.answered)}</b><br>${esc(d.of)}/${
    esc(d.file)} · ${esc(d.run)} · <a href="/#${encodeURIComponent(d.of)}/${
    encodeURIComponent(d.file)}" target="_blank" rel="noopener">review</a><br>${where}`;
}

function openLb(cl, i) {
  const imgs = lbImgs(cl);
  if (!imgs.length) return;
  i = Math.max(0, Math.min(i, imgs.length - 1));
  LB = { cl, i };
  const img = imgs[i], big = $("#lb-img");
  if (big.getAttribute("src") !== img.dataset.full) {
    big.classList.add("loading");
    big.src = img.dataset.full;
  }
  // A catalogue picture is a render or a label crop with a mask. It stands on white.
  big.classList.toggle("onwhite", !!img.dataset.card);
  $("#lb-cap").innerHTML = lbCaption(img, cl, i, imgs.length);
  document.querySelectorAll("img.lb-cur").forEach(e => e.classList.remove("lb-cur"));
  img.classList.add("lb-cur");
  $("#lb-prev").disabled = i === 0;
  $("#lb-next").disabled = i === imgs.length - 1;
  $("#lb-up").disabled = !lbNeighbour(cl, -1);
  $("#lb-down").disabled = !lbNeighbour(cl, 1);
  $("#lb").classList.add("on");
}

function stepLb(step) {
  if (LB) openLb(LB.cl, LB.i + step);
}

/* The page scrolls to the new cluster, so the eye keeps its place when the view
   closes. */
function stepLbRow(step) {
  if (!LB) return;
  const x = lbNeighbour(LB.cl, step);
  if (!x) return;
  openLb(x, LB.i);
  x.scrollIntoView({ block: "start" });
}

function closeLb() {
  $("#lb").classList.remove("on");
  $("#lb-img").removeAttribute("src");
  LB = null;
}

for (const type of ["load", "error"]) {
  $("#lb-img").addEventListener(type, ev => ev.target.classList.remove("loading"));
}

document.addEventListener("click", ev => {
  const img = ev.target.closest("#list img[data-full]");
  if (img) {
    // A click with a modifier key follows the link of the image into a new tab.
    if (ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
    ev.preventDefault();
    const cl = img.closest(".cl");
    openLb(cl, lbImgs(cl).indexOf(img));
    return;
  }
  const btn = ev.target.closest("#lb .lb-btn");
  if (btn) {
    if (btn.id === "lb-close") closeLb();
    else if (btn.dataset.step) stepLb(+btn.dataset.step);
    else if (btn.dataset.rstep) stepLbRow(+btn.dataset.rstep);
    return;
  }
  if (ev.target.id === "lb") closeLb();      // a click on the dark ground
});
document.addEventListener("keydown", ev => {
  if (!LB || !$("#lb").classList.contains("on")) return;
  if (ev.key === "Escape") { closeLb(); return; }
  if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
  const step = { ArrowRight: 1, ArrowLeft: -1 }[ev.key];
  if (step !== undefined) { ev.preventDefault(); stepLb(step); return; }
  const rstep = { ArrowDown: 1, ArrowUp: -1 }[ev.key];
  if (rstep !== undefined) { ev.preventDefault(); stepLbRow(rstep); }
});

let TYPING = 0;
(async function init() {
  let res;
  try {
    res = await fetch("/api/clusters");
    DATA = await res.json();
  } catch (e) {
    $("#list").innerHTML = `<p class="empty">Cannot read /api/clusters: ${esc(e)}</p>`;
    return;
  }
  if (!res.ok) {
    $("#list").innerHTML = `<p class="empty">${esc(DATA.error || res.status)}</p>`;
    return;
  }
  if (!DATA.exists) {
    $("#about").hidden = true;
    $("#list").innerHTML = `<p class="empty">No cluster file yet: <code>${
      esc(DATA.file)}</code>. Run <code>python3 scripts/10_clusters.py</code>, then load
      this page again.</p>`;
    return;
  }
  CARDS = DATA.cards || {};
  $("#head-sub").textContent =
    `${DATA.clusters.length} clusters · built ${DATA.built_at || "?"}`;
  $("#about-body").innerHTML = aboutHtml();
  for (const id of ["#kind", "#signal", "#size", "#sort", "#img"]) {
    $(id).addEventListener("change", render);
  }
  $("#q").addEventListener("input", () => {
    clearTimeout(TYPING);
    TYPING = setTimeout(render, 150);
  });
  render();
  openFromHash();
})();
window.addEventListener("hashchange", openFromHash);
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------- main


def main():
    ap = argparse.ArgumentParser(description="Manual review tool for the my/ photo set")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--dataset", default="", metavar="NAME",
                    help="the dataset of `config.yaml` to review. The default is "
                         "the dataset named `default`")
    args = ap.parse_args()

    # The dataset MUST be chosen before any path of this file is read. The names
    # of this file are bound again, because they were bound at import.
    try:
        common.select_dataset(args.dataset or None)
    except common.ConfigError as exc:
        sys.exit("error: %s" % exc)
    bind_paths()

    common.print_config()

    global _rows, _state
    if not os.path.isdir(MY):
        sys.exit(f"error: photo set not found: {MY}")
    _state = load_state()
    global _excluded, _patches, _crops, _labels, _label_boxes
    _excluded = load_excluded()
    catalog = load_catalog()
    # The patches MUST be read before the rows, because a row states whether its
    # bottle photo is a patch. The crops and the label crops MUST be read before
    # the rows for the same reason.
    _patches = load_patches()
    _crops = load_crops()
    _labels, _label_boxes = load_label_crops()
    group_of, groups = load_variants()
    _rows = build_rows(catalog, group_of)
    total = sum(len(r["photos"]) for r in _rows)
    dropped = prune_state(_rows)
    if dropped:
        save_state()
        print(f"dropped {dropped} label(s) whose photo is no longer in my/")
    counts = count_state()
    print(f"wines: {len(_rows)}   candidate photos: {total}")
    print(f"labels loaded: {counts['labelled']} "
          f"(positive {counts['positive']}, negative {counts['negative']}, "
          f"unusable {counts['unusable']}) from {LABEL_FILE}")
    if _excluded:
        ex_rows = [r for r in _rows if r["slug"] in _excluded]
        print(f"excluded slugs: {len(_excluded)} "
              f"({sum(len(r['photos']) for r in ex_rows)} photo(s) out of the "
              f"benchmark) from {EXCLUDED_FILE}")
    missing = sum(1 for r in _rows if not r["has_bottle"])
    if missing:
        print(f"wines without a catalogue bottle photo: {missing}")
    if _patches:
        unknown = sorted(set(_patches) - set(catalog))
        print(f"patched catalogue photos: {len(_patches)} from {PATCH_DIR}")
        print(f"  {', '.join(sorted(_patches))}")
        if unknown:
            print(f"  WARNING: {len(unknown)} patch file(s) name no card of the "
                  f"catalogue: {', '.join(unknown)}", file=sys.stderr)
    if BOTTLE_CROPPED_DIR:
        print(f"cropped catalogue photos: {len(_crops)} from {BOTTLE_CROPPED_DIR}")
        stale = sorted(s for s, p in _patches.items()
                       if s in _crops and common.changed_after(p, _crops[s]))
        if stale:
            print(f"  WARNING: {len(stale)} patch(es) changed after the crop, so the "
                  f"page shows the patch with its border: {', '.join(stale)}. Run "
                  f"svoe-wino-hackaton/scripts/build_cropped.py again.", file=sys.stderr)

    if BOTTLE_LABEL_DIR or BOTTLE_LABEL_BOX_DIR:
        print(f"label crops: {len(_labels)} from {BOTTLE_LABEL_DIR or '(unset)'}")
        print(f"label box crops: {len(_label_boxes)} from "
              f"{BOTTLE_LABEL_BOX_DIR or '(unset)'}")
        without = sum(1 for r in _rows if r["has_bottle"] and not r["has_label"])
        if without:
            print(f"  {without} wine(s) with a package picture and no label crop; "
                  f"the page shows the package for them")

    if groups:
        print(f"variant groups: {len(groups)}   wines in a group: "
              f"{sum(1 for r in _rows if r['group'])}")

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    httpd.catalog = catalog
    httpd.groups = groups
    httpd.daemon_threads = True
    url = f"http://{args.host}:{args.port}/"
    print(f"review tool: {url}   (Ctrl+C to stop)")
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
