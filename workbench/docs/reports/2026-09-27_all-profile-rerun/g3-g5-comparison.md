# Completed G3–G5 profile comparison

Date: 2026-09-27. All 12 selected runs are complete and validated.
This report uses saved results, traces, and frozen attempts only.

Package cropping adds 135, 223, and 136 correct top-1 answers for DINOv3 B,
DINOv3 L, and NaFlexViT, respectively. It also increases forbidden negative matches.
Barcode lookup adds 22–23 correct top-1 answers per profile, with no lost answers.
All 2204 fallback rows preserve their complete candidate records, ranks, predictions, and outcomes.

## Quality

Each run has 2228 rows and 1851 unique image digests.
The fixed denominators are 1644 positive rows and 584 negative constraints.
All result records store `http_status=200`. All runs have zero errors and zero degraded steps.
No row was excluded or rescored. An allowed negative answer is not confirmed identification.

| Profile | Correct R@1 /1644 | Correct R@5 /1644 | Forbidden top-1 /584 | Forbidden top-10 /584 |
|---|---:|---:|---:|---:|
| `dinov3-vitb16-as-is` | 569 (34.61%) | 1035 (62.96%) | 65 | 255 |
| `dinov3-vitb16-crop` | 704 (42.82%) | 1204 (73.24%) | 80 | 320 |
| `barcode-dinov3-vitb16-as-is` | 591 (35.95%) | 1056 (64.23%) | 65 | 255 |
| `barcode-dinov3-vitb16-crop` | 726 (44.16%) | 1225 (74.51%) | 80 | 320 |
| `dinov3-vitl16-as-is` | 490 (29.81%) | 943 (57.36%) | 46 | 212 |
| `dinov3-vitl16-crop` | 713 (43.37%) | 1208 (73.48%) | 65 | 304 |
| `barcode-dinov3-vitl16-as-is` | 513 (31.20%) | 964 (58.64%) | 46 | 212 |
| `barcode-dinov3-vitl16-crop` | 736 (44.77%) | 1229 (74.76%) | 65 | 304 |
| `naflexvit-p256-as-is` | 1085 (66.00%) | 1426 (86.74%) | 96 | 426 |
| `naflexvit-p256-crop` | 1221 (74.27%) | 1532 (93.19%) | 100 | 473 |
| `barcode-naflexvit-p256-as-is` | 1107 (67.34%) | 1447 (88.02%) | 96 | 426 |
| `barcode-naflexvit-p256-crop` | 1243 (75.61%) | 1552 (94.40%) | 100 | 473 |

## Paired crop changes

Each row compares crop with as-is in the same model and barcode setting.
Positive cells show gained / lost answers and the net change.
Negative cells show introduced / removed forbidden matches and the net change.

| Family and barcode setting | R@1 gained / lost; net | R@5 gained / lost; net | Forbidden top-1 introduced / removed; net | Forbidden top-10 introduced / removed; net |
|---|---:|---:|---:|---:|
| DINOv3 B; plain | 182 / 47; +135 | 205 / 36; +169 | 33 / 18; +15 | 75 / 10; +65 |
| DINOv3 B; barcode | 182 / 47; +135 | 205 / 36; +169 | 33 / 18; +15 | 75 / 10; +65 |
| DINOv3 L; plain | 288 / 65; +223 | 307 / 42; +265 | 37 / 18; +19 | 102 / 10; +92 |
| DINOv3 L; barcode | 288 / 65; +223 | 307 / 42; +265 | 37 / 18; +19 | 102 / 10; +92 |
| NaFlexViT; plain | 216 / 80; +136 | 116 / 10; +106 | 38 / 34; +4 | 59 / 12; +47 |
| NaFlexViT; barcode | 216 / 80; +136 | 115 / 10; +105 | 38 / 34; +4 | 59 / 12; +47 |

All profiles retrieve the full view only. Crop profiles add package segmentation.
These profiles do not retrieve a label embedding tower.
The NaFlexViT crop gains one fewer top-5 answer with barcode enabled.
Barcode already resolves that query, `q-000040`, in both barcode profiles.
The [JSON evidence](g3-g5-comparison.json) retains all exact paired change IDs.

## Barcode returns and fallback

All six barcode profiles have 2228 scan-cache hits, zero misses, and zero unrecorded cache flags.
Each has 54 rows with decoded codes. Exactly 24 rows resolve to one catalogue wine.
The other 30 code-bearing rows do not produce a unique wine answer.
Return counts describe query rows, not distinct wine identities.

The decoded codes, lookup hits, and return decisions match across all six profiles.
The same 24 query IDs and 24 image digests return early.
Every early return is a correct positive answer with one candidate and no retrieval steps.
The 2204 remaining rows continue to the matching plain pipeline.

| Plain profile → barcode version | R@1 gained / lost | R@5 gained / lost | Changed fallback candidate records / ranks / outcomes |
|---|---:|---:|---:|
| `dinov3-vitb16-as-is` | 22 / 0 | 21 / 0 | 0 / 0 / 0 |
| `dinov3-vitb16-crop` | 22 / 0 | 21 / 0 | 0 / 0 / 0 |
| `dinov3-vitl16-as-is` | 23 / 0 | 21 / 0 | 0 / 0 / 0 |
| `dinov3-vitl16-crop` | 23 / 0 | 21 / 0 | 0 / 0 / 0 |
| `naflexvit-p256-as-is` | 22 / 0 | 21 / 0 | 0 / 0 / 0 |
| `naflexvit-p256-crop` | 22 / 0 | 20 / 0 | 0 / 0 / 0 |

Barcode introduces and removes zero forbidden negative matches at both top-1 and top-10.
Fallback equality includes the complete saved candidate payload, including scores and candidate ranks.
Positive truth ranks, negative forbidden-slug ranks, top-1 predictions, and outcomes also match.
All 24 early-return candidate lists change to one candidate. Top-1 may already have been correct.
The JSON separates early-return and fallback change IDs for each field.

A scan-cache hit does not imply a catalogue match.
Native ZXing call totals are not recorded. Do not infer a measured call count from cache flags.

## Observed bulk costs

| Profile | Runner wall, s | Intent-to-final, s | Summed barcode step, s | Package cache hits / misses / unrecorded |
|---|---:|---:|---:|---:|
| `dinov3-vitb16-as-is` | 73.6 | 76.110 | — | — |
| `dinov3-vitb16-crop` | 87.8 | 90.052 | — | 2168 / 0 / 60 |
| `barcode-dinov3-vitb16-as-is` | 67.0 | 68.942 | 5.528 | — |
| `barcode-dinov3-vitb16-crop` | 84.8 | 87.354 | 4.512 | 2144 / 0 / 60 |
| `dinov3-vitl16-as-is` | 91.1 | 93.073 | — | — |
| `dinov3-vitl16-crop` | 96.6 | 99.021 | — | 2168 / 0 / 60 |
| `barcode-dinov3-vitl16-as-is` | 78.4 | 80.878 | 5.688 | — |
| `barcode-dinov3-vitl16-crop` | 91.4 | 93.676 | 4.843 | 2144 / 0 / 60 |
| `naflexvit-p256-as-is` | 94.3 | 96.485 | — | — |
| `naflexvit-p256-crop` | 90.8 | 93.391 | — | 2168 / 0 / 60 |
| `barcode-naflexvit-p256-as-is` | 75.7 | 78.829 | 8.141 | — |
| `barcode-naflexvit-p256-crop` | 91.1 | 93.698 | 7.219 | 2144 / 0 / 60 |

All runs use four query workers and `use_cache=true`. Plain profiles configure no barcode stage,
although the queue request sets `use_barcode=true`.
Each crop run has 60 package steps with `cached:null` and `out.rule=alpha`.
These steps use the alpha-image path and do not call SAM3.
Embedding steps do not record cache hits. Equal settings do not establish equal cache state.

The saved gates mark each model target as not ready before its first plain as-is run.
Later runs in each family have a ready target.
The `q-000001` embedding steps take 4.864 s for DINOv3 B, 8.722 s for DINOv3 L,
and 18.747 s for NaFlexViT. These costs remain in the reported totals.
They include waiting and request work. They do not isolate model-load time.
Do not attribute the complete plain/barcode wall-time difference to barcode lookup.

Each run's saved latency summary sets `comparable=false`.
Intent-to-final is an elapsed attempt interval, not isolated startup time.
Step durations overlap across workers. Their sum is not runner wall time.
These cached bulk runs do not measure fresh sequential HTTP recognition or establish a three-second deadline.

## Coverage and validation

All three indexes record 4054 current items, 127 missing items, two failed items, and zero stale items.
Each has 2051 full-view wines and 2047 label-view wines.
Each matched pair uses the same frozen index.
The full saved query, catalogue, config, production-source, and lookup identities match across all 12 runs.
Model and embedding-index identities differ between families.
Crop pairs differ only in profile and the expected SAM3 endpoint field.
Plain/barcode pairs differ only in profile and `has_barcode`.

The broader NaFlex-1024 index in the separate G2 report has different coverage.
Do not interpret a comparison with that index as a model-only effect.

The analysis verifies all 60 run-artifact hashes, archived attempt and job-log hashes,
canonical identity hashes, and exact query/result/prediction pairing.
Each archived job has one matching successful final event and recorded runner termination.
Artifact hashes were repeated after analysis.
The saved `done` state records the completion-time identity check.
This report does not inspect current database, index, process, or source-photo state.

## Frozen sources

The JSON stores source paths, verified hashes, cache counts, trace totals, and paired query-ID lists.
- `dinov3-vitb16-as-is`: [run](../../../runs/2026-09-27T023829Z-lab-dinov3-vitb16-as-is-my/run.json); [attempt](attempts/dinov3-vitb16-as-is-fc73403c7fce4febbf67911eb1d19393/attempt.json).
- `dinov3-vitb16-crop`: [run](../../../runs/2026-09-27T024004Z-lab-dinov3-vitb16-crop-my/run.json); [attempt](attempts/dinov3-vitb16-crop-e3039a2059664883942f54289036828c/attempt.json).
- `barcode-dinov3-vitb16-as-is`: [run](../../../runs/2026-09-27T024350Z-lab-barcode-dinov3-vitb16-as-is-my/run.json); [attempt](attempts/barcode-dinov3-vitb16-as-is-cff8f59adbb34c4f85db8f6e52212339/attempt.json).
- `barcode-dinov3-vitb16-crop`: [run](../../../runs/2026-09-27T024757Z-lab-barcode-dinov3-vitb16-crop-my/run.json); [attempt](attempts/barcode-dinov3-vitb16-crop-22a1bbde90bc4010a1e5fbb04071a4cd/attempt.json).
- `dinov3-vitl16-as-is`: [run](../../../runs/2026-09-27T025009Z-lab-dinov3-vitl16-as-is-my/run.json); [attempt](attempts/dinov3-vitl16-as-is-8f0f1cea1f9844e48f8b37ed73e4c022/attempt.json).
- `dinov3-vitl16-crop`: [run](../../../runs/2026-09-27T025224Z-lab-dinov3-vitl16-crop-my/run.json); [attempt](attempts/dinov3-vitl16-crop-3fed533656824a9385e2323cba25bdbe/attempt.json).
- `barcode-dinov3-vitl16-as-is`: [run](../../../runs/2026-09-27T025427Z-lab-barcode-dinov3-vitl16-as-is-my/run.json); [attempt](attempts/barcode-dinov3-vitl16-as-is-f102f48b78894ce8817cf82bd94bfce5/attempt.json).
- `barcode-dinov3-vitl16-crop`: [run](../../../runs/2026-09-27T025654Z-lab-barcode-dinov3-vitl16-crop-my/run.json); [attempt](attempts/barcode-dinov3-vitl16-crop-3ebc6317391f4a38ad2d415a339cc13b/attempt.json).
- `naflexvit-p256-as-is`: [run](../../../runs/2026-09-27T025904Z-lab-naflexvit-p256-as-is-my/run.json); [attempt](attempts/naflexvit-p256-as-is-5d57d00440614efab15cfeb81754e18e/attempt.json).
- `naflexvit-p256-crop`: [run](../../../runs/2026-09-27T030149Z-lab-naflexvit-p256-crop-my/run.json); [attempt](attempts/naflexvit-p256-crop-cbcabfa50dad425ea0d74f549d5334ea/attempt.json).
- `barcode-naflexvit-p256-as-is`: [run](../../../runs/2026-09-27T030347Z-lab-barcode-naflexvit-p256-as-is-my/run.json); [attempt](attempts/barcode-naflexvit-p256-as-is-265354f2a8f24eeabd81dfe6f8c68f26/attempt.json).
- `barcode-naflexvit-p256-crop`: [run](../../../runs/2026-09-27T030611Z-lab-barcode-naflexvit-p256-crop-my/run.json); [attempt](attempts/barcode-naflexvit-p256-crop-7d17894475d14b2b8326bd2120ec5273/attempt.json).
