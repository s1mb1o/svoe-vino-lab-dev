#!/usr/bin/env python3
"""Export the exact SigLIP2 NaFlex Android split as two static LiteRT models."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import tempfile
import time

import numpy as np
import torch
from torch import nn


MODEL_ID = "google/siglip2-so400m-patch16-naflex"
PATCH_SIZE = 16
PATCH_VALUES = 3 * PATCH_SIZE * PATCH_SIZE
SUPPORTED_PATCH_LIMITS = (256, 512, 1024)
STANDARD_POOLING = "standard"
FOREGROUND_POOLING = "foreground-1.0-background-0.1"
SUPPORTED_POOLING = (STANDARD_POOLING, FOREGROUND_POOLING)


class ExportError(ValueError):
    """The requested export cannot produce a compatible Android model."""


class NaFlexBackbone(nn.Module):
    """Apply the original patch projection and encoder to supplied positions."""

    def __init__(self, vision):
        super().__init__()
        self.patch_embedding = vision.embeddings.patch_embedding
        self.encoder = vision.encoder
        self.config = vision.config

    def forward(self, patches, positional_embeddings, encoder_attention_mask):
        hidden_states = self.patch_embedding(patches)
        hidden_states = hidden_states + positional_embeddings
        return self.encoder(
            inputs_embeds=hidden_states,
            attention_mask=encoder_attention_mask,
        ).last_hidden_state


class NaFlexPooling(nn.Module):
    """Apply the original post-LayerNorm and attention pooling head."""

    def __init__(self, vision):
        super().__init__()
        self.post_layernorm = vision.post_layernorm
        self.head = vision.head

    def forward(self, patch_tokens, attention_mask):
        return self.head(self.post_layernorm(patch_tokens), attention_mask)


class NaFlexForegroundPooling(nn.Module):
    """Apply the original pooling head with a soft foreground attention bias."""

    def __init__(self, vision):
        super().__init__()
        self.post_layernorm = vision.post_layernorm
        self.probe = vision.head.probe
        self.attention = vision.head.attention
        self.layernorm = vision.head.layernorm
        self.mlp = vision.head.mlp
        self.num_heads = vision.head.num_heads

    def forward(self, patch_tokens, patch_weights):
        hidden_state = self.post_layernorm(patch_tokens)
        batch_size = hidden_state.shape[0]
        probe = self.probe.repeat(batch_size, 1, 1)
        safe_weights = torch.clamp(patch_weights, min=1e-6)
        attention_bias = torch.where(
            patch_weights > 0,
            torch.log(safe_weights),
            torch.tensor(torch.finfo(probe.dtype).min, dtype=probe.dtype),
        )
        attention_bias = attention_bias[:, None, None, :]
        attention_bias = attention_bias.repeat(1, self.num_heads, 1, 1)
        attention_bias = attention_bias.reshape(-1, 1, hidden_state.shape[1])
        hidden_state = self.attention(
            probe,
            hidden_state,
            hidden_state,
            attn_mask=attention_bias,
        )[0]
        residual = hidden_state
        hidden_state = self.layernorm(hidden_state)
        hidden_state = residual + self.mlp(hidden_state)
        return hidden_state[:, 0]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def resolve_snapshot(model_id: str, cache_dir: Path, revision: str | None) -> Path:
    model_root = cache_dir / ("models--" + model_id.replace("/", "--"))
    snapshots = model_root / "snapshots"
    if revision:
        direct = snapshots / revision
        if direct.is_dir():
            return direct.resolve()
        ref = model_root / "refs" / revision
        if ref.is_file():
            resolved = snapshots / ref.read_text(encoding="utf-8").strip()
            if resolved.is_dir():
                return resolved.resolve()
        raise ExportError(f"the local cache has no revision {revision!r} for {model_id}")
    main_ref = model_root / "refs" / "main"
    if main_ref.is_file():
        resolved = snapshots / main_ref.read_text(encoding="utf-8").strip()
        if resolved.is_dir():
            return resolved.resolve()
    candidates = sorted(path for path in snapshots.glob("*") if path.is_dir())
    if len(candidates) != 1:
        raise ExportError(
            f"the local cache has {len(candidates)} snapshots for {model_id}; use --revision"
        )
    return candidates[0].resolve()


def sample_grid(max_num_patches: int) -> tuple[int, int]:
    if max_num_patches == 256:
        return 16, 16
    if max_num_patches == 512:
        return 22, 22
    if max_num_patches == 1024:
        return 31, 32
    raise ExportError(f"unsupported patch limit: {max_num_patches}")


def positional_input(
    vision,
    spatial_shapes: torch.Tensor,
    max_num_patches: int,
    position_grid: int,
    hidden_size: int,
):
    table = vision.embeddings.position_embedding.weight.reshape(
        position_grid,
        position_grid,
        hidden_size,
    )
    return vision.embeddings.resize_positional_embeddings(
        table,
        spatial_shapes,
        max_length=max_num_patches,
    )


def backbone_attention_mask(attention_mask: torch.Tensor) -> torch.Tensor:
    """Create the exact additive encoder mask outside the LiteRT graph."""
    patch_count = attention_mask.shape[1]
    valid_keys = attention_mask[:, None, None, :].bool()
    valid_keys = valid_keys.expand(-1, 1, patch_count, -1)
    return torch.where(
        valid_keys,
        torch.tensor(0.0, dtype=torch.float32),
        torch.tensor(torch.finfo(torch.float32).min, dtype=torch.float32),
    )
def cosine(left: torch.Tensor, right: torch.Tensor) -> float:
    value = torch.nn.functional.cosine_similarity(
        left.float().reshape(1, -1),
        right.float().reshape(1, -1),
    ).item()
    return max(-1.0, min(1.0, value))


def maximum_error(left: torch.Tensor, right: torch.Tensor) -> float:
    return (left.float() - right.float()).abs().max().item()


def convert_model(module: nn.Module, sample_args: tuple[torch.Tensor, ...], target: Path):
    import litert_torch

    converted = litert_torch.convert(
        module.eval(),
        sample_args=sample_args,
        strict_export=False,
    )
    converted.export(str(target))


def quantize_float16_fully_connected(source: Path, target: Path):
    from ai_edge_quantizer import qtyping, quantizer

    converter = quantizer.Quantizer(source)
    converter.update_quantization_recipe(
        regex=".*",
        algorithm_key=quantizer.AlgorithmName.FLOAT_CASTING,
        operation_name=qtyping.TFLOperationName.FULLY_CONNECTED,
        op_config=qtyping.OpQuantizationConfig(
            weight_tensor_config=qtyping.TensorQuantizationConfig(
                num_bits=16,
                dtype=qtyping.TensorDataType.FLOAT,
            ),
            compute_precision=qtyping.ComputePrecision.FLOAT,
        ),
    )
    result = converter.quantize(enable_progress_report=False)
    result.export_model(target, overwrite=True)


def run_litert(path: Path, values: list[np.ndarray]) -> list[np.ndarray]:
    from ai_edge_litert.interpreter import Interpreter

    interpreter = Interpreter(model_path=str(path), num_threads=4)
    interpreter.allocate_tensors()
    details = interpreter.get_input_details()
    if len(details) != len(values):
        raise ExportError(
            f"{path.name} has {len(details)} inputs instead of {len(values)}"
        )
    remaining = list(values)
    for detail in details:
        shape = tuple(int(value) for value in detail["shape"])
        dtype = np.dtype(detail["dtype"])
        match = next(
            (
                index
                for index, value in enumerate(remaining)
                if value.shape == shape and value.dtype == dtype
            ),
            None,
        )
        if match is None:
            available = [(value.shape, str(value.dtype)) for value in remaining]
            raise ExportError(
                f"cannot map LiteRT input {shape} {dtype}; available inputs: {available}"
            )
        interpreter.set_tensor(detail["index"], remaining.pop(match))
    interpreter.invoke()
    return [interpreter.get_tensor(detail["index"]) for detail in interpreter.get_output_details()]


def tensor_record(value: torch.Tensor) -> dict[str, object]:
    return {"shape": list(value.shape), "dtype": str(value.dtype).removeprefix("torch.")}


def build(args) -> dict[str, object]:
    output = Path(args.out_dir).resolve()
    project = Path(__file__).resolve().parents[1]
    if output == project or project in output.parents:
        raise ExportError("write generated model files outside the Android repository")
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()) and not args.replace:
        raise ExportError(f"output directory is not empty; use --replace: {output}")

    snapshot = resolve_snapshot(
        args.model_id,
        Path(args.cache_dir).expanduser().resolve(),
        args.revision,
    )
    from transformers import Siglip2VisionModel

    torch.manual_seed(args.seed)
    model = Siglip2VisionModel.from_pretrained(
        snapshot,
        local_files_only=True,
        torch_dtype=torch.float32,
        low_cpu_mem_usage=True,
    ).eval()
    vision = model.vision_model
    hidden_size = int(vision.config.hidden_size)
    position_grid = int(vision.embeddings.position_embedding_size)
    if vision.config.patch_size != PATCH_SIZE or position_grid <= 0 or hidden_size <= 0:
        raise ExportError("the source model does not match the Android NaFlex contract")

    grid_height, grid_width = sample_grid(args.max_num_patches)
    patches = torch.randn(1, args.max_num_patches, PATCH_VALUES, dtype=torch.float32)
    real_patch_count = grid_height * grid_width
    attention_mask = torch.zeros(1, args.max_num_patches, dtype=torch.int64)
    attention_mask[:, :real_patch_count] = 1
    encoder_attention_mask = backbone_attention_mask(attention_mask)
    spatial_shapes = torch.tensor([[grid_height, grid_width]], dtype=torch.int64)
    positions = positional_input(
        vision,
        spatial_shapes,
        args.max_num_patches,
        position_grid,
        hidden_size,
    ).float()
    backbone = NaFlexBackbone(vision).eval()
    if args.pooling == FOREGROUND_POOLING:
        pooling = NaFlexForegroundPooling(vision).eval()
        pooling_mask = torch.zeros(1, args.max_num_patches, dtype=torch.float32)
        foreground_pattern = torch.linspace(0.0, 1.0, real_patch_count)
        pooling_mask[:, :real_patch_count] = 0.1 + 0.9 * foreground_pattern
    else:
        pooling = NaFlexPooling(vision).eval()
        pooling_mask = attention_mask

    with torch.inference_mode():
        original = model(
            pixel_values=patches,
            pixel_attention_mask=attention_mask,
            spatial_shapes=spatial_shapes,
        ).pooler_output
        tokens = backbone(patches, positions, encoder_attention_mask)
        split = pooling(tokens, pooling_mask)
    # torch.export must receive a regular tensor. An inference tensor cannot be
    # saved for backward while the pooling graph is captured.
    tokens = tokens.clone()
    split_cosine = cosine(original, split) if args.pooling == STANDARD_POOLING else None
    split_max_error = maximum_error(original, split) if args.pooling == STANDARD_POOLING else None
    if (
        args.pooling == STANDARD_POOLING
        and (split_cosine < args.minimum_cosine or split_max_error > args.maximum_split_error)
    ):
        raise ExportError(
            f"PyTorch split parity failed: cosine={split_cosine}, max_error={split_max_error}"
        )

    positions_path = output / "siglip2_naflex_position_embeddings.f32"
    position_table = vision.embeddings.position_embedding.weight.detach().cpu().numpy()
    positions_path.write_bytes(position_table.astype("<f4", copy=False).tobytes(order="C"))
    backbone_path = output / "siglip2_naflex_backbone.tflite"
    pooling_path = output / "siglip2_naflex_pooling.tflite"
    if args.reuse_backbone_from:
        reuse_root = Path(args.reuse_backbone_from).resolve()
        reuse_metadata = json.loads((reuse_root / "metadata.json").read_text(encoding="utf-8"))
        if (
            reuse_metadata.get("model") != args.model_id
            or reuse_metadata.get("revision") != snapshot.name
            or reuse_metadata.get("max_num_patches") != args.max_num_patches
            or reuse_metadata.get("vector_dim") != hidden_size
        ):
            raise ExportError("--reuse-backbone-from has incompatible metadata")
        source_backbone = reuse_root / backbone_path.name
        if not source_backbone.is_file():
            raise ExportError("--reuse-backbone-from has no backbone model")
        shutil.copyfile(source_backbone, backbone_path)
    if args.reuse_models:
        if not backbone_path.is_file() or not pooling_path.is_file():
            raise ExportError("--reuse-models requires both exported LiteRT models")
    elif args.reuse_backbone_from:
        with tempfile.TemporaryDirectory(prefix="siglip2-naflex-litert-") as temporary:
            pooling_float = Path(temporary) / "pooling-float32.tflite"
            convert_model(pooling, (tokens, pooling_mask), pooling_float)
            quantize_float16_fully_connected(pooling_float, pooling_path)
    else:
        with tempfile.TemporaryDirectory(prefix="siglip2-naflex-litert-") as temporary:
            temporary = Path(temporary)
            backbone_float = temporary / "backbone-float32.tflite"
            pooling_float = temporary / "pooling-float32.tflite"
            convert_model(
                backbone,
                (patches, positions, encoder_attention_mask),
                backbone_float,
            )
            convert_model(pooling, (tokens, pooling_mask), pooling_float)
            quantize_float16_fully_connected(backbone_float, backbone_path)
            quantize_float16_fully_connected(pooling_float, pooling_path)

    backbone_values = [
        patches.detach().cpu().numpy(),
        positions.detach().cpu().numpy(),
        encoder_attention_mask.detach().cpu().numpy(),
    ]
    litert_tokens = torch.from_numpy(run_litert(backbone_path, backbone_values)[0])
    pooling_values = [
        litert_tokens.detach().cpu().numpy(),
        pooling_mask.detach().cpu().numpy(),
    ]
    litert_output = torch.from_numpy(run_litert(pooling_path, pooling_values)[0])
    backbone_cosine = cosine(tokens, litert_tokens)
    backbone_max_error = maximum_error(tokens, litert_tokens)
    pooling_cosine = cosine(split, litert_output)
    pooling_max_error = maximum_error(split, litert_output)
    end_to_end_cosine = (
        cosine(original, litert_output) if args.pooling == STANDARD_POOLING else None
    )
    required_cosines = [backbone_cosine, pooling_cosine]
    if end_to_end_cosine is not None:
        required_cosines.append(end_to_end_cosine)
    if min(required_cosines) < args.minimum_cosine:
        raise ExportError("LiteRT parity is below the required cosine")

    files = {}
    for path in (backbone_path, pooling_path, positions_path):
        files[path.name] = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
    metadata = {
        "format": "svoe-vino-siglip2-naflex-split",
        "format_version": 1,
        "created_at_epoch_ms": int(time.time() * 1000),
        "model": args.model_id,
        "revision": snapshot.name,
        "source_snapshot": str(snapshot),
        "patch_size": PATCH_SIZE,
        "max_num_patches": args.max_num_patches,
        "position_embedding_grid": position_grid,
        "vector_dim": hidden_size,
        "pooling_mode": args.pooling,
        "backbone_inputs": [
            tensor_record(patches),
            tensor_record(positions),
            tensor_record(encoder_attention_mask),
        ],
        "backbone_output": tensor_record(tokens),
        "pooling_inputs": [tensor_record(tokens), tensor_record(pooling_mask)],
        "pooling_output": tensor_record(split),
        "parity": {
            "pytorch_split_cosine": split_cosine,
            "pytorch_split_max_abs_error": split_max_error,
            "litert_backbone_cosine": backbone_cosine,
            "litert_backbone_max_abs_error": backbone_max_error,
            "litert_pooling_cosine": pooling_cosine,
            "litert_pooling_max_abs_error": pooling_max_error,
            "litert_end_to_end_cosine": end_to_end_cosine,
        },
        "tools": {
            "torch": torch.__version__,
            "transformers": package_version("transformers"),
            "litert-torch": package_version("litert-torch"),
            "ai-edge-litert": package_version("ai-edge-litert"),
            "ai-edge-quantizer": package_version("ai-edge-quantizer"),
        },
        "files": files,
    }
    metadata_path = output / "metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {"output": str(output), **metadata}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--model-id", default=MODEL_ID)
    parser.add_argument("--revision")
    parser.add_argument("--cache-dir", default=str(Path.home() / ".cache" / "huggingface" / "hub"))
    parser.add_argument("--max-num-patches", type=int, choices=SUPPORTED_PATCH_LIMITS, default=512)
    parser.add_argument("--pooling", choices=SUPPORTED_POOLING, default=STANDARD_POOLING)
    parser.add_argument("--seed", type=int, default=20261019)
    parser.add_argument("--minimum-cosine", type=float, default=0.999)
    parser.add_argument("--maximum-split-error", type=float, default=1e-5)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--reuse-models", action="store_true")
    parser.add_argument("--reuse-backbone-from")
    args = parser.parse_args(argv)
    try:
        result = build(args)
    except (ExportError, OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
