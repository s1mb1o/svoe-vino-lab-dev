"""The steps of one photo of a run, for the step popup of `/runs` (plan 41).

`GET /api/run-steps?id=<run>&query=<query id>` answers the rounds and the steps of one
row of `results.jsonl`. The page draws them as the step view of `drink-atlas-recognize`.

- An embedding run (`backend.kind: embedding`): the photo, the SAM3 cuts, the steps of
  each view, the embedding, the search in the space of each view, and the score. A row of
  a run after plan 41 holds the key `trace` (`embedding_run.Trace`): the time and the
  result of each step. The images are made again from the SAM3 answers of
  `data/cache/sam3/` with the code of the run, and each model input is checked against
  the sha256 of the trace. An older row has no time.
- A matcher run (`svoe-vino-matcher`): the photo, the model inputs of the matcher, the
  request, and the re-rank steps of its `explain` records, with the order before each.
- Another run: the photo and the answer of the backend.

The module reads files and the lab database. It writes nothing and sends no request.
"""
import hashlib
import io
import os
import re
import sqlite3
import sys
import urllib.parse
from contextlib import closing
from pathlib import Path

import alternatives
import build_embeddings
import derive
import embedding_run
import embeddings
import labdb
import run_files

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MATCHER_ROOT = os.path.join(os.path.dirname(ROOT), "svoe-vino-matcher")
# The gx10 gateway of the embedding and SAM3 calls (Admin/GPU_SERVERS.md).
GATEWAY_HOST = "192.168.86.14:18081"
MATCHER_PATH = re.compile(r"/v1/pipelines/([^/]+)/predict$")
# The long side of a cut image in the popup. A model input keeps its size.
CUT_SIDE = 1024
NO_TIME = "The run recorded no step time. A run after plan 41 records it."
NO_SPACE_LIST = ("The run kept no top list of this space. The list shows the candidates of "
                 "the answer by their cosine in this space.")

PHOTO_NOTE = "the photo as it came"
EMBEDDING_ROUNDS = (PHOTO_NOTE,
                    "the model inputs: the SAM3 cuts and the steps of each view",
                    "the embedding and the search: each view searches its own space")
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


class Photo:
    """The photo of one row: its URL, its file in the image store, and its opened image."""

    def __init__(self, conn, db_path, row):
        digest = str(row.get("image_sha256") or "")
        hit = conn.execute("SELECT folder, extension FROM image WHERE sha256 = ?",
                           (digest,)).fetchone() if digest else None
        self.extension = hit[1] if hit else None
        self.url = "/images/%s/%s.%s" % (hit[0], digest, hit[1]) if hit else None
        self.path = (os.path.join(labdb.image_store(db_path), hit[0],
                                  "%s.%s" % (digest, hit[1])) if hit else None)
        self.image, self.error = None, None
        if not self.path:
            self.error = "the photo of this query is not in the lab image store"
            return
        try:
            self.image, _icc = derive.open_image(self.path)
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

    def __init__(self, conn, row, card_images):
        self.row = row
        self.conn = conn
        self.card_images = card_images
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
            cards = self.card_images(self.conn)
            names = dict(self.conn.execute(
                "SELECT wine_slug, name FROM wine_catalog WHERE wine_slug IN (%s)"
                % ", ".join("?" for _ in self.slugs), sorted(self.slugs)))
        except sqlite3.Error:
            return  # the cards are a help; the slugs still stand
        for one in rounds:
            for part in one["steps"]:
                for group in part["lists"]:
                    for item in group["items"]:
                        card = cards.get(item["slug"]) or {}
                        item["image"] = item["image"] or (card.get("_patch_image_url")
                                                          or card.get("main_image_url"))
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
    """Return (sha256, view) -> embedding_hash of the present index of the entry, and the
    image file names of its directory."""
    try:
        directory = embeddings.entry_dir(db_path, name)
        index = embeddings.read_index(directory) or {}
        names = embeddings.image_names(directory)
    except (OSError, ValueError):
        return {}, set()
    return ({(item["source_sha256"], item["view"]): item["embedding_hash"]
             for item in index.get("items", [])}, names)


def _cut(photo, target, endpoint, scene_selection=False):
    """Return `(box, image, reason, result)` for one cached SAM3 target."""
    if photo.image is None:
        return None, None, photo.error, None
    try:
        trace = embedding_run.Trace()
        cut = embedding_run.cuts_of(
            photo.image, {target}, embedding_run.CachedSam3(endpoint), trace,
            scene_selection=scene_selection and target == "package").get(target)
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
    scene_selection = bool(spec.get("scene_selection"))
    name = spec.get("embedding") or spec.get("id")
    first = step("input", "Input photo")
    timed(first, records.get(("input", None)))
    first["artifacts"] = [a for a in [photo.artifact("00-input.%s" % (photo.extension or "jpg"))]
                          if a]
    first["result"] = first["result"] or photo.head(row)
    first["settings"] = {"photo": row.get("image_path"), "sha256": row.get("image_sha256")}
    if photo.error:
        first["notes"].append(photo.error)
    rounds = [[first], [], []]

    # A pipeline with the key `barcode` decodes the photo first. A code of `wine_code`
    # answers the photo, and no embedding model runs: its candidates hold the key `code`.
    code = records.get(("barcode", None))
    code_answer = any(isinstance(c, dict) and "code" in c for c in row.get("candidates") or ())
    if code or code_answer:
        part = step("barcode", "Decode codes, whole photo", "local", "zxing-cpp")
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

    cuts = {}
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
        box, processed, reason, replayed = _cut(photo, target, endpoint, scene_selection)
        cuts[target] = (box, processed) if box is not None else None
        part["settings"] = {"endpoint": endpoint, "texts": texts, "rule": rule}
        if reason:
            part["notes"].append(reason)
        if box is not None:
            number = len(rounds[0]) + len(rounds[1])
            box_art = photo.artifact("%02d-%s-box.%s" % (number, target, photo.extension or "jpg"),
                                     [box])
            part["artifacts"] = [a for a in [box_art] if a] + [{
                "src": png_uri(processed, CUT_SIDE), "caption": "%02d-%s-cut.png · %d × %d" % (
                    number, target, processed.width, processed.height),
                "width": processed.width, "height": processed.height, "boxes": [],
                "check": None, "alpha": processed.mode == "RGBA"}]
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
        rounds[1].append(part)

    for view, steps in views.items():
        chain = " → ".join(s.get("step", "?") for s in steps)
        part = step("view", "View %s" % view, "local", None, chain, view=view)
        record = records.get(("view", view))
        timed(part, record)
        part["settings"] = {"steps": steps}
        if photo.image is None:
            part["notes"].append(photo.error)
            rounds[1].append(part)
            continue
        target = embedding_run.segment_target(steps)
        if target is not None and cuts.get(target) is None:
            if part["state"] != "skipped":
                part["notes"].append("The model input needs the %s cut, which cannot be "
                                     "shown." % target)
            rounds[1].append(part)
            continue
        try:
            prepared, reason = embedding_run.view_input(photo.image, steps, cuts)
        except embeddings.ItemError as exc:
            prepared, reason = None, str(exc)
        if prepared is None:
            if reason and reason not in part["notes"]:
                part["notes"].append(reason)
            rounds[1].append(part)
            continue
        data = embeddings.png_bytes(prepared)
        digest = hashlib.sha256(data).hexdigest()
        recorded = ((record or {}).get("out") or {}).get("sha256")
        check = None if not recorded else ("same" if recorded == digest else "changed")
        number = len(rounds[0]) + len(rounds[1])
        part["artifacts"] = [{"src": build_embeddings.data_uri(data),
                              "caption": "%02d-view-%s.png · %d × %d" % (
                                  number, view, prepared.width, prepared.height),
                              "width": prepared.width, "height": prepared.height,
                              "boxes": [], "check": check, "sha256": digest}]
        if check == "changed":
            part["notes"].append("The model input made again differs from the input of the "
                                 "run: the code, the cache, or the photo changed.")
        if not part["result"]:
            part["result"] = {"width": prepared.width, "height": prepared.height,
                              "bytes": len(data), "sha256": digest}
        rounds[1].append(part)

    local = spec.get("model_backend") == "local"
    embed = step("embed", "Embedding", "local" if local else service_of(spec.get("url")),
                 spec.get("model"))
    timed(embed, records.get(("embed", None)))
    embed["settings"] = {"model": spec.get("model"), "model_backend": spec.get("model_backend"),
                         "url": spec.get("url"), "extra_body": spec.get("extra_body")}
    rounds[2].append(embed)

    present, names = _index_state(ctx.db_path, name) if name else ({}, set())
    cands = row.get("candidates") or []
    searched = [view for view in views if (("search", view) in records
                                           or any(view in c for c in cands))]
    for view in searched:
        part = step("search", "Search, space %s" % view, "local", name, "view %s" % view,
                    view=view)
        record = records.get(("search", view))
        timed(part, record)
        part["settings"] = {"index": name, "view": view, "top_k": spec.get("top_k")}
        top = ((record or {}).get("out") or {}).get("top")
        if isinstance(top, list):
            items = []
            for rank, hit in enumerate(top, 1):
                image = None
                key = (hit.get("sha256"), view)
                if (present.get(key) == hit.get("embedding_hash")
                        and embeddings.image_name(*key) in names):
                    image = _item_url(name, hit["sha256"], view, hit["embedding_hash"])
                items.append(lists.item(hit.get("slug"), rank, hit.get("cosine"),
                                        image=image, detail="%s · %s" % (view, hit.get("type"))))
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

    score = step("score", "Score", "local")
    timed(score, records.get(("score", None)))
    score["settings"] = {"score": spec.get("score")}
    score["lists"] = [answer_list(lists, row, "the answer", detail=lambda c: " · ".join(
        "%s %s" % (view, _cos(c.get(view))) for view in searched) or None)]
    rounds[2].append(score)
    if not trace:
        ctx.notes.append(NO_TIME)
    return [(EMBEDDING_ROUNDS[i], steps) for i, steps in enumerate(rounds) if steps]


def _item_url(name, digest, view, embedding_hash):
    """Return the URL of the PNG of one catalogue item of the index of `name`."""
    import embedding_routes  # here alone: the URL of a prepared image
    return embedding_routes.image_url(name, digest, view, embedding_hash)


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
    def __init__(self, db_path, conn, row, spec, kind, card_images):
        self.db_path, self.conn, self.row, self.spec, self.kind = db_path, conn, row, spec, kind
        self.photo = Photo(conn, db_path, row)
        self.lists = Lists(conn, row, card_images)
        self.notes = []


def steps_view(runs_dir, db_path, run_id, query_id, card_images):
    """Return the answer of `/api/run-steps`. Raise `StepError`."""
    if run_id not in run_files.run_dirs(runs_dir):
        raise StepError(404, "unknown run")
    row = run_files.run_result(runs_dir, run_id, query_id)
    if row is None:
        raise StepError(404, "unknown query")
    meta = run_files.read_json(run_files.run_path(runs_dir, run_id, "run.json")) or {}
    spec = meta.get("backend") if isinstance(meta.get("backend"), dict) else {}
    kind = run_kind(spec)
    try:
        conn = sqlite3.connect(Path(os.path.abspath(db_path)).as_uri() + "?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise StepError(503, "cannot read the lab database: %s" % exc)
    with closing(conn):
        ctx = Context(db_path, conn, row, spec, kind, card_images)
        built = BUILDERS[kind](ctx)
        rounds, number = [], 0
        for n, (note, steps) in enumerate(built):
            for part in steps:
                part["n"] = number
                number += 1
            rounds.append({"n": n, "title": "Round %d" % n, "note": note, "steps": steps})
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
