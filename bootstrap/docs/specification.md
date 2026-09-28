# Model Service Bootstrap Specification

Date: 2026-09-28

## Purpose

1. The bootstrap MUST let a hackathon organizer run the required inference tools on Apple Silicon or on an NVIDIA GPU host.
2. The bootstrap MUST include the endpoint source code.
3. The bootstrap MUST include separate Apple Silicon and Selectel instructions.
4. The bootstrap MUST run the model services directly.

## Supported models

5. The bootstrap MUST serve `qr-scanner`.
6. The bootstrap MUST serve `google/shieldgemma-2-4b-it` as `shieldgemma-2-4b-it`.
7. The bootstrap MUST serve `google/siglip2-so400m-patch16-naflex` as `siglip2-so400m-patch16-naflex`.
8. The bootstrap MUST serve `google/siglip2-so400m-patch16-512` as `siglip2-so400m-patch16-512`.
9. The bootstrap MUST serve `facebook/sam3` as `sam3`.
The bootstrap MUST document `qwen3.5:9b` through Ollama.
The bootstrap MUST identify `shieldgemma-2-4b-it` as an optional dependency of `telegram-bot`.

## API contract

10. The gateway MUST bind to `127.0.0.1` by default.
11. The default gateway port MUST be `18090`.
12. The gateway host and port MUST be configurable.
13. The gateway MUST forward `/upstream/<model>/<path>` to the selected model service.
14. The gateway MUST route `POST /v1/embeddings` from the JSON `model` field.
15. The SigLIP2 response MUST use the OpenAI embeddings response shape.
16. The SAM3 service MUST support `/segment` and `/segment_multi`.
17. The ShieldGemma service MUST support `/classify`.
18. The QR scanner service MUST support `/scan`.
19. Every model service MUST support `/health`.
Ollama MUST provide Qwen3.5-9B through `/v1/chat/completions`.

## Runtime model

20. Each model MUST run in a separate process.
21. The launcher MUST stop all child processes when it exits.
22. The launcher MUST wait for each selected model to become healthy.
23. The launcher MUST fail if a child process exits during model load.
24. The launcher MUST use MPS on Apple Silicon when MPS is available.
25. The launcher MUST use CUDA on an NVIDIA host when CUDA is available.
26. The launcher MUST permit an explicit CPU selection.
27. The core services MUST be available at the same time on a host that meets the memory requirements.
28. The core services MUST use one SigLIP2 model at a time.
29. The instructions MUST give separate memory requirements for the core profile and the optional ShieldGemma profile.

## Offline model delivery

30. Each Hugging Face snapshot MUST have a separate tarball.
31. A tarball MUST contain regular files instead of Hugging Face cache symlinks.
32. A manifest MUST record the model ID, archive name, archive size, and SHA-256 value.
33. The installer MUST verify the SHA-256 value before extraction.
34. The installer MUST reject an unsafe archive path.
35. The runtime MUST use local model paths.
36. The runtime MUST enable Hugging Face offline mode.
37. The runtime MUST NOT require a Hugging Face token after installation.
38. The repository MUST NOT track model tarballs or extracted model files.
Ollama MUST run `qwen3.5:9b` from local storage after the initial download.

## License handling

39. The instructions MUST identify gated model bundles as private artifacts.
40. The instructions MUST tell the operator to verify recipient license acceptance before transfer.
41. The bootstrap MUST preserve license and model-card files that exist in each snapshot.

## Verification

42. The test suite MUST test safe model bundle extraction.
43. The test suite MUST test gateway model routing.
44. The smoke test MUST send one real QR image.
45. The smoke test MUST send one real inference request to each accelerator model.
46. A SigLIP2 NaFlex smoke test MUST verify a 1,152-value finite vector at patch budgets 256, 512, and 1024.
47. A ShieldGemma smoke test MUST verify the policy result structure.
48. A SAM3 smoke test MUST verify the response dimensions and a nonempty instance list.
49. ShieldGemma MUST use float32 on MPS.
50. ShieldGemma MUST use bfloat16 on CUDA.
51. ShieldGemma MUST reject a non-finite policy score before JSON serialization.
52. The gateway health endpoint MUST probe every active model service.
53. The gateway health endpoint MUST return HTTP 503 when an active model service is not ready.
54. The launcher MUST stop the gateway when a ready child process exits.
