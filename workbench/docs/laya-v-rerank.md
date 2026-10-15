# Laya-V cluster reranking

The main Workbench configuration has the preset
`barcode-rerank_laya_v-siglip2-p512-rot5-seg`.
It copies `barcode-rerank-siglip2-p512-rot5-seg` and changes only the rerank VLM.
It uses the same four-worker default.

Use `workbench/config.laya-v.yaml` as a separate runnable configuration.
Its pipeline is `barcode-rerank-siglip2-p512-rot5-seg-laya-v`.
It uses the existing NaFlex p512 rot5 index, barcode scanner, segmented views,
cluster rules, and rerank window. It sends one query at a time.

The inference endpoint is
`http://192.168.86.14:18081/upstream/laya-v/v1/systemone`.
The model UI URL is not an inference endpoint.

## Answer mode

The adapter sends one strict Jev `choice` question for each scoreable label question.
Each question includes the existing options, `other`, and `not visible`.
Neutral option IDs map to the original option text.
The request includes the same label PNG that the Qwen reranker uses.
The image detail is `mid`, the deployed runtime default.

The response MUST include every question and every option probability.
The adapter rejects an invalid type, missing or extra fields, invalid probabilities,
an inconsistent choice, and invalid token usage. A partial response contributes no evidence.
The adapter normalizes the probabilities and uses the largest remainder method to
convert them to integer option scores. Each question total is exactly 100.

Jev `score` represents ordered levels. The label options have no such order.
Jev `noul` represents a binary decision. It does not provide a distribution over label options.
The adapter uses neither mode for this pipeline.

The existing reranker computes visible support and adds at most 0.05 to the embedding
decision score. It preserves the public scores. An absent expected value stays neutral.
An invalid response or transport failure preserves the visual ranking.

Laya-V uses an encoder and typed decision heads. It does not use chat generation.
The `thinking` and `max_tokens` rerank settings do not affect its request.
The configuration uses `protocol: laya-v` and `thinking_field: none`.
The VLM entry supports cluster option-score requests only. Image descriptions and
cluster rule generation still require a chat VLM entry.

## Cache

The cache stores the original Jev response after validation.
The cache key includes the endpoint, served model, image digest, question criteria,
context, image detail, schema, and adapter version.
The existing cache bypass uses a fresh request.

## Runtime evidence

On 2026-10-09, the gateway listed `laya-v` as ready.
The service health returned revision `5c56367ba43ad790a2ba8c1491e1bcc9b4cca56c`,
device `cuda`, and pooler `reconstructed-grid`.
The runtime is an experimental reconstruction. Contract checks do not establish
wine recognition accuracy. Use a separate benchmark before comparing accuracy.

The live adapter check sent one synthetic blue image. The service returned a valid
choice response in 54 ms. It assigned 15 percent to `blue` and 38 percent to
`not visible`. This answer was incorrect. The check confirms the API integration
and score conversion. It does not establish recognition quality.
Saved evidence is in `internal/laya-v-rerank-20261009/summary.json` at the repository root.

Local validation passed 98 tests: 11 adapter tests, 24 VLM configuration and display
tests, 34 label-rule tests, and 29 cluster-rerank tests. Ruff and the diff check passed.

## Official-test result

The preset completed all 95 scored photos of `official-test-2026-10-01`.
Top-1 was 86/95 (90.53 percent). Top-5 and Top-10 were 95/95.
All 20 Laya-V reads were fresh and valid. The reranker changed three Top-1 answers.
Against its visual ranking, it corrected one photo and regressed one photo.
The third change retained an incorrect answer. There were no request or rerank errors.

The run used four workers and the existing retrieval caches.
Median query latency was 2.220 seconds. The 95th percentile was 7.278 seconds.
The full query phase took 67 seconds. These cached query times are not a fresh latency benchmark.

The preceding Qwen run scored 90/95 (94.74 percent) at Top-1 and 95/95 at Top-5.
All 95 query hashes, truths, and visual Top-1 answers match between the runs.
All 20 rerank base-score dictionaries match. The recorded index states differ only
in the build timestamp. The comparison uses a preceding run, not simultaneous inference.
Laya-V corrected one of its errors and regressed five of its correct answers.

The original photo bytes and modification times passed verification.
The four frozen catalogue artifact hashes passed verification.
The run used staged copies with timestamps before the submission cutoff.
The run did not rebuild the shared index.
Evidence is in `internal/laya-v-rerank-20261009/official-test/summary.json`.

## PaddleOCR text evaluated by Laya

The opt-in preset `barcode-rerank_paddle_laya-siglip2-p512-rot5-seg` uses the same
retrieval, barcode lookup, crop preparation, cluster questions, window and 0.05 evidence
weight. Its reader is `paddle-laya`, with `protocol: laya-ocr`.

The pinned local CPU PaddleOCR reader recognizes the exact rerank label PNG.
It uses `PP-OCRv5_mobile_det` and `eslav_PP-OCRv5_mobile_rec` from the existing
`work/main-label-paddle` environment. Normal recognition requires those local weights;
it never downloads or invokes a hosted OCR engine.

The multilingual **text** Laya checkpoint evaluates the raw recognized lines.
Requests go to `/upstream/laya/v1/systemone`, with `model: multilingual`.
Laya receives text, line confidence and bounding boxes relative to the label image.
The request contains no image, query identifier, truth or catalogue card metadata.
No wine-term normalization or fuzzy recovery is applied to the OCR text.
The original question text and answer options are retained. Added instructions forbid
inferring visual colour or design from the transcription. Absent or unreadable evidence
uses `not visible`. The answer mode remains strict Jev `choice`.

The local OCR cache is isolated in `data/cache/laya-ocr-paddle/`. The typed decision
cache is in `data/cache/models/laya-multilingual/` and includes the exact source image
hash, raw OCR state, OCR identity, served model, questions, schema and adapter version.
Only validated complete answers are stored. A reader or evaluator failure preserves
the original visual ranking through the existing cluster reranker.

Cold OCR calls serialize through the local CPU reader; each cache miss launches its
separate Python environment. Cached calls avoid that setup. The official comparison
prepares the twenty OCR inputs in one batch and primes this isolated OCR cache before
the normal run. Report OCR preparation time separately from the cached query latency.
That run remains an accuracy comparison, not a fresh latency benchmark.

### Official OCR-text result

On 2026-10-10, all 95 scored photos completed. Top-1 was 85/95 (89.47 percent);
Top-5 and Top-10 were 95/95. All twenty text Laya evaluations were fresh and valid.
The variant corrected one visual error, introduced two, and changed one incorrect
winner to another incorrect winner. The same Qwen run scored 90/95 and image-based
Laya-V scored 86/95. Retrieval base scores and questions match all twenty prior reads.

PaddleOCR batch preparation took 128.18 seconds, including model initialization;
median per-image inference was 4.305 seconds. The subsequent cached query phase took
38.3 seconds, with median/p95 query times 1.240/3.651 seconds. The recorded rerank
median was 57.5 ms with prepared OCR. These query times exclude cold recognition.

PaddleOCR recognized SAPERAVI and АЛИГОТЕ / ЦИТРОН, but Laya's support was too weak
to correct their retrieval winners under the existing 0.05 weight. It supported
acacia and the author-technology banner despite neither phrase being present in the
transcription, causing two regressions. The correct Krinitsa selection is not reliable
year evidence: OCR read 2020 while Laya favored the offered 2024 option.

All source photo hashes and modification times, truths, and four catalogue artifact
hashes passed verification. All twenty OCR PNGs match the previous Laya-V inputs.
The text checkpoint remained on CUDA at revision
`7b928d828b7b0e022f929d9bd2e44165aa270148`.
Evidence is in `internal/laya-v-rerank-20261009/paddle-laya/summary.json` and `cases.json`.
