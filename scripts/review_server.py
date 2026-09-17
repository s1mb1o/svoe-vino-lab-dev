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

Run:
    python3 scripts/review_server.py
    python3 scripts/review_server.py --port 8154 --no-browser
"""
import argparse
import base64
import html
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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Every path comes from `config.yaml`. Read the file for the meaning of each key.
MY = common.PHOTO_DIR
# A deleted photo is moved here, not unlinked. The reviewer can get it back.
TRASH = common.TRASH_DIR
LABEL_FILE = common.LABEL_FILE
CATALOG = common.CATALOG_FILE
DEFAULT_PORT = 8154

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
LABELS = ("positive", "negative", "unusable", "variant")
COMMENT_MAX = 4000
VARIANTS_FILE = common.VARIANT_GROUPS_FILE
EXCLUDED_FILE = common.EXCLUDED_SLUGS_FILE
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


def load_variants():
    """Return slug -> group id, and group id -> the record of the group.

    `scripts/08_variants.py` writes the file. A missing file gives empty maps,
    and the tool then shows every wine as a row of its own.
    """
    if not os.path.exists(VARIANTS_FILE):
        print(f"note: no variant groups: {VARIANTS_FILE}", file=sys.stderr)
        return {}, {}
    try:
        with open(VARIANTS_FILE, encoding="utf-8") as f:
            blob = json.load(f)
    except (OSError, ValueError) as exc:
        print(f"warning: cannot read {VARIANTS_FILE}: {exc}", file=sys.stderr)
        return {}, {}
    by_slug, groups = {}, {}
    for g in blob.get("groups", []):
        gid = g.get("id")
        members = g.get("slugs") or []
        if not gid or len(members) < 2:
            continue
        groups[gid] = {"id": gid, "slugs": members,
                       "producer": g.get("producer", ""), "name": g.get("name", "")}
        for s in members:
            by_slug[s] = gid
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
        rec = catalog.get(slug) or {}
        bottle = rec.get("local_path")
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
        rows.append(
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
                "group": group_of.get(slug),
                "photos": photos,
                "min_conf": min(confs) if confs else None,
            }
        )
    return rows


def load_state():
    """Read `review-labels.json`. A missing or broken file gives empty state."""
    if not os.path.exists(LABEL_FILE):
        return {"labels": {}}
    try:
        with open(LABEL_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as exc:
        print(f"warning: cannot read {LABEL_FILE}: {exc}", file=sys.stderr)
        return {"labels": {}}
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
            "Field 'reassign_to' names the slug that the photo belongs to; "
            "scripts/09_apply_moves.py moves the file. "
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
    reassigned = commented = deleting = 0
    for photos in _state["labels"].values():
        for entry in photos.values():
            label = entry.get("label")
            if label in counts:
                counts[label] += 1
            if entry.get("reassign_to"):
                reassigned += 1
            if entry.get("delete"):
                deleting += 1
            if entry.get("comment"):
                commented += 1
    counts["labelled"] = sum(counts[k] for k in LABELS)
    counts["reassigned"] = reassigned
    counts["deleting"] = deleting
    counts["commented"] = commented
    counts["proposed"] = sum(
        1 for photos in _state["labels"].values() for e in photos.values()
        if e.get("proposed") and not e.get("label"))
    counts["wine_notes"] = sum(
        1 for w in _state["wines"].values() if (w or {}).get("comment"))
    return counts


API_FILTERS = ("all", "unlabelled", "needs_positive", "has_proposal",
               "fully_labelled", "in_variant_group")


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
        "bottle_path": rec.get("local_path"),
        "bottle_url": ("/img/bottle?slug=" + urllib.parse.quote(row["slug"])
                       if row["has_bottle"] else None),
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
                 "bottle_path": (catalog.get(x) or {}).get("local_path"),
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
            "has_bottle": bool(r.get("local_path")),
            "in_group": other in members,
            "score": -neg,
        })
    return out


# ------------------------------------------------------------------ the moves


def move_note(old_slug, new_slug, comment):
    """Return the comment of a moved photo.

    The comment is kept and gets one line in front of it that states where the
    photo was and where it went. The label is not kept: it judged the old pair.
    """
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


def free_name(directory, name):
    """Return a file name that is not taken in the directory."""
    if not os.path.exists(os.path.join(directory, name)):
        return name
    stem, ext = os.path.splitext(name)
    n = 2
    while os.path.exists(os.path.join(directory, "%s_moved%d%s" % (stem, n, ext))):
        n += 1
    return "%s_moved%d%s" % (stem, n, ext)


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
    """Move each planned photo into `work/trash/<slug>/` and drop its entry.

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

    def _file(self, path, cache=True):
        if not path or not os.path.isfile(path):
            self._send(404, "not found", "text/plain; charset=utf-8")
            return
        try:
            with open(path, "rb") as f:
                body = f.read()
        except OSError as exc:
            self._send(500, f"cannot read: {exc}", "text/plain; charset=utf-8")
            return
        extra = {"Cache-Control": "public, max-age=86400" if cache else "no-store"}
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
                self._json(200, {"rows": _rows, "labels": _state["labels"],
                                 "wines": _state["wines"],
                                 "excluded": _excluded,
                                 "groups": getattr(self.server, "groups", {}),
                                 "slugs": sorted(self.server.catalog)})
        elif route == "/api/state":
            with _lock:
                self._json(200, {"labels": _state["labels"], "wines": _state["wines"],
                                 "excluded": _excluded, "counts": count_state()})
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
            slug = (query.get("slug") or [""])[0]
            self._file(self._bottle_path(slug))
        elif route == "/img/photo":
            slug = (query.get("slug") or [""])[0]
            fn = (query.get("file") or [""])[0]
            self._file(self._photo_path(slug, fn))
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
        elif route == "/api/comment":
            self._set_comment(body)
        elif route == "/api/wine-comment":
            self._set_wine_comment(body)
        elif route == "/api/exclude":
            self._set_excluded(body)
        elif route == "/api/mark-delete":
            self._set_delete(body)
        elif route == "/api/apply-moves":
            self._apply_moves()
        elif route == "/api/fetch-image":
            self._fetch(body)
        elif route.startswith("/api/v1/"):
            self._api_post(route[len("/api/v1/"):], body)
        elif route == "/api/labels":
            self._set_many(body)
        else:
            self._json(404, {"error": "unknown route"})

    # -- route bodies

    def _reload(self):
        global _rows
        group_of, groups = load_variants()
        self.server.groups = groups
        rows = build_rows(getattr(self.server, "catalog", {}), group_of)
        with _lock:
            _rows = rows
            self._json(200, {"rows": _rows, "labels": _state["labels"],
                             "wines": _state["wines"], "excluded": _excluded})

    def _bottle_path(self, slug):
        rec = getattr(self.server, "catalog", {}).get(slug) or {}
        return rec.get("local_path")

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
        self._entry(slug, fn, "label", label)

    def _apply_reassign(self, slug, fn, to):
        """Record that the photo belongs to another slug. The file is not moved.

        `scripts/09_apply_moves.py` moves the files later, on one command.
        """
        if to and to not in self.server.catalog and not os.path.isdir(
                os.path.join(MY, os.path.basename(to))):
            raise ValueError("unknown target slug: %s" % to)
        if to == slug:
            raise ValueError("the target slug is the slug of the photo")
        self._entry(slug, fn, "reassign_to", to)

    def _apply_delete(self, slug, fn, on):
        """Mark or unmark one photo for deletion. The file is not touched here.

        `_apply_moves` moves every marked photo into `work/trash/` later, on one
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

    # ---- the API for an agent -------------------------------------------

    def _api_get(self, tail, query):
        catalog = getattr(self.server, "catalog", {})
        groups = getattr(self.server, "groups", {})
        one = (query.get("q") or [""])[0].strip().lower()

        if tail == "stats":
            with _lock:
                self._json(200, {
                    "wines": len(_rows),
                    "photos": sum(len(r["photos"]) for r in _rows),
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
                rows = [wine_view(r, catalog, groups) for r in _rows]
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

    def _apply_moves(self):
        """Move every recorded photo, delete every marked photo, rebuild the rows.

        The two actions run on one command, because the page offers one button.
        A photo that carries both a `reassign_to` and a `delete` is deleted and is
        not moved; `plan_moves` drops it.
        """
        global _rows
        try:
            with _lock:
                planned, done, bad = plan_moves(_state["labels"])
                moved, renamed = perform_moves(planned, _state["labels"])
                del_planned, del_gone = plan_deletes(_state["labels"])
                deleted, del_failed = perform_deletes(
                    del_planned, del_gone, _state["labels"])
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
                "renamed": [{"from": a, "to": b} for a, b in renamed],
                "deleted": [{"slug": a, "file": b, "to": c}
                            for a, b, c in deleted],
                "delete_failed": [{"slug": a, "file": b, "why": w}
                                  for a, b, w in del_failed],
                "delete_gone": len(del_gone),
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
            if row is not None:
                row["photos"] = [
                    {"file": f, "conf": int(NAME_RE.match(f).group(2))
                     if NAME_RE.match(f) else None}
                    for f in scan_photos(slug)
                ]
            return fn, (row["photos"] if row else [])

    def _known_slug(self, slug):
        return os.path.basename(slug) == slug and os.path.isdir(
            os.path.join(MY, slug))

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

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Svoe Vino photo review</title>
<style>
:root {
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
h1 { font-size: 15px; margin: 0 0 8px; font-weight: 650; letter-spacing: .01em; }
h1 .sub { color: var(--muted); font-weight: 400; }
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

main { padding: 12px 16px 64px; }
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
.bottle-col { display: flex; flex-direction: column; gap: 5px; min-width: 84px; }
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
.meta { min-width: 0; }
.meta .nm { font-weight: 650; }
.meta .pr { color: var(--text); }
.meta .sm { color: var(--muted); font-size: 12px; word-break: break-all; }
.meta a { color: var(--accent); }
.copy {
  border: 1px solid var(--line); background: var(--panel-2); color: var(--muted);
  border-radius: 4px; font: inherit; font-size: 10px; line-height: 1.2;
  padding: 1px 4px; margin-left: 4px; cursor: pointer; vertical-align: baseline;
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
.move {
  margin-top: 5px; width: 100%; padding: 4px 0; font: inherit; font-size: 11px;
  border-radius: 6px; border: 1px solid var(--line); background: var(--panel);
  color: var(--muted); cursor: pointer;
}
.move:hover { border-color: var(--accent); color: var(--text); }
.move.on { border-color: var(--accent); color: var(--accent); }
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
  <h1>Svoe Vino photo review <span class="sub" id="head-sub"></span></h1>
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
        <option value="moved">holds a photo moved to another slug</option>
        <option value="noted">holds a comment</option>
        <option value="proposal">holds a photo proposed by an agent</option>
        <option value="nobottle">no catalogue bottle photo</option>
      </select>
    </label>
    <label>Slugs
      <select id="slugsel" title="An excluded slug is out of the benchmark.">
        <option value="all">all</option>
        <option value="included">included</option>
        <option value="excluded">excluded</option>
      </select>
    </label>
    <label>Find <input id="q" type="search" placeholder="slug, name, producer, region"></label>
    <div class="progress">
      <span id="pending" hidden></span>
      <span id="stat"></span>
      <span class="meter"><i id="meter"></i></span>
    </div>
  </div>
</header>
<main>
  <p id="count"></p>
  <table><tbody id="rows"></tbody></table>
</main>
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
    <div class="mv-h">Move this photo to another wine</div>
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
      and <b>m</b> do not act while the cursor is in the field. Press Esc once to
      leave the field, and Esc again to close the view.</div>
  </aside>
  <div class="hint"><span id="lb-pos"></span>
    &larr; &rarr; photo of this wine &middot; &uarr; &darr; wine &middot;
    <b>1</b> positive &middot; <b>2</b> negative &middot; <b>3</b> unusable &middot;
    <b>4</b> other design &middot; <b>m</b> move &middot; right-click delete &middot; Esc close</div>
</div>
<div id="ctxmenu" class="ctxmenu" hidden></div>
<script>
let ROWS = [], V = {}, TOTAL = 0;
let VIEW = [];        // the rows as the table shows them now: filtered and sorted
let W = {};           // slug -> { comment, ts }: one note about a whole wine
/* slug -> { reason, ts }. An excluded slug holds an error, most often a wrong
   bottle photo. Its photos are NOT used for benchmarking. */
let EXC = {};
let GROUPS = {};      // group id -> { id, slugs, producer, name }
let SLUGS = [];       // every catalogue slug, for the move field
let LB = null;        // the place of the large view: { wine: index in VIEW, photo: index }

const $ = s => document.querySelector(s);
const esc = s => (s == null ? "" : String(s)).replace(/[&<>"']/g,
  c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/* The three labels. `negative` is a wanted result: the photo shows a different
   wine and stays in the set as a negative sample of this slug. `unusable` is
   the only label that takes a photo out of the set. */
const SHORT = { positive: "pos", negative: "neg", unusable: "unu", variant: "var" };
const KEY_OF = { "1": "positive", "2": "negative", "3": "unusable", "4": "variant" };
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
/* True when the photo is marked for deletion. The file is still on disk: the
   mark becomes a move into `work/trash/` only when "apply" is pressed. */
function deleteMarked(slug, file) {
  const r = V[slug] && V[slug][file];
  return !!(r && r.delete);
}
function wineNote(slug) {
  return (W[slug] && W[slug].comment) || "";
}
function isExcluded(slug) { return !!EXC[slug]; }
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
  const t = { positive: 0, negative: 0, unusable: 0, variant: 0, moved: 0, noted: 0,
              prop: 0, total: row.photos.length };
  for (const p of row.photos) {
    const l = labelOf(row.slug, p.file);
    if (l in SHORT) t[l]++;
    if (movedTo(row.slug, p.file)) t.moved++;
    if (commentOf(row.slug, p.file)) t.noted++;
    if (proposalOf(row.slug, p.file)) t.prop++;
  }
  t.labelled = t.positive + t.negative + t.unusable + t.variant;
  return t;
}

/* The short label counts of one wine, for the row and for the header. */
function rowTags(t) {
  return (t.positive ? `<span class="tag pos">${t.positive} pos</span> ` : "") +
         (t.variant ? `<span class="tag var">${t.variant} design</span> ` : "") +
         (t.negative ? `<span class="tag neg">${t.negative} neg</span> ` : "") +
         (t.unusable ? `<span class="tag unu">${t.unusable} unusable</span> ` : "") +
         (t.moved ? `<span class="tag grp">${t.moved} moved</span> ` : "") +
         (t.noted ? `<span class="tag grp">${t.noted} noted</span> ` : "") +
         (t.prop ? `<span class="tag var">${t.prop} proposed</span>` : "");
}

function matchFilter(row, mode) {
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

function labelButtons(current) {
  return Object.keys(SHORT).map(name =>
    `<button class="${SHORT[name]} ${current === name ? "on" : ""}" data-l="${name}"
             title="${TITLE[name]}">${GLYPH[name]}</button>`).join("");
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

function render() {
  const mode = $("#sort").value, filt = $("#filter").value;
  const sel = $("#slugsel").value;
  const q = $("#q").value.trim().toLowerCase();
  let rows = ROWS.filter(r => matchFilter(r, filt));
  if (sel === "excluded") rows = rows.filter(r => isExcluded(r.slug));
  else if (sel === "included") rows = rows.filter(r => !isExcluded(r.slug));
  if (q) {
    rows = rows.filter(r => (r.slug + " " + r.name + " " + r.producer + " " +
      r.region + " " + r.grapes).toLowerCase().includes(q));
  }
  rows = clusterGroups(sortRows(rows, mode));
  VIEW = rows;            // the arrow keys follow this order

  // Give each variant group one of two background colours, in the order of view.
  const gclass = new Map();
  let gi = 0;
  for (const r of rows) {
    if (r.group && !gclass.has(r.group)) gclass.set(r.group, (gi++ % 2) ? "grp-b" : "grp-a");
  }

  const html = rows.map(r => {
    const t = tally(r);
    const img = r.has_bottle
      ? `<img class="bottle" loading="lazy" src="/img/bottle?slug=${encodeURIComponent(r.slug)}"
             alt="" data-full="/img/bottle?slug=${encodeURIComponent(r.slug)}">`
      : `<div class="bottle missing">${r.in_catalog ? "no bottle<br>photo" : "not in<br>catalogue"}</div>`;
    const ex = isExcluded(r.slug), why = excludeReason(r.slug);
    const bottle = `<div class="bottle-col">${img}
      <button class="excl-btn ${ex ? "on" : ""}" data-excl="${esc(r.slug)}"
        title="${ex ? "excluded: " + esc(why) + "\nclick to include this slug again"
                    : "exclude this slug from the benchmark; its photos are then not used"}">${
        ex ? "Excluded" : "Exclude"}</button>
      ${ex && why ? `<div class="excl-why" title="${esc(why)}">${esc(why)}</div>` : ""}
      </div>`;
    const cards = r.photos.length ? r.photos.map(p => {
      const l = labelOf(r.slug, p.file), mv = movedTo(r.slug, p.file);
      const note = commentOf(r.slug, p.file), pr = proposalOf(r.slug, p.file);
      const dl = deleteMarked(r.slug, p.file);
      const src = `/img/photo?slug=${encodeURIComponent(r.slug)}&file=${encodeURIComponent(p.file)}`;
      return `<div class="card ${SHORT[l] || ""} ${mv ? "moved" : ""} ${note ? "noted" : ""}
                   ${pr ? "prop" : ""} ${dl ? "del" : ""}"
                   data-slug="${esc(r.slug)}" data-file="${esc(p.file)}">
        ${dl ? `<span class="del-tag" title="marked for deletion; press apply to move it to work/trash/">del</span>` : ""}
        ${pr ? `<span class="prop-tag" title="${esc(pr.by || "agent")} proposes ${
          esc(pr.proposed)}${pr.source_url ? "\nfrom " + esc(pr.source_url) : ""}">${
          esc(pr.proposed).slice(0, 3)} ${Math.round((pr.confidence || 0) * 100)}%</span>` : ""}
        ${noteBadge(note)}
        <img loading="lazy" src="${src}" alt="" data-full="${src}">
        <div class="cap"><span>${esc(p.file.split("_")[0] || "")}</span>
          <span>${p.conf === null ? "" : "conf " + p.conf}</span></div>
        <div class="btns">${labelButtons(l)}</div>
        <button class="move ${mv ? "on" : ""}" data-move="1"
                title="move this photo to another wine slug">${
          mv ? "\u2192 " + esc(mv) : "\u2192 move"}</button>
        </div>`;
    }).join("") : `<span class="empty">no photos</span>`;

    const grp = r.group ? GROUPS[r.group] : null;
    return `<tr data-slug="${esc(r.slug)}" class="${r.group ? gclass.get(r.group) : ""} ${
      ex ? "excl" : ""}">
      <td class="wine"><div class="wine-inner">${bottle}<div class="meta">
        <div class="nm">${esc(r.name) || "<span class='empty'>unknown name</span>"}</div>
        <div class="pr">${esc(r.producer)}</div>
        <div class="sm">${esc(r.category)}${r.region ? " &middot; " + esc(r.region) : ""}</div>
        <div class="sm">${esc(r.grapes)}</div>
        <div class="sm">${esc(r.slug)}<button class="copy" data-copy="${esc(r.slug)}"
             title="copy the slug to the clipboard">copy</button></div>
        ${grp ? `<div class="sm"><span class="tag grp">variant group of ${
          grp.slugs.length}</span></div>` : ""}
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
  $("#count").textContent = `${rows.length} of ${ROWS.length} wines shown`;
  stats();
}

function stats() {
  const all = { positive: 0, negative: 0, unusable: 0, variant: 0, moved: 0 };
  let doneWines = 0;
  for (const r of ROWS) {
    const t = tally(r);
    all.positive += t.positive; all.negative += t.negative;
    all.unusable += t.unusable; all.variant += t.variant; all.moved += t.moved;
    if (t.total && t.labelled === t.total) doneWines++;
  }
  const labelled = all.positive + all.negative + all.unusable + all.variant;
  $("#stat").innerHTML = `labelled <b>${labelled}</b>/<b>${TOTAL}</b> photos &middot; ` +
    rowTags({ ...all, total: TOTAL }) + ` &middot; ` +
    `<b>${doneWines}</b>/<b>${ROWS.length}</b> wines done`;
  $("#meter").style.width = TOTAL ? (100 * labelled / TOTAL).toFixed(1) + "%" : "0";

  let pending = 0, pendingDel = 0;
  for (const photos of Object.values(V)) {
    for (const e of Object.values(photos)) {
      if (e.delete) pendingDel++;          // a deletion drops the move
      else if (e.reassign_to) pending++;
    }
  }
  const box = $("#pending");
  box.hidden = pending === 0 && pendingDel === 0;
  if (!box.hidden) {
    const parts = [];
    if (pending) parts.push(`<b>${pending}</b> move${pending > 1 ? "s" : ""}`);
    if (pendingDel) parts.push(`<b>${pendingDel}</b> deletion${pendingDel > 1 ? "s" : ""}`);
    box.innerHTML = parts.join(" and ") + ` pending ` +
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
  fig.querySelector("figcaption").innerHTML = item.cap;
  fig.hidden = false;
}

function bottleItem(r) {
  if (!r || !r.has_bottle) return null;
  return {
    src: `/img/bottle?slug=${encodeURIComponent(r.slug)}`,
    cap: `<b>catalogue bottle</b><br>${esc(r.name || r.slug)}` +
         (r.producer ? `<br>${esc(r.producer)}` : "") +
         (r.group && GROUPS[r.group]
           ? `<br>variant group of ${GROUPS[r.group].slugs.length}` : ""),
  };
}

function candItem(r, pi) {
  const p = r.photos[pi];
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
  const l = labelOf(r.slug, p.file);
  const mv = movedTo(r.slug, p.file), pr = proposalOf(r.slug, p.file);
  el.textContent = (l === "positive" ? "positive \u2014 this wine"
                 : l === "negative" ? "negative sample \u2014 a different wine"
                 : l === "unusable" ? "unusable \u2014 not in the set"
                 : l === "variant" ? "this wine, different design"
                 : pr ? `${pr.by || "agent"} proposes ${pr.proposed} (${
                     Math.round((pr.confidence || 0) * 100)}%)`
                 : "not labelled") + (mv ? "  \u2192 " + mv : "");
  el.className = SHORT[l] || (pr ? "var" : "none");
}

/* Open the large view at one photo of one wine. The catalogue bottle stays at
   the left, so the eye compares the two labels without a scroll.
   `wi` is an index in VIEW, the order that the table shows now. */
function showLightbox(wi, pi) {
  if (wi < 0 || wi >= VIEW.length) return;
  const r = VIEW[wi];
  if (!r.photos.length) return;
  pi = Math.max(0, Math.min(pi, r.photos.length - 1));
  LB = { wine: wi, photo: pi };

  fillFig("#lb-ref", bottleItem(r));
  fillFig("#lb-cand", candItem(r, pi));
  renderLbStatus();
  $("#lb-pos").textContent =
    `wine ${wi + 1} of ${VIEW.length} — ${r.slug} · `;
  setHash(`${r.slug}/${r.photos[pi].file}`);
  loadComment(r, pi);
  $("#lb").classList.add("open");

  // Keep the table at the same wine, so the place is held when the view closes.
  const tr = $("#rows").children[wi];
  if (tr) tr.scrollIntoView({ block: "center" });
}

/* Move to the previous or the next wine. A wine with no photo is stepped over. */
function stepWine(step) {
  if (!LB) return;
  let i = LB.wine + step;
  while (i >= 0 && i < VIEW.length && !VIEW[i].photos.length) i += step;
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

async function copySlug(btn) {
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

/* Move every recorded photo now. The server moves the files, drops the label of
   each moved photo, keeps its comment with a line that states where it was, and
   answers the rebuilt rows. */
async function applyMoves(btn) {
  let nMove = 0, nDel = 0;
  for (const photos of Object.values(V)) {
    for (const e of Object.values(photos)) {
      if (e.delete) nDel++; else if (e.reassign_to) nMove++;
    }
  }
  const warn = [];
  if (nMove) warn.push(
    `Move ${nMove} photo(s) to their target wine. Each moved photo loses its ` +
    `label and must be reviewed again. Its comment is kept and states where ` +
    `the photo was.`);
  if (nDel) warn.push(
    `DELETE ${nDel} photo(s). Each one is moved out of my/ into work/trash/ ` +
    `and loses its label, its comment and any proposal. It leaves the set.`);
  if (!warn.length) return;
  if (!window.confirm(`Carry out the pending work now?\n\n` + warn.join("\n\n"))) return;
  btn.disabled = true; btn.textContent = "working...";
  let out = {};
  try {
    const res = await fetch("/api/apply-moves", { method: "POST" });
    out = await res.json();
    if (!res.ok) throw new Error(out.error || res.status);
  } catch (e) {
    alert("apply failed: " + e.message);
    btn.disabled = false; btn.textContent = "apply";
    return;
  }
  ROWS = out.rows; V = out.labels || {}; W = out.wines || W;
  TOTAL = ROWS.reduce((k, r) => k + r.photos.length, 0);
  $("#head-sub").textContent = `${ROWS.length} wines, ${TOTAL} candidate photos`;
  render();
  const deleted = out.deleted || [], delFailed = out.delete_failed || [];
  const lines = out.moved.map(m => `${m.from}/${m.file} -> ${m.to}/${m.as}`);
  const fails = out.failed.map(f => `! ${f.from}/${f.file} -> ${f.to}: ${f.why}`);
  const dels = deleted.map(d => `${d.slug}/${d.file} -> trash`);
  const dfails = delFailed.map(d => `! ${d.slug}/${d.file}: ${d.why}`);
  const report = [];
  if (out.moved.length || fails.length) {
    report.push(`moved ${out.moved.length} photo(s)`, ...lines, ...fails);
  }
  if (deleted.length || dfails.length) {
    if (report.length) report.push("");
    report.push(`deleted ${deleted.length} photo(s) into work/trash/`, ...dels, ...dfails);
  }
  if (out.delete_gone) report.push(`${out.delete_gone} marked photo(s) were already gone`);
  alert(report.length ? report.join("\n") : "nothing to do");
}

/* ---- the right-click menu of one photo ---- */

/* Mark one photo for deletion, or take the mark away. The file stays on disk.
   "apply" moves every marked photo into `work/trash/`. */
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

/* Show the menu for one photo at the pointer. */
function showCtxMenu(x, y, slug, file) {
  const m = $("#ctxmenu");
  const marked = deleteMarked(slug, file);
  m.innerHTML =
    `<div class="ctx-head">${esc(file)}</div>` +
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
  hideCtxMenu();
  if (act === "delete") markDelete(slug, file, true);
  else if (act === "undelete") markDelete(slug, file, false);
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
  const hits = ROWS.filter(r =>
    (r.slug + " " + r.name + " " + r.producer).toLowerCase().includes(q)).slice(0, 5);
  $("#ad-list").innerHTML = hits.map(r => `
    <button class="mv-item" data-slug="${esc(r.slug)}">
      ${r.has_bottle
        ? `<img loading="lazy" src="/img/bottle?slug=${encodeURIComponent(r.slug)}" alt="">`
        : `<span class="no-img"></span>`}
      <span class="t"><b>${esc(r.name) || esc(r.slug)}</b>
        <div>${esc(r.producer)}</div><div>${esc(r.slug)}</div></span>
    </button>`).join("");
}

async function addToWine(slug) {
  if (!slug) { alert("Name the wine slug."); return; }
  if (!ROWS.some(r => r.slug === slug)) {
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
      if (row) row.photos = out.photos;
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
      if (row) row.photos = out.photos;
      added.push(out.file);
    } catch (e) {
      alert(`cannot add ${f.name}: ${e.message}`);
    }
  }
  if (tr) tr.classList.remove("busy");
  if (added.length) {
    TOTAL = ROWS.reduce((k, r) => k + r.photos.length, 0);
    $("#head-sub").textContent = `${ROWS.length} wines, ${TOTAL} candidate photos`;
    render();
  }
}

/* ---- the move dialog ----
   The dialog offers the five wines that the photo most likely belongs to, with
   their catalogue bottle photo, and takes any other slug in a field.
   The file is not moved here. The target is written to the label file, and the
   button `apply` in the header moves the files. */
let MV_AT = null;

async function askMove(card, slugArg, fileArg) {
  const slug = card ? card.dataset.slug : slugArg;
  const file = card ? card.dataset.file : fileArg;
  if (!slug || !file) return;
  MV_AT = { slug, file };
  const cur = movedTo(slug, file) || "";

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
  if (!MV_AT || MV_AT.slug !== slug || MV_AT.file !== file) return;

  $("#mv-list").innerHTML = targets.length ? targets.map(t => `
    <button class="mv-item ${t.slug === cur ? "sel" : ""}" data-slug="${esc(t.slug)}">
      ${t.has_bottle
        ? `<img loading="lazy" src="/img/bottle?slug=${encodeURIComponent(t.slug)}" alt="">`
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

async function commitMove(to) {
  const at = MV_AT;
  if (!at) return;
  const res = await fetch("/api/reassign", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ slug: at.slug, file: at.file, to }),
  });
  const out = await res.json();
  if (!res.ok) { alert("move failed: " + (out.error || res.status)); return; }
  if (to) {
    (V[at.slug] = V[at.slug] || {})[at.file] =
      { ...((V[at.slug] || {})[at.file] || {}), reassign_to: to };
  } else if (V[at.slug] && V[at.slug][at.file]) {
    delete V[at.slug][at.file].reassign_to;
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
  const cut = raw.indexOf("/");
  if (cut < 0) return false;
  const slug = decodeURIComponent(raw.slice(0, cut));
  const file = decodeURIComponent(raw.slice(cut + 1));
  if (!ROWS.some(r => r.slug === slug)) return false;
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
  if (copy) { copySlug(copy); return; }

  const exb = ev.target.closest(".excl-btn");
  if (exb) { toggleExclude(exb); return; }

  const move = ev.target.closest(".move");
  if (move) { askMove(move.closest(".card")); return; }

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
      else if ($("#mv").classList.contains("open")) closeMove();
      else ev.target.blur();
      ev.stopPropagation();
    }
    return;
  }
  if (ev.key === "Escape") {
    if (!$("#ctxmenu").hidden) hideCtxMenu();
    else if ($("#ad").classList.contains("open")) closeWine();
    else if ($("#mv").classList.contains("open")) closeMove();
    else closeLightbox();
    return;
  }
  if ($("#mv").classList.contains("open") || $("#ad").classList.contains("open")) {
    return;                                          // a dialog takes the keys
  }
  if (!LB || !$("#lb").classList.contains("open")) return;
  if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
  const step = { ArrowRight: 1, ArrowLeft: -1 }[ev.key];
  if (step !== undefined) { ev.preventDefault(); showLightbox(LB.wine, LB.photo + step); return; }
  const wstep = { ArrowDown: 1, ArrowUp: -1 }[ev.key];
  if (wstep !== undefined) { ev.preventDefault(); stepWine(wstep); return; }
  // "1" positive, "2" negative sample, "3" unusable, "4" this wine other design.
  // The same key again clears the label. "m" moves the photo to another slug.
  if (ev.key === "m" || ev.key === "M") {
    ev.preventDefault();
    const r = VIEW[LB.wine];
    askMove(cardOf(r.slug, r.photos[LB.photo].file), r.slug, r.photos[LB.photo].file);
    return;
  }
  const want = KEY_OF[ev.key];
  if (want) {
    ev.preventDefault();
    const r = VIEW[LB.wine];
    setLabel(r.slug, r.photos[LB.photo].file, want);
  }
});
for (const id of ["#sort", "#filter", "#slugsel"]) {
  $(id).addEventListener("change", render);
}
let t = null;
$("#q").addEventListener("input", () => { clearTimeout(t); t = setTimeout(render, 180); });

(async function init() {
  const data = await (await fetch("/api/rows")).json();
  ROWS = data.rows; V = data.labels || {}; W = data.wines || {};
  EXC = data.excluded || {};
  GROUPS = data.groups || {}; SLUGS = data.slugs || [];
  $("#slug-list").innerHTML = SLUGS.map(x => `<option value="${esc(x)}">`).join("");
  $("#my-slug-list").innerHTML =
    ROWS.map(r => `<option value="${esc(r.slug)}">`).join("");
  TOTAL = ROWS.reduce((n, r) => n + r.photos.length, 0);
  $("#head-sub").textContent = `${ROWS.length} wines, ${TOTAL} candidate photos`;
  render();
  openFromHash();
})();
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
    args = ap.parse_args()

    common.print_config()

    global _rows, _state
    if not os.path.isdir(MY):
        sys.exit(f"error: photo set not found: {MY}")
    _state = load_state()
    global _excluded
    _excluded = load_excluded()
    catalog = load_catalog()
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
