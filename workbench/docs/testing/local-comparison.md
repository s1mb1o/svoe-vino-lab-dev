# Local comparison pipelines

The `lab-compare-*` presets run through the normal lab job API and write standard Runs
results with ten candidates, metrics and matching details. They read the current test
set. They never use historical truth labels, rankings or predictions as inference.

All query embeddings and new visual/OCR measurements run on this Mac. No remote model
service is changed or called by these presets. Bottle retrieval uses local float32
SigLIP2 NaFlex p512 queries against the fixed saved p512/rot5 catalogue. Its saved
reference vectors originally came from the configured service, so this baseline is
not a reproduction of that service's old run. Main-label retrieval uses reference
vectors recomputed with the same local model and processor as its queries.

## Presets

| Configuration suffix | Decision |
| --- | --- |
| `bottle` | Bottle cosine ranking |
| `tesseract`, `paddleocr` | Verify sugar, grapes, colour and product line on the bottle shortlist |
| `lightglue-score`, `superglue-score`, `loftr-score` | Highest foreground homography inlier count |
| `dinov2-score`, `dinov3-score` | Highest main-label CLS cosine |
| `dinov2-patch-score`, `dinov3-patch-score` | Highest symmetric foreground patch similarity |
| `lpips-score`, `dists-score` | Lowest main-label perceptual distance |
| `lpips-aligned-distance`, `dists-aligned-distance` | Lowest distance after valid LightGlue alignment |
| `siglip-main` | Global main-label catalogue retrieval |
| `siglip-main-frozen` | Local label cosine on the live bottle shortlist |
| `siglip-label-gate` | Label quality, cosine ≥0.90 and margin ≥0.01, otherwise bottle ranking |
| `siglip-main-tesseract`, `siglip-main-paddleocr` | Global main-label retrieval followed by variant text |
| `siglip-gated-tesseract`, `siglip-gated-paddleocr` | Text verification only after the label gate selects labels |

The pairwise approaches compare up to two front-label references per shortlisted wine.
An unaligned perceptual comparison has no distance; it cannot win with an invented
zero. Missing references or model failures preserve the bottle order and record a
reason. No average mixes bottle cosines with local pair metrics. Pairwise candidates
retain their bottle cosine in `score`; the metric, direction, original bottle rank
and selected reference are recorded separately in `comparison`. The final rank is
authoritative. Matching details show native metric values and reference image cards.

## Local assets and caches

The existing isolated environments in `work/main-label-pairwise` and
`work/main-label-paddle` supply pinned packages and local weights. The live worker's
model manifest, cache identity and cache provenance live in `work/local-comparison`.
Weights are loaded with offline Hugging Face settings and `local_files_only=True`.
PaddleOCR uses its pinned local CPU environment. A model worker starts lazily and is
closed when the run process ends. Run this suite with one query worker per pipeline
and one pipeline at a time to bound GPU memory.

Verified benchmark pair scores, features and OCR words can seed the live cache. Their
keys contain image hashes and the pinned model/preparation contract. Feature imports
are read only; new images and measurements are written to the live cache. No old run
row or wine identity is imported as a decision. The fresh worker parity checks cover
all seven visual engines. The local SigLIP2 checkpoint revision is
`cc24074f717b612951c2dead130904ab9b65a81e`.

Bottle results are cached under the current catalogue items, owners, vectors file,
model identity and preprocessing steps. Main-label preparation is cached under source
bytes, package box, gate thresholds and preparation code. Disabling the lab's
`Use caches` option recomputes retrieval, pair scores and OCR words. Saved catalogue
vectors, segmentation snapshots and keypoint feature assets remain fixed inputs.
Timings are not complete cold inference benchmarks.

SAM3 masks are read from the existing local cache, checking both historical PNG
compression keys, even when recognition caches are disabled. A photo without a cached package mask uses the existing white-border
crop with an explicit context-fallback trace. A photo without a cached main-label mask
keeps the bottle ranking. These presets send no new SAM3 request.

The suite deliberately skips the global automatic index rebuild: its fixed source
catalogue is recorded in each run. Other pipelines retain their normal rebuild behavior.
Catalogue source changes make the supplementary label index fail its stale-source
check instead of silently using mismatched references.

## Run and inspect

Select `my` on Testset, open `Run>`, and select a `lab-compare-*` preset. Saved runs appear
at `/runs`, and `/runs/charts?set=my` compares their metrics. The same job can be started
with `POST /api/run-jobs` and a body such as:

```json
{"configuration":"lab-compare-lightglue-score","set":"my","workers":1,"use_cache":true}
```

The evidence for the current suite, its input snapshot, worker checks and job links is
in `internal/victor-dravigny-rank6-20261007/lab-pipelines/` at the repository root.
The suite checks exact image hashes, labels and truths in every completed run.

Read-only checks are in `COMMANDS.md`. They use synthetic inputs and temporary
loopback HTTP fixtures, and do not call a configured model endpoint.
