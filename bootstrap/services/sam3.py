"""SAM3 HTTP service for the portable hackathon bootstrap.

The compatibility gateway forwards ``/upstream/sam3`` to this loopback service.
The service reads a local model snapshot and does not contact Hugging Face.

Concurrency model (2026-09-22, replaces one global lock):

  request thread   decode JPEG, run the processor, build prompts   <- parallel
        |          submit one job, wait
  worker thread    GPU: batched vision encode, per-noun decode     <- WORKERS at a time
        |          hand back CPU tensors
  request thread   mask -> PNG, build the response                 <- parallel

`--workers` sets how many batches run at once. `--batch-size` sets how many
images share one vision-encoder pass; `--batch-wait-ms` is how long a worker
waits to fill a batch. `--batch-size 1` reproduces the old one-at-a-time
behaviour without the lock.

Precision defaults to fp16 (2026-09-22). On GB10 that is ~2.9x faster than the
fp32 checkpoint at 1008x1008, and agreement is tight: same instance count, mask
areas identical, scores within 0.0005. Pass `--dtype fp32` to reproduce the old
numbers exactly. The whole model is cast once at load - this is not autocast, so
the GB10 mixed-precision dtype mismatches reported elsewhere do not apply.

Batching is exact, not approximate: a batched encode sliced back per image is
bit-identical to a single-image encode (verified on gx10, max abs diff 0.0).
"""

import argparse
import base64
import io
import json
import math
import os
import queue
import threading
import time
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import torch
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse
from PIL import Image
from pydantic import BaseModel, Field
from transformers import (
    Sam3Model,
    Sam3Processor,
    Sam3TrackerModel,
    Sam3TrackerProcessor,
)

MODEL_ID = os.environ.get("SAM3_MODEL", "facebook/sam3")
DTYPES = {
    "fp32": torch.float32,
    "float32": torch.float32,
    "fp16": torch.float16,
    "float16": torch.float16,
}


@dataclass
class Config:
    """Runtime knobs. Every one has an SAM3_* environment variable and a CLI flag."""

    host: str = os.environ.get("SAM3_HOST", "127.0.0.1")
    port: int = int(os.environ.get("SAM3_PORT", "7860"))
    model: str = MODEL_ID
    device: str = os.environ.get("BOOTSTRAP_DEVICE", "auto")
    workers: int = int(os.environ.get("SAM3_WORKERS", "1"))
    batch_size: int = int(os.environ.get("SAM3_BATCH_SIZE", "4"))
    batch_wait_ms: float = float(os.environ.get("SAM3_BATCH_WAIT_MS", "15"))
    dtype: str = os.environ.get("SAM3_DTYPE", "fp16")
    job_timeout: float = float(os.environ.get("SAM3_JOB_TIMEOUT", "600"))
    stats_window: float = float(os.environ.get("SAM3_STATS_WINDOW", "300"))


CONFIG = Config()

def _select_device(requested: str) -> str:
    if requested != "auto":
        if requested == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("CUDA was requested but is not available")
        if requested == "mps" and not torch.backends.mps.is_available():
            raise RuntimeError("MPS was requested but is not available")
        if requested not in {"cuda", "mps", "cpu"}:
            raise RuntimeError(f"unknown device {requested!r}")
        return requested
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


device = _select_device(CONFIG.device)
model = None
processor = None
# The tracker head is a second model over the same checkpoint, loaded lazily on
# the first /segment_point so that /segment consumers keep today's cold start.
tracker_model = None
tracker_processor = None
_tracker_load_lock = threading.Lock()


# ----------------------------------------------------------------------------- stats


class Stats:
    """Rolling window over completed batches and requests, for /stats and the UI."""

    def __init__(self, window: float) -> None:
        self.window = window
        self._lock = threading.Lock()
        self._batches: deque[tuple[float, float, int]] = deque()   # (t_end, seconds, images)
        self._requests: deque[tuple[float, float, float]] = deque()  # (t_end, wait, total)
        self._started = time.monotonic()
        self.queued = 0
        self.running = 0

    def _prune(self, now: float) -> None:
        cutoff = now - self.window
        while self._batches and self._batches[0][0] < cutoff:
            self._batches.popleft()
        while self._requests and self._requests[0][0] < cutoff:
            self._requests.popleft()

    def enqueued(self) -> None:
        with self._lock:
            self.queued += 1

    def started(self, images: int) -> None:
        with self._lock:
            self.queued -= images
            self.running += images

    def finished_batch(self, seconds: float, images: int) -> None:
        now = time.monotonic()
        with self._lock:
            self.running -= images
            self._batches.append((now, seconds, images))
            self._prune(now)

    def finished_request(self, wait: float, total: float) -> None:
        now = time.monotonic()
        with self._lock:
            self._requests.append((now, wait, total))
            self._prune(now)

    def snapshot(self) -> dict[str, Any]:
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            batches = list(self._batches)
            requests = list(self._requests)
            queued, running = self.queued, self.running
            elapsed = min(self.window, now - self._started)
        busy = sum(seconds for _, seconds, _ in batches)
        images = sum(count for _, _, count in batches)
        span = max(elapsed, 1e-6)
        load = 100.0 * busy / (span * CONFIG.workers)
        return {
            "workers": CONFIG.workers,
            "batch_size": CONFIG.batch_size,
            "batch_wait_ms": CONFIG.batch_wait_ms,
            "dtype": CONFIG.dtype,
            "device": device,
            "queued": max(queued, 0),
            "running": max(running, 0),
            "window_seconds": round(span, 1),
            "requests": len(requests),
            "requests_per_minute": round(60.0 * len(requests) / span, 2),
            "batches": len(batches),
            "avg_batch_size": round(images / len(batches), 2) if batches else 0.0,
            "avg_queue_wait_ms": round(1000.0 * sum(w for _, w, _ in requests) / len(requests), 1) if requests else 0.0,
            "avg_latency_ms": round(1000.0 * sum(t for _, _, t in requests) / len(requests), 1) if requests else 0.0,
            "load_percent": round(min(max(load, 0.0), 100.0), 1),
        }


STATS = Stats(CONFIG.stats_window)


# ----------------------------------------------------------------------------- queue


@dataclass
class _Job:
    """One unit of GPU work. `kind` decides which code path the worker takes."""

    kind: str                       # "text" | "box" | "point"
    payload: dict[str, Any]
    done: threading.Event = field(default_factory=threading.Event)
    result: Any = None
    error: BaseException | None = None
    t_submit: float = 0.0
    t_start: float = 0.0


_SHUTDOWN = _Job(kind="shutdown", payload={})
_jobs: "queue.Queue[_Job]" = queue.Queue()
_workers: list[threading.Thread] = []


def _submit(job: _Job) -> Any:
    """Queue one job, block until a worker finishes it, re-raise its error here."""
    job.t_submit = time.monotonic()
    STATS.enqueued()
    _jobs.put(job)
    if not job.done.wait(timeout=CONFIG.job_timeout):
        raise HTTPException(
            status_code=503,
            detail=f"request still queued after {CONFIG.job_timeout:g}s",
        )
    if job.error is not None:
        raise job.error
    STATS.finished_request(job.t_start - job.t_submit, time.monotonic() - job.t_submit)
    return job.result


def _slice_vision(vision: Any, index: int, total: int) -> Any:
    """One image's features out of a batched Sam3VisionEncoderOutput.

    Verified on gx10: slicing a batched encode gives exactly the tensors a
    single-image encode produces (max abs diff 0.0), so batching never changes
    a result.
    """
    if total == 1:
        return vision
    return type(vision)(
        last_hidden_state=vision.last_hidden_state[index:index + 1],
        fpn_hidden_states=tuple(t[index:index + 1] for t in vision.fpn_hidden_states),
        fpn_position_encoding=tuple(t[index:index + 1] for t in vision.fpn_position_encoding),
    )


def _cast_inputs(inputs, dtype):
    """Cast every float tensor to the weight dtype, not just `pixel_values`.

    Box and point coordinates go through their own linear projections
    (`boxes_direct_project`), and `F.linear` rejects a Float input against Half
    weights with "mat1 and mat2 must have the same dtype". Integer tensors such
    as `original_sizes` and `input_boxes_labels` are left alone.
    """
    if dtype == torch.float32:
        return inputs
    for key, value in list(inputs.items()):
        if isinstance(value, torch.Tensor) and value.is_floating_point():
            inputs[key] = value.to(dtype)
    return inputs


def _cpu_results(results: dict) -> dict:
    """Move one post-processed result off the GPU so the worker can move on."""
    out = {"masks": results["masks"].cpu(), "scores": results["scores"].cpu()}
    if "boxes" in results:
        out["boxes"] = results["boxes"].cpu()
    return out


def _run_text_batch(jobs: list[_Job]) -> None:
    """One vision-encoder pass for the whole batch, then a decoder pass per noun."""
    pixel_values = torch.cat([job.payload["pixel_values"] for job in jobs])
    pixel_values = pixel_values.to(device, dtype=model.dtype)
    with torch.no_grad():
        vision = model.get_vision_features(pixel_values=pixel_values)
        for index, job in enumerate(jobs):
            embeds = _slice_vision(vision, index, len(jobs))
            per_noun = []
            for noun, text_inputs in job.payload["prompts"]:
                outputs = model(
                    vision_embeds=embeds,
                    input_ids=text_inputs["input_ids"].to(device),
                    attention_mask=(
                        text_inputs["attention_mask"].to(device)
                        if "attention_mask" in text_inputs else None
                    ),
                )
                results = processor.post_process_instance_segmentation(
                    outputs,
                    threshold=job.payload["threshold"],
                    mask_threshold=job.payload["mask_threshold"],
                    target_sizes=job.payload["target_sizes"],
                )[0]
                per_noun.append((noun, _cpu_results(results)))
            job.result = per_noun


def _run_box(job: _Job) -> None:
    """Box-prompted segmentation. Never batched: the box goes through the processor
    together with the image, so it does not share a vision pass with other jobs."""
    inputs = _cast_inputs(job.payload["inputs"].to(device), model.dtype)
    with torch.no_grad():
        outputs = model(**inputs)
    results = processor.post_process_instance_segmentation(
        outputs,
        threshold=job.payload["threshold"],
        mask_threshold=job.payload["mask_threshold"],
        target_sizes=job.payload["target_sizes"],
    )[0]
    job.result = [(None, _cpu_results(results))]


def _run_point(job: _Job) -> None:
    """Click-prompted segmentation through the tracker head. Never batched."""
    inputs = _cast_inputs(job.payload["inputs"].to(device), tracker_model.dtype)
    with torch.no_grad():
        outputs = tracker_model(**inputs, multimask_output=job.payload["multimask"])
    # (num_objects, num_masks, H, W) at the ORIGINAL frame size.
    masks = tracker_processor.post_process_masks(
        outputs.pred_masks.cpu().float(),
        job.payload["original_sizes"],
        mask_threshold=job.payload["logit_threshold"],
    )[0][0]
    job.result = {
        "masks": masks,
        "scores": outputs.iou_scores[0, 0].cpu().float().tolist(),
        "object_logit": float(outputs.object_score_logits.reshape(-1)[0].cpu().float()),
    }


def _run_jobs(jobs: list[_Job]) -> None:
    t_start = time.monotonic()
    for job in jobs:
        job.t_start = t_start
    STATS.started(len(jobs))
    try:
        if jobs[0].kind == "text":
            _run_text_batch(jobs)
        elif jobs[0].kind == "box":
            _run_box(jobs[0])
        else:
            _run_point(jobs[0])
    except BaseException as exc:  # noqa: BLE001 - every waiter must learn about it
        for job in jobs:
            job.error = exc
    finally:
        STATS.finished_batch(time.monotonic() - t_start, len(jobs))
        for job in jobs:
            job.done.set()


def _worker_loop() -> None:
    """Pull one job, try to fill a batch within batch_wait_ms, run it."""
    pending: _Job | None = None
    while True:
        job = pending if pending is not None else _jobs.get()
        pending = None
        if job is _SHUTDOWN:
            return
        if job.kind != "text" or CONFIG.batch_size <= 1:
            _run_jobs([job])
            continue
        batch = [job]
        deadline = time.monotonic() + CONFIG.batch_wait_ms / 1000.0
        while len(batch) < CONFIG.batch_size:
            timeout = deadline - time.monotonic()
            if timeout <= 0:
                break
            try:
                nxt = _jobs.get(timeout=timeout)
            except queue.Empty:
                break
            if nxt is _SHUTDOWN or nxt.kind != "text":
                pending = nxt
                break
            batch.append(nxt)
        _run_jobs(batch)


# ----------------------------------------------------------------------------- app


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, processor
    dtype = DTYPES[CONFIG.dtype]
    print(
        f"Loading {CONFIG.model} on {device} ({CONFIG.dtype}), "
        f"workers={CONFIG.workers} batch_size={CONFIG.batch_size} "
        f"batch_wait_ms={CONFIG.batch_wait_ms:g}...",
        flush=True,
    )
    model = Sam3Model.from_pretrained(CONFIG.model, local_files_only=True).to(
        device=device, dtype=dtype
    )
    model.eval()
    processor = Sam3Processor.from_pretrained(CONFIG.model, local_files_only=True)
    for _ in range(CONFIG.workers):
        thread = threading.Thread(target=_worker_loop, daemon=True, name="sam3-worker")
        thread.start()
        _workers.append(thread)
    print(f"SAM3 loaded, {len(_workers)} worker(s) running", flush=True)
    yield
    for _ in _workers:
        _jobs.put(_SHUTDOWN)


app = FastAPI(
    title="SAM3",
    description=(
        "Segment Anything 3 — text-, box- and click-prompted instance segmentation.\n\n"
        "The portable compatibility gateway serves it under `/upstream/sam3/<path>`.\n\n"
        "This is **not** an OpenAI-compatible model: there is no `/v1/chat/completions`."
    ),
    version="2.0.0",
    openapi_tags=[
        {"name": "segmentation", "description": "Prompt the model with a noun, a box or a click."},
        {"name": "ops", "description": "Health, capacity and load."},
    ],
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)


# ----------------------------------------------------------------------------- schemas


class Instance(BaseModel):
    score: float = Field(description="Confidence of this instance, 0-1.")
    box: list[int] = Field(description="Bounding box [x1, y1, x2, y2] in original image pixels.")
    area: int = Field(description="Mask area in pixels.")
    label: str | None = Field(default=None, description="The noun that produced this instance.")
    mask_png_b64: str | None = Field(default=None, description="1-bit mask as a base64 PNG.")


class SegmentResponse(BaseModel):
    count: int
    width: int
    height: int
    prompt: str
    instances: list[Instance]


class SegmentMultiResponse(BaseModel):
    count: int
    width: int
    height: int
    prompts: list[str]
    instances: list[Instance]


class VerifyInstance(BaseModel):
    """Same as Instance, but the mask field keeps the verification contract's spelling."""

    score: float
    box: list[int]
    area: int
    label: str | None = None
    mask_png_base64: str | None = Field(default=None, description="1-bit mask as a base64 PNG.")


class SegmentVerifyResponse(BaseModel):
    count: int
    width: int
    height: int
    model_id: str
    prompt: str
    instances: list[VerifyInstance]


class SegmentPointResponse(BaseModel):
    count: int
    width: int
    height: int
    object_score: float = Field(description="Whether the model thinks anything is under the click.")
    object_score_logit: float
    instances: list[Instance]


class HealthResponse(BaseModel):
    status: str
    model: str
    device: str
    dtype: str
    workers: int
    batch_size: int


class StatsResponse(BaseModel):
    workers: int
    batch_size: int
    batch_wait_ms: float
    dtype: str
    device: str
    queued: int = Field(description="Jobs waiting for a worker right now.")
    running: int = Field(description="Images inside a GPU pass right now.")
    window_seconds: float
    requests: int
    requests_per_minute: float
    batches: int
    avg_batch_size: float
    avg_queue_wait_ms: float
    avg_latency_ms: float
    load_percent: float = Field(description="Share of worker time spent on the GPU in the window.")


# ----------------------------------------------------------------------------- helpers


@app.get("/", include_in_schema=False)
def ui():
    """Return service metadata without a bundled web UI."""
    return {"service": "sam3", "docs": "docs", "health": "health"}


@app.get("/docs", include_in_schema=False)
def docs():
    """Swagger UI. The OpenAPI URL is relative so it also works under /upstream/sam3/."""
    return get_swagger_ui_html(openapi_url="openapi.json", title="SAM3 API")


@app.get("/health", tags=["ops"], summary="Liveness and current configuration")
def health() -> HealthResponse:
    if model is None:
        raise HTTPException(status_code=503, detail="model still loading")
    return HealthResponse(
        status="ok",
        model="facebook/sam3",
        device=device,
        dtype=CONFIG.dtype,
        workers=CONFIG.workers,
        batch_size=CONFIG.batch_size,
    )


@app.get("/stats", tags=["ops"], summary="Queue depth, throughput and load",
         responses={200: {"model": StatsResponse}})
def stats():
    """Rolling statistics over the last `window_seconds` (default 300).

    `load_percent` is the share of worker time spent inside a GPU pass: 100 means
    every worker was busy for the whole window.
    """
    return STATS.snapshot()


def _png_b64(mask: np.ndarray) -> str:
    buf = io.BytesIO()
    Image.fromarray(mask * 255).save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def _bbox(mask: np.ndarray):
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]


def _instances(results, return_masks: bool, label: str | None = None) -> list[dict]:
    masks = results["masks"].cpu().numpy().astype(np.uint8)
    scores = results["scores"].cpu().tolist()
    boxes = results["boxes"].cpu().tolist() if "boxes" in results else None
    out = []
    for i, score in enumerate(scores):
        mask = masks[i]
        item = {
            "score": float(score),
            "box": [int(v) for v in boxes[i]] if boxes else _bbox(mask),
            "area": int(mask.sum()),
        }
        if label is not None:
            item["label"] = label
        if return_masks:
            item["mask_png_b64"] = _png_b64(mask)
        out.append(item)
    return out


def _read_image(image: UploadFile) -> Image.Image:
    try:
        return Image.open(io.BytesIO(image.file.read())).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"bad image: {exc}")


def _require_model():
    if model is None:
        raise HTTPException(status_code=503, detail="model still loading")


def _text_job(img: Image.Image, nouns: list[str], threshold: float, mask_threshold: float) -> _Job:
    """Do every CPU-side step here, in the request's own thread, then queue the GPU work."""
    img_inputs = processor(images=img, return_tensors="pt")
    prompts = [(noun, processor(text=noun, return_tensors="pt")) for noun in nouns]
    return _Job(
        kind="text",
        payload={
            "pixel_values": img_inputs["pixel_values"],
            "target_sizes": img_inputs["original_sizes"].tolist(),
            "prompts": prompts,
            "threshold": threshold,
            "mask_threshold": mask_threshold,
        },
    )


def _ensure_tracker():
    """Load Sam3TrackerModel on first use. Same checkpoint as the detector."""
    global tracker_model, tracker_processor
    if tracker_model is not None:
        return
    with _tracker_load_lock:
        if tracker_model is not None:
            return
        print(f"Loading {CONFIG.model} tracker head on {device}...", flush=True)
        proc = Sam3TrackerProcessor.from_pretrained(CONFIG.model, local_files_only=True)
        mdl = Sam3TrackerModel.from_pretrained(
            CONFIG.model, local_files_only=True
        ).to(device=device, dtype=DTYPES[CONFIG.dtype])
        mdl.eval()
        tracker_processor, tracker_model = proc, mdl
        print("SAM3 tracker loaded", flush=True)


def _prob_to_logit(p: float) -> float:
    """post_process_masks thresholds LOGITS (0.0 == p 0.5); callers send a probability."""
    if not 0.0 < p < 1.0:
        raise HTTPException(
            status_code=422, detail=f"mask_threshold must be between 0 and 1, got {p}")
    return math.log(p / (1.0 - p))


def _parse_points(raw: str, width: int, height: int) -> list[list[float]]:
    try:
        parsed = json.loads(raw)
    except Exception:
        raise HTTPException(
            status_code=422, detail='points must be JSON, e.g. "[[900, 700]]"')
    if not isinstance(parsed, list) or not parsed:
        raise HTTPException(
            status_code=422, detail="points must be a non-empty array of [x, y] pairs")
    out = []
    for i, pt in enumerate(parsed):
        if not isinstance(pt, (list, tuple)) or len(pt) != 2:
            raise HTTPException(
                status_code=422, detail=f"point {i} is not an [x, y] pair")
        try:
            x, y = float(pt[0]), float(pt[1])
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=422, detail=f"point {i} has non-numeric coordinates")
        if not (math.isfinite(x) and math.isfinite(y)):
            raise HTTPException(status_code=422, detail=f"point {i} is not finite")
        if not (0 <= x <= width - 1 and 0 <= y <= height - 1):
            raise HTTPException(
                status_code=422,
                detail=f"point {i} ({x:g}, {y:g}) lies outside the "
                       f"{width}x{height} image",
            )
        out.append([x, y])
    return out


def _parse_labels(raw: str, n_points: int) -> list[int]:
    try:
        parsed = json.loads(raw)
    except Exception:
        raise HTTPException(status_code=422, detail='labels must be JSON, e.g. "[1]"')
    if not isinstance(parsed, list):
        raise HTTPException(
            status_code=422, detail="labels must be an array of 1 (positive) or 0 (negative)")
    if len(parsed) != n_points:
        raise HTTPException(
            status_code=422,
            detail=f"labels has {len(parsed)} entries but points has {n_points}; "
                   "they describe the same clicks and must match",
        )
    out = []
    for i, value in enumerate(parsed):
        if isinstance(value, bool) or value not in (0, 1):
            raise HTTPException(
                status_code=422,
                detail=f"label {i} must be 1 (positive) or 0 (negative), got {value!r}",
            )
        out.append(int(value))
    return out


# ----------------------------------------------------------------------------- endpoints


@app.post("/segment_point", tags=["segmentation"], summary="Segment the object under a click",
          responses={200: {"model": SegmentPointResponse}})
def segment_point(
    image: UploadFile = File(..., description="The image to segment."),
    points: str = Form(..., description='JSON array of [x, y] clicks, e.g. "[[900, 700]]".'),
    labels: str = Form(..., description='JSON array of 1 (positive) or 0 (negative), one per point.'),
    multimask: bool = Form(True, description="Return three candidate masks instead of one."),
    mask_threshold: float = Form(0.5, description="Mask probability cut-off, 0-1."),
):
    """Segment the ONE object under a click, with no text prompt.

    Answered by Sam3TrackerModel, not the Sam3Model behind /segment: that class
    takes text/boxes and returns every instance of a concept, and does not accept
    points at all. Every point here refines a single mask - positives add,
    negatives subtract - so the response is candidate masks for one object.
    """
    _require_model()
    img = _read_image(image)
    pts = _parse_points(points, img.width, img.height)
    labs = _parse_labels(labels, len(pts))
    logit_threshold = _prob_to_logit(mask_threshold)

    _ensure_tracker()
    # input_points is 4 levels (image, object, point, xy); input_labels is 3.
    inputs = tracker_processor(
        images=img,
        input_points=[[pts]],
        input_labels=[[labs]],
        return_tensors="pt",
    )
    job = _Job(
        kind="point",
        payload={
            "inputs": inputs,
            "original_sizes": inputs["original_sizes"],
            "multimask": multimask,
            "logit_threshold": logit_threshold,
        },
    )
    out = _submit(job)

    masks = out["masks"].numpy().astype(np.uint8)
    instances = []
    for i, score in enumerate(out["scores"]):
        mask = masks[i]
        instances.append({
            "score": float(score),
            "box": _bbox(mask) or [0, 0, 0, 0],
            "area": int(mask.sum()),
            "mask_png_b64": _png_b64(mask),
        })
    instances.sort(key=lambda inst: inst["score"], reverse=True)

    return {
        "count": len(instances),
        "width": img.width,
        "height": img.height,
        # Whether the model thinks anything is under the click at all. Reported,
        # never acted on: filtering is the caller's decision, not the service's.
        "object_score": 1.0 / (1.0 + math.exp(-out["object_logit"])),
        "object_score_logit": out["object_logit"],
        "instances": instances,
    }


@app.post("/segment_multi", tags=["segmentation"], summary="Many nouns against one image",
          responses={200: {"model": SegmentMultiResponse}})
def segment_multi(
    image: UploadFile = File(..., description="The image to segment."),
    texts: str = Form(..., description='Comma-separated nouns, e.g. "helmet, glove".'),
    threshold: float = Form(0.5, description="Instance score cut-off, 0-1."),
    mask_threshold: float = Form(0.5, description="Mask probability cut-off, 0-1."),
    return_masks: bool = Form(True, description="Include base64 PNG masks in the response."),
):
    """Many noun prompts against one image, encoding the image once.

    /segment re-runs the vision encoder per call, which is nearly the whole
    model — the DETR decoder runs at hidden_size 256. Here get_vision_features()
    runs once and every prompt reuses the same vision_embeds, so a vocabulary
    sweep pays for one image encode instead of len(texts).

    Same tensors, so detections are identical to calling /segment per noun.
    """
    _require_model()
    nouns = [t.strip() for t in texts.split(",") if t.strip()]
    if not nouns:
        raise HTTPException(status_code=400, detail="texts must be a non-empty comma-separated list")
    img = _read_image(image)
    per_noun = _submit(_text_job(img, nouns, threshold, mask_threshold))

    instances: list[dict] = []
    for noun, results in per_noun:
        instances.extend(_instances(results, return_masks, label=noun))

    return {
        "count": len(instances),
        "width": img.width,
        "height": img.height,
        "prompts": nouns,
        "instances": instances,
    }


@app.post("/segment_verify", tags=["segmentation"], summary="Labeled instances, verification contract",
          responses={200: {"model": SegmentVerifyResponse}})
def segment_verify(
    image: UploadFile = File(..., description="The image to segment."),
    text: str = Form(..., description="One noun, or several separated by commas."),
    threshold: float = Form(0.5, description="Instance score cut-off, 0-1."),
    mask_threshold: float = Form(0.5, description="Mask probability cut-off, 0-1."),
    return_masks: bool = Form(True, description="Include base64 PNG masks in the response."),
):
    """Return labeled instances through the barcode verification contract."""
    _require_model()
    prompt = text.strip()
    nouns = [value.strip() for value in prompt.split(",") if value.strip()]
    if not nouns:
        raise HTTPException(status_code=400, detail="text must contain a noun")
    img = _read_image(image)
    per_noun = _submit(_text_job(img, nouns, threshold, mask_threshold))

    instances: list[dict] = []
    for noun, results in per_noun:
        instances.extend(_instances(results, return_masks, label=noun))

    for instance in instances:
        if "mask_png_b64" in instance:
            instance["mask_png_base64"] = instance.pop("mask_png_b64")

    return {
        "count": len(instances),
        "width": img.width,
        "height": img.height,
        "model_id": "sam3",
        "prompt": prompt,
        "instances": instances,
    }


@app.post("/segment", tags=["segmentation"], summary="Segment by one noun or one box",
          responses={200: {"model": SegmentResponse}})
def segment(
    image: UploadFile = File(..., description="The image to segment."),
    text: str = Form("", description='One noun, e.g. "bicycle helmet". Either this or box.'),
    box: str = Form("", description='Box prompt "x1,y1,x2,y2". Either this or text.'),
    threshold: float = Form(0.5, description="Instance score cut-off, 0-1."),
    mask_threshold: float = Form(0.5, description="Mask probability cut-off, 0-1."),
    return_masks: bool = Form(True, description="Include base64 PNG masks in the response."),
):
    """Segment by text prompt ("bicycle helmet") or by a box "x1,y1,x2,y2"."""
    _require_model()
    if not text.strip() and not box.strip():
        raise HTTPException(status_code=400, detail="pass either text or box")
    img = _read_image(image)

    if text.strip():
        job = _text_job(img, [text.strip()], threshold, mask_threshold)
    else:
        try:
            x1, y1, x2, y2 = (int(float(v)) for v in box.split(","))
        except Exception:
            raise HTTPException(status_code=400, detail='box must be "x1,y1,x2,y2"')
        # Nesting is [image level, box level] — a third level is rejected.
        inputs = processor(
            images=img,
            input_boxes=[[[x1, y1, x2, y2]]],
            input_boxes_labels=[[1]],
            return_tensors="pt",
        )
        job = _Job(
            kind="box",
            payload={
                "inputs": inputs,
                "target_sizes": inputs.get("original_sizes").tolist(),
                "threshold": threshold,
                "mask_threshold": mask_threshold,
            },
        )

    per_noun = _submit(job)
    instances = _instances(per_noun[0][1], return_masks)

    return {
        "count": len(instances),
        "width": img.width,
        "height": img.height,
        "prompt": text.strip() or box.strip(),
        "instances": instances,
    }


# ----------------------------------------------------------------------------- main


def parse_args() -> Config:
    p = argparse.ArgumentParser(description="SAM3 segmentation service")
    p.add_argument("--host", default=CONFIG.host)
    p.add_argument("--port", type=int, default=CONFIG.port)
    p.add_argument("--model", default=CONFIG.model, help="local SAM3 snapshot directory")
    p.add_argument("--device", default=CONFIG.device, choices=["auto", "cuda", "mps", "cpu"])
    p.add_argument("--workers", type=int, default=CONFIG.workers,
                   help="GPU worker threads; 1 is fastest on gx10 - more workers "
                        "fragment the batches and contend on one GPU")
    p.add_argument("--batch-size", type=int, default=CONFIG.batch_size,
                   help="images per vision-encoder pass; 1 disables batching")
    p.add_argument("--batch-wait-ms", type=float, default=CONFIG.batch_wait_ms,
                   help="how long a worker waits to fill a batch")
    p.add_argument("--dtype", default=CONFIG.dtype, choices=sorted(DTYPES),
                   help="fp16 (default, ~2.9x faster on GB10) or fp32")
    p.add_argument("--job-timeout", type=float, default=CONFIG.job_timeout,
                   help="seconds a queued request waits before 503")
    args = p.parse_args()
    if args.workers < 1 or args.batch_size < 1:
        p.error("--workers and --batch-size must be >= 1")
    return Config(
        host=args.host, port=args.port, model=args.model, device=args.device, workers=args.workers,
        batch_size=args.batch_size, batch_wait_ms=args.batch_wait_ms,
        dtype=args.dtype, job_timeout=args.job_timeout,
        stats_window=CONFIG.stats_window,
    )


if __name__ == "__main__":
    CONFIG = parse_args()
    device = _select_device(CONFIG.device)
    STATS = Stats(CONFIG.stats_window)
    uvicorn.run(app, host=CONFIG.host, port=CONFIG.port, log_level="info")
