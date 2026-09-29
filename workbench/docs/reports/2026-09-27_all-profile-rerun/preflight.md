# Profile queue preflight

Snapshot: 2026-09-27T02:38:24.877352+03:00.
Scope: the 53 authorized internal or local profiles in [queue.json](queue.json).
This report proposes an order. It does not change the queue.
No model was loaded. No photo was sent. No database or configuration was changed.

## Snapshot and evidence

The current configuration SHA-256 equals the queue configuration SHA-256:
`14642fdc568cc2d309ab52d95b3f428dae09d16bf68fb8250f1f358789916d77`.
The queue records 2228 test queries. Revalidate the query selection before launch.
The read-only catalogue snapshot contains 2101 Active wines, 2096 wines with usable
source references, and 2099 unique source images. No referenced source file is missing.

The inspection used `embeddings.read_inputs()` in one read-only SQLite transaction.
It used `plan_items()`, `item_status()`, and prepared-image directory names for coverage.
It read index JSON and vector-array headers through a read-only memory map.
It did not validate every vector value or decode any image.
The counts describe this snapshot. They are not launch-time locks.

Primary local sources:

- [Lab configuration](../../../config.yaml).
- [Coverage rules](../../../pipeline/embeddings.py).
- [Runtime catalogue selection](../../../pipeline/embedding_run.py).
- [GX10 model inventory](/Users/ashmelev/Admin/gx10/MODELS.md).
- [Image embedding API and loading rules](/Users/ashmelev/Admin/gx10/docs/inference/image-embeddings.md).
- [llama-swap memory and group rules](/Users/ashmelev/Admin/gx10/docs/inference/llama-swap.md).
- [GPU memory rule](/Users/ashmelev/Admin/GPU_SERVERS.md).
- [Shared GPU task tracker](/Users/ashmelev/Admin/GPU_TASKS.md).

## Actual endpoints and shared dependencies

`E` means `POST http://192.168.86.14:18081/v1/embeddings`.
All 49 authorized remote embedding profiles use E. The backend name `openai` means
an OpenAI-compatible internal API. It does not mean an OpenAI-hosted service.
`L` means the local `LocalBackend` in `pipeline/build_embeddings.py`.
Its device is MPS when available, otherwise CPU. It loads the Hugging Face model in
float32. The four local profiles still need remote SAM3 for their crop variants.

`S` means `POST http://192.168.86.14:18081/upstream/sam3/segment_multi`.
The configured base URL and `SAM3_ENDPOINT` both equal
`http://192.168.86.14:18081/upstream/sam3` in this process.
The current production client captures the configured default at import time.
An environment assignment alone does not change that captured default.
Refuse a configuration/environment mismatch before a future launch.

`R` means `POST http://192.168.86.14:18081/v1/chat/completions` with model
`qwen3.5-9b-nvfp4`. Only the three rerank profiles use R.
They request a label crop from S when the rerank condition occurs.
Their options are `thinking: false`, `side: 1536`, `max_tokens: 256`,
`timeout_s: 180`, and `window: 5`.

The rerank profiles read `clusters.json` and `cluster-rules.json` from
`gx10-siglip2-so400m-patch16-naflex-p256`.
The embedding model for these profiles is still fixed-resolution SigLIP2-512.
Reading these rules does not load the NaFlex embedding model.
The cluster artifact was built at `2026-09-26T10:33:43+0300`.
The rule artifact was updated at `2026-09-26T17:04:27+0300` and contains 382 card records.
Do not rebuild the rules as part of this queue. The configured rule-generation model
is external QwenCloud. That generation path is separate from internal recognition.

ZXing runs on the Mac. A barcode hit can bypass embedding, segmentation, and rerank.
A `use_barcode: true` run option retains the configured barcode stage. It does not add
that stage to a profile that has no `barcode` key.

## Proposed model-group order

Start after the barcode, crop, bulk, and sequential demo comparisons finish.
Prefer G1 first because the preceding comparisons use this model.
Recheck actual residency before using that optimization.
Run one profile at a time. Keep all profiles in one group together.
Keep the index variants in G2 together because they use one actual model.
Build I3 once in G2 before its four dependent profiles.
If I3 remains unavailable, record those four outcomes and continue independent groups.

The memory figures below are approximate resident costs from the GX10 model inventory.
They are not a measured peak for four concurrent queries or a 16-image index batch.
Do not add a resident model cost a second time when it is already included in live RAM use.

| Order | Group | Actual model | Destination | Approximate resident memory | Profiles |
|---|---|---|---|---:|---:|
| 1 | G1 | `siglip2-so400m-patch16-512` | E | 7 GB on GX10 | 7 |
| 2 | G2 | `siglip2-so400m-patch16-naflex` | E | 7 GB on GX10 | 14 |
| 3 | G3 | `dinov3-vitb16-pretrain-lvd1689m` | E | 2 GB on GX10 | 4 |
| 4 | G4 | `dinov3-vitl16-pretrain-lvd1689m` | E | 3 GB on GX10 | 4 |
| 5 | G5 | `naflexvit_so400m_patch16_siglip.v2_webli` | E | 3 GB on GX10 | 4 |
| 6 | G6 | `PE-Core-L14-336` | E | 3.5 GB on GX10 | 4 |
| 7 | G7 | `siglip2-so400m-patch16-256` | E | 7 GB on GX10 | 4 |
| 8 | G8 | `siglip2-so400m-patch16-384` | E | 7 GB on GX10 | 4 |
| 9 | G9 | `siglip2-so400m-patch14-384` | E | 7 GB on GX10 | 4 |
| 10 | G10 | `google/siglip2-so400m-patch16-naflex` | L | Not established on this Mac | 4 |

The shared SAM3 service has an approximate 7 GB resident cost.
The Qwen3.5-9B-NVFP4 service has an approximate 27 GB reserved footprint.
The pinned `qwen3.5-9b` service has an approximate 7 GB cost even though this queue
does not call it. These figures are documented in the same GX10 model inventory.
The local float32 model has no measured resident-memory figure in the inspected
infrastructure documents. Check Mac memory before G10. Do not apply the remote
service estimate as a measured local peak.

All nine remote image models belong to `image-embeddings` with `swap: false`.
They can remain resident together. Their documented total is approximately 47 GB.
Grouping models therefore reduces reloads but does not enforce a one-model memory limit.
Image models have a documented idle TTL of 1800 seconds. SAM3 has no idle unload.
Do not change TTL values or the swap configuration for this queue.

Before a previously unloaded model is called, inspect live RAM, GPU state, processes,
and gateway `/running`. Apply the estimated additional task memory plus the required
20 GB safety margin. Allow for the current inference batch and other resident services.
If the check fails, wait for capacity or natural idle expiry. Do not stop unrelated work.
A saved preflight from 02:28 is not sufficient for a later model transition.
The task tracker records concurrent Drink Atlas enrichment on SAM3 and Qwen3.5-9B-NVFP4.
That work can change memory use, queue pressure, and latency.
Do not probe an unloaded model through `/upstream/.../health` or `/docs` as a read-only
availability check. Those routes can load the model. `/running` and `/v1/models` do not
require inference. No endpoint probe was made for this report.

## Index coverage

The existing 11 indexes each contain 4058 stored vector rows.
The current catalogue selects 4054 of those rows.
Each existing index has 127 missing items and two failed items.
There are zero stale items under the current hash comparison.
Each index plan has 4183 items and two not-applicable label items outside that plan.
A current item requires a matching embedding hash and an existing prepared image.
It does not prove that the underlying package derivative uses the latest SAM3 rule.

`Full/label wines` counts unique Active wines with at least one current vector in each
view. It can exceed the corresponding unique image count because wines can share images.
The denominator of Active wines is 2101. Five Active wines have no usable source reference.
No `build.lock` file was present for any of the 12 entries at the snapshot time.

| Index | Entry | Group | Current full / label | Missing full / label | Failed | Stale | Full / label wines | Stored vector shape |
|---|---|---|---:|---:|---:|---:|---:|---|
| I1 | `gx10-siglip2-so400m-patch16-naflex-p256` | G2 | 2029 / 2025 | 57 / 70 | 2 | 0 | 2051 / 2047 | 4058 × 1152 |
| I2 | `gx10-siglip2-so400m-patch16-naflex-p512` | G2 | 2029 / 2025 | 57 / 70 | 2 | 0 | 2051 / 2047 | 4058 × 1152 |
| I3 | `gx10-siglip2-so400m-patch16-naflex-p1024` | G2 | 0 / 0 | 2086 / 2097 | 0 | 0 | 0 / 0 | none |
| I4 | `gx10-siglip2-so400m-patch14-384` | G9 | 2029 / 2025 | 57 / 70 | 2 | 0 | 2051 / 2047 | 4058 × 1152 |
| I5 | `gx10-siglip2-so400m-patch16-256` | G7 | 2029 / 2025 | 57 / 70 | 2 | 0 | 2051 / 2047 | 4058 × 1152 |
| I6 | `gx10-siglip2-so400m-patch16-384` | G8 | 2029 / 2025 | 57 / 70 | 2 | 0 | 2051 / 2047 | 4058 × 1152 |
| I7 | `gx10-siglip2-so400m-patch16-512` | G1 | 2029 / 2025 | 57 / 70 | 2 | 0 | 2051 / 2047 | 4058 × 1152 |
| I8 | `gx10-naflexvit-so400m-patch16-siglip2-p256` | G5 | 2029 / 2025 | 57 / 70 | 2 | 0 | 2051 / 2047 | 4058 × 1152 |
| I9 | `gx10-pe-core-l14-336` | G6 | 2029 / 2025 | 57 / 70 | 2 | 0 | 2051 / 2047 | 4058 × 1024 |
| I10 | `gx10-dinov3-vitb16` | G3 | 2029 / 2025 | 57 / 70 | 2 | 0 | 2051 / 2047 | 4058 × 768 |
| I11 | `gx10-dinov3-vitl16` | G4 | 2029 / 2025 | 57 / 70 | 2 | 0 | 2051 / 2047 | 4058 × 1024 |
| I12 | `local-siglip2-so400m-patch16-naflex-p256` | G10 | 2029 / 2025 | 57 / 70 | 2 | 0 | 2051 / 2047 | 4058 × 1152 |

I1, I2, and I3 send `max_num_patches` 256, 512, and 1024 respectively.
They share one service model but use different input patch budgets and separate indexes.
I8 and I12 use a 256-patch budget. Do not substitute one index for another.
Every configured index build uses batch size 16.

The active source set has 59 missing label derivatives, zero missing package derivatives,
and two labels marked not applicable. The approved I3 preparation plan covers only
missing label derivatives in that active source set. An unfiltered label seed is broader.
The new index can have more catalogue coverage than the existing indexes after its build.
Report this coverage difference in the model comparison. The current queue plan schedules
only I3 for a build. It does not authorize an unrecorded refresh of all existing indexes.

## Complete profile mapping

The order below follows the proposed model groups. It is not a mutation of `queue.json`.
`None` in the S column means no configured query segmentation or rerank label request.
`Package` and `label` calls use S. Rerank label calls are conditional.
All remote groups use four query workers. The local group uses one query worker.
All runs retain `use_cache: true` and the profile's configured barcode behavior.

| Group | Profile | Index | S use | R use | Barcode | Workers |
|---|---|---|---|---|---|---:|
| G1 | `siglip2-512-as-is` | I7 | None | None | no | 4 |
| G1 | `siglip2-512-crop` | I7 | package | None | no | 4 |
| G1 | `barcode-siglip2-512-as-is` | I7 | None | None | yes | 4 |
| G1 | `barcode-siglip2-512-crop` | I7 | package | None | yes | 4 |
| G1 | `rerank-siglip2-512-crop` | I7 | package; label on rerank | R | no | 4 |
| G1 | `barcode-rerank-siglip2-512-crop` | I7 | package; label on rerank | R | yes | 4 |
| G1 | `barcode-rerank-siglip2-512-crop-label` | I7 | label, package | R | yes | 4 |
| G2 | `siglip2-p256-as-is` | I1 | None | None | no | 4 |
| G2 | `siglip2-p256-crop` | I1 | package | None | no | 4 |
| G2 | `siglip2-p256-crop-seg` | I1 | package | None | no | 4 |
| G2 | `siglip2-p512-as-is` | I2 | None | None | no | 4 |
| G2 | `siglip2-p512-crop` | I2 | package | None | no | 4 |
| G2 | `siglip2-p1024-as-is` | I3 | None | None | no | 4 |
| G2 | `siglip2-p1024-crop` | I3 | package | None | no | 4 |
| G2 | `barcode-siglip2-p256-as-is` | I1 | None | None | yes | 4 |
| G2 | `barcode-siglip2-p256-crop` | I1 | package | None | yes | 4 |
| G2 | `barcode-siglip2-p256-crop-seg` | I1 | package | None | yes | 4 |
| G2 | `barcode-siglip2-p512-as-is` | I2 | None | None | yes | 4 |
| G2 | `barcode-siglip2-p512-crop` | I2 | package | None | yes | 4 |
| G2 | `barcode-siglip2-p1024-as-is` | I3 | None | None | yes | 4 |
| G2 | `barcode-siglip2-p1024-crop` | I3 | package | None | yes | 4 |
| G3 | `dinov3-vitb16-as-is` | I10 | None | None | no | 4 |
| G3 | `dinov3-vitb16-crop` | I10 | package | None | no | 4 |
| G3 | `barcode-dinov3-vitb16-as-is` | I10 | None | None | yes | 4 |
| G3 | `barcode-dinov3-vitb16-crop` | I10 | package | None | yes | 4 |
| G4 | `dinov3-vitl16-as-is` | I11 | None | None | no | 4 |
| G4 | `dinov3-vitl16-crop` | I11 | package | None | no | 4 |
| G4 | `barcode-dinov3-vitl16-as-is` | I11 | None | None | yes | 4 |
| G4 | `barcode-dinov3-vitl16-crop` | I11 | package | None | yes | 4 |
| G5 | `naflexvit-p256-as-is` | I8 | None | None | no | 4 |
| G5 | `naflexvit-p256-crop` | I8 | package | None | no | 4 |
| G5 | `barcode-naflexvit-p256-as-is` | I8 | None | None | yes | 4 |
| G5 | `barcode-naflexvit-p256-crop` | I8 | package | None | yes | 4 |
| G6 | `pe-core-l14-336-as-is` | I9 | None | None | no | 4 |
| G6 | `pe-core-l14-336-crop` | I9 | package | None | no | 4 |
| G6 | `barcode-pe-core-l14-336-as-is` | I9 | None | None | yes | 4 |
| G6 | `barcode-pe-core-l14-336-crop` | I9 | package | None | yes | 4 |
| G7 | `siglip2-256-as-is` | I5 | None | None | no | 4 |
| G7 | `siglip2-256-crop` | I5 | package | None | no | 4 |
| G7 | `barcode-siglip2-256-as-is` | I5 | None | None | yes | 4 |
| G7 | `barcode-siglip2-256-crop` | I5 | package | None | yes | 4 |
| G8 | `siglip2-384-as-is` | I6 | None | None | no | 4 |
| G8 | `siglip2-384-crop` | I6 | package | None | no | 4 |
| G8 | `barcode-siglip2-384-as-is` | I6 | None | None | yes | 4 |
| G8 | `barcode-siglip2-384-crop` | I6 | package | None | yes | 4 |
| G9 | `siglip2-p14-384-as-is` | I4 | None | None | no | 4 |
| G9 | `siglip2-p14-384-crop` | I4 | package | None | no | 4 |
| G9 | `barcode-siglip2-p14-384-as-is` | I4 | None | None | yes | 4 |
| G9 | `barcode-siglip2-p14-384-crop` | I4 | package | None | yes | 4 |
| G10 | `local-siglip2-p256-as-is` | I12 | None | None | no | 1 |
| G10 | `local-siglip2-p256-crop` | I12 | package | None | no | 1 |
| G10 | `barcode-local-siglip2-p256-as-is` | I12 | None | None | yes | 1 |
| G10 | `barcode-local-siglip2-p256-crop` | I12 | package | None | yes | 1 |

## Conflicts and launch gates

1. Keep `vino-svoe-search-by-photo` outside the authorized queue. Its destination is
   `https://api.vino-svoe.ru/v1/wines/search-by-photo`. The saved queue marks it
   `authorized_to_start: false` and `awaiting_user_approval`. The other 53 destinations
   are the internal GX10 routes or the local model. Do not infer external approval.
2. Read [ACTIVE_WORK.md](../../../ACTIVE_WORK.md) again before a build or derivative
   write. The session `drink-atlas-workspace-86 [92610a]` changed package selection to
   rule D and left catalogue re-cut and embedding rebuild pending owner choice.
   This snapshot has 156 active package `seg` derivatives whose settings are outside
   current `derive.PRESENT_SETTINGS`. One active label `seg` derivative also has other
   settings. These are provenance flags, not permission to overwrite manual work.
   `read_inputs()` carries derivative hashes but does not compare these rule strings.
   Zero stale index items therefore does not resolve the package-rule difference.
3. Keep the I3 build under the existing task-5 preparation plan. Preserve all existing
   and manual derivatives. Recheck eligibility inside the planned write transaction.
   Do not start a second index build from this sheet. No conflicting live build was
   established by this read-only inspection; launch-time process checks remain required.
4. Revalidate the configuration hash, selected query hashes and labels, index state,
   cluster files, and rule files. Stop and record any relevant change before comparison.
   A rebuild can make a later profile incomparable with an earlier profile.
5. Reconcile all running benchmark processes and run-job locks before dispatch.
   A profile lock is not a global queue lock. Save intent before the run POST.
   Reconcile an uncertain POST with PID commands, locks, and log timestamps before retry.
6. Check live GPU capacity before every new resident model. Keep the required 20 GB
   safety margin. Keep unrelated GPU work active. Do not restart or reload llama-swap.
7. Use the configured lab interpreter for barcode profiles. The system interpreter
   lacks ZXing in the inspected environment. Local profiles also require PyTorch and
   cached Hugging Face weights. Do not start a package installation from this sheet.
8. Require an exited runner, a final `done` event, zero query errors, and full persisted
   query coverage for success. Preserve every failed or stopped attempt. Cached queue
   latency does not prove a fresh-image 3-second demo deadline.

The only new repository artifact from this inspection is this report.
