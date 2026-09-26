# The full benchmark of 2026-09-26 on the test set `my`

Date: 2026-09-26. Session drink-atlas-workspace-39 / CLUSTERS [fb59ad].
Source: the owner message of 2026-09-26T11:30:00+0300 («run full benchmark with my
dataset») and the answer «All 45 pipelines» of 11:34:00.

## The run

- Test set `my`: 2,209 labelled photos, 1,625 positive and 584 negative.
- 45 pipelines of `config.yaml`: the official recognizer `vino-svoe-search-by-photo`, the 22
  embedding pipelines (`<entry>-as-is`, `<entry>-crop` for 11 embedding entries), and the
  22 barcode pipelines (`barcode-<entry>-as-is`, `barcode-<entry>-crop`).
- Label `bench45`: the run directories are `runs/<stamp>-lab-<pipeline>-my-bench45`.
- Pass 1, 11:35 to 12:57: `work/bench45/run_bench45.sh`, one embedding entry at a time (the
  build of the 2 to 34 missing items, then the four pipelines), 4 photos at a time; the
  official recognizer in parallel (`run_official45.sh`, 11:36 to 11:55). The 20 barcode
  pipelines of the gx10 entries stopped at once: the script ran them with `python3`, and
  only `embedding_python` (the lab venv) holds zxing-cpp.
- Pass 2, 12:59 to 14:18: `work/bench45/rerun_barcode45.sh` ran these 20 pipelines with
  `embedding_python`. All 45 runs finished with exit status 0.
- No pipeline uses the cluster rules of plan 45: the re-rank at query time is plan 47.

## Results

- Best: `barcode-siglip2-512-crop`, R@1 82.6 %, R@5 96.7 %, MRR 0.890, median 376 ms.
  Without the barcode step, `siglip2-512-crop` gives R@1 81.3 %.
- The official recognizer `vino-svoe-search-by-photo`: R@1 67.6 %, R@5 88.7 %, median
  1,629 ms, 5 errors.
- The barcode step adds 1.2 to 1.3 points of R@1 to every pipeline: 19 to 21 photos move
  to rank 1, and no photo leaves rank 1. The step doubles the median time (about 170 ms
  to about 360 ms), because the decode runs on the Mac.
- The crop view is better than the view as-is for each embedding entry, by 0.6 (siglip2-512)
  to 13.3 points (dinov3-vitl16).
- Each pipeline that also ran in plan 40 (label `bench40`, 2026-09-25, the same 2,209
  photos) is 1.3 to 2.4 points higher in R@1. The cause was not examined. Candidates: the
  new database of 07:42 (plan 28 seed) and the new label cuts (schema 021).
- The negatives: the DINOv3 entries give the fewest false matches at rank 1 (46 to 80
  of 584 photos), and they also have the lowest R@1. Every other pipeline gives 91 to
  111.
- At least one lab run gets 1,538 of the 1,625 positive photos (94.6 %) at rank 1.

## The tables

Made by `work/bench45/report45.py`. The rows of the first table stand by R@1.

### All runs on `my`

| pipeline | embedding | pos / neg | R@1 | R@1 bench40 | R@5 | R@10 | MRR | neg false@1 | neg in top 10 | median ms | errors | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| barcode-siglip2-512-crop | gx10-siglip2-so400m-patch16-512 | 1625 / 584 | 82.6 | — | 96.7 | 97.5 | 0.890 | 100 / 584 | 475 / 584 | 376 | 0 | 223.3 |
| barcode-siglip2-512-as-is | gx10-siglip2-so400m-patch16-512 | 1625 / 584 | 82.0 | — | 96.7 | 97.4 | 0.884 | 94 / 584 | 467 / 584 | 335 | 0 | 199.4 |
| siglip2-512-crop | gx10-siglip2-so400m-patch16-512 | 1625 / 584 | 81.3 | 79.8 | 95.6 | 96.4 | 0.878 | 100 / 584 | 475 / 584 | 172 | 0 | 111.9 |
| barcode-siglip2-p512-crop | gx10-siglip2-so400m-patch16-naflex-p512 | 1625 / 584 | 81.1 | — | 96.0 | 96.9 | 0.878 | 108 / 584 | 479 / 584 | 383 | 0 | 231.1 |
| siglip2-512-as-is | gx10-siglip2-so400m-patch16-512 | 1625 / 584 | 80.7 | 79.1 | 95.5 | 96.4 | 0.872 | 94 / 584 | 467 / 584 | 141 | 0 | 81.9 |
| barcode-siglip2-p14-384-crop | gx10-siglip2-so400m-patch14-384 | 1625 / 584 | 80.2 | — | 95.9 | 97.0 | 0.873 | 94 / 584 | 476 / 584 | 356 | 0 | 213.4 |
| siglip2-p512-crop | gx10-siglip2-so400m-patch16-naflex-p512 | 1625 / 584 | 79.9 | 78.6 | 94.8 | 95.8 | 0.866 | 108 / 584 | 479 / 584 | 183 | 0 | 121.0 |
| siglip2-p14-384-crop | gx10-siglip2-so400m-patch14-384 | 1625 / 584 | 78.9 | 77.5 | 94.8 | 96.0 | 0.860 | 94 / 584 | 476 / 584 | 175 | 0 | 115.5 |
| barcode-siglip2-p14-384-as-is | gx10-siglip2-so400m-patch14-384 | 1625 / 584 | 78.8 | — | 94.9 | 96.7 | 0.860 | 97 / 584 | 465 / 584 | 343 | 0 | 498.5 |
| barcode-siglip2-384-crop | gx10-siglip2-so400m-patch16-384 | 1625 / 584 | 78.0 | — | 95.1 | 96.7 | 0.855 | 99 / 584 | 471 / 584 | 363 | 0 | 219.7 |
| siglip2-p14-384-as-is | gx10-siglip2-so400m-patch14-384 | 1625 / 584 | 77.5 | 76.1 | 93.7 | 95.6 | 0.847 | 97 / 584 | 465 / 584 | 145 | 0 | 84.8 |
| barcode-local-siglip2-p256-crop | local-siglip2-so400m-patch16-naflex-p256 | 1625 / 584 | 76.9 | — | 93.3 | 95.3 | 0.844 | 94 / 584 | 472 / 584 | 362 | 0 | 862.0 |
| siglip2-384-crop | gx10-siglip2-so400m-patch16-384 | 1625 / 584 | 76.7 | 75.3 | 93.9 | 95.6 | 0.843 | 99 / 584 | 471 / 584 | 158 | 0 | 103.8 |
| barcode-siglip2-p256-crop | gx10-siglip2-so400m-patch16-naflex-p256 | 1625 / 584 | 76.5 | — | 93.1 | 95.0 | 0.841 | 97 / 584 | 472 / 584 | 378 | 0 | 226.8 |
| barcode-pe-core-l14-336-crop | gx10-pe-core-l14-336 | 1625 / 584 | 76.4 | — | 94.3 | 96.4 | 0.843 | 102 / 584 | 463 / 584 | 388 | 0 | 231.2 |
| barcode-siglip2-384-as-is | gx10-siglip2-so400m-patch16-384 | 1625 / 584 | 76.2 | — | 93.7 | 96.1 | 0.842 | 97 / 584 | 451 / 584 | 334 | 0 | 225.6 |
| barcode-naflexvit-p256-crop | gx10-naflexvit-so400m-patch16-siglip2-p256 | 1625 / 584 | 76.1 | — | 94.2 | 95.9 | 0.842 | 100 / 584 | 474 / 584 | 377 | 0 | 225.8 |
| barcode-siglip2-p512-as-is | gx10-siglip2-so400m-patch16-naflex-p512 | 1625 / 584 | 75.8 | — | 94.2 | 96.2 | 0.840 | 111 / 584 | 468 / 584 | 382 | 0 | 218.4 |
| local-siglip2-p256-crop | local-siglip2-so400m-patch16-naflex-p256 | 1625 / 584 | 75.7 | 74.2 | 92.1 | 94.2 | 0.832 | 94 / 584 | 472 / 584 | 199 | 0 | 516.0 |
| siglip2-p256-crop | gx10-siglip2-so400m-patch16-naflex-p256 | 1625 / 584 | 75.3 | 73.9 | 91.9 | 93.8 | 0.829 | 97 / 584 | 472 / 584 | 200 | 0 | 132.1 |
| pe-core-l14-336-crop | gx10-pe-core-l14-336 | 1625 / 584 | 75.3 | 73.4 | 93.1 | 95.3 | 0.831 | 102 / 584 | 463 / 584 | 169 | 0 | 110.4 |
| siglip2-384-as-is | gx10-siglip2-so400m-patch16-384 | 1625 / 584 | 74.9 | 73.5 | 92.5 | 95.0 | 0.829 | 97 / 584 | 451 / 584 | 137 | 0 | 78.7 |
| naflexvit-p256-crop | gx10-naflexvit-so400m-patch16-siglip2-p256 | 1625 / 584 | 74.9 | 73.3 | 93.0 | 94.8 | 0.830 | 100 / 584 | 474 / 584 | 162 | 0 | 106.0 |
| siglip2-p512-as-is | gx10-siglip2-so400m-patch16-naflex-p512 | 1625 / 584 | 74.5 | 73.2 | 93.0 | 95.2 | 0.828 | 111 / 584 | 468 / 584 | 157 | 0 | 92.2 |
| barcode-pe-core-l14-336-as-is | gx10-pe-core-l14-336 | 1625 / 584 | 72.4 | — | 92.7 | 95.7 | 0.811 | 93 / 584 | 439 / 584 | 350 | 0 | 227.9 |
| pe-core-l14-336-as-is | gx10-pe-core-l14-336 | 1625 / 584 | 71.2 | 69.8 | 91.5 | 94.6 | 0.799 | 93 / 584 | 439 / 584 | 141 | 0 | 81.8 |
| barcode-siglip2-256-crop | gx10-siglip2-so400m-patch16-256 | 1625 / 584 | 71.1 | — | 90.9 | 94.2 | 0.800 | 108 / 584 | 433 / 584 | 369 | 0 | 221.8 |
| siglip2-256-crop | gx10-siglip2-so400m-patch16-256 | 1625 / 584 | 69.8 | 68.4 | 89.6 | 92.9 | 0.787 | 108 / 584 | 433 / 584 | 161 | 0 | 106.4 |
| barcode-local-siglip2-p256-as-is | local-siglip2-so400m-patch16-naflex-p256 | 1625 / 584 | 68.1 | — | 87.9 | 91.1 | 0.770 | 92 / 584 | 429 / 584 | 335 | 0 | 766.9 |
| barcode-naflexvit-p256-as-is | gx10-naflexvit-so400m-patch16-siglip2-p256 | 1625 / 584 | 67.6 | — | 87.8 | 90.8 | 0.764 | 96 / 584 | 426 / 584 | 326 | 0 | 208.4 |
| vino-svoe-search-by-photo | — | 1625 / 584 | 67.6 | — | 88.7 | 91.3 | 0.769 | 91 / 584 | 421 / 584 | 1629 | 5 | 1187.2 |
| barcode-siglip2-p256-as-is | gx10-siglip2-so400m-patch16-naflex-p256 | 1625 / 584 | 67.0 | — | 88.1 | 91.3 | 0.764 | 98 / 584 | 422 / 584 | 355 | 0 | 203.5 |
| local-siglip2-p256-as-is | local-siglip2-so400m-patch16-naflex-p256 | 1625 / 584 | 66.9 | 65.6 | 86.7 | 90.0 | 0.757 | 92 / 584 | 429 / 584 | 177 | 0 | 422.8 |
| naflexvit-p256-as-is | gx10-naflexvit-so400m-patch16-siglip2-p256 | 1625 / 584 | 66.4 | 65.0 | 86.7 | 89.7 | 0.752 | 96 / 584 | 426 / 584 | 133 | 0 | 77.6 |
| siglip2-p256-as-is | gx10-siglip2-so400m-patch16-naflex-p256 | 1625 / 584 | 65.8 | 64.5 | 86.9 | 90.1 | 0.752 | 98 / 584 | 422 / 584 | 161 | 0 | 106.8 |
| barcode-siglip2-256-as-is | gx10-siglip2-so400m-patch16-256 | 1625 / 584 | 63.0 | — | 85.6 | 89.8 | 0.731 | 106 / 584 | 397 / 584 | 381 | 0 | 255.6 |
| siglip2-256-as-is | gx10-siglip2-so400m-patch16-256 | 1625 / 584 | 61.7 | 60.4 | 84.3 | 88.5 | 0.718 | 106 / 584 | 397 / 584 | 142 | 0 | 84.3 |
| barcode-dinov3-vitl16-crop | gx10-dinov3-vitl16 | 1625 / 584 | 44.4 | — | 74.0 | 80.2 | 0.565 | 65 / 584 | 302 / 584 | 355 | 0 | 214.0 |
| barcode-dinov3-vitb16-crop | gx10-dinov3-vitb16 | 1625 / 584 | 44.2 | — | 73.9 | 81.3 | 0.568 | 80 / 584 | 317 / 584 | 345 | 0 | 208.7 |
| dinov3-vitl16-crop | gx10-dinov3-vitl16 | 1625 / 584 | 43.1 | 40.7 | 72.9 | 79.1 | 0.554 | 65 / 584 | 302 / 584 | 165 | 0 | 109.8 |
| dinov3-vitb16-crop | gx10-dinov3-vitb16 | 1625 / 584 | 43.0 | 41.3 | 72.8 | 80.2 | 0.556 | 80 / 584 | 317 / 584 | 146 | 0 | 96.7 |
| barcode-dinov3-vitb16-as-is | gx10-dinov3-vitb16 | 1625 / 584 | 36.0 | — | 63.8 | 73.8 | 0.479 | 65 / 584 | 255 / 584 | 319 | 0 | 190.0 |
| dinov3-vitb16-as-is | gx10-dinov3-vitb16 | 1625 / 584 | 34.8 | 32.4 | 62.7 | 72.7 | 0.467 | 65 / 584 | 255 / 584 | 115 | 0 | 67.2 |
| barcode-dinov3-vitl16-as-is | gx10-dinov3-vitl16 | 1625 / 584 | 31.1 | — | 58.1 | 65.7 | 0.422 | 46 / 584 | 212 / 584 | 323 | 0 | 266.5 |
| dinov3-vitl16-as-is | gx10-dinov3-vitl16 | 1625 / 584 | 29.8 | 27.6 | 57.0 | 64.5 | 0.410 | 46 / 584 | 212 / 584 | 137 | 0 | 78.8 |

### Paired with siglip2-p256-as-is

| pipeline | R@1 hits | hits the reference misses | reference hits it misses |
|---|---|---|---|
| barcode-siglip2-512-crop | 1342 | 333 | 60 |
| barcode-siglip2-512-as-is | 1332 | 316 | 53 |
| siglip2-512-crop | 1321 | 313 | 61 |
| barcode-siglip2-p512-crop | 1318 | 319 | 70 |
| siglip2-512-as-is | 1311 | 296 | 54 |
| barcode-siglip2-p14-384-crop | 1303 | 313 | 79 |
| siglip2-p512-crop | 1298 | 300 | 71 |
| siglip2-p14-384-crop | 1282 | 293 | 80 |
| barcode-siglip2-p14-384-as-is | 1280 | 290 | 79 |
| barcode-siglip2-384-crop | 1268 | 290 | 91 |
| siglip2-p14-384-as-is | 1259 | 270 | 80 |
| barcode-local-siglip2-p256-crop | 1250 | 243 | 62 |
| siglip2-384-crop | 1247 | 270 | 92 |
| barcode-siglip2-p256-crop | 1244 | 237 | 62 |
| barcode-pe-core-l14-336-crop | 1242 | 292 | 119 |
| barcode-siglip2-384-as-is | 1238 | 267 | 98 |
| barcode-naflexvit-p256-crop | 1237 | 259 | 91 |
| barcode-siglip2-p512-as-is | 1232 | 260 | 97 |
| local-siglip2-p256-crop | 1230 | 223 | 62 |
| siglip2-p256-crop | 1224 | 217 | 62 |
| pe-core-l14-336-crop | 1223 | 274 | 120 |
| siglip2-384-as-is | 1217 | 247 | 99 |
| naflexvit-p256-crop | 1217 | 239 | 91 |
| siglip2-p512-as-is | 1211 | 240 | 98 |
| barcode-pe-core-l14-336-as-is | 1177 | 248 | 140 |
| pe-core-l14-336-as-is | 1157 | 229 | 141 |
| barcode-siglip2-256-crop | 1155 | 261 | 175 |
| siglip2-256-crop | 1134 | 241 | 176 |
| barcode-local-siglip2-p256-as-is | 1107 | 62 | 24 |
| barcode-naflexvit-p256-as-is | 1099 | 107 | 77 |
| barcode-siglip2-p256-as-is | 1089 | 20 | 0 |
| local-siglip2-p256-as-is | 1087 | 42 | 24 |
| naflexvit-p256-as-is | 1079 | 87 | 77 |
| siglip2-p256-as-is | 1069 | 0 | 0 |
| barcode-siglip2-256-as-is | 1024 | 173 | 218 |
| siglip2-256-as-is | 1003 | 153 | 219 |
| barcode-dinov3-vitl16-crop | 721 | 175 | 523 |
| barcode-dinov3-vitb16-crop | 718 | 157 | 508 |
| dinov3-vitl16-crop | 701 | 156 | 524 |
| dinov3-vitb16-crop | 699 | 139 | 509 |
| barcode-dinov3-vitb16-as-is | 585 | 103 | 587 |
| dinov3-vitb16-as-is | 566 | 85 | 588 |
| barcode-dinov3-vitl16-as-is | 505 | 108 | 672 |
| dinov3-vitl16-as-is | 485 | 89 | 673 |

At least one lab run gets 1538 of 1625 positive photos (94.6 %) at rank 1.

### The barcode step

| pipeline | R@1 without | R@1 with the barcode step | gain in points | photos won | photos lost |
|---|---|---|---|---|---|
| dinov3-vitb16-as-is | 34.8 | 36.0 | +1.2 | 19 | 0 |
| dinov3-vitb16-crop | 43.0 | 44.2 | +1.2 | 19 | 0 |
| dinov3-vitl16-as-is | 29.8 | 31.1 | +1.2 | 20 | 0 |
| dinov3-vitl16-crop | 43.1 | 44.4 | +1.2 | 20 | 0 |
| local-siglip2-p256-as-is | 66.9 | 68.1 | +1.2 | 20 | 0 |
| local-siglip2-p256-crop | 75.7 | 76.9 | +1.2 | 20 | 0 |
| naflexvit-p256-as-is | 66.4 | 67.6 | +1.2 | 20 | 0 |
| naflexvit-p256-crop | 74.9 | 76.1 | +1.2 | 20 | 0 |
| pe-core-l14-336-as-is | 71.2 | 72.4 | +1.2 | 20 | 0 |
| pe-core-l14-336-crop | 75.3 | 76.4 | +1.2 | 19 | 0 |
| siglip2-256-as-is | 61.7 | 63.0 | +1.3 | 21 | 0 |
| siglip2-256-crop | 69.8 | 71.1 | +1.3 | 21 | 0 |
| siglip2-384-as-is | 74.9 | 76.2 | +1.3 | 21 | 0 |
| siglip2-384-crop | 76.7 | 78.0 | +1.3 | 21 | 0 |
| siglip2-512-as-is | 80.7 | 82.0 | +1.3 | 21 | 0 |
| siglip2-512-crop | 81.3 | 82.6 | +1.3 | 21 | 0 |
| siglip2-p14-384-as-is | 77.5 | 78.8 | +1.3 | 21 | 0 |
| siglip2-p14-384-crop | 78.9 | 80.2 | +1.3 | 21 | 0 |
| siglip2-p256-as-is | 65.8 | 67.0 | +1.2 | 20 | 0 |
| siglip2-p256-crop | 75.3 | 76.5 | +1.2 | 20 | 0 |
| siglip2-p512-as-is | 74.5 | 75.8 | +1.3 | 21 | 0 |
| siglip2-p512-crop | 79.9 | 81.1 | +1.2 | 20 | 0 |

