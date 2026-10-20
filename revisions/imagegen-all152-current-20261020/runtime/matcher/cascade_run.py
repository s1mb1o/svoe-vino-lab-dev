"""The task graph of one request of the backend `cascade` (plan 85 of the workbench).

At the start, in parallel: the barcode scan of the full photo, SAM3 "full" (the package
nouns, `hand`, and `label` in one request), SAM3 "packages only" (optional), and SigLIP2
of the whole photo (optional). The first SAM3 answer with a package gives the crop
embedding. The full SAM3 answer gives the final package, its label, the scans of the
package and of the label, and the picture of the VLM re-rank.

The answer at each decision time is the first source with a result: a unique code of the
package or label scan (a final answer), a unique code of the full-photo scan, a shared
GTIN (its wines first), the re-ranked primary ranking, the primary ranking, and the
whole-photo ranking. The primary ranking is the crop ranking; with no package, it is the
whole-photo ranking.

The run stops at a final answer, when no task that can change the answer is left, at
`answer_at` when an answer exists, or at the hard limit. Then it cancels each pending
task: the HTTP client closes the connection of each pending call.
"""

import asyncio
from dataclasses import dataclass
import functools
import logging
from time import perf_counter

from PIL import Image, ImageOps

from . import codes as code_rules
from . import labels, photo, rerank
from . import selective_ocr
from .ocr import OCRError
from .group import GroupMatchError
from .input_selector import scale_box
from .main_scene import rank_packages
from .protection import ImageRejected
from .services import ScanError, ServiceError, VlmError
from .siglip2 import VIEW, Siglip2Error, model_png


LOGGER = logging.getLogger("uvicorn.error")
FAILED = object()
PACKAGE_NOUNS = ("wine bottle", "can", "packet", "box")
HAND_NOUN = "hand"
LABEL_NOUN = "label"
SAME_PACKAGE_IOU = 0.8
# The package and label scans get this margin on each side: a decoder needs the quiet
# zone around a code.
SCAN_MARGIN = 0.10
# The limits of one service call with no time budget (`POST /v1/match`).
CALL_TIMEOUTS = {"sam3": 30.0, "embed": 30.0, "scan": 10.0}
EXPECTED = (Siglip2Error, GroupMatchError, ServiceError, ImageRejected)


@dataclass(frozen=True)
class Budget:
    """The time limits of one request as `perf_counter` values. None is no limit."""

    started: float
    answer_at: float | None = None
    hard_at: float | None = None


@dataclass
class Answer:
    """One answer of `Run.decide`: its source, the ranked `(slug, score)` pairs, and
    whether no later result can change it."""

    source: str
    pairs: list
    final: bool = False
    code: dict | None = None
    rerank: dict | None = None


def _iou(a, b):
    width = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    height = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = width * height
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def code_pairs(slugs, base):
    """The code wines at score 1.0, then the ranking without them."""
    head = [(slug, 1.0) for slug in slugs]
    return head + [(slug, score) for slug, score in base or [] if slug not in slugs]


def gtin_first(base, slugs):
    """The wines of a shared GTIN first, at score 1.0: the ranked ones in rank order,
    then the unranked ones in slug order (plan 64 of the workbench). Then the others."""
    members = set(slugs)
    ranked = [slug for slug, _ in base if slug in members]
    unranked = sorted(members - set(ranked))
    return code_pairs(ranked + unranked, base)


def match_pairs(pairs, cards, k):
    """Return at most `k` pairs of wines with a card. A slug occurs one time, and the
    scores never increase: each score is clamped to [-1, 1] and to the score above it."""
    out, seen, previous = [], set(), 1.0
    for slug, score in pairs:
        if slug in seen or slug not in cards:
            continue
        seen.add(slug)
        previous = min(max(float(score), -1.0), 1.0, previous)
        out.append((slug, previous))
        if len(out) == k:
            break
    return out


class Run:
    """The stages of one request. `mode` is `predict` or `match`."""

    def __init__(self, cascade, body, budget, mode):
        self.cascade = cascade
        self.config = cascade.config
        self.body = body
        self.budget = budget
        self.mode = mode
        self.tasks = {}
        self.processed = set()
        self.stages = []
        self.failures = []
        self.photo = None
        self.copy_task = None
        self.codes = {}
        self.package = None
        self.package_number = 0
        # True when the package is known: the full SAM3 answer came, SAM3 failed, or
        # SAM3 is off. Before that, the package of `packages_first` is provisional.
        self.package_final = cascade.config.sam3 is None
        self.label = None
        self.label_ranking = None
        self.crop_ranking = None
        self.whole_ranking = None
        self.vlm = {}
        self.ocr_attempted = False
        self.ocr_pairs = None
        self.ocr_audit = None
        self.selection_audit = None

    # ------------------------------------------------------------------ the stages

    def ms(self):
        return round((perf_counter() - self.budget.started) * 1000, 1)

    async def cpu(self, function, *args):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.cascade.executor,
                                          functools.partial(function, *args))

    def deadline(self, kind):
        """The end of one service call: the hard limit with a budget, else the call
        limit of its kind."""
        if self.budget.hard_at is not None:
            return self.budget.hard_at
        limit = (self.config.rerank.timeout_seconds if kind == "vlm"
                 else CALL_TIMEOUTS[kind])
        return perf_counter() + limit

    def spawn(self, name, factory, *args):
        """Start one stage. A stage returns its value, or FAILED after an error."""
        async def stage():
            record = {"id": name, "start_ms": self.ms()}
            self.stages.append(record)
            try:
                value = await factory(*args)
            except asyncio.CancelledError:
                record.update(end_ms=self.ms(), status="cancelled")
                raise
            except EXPECTED as exc:
                record.update(end_ms=self.ms(), status="error", error=exc.detail)
                self.failures.append(exc)
                return FAILED
            except Exception as exc:  # noqa: BLE001 - a defect fails its stage alone
                LOGGER.exception("cascade stage %s failed", name)
                record.update(end_ms=self.ms(), status="error", error=type(exc).__name__)
                self.failures.append(exc)
                return FAILED
            record.update(end_ms=self.ms(), status="ok")
            return value

        self.tasks[name] = asyncio.create_task(stage(), name=name)

    async def _scan(self, box):
        png = await self.cpu(self._scan_png, box)
        instances = await self.cascade.services.scan(
            png, engine=self.config.barcode.engine, deadline=self.deadline("scan"))
        try:
            return code_rules.read(instances)
        except ValueError as exc:
            raise ScanError(502, "QR scanner answer: %s" % exc,
                            "QR scanner returned invalid data") from exc

    def _scan_png(self, box):
        if self.config.input_selector.enabled:
            image = self._recognition_photo()
            if self.label is not None and box == self.label["box"]:
                image = self.label["image"]
            # Keep the scanner quiet zone without importing a neighboring product.
            border = tuple(max(1, round(side * SCAN_MARGIN)) for side in image.size)
            image = ImageOps.expand(image, border=border, fill="white")
        else:
            image = self.photo if box is None else photo.crop(self.photo, box, SCAN_MARGIN)
        return photo.scaled_png(image)

    async def _segment(self, which):
        copy = await asyncio.shield(self.copy_task)
        nouns = (LABEL_NOUN,) if self.config.label_only else PACKAGE_NOUNS
        if which == "full":
            nouns = (nouns + ((HAND_NOUN,) if self.config.sam3.hand else ())
                     + ((LABEL_NOUN,) if self.config.sam3.label else ()))
        if self.config.input_selector.enabled:
            nouns = self.config.input_selector.nouns
        instances = await self.cascade.services.segment(
            copy.body, copy.media_type, nouns=nouns, threshold=self.config.sam3.threshold,
            width=copy.image.width, height=copy.image.height,
            deadline=self.deadline("sam3"))
        if self.config.input_selector.enabled:
            return await self.cpu(self._select_input, copy, instances)
        if self.config.label_only:
            return None, await self.cpu(self._label, copy, instances, None)
        package = await self.cpu(self._select, copy, instances)
        label = None
        if which == "full" and self.config.sam3.label:
            label = await self.cpu(self._label, copy, instances, package)
        return package, label

    def _select_input(self, copy, instances):
        """Reuse the full detector response on an aspect-correct working image.

        Selection happens at bounded resolution; recognition/scanner rectangles
        refer to the original RGB photo and retain its complete label pixels.
        """
        image = self.photo.copy()
        image.thumbnail((1600, 1600))
        result = self.config.input_selector.select(
            image, instances, detection_size=copy.image.size)
        self.selection_audit = result.as_dict(media=False)
        box = scale_box(result.crop_box, image.size, self.photo.size)
        chosen = next((c for c in result.candidates if c["id"] == result.selected_id), None)
        source = instances[chosen["source_index"]] if chosen else None
        package = {"box": tuple(source["box"]) if source else (0, 0, *copy.image.size),
                   "crop_box": box, "label": source["label"] if source else "original frame",
                   "score": source["score"] if source else 0.0}
        mask = result.keep_mask.resize(self.photo.size, Image.Resampling.NEAREST).crop(box)
        region = self.photo.crop(box)
        package["image"] = Image.composite(region, Image.new("RGB", region.size, "white"), mask)
        label = None
        if result.label_boxes:
            boxes = result.label_boxes
            combined = (min(b[0] for b in boxes), min(b[1] for b in boxes),
                        max(b[2] for b in boxes), max(b[3] for b in boxes))
            label_box = scale_box(combined, image.size, self.photo.size)
            label = {"image": self.photo.crop(label_box), "box": label_box,
                     "method": "complete-context", "parts": len(boxes)}
        return package, label

    def _select(self, copy, instances):
        """Return the selected package, or None: the first ranked package with a usable
        mask (`main_scene.rank_packages`, hand-aware when hands exist)."""
        for instance in rank_packages(copy.image, instances):
            box = photo.refined_box(instance, copy, self.photo)
            if box is not None:
                return {"box": tuple(instance["box"]), "crop_box": box,
                        "label": instance["label"], "score": instance["score"]}
        return None

    def _label(self, copy, instances, package):
        choice = labels.choose(instances, package["box"] if package else None,
                               copy.image.width, copy.image.height)
        if choice is None:
            return None
        if self.config.label_only or (self.config.crop_view == "label" and package is None):
            # Separate labels can belong to different bottles. Keep one mask.
            choice = labels.LabelChoice(choice.main, ())
        cut = labels.cut(choice, copy, self.photo)
        if cut is None:
            return None
        image, box = cut
        return {"image": image, "box": box, "method": "crop" if choice.others else "seg",
                "parts": 1 + len(choice.others)}

    async def _rank_png(self, png, view=VIEW):
        vectors = await self.cascade.services.embed(
            [png], model=self.cascade.model, extra_body=self.cascade.extra_body,
            dimension=self.cascade.bundle.dimension, deadline=self.deadline("embed"))
        return await self.cpu(self.cascade.bundle.ranked, view, vectors[0])

    async def _label_rank(self):
        png = await self.cpu(model_png, self.label["image"], photo.PNG_LEVEL)
        return await self._rank_png(png, "label")

    async def _whole(self):
        return await self._rank_png(await self.cpu(model_png, self.photo, photo.PNG_LEVEL))

    async def _crop(self, box):
        return await self._rank_png(await self.cpu(self._crop_png, box))

    def _crop_png(self, box):
        image = self._recognition_photo() if self.config.input_selector.enabled else self.photo.crop(box)
        return model_png(image, photo.PNG_LEVEL)

    async def _vlm(self, rule):
        picture = await self.cpu(self._picture)
        payload = rerank.payload(rule, picture, self.config.rerank.model,
                                 self.config.rerank.max_tokens, self.cascade.names,
                                 self.cascade.rules.descriptions,
                                 self.config.rerank.thinking_field)
        body = await self.cascade.services.chat(payload, deadline=self.deadline("vlm"))
        try:
            return rerank.answer_of(body)
        except ValueError as exc:
            raise VlmError(502, "VLM answer: %s" % exc, "VLM returned invalid data") from exc

    def _recognition_photo(self):
        if self.config.input_selector.enabled and self.package is not None:
            return self.package["image"]
        return self.photo

    def _picture(self):
        image = self.label["image"] if self.label else self._recognition_photo()
        png = photo.side_png(image, self.config.rerank.side)
        return rerank.jpeg_of(png) if self.config.rerank.format == "jpg" else png

    async def _selective_ocr(self, answer, deadline):
        settings = self.config.selective_ocr
        try:
            async with asyncio.timeout(max(0, deadline - perf_counter())):
                image = self._recognition_photo()
                actual_input = "full"
                if settings.input == "label" and self.label is not None:
                    image, actual_input = self.label["image"], "label"
                png = await self.cpu(photo.side_png, image, settings.side)
                result = await self.cascade.ocr.read(png, deadline)
                self.ocr_audit.update(input=actual_input, text=result.text,
                                      word_count=len(result.words), cached=result.cached)
                if not result.text:
                    self.ocr_audit.update(status="empty", reason="no_readable_text")
                    return None
                # Reuse the visual ranking. OCR does not add another embedding call.
                visual, source = self.primary()
                visual = visual or self.whole_ranking or answer.pairs
                members = set(answer.code["slugs"]) if answer.code is not None else None
                pool = [(slug, score) for slug, score in visual if slug in self.cascade.cards
                        and (members is None or slug in members)][:settings.pool]
                if members is not None:
                    included = {slug for slug, _ in pool}
                    pool += [(slug, score) for slug, score in answer.pairs
                             if slug in members and slug not in included]
                    pool = pool[:settings.pool]
                pairs, details = await self.cpu(selective_ocr.rank, pool, result.text,
                                               self.cascade.cards, settings, deadline)
                if not pairs:
                    self.ocr_audit.update(status="empty", reason="no_visual_candidates")
                    return None
                if not any(row["ocr_score"] > 0 for row in details):
                    self.ocr_audit.update(status="no_match", reason="no_candidate_text_support")
                    return None
                selected = {slug for slug, _ in pairs}
                tail = [(slug, score) for slug, score in answer.pairs if slug not in selected]
                self.ocr_audit.update(status="applied", pool_source=source or answer.source,
                                      pool_count=len(pool), candidates=details[:10],
                                      selected_top1=pairs[0][0],
                                      changed=pairs[0][0] != answer.pairs[0][0])
                return pairs + tail
        except asyncio.CancelledError:
            self.ocr_audit.update(status="cancelled", reason="request_limit")
            raise
        except TimeoutError as exc:
            self.ocr_audit.update(status="error", reason="timeout")
            raise OCRError(504, "selective OCR deadline expired", "OCR request timed out") from exc
        except Exception as exc:
            self.ocr_audit.update(status="error", reason=type(exc).__name__)
            raise

    def start_ocr(self, answer):
        """Start once, after the useful barcode, embedding and verification stages end."""
        if self.cascade.ocr is None or self.ocr_attempted:
            return False
        self.ocr_attempted = True
        settings = self.config.selective_ocr
        verification = selective_ocr.evidence(self, answer)
        triggered = selective_ocr.trigger(answer.pairs if answer else [], verification, settings)
        self.ocr_audit = {"backend": settings.ocr.backend, "triggered": triggered,
                          "evidence": verification, "status": "skipped",
                          "reason": "trigger_not_met"}
        if not triggered:
            return False
        now = perf_counter()
        limits = [now + settings.timeout_seconds]
        limits += [t for t in (self.budget.answer_at, self.budget.hard_at) if t is not None]
        deadline = min(limits)
        if deadline <= now:
            self.ocr_audit.update(reason="no_remaining_budget")
            return False
        self.ocr_audit.update(status="running", reason="uncertain_answer",
                              original_top1=answer.pairs[0][0])
        self.spawn("ocr", self._selective_ocr, answer, deadline)
        return True

    # ------------------------------------------------------------------ the results

    def start(self):
        if self.config.barcode is not None and not self.config.input_selector.enabled:
            self.spawn("scan_full", self._scan, None)
        if self.config.sam3 is not None:
            sam3 = self.config.sam3
            self.copy_task = asyncio.ensure_future(self.cpu(
                photo.sam3_copy, self.photo, sam3.input_size, sam3.upscale_small, sam3.format))
            which = "label" if self.config.label_only else "full"
            self.spawn("sam3_" + which, self._segment, which)
            if self.config.sam3.packages_first:
                self.spawn("sam3_packages", self._segment, "packages")
        if (not self.config.input_selector.enabled
                and (self.config.whole_image or self.config.sam3 is None)):
            self.spawn("whole", self._whole)

    def cancel(self, prefix):
        for name, task in self.tasks.items():
            if name.startswith(prefix) and not task.done():
                task.cancel()

    def set_package(self, package, final):
        if final:
            self.package_final = True
        if self.config.crop_view == "label":
            self.package = package
            return
        if package is None:
            if final:
                self.package = None
                self.crop_ranking = None
                self.cancel("crop:")
                if "whole" not in self.tasks and not self.config.input_selector.enabled:
                    self.spawn("whole", self._whole)
            return
        if self.package is not None and _iou(self.package["box"], package["box"]) >= SAME_PACKAGE_IOU:
            return
        self.cancel("crop:")
        self.crop_ranking = None
        self.package = package
        self.package_number += 1
        self.spawn("crop:%d" % self.package_number, self._crop, package["crop_box"])

    def on_done(self, name, value):
        if value is FAILED:
            if name == "sam3_full":
                self.set_package(self.package, final=True)
            elif (name.startswith("crop:") and "whole" not in self.tasks
                  and not self.config.input_selector.enabled):
                self.spawn("whole", self._whole)
            return
        if name.startswith("scan_"):
            self.codes[name] = value
        elif name == "sam3_label":
            self.package_final = True
            _, self.label = value
            if self.label is not None:
                self.spawn("label", self._label_rank)
        elif name == "label":
            self.label_ranking = value
        elif name == "sam3_full":
            package, self.label = value
            self.cancel("sam3_packages")
            self.set_package(package, final=True)
            if self.config.crop_view == "label" and self.label is not None:
                self.spawn("label", self._label_rank)
            if (package is not None and self.config.barcode is not None
                    and (self.config.barcode.crops or self.config.input_selector.enabled)):
                self.spawn("scan_package", self._scan, package["crop_box"])
                if self.label is not None and self.config.barcode.crops:
                    self.spawn("scan_label", self._scan, self.label["box"])
        elif name == "sam3_packages":
            if not self.package_final and value[0] is not None:
                self.set_package(value[0], final=False)
        elif name == "whole":
            self.whole_ranking = value
        elif name == "crop:%d" % self.package_number:
            self.crop_ranking = value
        elif name.startswith("vlm:"):
            self.vlm[name[4:]] = value
        elif name == "ocr":
            self.ocr_pairs = value
        self.start_vlm()

    def primary(self):
        """Return (the primary ranking, its source), or (None, None)."""
        if self.config.label_only or self.config.crop_view == "label":
            return self.label_ranking, "label"
        if self.crop_ranking is not None:
            return self.crop_ranking, "crop"
        if self.package_final and self.package is None and self.whole_ranking:
            return self.whole_ranking, "whole"
        return None, None

    def hits(self):
        """Return (the hit of the package and label codes, its scan, the hit of the
        full-photo codes)."""
        table = self.cascade.codes
        package_codes = self.codes.get("scan_package", [])
        crop = table.find(package_codes + self.codes.get("scan_label", []))
        scan = None
        if crop is not None:
            keys = {(hit["source"], hit["code"]) for hit in table.hits(package_codes)}
            scan = "package" if (crop["source"], crop["code"]) in keys else "label"
        return crop, scan, table.find(self.codes.get("scan_full", []))

    def reranked(self, pairs, first):
        """Return (the pairs re-ranked by a finished VLM answer, the explain record), or
        (None, None)."""
        if self.config.rerank is None or not pairs:
            return None, None
        rule, positions = self.cascade.rules.trigger(pairs, self.config.rerank.window, first)
        if rule is None or rule["key"] not in self.vlm:
            return None, None
        window = [pairs[position][0] for position in positions]
        ranking = rerank.window_ranking(rule, self.vlm[rule["key"]], window)
        return rerank.reorder(pairs, positions, ranking), {
            "cluster": rule["key"], "mode": rule["mode"], "window": window,
            "changed": ranking[0] != window[0]}

    def decide(self):
        answer = self.base_decision()
        if self.ocr_pairs is not None and answer is not None:
            return Answer("selective_ocr", self.ocr_pairs, code=answer.code,
                          rerank=answer.rerank)
        return answer

    def base_decision(self):
        base, source = self.primary()
        explain = None
        if base:
            new, explain = self.reranked(base, None)
            if new is not None:
                base, source = new, "rerank"
        elif self.whole_ranking:
            base, source = self.whole_ranking, "whole"
        crop, scan, full = self.hits()
        if code_rules.is_unique(crop):
            return Answer("code_" + scan, code_pairs(crop["slugs"], base), final=True,
                          code=crop)
        if code_rules.is_unique(full):
            return Answer("code_full", code_pairs(full["slugs"], base), code=full)
        shared = crop or full
        if shared is not None:
            primary, _ = self.primary()
            pairs = gtin_first(primary or base or [], shared["slugs"])
            new, gtin_explain = self.reranked(pairs, shared["slugs"])
            return Answer("gtin", new or pairs, code=shared, rerank=gtin_explain)
        if base:
            return Answer(source, base, rerank=explain if source == "rerank" else None)
        return None

    def start_vlm(self):
        """Start the VLM for the rule that the primary ranking triggers now."""
        if self.config.rerank is None or not self.package_final:
            return
        crop, _, full = self.hits()
        if code_rules.is_unique(crop) or code_rules.is_unique(full):
            return
        pairs, _ = self.primary()
        first = None
        shared = crop or full
        if shared is not None and pairs:
            first = shared["slugs"]
            pairs = gtin_first(pairs, first)
        if not pairs:
            return
        rule, _ = self.cascade.rules.trigger(pairs, self.config.rerank.window, first)
        if rule is not None and "vlm:" + rule["key"] not in self.tasks:
            self.spawn("vlm:" + rule["key"], self._vlm, rule)

    def useful(self, name, answer):
        """Tell whether a pending task can still change the answer."""
        unique = answer is not None and answer.code is not None \
            and code_rules.is_unique(answer.code)
        if name == "sam3_packages":
            return not self.package_final
        if name == "whole":
            # The provisional package of `packages_first` can fall away in the full SAM3
            # answer. Keep the whole photo until the package is final.
            return (not (self.mode == "predict" and unique)
                    and (self.crop_ranking is None or not self.package_final))
        if name.startswith("crop:"):
            return not (self.mode == "predict" and unique)
        if name.startswith("vlm:"):
            if unique:
                return False
            pairs, _ = self.primary()
            first = None
            if answer is not None and answer.source == "gtin":
                first = answer.code["slugs"]
                pairs = gtin_first(pairs or [], first)
            rule, _ = self.cascade.rules.trigger(pairs or [], self.config.rerank.window,
                                                 first)
            return rule is not None and name == "vlm:" + rule["key"]
        return True

    # ------------------------------------------------------------------ the loop

    def collect(self):
        """Handle each finished task one time, in start order."""
        for name, task in list(self.tasks.items()):
            if name in self.processed or not task.done():
                continue
            self.processed.add(name)
            if not task.cancelled():
                self.on_done(name, task.result())

    async def execute(self):
        """Return (the answer or None, the reason: final, done, answer_at, or timeout).
        Raise ImageRejected for an image that does not decode."""
        if self.budget.hard_at is None:
            self.photo = await self.cpu(photo.decode, self.body)
        else:
            remaining = self.budget.hard_at - perf_counter()
            if remaining <= 0:
                return None, "timeout"
            try:
                async with asyncio.timeout(remaining):
                    self.photo = await self.cpu(photo.decode, self.body)
            except TimeoutError:
                # A running CPU operation cannot be stopped. Cancel its future and
                # return without starting model calls or waiting for its thread.
                return None, "timeout"
            if perf_counter() >= self.budget.hard_at:
                return None, "timeout"
        self.start()
        try:
            while True:
                answer = self.decide()
                now = perf_counter()
                if self.budget.hard_at is not None and now >= self.budget.hard_at:
                    return answer, "timeout"
                if answer is not None and answer.final:
                    self.start_ocr(answer)
                    return answer, "final"
                live = []
                for name, task in self.tasks.items():
                    if task.done():
                        continue
                    if self.useful(name, answer):
                        live.append(task)
                    else:
                        task.cancel()
                if not live:
                    if self.start_ocr(answer):
                        continue
                    return answer, "done"
                now = perf_counter()
                if self.budget.hard_at is not None and now >= self.budget.hard_at:
                    return answer, "timeout"
                if (self.budget.answer_at is not None and now >= self.budget.answer_at
                        and answer is not None):
                    return answer, "answer_at"
                wake = [limit for limit in (self.budget.answer_at, self.budget.hard_at)
                        if limit is not None and limit > now]
                await asyncio.wait(live, timeout=min(wake) - now if wake else None,
                                   return_when=asyncio.FIRST_COMPLETED)
                self.collect()
        finally:
            pending = [task for task in self.tasks.values() if not task.done()]
            for task in pending:
                task.cancel()
            if self.copy_task is not None and not self.copy_task.done():
                self.copy_task.cancel()
                pending.append(self.copy_task)
            if pending:
                await asyncio.wait(pending, timeout=1.0)

    def trace(self, answer, reason):
        """Return the audit fields of the run."""
        decision = {"source": answer.source if answer else "none", "reason": reason,
                    "answered_ms": self.ms()}
        if answer is not None and answer.code is not None:
            decision["code"] = {key: answer.code[key]
                                for key in ("source", "code", "read", "format", "slugs")}
        if answer is not None and answer.rerank is not None:
            decision["rerank"] = answer.rerank
        if self.package is not None:
            decision["package"] = {"label": self.package["label"],
                                   "box": list(self.package["crop_box"])}
        if self.label is not None:
            decision["label"] = {"method": self.label["method"],
                                 "box": list(self.label["box"]),
                                 "parts": self.label["parts"]}
        if self.ocr_audit is not None:
            decision["selective_ocr"] = self.ocr_audit
        if self.selection_audit is not None:
            decision["input_selector"] = self.selection_audit
        return {"decision": decision, "stages": self.stages}
