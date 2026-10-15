"""The steps of one photo of a run, for the step popup of `/runs` (plan 41).

`GET /api/run-steps?id=<run>&query=<query id>` answers the rounds and the steps of one
row of `results.jsonl`. The page draws them as the step view of `drink-atlas-recognize`.

- An embedding run (`backend.kind: embedding`): the photo, the SAM3 cuts, the steps of
  each view, the embedding, the search in the space of each view, the score, and the VLM
  evidence re-rank when it acts. A row of a run after plan 41 holds the key `trace`
  (`embedding_run.Trace`): the time and the result of each step. The images are made
  again from the SAM3 answers of
  `data/cache/models/sam3/` with the code of the run, and each model input is checked against
  the sha256 of the trace. An older row has no time.
- A matcher run (`svoe-vino-matcher`): the photo, the model inputs of the matcher, the
  request, and the re-rank steps of its `explain` records, with the order before each.
- Another run: the photo and the answer of the backend.

The module reads files and the lab database. It writes nothing and sends no request.
"""
import base64
import hashlib
import io
import os
import re
import sqlite3
import sys
import threading
import urllib.parse
from collections import OrderedDict
from contextlib import closing
from copy import deepcopy
from pathlib import Path

import alternatives
import variant_attributes
import build_embeddings
import bottle_orientation
import derive
import embedding_run
import embeddings
import labdb
import main_scene
import model_cache
import run_files
from checked_read_cache import CheckedReadCache, ReadFlights, signature

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MATCHER_ROOT = os.path.join(os.path.dirname(os.path.dirname(ROOT)), "svoe-vino-matcher")
# The gx10 gateway of the embedding and SAM3 calls (Admin/GPU_SERVERS.md).
GATEWAY_HOST = "192.168.86.14:18081"
MATCHER_PATH = re.compile(r"/v1/pipelines/([^/]+)/predict$")
# The long side of a cut image in the popup. A model input keeps its size.
CUT_SIDE = 1024
THUMBNAILS = CheckedReadCache(max_entries=128, max_bytes=32 * 1024 * 1024)
INDEX_STATES = CheckedReadCache(max_entries=8, max_bytes=32 * 1024 * 1024)
NO_TIME = "The run recorded no step time. A run after plan 41 records it."
NO_SPACE_LIST = ("The run kept no top list of this space. The list shows the candidates of "
                 "the answer by their cosine in this space.")

PHOTO_NOTE = "the photo as it came"
EMBEDDING_ROUNDS = (PHOTO_NOTE,
                    "the model inputs: the SAM3 cuts and the steps of each view",
                    "the embedding and the search: each view searches its own space",
                    "the VLM supplies evidence scores; code decides the final order")
MATCHER_ROUNDS = (PHOTO_NOTE,
                  "the model inputs of the matcher, made again with the matcher code",
                  "the matcher request",
                  "the re-rank inside the matcher request")
REQUEST_ROUNDS = (PHOTO_NOTE, "the request to the backend")


class StepError(Exception):
    """The run or the query does not exist. `code` is the HTTP code."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def run_kind(spec):
    """Return the kind of a run from the key `backend` of its `run.json`."""
    if spec.get("kind") in ("embedding", "remote"):
        return spec["kind"]
    url = str(spec.get("url") or "")
    if MATCHER_PATH.search(urllib.parse.urlsplit(url).path):
        return "matcher"
    return "request" if url else "none"


def service_of(url):
    """Return the service word of the meta line of a step that calls `url`."""
    if not url:
        return "local"
    parts = urllib.parse.urlsplit(url)
    if parts.netloc == GATEWAY_HOST:
        return "gateway"
    if MATCHER_PATH.search(parts.path):
        return "matcher"
    return parts.netloc or url


def png_uri(image, side):
    """Return the PNG data URI of a copy of `image` with a long side of `side` at most."""
    if max(image.size) > side:
        image = image.copy()
        image.thumbnail((side, side))
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return build_embeddings.data_uri(buffer.getvalue())


def step(step_id, name, service="local", model=None, group=None, **keys):
    """Return a step of the answer with its defaults."""
    out = {"id": step_id, "name": name, "service": service, "model": model, "group": group,
           "start_ms": None, "ms": None, "state": "done", "cached": None, "error": None,
           "artifacts": [], "lists": [], "vlm": None, "settings": {}, "result": {},
           "notes": []}
    out.update(keys)
    return out


def timed(out, record):
    """Put the time, the cache flag, and the state of a trace record into the step `out`."""
    if not record:
        return out
    out["start_ms"], out["ms"] = record.get("start_ms"), record.get("ms")
    out["cached"] = record.get("cached")
    if record.get("error"):
        out["state"], out["error"] = "failed", record["error"]
    elif record.get("skipped"):
        out["state"] = "skipped"
        out["notes"].append(record["skipped"])
    if isinstance(record.get("out"), dict):
        out["result"] = record["out"]
    return out


QUALITY_REASONS = {
    "no_label": "No label was detected.",
    "empty_label_mask": "The label mask is empty.",
    "main_label_outside_crop": "The main label is outside the crop.",
    "empty_content": "The crop contains no nonwhite content.",
    "weak_detection": "Label detector confidence is too low.",
    "insufficient_native_detail": "The label is too small in the source photo.",
    "insufficient_input_detail": "The label is too small in the model input.",
    "unrelated_content": "The crop contains too much glass or other unrelated content.",
    "insufficient_sharpness": "The label has insufficient sharpness.",
    "label_on_other_package": "The label does not overlap the selected package enough.",
    "invalid_label_data": "The cached label data cannot be measured.",
}


def quality_step(record, options):
    """Show the recorded gate outcome and checks without opening the raw JSON."""
    part = step("label-quality", "Label crop quality")
    timed(part, record)
    part["settings"] = {"label_gate": options}
    result = part["result"]
    verdict = ("Accepted" if result.get("passed") else "Rejected") if "passed" in result else "Not recorded"
    part["name"] += " · " + verdict
    signals, options = result.get("signals") or {}, options or {}
    purity = signals.get("purity")
    if purity is not None:
        part["group"] = "label content %.1f%%" % (100 * purity)
    part["notes"].append("Crop quality: %s." % verdict.lower())

    def check(title, value, threshold, render):
        if value is None:
            part["notes"].append("%s: not measured." % title)
            return
        if threshold is None:
            part["notes"].append("%s: %s. Threshold not recorded." % (title, render(value)))
            return
        tested = min(value) if isinstance(value, (list, tuple)) else value
        status = "PASS" if tested >= threshold else "FAIL"
        limit = "%s px on each side" % threshold if isinstance(value, (list, tuple)) else render(threshold)
        part["notes"].append("%s · %s: %s (minimum %s)." % (status, title, render(value), limit))

    def percent(value):
        return "%.1f%%" % (value * 100)

    def size(value):
        return "%.1f × %.1f px" % tuple(value)

    check("Label content", purity, options.get("min_purity"), percent)
    check("Detector confidence", signals.get("detector_score"), options.get("min_detector_score"),
          lambda value: "%.4f" % value)
    check("Native label size", signals.get("native_label_size"), options.get("min_native_side"), size)
    check("Input label size", signals.get("input_label_size"), options.get("min_input_side"), size)
    check("Sharpness", signals.get("sharpness"), options.get("min_sharpness"),
          lambda value: "%.1f" % value)
    check("Package overlap", signals.get("package_overlap"), options.get("min_package_overlap"), percent)
    if signals.get("source_frame_edges"):
        part["notes"].append("The label touches %s source-frame edges. This flag alone does not reject it."
                             % signals["source_frame_edges"])
    for reason in result.get("reasons") or []:
        message = ("Label detection is unavailable." if reason.startswith("label_unavailable:")
                   else QUALITY_REASONS.get(reason, reason))
        part["notes"].append("Rejected: " + message)
    if result.get("passed"):
        part["notes"].append("The crop can use label matching. Similarity and margin are checked next.")
    elif "passed" in result:
        part["notes"].append("The label input is skipped. Matching falls back to the bottle space.")
    return part


class Photo:
    """The photo of one row: its URL, its file in the image store, and its opened image."""

    def __init__(self, conn, db_path, row):
        digest = str(row.get("image_sha256") or "")
        hit = conn.execute("SELECT folder, extension FROM image WHERE sha256 = ?",
                           (digest,)).fetchone() if digest else None
        self.extension = hit[1] if hit else None
        self.url = "/images/%s/%s.%s" % (hit[0], digest, hit[1]) if hit else None
        self.path = (os.path.join(labdb.image_dir(db_path, hit[0]),
                                  "%s.%s" % (digest, hit[1])) if hit else None)
        self.image, self.error, self.source_state = None, None, None
        self.artifact_sources = {}
        if not self.path:
            self.error = "the photo of this query is not in the lab image store"
            return
        try:
            self.source_state = signature(self.path)
            self.image, _icc = derive.open_image(self.path)
            if signature(self.path) != self.source_state:
                self.source_state = None
        except OSError as exc:
            self.error = "Pillow cannot read the photo: %s" % exc

    def head(self, row):
        return {"url": self.url, "path": row.get("image_path"),
                "width": self.image.width if self.image else None,
                "height": self.image.height if self.image else None}

    def artifact(self, caption, boxes=()):
        if not self.url:
            return None
        return {"src": self.url, "caption": caption,
                "width": self.image.width if self.image else None,
                "height": self.image.height if self.image else None,
                "boxes": [list(box) for box in boxes], "check": None}


class Lists:
    """The candidate cards of the steps: the catalogue image and the name of each slug."""

    def __init__(self, conn, row, card_images, card_images_for_slugs=None):
        self.row = row
        self.conn = conn
        self.card_images = card_images
        self.card_images_for_slugs = card_images_for_slugs
        self._cards = None
        self.slugs = set()

    def item(self, slug, rank, score, **keys):
        self.slugs.add(slug)
        item = {"slug": slug, "name": None, "rank": rank, "score": score, "image": None,
                "truth": slug in (self.row.get("truth") or ()),
                "forbidden": self.row.get("label") == "negative" and slug == self.row.get("slug"),
                "moved": None, "detail": None}
        item.update(keys)
        return item

    def finish(self, rounds):
        """Fill the image and the name of each list item of `rounds`."""
        if not self.slugs:
            return
        try:
            cards = (self.card_images_for_slugs(self.conn, slugs=self.slugs)
                     if self.card_images_for_slugs else self.card_images(self.conn))
            names = dict(self.conn.execute(
                "SELECT wine_slug, COALESCE(name_patched, name) FROM wine_catalog "
                "WHERE wine_slug IN (%s)"
                % ", ".join("?" for _ in self.slugs), sorted(self.slugs)))
        except sqlite3.Error:
            return  # the cards are a help; the slugs still stand
        for one in rounds:
            for part in one["steps"]:
                for group in part["lists"]:
                    for item in group["items"]:
                        card = cards.get(item["slug"]) or {}
                        fallback = card.get("_patch_image_url") or card.get("main_image_url")
                        item["image"] = item["image"] or fallback
                        if item.get("image_deferred"):
                            item["image_fallback"] = fallback
                        item["name"] = names.get(item["slug"])


def answer_list(lists, row, title, note=None, detail=None):
    """Return the list of the candidates of the row, in the order of the answer."""
    items = [lists.item(c.get("slug"), c.get("rank"), c.get("score"),
                        detail=detail(c) if detail else None)
             for c in row.get("candidates") or ()]
    return {"title": title, "note": note, "items": items}


def _cos(value):
    return "—" if value is None else "%.4f" % value


# ---- the embedding run ----

def _index_state(db_path, name):
    """Return current item hashes. Check the index file before each reuse."""
    try:
        directory = embeddings.entry_dir(db_path, name)
        path = os.path.join(directory, embeddings.INDEX)
        def load():
            index = embeddings.read_index(directory) or {}
            return {(item["source_sha256"], item["view"]): item["embedding_hash"]
                    for item in index.get("items", [])}
        return INDEX_STATES.get((path, embeddings.read_index), [path], load, copy_value=False)
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def _item_available(db_path, name, hit, view, present):
    """Check the recorded item hash and its required path. Scan no directory."""
    digest = hit.get("sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
        return False
    if view not in embeddings.VIEWS:
        return False
    key = (digest, view)
    if key not in present or present[key] != hit.get("embedding_hash"):
        return False
    try:
        path = os.path.join(embeddings.entry_dir(db_path, name), embeddings.IMAGES,
                            embeddings.image_name(digest, view))
        return os.path.isfile(path)
    except (OSError, ValueError, TypeError):
        return False


class VisualInputsCache:
    """Keep encoded artifacts with the identities of every file read to make them."""

    def __init__(self, max_entries=8, max_bytes=64 * 1024 * 1024):
        self.max_entries, self.max_bytes = max_entries, max_bytes
        self._entries = OrderedDict()
        self._bytes = 0
        self._lock = threading.Lock()
        self._flights = ReadFlights()
        self._epoch = 0

    def clear(self):
        with self._lock:
            self._epoch += 1
            self._entries.clear()
            self._bytes = 0

    @staticmethod
    def state(paths):
        try:
            return tuple(signature(path) for path in paths)
        except OSError:
            return None

    @staticmethod
    def size(value):
        # The payload holds dictionaries, lists, scalar values, and PNG URI strings.
        if isinstance(value, dict):
            return sys.getsizeof(value) + sum(VisualInputsCache.size(k) + VisualInputsCache.size(v)
                                             for k, v in value.items())
        if isinstance(value, (list, tuple)):
            return sys.getsizeof(value) + sum(VisualInputsCache.size(v) for v in value)
        return sys.getsizeof(value)

    def _remove(self, key):
        item = self._entries.pop(key, None)
        if item is not None:
            self._bytes -= item[3]

    def get(self, key, loader, *, sources_sink=None):
        with self._lock:
            epoch = self._epoch
        # Source paths are discovered by the loader. Each caller checks these
        # dependencies before cache publication, including after a shared read.
        def shared():
            return self._flights.run((key, epoch), loader)
        return self._get(key, shared, epoch, sources_sink)

    def _get(self, key, loader, epoch, sources_sink):
        with self._lock:
            item = self._entries.get(key)
            if item is not None:
                paths, state, value, _size = item
                if self.state(paths) == state:
                    result = deepcopy(value)
                    if self.state(paths) == state:
                        self._entries.move_to_end(key)
                        if sources_sink is not None:
                            sources_sink.update(zip(paths, state))
                        return result
                self._remove(key)
        value, sources, cacheable = loader()
        if sources_sink is not None:
            sources_sink.update(sources)
        paths, state = tuple(sources), tuple(sources.values())
        if not cacheable or None in state or self.state(paths) != state:
            return deepcopy(value)
        size = self.size(value) + self.size(key) + self.size(paths) + self.size(state)
        if self.max_entries <= 0 or size > self.max_bytes:
            return deepcopy(value)
        saved = deepcopy(value)
        with self._lock:
            if self._epoch != epoch or self.state(paths) != state:
                return deepcopy(value)
            self._remove(key)
            self._entries[key] = (paths, state, saved, size)
            self._bytes += size
            while len(self._entries) > self.max_entries or self._bytes > self.max_bytes:
                self._remove(next(iter(self._entries)))
        return deepcopy(value)


VISUAL_INPUTS = VisualInputsCache()


def _source(sources, path):
    path = os.path.abspath(path)
    try:
        state = signature(path)
    except OSError:
        state = None
    # A second read MUST NOT replace the identity from before the first read.
    sources.setdefault(path, state)


def _visual_key(photo, views, endpoint, scene_selection, label_mask_union=True, label_focus=False,
                label_on_main_bottle=True):
    version = main_scene.selector_version(scene_selection) if scene_selection else False
    constants = {}
    for module in (derive, alternatives, embeddings, main_scene, bottle_orientation):
        for name, value in vars(module).items():
            if name.isupper():
                try:
                    constants[module.__name__ + '.' + name] = model_cache.canonical(value)
                except (TypeError, ValueError):
                    continue
    source_state = getattr(photo, "source_state", None)
    identity = source_state if source_state is not None else ("unverified", id(photo.image))
    return (photo.path, identity, endpoint, version, label_mask_union, label_focus, label_on_main_bottle, CUT_SIDE, model_cache.ROOT,
            model_cache.READ, model_cache.canonical(views), model_cache.canonical(constants),
            embedding_run.CachedSam3, embedding_run.cuts_of, embedding_run.view_input,
            derive.open_image, embeddings.apply_steps, png_uri,
            build_embeddings.make_dis_segmenter_for_views, model_cache.lookup,
            getattr(embedding_run.CachedSam3, "_sent_copy", None),
            getattr(embedding_run.CachedSam3, "_post", None))


def _tracked_segmenter(endpoint, sources):
    client = embedding_run.CachedSam3(endpoint)
    if not isinstance(client, derive.Sam3Client):
        return client, False
    original = client._post
    original_copy = client._sent_copy
    sent = []

    def sent_copy(image):
        # Both target requests use the same unchanged photo in this reconstruction.
        if not sent or sent[0] is not image:
            sent[:] = [image, original_copy(image)]
        return sent[1]

    client._sent_copy = sent_copy

    def post(data, texts=derive.SAM3_TEXTS, return_masks=True):
        params = {"threshold": str(derive.SAM3_THRESHOLD),
                  "mask_threshold": str(derive.SAM3_MASK_THRESHOLD),
                  "return_masks": "true" if return_masks else "false"}
        fields = model_cache.request_fields(client.endpoint + "/segment_multi",
                                            derive.SAM3_MODEL, params, texts, [data])
        _source(sources, model_cache.path_of(fields))
        return original(data, texts, return_masks)

    client._post = post
    return client, True


def _reconstruct_inputs(photo, views, endpoint, scene_selection, label_mask_union=True, label_focus=False,
                        label_on_main_bottle=True):
    """Cache image artifacts alone. Read names, trace times, and comparisons each time."""
    def load():
        sources = {}
        if photo.path:
            sources[os.path.abspath(photo.path)] = getattr(photo, "source_state", None)
        for module in (sys.modules[__name__], derive, alternatives, embedding_run,
                       embeddings, main_scene, model_cache, build_embeddings,
                       embedding_run.main_label_match, bottle_orientation):
            _source(sources, module.__file__)
        segmenter, cacheable = _tracked_segmenter(endpoint, sources)
        cuts, out = {}, {"cuts": {}, "views": {}}
        targets = embedding_run.cut_targets(views)
        for target in (target for target in ("package", "label") if target in targets):
            box, processed, reason, result = _cut(photo, target, endpoint, scene_selection,
                                                   segmenter=segmenter,
                                                   label_mask_union=label_mask_union,
                                                   label_focus=label_focus,
                                                   label_on_main_bottle=label_on_main_bottle)
            cuts[target] = (box, processed) if box is not None else None
            item = {"box": box, "reason": reason, "result": result}
            if box is not None:
                item.update(src=png_uri(processed, CUT_SIDE), width=processed.width,
                            height=processed.height, alpha=processed.mode == "RGBA")
                selection = (result or {}).get("selection") or {}
                selected = selection.get("selected") or {}
                label = str(selected.get("label") or "").lower()
                if target == "package" and (label in ("bottle", "wine bottle") or
                                             "orientation" in selection):
                    used = bool(scene_selection and
                                main_scene.selector_version(scene_selection) >= main_scene.ORIENTATION_VERSION)
                    if used:
                        _, _, before, _, _ = main_scene.cut(photo.image, segmenter, version=4)
                        after, audit = processed, selection.get("orientation")
                    else:
                        before = processed
                        after, audit = bottle_orientation.normalize(before)
                    if audit is not None and (used or audit.get("angle_degrees")):
                        item["orientation"] = {"audit": audit, "used_in_run": used,
                            "before": {"src": png_uri(before, CUT_SIDE),
                                       "width": before.width, "height": before.height},
                            "after": {"src": png_uri(after, CUT_SIDE),
                                      "width": after.width, "height": after.height}}
            out["cuts"][target] = item
            cacheable = cacheable and reason is None
        try:
            dis_segmenter = build_embeddings.make_dis_segmenter_for_views(views)
        except (OSError, ImportError, ValueError) as exc:
            dis_segmenter = None
            dis_error = "The DIS input cannot be made again: %s." % exc
        else:
            dis_error = None
        for view, steps in views.items():
            target = embedding_run.segment_target(steps)
            if photo.image is None or (target is not None and cuts.get(target) is None):
                out["views"][view] = None
                cacheable = False
                continue
            try:
                prepared, reason = embedding_run.view_input(photo.image, steps, cuts, dis_segmenter)
            except embeddings.ItemError as exc:
                prepared, reason = None, str(exc)
            if prepared is None and dis_error and steps[0].get("step") == "segment_dis":
                reason = dis_error
            item = {"reason": reason}
            if prepared is not None:
                data = embeddings.png_bytes(prepared)
                item.update(src=build_embeddings.data_uri(data), width=prepared.width,
                            height=prepared.height, bytes=len(data),
                            sha256=hashlib.sha256(data).hexdigest())
            else:
                cacheable = False
            out["views"][view] = item
        # DIS weights have separate runtime state. Keep its existing reconstruction path.
        cacheable = cacheable and model_cache.READ and not any(
            s.get("step") == "segment_dis" for steps in views.values() for s in steps)
        if isinstance(segmenter, derive.Sam3Client):
            segmenter.session.close()
        return out, sources, cacheable

    return VISUAL_INPUTS.get(_visual_key(photo, views, endpoint, scene_selection,
                                        label_mask_union, label_focus, label_on_main_bottle), load,
                             sources_sink=getattr(photo, "artifact_sources", None))


def _cut(photo, target, endpoint, scene_selection=False, *, segmenter=None,
         label_mask_union=True, label_focus=False, label_on_main_bottle=True):
    """Return `(box, image, reason, result)` for one cached SAM3 target."""
    if photo.image is None:
        return None, None, photo.error, None
    try:
        trace = embedding_run.Trace()
        cut = embedding_run.cuts_of(
            photo.image, {target}, segmenter or embedding_run.CachedSam3(endpoint), trace,
            scene_selection=scene_selection if target == "package" else False,
            label_mask_union=label_mask_union, label_focus=label_focus,
            label_on_main_bottle=label_on_main_bottle).get(target)
        result = next((record.get("out") for record in trace.steps
                       if record.get("id") == "sam3-" + target), None)
    except derive.Sam3Unavailable as exc:
        return None, None, "The cut cannot be made again: %s." % exc, None
    except (OSError, ValueError) as exc:
        return None, None, "The cut cannot be made again: %s." % exc, None
    if cut is None:
        return None, None, "SAM3 found no %s." % target, result
    return cut[0], cut[1], None, result


def embedding_rounds(ctx):
    row, spec, photo, lists = ctx.row, ctx.spec, ctx.photo, ctx.lists
    trace = row.get("trace") if isinstance(row.get("trace"), dict) else None
    records = {}
    for record in (trace or {}).get("steps") or ():
        records.setdefault((record.get("id"), record.get("view")), record)
    views = spec.get("views") or {}
    sam3 = spec.get("sam3") or {}
    endpoint = sam3.get("endpoint") or derive.SAM3_ENDPOINT
    scene_selection = spec.get("scene_selection", False)
    name = spec.get("embedding") or spec.get("id")
    first = step("input", "Input photo")
    timed(first, records.get(("input", None)))
    first["artifacts"] = [a for a in [photo.artifact("00-input.%s" % (photo.extension or "jpg"))]
                          if a]
    first["result"] = first["result"] or photo.head(row)
    first["settings"] = {"photo": row.get("image_path"), "sha256": row.get("image_sha256")}
    if photo.error:
        first["notes"].append(photo.error)
    rounds = [[first], [], [], []]

    # A pipeline with the key `barcode` decodes the photo first. A code of `wine_code`
    # answers the photo, and no embedding model runs: its candidates hold the key `code`.
    code = records.get(("barcode", None))
    code_answer = any(isinstance(c, dict) and "code" in c for c in row.get("candidates") or ())
    if code or code_answer:
        part = step("barcode", "Decode codes, whole photo", "HTTP", "qr-scanner")
        timed(part, code)
        out = (code or {}).get("out") or {}
        if out.get("skipped"):
            part["state"] = "skipped"
            part["notes"].append(out["skipped"])
        hit = out.get("hit")
        if code_answer:
            part["lists"] = [answer_list(lists, row, "the answer of the code lookup",
                                         detail=lambda c: " ".join(
                                             str(c.get(k)) for k in ("format", "read")
                                             if c.get(k)) or None)]
            part["notes"].append("A code of the photo is in wine_code, so the code lookup "
                                 "answered the photo. No embedding model ran.")
        elif isinstance(hit, dict):
            part["lists"] = [{"title": "the wines of the code", "note": None,
                              "items": [lists.item(slug, i, 1.0)
                                        for i, slug in enumerate(hit.get("slugs") or [], 1)]}]
        rounds[0].append(part)
        if code_answer:
            return [(EMBEDDING_ROUNDS[0], rounds[0])]

    visual = _reconstruct_inputs(photo, views, endpoint, scene_selection,
                                  embedding_run.saved_label_mask_union(spec),
                                  sam3.get("label_focus") == "main",
                                  embedding_run.saved_label_on_main_bottle(spec))
    for target, label, group, texts, rule in (
            ("package", "Package selection and cut" if scene_selection else "Package cut",
             "segment", sam3.get("package_texts") or derive.SAM3_TEXTS,
             sam3.get("package")),
            ("label", "Label cut", "instances", alternatives.DETECT_TEXTS, sam3.get("label"))):
        if target not in embedding_run.cut_targets(views):
            continue
        part = step("sam3-" + target, label, service_of(endpoint), derive.SAM3_MODEL, group)
        record = records.get(("sam3-" + target, None))
        timed(part, record)
        cut = visual["cuts"][target]
        box, reason, replayed = cut["box"], cut["reason"], cut["result"]
        part["settings"] = {"endpoint": endpoint, "texts": texts, "rule": rule}
        if reason:
            part["notes"].append(reason)
        if box is not None:
            number = len(rounds[0]) + len(rounds[1])
            box_art = photo.artifact("%02d-%s-box.%s" % (number, target, photo.extension or "jpg"),
                                     [box])
            part["artifacts"] = [a for a in [box_art] if a] + [{
                "src": cut["src"], "caption": "%02d-%s-cut.png · %d × %d" % (
                    number, target, cut["width"], cut["height"]),
                "width": cut["width"], "height": cut["height"], "boxes": [],
                "check": None, "alpha": cut["alpha"]}]
            recorded = (record or {}).get("out") or {}
            if recorded.get("box") and list(recorded["box"]) != list(box):
                part["notes"].append("The cut made again has the box %s; the run had %s."
                                     % (list(box), recorded["box"]))
        if not part["result"]:
            part["result"] = replayed or {"box": list(box) if box is not None else None}
        selection = part["result"].get("selection") if isinstance(part["result"], dict) else None
        selected = selection.get("selected") if isinstance(selection, dict) else None
        if isinstance(selected, dict):
            part["notes"].append("The main-scene selector chose %s at score %.4f from %d "
                                 "package candidates and %d detected hands."
                                 % (selected.get("label"), selected.get("scene_score") or 0,
                                    len(selection.get("candidates") or ()),
                                    selection.get("hands") or 0))
        if isinstance(selection, dict):
            restored = selection.get("mask_holes_restored_pixels") or 0
            if restored:
                part["notes"].append("Restored %d pixels in enclosed package-mask holes "
                                     "to preserve printed label text and artwork." % restored)
            reason = selection.get("fallback_reason")
            if reason == "no_valid_package_mask":
                part["notes"].append("The package masks were too sparse. The photo context "
                                     "was preserved with a white-border crop.")
            elif reason == "full_frame_low_mask_fill":
                part["notes"].append("The package box covered almost the whole photo, but "
                                     "its mask removed most of the photo. The photo "
                                     "context was preserved with a white-border crop.")
        rounds[1].append(part)
        if target == "package" and cut.get("orientation"):
            rotation = cut["orientation"]
            audit = rotation["audit"]
            used = rotation["used_in_run"]
            angle = audit.get("angle_degrees", 0)
            rotation_name = "Query bottle rotation · %+.2f°" % angle
            if not used:
                rotation_name += " · preview only"
            part = step("bottle-orientation", rotation_name, group="portrait alignment")
            part["start_ms"], part["ms"] = None, None
            part["state"] = "done" if used and audit.get("applied") else "skipped"
            part["settings"] = {"geometry": "minimum-area enclosing mask rectangle",
                "angle_search": "0.5 degree search; 0.05 degree refinement",
                "direction": "visible neck at top; unknown direction has no forced half turn",
                "order": "mask and image rotate together; tight crop before model resize"}
            recorded = ((record or {}).get("out") or {}).get("selection") or {}
            part["result"] = dict(audit, used_in_saved_embedding=used,
                                  recorded_orientation=recorded.get("orientation"))
            for key, caption in (("before", "Before rotation · segmented query"),
                                 ("after", "After rotation · upright crop" if audit.get("applied")
                                  else "Query crop retained")):
                artifact = dict(rotation[key], caption=caption, boxes=[], check=None, alpha=True)
                part["artifacts"].append(artifact)
            if not used:
                part["notes"].append("This saved run did not use bottle rotation. The alignment "
                                     "preview does not change its embedding or ranking.")
            elif audit.get("applied"):
                part["notes"].append("Rotated the image and its mask by %+.2f° before resize "
                                     "and embedding." % angle)
                part["notes"].append("Rotation time is included in package selection and cut timing.")
            else:
                part["notes"].append("Kept the query crop: %s." % audit.get("reason", "no rotation needed"))
            if audit.get("direction_confident"):
                part["notes"].append("The mask width profile places the visible neck at the top; "
                                     "neck/body width ratio %.3f." % audit["neck_width_ratio"])
            else:
                part["notes"].append("No clear neck direction. The geometry does not force a 180° flip.")
            if "mask_crop_iou_before" in audit:
                part["notes"].append("Mask/crop IoU %.3f → %.3f. Crop area %.1f%% of the camera crop."
                    % (audit["mask_crop_iou_before"], audit["mask_crop_iou_after"],
                       100*audit["crop_area_ratio"]))
            rounds[1].append(part)

    quality = records.get(("label-quality", None))
    if quality:
        rounds[1].append(quality_step(quality, spec.get("label_gate") or
                                     (spec.get("local_comparison") or {}).get("gate")))

    prepared_label = records.get(("comparison-label", None))
    if prepared_label:
        part = step("comparison-label", "Segmented main label for local comparison")
        timed(part, prepared_label)
        result = part["result"]
        digest = result.get("sha256")
        if isinstance(digest, str) and re.fullmatch(r"[a-f0-9]{64}", digest):
            path = Path(ROOT) / "work/local-comparison/queries" / (digest + ".png")
            try:
                data = path.read_bytes()
                if hashlib.sha256(data).hexdigest() != digest:
                    raise ValueError("saved label input changed")
                from PIL import Image
                with Image.open(io.BytesIO(data)) as image:
                    part["artifacts"] = [{"src": build_embeddings.data_uri(data),
                        "caption": "masked main label · white background",
                        "width": image.width, "height": image.height,
                        "boxes": [], "check": "same", "sha256": digest}]
            except (OSError, ValueError) as exc:
                part["notes"].append(str(exc))
        part["result"] = {k: v for k, v in result.items() if k != "path"}
        rounds[1].append(part)

    for view, steps in views.items():
        chain = " → ".join(s.get("step", "?") for s in steps)
        part = step("view", "View %s" % view, "local", None, chain, view=view)
        record = records.get(("view", view))
        timed(part, record)
        part["settings"] = {"steps": steps}
        saved_input = False
        digest = ((record or {}).get("out") or {}).get("sha256")
        if spec.get("local_comparison") and isinstance(digest, str) and re.fullmatch(r"[a-f0-9]{64}", digest):
            path = Path(ROOT) / "work/local-comparison/bottle-inputs" / (digest + ".png")
            try:
                data = path.read_bytes()
                if hashlib.sha256(data).hexdigest() != digest:
                    raise ValueError("saved local model input changed")
                from PIL import Image
                with Image.open(io.BytesIO(data)) as image:
                    visual["views"][view] = {"src": build_embeddings.data_uri(data),
                        "sha256": digest, "width": image.width, "height": image.height,
                        "bytes": len(data)}
                saved_input = True
                part["notes"].append("Exact saved local model input; its byte hash matches the run.")
            except (OSError, ValueError):
                pass
        if spec.get("label_gate") is not None and part["state"] == "skipped":
            rounds[1].append(part)
            continue
        if photo.image is None:
            part["notes"].append(photo.error)
            rounds[1].append(part)
            continue
        target = embedding_run.segment_target(steps)
        if target is not None and visual["cuts"][target]["box"] is None and not saved_input:
            if part["state"] != "skipped":
                part["notes"].append("The model input needs the %s cut, which cannot be "
                                     "shown." % target)
            rounds[1].append(part)
            continue
        prepared = visual["views"][view]
        if "src" not in prepared:
            reason = prepared["reason"]
            if reason and reason not in part["notes"]:
                part["notes"].append(reason)
            rounds[1].append(part)
            continue
        digest = prepared["sha256"]
        recorded = ((record or {}).get("out") or {}).get("sha256")
        check = None if not recorded else ("same" if recorded == digest else "changed")
        number = len(rounds[0]) + len(rounds[1])
        part["artifacts"] = [{"src": prepared["src"],
                              "caption": "%02d-view-%s.png · %d × %d" % (
                                  number, view, prepared["width"], prepared["height"]),
                              "width": prepared["width"], "height": prepared["height"],
                              "boxes": [], "check": check, "sha256": digest}]
        if check == "changed":
            part["notes"].append("The model input made again differs from the input of the "
                                 "run: the code, the cache, or the photo changed.")
        if not part["result"]:
            part["result"] = {"width": prepared["width"], "height": prepared["height"],
                              "bytes": prepared["bytes"], "sha256": digest}
        rounds[1].append(part)

    local = spec.get("model_backend") == "local"
    embed = step("embed", "Embedding", "local" if local else service_of(spec.get("url")),
                 spec.get("model"))
    timed(embed, records.get(("embed", None)))
    embed["settings"] = {"model": spec.get("model"), "model_backend": spec.get("model_backend"),
                         "url": spec.get("url"), "extra_body": spec.get("extra_body")}
    rounds[2].append(embed)

    present = _index_state(ctx.db_path, name) if name else {}
    cands = row.get("candidates") or []
    searched = [view for view in views if (("search", view) in records
                                           or any(view in c for c in cands))]
    for view in searched:
        search_name = (spec.get("view_indexes") or {}).get(view, name)
        view_present = _index_state(ctx.db_path, search_name) if search_name != name else present
        part = step("search", "Search, space %s" % view, "local", search_name, "view %s" % view,
                    view=view)
        record = records.get(("search", view))
        timed(part, record)
        part["settings"] = {"index": search_name, "view": view, "top_k": spec.get("top_k")}
        top = ((record or {}).get("out") or {}).get("top")
        if isinstance(top, list):
            items = []
            for rank, hit in enumerate(top, 1):
                image = None
                deferred = False
                if _item_available(ctx.db_path, search_name, hit, view, view_present):
                    preview_query = getattr(ctx, "preview_query", None)
                    if preview_query and (hit.get("angle") or 0) % 360:
                        image = _preview_url(*preview_query, name, hit, view, rank)
                        deferred = True
                    else:
                        image = _item_image(ctx.db_path, search_name, hit, view)
                detail = "%s · %s" % (view, hit.get("type"))
                if hit.get("angle") is not None:
                    detail += " · %d°" % hit["angle"]
                item = lists.item(hit.get("slug"), rank, hit.get("cosine"),
                                  image=image, detail=detail)
                if deferred:
                    item["image_deferred"] = True
                items.append(item)
            part["lists"] = [{"title": "the top %d of the space %s" % (len(items), view),
                              "note": None, "items": items}]
            part["result"] = {k: v for k, v in part["result"].items() if k != "top"}
        else:
            ordered = sorted(cands, key=lambda c: (c.get(view) is None, -(c.get(view) or 0)))
            part["lists"] = [{"title": "the candidates of the answer, by the cosine of %s"
                                       % view, "note": NO_SPACE_LIST,
                              "items": [lists.item(c.get("slug"), i, c.get(view),
                                                   detail="rank %s in the answer"
                                                   % c.get("rank"))
                                        for i, c in enumerate(ordered, 1)]}]
        rounds[2].append(part)

    route = records.get(("label-route", None))
    if route:
        part = step("label-route", "Select retrieval space")
        timed(part, route)
        route_options = spec.get("label_gate") or (spec.get("local_comparison") or {}).get("gate")
        part["settings"] = {"label_gate": route_options}
        selected = part["result"].get("selected_view")
        if selected:
            part["name"] += " · " + ("Label" if selected == "label" else "Bottle")
        part["notes"].append("Use the %s ranking and its cosine scores."
                             % ("label" if selected == "label" else "bottle")
                             if selected else "No retrieval space is available.")
        reasons = {
            "label_quality_rejected": "The crop-quality gate rejected the label input.",
            "no_label_ranking": "No label ranking is available.",
            "label_score_below_threshold": "Label similarity is below the threshold.",
            "label_margin_below_threshold": "The label winner has insufficient lead over the second wine.",
            "no_fallback_ranking": "No bottle ranking is available for fallback.",
        }
        part["notes"].extend(reasons.get(reason, reason) for reason in part["result"].get("reasons") or [])
        for key, title, threshold in (("label_score", "Label similarity", "min_score"),
                                      ("label_margin", "Label margin", "min_margin")):
            value = part["result"].get(key)
            minimum = (route_options or {}).get(threshold)
            if value is not None:
                part["notes"].append("%s: %.4f%s." % (
                    title, value, " (minimum %.4f)" % minimum if minimum is not None else ""))
        rounds[2].append(part)

    score = step("score", "Score", "local")
    timed(score, records.get(("score", None)))
    score["settings"] = {"score": spec.get("score")}
    if spec.get("local_comparison"):
        score["settings"]["score"] = "Selected visual cosine; native metric or variant text may determine rank."
    score["lists"] = [answer_list(lists, row, "the answer", detail=lambda c: " · ".join(
        "%s %s" % (view, _cos(c.get(view))) for view in searched) or None)]
    rounds[2].append(score)

    record = records.get(("cluster_rules", None))
    if record:
        result = record.get("out") if isinstance(record.get("out"), dict) else {}
        part = step("cluster_rules", "VLM evidence re-rank", "VLM",
                    (spec.get("rerank") or {}).get("vlm"), "option scores")
        timed(part, record)
        if result.get("error"):
            part["notes"].append("The base order stays because the evidence call failed: %s"
                                 % result["error"])
        part["vlm"] = {
            "mode": result.get("mode"), "cluster": result.get("cluster"),
            "model": (result.get("model") or (spec.get("rerank") or {}).get("model")
                      or (spec.get("rerank") or {}).get("vlm")),
            "window": result.get("window") or [],
            "questions": result.get("questions") or [],
            "option_scores": result.get("option_scores") or {},
            "raw_option_scores": result.get("raw_option_scores") or {},
            "validation_errors": result.get("validation_errors") or {},
            "attempts": result.get("attempts") or [],
            "base_scores": result.get("base_scores") or {},
            "evidence_scores": result.get("evidence_scores") or {},
            "decision_scores": result.get("decision_scores") or {},
            "decision_weight": result.get("decision_weight"),
            "ms": result.get("ms"), "cached": bool(result.get("cached")),
            "error": result.get("error"), "changed": bool(result.get("changed")),
        }

        def decision_detail(candidate):
            slug = candidate.get("slug")
            if slug not in (result.get("window") or []):
                return None
            base = (result.get("base_scores") or {}).get(slug)
            evidence = (result.get("evidence_scores") or {}).get(slug)
            decision = (result.get("decision_scores") or {}).get(slug)
            return "embedding %s · evidence %s · decision %s" % (
                _cos(base), _cos(evidence), _cos(decision))

        part["lists"] = [answer_list(lists, row, "the answer after the evidence decision",
                                     detail=decision_detail)]
        by_slug = {candidate.get("slug"): candidate for candidate in cands}
        for item in part["lists"][0]["items"]:
            candidate = by_slug.get(item["slug"]) or {}
            explain = candidate.get("explain") if isinstance(candidate.get("explain"), dict) else {}
            base_rank = explain.get("base_rank")
            if base_rank is not None and candidate.get("rank") is not None:
                item["moved"] = base_rank - candidate["rank"] or None
        rounds[3].append(part)
    text_record = records.get(("label-text", None))
    if text_record:
        engine = ((text_record.get("out") or {}).get("engine") or
                  (spec.get("main_label") or {}).get("ocr", "tesseract"))
        model = "PaddleOCR PP-OCRv5 East Slavic" if engine == "paddleocr" else "Tesseract rus+eng"
        part = step("label-text", "Verify variant text", "local", model)
        timed(part, text_record)
        part["settings"] = spec.get("main_label") or spec.get("local_comparison") or {}
        result = part["result"]
        part["notes"].append("Read sugar level: %s. %s" % (
            result.get("observed_sugar") or "unreadable",
            "Explicit matches move ahead of conflicting variants; visual scores stay unchanged."
            if result.get("applied") else "The visual order stays unchanged."))
        observed = result.get("observed_attributes")
        if isinstance(observed, dict):
            active = result.get("discriminating_fields") or []
            for field in variant_attributes.FIELDS:
                value = ", ".join(observed.get(field) or []) or "unknown"
                state = "distinguishes shortlisted variants" if field in active else "unused for this shortlist"
                part["notes"].append("%s read: %s · %s." % (variant_attributes.LABELS[field], value, state))
            if result.get("ranking_policy") == variant_attributes.RANKING_POLICY:
                part["notes"].append("Reliable contradictions rank last; compatible and unknown metadata keep visual order. "
                                     "An explicitly read product line can promote its named candidate. Missing text remains unknown.")
            else:
                part["notes"].append("Complete matches precede partial matches, unknowns and explicit conflicts. "
                                     "Missing text and absent product-line terms remain unknown.")
        part["notes"].append("Variant text verifies distinguishing attributes; it does not establish complete wine identity.")
        normalization = result.get("normalization")
        if isinstance(normalization, dict):
            part["notes"].append("Shared wine-term normalization: %s." % (normalization.get("text") or "unreadable"))
            for correction in normalization.get("corrections") or []:
                part["notes"].append("OCR term: %s → %s (original confidence %s)." % (
                    correction["raw"], correction["normalized"], correction["confidence"]))
        if result.get("applied") or isinstance(result.get("candidate_attributes"), dict):
            def variant_detail(candidate):
                evidence = candidate.get("variant_text") or {}
                fields = (result.get("candidate_attributes") or {}).get(candidate.get("slug")) or evidence.get("attributes")
                if isinstance(fields, dict):
                    parts = []
                    for field in variant_attributes.FIELDS:
                        item = fields.get(field) or {}
                        expected = ", ".join(item.get("expected") or []) or "unknown"
                        parts.append("%s: %s · %s" % (variant_attributes.LABELS[field], expected,
                                                      item.get("status") or "unknown"))
                    return "; ".join(parts)
                return "Sugar level: %s · %s" % (evidence.get("expected") or "unknown",
                                                 evidence.get("status") or "unknown")

            group = answer_list(lists, row, "the answer after variant-text verification",
                                note="Original visual scores are preserved; text evidence determines this order.",
                                detail=variant_detail)
            for item, candidate in zip(group["items"], cands):
                before = (candidate.get("variant_text") or {}).get("visual_rank") if result.get("applied") else None
                if before is not None and candidate.get("rank") is not None:
                    item["moved"] = before - candidate["rank"] or None
            part["lists"] = [group]
        rounds[3].append(part)
    local_record = records.get(("local-comparison", None))
    global_record = records.get(("comparison-label-search", None))
    if global_record:
        options = spec.get("local_comparison") or {}
        part = step("comparison-label-search", "Search, space main label", "local", "SigLIP2 p512")
        timed(part, global_record)
        found = (global_record.get("out") or {}).get("top") or []
        items = []
        for c in found:
            hit = next((i for i in c.get("items", []) if i.get("view") == "label"), None)
            image = _item_image(ctx.db_path, options.get("index"), hit, "label") if hit else None
            items.append(lists.item(c.get("slug"), c.get("rank"), c.get("score"), image=image,
                                    detail="segmented main label · local cosine"))
        part["lists"] = [{"title": "the top %d of the space main label" % len(items),
                          "note": "Recorded before the quality gate and variant text.", "items": items}]
        part["result"] = {k: v for k, v in part["result"].items() if k != "top"}
        rounds[2].append(part)
    if local_record or global_record:
        options = spec.get("local_comparison") or {}
        method = options.get("method")
        part = step("local-comparison", "Local comparison · %s" % method, "local", method)
        if local_record:
            timed(part, local_record)
        else:
            part["result"] = {"applied": True, "method": method}
            part["notes"].append("This displays the selected ranking. Retrieval time appears in the main-label search step.")
        part["settings"] = options
        result = part["result"]
        if result.get("reason"):
            part["notes"].append("Bottle fallback: " + result["reason"])
        if result.get("error"):
            part["notes"].append("Comparison error: " + result["error"])
        metric = result.get("field") or ("selected visual cosine" if global_record else "label cosine")
        direction = "higher" if result.get("higher_is_better", True) else "lower"
        part["notes"].append("%s: %s values rank first. Bottle cosines remain separate." % (metric, direction))
        if "cached_pairs" in result:
            part["notes"].append("%s cached pairs; %s fresh pairs." %
                                 (result["cached_pairs"], result["fresh_pairs"]))
        entries = []
        for c in cands:
            detail = c.get("comparison") or {}
            ref = detail.get("reference")
            image = None
            if ref:
                hit = dict(ref, sha256=ref.get("source_sha256"))
                image = _item_image(ctx.db_path, options.get("index"), hit, "label")
            elif global_record and c.get("label") is not None:
                hit = next((i for i in c.get("items", []) if i.get("view") == "label"), None)
                if hit:
                    image = _item_image(ctx.db_path, options.get("index"), hit, "label")
            value = detail.get("value") if detail else c.get("score")
            entries.append(lists.item(c.get("slug"), c.get("rank"), value, image=image,
                detail=("%s · %s better · bottle rank %s / cosine %s" %
                       (detail.get("field"), direction, detail.get("bottle_rank"),
                        _cos(detail.get("bottle_score"))) if detail else "selected ranking")))
        part["lists"] = [{"title": "the top %d after %s" % (len(entries), method),
                          "note": "Raw distances and inlier counts are not probabilities.", "items": entries}]
        part["result"] = {k: v for k, v in result.items() if k not in ("top", "measurements")}
        rounds[3].append(part)
    if not trace:
        ctx.notes.append(NO_TIME)
    titles = list(EMBEDDING_ROUNDS)
    if spec.get("local_comparison"):
        titles[3] = "local comparison and variant text determine the final order"
    return [(titles[i], steps) for i, steps in enumerate(rounds) if steps]


def _item_url(name, digest, view, embedding_hash):
    """Return the URL of the PNG of one catalogue item of the index of `name`."""
    import embedding_routes  # here alone: the URL of a prepared image
    return embedding_routes.image_url(name, digest, view, embedding_hash)


def _preview_token(name, hit, view):
    fields = {"embedding": name, "sha256": hit.get("sha256"), "view": view,
              "embedding_hash": hit.get("embedding_hash"), "angle": hit.get("angle") or 0}
    return hashlib.sha256(model_cache.canonical(fields).encode("utf-8")).hexdigest()


def _preview_url(run_id, query_id, name, hit, view, rank):
    return "/api/run-preview?" + urllib.parse.urlencode({
        "id": run_id, "query": query_id, "view": view, "rank": rank,
        "token": _preview_token(name, hit, view)})


def preview_image(runs_dir, db_path, run_id, query_id, view, rank, token):
    """Resolve a recorded search hit. Render only a current prepared image."""
    if (view not in embeddings.VIEWS or not isinstance(rank, str)
            or not re.fullmatch(r"[1-9][0-9]{0,4}", rank)
            or not isinstance(token, str) or not re.fullmatch(r"[a-f0-9]{64}", token)):
        raise StepError(400, "invalid preview")
    row, _meta, spec = _run_data(runs_dir, run_id, query_id)
    if run_kind(spec) != "embedding" or view not in (spec.get("views") or {}):
        raise StepError(404, "unknown preview")
    record = next((part for part in (row.get("trace") or {}).get("steps") or ()
                   if part.get("id") == "search" and part.get("view") == view), None)
    top = ((record or {}).get("out") or {}).get("top")
    index = int(rank) - 1
    if not isinstance(top, list) or index >= len(top) or not isinstance(top[index], dict):
        raise StepError(404, "unknown preview")
    hit = top[index]
    name = spec.get("embedding") or spec.get("id")
    if not name or token != _preview_token(name, hit, view) or not (hit.get("angle") or 0) % 360:
        raise StepError(404, "preview changed since the popup opened")
    if not _item_available(db_path, name, hit, view, _index_state(db_path, name)):
        raise StepError(404, "preview is no longer in the index")
    path = os.path.join(embeddings.entry_dir(db_path, name), embeddings.IMAGES,
                        embeddings.image_name(hit["sha256"], view))
    try:
        before = signature(path)
        uri = _item_image(db_path, name, hit, view)
        stable = signature(path) == before
    except OSError as exc:
        raise StepError(404, "cannot read the prepared image") from exc
    if not stable or not _item_available(db_path, name, hit, view, _index_state(db_path, name)):
        raise StepError(404, "preview changed while it was read")
    prefix = "data:image/png;base64,"
    if not uri.startswith(prefix):
        raise StepError(404, "cannot read the prepared image")
    return base64.b64decode(uri[len(prefix):])


def _item_image(db_path, name, hit, view):
    """Return the image of one search hit: the URL of its prepared PNG. A hit of a rotation
    entry (plan 82) at an angle other than 0° gets a data URI of that PNG, rotated as the
    build rotates it. The index keeps the 0° PNG alone, and the build rotates before the
    last `resize`, so the pixels can differ a little from the model input."""
    url = _item_url(name, hit["sha256"], view, hit["embedding_hash"])
    angle = hit.get("angle") or 0
    if not angle % 360:
        return url
    path = os.path.join(embeddings.entry_dir(db_path, name), embeddings.IMAGES,
                        embeddings.image_name(hit["sha256"], view))
    def render():
        image, _icc = derive.open_image(path)
        rotated = embeddings.rotate_fixed_scale(image, angle, None, image.size)
        return png_uri(rotated, CUT_SIDE)

    try:
        return THUMBNAILS.get((path, hit["embedding_hash"], angle, CUT_SIDE), [path],
                              render, copy_value=False)
    except (OSError, ValueError):
        return url


# ---- the matcher run ----

def rerank_records(cand):
    """Return (the VLM rule record, the difference record) of one candidate, or None."""
    top = cand.get("explain") if isinstance(cand.get("explain"), dict) else None
    if not top:
        return None, None
    if top.get("kind") == "cluster_rules":
        inner = top.get("inner") if isinstance(top.get("inner"), dict) else None
        return top, inner if inner and inner.get("kind") == "difference" else None
    if top.get("kind") == "difference":
        return None, top
    return None, None


def _ordered(cands, rank_of):
    """Return the candidates in the order of `rank_of(candidate, position)`."""
    return [c for _, _, c in sorted((rank_of(c, i), i, c) for i, c in enumerate(cands))]


def _moves(before, after):
    """Return slug -> the move from `before` to `after`: positive is up."""
    place = {c.get("slug"): i for i, c in enumerate(before)}
    return {c.get("slug"): place.get(c.get("slug"), i) - i for i, c in enumerate(after)}


def matcher_rounds(ctx):
    row, spec, photo, lists = ctx.row, ctx.spec, ctx.photo, ctx.lists
    url = str(spec.get("url") or "")
    match = MATCHER_PATH.search(urllib.parse.urlsplit(url).path)
    pipeline = match.group(1) if match else spec.get("id")
    first = step("input", "Input photo")
    first["artifacts"] = [a for a in [photo.artifact("00-input.%s" % (photo.extension or "jpg"))]
                          if a]
    first["result"] = photo.head(row)
    first["settings"] = {"photo": row.get("image_path"), "sha256": row.get("image_sha256")}

    inputs = step("inputs", "Matcher inputs", "matcher", pipeline)
    inputs["settings"] = {"url": url, "matcher": MATCHER_ROOT}
    if photo.path:
        scripts = os.path.join(ROOT, "scripts")
        if scripts not in sys.path:
            sys.path.insert(1, scripts)
        try:
            import run_model_inputs  # noqa: E402  (PIL and the matcher code, on demand)
            answer = run_model_inputs.build_model_inputs(
                Path(MATCHER_ROOT), url, Path(photo.path), str(row.get("image_sha256") or ""),
                list(row.get("candidates") or []))
            for i, one in enumerate(answer.get("inputs") or [], 1):
                inputs["artifacts"].append({
                    "src": one.get("src"), "width": one.get("width"),
                    "height": one.get("height"), "boxes": [], "check": None,
                    "caption": "01-input-%d · %s · %s" % (
                        i, " + ".join(one.get("uses") or []),
                        ", ".join(one.get("pipelines") or []))})
            inputs["notes"].extend(answer.get("notes") or [])
        except Exception as exc:  # noqa: BLE001 - the popup shows why the inputs are absent
            inputs["notes"].append("The model inputs cannot be made again: %s" % exc)
    else:
        inputs["notes"].append(photo.error)

    cands = list(row.get("candidates") or [])
    records = [rerank_records(c) for c in cands]
    vlm = {c.get("slug"): r[0] for c, r in zip(cands, records) if r[0]}
    diff = {c.get("slug"): r[1] for c, r in zip(cands, records) if r[1]}
    before_vlm = _ordered(cands, lambda c, i: (vlm[c["slug"]].get("base_rank") or i + 1)
                          if c.get("slug") in vlm else i + 1)
    before_diff = _ordered(before_vlm, lambda c, i: (diff[c["slug"]].get("base_rank") or i + 1)
                           if c.get("slug") in diff else i + 1)

    def base_score(c):
        for record in (diff.get(c.get("slug")), vlm.get(c.get("slug"))):
            if record and record.get("base_score") is not None:
                return record["base_score"]
        return c.get("score")

    search = step("search", "Search", "matcher", pipeline, ms=row.get("latency_ms"))
    search["settings"] = {"url": url, "query": spec.get("query"), "top_k": spec.get("top_k")}
    search["result"] = {"http_status": row.get("http_status"), "latency_ms": row.get("latency_ms"),
                        "error": row.get("error")}
    if row.get("error"):
        search["state"], search["error"] = "failed", row["error"]
    title = "the order before the re-rank" if (vlm or diff) else "the answer"
    search["lists"] = [{"title": title, "note": None, "items": [
        lists.item(c.get("slug"), i, base_score(c)) for i, c in enumerate(before_diff, 1)]}]
    if vlm or diff:
        search["notes"].append("The time is the time of the whole request. The re-rank steps "
                               "ran inside it.")
    rounds = [[first], [inputs], [search], []]

    if diff:
        part = step("difference", "Difference words", "matcher", pipeline, "text")
        moves = _moves(before_diff, before_vlm)
        part["lists"] = [{"title": "the order after the step", "note": None, "items": [
            lists.item(c.get("slug"), i, (vlm.get(c.get("slug")) or {}).get("base_score",
                                                                            c.get("score")),
                       moved=moves.get(c.get("slug")) or None,
                       detail=_difference_detail(diff.get(c.get("slug"))))
            for i, c in enumerate(before_vlm, 1)]}]
        part["result"] = {slug: {k: v for k, v in record.items() if k != "kind"}
                          for slug, record in diff.items()}
        rounds[3].append(part)
    if vlm:
        record = next(iter(vlm.values()))
        part = step("vlm", "VLM cluster rule", "matcher", pipeline, "VLM",
                    ms=None if record.get("cached") else record.get("ms"),
                    cached=bool(record.get("cached")))
        if record.get("error"):
            part["notes"].append("No answer: %s. The base order stays." % record["error"])
        # The question text comes from the run alone (owner message of
        # 2026-09-26T07:32:51+0300: no more reads of dataset/catalog-cluster*.json).
        questions = record.get("questions") or []
        if not questions and record.get("answers"):
            part["notes"].append("The run holds the answers alone, with no question text.")
        part["vlm"] = {"mode": record.get("mode"), "cluster": record.get("cluster"),
                       "model": record.get("model"),
                       "window": record.get("window") or [], "questions": questions,
                       "answers": record.get("answers") or {},
                       "answer": record.get("answer"), "chosen": record.get("chosen"),
                       "scores": record.get("scores") or {}, "ms": record.get("ms"),
                       "cached": bool(record.get("cached")), "error": record.get("error"),
                       "changed": bool(record.get("changed"))}
        moves = _moves(before_vlm, cands)
        part["lists"] = [answer_list(lists, row, "the answer: the order after the step")]
        for item in part["lists"][0]["items"]:
            item["moved"] = moves.get(item["slug"]) or None
        part["result"] = {k: v for k, v in record.items() if k not in ("inner", "kind")}
        rounds[3].append(part)
    return [(MATCHER_ROUNDS[i], steps) for i, steps in enumerate(rounds) if steps]


def _words(values):
    """Return the text of a list of words: a word is a string, or a dict with `token`."""
    return ", ".join(str(v.get("token", v)) if isinstance(v, dict) else str(v) for v in values)


def _difference_detail(record):
    if not record:
        return None
    words = []
    if record.get("evidence") is not None:
        words.append("evidence %s" % record["evidence"])
    if record.get("contradicted"):
        words.append("contradicted %s" % _words(record["contradicted"]))
    if record.get("seen"):
        words.append("seen %s" % _words(record["seen"]))
    return " · ".join(words) or None


# ---- the other runs ----

def request_rounds(ctx):
    row, spec, photo, lists = ctx.row, ctx.spec, ctx.photo, ctx.lists
    url = spec.get("url")
    first = step("input", "Input photo")
    first["artifacts"] = [a for a in [photo.artifact("00-input.%s" % (photo.extension or "jpg"))]
                          if a]
    first["result"] = photo.head(row)
    if url:
        name = "Remote search" if ctx.kind == "remote" else "Backend request"
        answer = step("request", name, service_of(url), spec.get("id"),
                      ms=row.get("latency_ms"))
        answer["settings"] = {"url": url, "query": spec.get("query"), "field": spec.get("field"),
                              "top_k": spec.get("top_k")}
    else:
        answer = step("request", "Backend answer", "local", spec.get("id"))
        answer["notes"].append("This run sent no request to a model.")
    answer["result"] = {"http_status": row.get("http_status"),
                        "latency_ms": row.get("latency_ms"), "error": row.get("error")}
    if row.get("error"):
        answer["state"], answer["error"] = "failed", row["error"]
    answer["lists"] = [answer_list(lists, row, "the answer")]
    return [(REQUEST_ROUNDS[0], [first]), (REQUEST_ROUNDS[1], [answer])]


BUILDERS = {"embedding": embedding_rounds, "matcher": matcher_rounds,
            "remote": request_rounds, "request": request_rounds, "none": request_rounds}


class Context:
    def __init__(self, db_path, conn, row, spec, kind, card_images, card_images_for_slugs=None):
        self.db_path, self.conn, self.row, self.spec, self.kind = db_path, conn, row, spec, kind
        self.photo = Photo(conn, db_path, row)
        self.lists = Lists(conn, row, card_images, card_images_for_slugs)
        self.notes = []


def _run_data(runs_dir, run_id, query_id):
    if run_id not in run_files.run_dirs(runs_dir):
        raise StepError(404, "unknown run")
    row = run_files.run_result(runs_dir, run_id, query_id)
    if row is None:
        raise StepError(404, "unknown query")
    meta = run_files.read_json(run_files.run_path(runs_dir, run_id, "run.json")) or {}
    spec = meta.get("backend") if isinstance(meta.get("backend"), dict) else {}
    return row, meta, spec


def steps_view(runs_dir, db_path, run_id, query_id, card_images, *, card_images_for_slugs=None,
               artifact_only=False):
    """Return the answer of `/api/run-steps`. Raise `StepError`."""
    row, meta, spec = _run_data(runs_dir, run_id, query_id)
    kind = run_kind(spec)
    try:
        conn = sqlite3.connect(Path(os.path.abspath(db_path)).as_uri() + "?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise StepError(503, "cannot read the lab database: %s" % exc)
    with closing(conn):
        ctx = Context(db_path, conn, row, spec, kind, card_images, card_images_for_slugs)
        ctx.preview_query = (run_id, query_id)
        built = BUILDERS[kind](ctx)
        rounds, number = [], 0
        for n, (note, steps) in enumerate(built):
            for part in steps:
                part["n"] = number
                number += 1
            rounds.append({"n": n, "title": "Round %d" % n, "note": note, "steps": steps})
        if artifact_only:
            sources = ctx.photo.artifact_sources
            if (ctx.photo.path is None or ctx.photo.source_state is None or
                    VisualInputsCache.state([ctx.photo.path]) != (ctx.photo.source_state,) or
                    any(state is not None and VisualInputsCache.state([path]) != (state,)
                        for path, state in sources.items())):
                raise StepError(404, "artifact changed while it was read")
        else:
            ctx.lists.finish(rounds)
    return {
        "run": run_id, "query": query_id, "kind": kind,
        "configuration": run_files.configuration_of(meta),
        "photo": ctx.photo.head(row),
        "row": {key: row.get(key) for key in ("label", "outcome", "rank_of_truth", "truth",
                                              "slug", "latency_ms", "error", "image_path")},
        "recorded": isinstance(row.get("trace"), dict),
        "rounds": rounds, "notes": ctx.notes,
    }


def _artifact_token(run_id, query_id, part, index, artifact):
    return hashlib.sha256(model_cache.canonical(
        [run_id, query_id, part["id"], part.get("view"), part["n"], index, artifact]
    ).encode("utf-8")).hexdigest()


def defer_artifacts(answer):
    """Replace reconstructed PNGs with checked URLs; keep their captions and checks."""
    for round_ in answer["rounds"]:
        for part in round_["steps"]:
            for index, artifact in enumerate(part["artifacts"]):
                if not artifact.get("src", "").startswith("data:image/png;base64,"):
                    continue
                token = _artifact_token(answer["run"], answer["query"], part, index, artifact)
                artifact["src"] = "/api/run-artifact?" + urllib.parse.urlencode({
                    "id": answer["run"], "query": answer["query"], "step": part["n"],
                    "artifact": index, "token": token})
                artifact["deferred"] = True
    return answer


def artifact_image(runs_dir, db_path, run_id, query_id, number, index, token):
    """Read one recorded artifact. URLs cannot name arbitrary files or model requests."""
    try:
        number, index = int(number), int(index)
        if number < 0 or index < 0:
            raise ValueError()
    except (ValueError, TypeError):
        raise StepError(400, "invalid artifact")
    _run_data(runs_dir, run_id, query_id)  # validate identifiers before resolving paths
    paths = [run_files.run_path(runs_dir, run_id, file) for file in ("run.json", "results.jsonl")]
    before = VisualInputsCache.state(paths)
    answer = steps_view(runs_dir, db_path, run_id, query_id, lambda conn: {}, artifact_only=True)
    if before is None or VisualInputsCache.state(paths) != before:
        raise StepError(404, "run changed while the artifact was read")
    part = next((part for round_ in answer["rounds"] for part in round_["steps"]
                 if part["n"] == number), None)
    if part is None or index >= len(part["artifacts"]):
        raise StepError(404, "unknown artifact")
    artifact = part["artifacts"][index]
    if (not artifact.get("src", "").startswith("data:image/png;base64,") or
            token != _artifact_token(run_id, query_id, part, index, artifact)):
        raise StepError(404, "artifact changed since the popup opened")
    return base64.b64decode(artifact["src"].split(",", 1)[1])
