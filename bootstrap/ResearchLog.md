# Research Log

## 2026-09-28

The owner requires QR scanning, SAM3, Qwen3.5-9B, and one SigLIP2 model to stay available at the same time.
ShieldGemma is not part of the core profile.
Only `telegram-bot` needs ShieldGemma for image moderation of erotic and violent content.

The official Ollama registry provides `qwen3.5:9b` as a 6.6 GB multimodal model.
Ollama provides the same OpenAI-compatible API on macOS and Linux.
Ollama supports Metal and NVIDIA GPU execution.
The deployment therefore uses Ollama on both platforms.

The calculated minimum for the core Apple Silicon profile is 48 GiB of unified memory.
The calculated minimum for the core NVIDIA profile is 32 GiB RAM and 24 GiB VRAM.
The calculated minimum with ShieldGemma is 64 GiB of unified memory on Apple Silicon.
The calculated all-GPU NVIDIA minimum with ShieldGemma is 64 GiB RAM and 48 GiB VRAM.
A 24 GiB NVIDIA GPU can reserve VRAM for PyTorch and run Qwen on the CPU when ShieldGemma is required.
That profile needs at least 64 GiB RAM.

These values assume an 8192-token Qwen context and one parallel Qwen request.
The complete simultaneous profile has not passed a load test.

The GX10 deployment uses independent FastAPI processes.
SAM3 uses `facebook/sam3` and `transformers`.
ShieldGemma uses `google/shieldgemma-2-4b-it` and `transformers`.
Both SigLIP2 services use the same OpenAI-compatible embedding server.
The QR scanner is a CPU service.

The first shared-cache SAM3 snapshot was incomplete.
It contained only configuration files and an interrupted 934 MiB blob.
The running GX10 service used the complete snapshot in the user cache.
The bundle builder now rejects a snapshot that has no model weight file.

The final four model tarballs use approximately 21.2 GiB in total.
SAM3 uses 3,445,022,720 bytes.
ShieldGemma uses 8,639,662,080 bytes.
SigLIP2 NaFlex uses 4,581,457,920 bytes.
SigLIP2 512 uses 4,585,011,200 bytes.

The supplied Selectel host is `root@178.130.51.88`.
The host reports Ubuntu 24.04.3 and Python 3.12.3.
The host reports one NVIDIA GeForce RTX 4090 with 24,564 MiB of VRAM.
The host reports approximately 189 GiB of free root storage.

The local Apple Silicon host runs macOS 26.5 on `arm64`.
The host has an Apple M2 Max and 32 GiB of unified memory.
The workspace volume has approximately 643 GiB free.
The system data volume has little free storage.
The bootstrap must keep its virtual environment, package cache, archives, and extracted models on the workspace volume.

The Apple Silicon QR scanner decoded the generated smoke-test text through the public gateway.
The Apple Silicon SAM3 service loaded the offline snapshot on MPS with `float16` weights.
The SAM3 smoke request found one `wine bottle` instance in the generated test image.
The response dimensions were 320 by 480 pixels.
The first SAM3 inference took approximately 61 seconds.
The external-volume Python and PyTorch import phase took several minutes on the first start.

The Apple ShieldGemma float16 forward produced non-finite policy probabilities.
ShieldGemma now uses float32 on MPS.
The float32 smoke request returned finite scores for all three policies.
The first float32 three-policy request took approximately 4.1 minutes.

The Apple SigLIP2 NaFlex image request returned 1,152 finite values.
Its vector norm was 0.99999994.
The image request took approximately 2.8 seconds.
The NaFlex text request returned 1,152 finite values with norm 1.00000001.
The Apple SigLIP2 fixed-512 image request returned 1,152 finite values.
Its vector norm was 1.00000000.
The fixed-512 image request took approximately 2.3 seconds.

The Selectel Python environment uses PyTorch 2.11.0 with CUDA 13.0.
PyTorch detected the RTX 4090.
The eleven static tests passed on Selectel.
The Selectel QR scanner decoded the generated smoke-test text through the loopback gateway.

The Selectel SAM3 request returned one instance and the correct 320 by 480 dimensions.
The smoke command took approximately 2.4 seconds, including SSH overhead.
ShieldGemma float16 also produced non-finite probabilities on CUDA.
ShieldGemma now uses bfloat16 on CUDA.
The bfloat16 three-policy smoke request returned finite scores and took approximately 1.4 seconds.
The Selectel SigLIP2 NaFlex image request returned 1,152 finite values with norm 0.99999997.
The NaFlex text request returned 1,152 finite values with norm 0.99999998.
The Selectel SigLIP2 fixed-512 image request returned 1,152 finite values with norm 0.99999998.
Each Selectel SigLIP2 smoke command took less than one second, excluding model load.

The Selectel installer initially rejected the no-`--model` path before archive verification.
The selection condition was corrected.
Regression tests now cover full-manifest installation and unknown model selection.

The GX10 and Selectel benchmark used identical service source files.
It used two warm-up requests per model.
It used 16 measured requests at concurrency 1, 2, 4, and 8.
All 640 measured inference requests succeeded.

The Selectel RTX 4090 gave 2.88 times the GX10 SAM3 throughput for serial requests.
It gave 2.14 times the GX10 SAM3 throughput at concurrency 8.
The Selectel RTX 4090 gave 1.92 times the GX10 ShieldGemma throughput for serial requests.
It gave 2.06 times the GX10 ShieldGemma throughput at concurrency 8.
The Selectel RTX 4090 gave 1.49 times the GX10 fixed-512 SigLIP2 throughput for serial requests.
It gave 1.43 times the GX10 fixed-512 SigLIP2 throughput at concurrency 8.
SigLIP2 NaFlex single-request throughput differed by less than 5%.
The Selectel RTX 4090 gave 1.36 times the GX10 NaFlex throughput at concurrency 8.
GX10 gave 1.34 times the Selectel QR throughput for serial requests.
GX10 gave 1.64 times the Selectel QR throughput at concurrency 8.

ShieldGemma throughput stayed constant as client concurrency increased.
Its global model lock serialized the requests.
SAM3 batching increased GX10 throughput from 2.75 to 4.13 requests per second.
SAM3 batching increased RTX 4090 throughput from 7.91 to 8.84 requests per second.

The benchmark details are in `docs/benchmarks/2026-09-28-gx10-vs-rtx4090.md`.

The owner supplied the Google Drive distribution folder `1k_suN_6i6jaaS_ti1Lsm5xUypy5vh4HQ`.
The Drive connector confirmed `manifest.json` in the folder on 2026-09-28.
The Drive file matched the local `manifest.json` byte for byte.
The owner reported that the four model archives were still uploading.
The organizer runbooks require all five files to be visible before download.

The updated Apple NaFlex smoke test used patch budgets 256, 512, and 1024.
Each request returned 1,152 finite values.
The vector norms were 0.99999994, 1.00000003, and 1.00000002.
The updated Apple SAM3 smoke test found one instance in the generated wine-bottle image.
The gateway readiness endpoint returned HTTP 200 while SAM3 was ready.
The launcher stopped the gateway after the ready SAM3 child process received SIGTERM.
All 19 static tests passed after these changes.
