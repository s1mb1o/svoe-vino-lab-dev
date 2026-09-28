# The benchmark of the embedding entries with the basic pipelines

Date: 2026-09-26. Plan: [40](../plans/40_embedding-benchmark.md). Source: owner message of
2026-09-26T01:43:59+0300. Session drink-atlas-workspace-e2 [9e7fe4].

## 1. Summary

1. The best entry is `gx10-siglip2-so400m-patch16-512`. On the set `my`, the pipeline
   `siglip2-512-crop` finds the true wine at rank 1 for 79.8 % of the positive photos,
   and at rank 5 or better for 95.1 %. `siglip2-512-as-is` is 0.7 points lower.
2. The entry of the two present basic pipelines, `siglip2-p256` (NaFlex, 256 patches), is
   lower than `siglip2-512` in the same form: 5.9 points with the crop (73.9 %) and 14.6
   points as is (64.5 %).
3. The crop of the package helps each entry. The gain falls when the model sees more
   image detail: +9.3 points for `siglip2-p256`, +0.7 points for `siglip2-512`.
4. DINOv3 (`dinov3-vitb16`, `dinov3-vitl16`) is far behind: 41 % at best. PE-Core and the
   timm NaFlex ViT are near `siglip2-p256`.
5. On `official-real-photos`, 15 of the 59 positive photos show wines with no catalogue
   image in the lab database, so no embedding can find them. For the 44 other photos,
   `siglip2-512-crop` gets 93.2 % at rank 1, and the present recognizer of vino-svoe.ru
   gets 59.1 % (90.9 % at rank 5). The sample is small.
6. At least one of the 22 runs finds 1,500 of the 1,625 positive photos of `my` (92.3 %)
   at rank 1. The models make different errors, so a fusion of two models MAY help.

## 2. What ran

- Pipelines: the two basic forms of the owner message of 2026-09-26T00:45:33+0300, for
  each of the 11 entries of `embeddings` in `config.yaml` (22 pipelines, 20 of them new).
  `as-is`: `white_background`, `resize` 1024. `crop`: SAM3 finds the package and the
  photo is cut to its box, the background inside the box stays, then `white_background`,
  `resize` 1024.
- The catalogue side: the index of each entry, built with the same steps for all
  entries. The query has the view `full` alone, so only the `full` items count: the
  package cut with the background removed, on white. The label items were not compared.
- Before the runs, `build_embeddings.py` added the missing items to each index (117 or
  fewer items; `gx10-siglip2-so400m-patch16-512` got its first full build of 4,047 items
  in about 8 min). So each of the 44 runs compares the same 4,043 current items of 2,046
  wines. 4 label items fail in each entry (no label cut); they do not count here.
- Sets: `my` (1,625 positive and 584 negative photos) and `official-real-photos` (59
  positive and 21 negative photos). 44 runs, 0 errors. Run ids end with `-bench40`.
- The gx10 entries ran through llama-swap 18081 with 4 photos at a time. The entry
  `local-siglip2-so400m-patch16-naflex-p256` ran on this Mac (MPS), one photo at a time.
  The whole queue took 67 min (01:56 to 03:03).
- A positive photo shows its wine. A negative photo shows another wine than its slug; a
  false match at 1 is that slug at rank 1. The column "wine in index" counts only the
  positive photos whose true wine has a catalogue image.

## 3. Results on `my`

1,625 positive photos; 1,591 of them show a wine with a catalogue image.

| # | Pipeline | R@1 | R@5 | R@10 | MRR | R@1, wine in index | R@5, wine in index | False match at 1 |
|---|---|---|---|---|---|---|---|---|
| 1 | `siglip2-512-crop` | 79.8 | 95.1 | 95.9 | 0.867 | 81.5 | 97.2 | 98 / 584 |
| 2 | `siglip2-512-as-is` | 79.1 | 95.0 | 95.9 | 0.860 | 80.8 | 97.0 | 96 / 584 |
| 3 | `siglip2-p512-crop` | 78.6 | 93.9 | 95.0 | 0.855 | 80.3 | 95.9 | 107 / 584 |
| 4 | `siglip2-p14-384-crop` | 77.5 | 93.8 | 95.1 | 0.848 | 79.2 | 95.8 | 94 / 584 |
| 5 | `siglip2-p14-384-as-is` | 76.1 | 92.6 | 94.7 | 0.835 | 77.7 | 94.6 | 95 / 584 |
| 6 | `siglip2-384-crop` | 75.3 | 92.5 | 94.9 | 0.830 | 76.9 | 94.5 | 99 / 584 |
| 7 | `local-siglip2-p256-crop` | 74.2 | 91.1 | 93.7 | 0.820 | 75.8 | 93.1 | 97 / 584 |
| 8 | `siglip2-p256-crop` | 73.9 | 90.9 | 93.3 | 0.817 | 75.4 | 92.8 | 100 / 584 |
| 9 | `siglip2-384-as-is` | 73.5 | 91.3 | 94.0 | 0.816 | 75.0 | 93.2 | 98 / 584 |
| 10 | `pe-core-l14-336-crop` | 73.4 | 91.8 | 94.5 | 0.816 | 75.0 | 93.8 | 102 / 584 |
| 11 | `naflexvit-p256-crop` | 73.3 | 92.4 | 94.3 | 0.818 | 74.9 | 94.4 | 103 / 584 |
| 12 | `siglip2-p512-as-is` | 73.2 | 91.9 | 94.4 | 0.816 | 74.8 | 93.9 | 109 / 584 |
| 13 | `pe-core-l14-336-as-is` | 69.8 | 90.0 | 93.7 | 0.785 | 71.3 | 92.0 | 94 / 584 |
| 14 | `siglip2-256-crop` | 68.4 | 88.5 | 92.0 | 0.774 | 69.8 | 90.4 | 106 / 584 |
| 15 | `local-siglip2-p256-as-is` | 65.6 | 85.8 | 89.2 | 0.747 | 67.0 | 87.6 | 89 / 584 |
| 16 | `naflexvit-p256-as-is` | 65.0 | 85.9 | 89.0 | 0.741 | 66.4 | 87.7 | 93 / 584 |
| 17 | `siglip2-p256-as-is` | 64.5 | 86.0 | 89.3 | 0.742 | 65.9 | 87.8 | 95 / 584 |
| 18 | `siglip2-256-as-is` | 60.4 | 83.3 | 87.6 | 0.706 | 61.7 | 85.0 | 103 / 584 |
| 19 | `dinov3-vitb16-crop` | 41.3 | 71.2 | 79.4 | 0.540 | 42.2 | 72.7 | 82 / 584 |
| 20 | `dinov3-vitl16-crop` | 40.7 | 71.0 | 78.2 | 0.531 | 41.5 | 72.5 | 67 / 584 |
| 21 | `dinov3-vitb16-as-is` | 32.4 | 60.9 | 71.2 | 0.446 | 33.1 | 62.2 | 67 / 584 |
| 22 | `dinov3-vitl16-as-is` | 27.6 | 54.1 | 63.2 | 0.385 | 28.2 | 55.2 | 48 / 584 |

## 4. Results on `official-real-photos`

59 positive photos; 44 of them show a wine with a catalogue image. The baseline is the
run `2026-09-25T193223Z-lab-vino-svoe-search-by-photo-official-real-photos` of the
present recognizer of vino-svoe.ru, matched by the SHA-256 of the photo.

| # | Pipeline | R@1 | R@5 | R@10 | MRR | R@1, wine in index | R@5, wine in index | False match at 1 |
|---|---|---|---|---|---|---|---|---|
| 1 | `siglip2-512-crop` | 69.5 | 74.6 | 74.6 | 0.718 | 93.2 | 100.0 | 7 / 21 |
| 2 | `siglip2-384-crop` | 69.5 | 74.6 | 74.6 | 0.715 | 93.2 | 100.0 | 6 / 21 |
| 3 | `siglip2-512-as-is` | 67.8 | 74.6 | 74.6 | 0.709 | 90.9 | 100.0 | 7 / 21 |
| 4 | `siglip2-p14-384-crop` | 67.8 | 74.6 | 74.6 | 0.706 | 90.9 | 100.0 | 6 / 21 |
| 5 | `siglip2-p512-crop` | 66.1 | 74.6 | 74.6 | 0.701 | 88.6 | 100.0 | 5 / 21 |
| 6 | `pe-core-l14-336-as-is` | 66.1 | 74.6 | 74.6 | 0.698 | 88.6 | 100.0 | 3 / 21 |
| 7 | `pe-core-l14-336-crop` | 64.4 | 74.6 | 74.6 | 0.692 | 86.4 | 100.0 | 5 / 21 |
| 8 | `siglip2-p14-384-as-is` | 64.4 | 74.6 | 74.6 | 0.686 | 86.4 | 100.0 | 5 / 21 |
| 9 | `siglip2-p512-as-is` | 64.4 | 72.9 | 74.6 | 0.685 | 86.4 | 97.7 | 6 / 21 |
| 10 | `local-siglip2-p256-crop` | 61.0 | 72.9 | 72.9 | 0.661 | 81.8 | 97.7 | 4 / 21 |
| 11 | `siglip2-384-as-is` | 59.3 | 74.6 | 74.6 | 0.664 | 79.5 | 100.0 | 5 / 21 |
| 12 | `siglip2-p256-crop` | 59.3 | 71.2 | 72.9 | 0.647 | 79.5 | 95.5 | 4 / 21 |
| 13 | `vino-svoe-search-by-photo` | 57.6 | 93.2 | 96.6 | 0.746 | 59.1 | 90.9 | 4 / 21 |
| 14 | `naflexvit-p256-crop` | 57.6 | 71.2 | 74.6 | 0.644 | 77.3 | 95.5 | 4 / 21 |
| 15 | `naflexvit-p256-as-is` | 54.2 | 69.5 | 72.9 | 0.613 | 72.7 | 93.2 | 4 / 21 |
| 16 | `siglip2-256-crop` | 49.1 | 72.9 | 74.6 | 0.606 | 65.9 | 97.7 | 2 / 21 |
| 17 | `local-siglip2-p256-as-is` | 47.5 | 69.5 | 71.2 | 0.570 | 63.6 | 93.2 | 4 / 21 |
| 18 | `siglip2-p256-as-is` | 47.5 | 67.8 | 69.5 | 0.565 | 63.6 | 90.9 | 4 / 21 |
| 19 | `siglip2-256-as-is` | 40.7 | 62.7 | 66.1 | 0.516 | 54.5 | 84.1 | 2 / 21 |
| 20 | `dinov3-vitl16-crop` | 30.5 | 55.9 | 57.6 | 0.416 | 40.9 | 75.0 | 1 / 21 |
| 21 | `dinov3-vitb16-crop` | 28.8 | 54.2 | 59.3 | 0.391 | 38.6 | 72.7 | 1 / 21 |
| 22 | `dinov3-vitb16-as-is` | 22.0 | 40.7 | 50.8 | 0.313 | 29.5 | 54.5 | 2 / 21 |
| 23 | `dinov3-vitl16-as-is` | 17.0 | 45.8 | 49.1 | 0.275 | 22.7 | 61.4 | 2 / 21 |

For the 44 photos with a catalogue image, `siglip2-512-crop` and vino-svoe.ru both find
24 at rank 1; `siglip2-512-crop` alone finds 17 more, and vino-svoe.ru alone finds 2. For
the 15 other photos, vino-svoe.ru finds 8 at rank 1 and all 15 at rank 5 or better.

## 5. The effect of the crop

R@1 on `my`, positive photos.

| Entry | `as-is` | `crop` | Gain |
|---|---|---|---|
| `siglip2-512` | 79.1 | 79.8 | +0.7 |
| `siglip2-p512` | 73.2 | 78.6 | +5.4 |
| `siglip2-p14-384` | 76.1 | 77.5 | +1.4 |
| `siglip2-384` | 73.5 | 75.3 | +1.8 |
| `siglip2-p256` | 64.5 | 73.9 | +9.3 |
| `local-siglip2-p256` | 65.6 | 74.2 | +8.6 |
| `pe-core-l14-336` | 69.8 | 73.4 | +3.6 |
| `naflexvit-p256` | 65.0 | 73.3 | +8.3 |
| `siglip2-256` | 60.4 | 68.4 | +7.9 |
| `dinov3-vitb16` | 32.4 | 41.3 | +8.9 |
| `dinov3-vitl16` | 27.6 | 40.7 | +13.1 |

The crop puts more pixels of the bottle into the model input. A model that sees much
detail already gains little.

## 6. Observations

1. The number of image patches follows the rank of the SigLIP2 entries: `patch16-512`
   (32 x 32 = 1,024 patches) is first, `patch14-384` (27 x 27 = 729) is second,
   `patch16-384` (24 x 24 = 576) is next, and `patch16-256` (256) is last. These patch
   counts come from the model names; this session did not read the gateway code.
2. At about the same patch count, a NaFlex entry beats a square entry: `siglip2-p256`
   crop 73.9 % against `siglip2-256` crop 68.4 %; `siglip2-p512` crop 78.6 % against
   `siglip2-384` crop 75.3 %. A NaFlex model keeps the aspect ratio of the tall bottle.
   How the gateway fits a tall photo into a square input (a stretch or a crop) was not
   checked.
3. The local copy of `siglip2-p256` gives nearly the same metrics as the gateway (as is
   65.6 % against 64.5 %, crop 74.2 % against 73.9 %). But for 65 of the 1,625 positive
   photos, one of the two as-is runs has the true wine at rank 1 and the other does not.
   So the two model paths are not identical. The cause was not checked.
4. The errors of the best run stand close to the truth: of the 1,625 positive photos of
   `siglip2-512-crop`, 1,297 are at rank 1, 177 at rank 2, 47 at rank 3, 38 at rank 4 to
   10, and 66 are not in the top 10. The median score margin is 0.045 for a correct answer
   and 0.008 for a wrong answer. A margin rule MAY mark the uncertain answers.
5. The false match at 1 of the negative photos stays between 89 and 109 of 584 for the
   SigLIP2, PE-Core, and NaFlex ViT entries. A better model does not lower it. A very
   likely cause: a negative photo often shows a near wine of the same producer. DINOv3
   has fewer false matches (48 to 82). Very likely it ranks near wines lower in general;
   it does not reject them, because an embedding pipeline always answers.
6. An embedding pipeline always answers. These runs do not measure a rule for "no
   match".

## 7. Defects of the data found on the way

1. 34 positive photos of `my` show 15 wines with no catalogue image in the lab database
   (14 `Active`, 1 `Disabled`): `agora-muskat` (4), `aligote-barrel-2024` (3),
   `aratti-shardone-beloe-suhoe` (1), `arie-vyderzhka-bochka-francziya-2020` (2),
   `b-yu-rne-krasnostop-suhoe-krasnoe-classic` (3), `balaklava-muskat` (6),
   `balaklava-pino-nuar` (1), `bryut-rozovoe-zolotaya-balka` (1), `bukovinka` (1),
   `grand-jete-blanc-de-blancs` (1), `pozdnij-sbor-beloe` (2), `risling` (2),
   `shardone-balaklava` (2), `shato-pino-aligote-rkatsiteli-beloe-suhoe-12` (1),
   `vysokij-bereg-risling-zelenaya-seriya-1` (4).
2. 15 positive photos of `official-real-photos` show 10 such wines: `balaklava-muskat`,
   `bukovinka`, `czitronnyj-magaracha` (2), `oleg` (2), `pobeda`, `pozdnij-sbor-krasnoe`,
   `roze-2` (3), `rozovoe-zoloto`, `rubin-golodrigi` (2), `zhemchuzhnaya-9-aligote-czitron`.
   A catalogue image for these wines raises the R@1 limit of this set from 74.6 % to
   100 %.
3. 5 photos of `my` are byte-equal to catalogue images of other wines. Two catalogue
   cards hold photos of other wines:
   `fanagoriya-100-ottenkov-krasnogo-kaberne-kaberne-sovinon-krasnoe-suhoe-135`
   (`main_patched` = `q-000001`, a photo of `a-gordienko-m-nikolaev-pino-nuar-…`;
   `full_front` = `q-000299`, a photo of `agora-yachting-chardonnay`) and
   `avtohtonnoe-vino-kryma-beloe-suhoe` (`full_front`, `full_back`, `label_back` =
   photos of three other wines). These wines take rank 1 for their photos. The defects
   are not in `docs/catalogue-defects.md` yet.

## 8. Limits of this benchmark

1. The latency of these runs is not a real-time figure. The gx10 runs sent 4 photos at a
   time, and the crop runs read the SAM3 answers from `data/cache/sam3/`. A real SAM3 call
   adds about 1.2 s to a crop photo (`ResearchLog.md`, 2026-09-26).
2. Each pipeline ran one time on each set. A second run of the same pipeline can differ a
   little: the run of `siglip2-p256-as-is` of 01:07 gave 64.6 %, this run 64.5 %, with 4
   more items in the index.
3. `official-real-photos` is small (44 comparable photos). One photo is 2.3 points.
4. The catalogue defects of section 7 lower each run. Very likely they lower the absolute
   values more than they change the order of the entries.

## 9. Recommendations

1. Use `gx10-siglip2-so400m-patch16-512` as the embedding of the next pipelines.
   `siglip2-512-as-is` needs no SAM3 call and is only 0.7 points behind the crop. So it
   is the fast choice; `siglip2-512-crop` is the accurate choice.
2. Add catalogue images for the 23 wines of section 7, and correct the two cards of
   section 7 item 3.
3. Next experiments: the view `label` of the query (the steps of the entry); a fusion of
   `siglip2-512` and `siglip2-p14-384`; a margin rule for uncertain answers; the
   question how the gateway fits a tall photo into a square input.
4. Drop the DINOv3 entries from the match pipelines.

## 10. How to make the tables again

```bash
bash work/bench40/run_bench40.sh           # the queue: builds, then 44 runs
python3 work/bench40/report40.py           # the tables of all bench40 runs
```

The runs are on `/runs`; the filter `Pipeline` selects one pipeline. A click on a
candidate image of a run shows the catalogue inputs and their cosines (plan 38).
