# Decision 002: Qwen3.5-9B through Ollama

Date: 2026-09-28

## Context

The core service needs Qwen3.5-9B, SAM3, QR scanning, and one SigLIP2 model at the same time.
The optional `telegram-bot` profile also needs ShieldGemma.
The deployment must support Apple Silicon and NVIDIA GPU hosts.

## Options

### Ollama on both platforms

This option uses the same model ID and API on both platforms.
Ollama provides `qwen3.5:9b` as a public 6.6 GB package.
Ollama supports Metal and NVIDIA GPUs.

### Ollama on Apple Silicon and vLLM on NVIDIA

This option uses two deployment procedures.
The full Qwen model weights use approximately 19.3 GB before runtime buffers.
This option leaves less GPU memory for the other models.

### Ollama on Apple Silicon and a direct GGUF server on NVIDIA

This option requires separate GGUF file management.
This option also requires a separate service configuration.

## Decision

Use Ollama on Apple Silicon and NVIDIA GPU hosts.
Use the model ID `qwen3.5:9b`.
Use the OpenAI-compatible endpoint `/v1/chat/completions`.
Keep Ollama on the loopback interface.
Use an 8192-token context and one parallel Qwen request for the minimum memory profile.

Treat ShieldGemma as an optional dependency of `telegram-bot`.
Do not include ShieldGemma in the core service memory requirement.

## Consequences

The Mac and NVIDIA instructions use the same Qwen model and API.
The core NVIDIA profile needs at least 24 GiB VRAM.
The optional ShieldGemma profile needs at least 48 GiB VRAM when every model uses the GPU.
A 24 GiB NVIDIA GPU can use CPU inference for Qwen when ShieldGemma is required.
That profile needs at least 64 GiB RAM.

The memory requirements are planning values.
A simultaneous load test is still required before the hackathon handoff.

## Sources

- [Ollama Qwen3.5 model](https://registry.ollama.com/library/qwen3.5)
- [Ollama OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility)
- [Ollama hardware support](https://docs.ollama.com/gpu)
- [Qwen3.5-9B model card](https://huggingface.co/Qwen/Qwen3.5-9B)
