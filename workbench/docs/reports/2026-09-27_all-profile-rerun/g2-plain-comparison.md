# Completed plain NaFlex G2 comparison

Date: 2026-09-27. All seven runs are complete and validated.
This report uses saved results, traces, and frozen attempt identities only.

Package cropping improves positive top-1 recall within all three indexes.
The net gains are 158, 88, and 47 answers for 256, 512, and 1024 patches.
Cropping also increases forbidden negative matches in the top 10 for all three indexes.
Additional background removal loses 16 net top-1 answers against the ordinary 256-patch crop.

## Quality

Every run contains 2228 query rows and 1851 unique image digests.
The fixed denominators are 1644 positive rows and 584 negative constraints.
All result records store `http_status=200`.
All runs have zero errors and zero degraded trace steps.
No failed, unavailable, or incorrect query was removed from a denominator.

| Profile | Correct R@1 / 1644 | Correct R@5 / 1644 | Forbidden top-1 / 584 | Forbidden top-10 / 584 |
|---|---:|---:|---:|---:|
| `siglip2-p256-as-is` | 1074 (65.33%) | 1429 (86.92%) | 98 | 422 |
| `siglip2-p256-crop` | 1232 (74.94%) | 1515 (92.15%) | 97 | 472 |
| `siglip2-p256-crop-seg` | 1216 (73.97%) | 1513 (92.03%) | 96 | 475 |
| `siglip2-p512-as-is` | 1219 (74.15%) | 1528 (92.94%) | 111 | 468 |
| `siglip2-p512-crop` | 1307 (79.50%) | 1558 (94.77%) | 108 | 480 |
| `siglip2-p1024-as-is` | 1300 (79.08%) | 1573 (95.68%) | 103 | 489 |
| `siglip2-p1024-crop` | 1347 (81.93%) | 1593 (96.90%) | 98 | 502 |

A forbidden negative prediction violates the saved negative constraint.
An allowed negative prediction is not a confirmed identification.

## Paired changes

The variant is compared with the reference on identical query identities.
Each pair uses the same frozen index and catalogue identity.

| Reference → variant | R@1 gained / lost; net | R@5 gained / lost; net | Forbidden top-1 introduced / removed; net | Forbidden top-10 introduced / removed; net |
|---|---:|---:|---:|---:|
| `siglip2-p256-as-is` → `siglip2-p256-crop` | 221 / 63; +158 | 101 / 15; +86 | 43 / 44; -1 | 66 / 16; +50 |
| `siglip2-p512-as-is` → `siglip2-p512-crop` | 141 / 53; +88 | 35 / 5; +30 | 38 / 41; -3 | 27 / 15; +12 |
| `siglip2-p1024-as-is` → `siglip2-p1024-crop` | 103 / 56; +47 | 30 / 10; +20 | 26 / 31; -5 | 26 / 13; +13 |
| `siglip2-p256-crop` → `siglip2-p256-crop-seg` | 35 / 51; -16 | 11 / 13; -2 | 16 / 17; -1 | 15 / 12; +3 |

The ordinary crop adds package segmentation before image preparation.
`siglip2-p256-crop-seg` also adds `remove_background`.
All profiles retrieve only the full view. The names do not imply label retrieval.
The [JSON evidence](g2-plain-comparison.json) contains every paired gained, lost, introduced, and removed query ID.

## Index coverage

| Patch budget | Current items | Missing / failed / stale | Full-view wines | Label-view wines |
|---|---:|---:|---:|---:|
| 256 | 4054 | 127 / 2 / 0 | 2051 | 2047 |
| 512 | 4054 | 127 / 2 / 0 | 2051 | 2047 |
| 1024 | 4181 | 0 / 2 / 0 | 2096 | 2092 |

The 1024-patch index was rebuilt before these runs. It contains 127 more current items
and 45 more wines in each view than the 256- and 512-patch indexes.
Thus, cross-budget comparisons with 1024 do not isolate the patch budget.
The crop-versus-as-is comparisons within each budget do not have this coverage difference.
All budgets use the same served model, `siglip2-so400m-patch16-naflex`.
The configured request budgets and index pairings differ.

## Observed bulk costs

| Profile | Runner wall, s | Intent-to-final, s | Package SAM3 cache hits / misses / unrecorded |
|---|---:|---:|---:|
| `siglip2-p256-as-is` | 81.1 | 82.288 | — |
| `siglip2-p256-crop` | 95.5 | 96.778 | 2168 / 0 / 60 |
| `siglip2-p256-crop-seg` | 93.4 | 94.753 | 2168 / 0 / 60 |
| `siglip2-p512-as-is` | 86.5 | 87.982 | — |
| `siglip2-p512-crop` | 98.4 | 99.820 | 2168 / 0 / 60 |
| `siglip2-p1024-as-is` | 110.0 | 111.688 | — |
| `siglip2-p1024-crop` | 113.1 | 114.798 | 2168 / 0 / 60 |

All runs use four workers and `use_cache=true`. Embedding trace steps do not record cache hits.
The 60 package steps without a cache flag use the alpha-image path.
These steps do not call SAM3.
Do not treat equal cache settings as proof of equal cache state.
The JSON retains trace-step totals and the saved per-row timing fields.
Each run's saved latency summary sets `comparable=false`.
Summed trace durations overlap across workers. They are not runner wall time.
These costs do not measure fresh sequential HTTP recognition or establish a three-second deadline.

The queue requests set `use_barcode=true`, but these profiles configure no barcode stage.
All seven frozen identities have `has_barcode=false`. No result trace contains a barcode step.

## Validation and sources

All result and query records match in query ID, path, digest, slug, label, and truth.
All five run-artifact hashes match each frozen attempt. Archived job-log hashes match.
Each attempt has verified runner termination, one successful final event, and complete results.
The saved `done` state records the completion-time input-identity check.
This offline review verifies that persisted evidence and repeats the artifact hashes after reading.
It does not inspect current database or index state.

Across all seven runs, the frozen fields differ only in profile, embedding index,
index identity, and the expected SAM3 endpoint used by crop profiles.
Within each crop-versus-as-is pair, only profile and endpoint fields differ.
Within the background-removal pair, only the profile field differs.

The JSON stores artifact hashes, identity-field hashes, exact counts, and source paths.

- `siglip2-p256-as-is`: [run](../../../runs/2026-09-27T014951Z-lab-siglip2-p256-as-is-my/run.json); [frozen attempt](attempts/siglip2-p256-as-is-a5a4e037bb55433781f49c05557f146e/attempt.json).
- `siglip2-p256-crop`: [run](../../../runs/2026-09-27T015229Z-lab-siglip2-p256-crop-my/run.json); [frozen attempt](attempts/siglip2-p256-crop-50b727f016ed4322a6bda496ebd1b08f/attempt.json).
- `siglip2-p256-crop-seg`: [run](../../../runs/2026-09-27T015809Z-lab-siglip2-p256-crop-seg-my/run.json); [frozen attempt](attempts/siglip2-p256-crop-seg-5bd0b5ed4fb647ae958ebbd93e5e5adf/attempt.json).
- `siglip2-p512-as-is`: [run](../../../runs/2026-09-27T020325Z-lab-siglip2-p512-as-is-my/run.json); [frozen attempt](attempts/siglip2-p512-as-is-d10178badcf84387ac0961776e9b74b5/attempt.json).
- `siglip2-p512-crop`: [run](../../../runs/2026-09-27T020907Z-lab-siglip2-p512-crop-my/run.json); [frozen attempt](attempts/siglip2-p512-crop-8e1bfc95df8d410ebdabbb728dd82a27/attempt.json).
- `siglip2-p1024-as-is`: [run](../../../runs/2026-09-27T021111Z-lab-siglip2-p1024-as-is-my/run.json); [frozen attempt](attempts/siglip2-p1024-as-is-e5cb6dd6321c46449621bfc23174e6cb/attempt.json).
- `siglip2-p1024-crop`: [run](../../../runs/2026-09-27T021340Z-lab-siglip2-p1024-crop-my/run.json); [frozen attempt](attempts/siglip2-p1024-crop-df766fbdfb4a4c5b99cef975a86156ea/attempt.json).
