# Completed G2 barcode comparison

Date: 2026-09-27. All 14 runs are complete and validated.
Each barcode profile is paired with its exact plain variant.
This report reads saved results, traces, and frozen attempts only.

Barcode lookup adds 22–24 correct top-1 answers per profile, with no lost answers.
All seven profiles return the same 24 correct barcode answers.
The other 2204 rows retain the same predictions, candidate order, and relevant ranks.
Forbidden negative matches do not change.

## Quality

Every run contains 2228 query rows and 1851 unique image digests.
The fixed denominators are 1644 positive rows and 584 negative constraints.
All result records store `http_status=200`. All runs have zero errors and zero degraded trace steps.
No failed, unavailable, or incorrect row was removed from a denominator.

| Plain profile → barcode version | R@1 plain → barcode / 1644 | R@5 plain → barcode / 1644 | Forbidden top-1 / 584 | Forbidden top-10 / 584 |
|---|---:|---:|---:|---:|
| `siglip2-p256-as-is` | 1074 → 1096 | 1429 → 1450 | 98 → 98 | 422 → 422 |
| `siglip2-p256-crop` | 1232 → 1254 | 1515 → 1536 | 97 → 97 | 472 → 472 |
| `siglip2-p256-crop-seg` | 1216 → 1238 | 1513 → 1533 | 96 → 96 | 475 → 475 |
| `siglip2-p512-as-is` | 1219 → 1243 | 1528 → 1549 | 111 → 111 | 468 → 468 |
| `siglip2-p512-crop` | 1307 → 1330 | 1558 → 1579 | 108 → 108 | 480 → 480 |
| `siglip2-p1024-as-is` | 1300 → 1324 | 1573 → 1594 | 103 → 103 | 489 → 489 |
| `siglip2-p1024-crop` | 1347 → 1370 | 1593 → 1611 | 98 → 98 | 502 → 502 |

| Plain profile → barcode version | R@1 gained / lost; net | R@5 gained / lost; net | Forbidden top-1 introduced / removed; net | Forbidden top-10 introduced / removed; net |
|---|---:|---:|---:|---:|
| `siglip2-p256-as-is` | 22 / 0; +22 | 21 / 0; +21 | 0 / 0; +0 | 0 / 0; +0 |
| `siglip2-p256-crop` | 22 / 0; +22 | 21 / 0; +21 | 0 / 0; +0 | 0 / 0; +0 |
| `siglip2-p256-crop-seg` | 22 / 0; +22 | 20 / 0; +20 | 0 / 0; +0 | 0 / 0; +0 |
| `siglip2-p512-as-is` | 24 / 0; +24 | 21 / 0; +21 | 0 / 0; +0 | 0 / 0; +0 |
| `siglip2-p512-crop` | 23 / 0; +23 | 21 / 0; +21 | 0 / 0; +0 | 0 / 0; +0 |
| `siglip2-p1024-as-is` | 24 / 0; +24 | 21 / 0; +21 | 0 / 0; +0 | 0 / 0; +0 |
| `siglip2-p1024-crop` | 23 / 0; +23 | 18 / 0; +18 | 0 / 0; +0 | 0 / 0; +0 |

An allowed negative prediction is not a confirmed identification.
The [JSON evidence](g2-barcode-comparison.json) retains every paired change ID.

## Barcode returns and fallback

| Barcode profile | Cache hits / misses / unrecorded | Rows with codes | Rows with one wine match | Rows with codes but no unique return |
|---|---:|---:|---:|---:|
| `barcode-siglip2-p256-as-is` | 2228 / 0 / 0 | 54 | 24 | 30 |
| `barcode-siglip2-p256-crop` | 2228 / 0 / 0 | 54 | 24 | 30 |
| `barcode-siglip2-p256-crop-seg` | 2228 / 0 / 0 | 54 | 24 | 30 |
| `barcode-siglip2-p512-as-is` | 2228 / 0 / 0 | 54 | 24 | 30 |
| `barcode-siglip2-p512-crop` | 2228 / 0 / 0 | 54 | 24 | 30 |
| `barcode-siglip2-p1024-as-is` | 2228 / 0 / 0 | 54 | 24 | 30 |
| `barcode-siglip2-p1024-crop` | 2228 / 0 / 0 | 54 | 24 | 30 |

All seven profiles return the same 24 query IDs from barcode lookup.
These rows contain 24 unique image digests. All 24 barcode answers are correct positive rows.
The decoded-code records and lookup hits match across all seven profiles.
Each unique return contains one candidate and bypasses retrieval.
The other 2204 rows continue to the matching embedding pipeline.
A cache hit indicates a cached scan result. It does not imply a unique wine answer.
Native ZXing call totals are not recorded in these traces.
Do not convert cache flags into an instrumented native-call count.

| Plain profile → barcode version | Changed top-1: return / fallback | Changed positive rank: return / fallback | Changed candidate order: return / fallback |
|---|---:|---:|---:|
| `siglip2-p256-as-is` | 22 / 0 | 22 / 0 | 24 / 0 |
| `siglip2-p256-crop` | 22 / 0 | 22 / 0 | 24 / 0 |
| `siglip2-p256-crop-seg` | 22 / 0 | 22 / 0 | 24 / 0 |
| `siglip2-p512-as-is` | 24 / 0 | 24 / 0 | 24 / 0 |
| `siglip2-p512-crop` | 23 / 0 | 23 / 0 | 24 / 0 |
| `siglip2-p1024-as-is` | 24 / 0 | 24 / 0 | 24 / 0 |
| `siglip2-p1024-crop` | 23 / 0 | 23 / 0 | 24 / 0 |

The JSON also records changes in the forbidden slug rank on negative rows.
A one-candidate barcode return can change the candidate list even when top-1 stays correct.

## Observed bulk costs

| Plain profile → barcode version | Plain runner wall, s | Barcode runner wall, s | Summed barcode step, s |
|---|---:|---:|---:|
| `siglip2-p256-as-is` | 81.1 | 82.3 | 4.155 |
| `siglip2-p256-crop` | 95.5 | 93.6 | 4.745 |
| `siglip2-p256-crop-seg` | 93.4 | 92.2 | 5.954 |
| `siglip2-p512-as-is` | 86.5 | 85.9 | 3.987 |
| `siglip2-p512-crop` | 98.4 | 97.0 | 4.682 |
| `siglip2-p1024-as-is` | 110.0 | 108.7 | 5.149 |
| `siglip2-p1024-crop` | 113.1 | 110.3 | 4.106 |

All runs use four workers and `use_cache=true`. Equal settings do not prove equal cache state.
Embedding trace steps do not record cache hits.
Each run's saved latency summary sets `comparable=false`.
The JSON retains runner wall, intent-to-final time, and trace-step totals.
Step times overlap across workers. Summed step time is not runner wall.
These are cached bulk runs. They do not measure fresh sequential HTTP recognition
or establish a three-second response deadline.

## Coverage and validation

Each plain/barcode pair uses the same frozen index.
The p256 and p512 indexes each have 4054 current items and 127 missing items.
Each has 2051 full-view wines and 2047 label-view wines.
The rebuilt p1024 index has 4181 current items and no missing items.
It has 2096 full-view wines and 2092 label-view wines.
All three indexes retain two failed items and zero stale items.
The broader p1024 coverage confounds comparisons across patch budgets.
It does not confound the plain/barcode comparison within a matched pair.

All frozen paired identities differ only in profile and `has_barcode`.
Queries match exactly in query ID, path, digest, slug, label, and truth.
All five run-artifact hashes and archived job-log hashes match the frozen attempts.
All attempts record runner termination and one matching successful final event.
The saved `done` state records the completion-time input-identity check.
This offline analysis verifies persisted evidence and repeated artifact hashes.
It does not inspect current catalogue, image, or index state.

## Frozen sources

- `siglip2-p256-as-is`: [run](../../../runs/2026-09-27T014951Z-lab-siglip2-p256-as-is-my/run.json); [attempt](attempts/siglip2-p256-as-is-a5a4e037bb55433781f49c05557f146e/attempt.json).
- `barcode-siglip2-p256-as-is`: [run](../../../runs/2026-09-27T021623Z-lab-barcode-siglip2-p256-as-is-my/run.json); [attempt](attempts/barcode-siglip2-p256-as-is-c64060b4002c4182891ad65d55e0b7e0/attempt.json).
- `siglip2-p256-crop`: [run](../../../runs/2026-09-27T015229Z-lab-siglip2-p256-crop-my/run.json); [attempt](attempts/siglip2-p256-crop-50b727f016ed4322a6bda496ebd1b08f/attempt.json).
- `barcode-siglip2-p256-crop`: [run](../../../runs/2026-09-27T021823Z-lab-barcode-siglip2-p256-crop-my/run.json); [attempt](attempts/barcode-siglip2-p256-crop-c796f7db40814eae8073c391a87cb99a/attempt.json).
- `siglip2-p256-crop-seg`: [run](../../../runs/2026-09-27T015809Z-lab-siglip2-p256-crop-seg-my/run.json); [attempt](attempts/siglip2-p256-crop-seg-5bd0b5ed4fb647ae958ebbd93e5e5adf/attempt.json).
- `barcode-siglip2-p256-crop-seg`: [run](../../../runs/2026-09-27T022056Z-lab-barcode-siglip2-p256-crop-seg-my/run.json); [attempt](attempts/barcode-siglip2-p256-crop-seg-d4062801df7b4195b49a05f9e911167a/attempt.json).
- `siglip2-p512-as-is`: [run](../../../runs/2026-09-27T020325Z-lab-siglip2-p512-as-is-my/run.json); [attempt](attempts/siglip2-p512-as-is-d10178badcf84387ac0961776e9b74b5/attempt.json).
- `barcode-siglip2-p512-as-is`: [run](../../../runs/2026-09-27T022325Z-lab-barcode-siglip2-p512-as-is-my/run.json); [attempt](attempts/barcode-siglip2-p512-as-is-9fccd48b8cd04937b879e124abfd55aa/attempt.json).
- `siglip2-p512-crop`: [run](../../../runs/2026-09-27T020907Z-lab-siglip2-p512-crop-my/run.json); [attempt](attempts/siglip2-p512-crop-8e1bfc95df8d410ebdabbb728dd82a27/attempt.json).
- `barcode-siglip2-p512-crop`: [run](../../../runs/2026-09-27T022600Z-lab-barcode-siglip2-p512-crop-my/run.json); [attempt](attempts/barcode-siglip2-p512-crop-4ec8f62ddb954718ba25b769a74179f5/attempt.json).
- `siglip2-p1024-as-is`: [run](../../../runs/2026-09-27T021111Z-lab-siglip2-p1024-as-is-my/run.json); [attempt](attempts/siglip2-p1024-as-is-e5cb6dd6321c46449621bfc23174e6cb/attempt.json).
- `barcode-siglip2-p1024-as-is`: [run](../../../runs/2026-09-27T022832Z-lab-barcode-siglip2-p1024-as-is-my/run.json); [attempt](attempts/barcode-siglip2-p1024-as-is-b1fc862e03b44a14b513e1b87db5e573/attempt.json).
- `siglip2-p1024-crop`: [run](../../../runs/2026-09-27T021340Z-lab-siglip2-p1024-crop-my/run.json); [attempt](attempts/siglip2-p1024-crop-df766fbdfb4a4c5b99cef975a86156ea/attempt.json).
- `barcode-siglip2-p1024-crop`: [run](../../../runs/2026-09-27T023118Z-lab-barcode-siglip2-p1024-crop-my/run.json); [attempt](attempts/barcode-siglip2-p1024-crop-127072ef747844499dc7b4949bc7826e/attempt.json).
