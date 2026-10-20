"""Encode fixed pixels with native SigLIP2 spatial attention weights."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import time
import numpy as np
from PIL import Image
import torch
import transformers
from transformers import AutoModel, AutoImageProcessor
from gpu_pooling import normalized

PROFILES = [{"background": .1, "bottle": 1., "label": 1.},
            {"background": 0., "bottle": 1., "label": 1.},
            {"background": .1, "bottle": 1., "label": 2.},
            {"background": 0., "bottle": 1., "label": 2.}]


def available():
    return int(next(s.split()[1] for s in Path("/proc/meminfo").read_text().splitlines()
                    if s.startswith("MemAvailable:"))) / 1024**2


def guard(floor=20):
    free = available()
    if free < floor:
        raise RuntimeError(f"Memory reserve: {free:.2f} GiB available; need {floor} GiB")
    return free


def atomic(path, values):
    temporary = path.with_suffix(".tmp.npz")
    np.savez_compressed(temporary, **values)
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, default=Path("inputs"))
    parser.add_argument("--controls-only", action="store_true")
    parser.add_argument("--batch-size", type=int, default=36)
    args = parser.parse_args()
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    guard(28)
    total = torch.cuda.get_device_properties(0).total_memory
    torch.cuda.set_per_process_memory_fraction(8 * 2**30 / total, 0)
    checkpoint = Path.home() / ".cache/huggingface/hub/models--google--siglip2-so400m-patch16-naflex/snapshots/cc24074f717b612951c2dead130904ab9b65a81e"
    processor = AutoImageProcessor.from_pretrained(checkpoint, local_files_only=True)
    model = AutoModel.from_pretrained(checkpoint, local_files_only=True, dtype=torch.bfloat16).to("cuda").eval()
    vision = model.vision_model
    guard()
    inputs = args.inputs.resolve()
    manifest = json.loads((inputs / "manifest.json").read_text())
    controls = np.load(inputs / "controls.npz", allow_pickle=False)
    result_root = inputs.parent / "native-results"
    result_root.mkdir(exist_ok=True)
    minimum = available()
    max_uniform_delta, max_catalogue_delta, min_catalogue_cosine = 0., 0., 1.
    recipe = {"revision": checkpoint.name, "torch": torch.__version__, "transformers": transformers.__version__,
              "pillow": __import__("PIL").__version__, "dtype": "bfloat16", "max_num_patches": 512,
              "profiles": PROFILES, "batch_size": args.batch_size,
              "pooling": "Native learned attention head. Add log(patch weight) to attention logits.",
              "mask_fractions": "BOX sample mask coverage to the actual NaFlex patch grid. Label coverage cannot exceed foreground coverage.",
              "zero_weight": "Exclude the token from pooling. Keep padded tokens excluded.",
              "cuda_limit_gib": 8, "reserve_gib": 20, "render_threads": 8, "torch_threads": 4,
              "config_sha256": hashlib.sha256((checkpoint / "config.json").read_bytes()).hexdigest(),
              "processor_sha256": hashlib.sha256((checkpoint / "preprocessor_config.json").read_bytes()).hexdigest(),
              "manifest_sha256": hashlib.sha256((inputs / "manifest.json").read_bytes()).hexdigest(),
              "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "pooling_sha256": hashlib.sha256(Path("gpu_pooling.py").read_bytes()).hexdigest()}
    if (result_root / "recipe.json").exists():
        assert json.loads((result_root / "recipe.json").read_text()) == recipe, "Do not mix native cache recipes."
    else:
        (result_root / "recipe.json").write_text(json.dumps(recipe, indent=2))
    @lru_cache(maxsize=4)
    def originals(identity, image_path, fg_path, label_path):
        result = []
        for path, mode in [(image_path, "RGB"), (fg_path, "L"), (label_path, "L")]:
            with Image.open(inputs / path) as im:
                result.append(im.convert(mode))
        return result

    def render(job):
        record, angle = job
        values = originals(record["id"], record["image"], record["foreground"], record["label"])
        images = []
        step = record["resize"]
        scale = min(1., step["max_size"] / max(values[0].size)) if step and not step.get("upscale") else (step["max_size"] / max(values[0].size) if step else 1.)
        for position, image in enumerate(values):
            if angle:
                image = image.rotate(angle, Image.Resampling.BICUBIC, expand=True,
                                     fillcolor=(255, 255, 255) if position == 0 else 0)
            if scale != 1.:
                size = tuple(max(1, round(v * scale)) for v in image.size)
                image = image.resize(size, Image.Resampling.LANCZOS)
            images.append(image)
        assert images[0].size == images[1].size == images[2].size
        return images

    def encode(rendered):
        nonlocal minimum, max_uniform_delta
        minimum = min(minimum, guard())
        batch = processor(images=[r[0] for r in rendered], return_tensors="pt", max_num_patches=512)
        shapes = batch["spatial_shapes"].tolist()
        mask = batch["pixel_attention_mask"]
        weights = []
        for i, ((rows, cols), images) in enumerate(zip(shapes, rendered)):
            count = rows * cols
            assert int(mask[i].sum()) == count
            fg = np.asarray(images[1].resize((cols, rows), Image.Resampling.BOX), np.float32).ravel() / 255
            label = np.minimum(fg, np.asarray(images[2].resize((cols, rows), Image.Resampling.BOX), np.float32).ravel() / 255)
            values = np.zeros((5, mask.shape[1]), np.float32)
            values[0, :count] = 1.
            for j, profile in enumerate(PROFILES, 1):
                values[j, :count] = profile["background"] * (1-fg) + fg + (profile["label"] - 1.) * label
                if values[j].sum() == 0:
                    values[j, :count] = 1.
            weights.append(torch.from_numpy(values).to("cuda"))
        if transformers.__version__.startswith("5."):
            batch["attention_mask"] = batch.pop("pixel_attention_mask")
        begin = time.perf_counter()
        def weighted_head(hidden, weights):
            weights = weights.to(hidden)
            bias = weights.clamp_min(torch.finfo(hidden.dtype).tiny).log()
            bias = bias.masked_fill(weights == 0, float("-inf"))
            bias = bias[:, None, :].repeat_interleave(vision.head.num_heads, dim=0)
            probe = vision.head.probe.repeat(hidden.shape[0], 1, 1)
            # Keep the same MultiheadAttention path as the live BF16 pooling head.
            pooled = vision.head.attention(probe, hidden, hidden, attn_mask=bias, need_weights=True)[0]
            return (pooled + vision.head.mlp(vision.head.layernorm(pooled)))[:, 0]
        with torch.inference_mode():
            output = vision(**batch.to("cuda"))
            all_weights = torch.stack(weights)
            by_profile = [normalized(weighted_head(output.last_hidden_state, all_weights[:, j]).float().cpu().numpy())
                          for j in range(5)]
            pooled = np.stack(by_profile, axis=1)
            baseline = normalized(output.pooler_output.float().cpu().numpy())
        torch.cuda.synchronize()
        elapsed = time.perf_counter() - begin
        for i, vectors in enumerate(pooled):
            delta = float(np.max(np.abs(vectors[0] - baseline[i])))
            max_uniform_delta = max(max_uniform_delta, delta)
            assert delta < 2e-5, ("Uniform pooling differs from the original head", delta)
        minimum = min(minimum, guard())
        return np.stack(pooled), baseline, elapsed

    records = [r for r in manifest["records"] if r.get("control")] if args.controls_only else manifest["records"] + manifest["queries"]
    began = time.perf_counter()
    with ThreadPoolExecutor(max_workers=8) as pool:
        for number, record in enumerate(records, 1):
            path = result_root / (record["id"] + ".npz")
            if path.exists() and not args.controls_only:
                continue
            all_vectors, all_baseline, seconds = [], [], 0.
            for offset in range(0, len(record["angles"]), args.batch_size):
                angles = record["angles"][offset:offset + args.batch_size]
                rendered = list(pool.map(render, [(record, angle) for angle in angles]))
                vectors, baseline, elapsed = encode(rendered)
                seconds += elapsed
                if record.get("control"):
                    expected = controls[record["id"]][offset:offset + len(angles)]
                    cosine = np.sum(expected * baseline, axis=1)
                    delta = float(np.max(np.abs(expected-baseline)))
                    min_catalogue_cosine = min(min_catalogue_cosine, float(cosine.min()))
                    max_catalogue_delta = max(max_catalogue_delta, delta)
                    assert cosine.min() > .99999 and delta < .001, (record["id"], angles, cosine, delta)
                all_vectors.extend(vectors[:, 1:])
                all_baseline.extend(baseline)
            if not args.controls_only:
                atomic(path, {"vectors": np.asarray(all_vectors, np.float32),
                              "baseline": np.asarray(all_baseline, np.float32), "seconds": np.asarray(seconds)})
            if number % 10 == 0 or record.get("control") or number == len(records):
                progress = {"done": number, "total": len(records), "id": record["id"], "seconds": round(time.perf_counter()-began, 1),
                            "minimum_available_gib": round(minimum, 2), "max_uniform_delta": max_uniform_delta,
                            "min_catalogue_cosine": min_catalogue_cosine, "max_catalogue_delta": max_catalogue_delta}
                (result_root / "progress.json").write_text(json.dumps(progress))
                print(json.dumps(progress), flush=True)
    summary = {**recipe, "minimum_available_gib": minimum, "max_uniform_delta": max_uniform_delta,
               "min_catalogue_cosine": min_catalogue_cosine, "max_catalogue_delta": max_catalogue_delta,
               "seconds": time.perf_counter()-began, "peak_reserved_gib": torch.cuda.max_memory_reserved()/2**30,
               "records": len(records), "controls_only": args.controls_only}
    (result_root / ("controls.json" if args.controls_only else "complete.json")).write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
