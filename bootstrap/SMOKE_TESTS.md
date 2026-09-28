# Smoke Tests

## Static tests

- Run the unit tests.
- Confirm that unsafe tar paths are rejected.
- Confirm that the gateway routes each supported model ID.
- Confirm that an unknown model ID returns HTTP 404.

## QR scanner

- Start `qr-scanner`.
- Send a generated QR image with `POST /upstream/qr-scanner/scan`.
- Confirm that the response contains the generated text.

## SigLIP2 NaFlex

- Install the `google/siglip2-so400m-patch16-naflex` bundle.
- Start `siglip2-so400m-patch16-naflex`.
- Send one image with `max_num_patches` set to 256, 512, and 1024.
- Confirm that each response contains one finite 1,152-value vector.
- Send one text input.
- Confirm that the response contains one finite 1,152-value vector.

## SigLIP2 512

- Install the `google/siglip2-so400m-patch16-512` bundle.
- Start `siglip2-so400m-patch16-512`.
- Send one image to `POST /v1/embeddings`.
- Confirm that the response contains one finite 1,152-value vector.

## ShieldGemma

- Install the `google/shieldgemma-2-4b-it` bundle.
- Start `shieldgemma-2-4b-it`.
- Send one image to `POST /upstream/shieldgemma-2-4b-it/classify`.
- Confirm that the response contains the requested policy results.

## SAM3

- Install the `facebook/sam3` bundle.
- Start `sam3`.
- Send one image and one text prompt to `POST /upstream/sam3/segment`.
- Confirm that the response dimensions equal the input dimensions.
- Confirm that `instances` is a list.
- Confirm that the generated wine-bottle image returns at least one instance.

## Qwen3.5-9B through Ollama

- Confirm that `ollama list` contains `qwen3.5:9b`.
- Send one request to `POST /v1/chat/completions`.
- Confirm that the response has HTTP status 200.
- Confirm that the response contains assistant text.
- Run `ollama ps`.
- Confirm that Qwen uses the intended processor for the selected memory profile.

## Simultaneous core profile

- Start Ollama with `qwen3.5:9b` loaded.
- Start QR scanner, SAM3, and one SigLIP2 model through the launcher.
- Confirm that all four services answer a real request.
- Confirm that no process exits because of insufficient memory.
- Do not start the second SigLIP2 model.
- Add ShieldGemma only for the optional `telegram-bot` profile.

## External endpoint compatibility

- Set `QR_SCANNER_ENDPOINT`, `SAM3_ENDPOINT`, `SIGLIP2_ENDPOINT`, `VLM_ENDPOINT`, and `VLM_MODEL`.
- Run `scripts/check_compatibility.py`.
- Confirm that the QR endpoint decodes the generated text.
- Confirm that the SAM3 endpoint returns at least one wine-bottle instance.
- Confirm that the SigLIP2 endpoint returns one finite 1,152-value NaFlex vector with `max_num_patches=512`.
- Confirm that the Qwen endpoint accepts an image through `POST /chat/completions` and returns the requested JSON object.
- Set `SHIELDGEMMA_ENDPOINT` to include the optional moderation contract.
- Confirm that the command returns a nonzero exit code when a required contract fails.

## Performance benchmark

- Start one isolated model process.
- Send two warm-up requests.
- Send 16 requests with client concurrency 1, 2, 4, and 8.
- Confirm that all 64 measured requests succeed.
- Record throughput, p50 latency, and p95 latency.
- Stop the model process.
- Confirm that the loopback port is closed.
- Run one accelerator model at a time.
