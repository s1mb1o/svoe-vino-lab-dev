# Z-rotation test of SigLIP2 embeddings, 2026-10-01

Source: owner messages of about 2026-09-30T23:56:00+0300 (part 1) and
2026-10-01T00:10:00+0300 (part 2).
Session: drink-atlas-workspace-08.
Script: [scripts/zrotation_similarity.py](../../scripts/zrotation_similarity.py) (the test,
the charts, and the collages). The charts have Russian text, as the charts of the rotation
test of 2026-09-29 (owner message of 2026-09-29T01:23:58+0300).
Artifacts (not in git): `docs/reports/zrotation-similarity-2026-10-01/`.
Related: [rotation-similarity-2026-09-29.md](rotation-similarity-2026-09-29.md) (a rotation
of the catalogue image in the image plane).

## Question

1. A real bottle turns about its vertical axis (the z axis). How does the cosine similarity
   of each photo to the catalogue image of the wine change during one turn?
2. `tools/bottle_rotation` makes copies of the catalogue image that are turned about the z
   axis from −30° to +30°. Does the maximum cosine over these copies make the similarity
   higher?

## Method

1. Wine: `winemaker-selection` ("Winemaker selection", Инкерманский ЗМВ). The catalogue has
   one image of this wine: the `main` image `3c0b5db8…` (WebP with alpha). Its package cut
   is `38e6b4e9566b8416d3231fa9daf08f6806223a7abae34f4ce6c5220b38d40ef0` (method `crop`,
   alpha > 32, 295 x 1094 pixels).
2. Reference: the cut with the steps of the view `full` after `remove_background`
   (`white_background`, then `resize` to a long side of 1,024 pixels). The model input is
   276 x 1024 pixels.
3. Photos: 33 Pixel photos (3072 x 4080 pixels) in
   `/Users/ashmelev/Downloads/winemaker-selection-z-rotation`, taken in 27 s. The bottle
   stands on a turntable. A second, smaller bottle stands in the background.
4. Query side: each photo gets the steps of the lab pipelines `siglip2-*-seg`, which are
   the steps of the view `full`: the SAM3 package cut (`embedding_run.cuts_of`),
   `remove_background`, `white_background`, and `resize` to 1,024 pixels. SAM3 took the
   turntable bottle in all 33 photos (the largest `wine bottle` instance). The model
   inputs are 274 to 279 x 1024 pixels.
5. Turned copies (part 2): `BottleRotator` of `tools/bottle_rotation` with a calibration of
   this cut (`CALIBRATION` in the script). The calibration has two layers: the front label
   (a polygon 2 pixels outside the measured edges) and the white print "INKERMAN" on the
   neck. The angles are −30° to +30° in steps of 5° (13 images). A positive angle moves the
   label to the right. The 0° copy is the cut itself. The presets of the tool are other
   wines, so the tool needed this new calibration.
6. Embedding: the six entries of the test of 2026-09-29 (NaFlex p256, p512, p1024; fixed
   256, 384, 512), llama-swap 18081, 8 images for each request.
7. Measures for each photo and each entry:
   - `cosine`: the cosine to the vector of the reference (the 0° copy);
   - `zmax_cosine` and `zmax_angle`: the maximum cosine over the 13 vectors of the turned
     copies, and the angle of that copy;
   - `rank`: the rank of the wine among the `full` vectors of the index, with the best item
     of each wine, and the best cosine of another wine (`best_other_cosine`).

## Checks of the set-up

1. `embeddings.prepare()` gives the same pixels as the stored index PNG.
2. The 0° turned copy gives the same pixels as `prepare()`.
3. The 0° vector gives the cosine 1.000000 to the stored index vector for each entry. Fixed
   256 gives 0.999901.

## Two differences between the photos and the catalogue image

1. The label design. The photographed bottle has a newer label: the vintage 2025, a tower
   logo with "19 61", and a green band "WINEMAKER'S SELECTION". The catalogue image has
   the older label: the vintage 2019, "SINCE 1961", and a gold band "WINEMAKER SELECTION".
   So the front photos also stay far below a cosine of 1.
2. The turn. The photos cover a little more than one turn. Photo 32 is the photo most
   similar to photo 1 (mean cosine of the six entries 0.966). Photo 33 is the photo most
   similar to photo 2 (0.972). So one turn is about 31 photo intervals, or about 26 s.
   The front label faces the camera at photos 9 to 11. The back label faces the camera at
   photos 21 to 27. The axis of the charts is the photo number, not an angle.

## Results

The six entries, cosine to the one vector of the catalogue cut, with no synthetic rotation.
An open circle marks a photo where another wine of the index is nearer than this wine
(rank > 1):

![Cosine of each photo to the one vector of the catalogue cut, six entries](zrotation-similarity-2026-10-01/chart-models.png)

The six entries, the maximum cosine over the 13 turned copies (owner answer of about
2026-10-01T00:28:00+0300). The cosine axis is the axis of the chart above. An open circle
marks a photo where the best other wine is at or above this maximum. That mark is
optimistic, because the other wines keep one vector:

![Maximum cosine over the 13 turned copies, six entries](zrotation-similarity-2026-10-01/chart-models-zmax.png)

One panel for each entry: one vector (blue), the maximum over the 13 turned copies
(orange), and the best other wine of the index (grey):

![One vector against the maximum over the turned copies](zrotation-similarity-2026-10-01/chart-by-model.png)

Collages at one common scale:

- The 13 turned copies: [collage-z.png](zrotation-similarity-2026-10-01/collage-z.png)
- The 33 model inputs of the photos: [collage-photos.png](zrotation-similarity-2026-10-01/collage-photos.png)

Cosine to the reference at selected photos (the front label faces the camera at 9 to 11):

| Entry | 1 | 3 | 5 | 7 | 9 | 10 | 11 | 13 | 15 | 17 | 21 | 25 | 29 | 33 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| naflex-p256 | 0.694 | 0.753 | 0.782 | 0.875 | 0.898 | 0.896 | 0.894 | 0.812 | 0.783 | 0.710 | 0.703 | 0.667 | 0.664 | 0.724 |
| naflex-p512 | 0.724 | 0.730 | 0.753 | 0.845 | 0.882 | 0.883 | 0.850 | 0.826 | 0.764 | 0.744 | 0.737 | 0.722 | 0.703 | 0.729 |
| naflex-p1024 | 0.702 | 0.752 | 0.794 | 0.875 | 0.898 | 0.899 | 0.896 | 0.845 | 0.794 | 0.757 | 0.741 | 0.771 | 0.713 | 0.750 |
| 256 | 0.676 | 0.714 | 0.794 | 0.828 | 0.881 | 0.873 | 0.860 | 0.819 | 0.748 | 0.744 | 0.708 | 0.667 | 0.653 | 0.709 |
| 384 | 0.702 | 0.719 | 0.803 | 0.847 | 0.894 | 0.895 | 0.884 | 0.842 | 0.805 | 0.747 | 0.751 | 0.731 | 0.713 | 0.728 |
| 512 | 0.733 | 0.758 | 0.812 | 0.881 | 0.895 | 0.904 | 0.897 | 0.837 | 0.823 | 0.767 | 0.757 | 0.746 | 0.740 | 0.755 |

Summary over the 33 photos (`summary.csv`). "Rank 1" counts the photos where this wine is
the nearest wine of the index. "Rank 1 with copies" counts the photos where the maximum
over the copies is above the best other wine. That count is optimistic, because the other
wines keep one vector.

| Entry | Mean cosine | Best cosine (photo) | Mean maximum over copies | Mean gain | Largest gain | Rank 1 (photos) | Rank 1 with copies |
|---|---:|---:|---:|---:|---:|---|---:|
| naflex-p256 | 0.749 | 0.901 (8) | 0.778 | +0.029 | +0.042 | 11 (5–15) | 13 |
| naflex-p512 | 0.758 | 0.883 (10) | 0.777 | +0.018 | +0.028 | 13 (3, 5–16) | 15 |
| naflex-p1024 | 0.780 | 0.899 (10) | 0.798 | +0.019 | +0.033 | 13 (4–16) | 14 |
| 256 | 0.731 | 0.881 (9) | 0.758 | +0.028 | +0.040 | 7 (6–11, 13) | 10 |
| 384 | 0.764 | 0.895 (10) | 0.775 | +0.011 | +0.034 | 12 (5–16) | 12 |
| 512 | 0.790 | 0.904 (10) | 0.805 | +0.015 | +0.026 | 12 (5–15, 22) | 16 |

Means for two sectors of the turn: the front label in view (photos 5 to 15) and the back
label in view (photos 18 to 30):

| Entry | Front: cosine | Front: maximum over copies | Back: cosine | Back: maximum over copies | Back: worst rank |
|---|---:|---:|---:|---:|---:|
| naflex-p256 | 0.846 | 0.867 | 0.685 | 0.724 | 1,212 |
| naflex-p512 | 0.825 | 0.845 | 0.720 | 0.734 | 176 |
| naflex-p1024 | 0.855 | 0.870 | 0.744 | 0.761 | 97 |
| 256 | 0.827 | 0.861 | 0.664 | 0.689 | 1,084 |
| 384 | 0.848 | 0.854 | 0.722 | 0.736 | 459 |
| 512 | 0.861 | 0.873 | 0.753 | 0.769 | 54 |

## Is there a win from the turned copies?

Owner message of about 2026-10-01T00:31:00+0300: the curves of the charts above are too
near to compare. The chart below shows the gain itself: the maximum cosine over the 13
copies minus the cosine to the one vector, for each photo. A grey band marks a photo where
the wine is already the nearest wine with the one vector. An orange bar marks a photo where
the wine becomes the nearest wine only with the copies (optimistic: the other wines keep
one vector).

![The gain of the turned copies for each photo](zrotation-similarity-2026-10-01/chart-gain.png)

| Entry | Mean gain, photos with rank 1 (count) | Mean gain, other photos (count) | Photos with rank 1: one vector → with copies |
|---|---:|---:|---:|
| naflex-p256 | +0.020 (11) | +0.034 (22) | 11 → 13 |
| naflex-p512 | +0.020 (13) | +0.017 (20) | 13 → 15 |
| naflex-p1024 | +0.016 (13) | +0.021 (20) | 13 → 14 |
| 256 | +0.033 (7) | +0.026 (26) | 7 → 10 |
| 384 | +0.007 (12) | +0.014 (21) | 12 → 12 |
| 512 | +0.012 (12) | +0.016 (21) | 12 → 16 |

The answer: no real win in this test.

1. The gain is small: +0.007 to +0.034 of cosine on average.
2. The gain does not come from a better match. On the photos where the wine is not the
   nearest wine (mostly back views), the gain is as large as on the matching photos, or
   larger (4 of 6 entries). The copies show only the front label, so they cannot match a
   back view better. The gain comes from the maximum over 13 similar vectors.
3. So each other wine would get a similar gain from its own copies. The 0 to 4 new photos
   with rank 1 are an upper limit. A fair test needs copies for each wine of the index.
   `tools/bottle_rotation` needs a calibration for each image, so such a test needs an
   automatic calibration first, for example from the SAM3 label box.

## Findings

1. The cosine follows the side of the bottle that faces the camera. It is highest when the
   front label faces the camera: 0.881 to 0.904 at photos 8 to 10. It falls to 0.59 to 0.79
   when the back label is in view (photos 18 to 30).
2. The curve is flat near the front view. From photo 8 to photo 11 (about 35° of the turn),
   the cosine changes by 0.007 (NaFlex p256, NaFlex p1024) to 0.033 (NaFlex p512). In the
   test of 2026-09-29, a rotation of 5° in the image plane cost 0.05 to 0.13. That test
   compared the image with itself, so the two numbers are not an exact comparison.
3. The wine is the nearest wine only while the front label is in view. For five entries,
   rank 1 covers photos 5 to 15 or a similar range: 11 to 13 photos, about ±60° around the
   front view. Fixed 256 has the smallest range: photos 6 to 11 and 13.
4. When the back label is in view (photos 18 to 30), another wine is nearer in 77 of the 78
   rows: rank 2 to 1,212. The one exception is fixed 512 at photo 22 (rank 1). The nearest
   other wine is mostly another Inkerman wine with a similar label design:
   `inkermanskiy-zmv-inkerman-bryut-shardone-beloe-135` is the nearest other wine in 74 of
   198 rows (43 of the 66 rows of photos 5 to 15). The catalogue has no back image of this
   wine, so a back view cannot match.
5. Part 2: the turned copies raise the cosine a little. The mean gain over the 33 photos is
   +0.011 (fixed 384) to +0.029 (NaFlex p256). The largest gain for one photo is +0.026 to
   +0.042.
6. The copies add 0 to 4 photos of rank 1 (optimistic): NaFlex p256 photos 3 and 4, NaFlex
   p512 photos 4 and 33, NaFlex p1024 photo 3, fixed 256 photos 5, 12, and 14, fixed 384
   none, fixed 512 photos 16, 23, 24, and 25. For the NaFlex entries, the new photos are
   photos 3 and 4, where the label enters the view (photo 33 has the view of photo 2). The
   copies show only the front label. Only fixed 512 gets back views (photos 23 to 25), where
   its margin to the best other wine was already small.
7. For the NaFlex entries, the best copy follows the real turn. Before the front view
   (photos 3 to 8, the label is on the right), NaFlex p512 and p1024 choose +20° to +30°.
   After the front view (photos 10 to 16, the label is on the left), they mostly choose
   −10° to −30°. So the direction of `tools/bottle_rotation` agrees with the real turn. The
   fixed entries do not follow the turn: fixed 256 chooses +25° for 12 of the photos 3 to
   17. The cause is not known.
8. Limits. The test uses one wine, one photo series, and one light setting. The
   photographed label differs from the catalogue label, so the absolute values are low for
   this wine. The copies come from one catalogue render: they cannot show the back label,
   the new label, or the real reflections of the room. The rank with copies is optimistic.
   The vectors come from batches of 8 images. The matcher sends one image in each request;
   the side finding of 2026-09-29 shows that NaFlex p256 then differs by up to 0.006.

## Files of the artifact folder

- `results.csv`: one row for each entry and photo, with the columns of the method and
  `time_s`, the time from the first photo.
- `z_cosines.csv`: the cosine of each photo to each turned copy, for each entry.
- `summary.csv`: the summary table.
- `meta.json`: the wine, the calibration, the SAM3 box of each photo, and the checks.
- `vectors/<entry>.npz`: `z_angles`, `z` (13 x 1152), `photos` (33 x 1152), and `stored`
  (the index vector). All vectors are L2-normalised float32.
- `images/`: the model inputs `z-30.png` to `z+30.png` and `photo_01.png` to
  `photo_33.png`.
- `chart-models.png` (one vector), `chart-models-zmax.png` (the maximum over the copies),
  `chart-by-model.png`, `chart-gain.png` (the gain), `collage-z.png`,
  `collage-photos.png`.

## Reproduce

Run from the workbench root. The first command sends 33 SAM3 requests and 36 embedding
requests (6 for each entry). A second run reads the SAM3 answers from
`data/cache/models/sam3/`. The run of 2026-10-01 took 1 minute 41 seconds. The script
changes no file outside `--out` and the SAM3 cache.

```sh
python3 scripts/zrotation_similarity.py --photos ~/Downloads/winemaker-selection-z-rotation \
    --out docs/reports/zrotation-similarity-2026-10-01
```

The charts again, with no request:

```sh
python3 scripts/zrotation_similarity.py --out docs/reports/zrotation-similarity-2026-10-01 --plots-only
```

Options: `--z-step <degrees>` (a divisor of 30), `--batch <images>`, `--entries <names>`.
