#!/usr/bin/env python3
"""Export SigLIP2 Base NaFlex p512 for the fixed square iPhone pipeline."""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

os.environ.setdefault("TMPDIR", "/private/tmp/chtozavino-coreml-tmp")
Path(os.environ["TMPDIR"]).mkdir(parents=True, exist_ok=True)

import coremltools as ct
import numpy as np
import torch
from transformers import AutoModel


MODEL_ID = "google/siglip2-base-patch16-naflex"
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "ChtoZaVino/Resources/Models/SigLIP2BaseNaFlexP512ImageEncoder.mlpackage"
MODEL_CACHE = Path.home() / ".cache/huggingface/hub/models--google--siglip2-base-patch16-naflex/snapshots"


class SquareNaFlexEncoder(torch.nn.Module):
    """Use the 484 valid tokens produced by a square p512 input."""

    def __init__(self, vision: torch.nn.Module) -> None:
        super().__init__()
        self.vision = vision
        positions = vision.embeddings.position_embedding.weight.reshape(16, 16, -1)
        positions = vision.embeddings.resize_positional_embeddings(positions, torch.tensor([[22, 22]]), 484)
        self.register_buffer("positions", positions)

        attention = vision.head.attention
        self.query = torch.nn.Linear(768, 768)
        self.key = torch.nn.Linear(768, 768)
        self.value = torch.nn.Linear(768, 768)
        self.output = torch.nn.Linear(768, 768)
        with torch.no_grad():
            self.query.weight.copy_(attention.in_proj_weight[:768])
            self.query.bias.copy_(attention.in_proj_bias[:768])
            self.key.weight.copy_(attention.in_proj_weight[768:1536])
            self.key.bias.copy_(attention.in_proj_bias[768:1536])
            self.value.weight.copy_(attention.in_proj_weight[1536:])
            self.value.bias.copy_(attention.in_proj_bias[1536:])
            self.output.load_state_dict(attention.out_proj.state_dict())
        self.probe = vision.head.probe
        self.pool_layer_norm = vision.head.layernorm
        self.pool_mlp = vision.head.mlp

    def forward(self, patches: torch.Tensor) -> torch.Tensor:
        values = self.vision.embeddings.patch_embedding(patches) + self.positions
        values = self.vision.encoder(inputs_embeds=values, attention_mask=None).last_hidden_state
        values = self.vision.post_layernorm(values)
        query = self.query(self.probe).view(1, 1, 12, 64).transpose(1, 2)
        key = self.key(values).view(1, 484, 12, 64).transpose(1, 2)
        value = self.value(values).view(1, 484, 12, 64).transpose(1, 2)
        weights = torch.softmax(torch.matmul(query, key.transpose(-1, -2)) * 0.125, dim=-1)
        pooled = torch.matmul(weights, value).transpose(1, 2).reshape(1, 1, 768)
        pooled = self.output(pooled)
        pooled = pooled + self.pool_mlp(self.pool_layer_norm(pooled))
        return pooled[:, 0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    snapshots = sorted(path for path in MODEL_CACHE.glob("*") if path.is_dir())
    source: str | Path = snapshots[-1] if snapshots else MODEL_ID
    full = AutoModel.from_pretrained(source, local_files_only=bool(snapshots), attn_implementation="eager").eval()
    wrapped = SquareNaFlexEncoder(full.vision_model).eval()
    example = torch.zeros(1, 484, 768)
    traced = torch.jit.trace(wrapped, example, strict=True)
    model = ct.convert(
        traced,
        convert_to="mlprogram",
        minimum_deployment_target=ct.target.iOS17,
        compute_precision=ct.transform.FP16ComputePrecision(
            op_selector=lambda operation: operation.op_type not in {"layer_norm", "softmax"}
        ),
        inputs=[ct.TensorType(name="patches", shape=example.shape, dtype=np.float32)],
        outputs=[ct.TensorType(name="embedding", dtype=np.float32)],
    )
    model.author = "Google SigLIP2 export for Что за вино?"
    model.license = "Apache-2.0 model license. See the upstream model card."
    model.short_description = "google/siglip2-base-patch16-naflex p512 square image encoder"
    model.user_defined_metadata.update({
        "model_id": MODEL_ID,
        "max_num_patches": "512",
        "patch_grid": "22x22",
        "vector_dimension": "768",
    })
    if args.output.exists():
        shutil.rmtree(args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    model.save(str(args.output))

    loaded = ct.models.MLModel(str(args.output), compute_units=ct.ComputeUnit.CPU_ONLY)
    sample = np.random.default_rng(0).normal(size=(1, 484, 768)).astype(np.float32)
    expected = traced(torch.from_numpy(sample)).detach().numpy().reshape(-1)
    actual = loaded.predict({"patches": sample})["embedding"].reshape(-1)
    cosine = float(np.dot(expected, actual) / (np.linalg.norm(expected) * np.linalg.norm(actual)))
    print(f"Core ML cosine against PyTorch: {cosine:.8f}")
    if cosine < 0.999:
        raise SystemExit("Core ML NaFlex export does not match PyTorch")
    print(args.output)


if __name__ == "__main__":
    main()
