"""Optional pinned DIS LiteRT foreground baseline, without semantic bottle rules."""

from functools import lru_cache
import hashlib
import math
from pathlib import Path
import threading
from time import monotonic

import numpy as np
from PIL import Image

from .group import GroupMatchError, SAM3_TIMEOUT_SECONDS, _normalize_image
from .semantic_selector import Selection, _png


VERSION = "dis-v1"
SIZE = 1024
MODEL_REPOSITORY = "litert-community/DIS-ISNet-LiteRT"
MODEL_REVISION = "1b966dbe2f33bd5ca1299cf94fbab59265210b6b"
MODEL_SHA256 = "0c3c93b6a2a65e7c69137ec82596944e6bfb97d982c75bab03acb0738dbaa087"
THRESHOLD = 0.5
MARGIN = 0.04
MIN_FOREGROUND = 0.005
MAX_FOREGROUND = 0.995
READINESS_TIMEOUT_SECONDS = 30.0
_LOAD_LOCK = threading.Lock()


def _remaining(deadline):
    remaining = deadline - monotonic()
    if remaining <= 0:
        raise GroupMatchError(504, "DIS request timed out")
    return remaining


class _Runtime:
    """One lazily loaded CPU interpreter, serialized across concurrent requests."""

    def __init__(self, path):
        try:
            model = Path(path).read_bytes()
        except OSError as exc:
            raise GroupMatchError(503, "DIS model file is unavailable") from exc
        if hashlib.sha256(model).hexdigest() != MODEL_SHA256:
            raise GroupMatchError(503, "DIS model SHA-256 does not match dis-v1")
        try:
            from ai_edge_litert.interpreter import Interpreter
            interpreter = Interpreter(model_content=model, num_threads=4)
            inputs, outputs = interpreter.get_input_details(), interpreter.get_output_details()
            if (len(inputs) != 1 or len(outputs) != 1
                    or tuple(inputs[0]["shape"]) != (1, 3, SIZE, SIZE)
                    or tuple(outputs[0]["shape"]) != (1, 1, SIZE, SIZE)
                    or inputs[0]["dtype"] != np.float32 or outputs[0]["dtype"] != np.float32):
                raise ValueError("unexpected DIS tensor contract")
            interpreter.allocate_tensors()
        except ImportError as exc:
            raise GroupMatchError(503, "DIS runtime is unavailable; install requirements-dis.txt") from exc
        except Exception as exc:
            raise GroupMatchError(503, "DIS model could not be initialized") from exc
        self.interpreter = interpreter
        self.input_index = inputs[0]["index"]
        self.output_index = outputs[0]["index"]
        self.lock = threading.Lock()
        self.ready = False

    def mask(self, image, deadline, *, probe=False):
        # Match the existing Android/workbench DIS preprocessing: stretched NCHW,
        # bilinear RGB, float32 / 255 - 0.5. No detector or network call is made.
        rgb = image.convert("RGB").resize((SIZE, SIZE), Image.Resampling.BILINEAR)
        tensor = np.transpose(np.asarray(rgb, dtype=np.float32) / 255.0 - 0.5,
                              (2, 0, 1))[None]
        if not self.lock.acquire(timeout=_remaining(deadline)):
            raise GroupMatchError(504, "DIS request timed out")
        try:
            _remaining(deadline)
            if probe and self.ready:
                return None
            self.interpreter.set_tensor(self.input_index, tensor)
            self.interpreter.invoke()
            output = self.interpreter.get_tensor(self.output_index)
            if output.shape != (1, 1, SIZE, SIZE) or not np.isfinite(output).all():
                self.ready = False
                raise GroupMatchError(502, "DIS returned an invalid mask")
            self.ready = True
            _remaining(deadline)
            return output[0, 0]
        except GroupMatchError:
            raise
        except Exception as exc:
            self.ready = False
            raise GroupMatchError(502, "DIS inference failed") from exc
        finally:
            self.lock.release()


@lru_cache(maxsize=1)
def _cached_runtime(path):
    return _Runtime(path)


def _runtime(model_path, deadline):
    if not model_path:
        raise GroupMatchError(503, "DIS model_path is not configured")
    if not _LOAD_LOCK.acquire(timeout=_remaining(deadline)):
        raise GroupMatchError(504, "DIS request timed out")
    try:
        runtime = _cached_runtime(str(Path(model_path).expanduser().resolve()))
    finally:
        _LOAD_LOCK.release()
    _remaining(deadline)
    return runtime


def infer_mask(image, model_path, timeout=SAM3_TIMEOUT_SECONDS):
    """Load only on first use; bound waiting for model initialization and inference."""
    deadline = monotonic() + timeout
    return _runtime(model_path, deadline).mask(image, deadline)


def check_ready(model_path, timeout=READINESS_TIMEOUT_SECONDS):
    """Probe once, then inspect cached successful runtime state without invoking DIS.

    The tensor contract and model bytes are immutable and checked at load. An
    inference failure invalidates readiness. A busy previously healthy interpreter
    is alive; a cold probe rechecks readiness after acquiring the inference lock.
    """
    deadline = monotonic() + timeout
    runtime = _runtime(model_path, deadline)
    if not runtime.ready:
        runtime.mask(Image.new("RGB", (32, 32), "white"), deadline, probe=True)


def from_mask(image, output):
    """Create the shared selector result from raw DIS output, without label repair.

    An empty, flat or all-frame foreground returns the original frame. Malformed
    or nonfinite model data remains an error. Disconnected components are one
    saliency region; this baseline does not invent bottle instances or label IDs.
    """
    image = image.convert("RGB")
    values = np.asarray(output, dtype=np.float32)
    if values.shape != (SIZE, SIZE) or not np.isfinite(values).all():
        raise GroupMatchError(502, "DIS returned an invalid mask")
    result = Selection("no_target", *image.size, variant=VERSION,
                       selection_mode="fallback", crop_scope="original_frame")
    low, high = float(values.min()), float(values.max())
    trigger = "dis_flat_mask"
    mask = None
    if high - low > 1e-6:
        mask = np.clip((values - low) / (high - low), 0.0, 1.0)
        foreground = mask >= THRESHOLD
        fraction = float(foreground.mean())
        trigger = ("dis_no_foreground" if fraction < MIN_FOREGROUND else
                   "dis_all_foreground" if fraction > MAX_FOREGROUND else None)
    if trigger:
        result.reason = "fallback_original_frame"
        result.fallback_trigger = trigger
        result.crop_box = (0, 0, *image.size)
        result.keep_mask = Image.new("L", image.size, 255)
        result.crop = _png(image)
        return result
    rows, columns = np.nonzero(foreground)
    box = (int(columns.min()) * image.width // SIZE,
           int(rows.min()) * image.height // SIZE,
           math.ceil((int(columns.max()) + 1) * image.width / SIZE),
           math.ceil((int(rows.max()) + 1) * image.height / SIZE))
    dx, dy = (int((box[2] - box[0]) * MARGIN + 0.5),
              int((box[3] - box[1]) * MARGIN + 0.5))
    box = (max(0, box[0] - dx), max(0, box[1] - dy),
           min(image.width, box[2] + dx), min(image.height, box[3] + dy))
    # Preserve reference nearest-index sampling, represented as an 8-bit alpha
    # for the shared cascade adapter. Soft edges may alter observed RGB by design.
    y = np.arange(image.height, dtype=np.int64) * SIZE // image.height
    x = np.arange(image.width, dtype=np.int64) * SIZE // image.width
    alpha = np.floor(mask[np.ix_(y, x)] * 255.0 + 0.5).astype(np.uint8)
    result.keep_mask = Image.fromarray(alpha)
    result.crop_box = box
    result.crop = _png(Image.composite(image, Image.new("RGB", image.size, "white"),
                                       result.keep_mask).crop(box))
    result.status = "selected"
    result.selected_id = "dis-foreground"
    result.reason = "dis_foreground_mask"
    result.selection_mode = "foreground"
    result.crop_scope = "foreground_region"
    result.candidates = [dict(id=result.selected_id, source_index=None, kind="foreground",
                              box=list(box), signals=dict(
                                  foreground_fraction=fraction, model_sha256=MODEL_SHA256,
                                  model_revision=MODEL_REVISION))]
    return result


def select(image, model_path, *, timeout=SAM3_TIMEOUT_SECONDS):
    return from_mask(image, infer_mask(image, model_path, timeout))


def select_photo(body, model_path, *, timeout=SAM3_TIMEOUT_SECONDS):
    image, _ = _normalize_image(body)
    return select(image, model_path, timeout=timeout)
