# The backend `cascade`

The backend `cascade` recognizes one wine photo with a code lookup, SAM3, SigLIP2, and a
VLM cluster re-rank. The stages run in parallel where their inputs allow it. A time budget
can limit `POST /v1/eval/predict`. The plan is
[workbench plan 85](../../workbench/docs/plans/85_matcher-cascade-fast-answer.md).

## Scope

- `POST /v1/eval/predict` uses the stages and the time budget `matcher.fast_answer`.
- `POST /v1/match` uses the same stages with no time budget. Each service call has its
  own limit.
- `POST /v1/group/match` does not use the stages. It uses the SigLIP2 group ranking of
  the embedding `group_embedding` (read [group-match.md](group-match.md)).
- The code is in `cascade.py` (the runtime), `cascade_run.py` (the task graph),
  `services.py` (the HTTP clients), `photo.py` (the image steps), `codes.py`, `labels.py`,
  and `rerank.py` (the ports of the lab rules). `service.py` parses the configuration.

## Configuration

```yaml
matcher:
  pipeline: cascade-p512-rot5
  output_dir: "{env:SVOE_VINO_MATCHER_OUTPUT_DIR}"
  fast_answer:
    enabled: true
    answer_at_seconds: 2.9
    timeout_seconds: 9.5

pipeline:
  - name: cascade-p512-rot5
    backend: cascade
    catalog: workbench/data/catalog
    embedding: gx10-siglip2-so400m-patch16-naflex-p512-rot5
    group_embedding: gx10-siglip2-so400m-patch16-naflex-p512
    endpoint: "{env:SIGLIP2_ENDPOINT}"
    whole_image: true
    barcode: {endpoint: "{env:QR_SCANNER_ENDPOINT}", engine: zxing-cpp, crops: true}
    sam3: {endpoint: "{env:SAM3_ENDPOINT}", threshold: 0.35, hand: true, label: true,
           packages_first: false}
    rerank: {clusters: gx10-siglip2-so400m-patch16-naflex-p512,
             endpoint: "{env:VLM_ENDPOINT}", model: qwen3.5-9b-nvfp4, window: 10,
             side: 1536, max_tokens: 256, timeout_seconds: 60}
```

| Key | Default | Meaning |
|---|---|---|
| `matcher.fast_answer.enabled` | `true` | The time budget of `POST /v1/eval/predict`. |
| `matcher.fast_answer.answer_at_seconds` | 2.9 | When an answer exists at this time, the matcher answers. |
| `matcher.fast_answer.timeout_seconds` | 9.5 | The hard limit. With no answer, the matcher answers `{"slug": ""}`. |
| `catalog` | required | A catalogue copy of `workbench/scripts/copy_catalog.py`. |
| `embedding` | required | The index of the single-image search. It gives the model and `extra_body`. |
| `group_embedding` | `embedding` | The index of `POST /v1/group/match`. It MUST hold the view `label`. |
| `endpoint` | required | The SigLIP2 gateway root. The client adds `/v1/embeddings`. |
| `whole_image` | `true` | SigLIP2 of the whole photo at the start. |
| `barcode.endpoint` | required | The QR scanner root (`…/upstream/qr-scanner`). The client adds `/scan`. |
| `barcode.engine` | `zxing-cpp` | `zxing-cpp`, `zxing-cpp-sr`, or `boofcv-qr-cpp`. `auto` is refused: it runs SAM3 and the VLM for 8 to 15 s. |
| `barcode.crops` | `true` | The scans of the package crop and of the label crop. They need `sam3`. |
| `sam3.endpoint` | required | The SAM3 root (`…/upstream/sam3`). The client adds `/segment_multi`. |
| `sam3.threshold` | 0.35 | The instance threshold of the request. |
| `sam3.hand` | `true` | The noun `hand` in the request. |
| `sam3.label` | `true` | The noun `label` in the request: the label cut, its scan, and the VLM picture. |
| `sam3.packages_first` | `false` | A second request with the package nouns alone. |
| `rerank.clusters` | required | The index directory of `clusters.json` and `cluster-rules.json`. |
| `rerank.endpoint` | required | The VLM root with `/v1` (`VLM_ENDPOINT`). The client adds `/chat/completions`. |
| `rerank.model` | `qwen3.5-9b-nvfp4` | The VLM model. |
| `rerank.window` | 10 | The trigger window. |
| `rerank.side` | 1536 | The long side of the VLM picture. |
| `rerank.max_tokens` | 256 | The token limit of the VLM answer. |
| `rerank.timeout_seconds` | 60 | The VLM limit of `POST /v1/match`. |

- The loader refuses an unknown key at each level and names it.
- Omit `barcode`, `sam3`, or `rerank` to turn that stage off.
- `matcher.fast_answer` is valid only with a pipeline of the backend `cascade`.
- The fixed values are the lab values: the package nouns `wine bottle, can, packet, box`;
  the mask threshold 0.5; the scan images at the long side 1600 px, scaled up or down; the
  formats EAN-13, Code 128 as a valid GTIN-13, and QR; the SigLIP2 input at most 1024 px.

## The time budget

- The protection middleware notes the time when uvicorn parsed the request headers
  (`scope["state"]["started_at"]`). The queue wait, the upload, the multipart parse, and
  the archive write count in the budget.
- The time before the headers arrive is outside the server clock: DNS, TCP, TLS, the edge
  proxy, and the tunnel. The response transfer is outside too. The reserve of
  `answer_at_seconds` (0.1 s below the SLA of 3 s) MUST cover them. Measure the gap on the
  real client path before an evaluation.
- At `answer_at_seconds`, the matcher answers when an answer exists. With no answer, it
  answers with the first answer that follows, or at `timeout_seconds` with `""`.
- Then the matcher cancels each pending call. The HTTP client closes the connection, so a
  service sees the disconnect. A SAM3 job that runs on the GPU still ends there.

## The stages

| Stage | Start | Work |
|---|---|---|
| `scan_full` | at the start | The photo at the long side 1600 px → `/scan`. |
| `sam3_full` | at the start | One `/segment_multi` request: the package nouns, `hand`, and `label`. |
| `sam3_packages` | at the start, with `packages_first` | The package nouns alone. |
| `whole` | at the start, with `whole_image` | SigLIP2 of the whole photo → the ranking. |
| `crop:N` | the first SAM3 answer with a package; again when the full answer selects a package with IoU below 0.8 | The crop of the refined mask box from the full-resolution photo → SigLIP2 → the ranking. |
| `scan_package`, `scan_label` | the full SAM3 answer with a package (and a label) | The crop plus 10 % on each side, at the long side 1600 px → `/scan`. |
| `vlm:<cluster>` | the trigger holds, the full SAM3 answer exists, and no code is unique | The label cut on white (else the photo) at the long side 1536 px → `/chat/completions`. |

- The package is the first package of `main_scene.rank_packages` with a usable mask. The
  selection uses the hands when the answer holds hands.
- The crop box is the box of the refined mask of the lab: the mask at the photo size, the
  pixels of at least 128, `refine_mask`. The matcher computes it on the package region
  plus a margin of 3 sigma, so the cost does not grow with the photo.
- The label is the rule of `workbench/pipeline/alternatives.py` on the selected package:
  the label centre MUST lie on the package, a label that is the package does not count,
  the largest label wins, and other body labels give the box of all labels. With no
  package, the largest label wins (a close-up).
- The primary ranking is the crop ranking. With no package, it is the whole ranking.
- The ranking of a wine is the best cosine over all its rows: with a rotated index, the
  maximum over the angles of each reference image.
- The re-rank trigger: the rank-1 wine is in a cluster with a rule of the mode `sheet` or
  `verdict`, and another wine of the cluster is in the first `window` positions. The VLM
  prompts are the lab prompts, verbatim. Every position keeps its score.

## The answer

The answer is the first source with a result:

1. A unique Active wine of a code of the package scan or of the label scan. This answer
   is final.
2. A unique Active wine of a code of the full-photo scan.
3. A shared GTIN: its wines first, in ranking order, each at score 1.0.
4. The re-ranked primary ranking, the primary ranking, the whole ranking.

A shared QR URL never decides. `POST /v1/match` gives the code wines at 1.0, then the
ranking without them, at most `k` wines with a card. The scores never increase.

A failed stage does not fail the request. When all stages end with no answer, the first
error answers (HTTP 502 or 504). A damaged image gets HTTP 422 and no service call.

## The data

- The catalogue copy holds `catalog.sqlite3` and one directory for each embedding.
  `copy_catalog.py --embedding <embedding> --embedding <group_embedding>` copies both
  directories and the rule files of each.
- The codes come from the tables `wine_code` and `wine_catalog` (the Active wines, the
  kinds `gtin` and `qr_url`). This read is an owner exception to the rule "fixed views
  only" (plan 85, decision 10).
- The rule files come from `embeddings/<rerank.clusters>/`. A wine that is newer than the
  rule files is in no cluster, so the re-rank never moves it.

## The audit record

`request.json` gets the key `decision` and the list `stages` in `response`:

- `decision.source`: `code_package`, `code_label`, `code_full`, `gtin`, `rerank`, `crop`,
  `whole`, or `none`.
- `decision.reason`: `final`, `done`, `answer_at`, or `timeout`.
- `decision.answered_ms`: the answer time from the request start.
- `decision.code`, `decision.rerank`, `decision.package`, and `decision.label`, when they
  apply.
- `stages[]`: `id`, `start_ms`, `end_ms`, `status` (`ok`, `error`, `cancelled`), `error`.

The log line `matcher_request` holds `decision.source`, `reason`, and `answered_ms`. The
API answer does not change.

## Limits

- Cold starts are longer than the budget: the VLM about 3.5 min, the NaFlex SigLIP2 about
  48 s. Warm the models before an evaluation.
- The gx10 gateway (checked 2026-09-29): llama-swap pins `qwen3.5-9b-nvfp4` in the
  group `pinned` (no `ttl`, a preload at the llama-swap start) since 16:03 MSK. `sam3`
  has no `ttl`. `siglip2-so400m-patch16-naflex` and `qr-scanner` have a `ttl` of 24 h. The
  container health check calls `/readyz` each 30 s, and `/readyz` sends a request to
  SigLIP2, SAM3, and the scanner. A reload of the llama-swap configuration stops all
  models: the VLM then needs its cold start again.
- The load of the rot5 index peaks at about 2.6 GB of memory. The index uses 760 MB.
- The gx10 SAM3 server answers the requests of one batch together, so `packages_first`
  does not give an earlier crop there.
- This combination of stages was not measured as a whole before plan 85.

## Verification

- `matcher/tests/test_cascade.py`: the task graph, the time budget, the priority, the
  cancellation, and the SAM3 cases, with the fakes of `matcher/tests/cascade_fakes.py`.
- `matcher/tests/test_cascade_api.py`: the configuration and the API through uvicorn,
  including the timer of the request headers.
- `matcher/tests/test_codes.py`, `test_labels.py`, `test_rerank.py`: the ports.
- `workbench/tests/test_matcher_parity.py`: the ports give the results of the lab code.
