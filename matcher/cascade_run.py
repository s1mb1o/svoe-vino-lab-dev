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

from . import codes as code_rules
from . import labels, photo, rerank
from .group import GroupMatchError
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
        self.crop_ranking = None
        self.whole_ranking = None
        self.vlm = {}

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
        image = self.photo if box is None else photo.crop(self.photo, box, SCAN_MARGIN)
        return photo.scaled_png(image)

    async def _segment(self, which):
        copy = await asyncio.shield(self.copy_task)
        nouns = PACKAGE_NOUNS
        if which == "full":
            nouns = (nouns + ((HAND_NOUN,) if self.config.sam3.hand else ())
                     + ((LABEL_NOUN,) if self.config.sam3.label else ()))
        instances = await self.cascade.services.segment(
            copy.jpeg, nouns=nouns, threshold=self.config.sam3.threshold,
            width=copy.image.width, height=copy.image.height,
            deadline=self.deadline("sam3"))
        package = await self.cpu(self._select, copy, instances)
        label = None
        if which == "full" and self.config.sam3.label:
            label = await self.cpu(self._label, copy, instances, package)
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
        cut = labels.cut(choice, copy, self.photo)
        if cut is None:
            return None
        image, box = cut
        return {"image": image, "box": box, "method": "crop" if choice.others else "seg"}

    async def _rank_png(self, png):
        vectors = await self.cascade.services.embed(
            [png], model=self.cascade.model, extra_body=self.cascade.extra_body,
            dimension=self.cascade.bundle.dimension, deadline=self.deadline("embed"))
        return await self.cpu(self.cascade.bundle.ranked, VIEW, vectors[0])

    async def _whole(self):
        return await self._rank_png(await self.cpu(model_png, self.photo, photo.PNG_LEVEL))

    async def _crop(self, box):
        return await self._rank_png(await self.cpu(self._crop_png, box))

    def _crop_png(self, box):
        return model_png(self.photo.crop(box), photo.PNG_LEVEL)

    async def _vlm(self, rule):
        picture = await self.cpu(self._picture)
        payload = rerank.payload(rule, picture, self.config.rerank.model,
                                 self.config.rerank.max_tokens, self.cascade.names,
                                 self.cascade.rules.descriptions)
        body = await self.cascade.services.chat(payload, deadline=self.deadline("vlm"))
        try:
            return rerank.answer_of(body)
        except ValueError as exc:
            raise VlmError(502, "VLM answer: %s" % exc, "VLM returned invalid data") from exc

    def _picture(self):
        image = self.label["image"] if self.label else self.photo
        return photo.side_png(image, self.config.rerank.side)

    # ------------------------------------------------------------------ the results

    def start(self):
        if self.config.barcode is not None:
            self.spawn("scan_full", self._scan, None)
        if self.config.sam3 is not None:
            self.copy_task = asyncio.ensure_future(self.cpu(photo.sam3_copy, self.photo))
            self.spawn("sam3_full", self._segment, "full")
            if self.config.sam3.packages_first:
                self.spawn("sam3_packages", self._segment, "packages")
        if self.config.whole_image or self.config.sam3 is None:
            self.spawn("whole", self._whole)

    def cancel(self, prefix):
        for name, task in self.tasks.items():
            if name.startswith(prefix) and not task.done():
                task.cancel()

    def set_package(self, package, final):
        if final:
            self.package_final = True
        if package is None:
            if final:
                self.package = None
                self.crop_ranking = None
                self.cancel("crop:")
                if "whole" not in self.tasks:
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
            elif name.startswith("crop:") and "whole" not in self.tasks:
                self.spawn("whole", self._whole)
            return
        if name.startswith("scan_"):
            self.codes[name] = value
        elif name == "sam3_full":
            package, self.label = value
            self.cancel("sam3_packages")
            self.set_package(package, final=True)
            if package is not None and self.config.barcode is not None \
                    and self.config.barcode.crops:
                self.spawn("scan_package", self._scan, package["crop_box"])
                if self.label is not None:
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
        self.start_vlm()

    def primary(self):
        """Return (the primary ranking, its source), or (None, None)."""
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
        self.photo = await self.cpu(photo.decode, self.body)
        self.start()
        try:
            while True:
                answer = self.decide()
                if answer is not None and answer.final:
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
            if self.copy_task is not None:
                self.copy_task.cancel()
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
                                 "box": list(self.label["box"])}
        return {"decision": decision, "stages": self.stages}
