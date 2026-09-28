"""Image-embedding HTTP service — SigLIP2, DINOv3, timm NaFlexViT and Meta PE-Core.

Loopback-only FastAPI app serving the OpenAI route POST /v1/embeddings.
The gateway routes each request by the `model` field.
Run one process for each model ID.

Backends (--backend):
  transformers  AutoModel checkpoints: SigLIP2 (image+text), DINOv3 (image-only)
  timm          timm hf-hub checkpoints, e.g. timm/naflexvit_so400m_patch16_siglip.v2_webli (image-only)
  pe            Meta Perception Encoder CLIP, e.g. facebook/PE-Core-L14-336 (image+text).
                Code vendored under ./core/vision_encoder from facebookresearch/perception_models.

NaFlex models (SigLIP2 NaFlex, timm NaFlexViT) take a patch budget: --max-num-patches is the
default, and a request may override it with the non-OpenAI field `max_num_patches`.
"""

import argparse
import base64
import binascii
import io
import re
import struct
import threading

import torch
import torch.nn.functional as F
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from PIL import Image, ImageDraw
from pydantic import BaseModel, Field
from transformers import AutoImageProcessor, AutoModel, AutoProcessor

DATA_URI_RE = re.compile(r"^data:image/[a-zA-Z0-9.+-]+;base64,", re.IGNORECASE)
MAX_NUM_PATCHES_LIMIT = 4096  # upper bound for a request override; bounds memory per image
GATEWAY = "http://127.0.0.1:18090"

args = None
model = None
processor = None   # transformers: AutoProcessor / AutoImageProcessor; pe: image transform
tokenizer = None   # pe only
device = "cpu"
dtype = torch.float32
has_text_tower = False
is_naflex = False
embed_dim = None
_lock = threading.Lock()


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

app = FastAPI(
    title="img-embed",
    description="SigLIP2 / DINOv3 / NaFlexViT / PE-Core image embeddings. The model-specific text is set after load.",
    version="2.0.0",
    openapi_tags=[
        {"name": "embeddings", "description": "OpenAI-compatible embeddings for images (and text, where the model has a text tower)."},
        {"name": "ops", "description": "Model info and health."},
    ],
    # "." = relative to the spec URL, so "Try it out" also works under /upstream/<id>/.
    servers=[{"url": "."}],
    docs_url=None,
    redoc_url=None,
)


class EmbeddingsRequest(BaseModel):
    input: str | list[str] = Field(
        description=(
            "One item or a batch (max `--max-batch`, default 64). An item that starts with "
            "`data:image/<type>;base64,` is an image; any other string is text. Text on an image-only "
            "model returns 400. No URLs or file paths: base64 the file on the client."
        ),
    )
    model: str | None = Field(
        default=None,
        description="Model id. The gateway routes on it; this process serves one model and echoes its id.",
    )
    encoding_format: str = Field(
        default="float",
        description="`float` (JSON list) or `base64` (little-endian float32 packing).",
    )
    max_num_patches: int | None = Field(
        default=None,
        description=(
            f"Local extension, NaFlex models only. Maximum number of 16x16 px patches per image; the "
            f"image is resized at its native aspect ratio to fit. Range 1..{MAX_NUM_PATCHES_LIMIT}. "
            "Omit it to use the server default (`--max-num-patches`). With the OpenAI SDK pass it as "
            "`extra_body={\"max_num_patches\": 512}`. Vectors made with different budgets do not "
            "belong in one index."
        ),
    )


class EmbeddingItem(BaseModel):
    object: str = "embedding"
    index: int = Field(description="Position of the item in `input`.")
    embedding: list[float] | str = Field(description="L2-normalized vector, or its base64 packing.")


class Usage(BaseModel):
    prompt_tokens: int = Field(description="Number of input items, not tokens (images have no tokens).")
    total_tokens: int


class EmbeddingsResponse(BaseModel):
    object: str = "list"
    data: list[EmbeddingItem]
    model: str
    usage: Usage


class InfoResponse(BaseModel):
    served_model: str
    checkpoint: str = Field(description="HF repo id.")
    backend: str = Field(description="Loader: transformers, timm or pe.")
    modalities: list[str] = Field(description='["image"] or ["image", "text"].')
    dim: int | None = Field(description="Vector length.")
    max_num_patches: int | None = Field(description="Default NaFlex patch budget; null when the model is not NaFlex.")
    device: str


class HealthResponse(BaseModel):
    status: str
    model: str
    device: str


class ErrorResponse(BaseModel):
    detail: str


ERRORS = {
    400: {"model": ErrorResponse, "description": "Bad request: text on an image-only model, a malformed image, "
          "`max_num_patches` out of range or on a non-NaFlex model, or a batch over `--max-batch`."},
    503: {"model": ErrorResponse, "description": "Model still loading."},
}


@app.on_event("startup")
def load_model() -> None:
    """Load the checkpoint named by --model with the loader named by --backend."""
    global dtype
    if args.dtype == "auto":
        dtype = torch.bfloat16 if device == "cuda" else torch.float16 if device == "mps" else torch.float32
    else:
        dtype = getattr(torch, args.dtype, torch.float32)
    print(f"Loading {args.model} on {device} ({dtype}, backend {args.backend})...", flush=True)
    {"transformers": _load_transformers, "timm": _load_timm, "pe": _load_pe}[args.backend]()
    model.eval()
    app.title = f"{args.served_name} — image embeddings"
    app.description = _describe()
    app.openapi_schema = None  # rebuild with the model-specific text and examples
    print(f"{args.served_name} loaded (text tower: {has_text_tower}, naflex: {is_naflex}, dim: {embed_dim})", flush=True)


def _load_transformers() -> None:
    global model, processor, has_text_tower, is_naflex, embed_dim
    model = AutoModel.from_pretrained(
        args.model, dtype=dtype, local_files_only=True
    ).to(device)
    has_text_tower = hasattr(model, "get_text_features")
    # SigLIP ships a full processor (tokenizer + image); DINOv3 is vision-only.
    processor = (AutoProcessor if has_text_tower else AutoImageProcessor).from_pretrained(
        args.model, local_files_only=True
    )
    image_processor = getattr(processor, "image_processor", processor)
    is_naflex = hasattr(image_processor, "max_num_patches")
    cfg = model.config
    vision = getattr(cfg, "vision_config", cfg)
    embed_dim = getattr(cfg, "projection_dim", None) or getattr(vision, "hidden_size", None)


def _load_timm() -> None:
    global model, has_text_tower, is_naflex, embed_dim
    import timm

    model = timm.create_model(f"hf-hub:{args.model}", pretrained=True, num_classes=0).to(device, dtype)
    has_text_tower = False  # timm checkpoints are vision towers only
    is_naflex = type(model).__name__ == "NaFlexVit"
    if not is_naflex:
        raise SystemExit(f"--backend timm supports NaFlexVit models only, got {type(model).__name__}")
    embed_dim = model.num_features


def _load_pe() -> None:
    global model, processor, tokenizer, has_text_tower, is_naflex, embed_dim
    import core.vision_encoder.pe as pe
    import core.vision_encoder.transforms as pe_transforms

    # from_config fetches facebook/<name>:<name>.pt through hf_hub_download (HF cache, offline).
    name = args.model.split("/")[-1]
    model = pe.CLIP.from_config(name, pretrained=True).to(device, dtype)
    processor = pe_transforms.get_image_transform(model.image_size)
    tokenizer = pe_transforms.get_text_tokenizer(model.context_length)
    has_text_tower = True
    is_naflex = False
    embed_dim = model.visual.proj_dim


def _describe() -> str:
    """Model-specific OpenAPI description: capabilities, how to call, errors."""
    sid = args.served_name
    modal = "image **and** text, one shared space" if has_text_tower else "image only (no text tower)"
    naflex = (
        f"yes — default {args.max_num_patches} patches, per request `max_num_patches` 1..{MAX_NUM_PATCHES_LIMIT}"
        if is_naflex else "no — `max_num_patches` returns 400"
    )
    budget = ', extra_body={"max_num_patches": 512}' if is_naflex else ""
    query = (
        f'q = client.embeddings.create(model="{sid}", input="a red square").data[0].embedding\n'
        if has_text_tower else ""
    )
    return (
        f"Embeddings from the local snapshot `{args.model}`.\n\n"
        f"| | |\n|---|---|\n"
        f"| Model id | `{sid}` |\n| Checkpoint | `{args.model}` (backend `{args.backend}`) |\n"
        f"| Input | {modal} |\n| Vector | {embed_dim}-d, L2-normalized (cosine = dot product) |\n"
        f"| NaFlex | {naflex} |\n| Batch | up to {args.max_batch} items per request |\n\n"
        f"**Call it through the gateway**: `POST {GATEWAY}/v1/embeddings` with `\"model\": \"{sid}\"`. "
        f"The bootstrap launcher starts the selected model. \"Try it out\" on this page sends the request to "
        f"this model directly (`/upstream/{sid}/`).\n\n"
        "**Images** go in `input` as `data:image/<type>;base64,<payload>` strings. Any other string is "
        f"text{'' if has_text_tower else ', and text returns 400 on this model'}.\n\n"
        "**OpenAI SDK** (Python):\n\n"
        "```python\nfrom openai import OpenAI\n"
        f'client = OpenAI(base_url="{GATEWAY}/v1", api_key="unused")\n'
        f'v = client.embeddings.create(model="{sid}", input=["data:image/jpeg;base64,..."]{budget}).data[0].embedding\n'
        f"{query}```\n\n"
        "**Rules**: one model per index; never mix vectors of different models"
        f"{' or different `max_num_patches` values' if is_naflex else ''}. Cosine values are not "
        "calibrated: rank, do not threshold.\n\n"
        "**Errors**: 400 bad input (see the endpoint), 503 still loading. The gateway returns 404 for "
        "an unknown model id and 429 above 10 requests in flight per model.\n\n"
        "The runtime uses local files and Hugging Face offline mode."
    )


def _example_image_uri() -> str:
    im = Image.new("RGB", (96, 64), "white")
    ImageDraw.Draw(im).rectangle((24, 8, 72, 56), fill="red")
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _openapi() -> dict:
    """Default schema plus per-model request examples (a working 96x64 PNG is embedded)."""
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(title=app.title, version=app.version, description=app.description,
                         routes=app.routes, tags=app.openapi_tags, servers=app.servers)
    if args is not None and model is not None:
        sid, img = args.served_name, _example_image_uri()
        examples = {"image": {"summary": "One image", "value": {"model": sid, "input": [img]}}}
        if has_text_tower:
            examples["text"] = {"summary": "One text query", "value": {"model": sid, "input": "a red square"}}
            examples["mixed"] = {"summary": "Image and text in one batch",
                                 "value": {"model": sid, "input": [img, "a red square"]}}
        if is_naflex:
            examples["budget"] = {"summary": "Image with a 512-patch budget",
                                  "value": {"model": sid, "input": [img], "max_num_patches": 512}}
        examples["base64"] = {"summary": "Base64-packed output",
                              "value": {"model": sid, "input": [img], "encoding_format": "base64"}}
        body = schema["paths"]["/v1/embeddings"]["post"]["requestBody"]["content"]["application/json"]
        body["examples"] = examples
        if not is_naflex:
            prop = schema["components"]["schemas"]["EmbeddingsRequest"]["properties"]["max_num_patches"]
            prop["description"] = f"**Not supported by `{sid}`: sending it returns 400.** " + prop["description"]
    app.openapi_schema = schema
    return schema


app.openapi = _openapi


@app.get("/docs", include_in_schema=False)
def docs():
    """Swagger UI. The OpenAPI URL is relative so it also works under /upstream/<id>/."""
    return get_swagger_ui_html(openapi_url="openapi.json", title=f"{args.served_name} API")


@app.get("/", tags=["ops"], summary="Model info: id, checkpoint, modalities, vector size, NaFlex budget")
def info() -> InfoResponse:
    return InfoResponse(
        served_model=args.served_name,
        checkpoint=args.model,
        backend=args.backend,
        modalities=["image", "text"] if has_text_tower else ["image"],
        dim=embed_dim,
        max_num_patches=args.max_num_patches if is_naflex else None,
        device=device,
    )


@app.get("/health", tags=["ops"], summary="Liveness", responses={503: ERRORS[503]})
def health() -> HealthResponse:
    if model is None:
        raise HTTPException(status_code=503, detail="model still loading")
    return {"status": "ok", "model": args.served_name, "device": device}


def _decode_image(item: str) -> Image.Image:
    payload = DATA_URI_RE.sub("", item, count=1)
    try:
        raw = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"malformed base64 image: {exc}") from exc
    try:
        return Image.open(io.BytesIO(raw)).convert("RGB")
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"not a decodable image: {exc}") from exc


def _pooled(out) -> torch.Tensor:
    """transformers 5.x returns a ModelOutput from get_*_features, not a bare tensor."""
    if isinstance(out, torch.Tensor):
        return out
    pooled = getattr(out, "pooler_output", None)
    if pooled is None:
        raise HTTPException(status_code=500, detail=f"no pooler_output on {type(out).__name__}")
    return pooled


def _timm_naflex_batch(images: list[Image.Image], max_num_patches: int) -> dict:
    """Resize each image to fit the patch budget at native aspect, patchify, pad to one batch."""
    from torchvision.transforms import functional as TF
    from timm.data.naflex_transforms import Patchify, ResizeToSequence

    cfg = model.pretrained_cfg
    patch = model.embeds.patch_size[0] if isinstance(model.embeds.patch_size, (tuple, list)) else model.embeds.patch_size
    resize = ResizeToSequence(patch, max_seq_len=max_num_patches, interpolation=cfg.get("interpolation", "bicubic"))
    patchify = Patchify(patch)
    items = []
    for img in images:
        x = TF.normalize(resize(TF.to_tensor(img)), cfg["mean"], cfg["std"])
        items.append(patchify(x))
    n = max(it["patches"].shape[0] for it in items)
    batch = {
        "patches": torch.zeros((len(items), n, items[0]["patches"].shape[1])),
        "patch_coord": torch.zeros((len(items), n, 2), dtype=torch.int64),
        "patch_valid": torch.zeros((len(items), n), dtype=torch.bool),
    }
    for i, it in enumerate(items):
        k = it["patches"].shape[0]
        batch["patches"][i, :k] = it["patches"]
        batch["patch_coord"][i, :k] = it["patch_coord"]
        batch["patch_valid"][i, :k] = it["patch_valid"]
    batch["patches"] = batch["patches"].to(device, dtype)
    batch["patch_coord"] = batch["patch_coord"].to(device)
    batch["patch_valid"] = batch["patch_valid"].to(device)
    return batch


@torch.inference_mode()
def _embed_images(images: list[Image.Image], max_num_patches: int | None) -> torch.Tensor:
    if args.backend == "timm":
        return model(_timm_naflex_batch(images, max_num_patches))
    if args.backend == "pe":
        batch = torch.stack([processor(img) for img in images]).to(device, dtype)
        return model.encode_image(batch)
    kwargs = {"max_num_patches": max_num_patches} if is_naflex else {}
    batch = processor(images=images, return_tensors="pt", **kwargs).to(device)
    if has_text_tower:
        return _pooled(model.get_image_features(**batch))
    # DINOv3: the CLS-token pooler output is the recommended global descriptor.
    return _pooled(model(**batch))


@torch.inference_mode()
def _embed_texts(texts: list[str]) -> torch.Tensor:
    if not has_text_tower:
        raise HTTPException(
            status_code=400,
            detail=f"{args.served_name} is image-only (no text tower) — send data:image/... URIs, not prose",
        )
    if args.backend == "pe":
        return model.encode_text(tokenizer(texts).to(device))
    # SigLIP was trained with fixed 64-token max_length padding; other padding hurts it.
    batch = processor(text=texts, padding="max_length", truncation=True, return_tensors="pt").to(device)
    return _pooled(model.get_text_features(**batch))


def _pack(vec: list[float], encoding_format: str):
    if encoding_format == "base64":
        return base64.b64encode(struct.pack(f"<{len(vec)}f", *vec)).decode()
    return vec


@app.post(
    "/v1/embeddings",
    tags=["embeddings"],
    summary="Embed images (and text, where the model has a text tower)",
    description="One vector per `input` item, in input order. Images and text may be mixed in one batch "
                "on image+text models; the server splits them by tower and restores the order.",
    response_model=EmbeddingsResponse,
    responses=ERRORS,
)
def embeddings(req: EmbeddingsRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="model still loading")
    if req.encoding_format not in ("float", "base64"):
        raise HTTPException(status_code=400, detail="encoding_format must be 'float' or 'base64'")
    if req.max_num_patches is not None:
        if not is_naflex:
            raise HTTPException(status_code=400, detail=f"{args.served_name} is not a NaFlex model; max_num_patches is not supported")
        if not 1 <= req.max_num_patches <= MAX_NUM_PATCHES_LIMIT:
            raise HTTPException(status_code=400, detail=f"max_num_patches must be 1..{MAX_NUM_PATCHES_LIMIT}")
    max_num_patches = req.max_num_patches or args.max_num_patches
    items = [req.input] if isinstance(req.input, str) else list(req.input)
    if not items:
        raise HTTPException(status_code=400, detail="input must not be empty")
    if len(items) > args.max_batch:
        raise HTTPException(status_code=400, detail=f"batch of {len(items)} exceeds --max-batch {args.max_batch}")

    # Images and text go through different towers, so split, embed, then restore input order.
    image_idx = [i for i, s in enumerate(items) if DATA_URI_RE.match(s)]
    text_idx = [i for i in range(len(items)) if i not in set(image_idx)]
    out: list[torch.Tensor | None] = [None] * len(items)
    with _lock:
        if image_idx:
            vecs = _embed_images([_decode_image(items[i]) for i in image_idx], max_num_patches)
            for slot, vec in zip(image_idx, vecs):
                out[slot] = vec
        if text_idx:
            vecs = _embed_texts([items[i] for i in text_idx])
            for slot, vec in zip(text_idx, vecs):
                out[slot] = vec

    stacked = F.normalize(torch.stack(out).float(), p=2, dim=-1).cpu().tolist()
    return {
        "object": "list",
        "data": [
            {"object": "embedding", "index": i, "embedding": _pack(v, req.encoding_format)}
            for i, v in enumerate(stacked)
        ],
        "model": args.served_name,
        # No tokenizer runs for images, so this counts inputs, not tokens.
        "usage": {"prompt_tokens": len(items), "total_tokens": len(items)},
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", required=True, help="HF repo id of the checkpoint to serve")
    p.add_argument("--backend", default="transformers", choices=["transformers", "timm", "pe"])
    p.add_argument("--served-name", help="model id echoed in responses (default: last path segment of --model)")
    p.add_argument("--port", type=int, required=True)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--device", default="auto", choices=["auto", "cuda", "mps", "cpu"])
    p.add_argument("--dtype", default="auto", choices=["auto", "float32", "bfloat16", "float16"])
    p.add_argument("--max-batch", type=int, default=64)
    p.add_argument("--max-num-patches", type=int, default=256,
                   help="NaFlex default patch budget; a request may override it with max_num_patches")
    args = p.parse_args()
    args.served_name = args.served_name or args.model.split("/")[-1]
    device = _select_device(args.device)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
