# Svoe Vino feature inventory

Date: 2026-09-28

This inventory combines relevant active and archived Codex task histories with the current repository state.
It includes committed code and current uncommitted worktree changes.

## Status terms

- **Deployed**: The task history records a successful deployment and a live check.
- **Implemented**: The current repository contains the feature and its tests or documentation.
- **Research-only**: The workbench contains the feature or experiment, but the current standalone matcher does not use it.
- **Skipped**: The chats discussed the feature, but the current repository does not contain a complete active implementation.
- **Rejected**: An experiment showed a regression or an unacceptable tradeoff.

## Implemented features

### Recognition API and matcher

- **Implemented:** `POST /v1/eval/predict` returns the Top-1 `wine_slug` for the official evaluator contract.
- **Implemented:** `POST /v1/match` returns ranked candidates, scores, the active pipeline name, and complete wine cards.
- **Implemented:** Version 2 embedding bundles contain vectors and wine metadata for 2,094 wines.
- **Implemented:** SigLIP2 image normalization, embedding generation, cosine search, deterministic ranking, bundle hash validation, and request protection.
- **Implemented:** `POST /v1/group/match` processes a complete shelf photograph.
- **Implemented:** Shelf matching uses SAM3 bottle segmentation and one batch SigLIP2 request.
- **Implemented:** Shelf matching returns the normalized preview, bottle coordinates, transparent masks, and the best wine card for each bottle.
- **Implemented:** The matcher supports request archiving for later inspection.
- **Deployed:** The public matcher routes use TLS and HTTP Basic authentication through Caddy.

Evidence: [matcher/README.md](../matcher/README.md), [matcher/ChangeLog.md](../matcher/ChangeLog.md), and [BENCHMARKS.md](../BENCHMARKS.md).

### Public Web UI

- **Deployed:** The public portal is available at `https://chtozavino.ru/`.
- **Implemented:** The responsive Nuxt scanner accepts a camera image, uploaded file, drag-and-drop file, or bundled example.
- **Implemented:** The portal requires an 18+ confirmation and stores only the confirmation flag in local storage.
- **Implemented:** The result shows the matched bottle, title, and direct `vino-svoe.ru` link.
- **Implemented:** The shelf tab sends one request to `/v1/group/match` and draws bottle masks and controls over the shelf preview.
- **Implemented:** A bottle selection opens the ready result without a second recognition request.
- **Implemented:** The portal is an installable PWA with regular, maskable, and Apple icons.
- **Implemented:** The PWA caches the app shell but does not cache photo uploads or recognition API responses.
- **Implemented:** The portal provides canonical metadata, Open Graph metadata, JSON-LD, `robots.txt`, and `sitemap.xml`.
- **Implemented:** The portal provides four post-result demonstration actions: product pairing, label explanation, a fictional story, and an Abrau-Durso product-line map.
- **Implemented:** The portal provides browser tools for supported WebMCP browsers.

Evidence: [webui/README.md](../webui/README.md), [webui/ChangeLog.md](../webui/ChangeLog.md), and [webui/ARCHITECTURE.md](../webui/ARCHITECTURE.md).

### Telegram bot and internal recognition API

- **Deployed:** `@ChtoZaVinoBot` runs on GX10.
- **Implemented:** The bot accepts one photo or a Telegram album and returns one result for each photo.
- **Implemented:** The bot requires an 18+ confirmation before image processing.
- **Implemented:** The bot uses a persistent FIFO queue with restart recovery and queue-position messages.
- **Implemented:** The production user limit is 50 images per hour.
- **Implemented:** ShieldGemma moderation can reject unsafe images before matcher processing.
- **Implemented:** Moderation is optional through configuration. The default is enabled.
- **Implemented:** Local blur and glare checks and SAM3 bottle and label checks produce advisory quality metadata.
- **Implemented:** The bot requests four matcher candidates and can return `Не уверен` from score and margin thresholds.
- **Implemented:** A successful result includes wine parameters, the catalogue link, and a prepared result image.
- **Implemented:** The bot shows positive and negative feedback actions.
- **Implemented:** Negative feedback shows ranks 2 through 4 and `Ничего из этого`.
- **Implemented:** The bot stores feedback, timings, hashes, moderation results, quality results, and candidate cards in SQLite.
- **Implemented:** Wine and candidate responses include valid QR URLs when the wine card contains them.
- **Implemented:** The bot exposes a LAN-only synchronous recognition API at `/api/v1/recognize`.
- **Implemented:** Telegram and HTTP requests use the same queue and processing pipeline.
- **Implemented:** A password-protected LAN administration UI shows users, requests, timings, moderation, quality, candidates, feedback, and safe visual artifacts.
- **Implemented:** Quarantined requests expose only an irreversible server-generated blurred preview.
- **Implemented:** The administration UI can reset rate limits and retry a previously safe request.

Evidence: [telegram-bot/README.md](../telegram-bot/README.md) and [telegram-bot/ChangeLog.md](../telegram-bot/ChangeLog.md).

### Android application

- **Implemented:** The Android 9+ application supports camera capture and gallery selection.
- **Implemented:** The application has an 18+ confirmation.
- **Implemented:** Google Code Scanner reads barcode and QR input.
- **Implemented:** DIS performs foreground segmentation.
- **Implemented:** The application creates a white-background crop and a SigLIP2 Base/16 224 embedding on the device.
- **Implemented:** The application performs local cosine search and stores local history.
- **Implemented:** A verified model-pack contract keeps model weights and catalogue vectors outside Git.
- **Implemented:** The project has unit tests and a verified debug APK build.

Evidence: [android/README.md](../android/README.md) and [android/ChangeLog.md](../android/ChangeLog.md).

### Workbench, catalogue, and evaluation

- **Implemented:** The workbench manages the wine catalogue, images, patches, test sets, annotations, embeddings, pipelines, runs, and reports.
- **Implemented:** The workbench builds and validates production matcher bundles.
- **Implemented:** It supports multiple image views, SAM3 crops, barcode signals, cluster rules, VLM descriptions, reranking experiments, and reproducible run artifacts.
- **Implemented:** A failed-match test set named `my-1` contains 252 positive images that missed Rank 1 in the selected run.
- **Implemented:** SAM3 processed 3,474 unique test-set images and added `barcode` and `qr_code` tags.
- **Implemented:** The completed pass tagged 513 barcode images, 248 QR-code images, and 213 images with both tags.
- **Implemented:** Additional-image upload calls the existing QR/barcode decoder.
- **Implemented:** A valid GTIN populates barcode fields, and a valid HTTP(S) QR URL populates QR URL fields.
- **Implemented:** The upload remains saved when decoding fails, and a retry is available.

Evidence: [workbench/README.md](../workbench/README.md) and [workbench/ChangeLog.md](../workbench/ChangeLog.md).

### Model-service bootstrap and reproducibility

- **Implemented:** The bootstrap provides local QR scanner, SAM3, ShieldGemma 2, and SigLIP2 endpoints.
- **Implemented:** Qwen3.5-9B uses an OpenAI-compatible API. The reference setup uses Ollama on Apple Silicon and NVIDIA hosts.
- **Implemented:** The documentation covers Apple Silicon and NVIDIA deployment, memory requirements, disk requirements, model archives, health checks, and smoke tests.
- **Implemented:** A compatibility command checks the mandatory QR, SAM3, SigLIP2, and Qwen API contracts.
- **Implemented:** The project contains GX10 versus RTX 4090 benchmark results.
- **Implemented:** Docker packaging exists for the matcher, Telegram bot, administration UI, and Matcher Inspector.

Evidence: [bootstrap/README.md](../bootstrap/README.md), [docs/bootstrap/README.md](bootstrap/README.md), and [SETUP.md](../SETUP.md).

### Inspection, deployment, and monitoring

- **Deployed:** Matcher Inspector runs on GX10 on the production and development ports.
- **Implemented:** Matcher Inspector shows request journals, archived images, complete request JSON, and installed embedding bundles.
- **Implemented:** Matcher Inspector has read-only mounts and does not use the Docker socket.
- **Deployed:** The public portal runs on Princess and reaches the private GX10 matcher through the protected edge configuration.
- **Deployed:** Caddy provides TLS, HTTP Basic authentication, structured access logs, and separate evaluator and monitoring accounts.
- **Deployed:** Uptime Kuma checks the complete public matcher route without running inference.
- **Deployed:** Telegram alert delivery uses a restricted tunnel that permits only `api.telegram.org:443`.

Evidence: [matcher-inspector/README.md](../matcher-inspector/README.md) and the deployment runbooks in the workspace `deploy/` directory.

## Implemented only in research or inactive code

### Stronger recognition pipeline

- **Research-only:** `barcode-rerank-siglip2-512-crop` reached 84.67% R@1 and 97.02% R@5 on the internal test set.
- **Research-only:** `barcode-siglip2-p1024-crop` reached 97.99% R@5.
- **Current judging path:** The standalone matcher uses `siglip2-p512-as-is`, which reached 74.15% R@1 and 92.94% R@5.
- **Consequence:** The best research result is not the current standalone matcher result.

### Retail integration

- **Inactive:** A live Globus integration exists in the repository.
- **Current UI:** The rendered post-result product action uses a simulated SuperLenta flow with fictional products.
- **Current UI:** It does not request real location and does not call a retailer API.

### Web result metadata

- **Partial:** The single-bottle Web UI uses a 12-wine local metadata fixture after an upstream slug result.
- **Complete elsewhere:** `/v1/match` and `/v1/group/match` can return complete wine cards from bundle version 2.

## Discussed but skipped, rejected, or incomplete

### Recognition improvements

- **Skipped:** Move the best barcode, SAM3 crop, and cluster rerank pipeline into the standalone matcher and official evaluator path.
- **Skipped:** OCR-based candidate generation and production OCR reranking.
- **Skipped:** A discriminative-region reranker for small differences such as `BRUT` versus `EXTRA BRUT`.
- **Skipped:** Catalogue-label OCR and a closed-vocabulary attribute classifier for sweetness, vintage, and grape.
- **Skipped:** Logo and emblem detection as an independent retrieval signal.
- **Skipped:** Candidate-neighbour graphs and visual-family expansion outside the initial Top-K.
- **Skipped:** VLM-generated label-description embeddings and a second VLM verifier.
- **Skipped:** A calibrated `confident`, `uncertain`, and `not_found` contract in the official evaluator route.
- **Rejected:** The tested 50/50 full-image and label-space fusion reduced R@1 from 84.67% to 82.91% and increased median latency from 186 ms to 1,800 ms.
- **Incomplete:** A verified no-match set and a complete confidence calibration for the hidden-style evaluation.

### Product and discovery features

- **Skipped:** Real "similar Russian wines" recommendations across the complete catalogue.
- **Skipped:** A rules-based sommelier and real post-search alternatives from other wineries.
- **Skipped:** Taste-profile estimates from public wine datasets.
- **Skipped:** International taste twins, taste-based search, a blind-tasting game, and a personal taste passport.
- **Skipped:** Real audio stories. The current UI contains only a future-audio callout.
- **Skipped:** A real production retailer flow in the current result UI.
- **Skipped:** A complete planogram system with target layouts, facings, compliance, and stored shelf history.
- **Skipped:** Public catalogue browsing in the current Web UI. The portal focuses on scanning.

### Catalogue and data workflows

- **Incomplete:** End-to-end new-product creation with one or more new images and automatic incremental index activation.
- **Incomplete:** Complete FRAP-backed catalogue normalization, canonical merge and split, and planogram-safe product identity.
- **Incomplete:** Export of subscribed wine Telegram channels with images and captions. The attempted Telegram Desktop export stopped before the scoped export completed.
- **Skipped:** Synthetic chroma-key bottle photography with replaceable labels and geometric marker reconstruction.
- **Skipped:** Training or adapting a wine-specific OCR or field detector from the downloaded public datasets.

### Deployment and operations

- **Incomplete:** One-command real deployment with all required model weights and the production embedding bundle included in the repository.
- **Incomplete:** Automatic failover from GX10 to a second inference host.
- **Skipped:** A periodic full inference canary with a fixed wine image.
- **Skipped:** An external dead-man monitor for the Uptime Kuma host.
- **Skipped:** An off-site backup for the Uptime Kuma host.
- **Skipped:** Uptime Kuma 2FA at the time of the monitoring review.

## Important scope differences

- The original Telegram-bot request proposed 25 requests per hour. The implemented production limit is 50 requests per hour.
- Shelf matching is implemented in the matcher and Web UI code. A deployment must configure a compatible upstream matcher before the shelf tab becomes active.
- Android recognition is implemented, but the model pack is external to Git.
- The current worktree contains uncommitted changes in Android, bootstrap, Telegram bot, and workbench files. This inventory describes the current workspace, not only the last commit.
