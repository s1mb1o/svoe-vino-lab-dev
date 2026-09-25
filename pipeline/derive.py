"""Process an original image of the store: cut its border away, or segment the package.

`seed_images.py` and `seed_patched.py` call `derive_all` for each original that they
store or keep. Read `docs/plans/09_image-processing.md`.

Rules of the processing:
- An original with transparent pixels gets `crop`. A pixel is content when its alpha
  value is above `ALPHA_THRESHOLD`. The rule is the alpha rule of
  `svoe-wino-hackaton/scripts/build_cropped.py`.
- An original with no transparent pixels goes to SAM3. SAM3 finds the package: a
  bottle, a can, a packet, or a box. A box is the package of a bag-in-box; without the
  noun, SAM3 takes the bottle that is printed on the box. The main image holds one
  package, so the largest instance wins. The owner asked for the noun `box` on
  2026-09-25. The mask is smoothed and grown a little, and it becomes the alpha
  channel. The result gets `seg`.
- SAM3 answers and finds no package: the white rule of `build_cropped.py` cuts the
  border. A pixel is content when a colour channel is below `WHITE_LEVEL`. The result
  gets `crop`.
- SAM3 does not answer: the original gets no processed file. A later run asks again.
  After the first failure the run asks SAM3 no more.
- The alpha rule and the white rule remove each structure narrower than `OPEN_SIZE`
  pixels before they measure the box, as `build_cropped.py` does.
- The box has no margin. An image with no content keeps the whole canvas.
- The processed file is a PNG in `images/cropped/`. It keeps the pixels of the
  original. `image_derivative` links it to the original and holds the box in the pixels
  of the original, after its EXIF orientation.
- An original whose row of `image_derivative` holds one of the present settings is not
  processed again. A row with other settings is processed again and replaced.
"""
import base64
import collections
import hashlib
import io
import os
import random
import time

import numpy as np
import requests
from PIL import Image, ImageChops, ImageFilter, ImageOps

import imagestore
import labdb

# The rule of `build_cropped.py`.
ALPHA_THRESHOLD = 32
WHITE_LEVEL = 245
OPEN_SIZE = 5

# The SAM3 service of gx10 and the values of `build_labels.py`.
SAM3_ENDPOINT = "http://192.168.86.14:18081/upstream/sam3"
SAM3_TEXTS = "wine bottle, can, packet, box"
SAM3_THRESHOLD = 0.35
SAM3_MASK_THRESHOLD = 0.5
SAM3_MAX_SIDE = 1536
SAM3_TIMEOUT = 120
SAM3_RETRIES = 4
SAM3_RETRY_WAIT = 2.0
SAM3_MAX_RETRY_WAIT = 30.0

# The smoothing and the growth of the SAM3 mask. A Gaussian blur with a sigma of
# `MASK_BLUR` of the long side, and a cut at `MASK_KEEP` of 255, smooth the edge and
# grow the mask by about 0.67 sigma. A blur of `EDGE_BLUR` pixels makes the edge soft.
MASK_BLUR = 0.005
MASK_KEEP = 64
EDGE_BLUR = 1.0

SETTINGS_ALPHA = "alpha > %d, opening %d px" % (ALPHA_THRESHOLD, OPEN_SIZE)
# The white rule follows an answer of SAM3, so its settings name the SAM3 texts too. A
# change of the texts asks SAM3 again for such an image.
SETTINGS_WHITE = ("white < %d, opening %d px; SAM3 %r found no package"
                  % (WHITE_LEVEL, OPEN_SIZE, SAM3_TEXTS))
SETTINGS_SEG = ("SAM3 %r, threshold %s, mask %s, max side %d; mask blur %s of the long "
                "side, keep >= %d/255; edge blur %s px"
                % (SAM3_TEXTS, SAM3_THRESHOLD, SAM3_MASK_THRESHOLD, SAM3_MAX_SIDE,
                   MASK_BLUR, MASK_KEEP, EDGE_BLUR))
# The settings of a processed file that stays.
PRESENT_SETTINGS = frozenset({SETTINGS_ALPHA, SETTINGS_WHITE, SETTINGS_SEG})


class Sam3Unavailable(Exception):
    """The SAM3 service did not answer."""


class Sam3Client:
    """The client of `POST /segment_multi` of the SAM3 service."""

    def __init__(self, endpoint=SAM3_ENDPOINT):
        self.endpoint = endpoint.rstrip("/")
        self.session = requests.Session()

    def _post(self, data):
        # The service answers HTTP 429 when its queue is full, because it serves every
        # client of the host. The client waits and asks again, as `build_labels.py`.
        last = None
        for attempt in range(SAM3_RETRIES + 1):
            wait = 0.0
            try:
                response = self.session.post(
                    self.endpoint + "/segment_multi",
                    files={"image": ("image.png", data, "image/png")},
                    data={"texts": SAM3_TEXTS, "threshold": str(SAM3_THRESHOLD),
                          "mask_threshold": str(SAM3_MASK_THRESHOLD),
                          "return_masks": "true"},
                    timeout=SAM3_TIMEOUT)
                if response.status_code == 200:
                    return response.json()
                last = "HTTP %d: %s" % (response.status_code, response.text[:200])
                retryable = response.status_code == 429 or response.status_code >= 500
                try:
                    wait = float(response.headers.get("Retry-After") or 0)
                except ValueError:
                    wait = 0.0
            except (requests.RequestException, ValueError) as exc:
                last = str(exc)
                retryable = True
            if attempt >= SAM3_RETRIES or not retryable:
                break
            if wait <= 0:
                wait = min(SAM3_RETRY_WAIT * (2 ** attempt), SAM3_MAX_RETRY_WAIT)
            time.sleep(wait + random.uniform(0, 0.5))
        raise Sam3Unavailable("the SAM3 service at %s did not answer: %s"
                              % (self.endpoint, last))

    def segment(self, image):
        """Return the mask of the package as an `L` image of the size of `image`, or
        None when SAM3 finds no package. Raise `Sam3Unavailable`."""
        flat = image.convert("RGB")
        if image.mode == "RGBA":
            flat = Image.new("RGB", image.size, "white")
            flat.paste(image, mask=image.getchannel("A"))
        scale = min(1.0, SAM3_MAX_SIDE / float(max(flat.size)))
        if scale < 1.0:
            flat = flat.resize((max(1, round(flat.width * scale)),
                                max(1, round(flat.height * scale))), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        flat.save(buffer, "PNG")
        answer = self._post(buffer.getvalue())
        instances = [item for item in answer.get("instances") or []
                     if item.get("mask_png_b64")]
        if not instances:
            return None
        best = max(instances, key=lambda item: (int(item.get("area") or 0),
                                                float(item.get("score") or 0)))
        with Image.open(io.BytesIO(base64.b64decode(best["mask_png_b64"]))) as mask:
            mask = mask.convert("L")
        if mask.size != image.size:
            mask = mask.resize(image.size, Image.Resampling.BILINEAR)
        return mask.point(lambda value: 255 if value >= 128 else 0)


class _Once:
    """A segmenter that stops after its first failure, so a run with no service does
    not wait for each image."""

    def __init__(self, segmenter):
        self.segmenter = segmenter
        self.failure = None

    def segment(self, image):
        if self.failure:
            raise Sam3Unavailable("no request: the service did not answer earlier in "
                                  "this run")
        try:
            return self.segmenter.segment(image)
        except Sam3Unavailable as exc:
            self.failure = str(exc)
            raise


def open_image(path):
    """Return the image at `path` after its EXIF orientation, as RGBA or RGB, and its
    ICC profile."""
    with Image.open(path) as opened:
        icc_profile = opened.info.get("icc_profile")
        image = ImageOps.exif_transpose(opened)
        alpha = image.mode in ("RGBA", "LA", "PA") or (
            image.mode == "P" and "transparency" in image.info)
        image = image.convert("RGBA" if alpha else "RGB")
    return image, icc_profile


def has_transparency(image):
    return image.mode == "RGBA" and image.getchannel("A").getextrema()[0] < 255


def erode(mask, radius):
    """Keep a pixel only when the whole square around it is content. A copy of
    `erode` of `build_cropped.py`: the area outside the image counts as empty."""
    height, width = mask.shape
    side = 2 * radius + 1
    padded = np.pad(mask, radius, mode="constant", constant_values=False)
    rows = padded[0:height, :].copy()
    for step in range(1, side):
        rows &= padded[step:step + height, :]
    out = rows[:, 0:width].copy()
    for step in range(1, side):
        out &= rows[:, step:step + width]
    return out


def bounding_box(mask):
    rows = np.flatnonzero(mask.any(axis=1))
    if rows.size == 0:
        return None
    cols = np.flatnonzero(mask.any(axis=0))
    return (int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1)


def package_box(mask):
    """Return the box of the mask after an opening of `OPEN_SIZE`, as
    `build_cropped.py` does. A mask with no content gives None."""
    plain = bounding_box(mask)
    if plain is None:
        return None
    radius = OPEN_SIZE // 2
    core = bounding_box(erode(mask, radius))
    if core is None:
        return plain
    height, width = mask.shape
    x1, y1, x2, y2 = core
    return (max(0, x1 - radius), max(0, y1 - radius),
            min(width, x2 + radius), min(height, y2 + radius))


def refine_mask(mask):
    """Smooth the edge of a 0/255 mask, grow it a little, and make the edge soft."""
    sigma = max(1.0, MASK_BLUR * max(mask.size))
    kept = mask.filter(ImageFilter.GaussianBlur(sigma)).point(
        lambda value: 255 if value >= MASK_KEEP else 0)
    return kept.filter(ImageFilter.GaussianBlur(EDGE_BLUR))


def derive_image(image, segmenter):
    """Return (method, settings, processed image, box) of one original.

    Raise `Sam3Unavailable` when the original needs SAM3 and the service does not
    answer.
    """
    full = (0, 0, image.width, image.height)
    if has_transparency(image):
        mask = np.asarray(image.getchannel("A")) > ALPHA_THRESHOLD
        box = package_box(mask) or full
        return "crop", SETTINGS_ALPHA, image.crop(box), box
    mask = segmenter.segment(image)
    if mask is None:
        rgb = np.asarray(image.convert("RGB"))
        box = package_box((rgb < WHITE_LEVEL).any(axis=2)) or full
        return "crop", SETTINGS_WHITE, image.crop(box), box
    alpha = refine_mask(mask)
    if image.mode == "RGBA":
        alpha = ImageChops.darker(alpha, image.getchannel("A"))
    box = alpha.point(lambda value: 255 if value > 0 else 0).getbbox() or full
    out = image.convert("RGBA")
    out.putalpha(alpha)
    return "seg", SETTINGS_SEG, out.crop(box), box


def png_bytes(image, icc_profile):
    buffer = io.BytesIO()
    if icc_profile:
        image.save(buffer, "PNG", icc_profile=icc_profile)
    else:
        image.save(buffer, "PNG")
    return buffer.getvalue()


class Derivatives:
    """The processed files of one run. The importer writes the rows in its
    transaction with `write_rows`."""

    def __init__(self):
        self.images = []                        # rows of `image` for processed files
        self.links = []                         # rows of `image_derivative`
        self.methods = collections.Counter()    # processed originals by method
        self.present = 0      # originals with a processed file of the present settings
        self.unavailable = 0  # originals that need SAM3 while the service is down
        self.unreadable = 0   # originals that Pillow cannot read
        self.errors = 0       # store errors of processed files
        self.written = 0      # processed files written to the store

    def processed(self):
        return sum(self.methods.values())


def derive_all(conn, db_path, originals, segmenter, log=print):
    """Process each original that needs it. Return a `Derivatives`.

    `originals` maps the sha256 of an original to its path in the store.
    """
    done = dict(conn.execute("SELECT source_sha256, settings FROM image_derivative"))
    folder = imagestore.folder_of(db_path, labdb.DERIVED_FOLDER)
    os.makedirs(folder, exist_ok=True)
    segmenter = _Once(segmenter)
    out = Derivatives()
    for digest, path in originals.items():
        if done.get(digest) in PRESENT_SETTINGS:
            out.present += 1
            continue
        try:
            image, icc_profile = open_image(path)
            method, settings, result, box = derive_image(image, segmenter)
        except Sam3Unavailable as exc:
            out.unavailable += 1
            log("no processing: %s: %s" % (path, exc))
            continue
        except OSError as exc:
            out.unreadable += 1
            log("no processing: %s: Pillow cannot read the image: %s" % (path, exc))
            continue
        data = png_bytes(result, icc_profile)
        derived = hashlib.sha256(data).hexdigest()
        try:
            if imagestore.store_bytes(data, os.path.join(folder, derived + ".png"),
                                      derived):
                out.written += 1
        except (imagestore.StoreError, OSError) as exc:
            out.errors += 1
            log("error: %s: %s" % (path, exc))
            continue
        out.methods[method] += 1
        out.images.append((derived, labdb.DERIVED_FOLDER, "png") + result.size)
        out.links.append((digest, method, settings, derived) + tuple(box))
    return out


def write_rows(conn, derivatives):
    """Write the rows of `derivatives`. The caller holds the transaction. The
    original of each link MUST have its row in `image` already."""
    conn.executemany(
        "INSERT INTO image (sha256, folder, extension, width, height) "
        "VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING", derivatives.images)
    conn.executemany(
        "INSERT INTO image_derivative (source_sha256, method, settings, sha256, box_left, "
        "box_top, box_right, box_bottom) VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT (source_sha256) DO UPDATE SET method = excluded.method, "
        "settings = excluded.settings, sha256 = excluded.sha256, "
        "box_left = excluded.box_left, box_top = excluded.box_top, "
        "box_right = excluded.box_right, box_bottom = excluded.box_bottom",
        derivatives.links)
