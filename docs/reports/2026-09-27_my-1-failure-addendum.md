# Addendum: failures of `barcode-rerank-siglip2-512-crop-my-1`

Date: 2026-09-27. Session: drink-atlas-workspace-38 [2e502f]. Owner message of
2026-09-27T10:13:36+0300.

Run: `2026-09-27T070800Z-lab-barcode-rerank-siglip2-512-crop-my-1`.

The main analysis is [2026-09-27_my-1-failure-analysis.md](2026-09-27_my-1-failure-analysis.md).
Another session wrote it at 10:26. This addendum does not repeat it. It adds six
findings and one correction. The numbers come from the read-only script
[replay.py](2026-09-27_my-1-failure-addendum/replay.py). The script sends no request and
calls no model.

```text
python3 docs/reports/2026-09-27_my-1-failure-addendum/replay.py \
    runs/2026-09-27T011711Z-lab-barcode-rerank-siglip2-512-crop-my \
    runs/2026-09-27T070800Z-lab-barcode-rerank-siglip2-512-crop-my-1
```

## Facts that both reports agree on

- `my-1` holds the R@1 misses of the run `2026-09-27T011711Z-…-my` of the same pipeline.
  The first run on `my-1` with the old index gave R@1 0 %. So 12 % R@1 is not a product
  value. `my-1` is a diagnostic set.
- Most misses confuse two cards of one producer. The true card is in the top 5 for most
  misses.
- The re-rank ran for 95 photos. It gave no new R@1 hit. It demoted 10 base R@1 answers.
  On the full `my` set, it gave 51 hits and 10 losses.
- Ten photos decoded a code. Two codes had a `wine_code` row. Eight codes had no row.

## Finding 1: the 30 new hits come from the data

The index of the source run had 127 missing items. The index of this run has none.

| Cause of the hit | Photos |
|---|---:|
| The winning image of the true card entered the index after the source run | 27 |
| A new `wine_code` row gave a barcode hit | 2 |
| The same images, a changed order | 1 |

## Finding 2: the rule fixes of the re-rank do not raise R@1

The replay uses the saved VLM answers. It takes the base order from
`explain.base_rank`. The line "as coded" gives the real R@1 of both runs.

| Scoring | `my` R@1 (of 1,644) | Hits / losses on `my` | `my-1` R@1 (of 250) |
|---|---:|---:|---:|
| No re-rank | 1,351 | — | 40 |
| As coded | 1,392 | 51 / 10 | 30 |
| No vintage question, unless the slugs differ by a year | 1,391 | 48 / 8 | 32 |
| An answer `other` gives 0 | 1,390 | 48 / 9 | 31 |
| Keep the base order for a verdict with no separating feature | 1,389 | 46 / 8 | 32 |
| All three | 1,388 | 43 / 6 | 34 |

- Each fix removes some losses and removes more hits. The net change on `my` is -1 to
  -4.
- The "no separating feature" verdicts are coin flips. They gave 5 hits and 2 losses on
  `my`, and 2 losses on `my-1`.
- Fix 2 of the main report has the acceptance condition "retain the current net
  reranker benefit". The abstention alone misses this condition by 3 hits in the replay.
- A fix of the rule logic is a decision about predictability. It is not a gain of R@1.

## Finding 3: the re-rank trigger covers few confused pairs

The trigger needs a `combined` cluster of NaFlex-p256. The clusters use a cosine of 0.95
or more. The table counts the 157 genuine misses. A genuine miss is a miss whose answer
is not another positive slug of the same bytes.

| Cluster state of the miss | Genuine misses |
|---|---:|
| The rank-1 card is in no cluster | 90 |
| The true card is not in the cluster of the rank-1 card | 33 |
| Both cards are in one cluster | 34 |

- 152 genuine misses have two different catalogue images. Their median NaFlex-p256
  cosine is 0.910. Only 25 pairs have 0.95 or more. 85 pairs have 0.90 or more.
- A new rule cannot help 123 of the 157 genuine misses, because the trigger does not
  start or cannot move the true card.

## Finding 4: which feature separates the confused cards

The catalogue fields `producer`, `category`, `grapes`, and `name`, and the sugar word and
the numbers of the slug, were compared.

| Difference between the true card and the rank-1 card | Genuine misses |
|---|---:|
| Same producer; the colour, the sugar, or the grape differs | 90 |
| Same producer; only the ABV, the vintage, the line name, or nothing differs | 53 |
| Other producer | 14 |

- The front label usually prints the colour, the sugar, and the grape in large text.
  A text check can separate the 90 pairs. This is an upper limit, not an estimate.
- The ABV is small print. It is often on the back label. Example: `q-000003`. The two
  catalogue cards of Brut d'Or Blanc de Blancs show the same bottle and the vintage
  2021. Only the ABV of the slug differs (12 against 12.5). The photo shows the vintage
  2016 and no ABV. No recognizer can choose the card from this photo. These 53 pairs need
  a decision about the data: an alias, a variant group, or a merge.

## Finding 5: four back-label images are hubs

The catalogue has 4 images of the type `full_back`. In this run, a `full_back` image
wins rank 1 for 13 photos: 12 genuine misses and 1 hit. Three of the 4 images win. The
back label of `agrolayn-mountain-eagle-semillon-semilon-beloe-suhoe-11` wins 7 misses and
the 1 hit. The back of `aratti-shardone-beloe-suhoe` wins 3 misses. The back of
`vysokij-bereg-risling-zelenaya-seriya-2` wins 2 misses. The three query photos that were
checked (`q-000125`, `q-000205`, `q-000245`) show a back label.

- Back labels share one template: the health warning, the ЕАС mark, the recycling marks,
  and the barcode. SigLIP2 does not read the small text.
- A replay without the `full_back` items gives the true card rank 1 for none of the 12
  misses. The true card goes to rank 2 to 7, or stays absent. So the removal of these
  images is not a fix.
- Four of the 12 photos (`q-000060`, `q-000125`, `q-000214`, `q-000224`) decoded a code
  with no `wine_code` row. A verified mapping fixes these four. For the other back
  labels, OCR of the wine name on the back label is the path.

## Finding 6: shared catalogue images

Eight misses confuse two cards that have one catalogue image with the same SHA-256. One
pair is `derbent-vino-endemy-shardone-beloe-suhoe-13` (a still wine) and
`derbent-vino-endemy-shardone-beloe-bryut-105-125` (a sparkling brut). One of the two
cards probably has a wrong image. The other pairs are `aligote-avtorskoe` with
`aligote-avtorskoe-vino`, and `aligote-barrel-2024` with `aligote-barrel-2025`.

## Correction to the main report

The main report counts 67 misses whose answer is another positive slug of the same
bytes, and 153 genuine misses. This script counts 63 and 157. It uses the labels
`positive` of the set `my` in `data/lab.sqlite3`, with no row marked for deletion. The
labels of `queries.jsonl` of the source runs give the same 63. The cause of the
difference of 4 rows is not known.
