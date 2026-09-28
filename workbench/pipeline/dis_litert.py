"""Run the Android DIS LiteRT model and prepare the main object on white."""

import math

import numpy as np
from PIL import Image


SIZE = 1024
MAX_SOURCE_SIDE = 2048
MIN_FOREGROUND = 0.005
MAX_FOREGROUND = 0.995


class DisError(ValueError):
    """The DIS model or its mask cannot prepare an image."""


def normalize_mask(mask):
    """Apply the min-max normalization of the reference DIS inference code."""
    mask = np.asarray(mask, dtype=np.float32)
    if mask.shape != (SIZE, SIZE) or not np.isfinite(mask).all():
        raise DisError("DIS returned an invalid 1024 by 1024 mask")
    low = float(mask.min())
    high = float(mask.max())
    if high - low <= 1e-6:
        raise DisError("DIS returned a flat mask")
    return np.clip((mask - low) / (high - low), 0.0, 1.0)


def limit_source(image):
    """Apply the Android long-side limit and return an RGB image."""
    image = image.convert("RGB")
    longest = max(image.size)
    if longest <= MAX_SOURCE_SIDE:
        return image
    scale = MAX_SOURCE_SIDE / float(longest)
    size = (max(1, int(image.width * scale + 0.5)),
            max(1, int(image.height * scale + 0.5)))
    return image.resize(size, Image.Resampling.LANCZOS)


def composite_mask(source, mask, threshold=0.5, margin=0.04):
    """Apply one 1024 by 1024 soft mask as the Android application does."""
    source = limit_source(source)
    mask = np.asarray(mask, dtype=np.float32)
    if mask.shape != (SIZE, SIZE) or not np.isfinite(mask).all():
        raise DisError("DIS returned an invalid 1024 by 1024 mask")
    foreground = mask >= threshold
    fraction = float(foreground.mean())
    if fraction < MIN_FOREGROUND:
        raise DisError("DIS found no main object")
    if fraction > MAX_FOREGROUND:
        raise DisError("DIS selected the complete image")
    rows, columns = np.nonzero(foreground)
    min_x, max_x = int(columns.min()), int(columns.max())
    min_y, max_y = int(rows.min()), int(rows.max())
    left = int(min_x / SIZE * source.width)
    top = int(min_y / SIZE * source.height)
    right = math.ceil((max_x + 1) / SIZE * source.width)
    bottom = math.ceil((max_y + 1) / SIZE * source.height)
    margin_x = int((right - left) * margin + 0.5)
    margin_y = int((bottom - top) * margin + 0.5)
    left, top = max(0, left - margin_x), max(0, top - margin_y)
    right, bottom = min(source.width, right + margin_x), min(source.height, bottom + margin_y)
    if right <= left or bottom <= top:
        raise DisError("DIS returned an empty main-object box")

    pixels = np.asarray(source, dtype=np.float32)[top:bottom, left:right]
    mask_y = np.arange(top, bottom, dtype=np.int64) * SIZE // source.height
    mask_x = np.arange(left, right, dtype=np.int64) * SIZE // source.width
    alpha = np.clip(mask[np.ix_(mask_y, mask_x)], 0.0, 1.0)[..., None]
    composite = np.floor(255.0 + (pixels - 255.0) * alpha + 0.5)
    return Image.fromarray(np.clip(composite, 0, 255).astype(np.uint8))


def square_on_white(image):
    """Put an image at the center of a white square."""
    image = image.convert("RGB")
    side = max(image.size)
    out = Image.new("RGB", (side, side), "white")
    out.paste(image, ((side - image.width) // 2, (side - image.height) // 2))
    return out


class Segmenter:
    """One LiteRT interpreter for the pinned public DIS model."""

    def __init__(self, repo_id, revision, filename="dis.tflite", threads=4):
        from ai_edge_litert.interpreter import Interpreter
        from huggingface_hub import hf_hub_download
        import ai_edge_litert

        path = hf_hub_download(repo_id=repo_id, filename=filename, revision=revision)
        self.interpreter = Interpreter(model_path=path, num_threads=threads)
        self.interpreter.allocate_tensors()
        self.input = self.interpreter.get_input_details()[0]
        self.output = self.interpreter.get_output_details()[0]
        self.repo_id = repo_id
        self.revision = revision
        self.path = path
        self.version = getattr(ai_edge_litert, "__version__", "unknown")

    def software(self):
        return {"dis_model": self.repo_id, "dis_revision": self.revision,
                "ai_edge_litert": self.version}

    def segment(self, image, threshold=0.5, margin=0.04):
        source = limit_source(image)
        resized = source.resize((SIZE, SIZE), Image.Resampling.BILINEAR)
        array = np.asarray(resized, dtype=np.float32)
        tensor = np.transpose(array / 255.0 - 0.5, (2, 0, 1))[None]
        self.interpreter.set_tensor(self.input["index"], tensor)
        self.interpreter.invoke()
        output = self.interpreter.get_tensor(self.output["index"])
        if output.size != SIZE * SIZE:
            raise DisError("DIS returned %d mask values" % output.size)
        mask = normalize_mask(output.reshape(SIZE, SIZE))
        return composite_mask(source, mask, threshold, margin)
