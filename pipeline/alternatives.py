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
  (`label_instance`). `image_derivative` holds one cut for each original and kind
  (`package`, `label`), so each row shows the cut of its own kind, and a change back to
  a kind reuses its cut.
- A request processes a photo whenever its row has no current cut of its kind: an upload,
  the same photo again, and each type change. So a photo stored while SAM3 was down gets
  its cut on the next request.
- The same photo on the same wine a second time changes no row.
- `remove_alternative` deletes the row alone. The file stays in the store.
- SAM3 runs before the write transaction, so a slow SAM3 does not hold the write lock.

The store path and the `INSERT INTO image` are each in one function of `patches.py`:
`file_path` and `insert_image`. `lab_server.alternative_images` builds the URLs.
"""
import base64
import hashlib
import io
import os

from PIL import Image, ImageChops

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

SETTINGS_LABEL = (
    "SAM3 %r, threshold %s, mask %s, max side %d; the largest label that is not the "
    "package (build_labels.py), else the largest label; mask blur %s of the long side, "
    "keep >= %d/255; edge blur %s px"
    % (DETECT_TEXTS, derive.SAM3_THRESHOLD, derive.SAM3_MASK_THRESHOLD,
       derive.SAM3_MAX_SIDE, derive.MASK_BLUR, derive.MASK_KEEP, derive.EDGE_BLUR))

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


def has_current_cut(conn, digest, kind):
    """Tell whether the original `digest` has a cut of `kind` (`full` or `label`) with
    the present settings."""
    row = conn.execute("SELECT settings FROM image_derivative WHERE source_sha256 = ? "
                       "AND kind = ?", (digest, CUTS[kind])).fetchone()
    if row is None:
        return False
    return row[0] == SETTINGS_LABEL if kind == "label" else row[0] in derive.PRESENT_SETTINGS


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


def label_instance(instances):
    """Return the label instance of a close-up, or None.

    The rule of `build_labels.py`: of two instances of one region the larger one stays;
    a label that is the bottle, or that holds the bottle, is the package and not a label;
    the largest mask wins, not the best score. In a close-up the label can fill the frame
    and equal the bottle box; when the rule leaves no label, the largest label counts.
    """
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
    candidates = kept or unique
    return min(candidates, key=order) if candidates else None


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


def label_derivatives(conn, db_path, digest, image, icc_profile, instances, log):
    """Return the `derive.Derivatives` (kind `label`) of the label cut of one original.

    `instances` is the SAM3 answer of `DETECT_TEXTS` with masks. A present label cut with
    `SETTINGS_LABEL` is kept. `seed_label_cuts.py` calls this function too.
    """
    out = derive.Derivatives("label")
    if has_current_cut(conn, digest, "label"):
        out.present += 1
        return out
    instance = label_instance(instances)
    if instance is None:
        log("no processing: SAM3 found no label")
        return out
    result, box = label_cut(image, instance)
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
    out.methods["seg"] += 1
    out.images.append((derived, labdb.DERIVED_FOLDER, "png") + result.size)
    out.links.append((digest, "seg", SETTINGS_LABEL, derived) + tuple(box))
    return out


def _process(conn, db_path, digest, path, kind, segmenter, warnings, answer=None):
    """Process one original for `kind`. `answer` is the SAM3 answer of the detection, or
    None. Return a `derive.Derivatives`."""
    if kind == "full":
        return derive.derive_all(conn, db_path, {digest: path}, segmenter, warnings.append)
    try:
        image, icc_profile = derive.open_image(path)
    except OSError as exc:
        warnings.append("no processing: Pillow cannot read the image: %s" % exc)
        out = derive.Derivatives("label")
        out.unreadable += 1
        return out
    if answer is None:
        try:
            answer, _scale = segmenter.instances(image, DETECT_TEXTS)
        except derive.Sam3Unavailable as exc:
            warnings.append("no processing: %s" % exc)
            out = derive.Derivatives("label")
            out.unavailable += 1
            return out
    return label_derivatives(conn, db_path, digest, image, icc_profile, answer,
                             warnings.append)


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
            or not (derivatives.links or derivatives.present)):
        warnings.insert(0, text)


def _stored_path(conn, db_path, digest):
    folder, extension = conn.execute("SELECT folder, extension FROM image WHERE "
                                     "sha256 = ?", (digest,)).fetchone()
    return file_path(db_path, folder, digest, extension)


def _process_again(conn, db_path, slug, digest, image_type, segmenter, text):
    """Process a stored photo that has no current cut of its kind, and write the cut.
    Return the warnings."""
    warnings = []
    derivatives = _process(conn, db_path, digest, _stored_path(conn, db_path, digest),
                           KINDS[image_type], segmenter or derive.Sam3Client(), warnings)
    _warn(derivatives, warnings, text)
    conn.execute("BEGIN IMMEDIATE")
    try:
        derive.write_rows(conn, derivatives)
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
        warnings = [] if has_current_cut(conn, digest, KINDS[present]) else _process_again(
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
    derivatives = _process(conn, db_path, digest, path, kind, client, warnings, answer)
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
            derive.write_rows(conn, derivatives)
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
        warnings = [] if has_current_cut(conn, digest, kind) else _process_again(
            conn, db_path, slug, digest, image_type, segmenter, NO_NEW_CUT)
        return {"type": old, "changed": False, "warnings": warnings}
    warnings = []
    derivatives = derive.Derivatives(CUTS[kind])
    if not has_current_cut(conn, digest, kind):
        derivatives = _process(conn, db_path, digest, _stored_path(conn, db_path, digest),
                               kind, segmenter or derive.Sam3Client(), warnings)
        _warn(derivatives, warnings, NO_NEW_CUT)
    conn.execute("BEGIN IMMEDIATE")
    try:
        if conn.execute("UPDATE wine_image SET image_type = ? WHERE wine_slug = ? AND "
                        "sha256 = ? AND image_type = ?",
                        (image_type, slug, digest, old)).rowcount != 1:
            raise patches.PatchError(409, "the photo %s of %s changed meanwhile"
                                     % (digest, slug))
        derive.write_rows(conn, derivatives)
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    return {"type": image_type, "changed": True, "warnings": warnings}


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
