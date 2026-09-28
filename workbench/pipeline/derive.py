"""Process an original image of the store: cut its border away, or segment the package.

`seed_images.py` and `seed_patched.py` call `derive_all` for each original that they
store or keep. Read `docs/plans/09_image-processing.md`.

Rules of the processing:
- An original with transparent pixels gets `crop`. A pixel is content when its alpha
  value is above `ALPHA_THRESHOLD`. The rule is the alpha rule of
  `svoe-wino-hackaton/scripts/build_cropped.py`.
- An original with no transparent pixels goes to SAM3. SAM3 finds the package: a
  bottle, a can, a packet, or a box. A box is the package of a bag-in-box; without the
  noun, SAM3 takes the bottle that is printed on the box. The owner asked for the noun
  `box` on 2026-09-25. A wine bottle wins over a larger box, can, or packet: a photo can
  show a gift box or a tube next to the bottle (owner message of
  2026-09-27T00:05:00+0300). A bottle that is printed on a packet or on a box is not
  the package, so that packet or box wins (`package_instance`). With no bottle, the
  largest instance wins. The mask is smoothed and grown a little, and it becomes the
  alpha channel. The result gets `seg`.
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
import threading
import time

import numpy as np
import requests
import yaml
from PIL import Image, ImageChops, ImageFilter, ImageOps

import imagestore
import labdb
import model_cache

# The rule of `build_cropped.py`.
ALPHA_THRESHOLD = 32
WHITE_LEVEL = 245
OPEN_SIZE = 5

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "config.yaml")


def configured_endpoint(default, path=CONFIG_PATH):
    """Return the key `sam3.endpoint` of `config.yaml`, or `default` when the file or the
    key is absent."""
    try:
        with open(path, encoding="utf-8") as fh:
            config = yaml.safe_load(fh) or {}
    except FileNotFoundError:
        return default
    endpoint = ((config.get("sam3") if isinstance(config, dict) else None) or {}).get("endpoint")
    if endpoint is None:
        return default
    if not isinstance(endpoint, str) or not endpoint.strip():
        raise ValueError("%s: `sam3.endpoint` MUST be a URL" % path)
    return endpoint.strip()


# The SAM3 service and the values of `build_labels.py`. The key `sam3.endpoint` of
# `config.yaml` names the service; without the key, the service of gx10 stays.
SAM3_ENDPOINT = configured_endpoint("http://192.168.86.14:18081/upstream/sam3")
# The served name of the gateway. It names the directory of the cache records.
SAM3_MODEL = "sam3"
SAM3_TEXTS ="wine bottle, can, packet, box"
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

# The choice of the package instance (owner message of 2026-09-27T00:05:00+0300). The
# largest bottle wins over each other noun. A bottle is printed on a packet when
# `PRINTED_COVER` of its box lies inside the box of the packet. A bottle is printed on a
# box when it lies inside the box in the same way and has less than `PRINTED_AREA` of
# the area of the box. A real bottle in an open gift box or in front of a crate has more.
# A replay of the cached SAM3 answers of 2026-09-27 gave these shares: printed bottles
# 0.005 to 0.21 (packets) and 0.015 to 0.06 (bag-in-box); real bottles in a box 0.13 to 0.36.
BOTTLE_LABEL = "wine bottle"
PRINTED_LABELS = ("packet", "box")
PRINTED_COVER = 0.9
PRINTED_AREA = 0.1

SETTINGS_ALPHA = "alpha > %d, opening %d px" % (ALPHA_THRESHOLD, OPEN_SIZE)
# The white rule follows an answer of SAM3, so its settings name the SAM3 texts too. A
# change of the texts asks SAM3 again for such an image.
SETTINGS_WHITE = ("white < %d, opening %d px; SAM3 %r found no package"
                  % (WHITE_LEVEL, OPEN_SIZE, SAM3_TEXTS))
SETTINGS_SEG = ("SAM3 %r, threshold %s, mask %s, max side %d; %r first, except a bottle "
                "printed on a packet or a box (cover %s, box area < %s); mask blur %s of "
                "the long side, keep >= %d/255; edge blur %s px"
                % (SAM3_TEXTS, SAM3_THRESHOLD, SAM3_MASK_THRESHOLD, SAM3_MAX_SIDE,
                   BOTTLE_LABEL, PRINTED_COVER, PRINTED_AREA, MASK_BLUR, MASK_KEEP,
                   EDGE_BLUR))
# The settings of a processed file that stays.
PRESENT_SETTINGS = frozenset({SETTINGS_ALPHA, SETTINGS_WHITE, SETTINGS_SEG})
# The settings of a manual cut start with this text (plan 56). A manual cut stays: no
# automatic run processes its original again.
MANUAL_PREFIX = "manual "


def is_manual(settings):
    """Tell whether `settings` of a row of `image_derivative` names a manual cut."""
    return isinstance(settings, str) and settings.startswith(MANUAL_PREFIX)


class Sam3Unavailable(Exception):
    """The SAM3 service did not answer."""


class Sam3Client:
    """The client of `POST /segment_multi` of the SAM3 service. With `refresh`, a call
    reads no record of `model_cache`: it asks SAM3 and stores the fresh answer in place of
    the old record (owner message of 2026-09-27T00:51:44+0300)."""

    def __init__(self, endpoint=SAM3_ENDPOINT, refresh=False):
        self.endpoint = endpoint.rstrip("/")
        self.refresh = refresh
        self.session = requests.Session()
        # Whether the last call of this thread read `model_cache` (plan 41).
        self._last = threading.local()

    def cached(self):
        """Tell whether the last call of this thread read its answer from `model_cache`.
        None means no call yet."""
        return getattr(self._last, "cached", None)

    def _post(self, data, texts=SAM3_TEXTS, return_masks=True):
        # A repeated request reads the answer of `model_cache`. Only an answer of HTTP
        # 200 is stored, so a failure asks SAM3 again. Read docs/plans/25_model-call-cache.md.
        form = {"texts": texts, "threshold": str(SAM3_THRESHOLD),
                "mask_threshold": str(SAM3_MASK_THRESHOLD),
                "return_masks": "true" if return_masks else "false"}
        params = {key: value for key, value in form.items() if key != "texts"}
        fields = model_cache.request_fields(self.endpoint + "/segment_multi", SAM3_MODEL,
                                            params, texts, [data])
        record = None if self.refresh else model_cache.lookup(fields)
        self._last.cached = record is not None
        if record is not None:
            return record["answer"]
        started = time.perf_counter()
        answer = self._send(data, form)
        model_cache.store(fields, answer, (time.perf_counter() - started) * 1000)
        return answer

    def _send(self, data, form):
        # The service answers HTTP 429 when its queue is full, because it serves every
        # client of the host. The client waits and asks again, as `build_labels.py`.
        last = None
        for attempt in range(SAM3_RETRIES + 1):
            wait = 0.0
            try:
                response = self.session.post(
                    self.endpoint + "/segment_multi",
                    files={"image": ("image.png", data, "image/png")},
                    data=form,
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

    def _sent_copy(self, image):
        """Return (the PNG bytes of the copy that goes to SAM3, the scale of the copy).
        The copy lies on white and has a long side of at most `SAM3_MAX_SIDE`."""
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
        return buffer.getvalue(), scale

    def instances(self, image, texts, masks=True):
        """Send `image` with the nouns `texts` to SAM3. Return (instances, scale).

        Each instance is the dict of the service as it comes: `label` (the noun that
        found it), `box`, `score`, `area`, and `mask_png_b64` when `masks`. The box and the
        mask are in the pixels of the sent copy: divide a box by `scale` for the pixels of
        `image`. Raise `Sam3Unavailable`.
        """
        data, scale = self._sent_copy(image)
        answer = self._post(data, texts, masks)
        return list(answer.get("instances") or []), scale

    def segment(self, image):
        """Return the mask of the package as an `L` image of the size of `image`, or
        None when SAM3 finds no package. Raise `Sam3Unavailable`."""
        data, _scale = self._sent_copy(image)
        answer = self._post(data)
        best = package_instance(answer.get("instances") or [])
        if best is None:
            return None
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


def _printed_on(bottle, item):
    """Tell whether the instance `bottle` is a picture that is printed on the packet or
    the box `item`. The boxes are in the pixels of the sent copy."""
    if item.get("label") not in PRINTED_LABELS:
        return False
    inner, outer = bottle.get("box"), item.get("box")
    if not inner or not outer or len(inner) != 4 or len(outer) != 4:
        return False
    width = min(inner[2], outer[2]) - max(inner[0], outer[0])
    height = min(inner[3], outer[3]) - max(inner[1], outer[1])
    own = (inner[2] - inner[0]) * (inner[3] - inner[1])
    if width <= 0 or height <= 0 or own <= 0 or width * height < PRINTED_COVER * own:
        return False
    return (item.get("label") == "packet"
            or int(bottle.get("area") or 0) < PRINTED_AREA * int(item.get("area") or 0))


def package_instance(instances):
    """Return the package instance of the SAM3 answer `instances`, or None when no
    instance has a mask. The largest wine bottle wins, unless it is printed on a packet
    or a box (`_printed_on`); then the largest of those wins. With no bottle, the largest
    instance wins. The score decides between two instances of one area."""
    size = lambda item: (int(item.get("area") or 0), float(item.get("score") or 0))
    instances = [item for item in instances if item.get("mask_png_b64")]
    if not instances:
        return None
    bottles = [item for item in instances if item.get("label") == BOTTLE_LABEL]
    if not bottles:
        return max(instances, key=size)
    bottle = max(bottles, key=size)
    hosts = [item for item in instances if _printed_on(bottle, item)]
    return max(hosts, key=size) if hosts else bottle


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
    transaction with `write_rows`. `kind` is the kind of cut of each link: `package`
    (this module) or `label` (`alternatives.label_derivatives`)."""

    def __init__(self, kind="package"):
        self.kind = kind
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
    done = dict(conn.execute("SELECT source_sha256, settings FROM image_derivative "
                             "WHERE kind = 'package'"))
    folder = imagestore.folder_of(db_path, labdb.DERIVED_FOLDER)
    os.makedirs(folder, exist_ok=True)
    segmenter = _Once(segmenter)
    out = Derivatives()
    for digest, path in originals.items():
        if done.get(digest) in PRESENT_SETTINGS or is_manual(done.get(digest)):
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
    """Write the rows of `derivatives`, each with the kind `derivatives.kind`. The caller
    holds the transaction. The original of each link MUST have its row in `image`
    already."""
    conn.executemany(
        "INSERT INTO image (sha256, folder, extension, width, height) "
        "VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING", derivatives.images)
    conn.executemany(
        "INSERT INTO image_derivative (source_sha256, method, settings, sha256, box_left, "
        "box_top, box_right, box_bottom, kind) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT (source_sha256, kind) DO UPDATE SET method = excluded.method, "
        "settings = excluded.settings, sha256 = excluded.sha256, "
        "box_left = excluded.box_left, box_top = excluded.box_top, "
        "box_right = excluded.box_right, box_bottom = excluded.box_bottom",
        [link + (derivatives.kind,) for link in derivatives.links])
