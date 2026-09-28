"""ShieldGemma 2 HTTP service for the portable hackathon bootstrap.

The compatibility gateway forwards the public model path to this loopback service.
The service reads a local model snapshot and does not contact Hugging Face.

One image per request. The processor builds one prompt per <image, policy> pair,
and the model returns P(Yes) and P(No) for the next token of each prompt.
"Yes" means the image violates the policy, so the score is probabilities[:, 0].
The transformers 5.3 docstring says [:, 1]; that is wrong (index 1 is "No").

The GPU forward runs under one lock. One forward already fills the GB10, so
parallel forwards would only compete for it.
"""

import argparse
import io
import math
import threading
from contextlib import asynccontextmanager

import torch
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.openapi.docs import get_swagger_ui_html
from PIL import Image
from pydantic import BaseModel, Field
from transformers import AutoProcessor, ShieldGemma2ForImageClassification

DTYPES = {"bfloat16": torch.bfloat16, "float16": torch.float16, "float32": torch.float32}

args = None
model = None
processor = None
device = "cpu"
gpu_lock = threading.Lock()


def _select_device(requested: str) -> str:
    if requested != "auto":
        if requested == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("CUDA was requested but is not available")
        if requested == "mps" and not torch.backends.mps.is_available():
            raise RuntimeError("MPS was requested but is not available")
        return requested
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, processor
    print(f"Loading {args.model} on {device} (dtype={args.dtype})...", flush=True)
    processor = AutoProcessor.from_pretrained(args.model, local_files_only=True)
    model = ShieldGemma2ForImageClassification.from_pretrained(
        args.model, dtype=DTYPES[args.dtype], local_files_only=True
    )
    # The checkpoint has no lm_head: Gemma 3 ties it to the token embeddings.
    # transformers 5.3.0 does not apply that tie through this wrapper class, so
    # lm_head stays randomly initialised (load report: "model.lm_head.weight
    # MISSING") and the Yes/No scores are noise. Tie it by hand.
    embed = model.model.model.language_model.embed_tokens
    model.model.lm_head.weight = embed.weight
    model.to(device).eval()
    if model.model.lm_head.weight.data_ptr() != embed.weight.data_ptr():
        raise RuntimeError("lm_head is not tied to embed_tokens; scores would be noise")
    print(f"{args.served_name} loaded, policies: {', '.join(processor.policy_definitions)}", flush=True)
    yield


app = FastAPI(
    title="shieldgemma2",
    description=(
        "ShieldGemma 2 — image safety classification against the three built-in policies "
        "(`dangerous`, `sexual`, `violence`).\n\n"
        "The portable compatibility gateway serves this endpoint under "
        "`/upstream/shieldgemma-2-4b-it/classify`."
    ),
    version="1.0.0",
    openapi_tags=[
        {"name": "safety", "description": "Classify one image against the safety policies."},
        {"name": "ops", "description": "Health."},
    ],
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)


class ClassifyResponse(BaseModel):
    model: str
    width: int
    height: int
    threshold: float
    scores: dict[str, float] = Field(description="Policy -> P(Yes), the probability that the image violates it.")
    flagged: list[str] = Field(description="Policies whose score is >= threshold.")


class HealthResponse(BaseModel):
    status: str
    model: str
    served_name: str
    device: str
    dtype: str
    policies: list[str]


@app.get("/docs", include_in_schema=False)
def docs():
    """Swagger UI. The OpenAPI URL is relative so it also works under /upstream/<id>/."""
    return get_swagger_ui_html(openapi_url="openapi.json", title=f"{args.served_name} API")


@app.get("/health", tags=["ops"], summary="Liveness and current configuration")
def health() -> HealthResponse:
    if model is None:
        raise HTTPException(status_code=503, detail="model still loading")
    return HealthResponse(
        status="ok", model=args.model, served_name=args.served_name, device=device,
        dtype=args.dtype, policies=list(processor.policy_definitions),
    )


@app.post("/classify", tags=["safety"], summary="Score one image against the safety policies",
          responses={200: {"model": ClassifyResponse}})
def classify(
    image: UploadFile = File(..., description="The image to classify."),
    policies: str = Form("", description='Comma-separated subset, e.g. "sexual, violence". Empty = all three.'),
    threshold: float = Form(0.5, description="Score cut-off for `flagged`, 0-1."),
):
    """Returns P(Yes) per policy. "Yes" means the image violates that policy."""
    if model is None:
        raise HTTPException(status_code=503, detail="model still loading")

    known = list(processor.policy_definitions)
    selected = [p.strip().lower() for p in policies.split(",") if p.strip()] or known
    unknown = [p for p in selected if p not in known]
    if unknown:
        raise HTTPException(status_code=400, detail=f"unknown policies {unknown}; known: {known}")

    try:
        img = Image.open(io.BytesIO(image.file.read())).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"bad image: {exc}")

    inputs = processor(images=[img], policies=selected, return_tensors="pt").to(device, dtype=model.dtype)
    with gpu_lock, torch.inference_mode():
        probabilities = model(**inputs).probabilities
    p_yes = probabilities[:, 0].float().cpu().tolist()
    if not all(math.isfinite(value) for value in p_yes):
        raise HTTPException(
            status_code=500,
            detail=f"model returned a non-finite score with dtype {args.dtype} on {device}",
        )

    scores = {policy: round(p, 6) for policy, p in zip(selected, p_yes)}
    return {
        "model": args.served_name,
        "width": img.width,
        "height": img.height,
        "threshold": threshold,
        "scores": scores,
        "flagged": [policy for policy, p in scores.items() if p >= threshold],
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", default="google/shieldgemma-2-4b-it", help="HF repo id of the checkpoint")
    p.add_argument("--served-name", help="model id echoed in responses (default: last path segment of --model)")
    p.add_argument("--port", type=int, required=True)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--device", default="auto", choices=["auto", "cuda", "mps", "cpu"])
    p.add_argument("--dtype", default="float16", choices=sorted(DTYPES), help="weights dtype")
    args = p.parse_args()
    args.served_name = args.served_name or args.model.split("/")[-1]
    device = _select_device(args.device)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
