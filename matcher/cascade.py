"""The runtime of the backend `cascade` (plan 85 of the workbench).

A code lookup, SAM3, SigLIP2, and the VLM cluster re-rank answer one photo. The stages
run in parallel where their inputs allow it; `cascade_run.py` holds the task graph. With
a time budget (`matcher.fast_answer`, `POST /v1/eval/predict` alone), the answer comes at
`answer_at_seconds` from the request start when an answer exists, and at
`timeout_seconds` at the latest. `service.py` parses the configuration. Read
`docs/cascade.md`.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from time import perf_counter

from .cascade_run import Budget, Run, match_pairs
from .codes import CodeTable
from .group import GroupMatchError
from .services import ScanError


CPU_WORKERS = 8
READINESS_TIMEOUT_SECONDS = 8.0


@dataclass(frozen=True)
class FastAnswer:
    """The time budget of `POST /v1/eval/predict`, in seconds from the request start."""

    enabled: bool = True
    answer_at_seconds: float = 2.9
    timeout_seconds: float = 9.5


@dataclass(frozen=True)
class BarcodeConfig:
    engine: str = "zxing-cpp"
    crops: bool = True


@dataclass(frozen=True)
class Sam3Config:
    threshold: float = 0.35
    hand: bool = True
    label: bool = True
    packages_first: bool = False


@dataclass(frozen=True)
class RerankConfig:
    model: str = "qwen3.5-9b-nvfp4"
    window: int = 10
    side: int = 1536
    max_tokens: int = 256
    timeout_seconds: float = 60.0


@dataclass(frozen=True)
class CascadeConfig:
    """The stages of one pipeline. A stage that is None is off."""

    whole_image: bool = True
    barcode: BarcodeConfig | None = None
    sam3: Sam3Config | None = None
    rerank: RerankConfig | None = None


class Cascade:
    """The data and the clients of one pipeline of the backend `cascade`."""

    def __init__(self, config, bundle, services, codes=None, rules=None,
                 cpu_workers=CPU_WORKERS):
        if config.rerank is not None and rules is None:
            raise ValueError("a re-rank needs the rule files")
        self.config = config
        self.bundle = bundle
        self.services = services
        self.codes = CodeTable(codes or {})
        self.rules = rules
        self.model = bundle.embedding["model"]
        self.extra_body = dict(bundle.embedding.get("extra_body") or {})
        self.names = {slug: card.get("name") for slug, card in (bundle.cards or {}).items()}
        self.executor = ThreadPoolExecutor(cpu_workers, thread_name_prefix="cascade")

    @property
    def cards(self):
        return self.bundle.cards

    async def start(self):
        await self.services.start()

    async def close(self):
        await self.services.close()
        self.executor.shutdown(wait=False, cancel_futures=True)

    @staticmethod
    def budget(started_at, fast_answer=None):
        """Return the budget of one request that started at `started_at` (perf_counter)."""
        if fast_answer is None or not fast_answer.enabled:
            return Budget(started_at)
        return Budget(started_at, started_at + fast_answer.answer_at_seconds,
                      started_at + fast_answer.timeout_seconds)

    async def predict(self, body, budget):
        """Return (the Top-1 slug, the audit fields). The slug is empty when the hard
        limit comes with no answer. When all stages end with no answer after an error,
        raise the first error."""
        run = Run(self, body, budget, "predict")
        answer, reason = await run.execute()
        trace = run.trace(answer, reason)
        if answer is not None and answer.pairs:
            return answer.pairs[0][0], trace
        if reason == "timeout" or not run.failures:
            return "", trace
        raise run.failures[0]

    async def match(self, body, k, budget):
        """Return (at most `k` ranked `(slug, score)` pairs of wines with a card, the
        audit fields). Scores never increase. With no answer after an error, raise the
        first error."""
        run = Run(self, body, budget, "match")
        answer, reason = await run.execute()
        trace = run.trace(answer, reason)
        if answer is None:
            if run.failures:
                raise run.failures[0]
            return [], trace
        return match_pairs(answer.pairs, self.cards, k), trace

    async def check_ready(self, probe_png):
        """Check each service of the pipeline except the VLM: one SigLIP2 embedding,
        `GET <SAM3>/health`, and `GET <scanner>/health`."""
        deadline = perf_counter() + READINESS_TIMEOUT_SECONDS
        checks = [self.services.embed([probe_png], model=self.model,
                                      extra_body=self.extra_body,
                                      dimension=self.bundle.dimension, deadline=deadline)]
        if self.config.sam3 is not None:
            checks.append(self.services.health(
                self.services.sam3_root, "SAM3 service",
                lambda status, message, detail: GroupMatchError(status, detail),
                deadline=deadline))
        if self.config.barcode is not None:
            checks.append(self.services.health(self.services.scanner_root, "QR scanner",
                                               ScanError, deadline=deadline))
        await asyncio.gather(*checks)
