"""Make a new wine of the lab from one Drink Atlas product (plan 95, "New from Atlas").

The routes of `atlas_import_routes.py` and `lab_server.start_atlas_wine` call these
functions. The owner chose the design on 2026-09-30. Read
`docs/plans/95_new-from-atlas.md`.

Rules:
- The owner gives the URL of an Atlas product page, for example
  `http://127.0.0.1:8157/products/<uuid>`. The origin of the URL is the Atlas web UI.
  Its host MUST be a loopback host (`LOOPBACK_HOSTS`): the Atlas proxy answers a loopback
  host only, and the lab server fetches no other host.
- All calls go through the proxy of the Atlas web UI. The proxy adds the Core token and
  the coordinator token, so the lab keeps no Atlas token. A POST needs the headers
  `Origin` and `X-Atlas-Action: enrichment`.
- `advance` does the three buttons of the Atlas product page, in the order of a careful
  person: stage 1 is `Удалить белые поля и полосы` and `Извлечь изображения из PDF`;
  stage 2, when each stage 1 task is terminal, is `Распознать штрихкоды` on the
  product as it is then. A step with a task of its profile and media gets no new request,
  also when the task failed. So a repeated `advance` sends no duplicate request. The
  button `load photos` of a card runs no Atlas step (owner message of
  2026-09-30T23:20): it takes the photos that Atlas has.
- `select_photos` groups similar photos by the rule of the Atlas button
  `Сгруппировать похожие` (`drink-atlas-webui/src/similar-images.ts`) and selects the
  best photo of each group by the Atlas quality rule (`compare_quality`).
- `download` reads the file of a photo as the Atlas download does
  (`drink-atlas-webui/src/asset-download.ts`, `downloadImage`).
- `insert_wine` writes the wine with no main photo, and its manual Atlas binding.
"""
import io
import json
import math
import re
import urllib.error
import urllib.parse
import urllib.request

import numpy as np
from PIL import Image, ImageOps

import atlas_bindings
import beverage_types
import manual_wines
import patches

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
PRODUCT_PATH = re.compile(r"^/products/([0-9A-Fa-f-]{36})/?$")
TIMEOUT = 60
# The profiles of the three buttons of the Atlas product page
# (`drink-atlas-webui/src/enrichment.tsx`) and their labels.
CLEAN = "image-auto-clean-v1"
PDF = "pdf-embedded-images-v7"
BARCODE = "image-barcode-v3"
LABELS = {CLEAN: "Удалить белые поля и полосы", PDF: "Извлечь изображения из PDF",
          BARCODE: "Распознать штрихкоды"}
# The task states that end a task. `input_unavailable` is the answer of a request that
# Core could not give an input for; the request has no task.
TERMINAL = frozenset({"succeeded", "failed", "stale", "blocked", "input_unavailable"})
PDF_TYPE = "application/pdf"
# The wine colour of Atlas -> the broad colour of the lab (`wine_catalog.category`).
CATEGORIES = {"white": "Белое", "red": "Красное", "rose": "Розовое",
              "orange": "Оранжевое"}
# The rule of `display_names._base_style` of Drink Atlas Core: a code that starts with
# 44 or 45 is a sparkling wine, a code that starts with 40 to 43 is a wine.
SPARKLING_CODES = ("44", "45")
WINE_CODES = ("40", "41", "42", "43")
# The value of `csv_photo_name` of a wine with no main photo.
PHOTO_NAME = "atlas-%s"
# The Pillow format of a file that the store takes as it is -> its extension.
FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}

# The similar-photo rule of `similar-images.ts` and `imageFingerprint` of `main.tsx`.
SIZE = 32
DISTANCE = 0.07
ASPECT_DELTA = 0.04
CROP_DISTANCE = DISTANCE
DETAIL_CROP_DISTANCE = 0.15
DETAIL_CROP_MAX_FRACTION = 0.8
MIN_CROP_FRACTION = 0.625
WHITE_MIN = 245
EDGE_COVERAGE = 0.995


class AtlasError(Exception):
    """An Atlas import step is not possible. `code` is the HTTP status of the answer."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def parse_url(url):
    """Return (the origin, the product UUID, `include_hidden`) of an Atlas product URL.
    Raise `AtlasError` 400."""
    if not isinstance(url, str) or not url.strip():
        raise AtlasError(400, "the request holds no Atlas product URL")
    parts = urllib.parse.urlsplit(url.strip())
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise AtlasError(400, "the Atlas URL MUST start with http:// or https://")
    if parts.hostname.lower() not in LOOPBACK_HOSTS:
        raise AtlasError(400, "the Atlas URL MUST name a loopback host (%s)"
                         % ", ".join(sorted(LOOPBACK_HOSTS)))
    match = PRODUCT_PATH.match(parts.path)
    if not match:
        raise AtlasError(400, "the Atlas URL MUST have the form "
                              "<origin>/products/<uuid>")
    try:
        product = atlas_bindings.clean_uuid(match.group(1))
    except atlas_bindings.BindingError as exc:
        raise AtlasError(400, str(exc))
    query = urllib.parse.parse_qs(parts.query)
    hidden = (query.get("include_hidden") or [""])[0] == "true"
    return "%s://%s" % (parts.scheme, parts.netloc), product, hidden


class AtlasClient:
    """The HTTP client of the proxy of the Atlas web UI at `origin`."""

    def __init__(self, origin, include_hidden=False, timeout=TIMEOUT):
        self.origin = origin
        self.include_hidden = include_hidden
        self.timeout = timeout

    def _hidden(self, path):
        if not self.include_hidden:
            return path
        return path + ("&" if "?" in path else "?") + "include_hidden=true"

    def request(self, method, path, body=None):
        """Return (the body bytes, the content type) of one request. Raise `AtlasError`
        502."""
        headers = {"Accept": "*/*"}
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers.update({"Content-Type": "application/json", "Origin": self.origin,
                            "X-Atlas-Action": "enrichment"})
        request = urllib.request.Request(self.origin + path, data=data, headers=headers,
                                         method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.read(), response.headers.get("Content-Type") or ""
        except urllib.error.HTTPError as exc:
            detail = exc.read(2000).decode("utf-8", "replace").strip()
            raise AtlasError(502, "Drink Atlas answered HTTP %d for %s %s: %s"
                             % (exc.code, method, path, detail or exc.reason))
        except (urllib.error.URLError, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            raise AtlasError(502, "cannot reach Drink Atlas at %s: %s"
                             % (self.origin, reason))

    def json(self, method, path, body=None):
        data, _ctype = self.request(method, path, body)
        try:
            return json.loads(data)
        except ValueError:
            raise AtlasError(502, "Drink Atlas sent no JSON for %s %s" % (method, path))

    def product(self, product_uuid):
        product = self.json("GET", self._hidden("/api/v1/products/%s" % product_uuid))
        if not isinstance(product, dict):
            raise AtlasError(502, "Drink Atlas sent no product %s" % product_uuid)
        return product

    def tasks(self, product_uuid, media_id):
        query = urllib.parse.urlencode({"product_uuid": product_uuid,
                                        "media_id": media_id, "limit": 200})
        answer = self.json("GET", "/api/enrichment/tasks?" + query)
        return answer.get("items") or [] if isinstance(answer, dict) else []

    def submit(self, product_uuid, profile, media_id):
        answer = self.json("POST", "/api/enrichment/requests", {
            "product_uuids": [product_uuid], "profile": profile,
            "queue_class": "interactive", "params": {"media_id": media_id}})
        items = answer.get("items") if isinstance(answer, dict) else None
        if not items:
            raise AtlasError(502, "Drink Atlas accepted no request for %s" % profile)
        return items[0]

    def asset(self, media_id, part):
        """Return (the bytes, the content type) of `/api/v1/assets/<id>/<part>`."""
        return self.request("GET", self._hidden("/api/v1/assets/%d/%s" % (media_id, part)))

    def asset_url(self, media_id, part):
        return self.origin + self._hidden("/api/v1/assets/%d/%s" % (media_id, part))


def _int(value):
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def images(product):
    """Return the image assets of `product`, one for each `media_id`, in product order."""
    seen, out = set(), []
    for asset in product.get("assets") or []:
        media = _int(asset.get("media_id")) if isinstance(asset, dict) else None
        if media is None or media in seen or asset.get("kind") != "image":
            continue
        seen.add(media)
        out.append(asset)
    return out


def _derived(asset):
    return _int((asset.get("crop") or {}).get("derived_media_id"))


def stage_one(product):
    """Return the (profile, media id) steps of the clean and the PDF buttons."""
    steps = [(CLEAN, asset["media_id"]) for asset in images(product)
             if not asset.get("pdf_sources")]
    seen = set()
    for asset in product.get("assets") or []:
        media = _int(asset.get("media_id")) if isinstance(asset, dict) else None
        if media is not None and media not in seen and asset.get("content_type") == PDF_TYPE:
            seen.add(media)
            steps.append((PDF, media))
    return steps


def stage_two(product):
    """Return the (profile, media id) steps of the barcode button: each image and each
    published crop."""
    ids = []
    for asset in images(product):
        for media in (asset["media_id"], _derived(asset)):
            if media is not None and media not in ids:
                ids.append(media)
    return [(BARCODE, media) for media in ids]


def _run_steps(client, product_uuid, steps):
    out = []
    for profile, media in steps:
        tasks = [task for task in client.tasks(product_uuid, media)
                 if isinstance(task, dict) and task.get("profile") == profile]
        task = max(tasks, key=lambda item: item.get("id") or 0) if tasks else None
        submitted = task is None
        if submitted:
            task = client.submit(product_uuid, profile, media)
        out.append({"profile": profile, "label": LABELS[profile], "media_id": media,
                    "task_id": task.get("task_id", task.get("id")),
                    "status": task.get("status") or "unknown",
                    "queue_position": task.get("queue_position"),
                    "submitted": submitted})
    return out


def _terminal(steps):
    return all(step["status"] in TERMINAL for step in steps)


def advance(client, product_uuid):
    """Send the missing requests of the three Atlas steps. Return the state: `stage`
    (`clean`, `barcode`, or `done`), `steps`, `product`, and `prefill`."""
    product = client.product(product_uuid)
    steps = _run_steps(client, product_uuid, stage_one(product))
    stage = "clean"
    if _terminal(steps):
        # Stage 2 covers the new PDF images and the new published crops.
        product = client.product(product_uuid)
        steps += _run_steps(client, product_uuid, stage_two(product))
        stage = "done" if _terminal(steps) else "barcode"
    return {"product_uuid": product_uuid, "stage": stage, "done": stage == "done",
            "steps": steps, "product": summary(product), "prefill": prefill(product)}


def summary(product):
    """Return the fields of `product` that the dialog shows."""
    return {"display_name": product.get("display_name") or product.get("name"),
            "image_count": len(images(product))}


def _text(value):
    return value.strip() if isinstance(value, str) else ""


def beverage_type(code):
    """Return the lab category code ("4", "44") of an Atlas `beverage_type_code`, or ""."""
    code = _text(code)
    if code.startswith(SPARKLING_CODES):
        return "44"
    if code.startswith(WINE_CODES):
        return "4"
    return ""


def prefill(product):
    """Return the values of the form `Add wine` from `product`. An unknown value is ""."""
    producers = [_text(item.get("name")) for item in product.get("producers") or []
                 if isinstance(item, dict)]
    grapes = product.get("grapes_and_harvest")
    if isinstance(grapes, list):
        grapes = ", ".join(_text(item) for item in grapes if _text(item))
    profile = product.get("wine_profile") or {}
    return {"name": _text(product.get("display_name")) or _text(product.get("name")),
            "producer": next((name for name in producers if name), "")
            or _text(product.get("brand")),
            "beverage_type_code": beverage_type(product.get("beverage_type_code")),
            "category": CATEGORIES.get(profile.get("wine_color_code"), ""),
            "color": "",
            "region": _text(product.get("origin_region")),
            "grapes": _text(grapes),
            "description": _text(product.get("description"))}


# --- The similar photos ---------------------------------------------------------------

def _positive(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) \
        and math.isfinite(value) and value > 0 else 0


def pixel_count(asset):
    """Return the pixel count of the photo that Atlas shows: the crop, or the original."""
    crop = asset.get("crop") or {}
    width, height = _positive(crop.get("width")), _positive(crop.get("height"))
    if width and height:
        return width * height
    return _positive(asset.get("width_px")) * _positive(asset.get("height_px"))


def quality_key(asset):
    """The sort key of `compareAssetQuality`: the most pixels, then the most bytes, then
    the lowest media id."""
    return (-pixel_count(asset), -_positive(asset.get("content_length")), asset["media_id"])


def outer_white_bounds(rgb):
    """Return (x, y, width, height) of `rgb` with no outer white fields, as
    `detectOuterWhiteBounds`. `rgb` is an array of the shape (height, width, 3)."""
    height, width = rgb.shape[:2]
    white = np.all(rgb >= WHITE_MIN, axis=2)
    rows, columns = white.sum(axis=1), white.sum(axis=0)
    row_minimum = math.ceil(width * EDGE_COVERAGE)
    column_minimum = math.ceil(height * EDGE_COVERAGE)
    top = bottom = left = right = 0
    while top < height and rows[top] >= row_minimum:
        top += 1
    while bottom < height - top and rows[height - 1 - bottom] >= row_minimum:
        bottom += 1
    while left < width and columns[left] >= column_minimum:
        left += 1
    while right < width - left and columns[width - 1 - right] >= column_minimum:
        right += 1
    cropped_width, cropped_height = width - left - right, height - top - bottom
    if cropped_width > 0 and cropped_height > 0:
        return left, top, cropped_width, cropped_height
    return 0, 0, width, height


def fingerprint(data, crop_outer_white):
    """Return the fingerprint of the thumbnail `data`: a dict with `aspect`, `pixels`
    (a uint8 array of the shape (SIZE, SIZE, 3)), and `original`. Raise OSError."""
    with Image.open(io.BytesIO(data)) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGBA")
    white = Image.new("RGBA", image.size, (255, 255, 255, 255))
    rgb = Image.alpha_composite(white, image).convert("RGB")
    x, y, width, height = (outer_white_bounds(np.asarray(rgb)) if crop_outer_white
                           else (0, 0, rgb.width, rgb.height))
    small = rgb.crop((x, y, x + width, y + height)).resize((SIZE, SIZE), Image.LANCZOS)
    return {"aspect": width / height, "pixels": np.asarray(small, dtype=np.uint8),
            "original": crop_outer_white}


def distance(a, b):
    """Return the fingerprint distance of `fingerprintDistance`, or infinity."""
    if a["pixels"].shape != b["pixels"].shape or not a["aspect"] or not b["aspect"]:
        return math.inf
    if abs(a["aspect"] - b["aspect"]) / max(a["aspect"], b["aspect"]) > ASPECT_DELTA:
        return math.inf
    difference = (a["pixels"].astype(np.float64) - b["pixels"]) / 255
    return float(np.sqrt(np.mean(difference * difference)))


def _round(value):
    # `Math.round` of JavaScript: a half goes up.
    return math.floor(value + 0.5)


def _samples(start, length):
    """Return the sample positions of `cropDistance` for each offset `start`: the low
    index, the high index, and the weight, each of the shape (len(start), SIZE)."""
    target = (np.arange(SIZE) + 0.5) * length / SIZE - 0.5
    position = np.clip(start[:, None] + target[None, :], start[:, None],
                       start[:, None] + length - 1)
    low = np.floor(position).astype(int)
    high = np.minimum(start[:, None] + length - 1, low + 1)
    return low, high, position - low


def crop_match(source, target):
    """Tell whether `target` matches a crop of `source`, as `directionalCropMatch`."""
    pixels = source["pixels"].astype(np.float64)
    goal = target["pixels"].astype(np.float64)
    minimum = math.ceil(SIZE * MIN_CROP_FRACTION)
    for height in range(minimum, SIZE + 1):
        width = _round(height * target["aspect"] / source["aspect"])
        if width < minimum or width > SIZE:
            continue
        limit = (DETAIL_CROP_DISTANCE if max(width, height) / SIZE <= DETAIL_CROP_MAX_FRACTION
                 else CROP_DISTANCE)
        y0, y1, wy = _samples(np.arange(SIZE - height + 1), height)
        x0, x1, wx = _samples(np.arange(SIZE - width + 1), width)
        # The axes: y offset, x offset, target row, target column, channel.
        r0, r1 = y0[:, None, :, None], y1[:, None, :, None]
        c0, c1 = x0[None, :, None, :], x1[None, :, None, :]
        fy, fx = wy[:, None, :, None, None], wx[None, :, None, :, None]
        top = pixels[r0, c0] * (1 - fx) + pixels[r0, c1] * fx
        bottom = pixels[r1, c0] * (1 - fx) + pixels[r1, c1] * fx
        difference = top * (1 - fy) + bottom * fy - goal
        distances = np.sqrt(np.mean(difference * difference, axis=(2, 3, 4))) / 255
        if (distances <= limit).any():
            return True
    return False


def similar(a, b):
    """Tell whether two fingerprints show the same photo, as `areSimilarFingerprints`."""
    if distance(a, b) <= DISTANCE:
        return True
    return a["original"] != b["original"] and (crop_match(a, b) or crop_match(b, a))


def group(assets, fingerprints):
    """Return the groups of similar photos, each group sorted by `quality_key`, in the
    order of the first photo of each group. A photo with no fingerprint is a group of
    its own."""
    parents = list(range(len(assets)))

    def find(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    for left in range(len(assets)):
        first = fingerprints.get(assets[left]["media_id"])
        if first is None:
            continue
        for right in range(left + 1, len(assets)):
            second = fingerprints.get(assets[right]["media_id"])
            if second is not None and similar(first, second):
                root_left, root_right = find(left), find(right)
                if root_left != root_right:
                    parents[root_right] = root_left
    components = {}
    for index, asset in enumerate(assets):
        components.setdefault(find(index), []).append(asset)
    return [sorted(items, key=quality_key) for items in components.values()]


def thumbnail_id(asset):
    """Return the media id of the thumbnail of the fingerprint (`assetImageUrl`)."""
    display = _int(asset.get("display_media_id"))
    if display is not None and display != asset["media_id"]:
        return display
    return _derived(asset) or asset["media_id"]


def select_photos(client, product):
    """Return the photos to import: the best photo of each group of similar photos. Each
    photo is a dict: `media_id`, `width`, `height`, `pixels`, `bytes`, `pdf`, `group`
    (the media ids of the group), and `thumbnail_url`."""
    assets = images(product)
    fingerprints, failed = {}, []
    for asset in assets:
        try:
            data, _ctype = client.asset(thumbnail_id(asset), "thumbnail")
            fingerprints[asset["media_id"]] = fingerprint(data, not asset.get("pdf_sources"))
        except (AtlasError, OSError, ValueError):
            failed.append(asset["media_id"])
    photos = []
    for items in group(assets, fingerprints):
        best = items[0]
        crop = best.get("crop") or {}
        width = _positive(crop.get("width")) or _positive(best.get("width_px"))
        height = _positive(crop.get("height")) or _positive(best.get("height_px"))
        photos.append({"media_id": best["media_id"], "width": width, "height": height,
                       "pixels": pixel_count(best),
                       "bytes": _positive(best.get("content_length")),
                       "pdf": bool(best.get("pdf_sources")),
                       "group": [item["media_id"] for item in items],
                       "thumbnail_url": client.asset_url(thumbnail_id(best), "thumbnail")})
    return {"photos": photos, "fingerprint_failures": failed, "product": summary(product)}


# --- The download and the write -------------------------------------------------------

REFLECTIONS = {"mirror_horizontal": Image.FLIP_LEFT_RIGHT,
               "mirror_vertical": Image.FLIP_TOP_BOTTOM,
               "transpose": Image.TRANSPOSE, "transverse": Image.TRANSVERSE}
# A clockwise turn -> the Pillow transpose (Pillow turns counter-clockwise).
ROTATIONS = {90: Image.ROTATE_270, 180: Image.ROTATE_180, 270: Image.ROTATE_90}


def _turn(data, rotation, reflection):
    """Return the PNG of `data` with the reflection, then the clockwise rotation, of
    `transformedCanvas`."""
    if reflection and reflection not in REFLECTIONS:
        raise AtlasError(502, "unknown Atlas reflection %r" % reflection)
    if rotation and rotation not in ROTATIONS:
        raise AtlasError(502, "unknown Atlas rotation %r" % rotation)
    with Image.open(io.BytesIO(data)) as opened:
        image = opened.convert("RGBA") if opened.mode in ("RGBA", "LA", "P") else \
            opened.convert("RGB")
    if reflection:
        image = image.transpose(REFLECTIONS[reflection])
    if rotation:
        image = image.transpose(ROTATIONS[rotation])
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def _stored_form(data):
    """Return (the bytes, the extension) of a file that the image store takes: a JPEG,
    PNG, or WebP stays as it is; another type becomes PNG."""
    try:
        with Image.open(io.BytesIO(data)) as opened:
            kind = opened.format
            if kind in FORMATS:
                return data, FORMATS[kind]
            image = opened.convert("RGBA") if "A" in opened.getbands() else \
                opened.convert("RGB")
    except OSError as exc:
        raise AtlasError(502, "Pillow cannot read the Atlas file: %s" % exc)
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue(), "png"


def download(client, asset):
    """Return (the bytes, the source name) of the photo `asset` as Atlas shows it: the
    published crop, the crop, or the oriented original."""
    media = asset["media_id"]
    crop = asset.get("crop") or None
    orientation = asset.get("orientation") or None
    if not (isinstance(orientation, dict) and orientation.get("state") == "confirmed"):
        orientation = None
    if crop:
        derived = _derived(asset)
        data, _ctype = (client.asset(derived, "content") if derived
                        else client.asset(media, "crop"))
    else:
        source = (_int((orientation or {}).get("derived_media_id"))
                  or _int(asset.get("display_media_id")) or media)
        data, _ctype = client.asset(source, "content")
    if orientation and (crop or not _int(orientation.get("derived_media_id"))):
        data = _turn(data, orientation.get("rotation_cw") or 0,
                     orientation.get("reflection") or None)
    data, extension = _stored_form(data)
    return data, "atlas-%d.%s" % (media, extension)


def read_media_ids(body, product):
    """Return the image assets of `product` that `body["media_ids"]` names, in that order.
    Raise `AtlasError` 400."""
    ids = body.get("media_ids")
    if not isinstance(ids, list) or not ids or not all(_int(item) is not None
                                                       for item in ids):
        raise AtlasError(400, "`media_ids` MUST be a list of one or more media ids")
    by_id = {asset["media_id"]: asset for asset in images(product)}
    unknown = [item for item in ids if item not in by_id]
    if unknown:
        raise AtlasError(400, "the product has no image %s"
                         % ", ".join(str(item) for item in unknown))
    return [by_id[item] for item in dict.fromkeys(ids)]


def check_wine(body):
    """Return (the slug, the text values, the category code) of the form values of
    `body`, by the rules of `manual_wines.py`. The main image is not required. Raise
    `manual_wines.WineError` 400."""
    return (manual_wines.check_slug(body.get("slug")), manual_wines.read_fields(body),
            manual_wines.read_beverage_type(body))


def insert_wine(conn, product_uuid, slug, values, beverage_type_code, draft=None):
    """Write the wine `slug` with no image, and its manual Atlas binding, in one write
    transaction. `conn` is a write connection with `isolation_level` None. Raise
    `manual_wines.WineError` 409 for a slug that the catalogue holds."""
    def check_new():
        if conn.execute("SELECT 1 FROM wine_catalog WHERE wine_slug = ?",
                        (slug,)).fetchone() is not None:
            raise manual_wines.WineError(409, "the database holds a wine with the slug %s "
                                              "already" % slug)

    import wine_draft

    if draft is not None:
        wine_draft.read_values(draft)
    check_new()
    conn.execute("BEGIN IMMEDIATE")
    try:
        check_new()
        if draft is not None:
            wine_draft.guard(conn, draft)
        fields = manual_wines.TEXT_FIELDS
        conn.execute("INSERT INTO wine_catalog (wine_slug, %s, csv_photo_name, state) "
                     "VALUES (?, %s, ?, 'Active')"
                     % (", ".join(fields), ", ".join("?" for _ in fields)),
                     [slug] + list(values) + [PHOTO_NAME % product_uuid])
        if beverage_type_code is not None:
            beverage_types.set_type(conn, slug, beverage_type_code)
        if draft is not None:
            wine_draft.store_tags(conn, slug, draft)
        atlas_bindings.add_manual(conn, slug, product_uuid)
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise


def check_size(data, name):
    """Raise `AtlasError` 413 for a file that the image store does not take."""
    if len(data) > patches.MAX_BYTES:
        raise AtlasError(413, "the Atlas file %s is larger than %d bytes"
                         % (name, patches.MAX_BYTES))
