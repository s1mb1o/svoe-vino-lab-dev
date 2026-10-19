"""Real text embeddings, immutable artifact validation, and exact cosine search."""
from __future__ import annotations

import concurrent.futures
import hashlib
import http.client
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np

from .data import Knowledge, canonical, digest
from .configuration import EmbeddingSettings, secret

MODEL = "qwen3.7-text-embedding"
ENDPOINT = "https://maas.qwencloudapi.com/compatible-mode/v1/embeddings"
DIMENSIONS = 1024


def request_vectors(texts: list[str], *, timeout: float | None = None, settings: EmbeddingSettings | None = None) -> tuple[np.ndarray, dict]:
    settings = settings or EmbeddingSettings()
    if not 1 <= len(texts) <= 20:
        raise ValueError("Embedding batch must contain 1 to 20 texts")
    key = secret(settings.api_key_env, required=False)
    if not key:
        raise RuntimeError("QWENCLOUD_PAYGO_API_KEY is required to build an embedding index")
    body = canonical({"model": settings.model, "input": texts, "dimensions": settings.dimensions,
                      "encoding_format": "float"}).encode()
    started = time.monotonic()
    for attempt in range(settings.attempts):
        try:
            req = urllib.request.Request(settings.endpoint, data=body, headers={
                "Content-Type": "application/json", "Authorization": "Bearer " + key})
            with urllib.request.urlopen(req, timeout=timeout or settings.socket_timeout_seconds) as response:
                value = json.load(response)
            if value.get("model") != settings.model:
                raise RuntimeError("Embedding model mismatch")
            entries = sorted(value["data"], key=lambda row: row["index"])
            if [e["index"] for e in entries] != list(range(len(texts))):
                raise RuntimeError("Embedding response indices are incomplete or duplicated")
            array = np.asarray([e["embedding"] for e in entries], dtype=np.float32)
            if array.shape != (len(texts), settings.dimensions) or not np.isfinite(array).all():
                raise RuntimeError("Invalid embedding shape or numeric values")
            norms = np.linalg.norm(array, axis=1, keepdims=True)
            if np.any(norms <= 1e-12):
                raise RuntimeError("Zero-length embedding")
            array = array / norms
            return array, {"requested_model": settings.model, "returned_model": value["model"],
                           "request_sha256": hashlib.sha256(body).hexdigest(),
                           "usage": value.get("usage", {}), "attempts": attempt + 1,
                           "latency_seconds": round(time.monotonic() - started, 3)}
        except urllib.error.HTTPError as exc:
            # Never expose credential-bearing request headers or unrestricted provider bodies.
            if exc.code not in {429, 500, 502, 503, 504} or attempt == settings.attempts - 1:
                raise RuntimeError("Embedding provider HTTP " + str(exc.code)) from None
            time.sleep(2 ** (attempt + 1))
        except (TimeoutError, OSError, http.client.HTTPException, json.JSONDecodeError):
            if attempt == settings.attempts - 1:
                raise RuntimeError("Embedding provider transport failure") from None
            time.sleep(2 ** (attempt + 1))
    raise RuntimeError("Embedding request failed")


def build_index(knowledge: Knowledge, directory: str | Path, workers: int | None = None, *, settings: EmbeddingSettings | None = None) -> dict:
    settings = settings or EmbeddingSettings()
    directory = Path(directory)
    cache = directory / "embedding-cache"
    cache.mkdir(parents=True, exist_ok=True)
    docs = knowledge.embedding_documents()
    groups = [docs[i:i + 20] for i in range(0, len(docs), 20)]

    def embed(group):
        identity = digest({"model": settings.model, "dimensions": settings.dimensions, "documents": group})
        path = cache / (identity + ".npz")
        meta_path = cache / (identity + ".json")
        if path.exists() and meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if hashlib.sha256(path.read_bytes()).hexdigest() != meta["array_sha256"]:
                raise ValueError("Embedding batch cache was modified")
            with np.load(path, allow_pickle=False) as stored:
                vectors = stored["vectors"].copy()
            return vectors, meta
        vectors, receipt = request_vectors([d["text"] for d in group], settings=settings)
        np.savez_compressed(path, vectors=vectors)
        meta = {**receipt, "document_ids": [d["id"] for d in group],
                "array_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return vectors, meta

    batches = [None] * len(groups)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers or settings.workers) as pool:
        futures = {pool.submit(embed, group): i for i, group in enumerate(groups)}
        for count, future in enumerate(concurrent.futures.as_completed(futures), 1):
            batches[futures[future]] = future.result()
            if count % 10 == 0 or count == len(groups):
                print(json.dumps({"embedding_batches": count, "total": len(groups)}), flush=True)
    matrix = np.concatenate([entry[0] for entry in batches], axis=0)
    path = directory / "vectors.npz"
    np.savez_compressed(path, vectors=matrix)
    manifest = {"version": 1, "model": settings.model, "dimensions": settings.dimensions,
                "normalization": "L2 float32", "dataset_sha256": knowledge.sha256,
                "documents_sha256": digest(docs), "document_ids": [d["id"] for d in docs],
                "wine_documents": sum(d["kind"] == "wine" for d in docs),
                "query_documents": sum(d["kind"] == "query" for d in docs),
                "vectors_file": path.name, "vectors_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "provider_receipts": [entry[1] for entry in batches],
                "total_usage_tokens": sum(entry[1].get("usage", {}).get("total_tokens", 0) for entry in batches)}
    (directory / "index.manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


class EmbeddingIndex:
    def __init__(self, knowledge: Knowledge, directory: str | Path, *, settings: EmbeddingSettings | None = None):
        settings = settings or EmbeddingSettings()
        directory = Path(directory)
        manifest_path = directory / "index.manifest.json"
        raw = manifest_path.read_bytes()
        self.version = hashlib.sha256(raw).hexdigest()
        manifest = json.loads(raw)
        docs = knowledge.embedding_documents()
        if (manifest["model"] != settings.model or manifest["dimensions"] != settings.dimensions
                or manifest["dataset_sha256"] != knowledge.sha256
                or manifest["documents_sha256"] != digest(docs)
                or manifest["document_ids"] != [d["id"] for d in docs]):
            raise ValueError("Index does not match the catalog, queries or configured embedding model")
        path = directory / "vectors.npz"
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["vectors_sha256"]:
            raise ValueError("Embedding matrix hash mismatch")
        with np.load(path, allow_pickle=False) as stored:
            matrix = stored["vectors"].copy()
        if matrix.shape != (len(docs), settings.dimensions) or not np.isfinite(matrix).all():
            raise ValueError("Invalid embedding matrix")
        if not np.allclose(np.linalg.norm(matrix, axis=1), 1, atol=1e-4):
            raise ValueError("Embedding vectors must be normalized")
        self.rows = {doc["id"]: i for i, doc in enumerate(docs)}
        self.matrix = matrix
        self.model = manifest["model"]

    def similarities(self, query_key: str, slugs: list[str]) -> dict[str, float]:
        # Only eligible slugs enter vector search. Exclusions cannot be overridden by similarity.
        q = self.matrix[self.rows["query:" + query_key]]
        positions = [self.rows["wine:" + slug] for slug in slugs]
        scores = self.matrix[positions] @ q
        return {slug: float(score) for slug, score in zip(slugs, scores)}
