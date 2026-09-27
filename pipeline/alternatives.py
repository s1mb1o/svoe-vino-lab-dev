"""Store, type, and remove the alternative images of one wine.

An alternative image is a row of `wine_image` of the type `full_front`, `label_front`,
`full_back`, or `label_back`. The lab server calls these functions for the routes
`/api/dataset-alternative` and `/api/dataset-alternative-type`. Read
`docs/plans/16_alternative-images.md`.

Rules:
- A photo is a JPEG, PNG, or WebP image of at most `patches.MAX_BYTES` bytes, as a patch.
- The file goes to `images/additional/<sha256>.<extension>`, or reuses a stored file with
  the same SHA-256.
- SAM3 tells a full package from a label close-up (`detect`), and the front from the back
  (`side`): a barcode on the package is the back. The type is one of the four. SAM3 does
  not answer: the type is `full_front`, and the answer holds a warning.
- A full type gets the package cut of `derive.py`. A label type gets the label cut
  (`label_instance`): the segment of the main label, or the box around the main label
  and the other body labels of the same bottle (`body_labels`). In a label close-up the
  largest label is the main label, with no bottle test (`SETTINGS_LABEL_CLOSE_UP`).
  `image_derivative` holds one cut for each original and kind
  (`package`, `label`), so each row shows the cut of its own kind, and a change back to
  a kind reuses its cut.
- A request processes a photo whenever its row has no current cut of its kind: an upload,
  the same photo again, and each type change. So a photo stored while SAM3 was down gets
  its cut on the next request.
- The same photo on the same wine a second time changes no row.
- `remove_alternative` deletes the row alone. The file stays in the store.
- SAM3 runs before the write transaction, so a slow SAM3 does not hold the write lock.
- A manual cut (plan 56) is a polygon of the owner on the original. It replaces the cut
  of the kind of the current type, and no automatic run replaces it
  (`derive.is_manual`). `reset_manual_cut` removes it, and SAM3 cuts the photo again.

The store path and the `INSERT INTO image` are each in one function of `patches.py`:
`file_path` and `insert_image`. `lab_server.alternative_images` builds the URLs.
"""
import base64
import hashlib
import io
import json
import math
import os

from PIL import Image, ImageChops, ImageDraw, ImageFilter

import derive
import imagestore
import labdb
import patches

TYPES = ("full_front", "label_front", "full_back", "label_back")
KINDS = {"full_front": "full", "full_back": "full",
         "label_front": "label", "label_back": "label"}
# The kind of cut in `image_derivative` of each kind of photo.
CUTS = {"full": "package", "label": "label"}
# The type of a detected kind and side.
DETECTED = {("full", "front"): "full_front", ("full", "back"): "full_back",
            ("label", "front"): "label_front", ("label", "back"): "label_back"}
MATCH_METHOD = "manual"
FOLDER = labdb.IMAGE_FOLDERS["full_front"]

# The nouns of the detection. The answer also gives the label cut of a close-up. The
# owner chose the four nouns `barcode, bottle, label, bottle neck` for a quick
# classification, and `can` for the can rule (2026-09-25T11:45:49 and the answer after it).
DETECT_TEXTS = "barcode, bottle, label, bottle neck, can"
BOTTLE_NOUN = "bottle"
NECK_NOUN = "bottle neck"
CAN_NOUN = "can"
# A barcode is on the back of a package. The owner set this rule on 2026-09-25. The
# barcode counts when its centre lies on the largest bottle or can, so a price tag on a
# shop shelf does not count; a photo with no bottle and no can counts each barcode. In
# the FRAP prototype the barcode alone gave the wrong side for 9 of 72 full packages.
# A barcode needs a score of at least `BARCODE_SCORE` and a width of at least
# `BARCODE_WIDTH` of the package: a probe of 2026-09-25 found faint false barcodes in the
# text of a front label (scores 0.38 and 0.56) and the edge of a barcode on the side of a
# front view (6 % of the width); real back barcodes had 0.94 and 0.95, 18 % and 30 %.
BARCODE_NOUN = "barcode"
BARCODE_SCORE, BARCODE_WIDTH = 0.7, 0.10
LABEL_NOUNS = ("label",)
NO_SEPARATE_LABEL_NOUNS = ("packet", "box")
# A real neck: its top is below `NECK_TOP` of the height, its bottom is above
# `NECK_BOTTOM` of the height, it is not wider than `NECK_WIDTH` of the largest bottle, and
# it lies inside that bottle with a tolerance of `INSIDE` of the width and of the height.
# The rule comes from the FRAP page-role prototype of 2026-09-23 (workspace
# `ResearchLog.md`), with the test "inside" of plan 16.
NECK_TOP, NECK_BOTTOM, NECK_WIDTH, INSIDE = 0.02, 0.5, 0.7, 0.02
# A can with no neck is a full package when it covers `CAN_HEIGHT` of the height of a
# photo that is at least `CAN_ASPECT` times as tall as it is wide.
CAN_HEIGHT, CAN_ASPECT = 0.9, 2.0
# The label rule of `svoe-wino-hackaton/scripts/build_labels.py`.
BOTTLE_IOU, BOTTLE_COVER, BOTTLE_COVER_IOU = 0.80, 0.80, 0.40
DUPLICATE_IOU = 0.90
MIN_BOX_SIDE = 8
# A second body label on the bottle of the main label, owner answer of
# 2026-09-25T19:16:44+0300: a label counts when its centre lies on the largest bottle,
# when less than `PART_COVER` of it lies inside the main label, and when it has at least
# `BODY_AREA` of the area and `BODY_WIDTH` of the width of the main label. A neck label, a
# capsule, and a part of the main label do not count. With a counted label, the cut is
# the box around the main label and the counted labels, with no mask: the segment of one
# label loses the other label. On 251 cached SAM3 answers of 2026-09-25, 13 photos got the
# box: two labels one above the other, and sparkling wines with a large shoulder label.
BODY_AREA, BODY_WIDTH, PART_COVER = 0.25, 0.60, 0.80

_LABEL_HEAD = ("SAM3 %r, threshold %s, mask %s, max side %d; "
               % (DETECT_TEXTS, derive.SAM3_THRESHOLD, derive.SAM3_MASK_THRESHOLD,
                  derive.SAM3_MAX_SIDE))
_LABEL_TAIL = (
    "; a second label on the bottle, less than %s inside it, with >= %s of its area and "
    ">= %s of its width: the box of the labels, no mask; else the mask: mask blur %s of "
    "the long side, keep >= %d/255; edge blur %s px"
    % (PART_COVER, BODY_AREA, BODY_WIDTH, derive.MASK_BLUR, derive.MASK_KEEP,
       derive.EDGE_BLUR))
SETTINGS_LABEL = (_LABEL_HEAD + "the largest label that is not the package "
                  "(build_labels.py), else the largest label" + _LABEL_TAIL)
# A label close-up (`label_front`, `label_back`): the largest label wins, with no bottle
# test. Owner message of 2026-09-26T19:38:53+0300: in a close-up the bottle fills the
# frame, so the box of the real label is close to the box of the bottle (IoU 0.84 on
# `d9f847bd…`). The bottle test dropped that label and kept a small QR sticker.
SETTINGS_LABEL_CLOSE_UP = (_LABEL_HEAD + "a label close-up: the largest label, with no "
                           "bottle test" + _LABEL_TAIL)
SETTINGS_LABEL_ABSENCE = (
    "SAM3 %r found no label; SAM3 %r classified the package as packet or box; "
    "threshold %s, mask %s, max side %d"
    % (DETECT_TEXTS, derive.SAM3_TEXTS, derive.SAM3_THRESHOLD,
       derive.SAM3_MASK_THRESHOLD, derive.SAM3_MAX_SIDE))

NO_PROCESSED_FILE = "The photo is stored with no processed file. The card shows it as it is."
NO_NEW_CUT = ("The photo got no cut of its new kind. The card shows it as it is; the next "
              "type change processes it again.")


class _Down:
    """A segmenter whose service did not answer the detection. `derive_all` then asks
    no more, as `derive._Once` does in one run."""

    def __init__(self, reason):
        self.reason = reason

    def segment(self, image):
        raise derive.Sam3Unavailable("no request: %s" % self.reason)


def file_path(db_path, folder, digest, extension):
    """Return the path of one file of the image store."""
    return patches.file_path(db_path, folder, digest, extension)


def insert_image(conn, digest, extension, width, height):
    """Write the row of `image` of an alternative photo, unless the table holds it."""
    patches.insert_image(conn, digest, extension, width, height, FOLDER)


def has_current_cut(conn, digest, kind, close_up=False):
    """Tell whether the original `digest` has a cut of `kind` (`full` or `label`) with
    the present settings. `close_up` tells that the label cut is the cut of a label
    close-up (`SETTINGS_LABEL_CLOSE_UP`)."""
    row = conn.execute("SELECT settings FROM image_derivative WHERE source_sha256 = ? "
                       "AND kind = ?", (digest, CUTS[kind])).fetchone()
    if row is None:
        return False
    if derive.is_manual(row[0]):
        return True
    if kind == "label":
        return row[0] == (SETTINGS_LABEL_CLOSE_UP if close_up else SETTINGS_LABEL)
    return row[0] in derive.PRESENT_SETTINGS


def current_absence(conn, digest):
    """Return the reason when the label derivative of `digest` is not applicable under
    the present rule. Return None for no marker or a marker of old settings."""
    row = conn.execute(
        "SELECT settings, reason FROM image_derivative_absence WHERE source_sha256 = ? "
        "AND kind = 'label'", (digest,)).fetchone()
    return row[1] if row and row[0] == SETTINGS_LABEL_ABSENCE else None


def _box(item):
    box = item.get("box")
    if not box or len(box) != 4:
        return None
    return tuple(float(value) for value in box)


def _area(box):
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def _iou(a, b):
    inter = _area((max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])))
    union = _area(a) + _area(b) - inter
    return inter / union if union > 0 else 0.0


def _covers(a, b):
    """Return the share of `b` that lies inside `a`."""
    inter = _area((max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])))
    return inter / _area(b) if _area(b) > 0 else 0.0


def detect(instances, width, height):
    """Return `full` or `label` for the SAM3 instances of a photo of `width` × `height`
    pixels (the pixels of the sent copy, as the boxes)."""
    bottles = sorted((box for box in (_box(item) for item in instances
                                      if item.get("label") == BOTTLE_NOUN) if box),
                     key=lambda box: -_area(box))
    if bottles:
        bx1, by1, bx2, by2 = bottles[0]
        for item in instances:
            box = _box(item)
            if item.get("label") != NECK_NOUN or not box:
                continue
            x1, y1, x2, y2 = box
            inside = (x1 >= bx1 - INSIDE * width and x2 <= bx2 + INSIDE * width
                      and y1 >= by1 - INSIDE * height)
            if (inside and y1 > NECK_TOP * height and y2 < NECK_BOTTOM * height
                    and (x2 - x1) <= NECK_WIDTH * (bx2 - bx1)):
                return "full"
    for item in instances:
        box = _box(item)
        if (item.get("label") == CAN_NOUN and box and box[3] - box[1] >= CAN_HEIGHT * height
                and height >= CAN_ASPECT * width):
            return "full"
    return "label"


def side(instances, width, height):
    """Return `back` when a barcode lies on the package of the photo, else `front`. The
    package is the largest bottle or can; the boxes are in the pixels of the sent copy.
    With no package, a barcode of `BARCODE_SCORE` counts wherever it is."""
    packages = sorted((box for box in (_box(item) for item in instances
                                       if item.get("label") in (BOTTLE_NOUN, CAN_NOUN)) if box),
                      key=lambda box: -_area(box))
    for item in instances:
        box = _box(item)
        if (item.get("label") != BARCODE_NOUN or not box
                or float(item.get("score") or 0) < BARCODE_SCORE):
            continue
        if not packages:
            return "back"
        px1, py1, px2, py2 = packages[0]
        if box[2] - box[0] < BARCODE_WIDTH * (px2 - px1):
            continue
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        if (px1 - INSIDE * width <= cx <= px2 + INSIDE * width
                and py1 - INSIDE * height <= cy <= py2 + INSIDE * height):
            return "back"
    return "front"


def label_instance(instances, close_up=False):
    """Return the label instance of a photo, or None.

    The rule of `build_labels.py`: of two instances of one region the larger one stays;
    a label that is the bottle, or that holds the bottle, is the package and not a label;
    the largest mask wins, not the best score. When the rule leaves no label, the largest
    label counts. In a label close-up (`close_up`) the label can fill the frame and equal
    the bottle box, so the largest label wins with no bottle test.
    """
    candidates, _bottles = _label_candidates(instances, close_up)
    return candidates[0] if candidates else None


def label_absence_reason(instances):
    """Return a reason when the package instances identify a packet or box.

    The caller uses this only after the label prompt found no label. The largest
    packet or box wins. A bottle or can with no detected label stays a real failure.
    """
    candidates = [item for item in instances
                  if item.get("label") in NO_SEPARATE_LABEL_NOUNS and _box(item)]
    if not candidates:
        return None
    item = max(candidates, key=lambda value: (_area(_box(value)),
                                               float(value.get("score") or 0)))
    return "the %s has no separate label" % item["label"]


def _label_candidates(instances, close_up=False):
    """Return (the labels of the rule of `label_instance`, the largest first; the bottle
    boxes). With `close_up`, no label is dropped by the bottle test."""
    labels, bottles = [], []
    for item in instances:
        box = _box(item)
        if not box or item.get("score") is None:
            continue
        if box[2] - box[0] < MIN_BOX_SIDE or box[3] - box[1] < MIN_BOX_SIDE:
            continue
        if item.get("label") == BOTTLE_NOUN:
            bottles.append(box)
        elif item.get("label") in LABEL_NOUNS and item.get("mask_png_b64"):
            labels.append(item)
    order = lambda item: (-int(item.get("area") or 0), -float(item["score"]))
    unique = []
    for item in sorted(labels, key=order):
        if all(_iou(_box(item), _box(kept)) <= DUPLICATE_IOU for kept in unique):
            unique.append(item)
    kept = [item for item in unique
            if not any(_iou(_box(item), bottle) > BOTTLE_IOU
                       or (_covers(_box(item), bottle) > BOTTLE_COVER
                           and _iou(_box(item), bottle) > BOTTLE_COVER_IOU)
                       for bottle in bottles)]
    return (unique if close_up else (kept or unique)), bottles


def _centre_on(box, package, width, height):
    """Tell whether the centre of `box` lies on `package`, with the tolerance `INSIDE`
    of the photo of `width` × `height` pixels."""
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    return (package[0] - INSIDE * width <= cx <= package[2] + INSIDE * width
            and package[1] - INSIDE * height <= cy <= package[3] + INSIDE * height)


def body_labels(instances, main, width, height):
    """Return the other labels of `instances` that count next to the label `main` (the
    rule of `BODY_AREA`), the largest first. The boxes are in the pixels of the sent copy
    of `width` × `height` pixels. With no bottle, each label can count."""
    candidates, bottles = _label_candidates(instances)
    bottle = max(bottles, key=_area) if bottles else None
    main_box, main_area = _box(main), float(main.get("area") or 0)
    out = []
    for item in candidates:
        if item is main:
            continue
        box = _box(item)
        if (float(item.get("area") or 0) >= BODY_AREA * main_area
                and box[2] - box[0] >= BODY_WIDTH * (main_box[2] - main_box[0])
                and _covers(main_box, box) < PART_COVER
                and (bottle is None or _centre_on(box, bottle, width, height))):
            out.append(item)
    return out


def _copy_scale(image, instance):
    """Return the scale of the copy that SAM3 got: the width of the mask of `instance`
    over the width of `image`."""
    with Image.open(io.BytesIO(base64.b64decode(instance["mask_png_b64"]))) as mask:
        return mask.width / image.width


def label_box_cut(image, items, scale):
    """Return (the crop of `image` to the box around the boxes of `items` as an RGBA
    image, the box in the pixels of `image`). The boxes of `items` are in the pixels of the
    sent copy of the scale `scale`. No mask is applied."""
    boxes = [_box(item) for item in items]
    box = (max(0, math.floor(min(b[0] for b in boxes) / scale)),
           max(0, math.floor(min(b[1] for b in boxes) / scale)),
           min(image.width, math.ceil(max(b[2] for b in boxes) / scale)),
           min(image.height, math.ceil(max(b[3] for b in boxes) / scale)))
    if box[2] <= box[0] or box[3] <= box[1]:
        box = (0, 0, image.width, image.height)
    return image.convert("RGBA").crop(box), box


def label_cut(image, instance):
    """Return (the label cut as an RGBA image, its box in the pixels of `image`)."""
    with Image.open(io.BytesIO(base64.b64decode(instance["mask_png_b64"]))) as mask:
        mask = mask.convert("L")
    if mask.size != image.size:
        mask = mask.resize(image.size, Image.Resampling.BILINEAR)
    alpha = derive.refine_mask(mask.point(lambda value: 255 if value >= 128 else 0))
    if image.mode == "RGBA":
        alpha = ImageChops.darker(alpha, image.getchannel("A"))
    box = alpha.point(lambda value: 255 if value > 0 else 0).getbbox() \
        or (0, 0, image.width, image.height)
    out = image.convert("RGBA")
    out.putalpha(alpha)
    return out.crop(box), box


def label_cut_of(image, instances, close_up=False):
    """Return (the method, the label cut as an RGBA image, its box in the pixels of
    `image`), or None when the SAM3 answer `instances` of `DETECT_TEXTS` holds no label.

    One label gets its mask (`seg`). A label with other body labels gets the box around
    them all (`crop`). `label_derivatives` and the embedding runner of plan 33 use this
    function, so a test photo gets the cut of a catalogue image. `close_up` selects the
    main label of a label close-up (`label_instance`).
    """
    instance = label_instance(instances, close_up)
    if instance is None:
        return None
    scale = _copy_scale(image, instance)
    others = body_labels(instances, instance, image.width * scale, image.height * scale)
    if others:
        result, box = label_box_cut(image, [instance] + others, scale)
        return "crop", result, box
    result, box = label_cut(image, instance)
    return "seg", result, box


def label_derivatives(conn, db_path, digest, image, icc_profile, instances, log,
                      close_up=False):
    """Return the `derive.Derivatives` (kind `label`) of the label cut of one original.

    `instances` is the SAM3 answer of `DETECT_TEXTS` with masks. A present label cut with
    `SETTINGS_LABEL` is kept, or with `SETTINGS_LABEL_CLOSE_UP` when `close_up`.
    `seed_label_cuts.py` calls this function too.
    """
    out = derive.Derivatives("label")
    out.not_applicable = None
    if has_current_cut(conn, digest, "label", close_up):
        out.present += 1
        return out
    cut = label_cut_of(image, instances, close_up)
    if cut is None:
        log("no processing: SAM3 found no label")
        return out
    method, result, box = cut
    data = derive.png_bytes(result, icc_profile)
    derived = hashlib.sha256(data).hexdigest()
    folder = imagestore.folder_of(db_path, labdb.DERIVED_FOLDER)
    os.makedirs(folder, exist_ok=True)
    try:
        if imagestore.store_bytes(data, os.path.join(folder, derived + ".png"), derived):
            out.written += 1
    except (imagestore.StoreError, OSError) as exc:
        out.errors += 1
        log("error: %s" % exc)
        return out
    out.methods[method] += 1
    out.images.append((derived, labdb.DERIVED_FOLDER, "png") + result.size)
    settings = SETTINGS_LABEL_CLOSE_UP if close_up else SETTINGS_LABEL
    out.links.append((digest, method, settings, derived) + tuple(box))
    return out


def write_processed_rows(conn, derivatives):
    """Write a package or label processing result in the caller's transaction.

    A label result also writes or clears its deliberate-absence marker.
    """
    derive.write_rows(conn, derivatives)
    if derivatives.kind != "label":
        return
    reason = getattr(derivatives, "not_applicable", None)
    if reason:
        conn.execute(
            "INSERT INTO image_derivative_absence (source_sha256, kind, settings, reason) "
            "VALUES (?, 'label', ?, ?) ON CONFLICT (source_sha256, kind) DO UPDATE SET "
            "settings = excluded.settings, reason = excluded.reason",
            (derivatives.source_sha256, SETTINGS_LABEL_ABSENCE, reason))
    else:
        conn.execute("DELETE FROM image_derivative_absence WHERE source_sha256 = ? "
                     "AND kind = 'label'", (derivatives.source_sha256,))


def process_image(conn, db_path, digest, path, kind, segmenter, warnings, answer=None,
                  close_up=False):
    """Process one original for `kind`. `answer` is the SAM3 answer of the detection, or
    None. `close_up` tells that the original is a label close-up. Return a
    `derive.Derivatives`. Patch uploads also use this function to create their label cut
    of a full photo."""
    if kind == "full":
        return derive.derive_all(conn, db_path, {digest: path}, segmenter, warnings.append)
    absence = current_absence(conn, digest)
    if absence:
        out = derive.Derivatives("label")
        out.source_sha256 = digest
        out.not_applicable = absence
        return out
    if has_current_cut(conn, digest, "label", close_up):
        out = derive.Derivatives("label")
        out.source_sha256 = digest
        out.not_applicable = None
        out.present += 1
        return out
    try:
        image, icc_profile = derive.open_image(path)
    except OSError as exc:
        warnings.append("no processing: Pillow cannot read the image: %s" % exc)
        out = derive.Derivatives("label")
        out.source_sha256 = digest
        out.not_applicable = None
        out.unreadable += 1
        return out
    if answer is None:
        try:
            answer, _scale = segmenter.instances(image, DETECT_TEXTS)
        except derive.Sam3Unavailable as exc:
            warnings.append("no processing: %s" % exc)
            out = derive.Derivatives("label")
            out.source_sha256 = digest
            out.not_applicable = None
            out.unavailable += 1
            return out
    label_notes = len(warnings)
    out = label_derivatives(conn, db_path, digest, image, icc_profile, answer,
                            warnings.append, close_up)
    out.source_sha256 = digest
    if out.links or out.present or out.errors:
        return out
    try:
        package_answer, _scale = segmenter.instances(image, derive.SAM3_TEXTS)
    except derive.Sam3Unavailable as exc:
        warnings.append("no label applicability: %s" % exc)
        out.unavailable += 1
        return out
    out.not_applicable = label_absence_reason(package_answer)
    if out.not_applicable:
        del warnings[label_notes:]
    return out


def _check_slug(slug):
    if not isinstance(slug, str) or not slug:
        raise patches.PatchError(400, "the request holds no wine slug")


def _check_wine(conn, slug):
    if conn.execute("SELECT 1 FROM wine_catalog WHERE wine_slug = ?",
                    (slug,)).fetchone() is None:
        raise patches.PatchError(404, "no wine with the slug %s" % slug)


def _present_type(conn, slug, digest):
    row = conn.execute("SELECT image_type FROM wine_image WHERE wine_slug = ? AND "
                       "sha256 = ? AND image_type IN (%s)" % ", ".join("?" for _ in TYPES),
                       (slug, digest) + TYPES).fetchone()
    return row[0] if row else None


def _warn(derivatives, warnings, text=NO_PROCESSED_FILE):
    if (derivatives.unavailable or derivatives.unreadable or derivatives.errors
            or not (derivatives.links or derivatives.present
                    or getattr(derivatives, "not_applicable", None))):
        warnings.insert(0, text)


def _stored_path(conn, db_path, digest):
    folder, extension = conn.execute("SELECT folder, extension FROM image WHERE "
                                     "sha256 = ?", (digest,)).fetchone()
    return file_path(db_path, folder, digest, extension)


def _process_again(conn, db_path, slug, digest, image_type, segmenter, text):
    """Process a stored photo that has no current cut of its kind, and write the cut.
    Return the warnings."""
    warnings = []
    kind = KINDS[image_type]
    derivatives = process_image(conn, db_path, digest, _stored_path(conn, db_path, digest),
                                kind, segmenter or derive.Sam3Client(), warnings,
                                close_up=kind == "label")
    _warn(derivatives, warnings, text)
    conn.execute("BEGIN IMMEDIATE")
    try:
        write_processed_rows(conn, derivatives)
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    return warnings


def store_alternative(conn, db_path, slug, data, name=None, segmenter=None):
    """Store `data` as an alternative photo of the wine `slug`. Return a dict: `sha256`,
    `type`, `changed` (False when the wine has this photo already), and `warnings`.

    `conn` is a write connection with `isolation_level` None. `segmenter` is the SAM3
    client; None means `derive.Sam3Client()`.
    """
    _check_slug(slug)
    extension, width, height = patches.read_image(data)
    _check_wine(conn, slug)
    digest = hashlib.sha256(data).hexdigest()
    present = _present_type(conn, slug, digest)
    if present:
        warnings = [] if has_current_cut(conn, digest, KINDS[present],
                                         KINDS[present] == "label") else _process_again(
            conn, db_path, slug, digest, present, segmenter, NO_PROCESSED_FILE)
        return {"sha256": digest, "type": present, "changed": False, "warnings": warnings}
    row = conn.execute("SELECT folder, extension FROM image WHERE sha256 = ?",
                       (digest,)).fetchone()
    folder, stored_extension = row or (FOLDER, extension)
    path = file_path(db_path, folder, digest, stored_extension)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        imagestore.store_bytes(data, path, digest)
    except (imagestore.StoreError, OSError) as exc:
        raise patches.PatchError(500, "cannot store the photo: %s" % exc)

    client = segmenter or derive.Sam3Client()
    warnings = []
    image, _icc = derive.open_image(path)
    try:
        answer, scale = client.instances(image, DETECT_TEXTS)
        sent = (image.width * scale, image.height * scale)
        kind, face = detect(answer, *sent), side(answer, *sent)
    except derive.Sam3Unavailable as exc:
        answer, kind, face = None, "full", "front"
        warnings.append("no detection: %s; the type is full_front" % exc)
        client = _Down(str(exc))
    image_type = DETECTED[(kind, face)]
    derivatives = process_image(conn, db_path, digest, path, kind, client, warnings, answer,
                                close_up=kind == "label")
    _warn(derivatives, warnings)

    conn.execute("BEGIN IMMEDIATE")
    try:
        _check_wine(conn, slug)
        present = _present_type(conn, slug, digest)
        if present is None:
            insert_image(conn, digest, extension, width, height)
            conn.execute("INSERT INTO wine_image (wine_slug, image_type, sha256, "
                         "source_name, match_method) VALUES (?, ?, ?, ?, ?)",
                         (slug, image_type, digest, patches.source_name(name), MATCH_METHOD))
            write_processed_rows(conn, derivatives)
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    if present:
        return {"sha256": digest, "type": present, "changed": False, "warnings": []}
    return {"sha256": digest, "type": image_type, "changed": True, "warnings": warnings}


def set_type(conn, db_path, slug, digest, image_type, segmenter=None):
    """Give the alternative photo `digest` of the wine `slug` the type `image_type`.
    Return a dict: `type`, `changed`, and `warnings`. The photo is processed when it has no
    current cut of the kind of `image_type`; a change back to a kind reuses its cut."""
    _check_slug(slug)
    if image_type not in TYPES:
        raise patches.PatchError(400, "unknown type %r; use one of: %s"
                                 % (image_type, ", ".join(TYPES)))
    if not isinstance(digest, str) or not digest:
        raise patches.PatchError(400, "the request holds no sha256")
    _check_wine(conn, slug)
    old = _present_type(conn, slug, digest)
    if old is None:
        raise patches.PatchError(404, "the wine %s has no alternative photo %s"
                                 % (slug, digest))
    kind = KINDS[image_type]
    if old == image_type:
        warnings = [] if has_current_cut(conn, digest, kind,
                                         kind == "label") else _process_again(
            conn, db_path, slug, digest, image_type, segmenter, NO_NEW_CUT)
        return {"type": old, "changed": False, "warnings": warnings}
    warnings = []
    derivatives = derive.Derivatives(CUTS[kind])
    if not has_current_cut(conn, digest, kind, kind == "label"):
        derivatives = process_image(conn, db_path, digest,
                                    _stored_path(conn, db_path, digest), kind,
                                    segmenter or derive.Sam3Client(), warnings,
                                    close_up=kind == "label")
        _warn(derivatives, warnings, NO_NEW_CUT)
    conn.execute("BEGIN IMMEDIATE")
    try:
        if conn.execute("UPDATE wine_image SET image_type = ? WHERE wine_slug = ? AND "
                        "sha256 = ? AND image_type = ?",
                        (image_type, slug, digest, old)).rowcount != 1:
            raise patches.PatchError(409, "the photo %s of %s changed meanwhile"
                                     % (digest, slug))
        write_processed_rows(conn, derivatives)
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    return {"type": image_type, "changed": True, "warnings": warnings}


# A manual cut (plan 56): the polygon of the owner on the original, in the pixels after
# the EXIF orientation. The row of `image_derivative` has the method `seg` and the settings
# `MANUAL_HEAD` + the points as JSON, so the editor can load the polygon again.
MANUAL_HEAD = "%spolygon, edge blur %s px; points " % (derive.MANUAL_PREFIX, derive.EDGE_BLUR)
MIN_POINTS, MAX_POINTS = 3, 1000
MIN_CUT_SIDE = 2


def manual_points(settings):
    """Return the points of the manual cut of `settings`, or None for another cut."""
    if not isinstance(settings, str) or not settings.startswith(MANUAL_HEAD):
        return None
    try:
        return json.loads(settings[len(MANUAL_HEAD):])
    except ValueError:
        return None


def _number(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value))


def check_points(points, width, height):
    """Return `points` as integer pairs [x, y] inside an image of `width` × `height`
    pixels. Raise `patches.PatchError` 400 for a bad value."""
    if not isinstance(points, list) or not MIN_POINTS <= len(points) <= MAX_POINTS:
        raise patches.PatchError(400, "points MUST be a list of %d to %d points"
                                 % (MIN_POINTS, MAX_POINTS))
    out = []
    for point in points:
        if not isinstance(point, (list, tuple)) or len(point) != 2 \
                or not all(_number(value) for value in point):
            raise patches.PatchError(400, "each point MUST be a pair of numbers [x, y]")
        out.append([min(max(round(point[0]), 0), width),
                    min(max(round(point[1]), 0), height)])
    xs, ys = [point[0] for point in out], [point[1] for point in out]
    if max(xs) - min(xs) < MIN_CUT_SIDE or max(ys) - min(ys) < MIN_CUT_SIDE:
        raise patches.PatchError(400, "the polygon MUST be at least %d px wide and high"
                                 % MIN_CUT_SIDE)
    return out


def polygon_cut(image, points):
    """Return (the cut of `image` along the polygon `points` as an RGBA image, its box in
    the pixels of `image`). The edge gets the blur `derive.EDGE_BLUR`; the alpha of an
    RGBA original limits the cut, as in `label_cut`."""
    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).polygon([tuple(point) for point in points], fill=255)
    alpha = mask.filter(ImageFilter.GaussianBlur(derive.EDGE_BLUR))
    if image.mode == "RGBA":
        alpha = ImageChops.darker(alpha, image.getchannel("A"))
    box = alpha.point(lambda value: 255 if value > 0 else 0).getbbox()
    if box is None:
        raise patches.PatchError(400, "the polygon holds no visible pixel of the photo")
    out = image.convert("RGBA")
    out.putalpha(alpha)
    return out.crop(box), box


def _alternative_type(conn, slug, digest):
    """Return the type of the alternative photo `digest` of the wine `slug`. Raise
    `patches.PatchError` for a bad request or no such photo."""
    _check_slug(slug)
    if not isinstance(digest, str) or not digest:
        raise patches.PatchError(400, "the request holds no sha256")
    _check_wine(conn, slug)
    image_type = _present_type(conn, slug, digest)
    if image_type is None:
        raise patches.PatchError(404, "the wine %s has no alternative photo %s"
                                 % (slug, digest))
    return image_type


def store_manual_cut(conn, db_path, slug, digest, points):
    """Store the manual cut along `points` of the alternative photo `digest` of the wine
    `slug`, for the kind of its current type. The cut replaces the cut of that kind.
    Return a dict: `type`, `kind` (of `image_derivative`), `changed`, and `warnings`."""
    image_type = _alternative_type(conn, slug, digest)
    try:
        image, icc_profile = derive.open_image(_stored_path(conn, db_path, digest))
    except OSError as exc:
        raise patches.PatchError(500, "cannot read the photo: %s" % exc)
    points = check_points(points, image.width, image.height)
    result, box = polygon_cut(image, points)
    data = derive.png_bytes(result, icc_profile)
    derived = hashlib.sha256(data).hexdigest()
    folder = imagestore.folder_of(db_path, labdb.DERIVED_FOLDER)
    try:
        os.makedirs(folder, exist_ok=True)
        imagestore.store_bytes(data, os.path.join(folder, derived + ".png"), derived)
    except (imagestore.StoreError, OSError) as exc:
        raise patches.PatchError(500, "cannot store the cut: %s" % exc)
    cut_kind = CUTS[KINDS[image_type]]
    derivatives = derive.Derivatives(cut_kind)
    derivatives.source_sha256 = digest
    derivatives.not_applicable = None
    derivatives.images.append((derived, labdb.DERIVED_FOLDER, "png") + result.size)
    derivatives.links.append((digest, "seg", MANUAL_HEAD + json.dumps(
        points, separators=(",", ":")), derived) + tuple(box))
    conn.execute("BEGIN IMMEDIATE")
    try:
        if _present_type(conn, slug, digest) != image_type:
            raise patches.PatchError(409, "the photo %s of %s changed meanwhile"
                                     % (digest, slug))
        write_processed_rows(conn, derivatives)
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    return {"type": image_type, "kind": cut_kind, "changed": True, "warnings": []}


def reset_manual_cut(conn, db_path, slug, digest, segmenter=None):
    """Remove the manual cut of the kind of the current type of the alternative photo
    `digest` of the wine `slug`, and let SAM3 cut the photo again. Return a dict: `type`,
    `kind`, `changed` (False when the photo has no manual cut of that kind), and
    `warnings`."""
    image_type = _alternative_type(conn, slug, digest)
    cut_kind = CUTS[KINDS[image_type]]
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = conn.execute("SELECT settings FROM image_derivative WHERE source_sha256 = ? "
                           "AND kind = ?", (digest, cut_kind)).fetchone()
        manual = row is not None and derive.is_manual(row[0])
        if manual:
            conn.execute("DELETE FROM image_derivative WHERE source_sha256 = ? AND kind = ?",
                         (digest, cut_kind))
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    if not manual:
        return {"type": image_type, "kind": cut_kind, "changed": False, "warnings": []}
    warnings = _process_again(conn, db_path, slug, digest, image_type, segmenter,
                              NO_PROCESSED_FILE)
    return {"type": image_type, "kind": cut_kind, "changed": True, "warnings": warnings}


def remove_alternative(conn, slug, digest):
    """Delete the alternative photo `digest` of the wine `slug`. The file stays in the
    store. Return a dict: `sha256` and `type` of the removed row."""
    _check_slug(slug)
    if not isinstance(digest, str) or not digest:
        raise patches.PatchError(400, "the request holds no sha256")
    conn.execute("BEGIN IMMEDIATE")
    try:
        _check_wine(conn, slug)
        old = _present_type(conn, slug, digest)
        if old is None:
            raise patches.PatchError(404, "the wine %s has no alternative photo %s"
                                     % (slug, digest))
        conn.execute("DELETE FROM wine_image WHERE wine_slug = ? AND sha256 = ? AND "
                     "image_type = ?", (slug, digest, old))
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    return {"sha256": digest, "type": old}


def recut_alternative(conn, db_path, slug, digest, segmenter=None):
    """Segment the alternative photo `digest` of the wine `slug` again, with no read of
    the SAM3 cache (owner message of 2026-09-27T00:51:44+0300). Return a dict: `type`,
    `kind`, `changed` (True), and `warnings`.

    Two steps. First, SAM3 gets each request of the cut of the kind of the current type
    again, and the fresh answers replace the records of `model_cache`. Then the cut of
    that kind is removed, and `_process_again` cuts the photo from the fresh records. When
    SAM3 does not answer in the first step, nothing changes (HTTP 503). A photo with a
    manual cut of that kind is refused (HTTP 409): the manual cut stays. `segmenter` is
    the SAM3 client of both steps; None means `derive.Sam3Client(refresh=True)` for the
    first step and `derive.Sam3Client()` for the second.
    """
    image_type = _alternative_type(conn, slug, digest)
    kind = KINDS[image_type]
    cut_kind = CUTS[kind]
    row = conn.execute("SELECT settings FROM image_derivative WHERE source_sha256 = ? "
                       "AND kind = ?", (digest, cut_kind)).fetchone()
    if row is not None and derive.is_manual(row[0]):
        raise patches.PatchError(409, "the photo has a manual cut; remove the manual cut "
                                      "first")
    image, _icc_profile = derive.open_image(_stored_path(conn, db_path, digest))
    # The requests of `process_image`: a full photo with transparent pixels gets the
    # alpha rule and no SAM3 request; a label cut asks the label nouns, and the package
    # nouns when it finds no label.
    if kind == "full":
        texts = [] if derive.has_transparency(image) else [derive.SAM3_TEXTS]
    else:
        texts = [DETECT_TEXTS, derive.SAM3_TEXTS]
    fresh = segmenter or derive.Sam3Client(refresh=True)
    try:
        for text in texts:
            fresh.instances(image, text)
    except derive.Sam3Unavailable as exc:
        raise patches.PatchError(503, "SAM3 did not answer; the cut stays: %s" % exc)
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute("DELETE FROM image_derivative WHERE source_sha256 = ? AND kind = ?",
                     (digest, cut_kind))
        if kind == "label":
            conn.execute("DELETE FROM image_derivative_absence WHERE source_sha256 = ? "
                         "AND kind = 'label'", (digest,))
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    warnings = _process_again(conn, db_path, slug, digest, image_type,
                              segmenter or derive.Sam3Client(), NO_PROCESSED_FILE)
    return {"type": image_type, "kind": cut_kind, "changed": True, "warnings": warnings}
