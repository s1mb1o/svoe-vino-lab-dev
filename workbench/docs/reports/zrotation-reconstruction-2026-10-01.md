# Turntable photos against 360° renders of the reconstructed bottle, 2026-10-01

Source: owner message of about 2026-10-01T08:30:00+0300.
Session: drink-atlas-workspace-08.
Script: [scripts/zrotation_reconstruction.py](../../scripts/zrotation_reconstruction.py) (the
renders, the embeddings, the charts). The charts have Russian text, as the charts of the
earlier rotation tests.
Artifacts (not in git): `docs/reports/zrotation-reconstruction-2026-10-01/`.
Related: [zrotation-similarity-2026-10-01.md](zrotation-similarity-2026-10-01.md) (the same
33 photos against the catalogue cut and the ±30° copies of `rotate_bottle.py`).

## Question

`tools/bottle_rotation/reconstruction` rebuilds the bottle of `winemaker-selection` and
renders any yaw from 0° to 360°. Do these renders match the turntable photos better than
the catalogue cut, also when the back label faces the camera?

## Method

1. Model: `output/bottle-reconstruction/winemaker-selection/model/` (`profile.json`,
   `atlas.png`, `material-mask.png`), used read-only. The tool rebuilt the bottle from three
   FRAP photos of the 2020 edition (front, back, back label). Its front has the 60-year
   emblem with lions and a gold band. The photos show the 2025 edition (tower "19 61",
   green band), and the catalogue cut shows the 2019 edition (gold band).
2. Renders: yaw 0° to 355° in steps of 5° (72 renders). Yaw 0° shows the front, 180° the
   back. The camera is the camera of `render_showcase.py`: orthographic, elevation 5°,
   `ortho_height` 1.12, `target_height` 0.5, synthetic studio shading, 400 x 1100 pixels,
   antialias 2. A render takes about 5 s on the Mac; 8 worker processes render the 72.
3. Each render is a transparent PNG, so it gets the processing of a transparent catalogue
   image: the alpha crop of `derive.derive_image` and the steps of the view `full`. The
   model input at 0° is 252 x 992 pixels.
4. Embedding: the six entries of the earlier tests (NaFlex p256, p512, p1024; fixed 256,
   384, 512), llama-swap 18081, 8 images for each request.
5. The photo vectors, the cosine to the catalogue cut, and the maximum over the ±30° copies
   come from `docs/reports/zrotation-similarity-2026-10-01/`.
6. Measures for each photo and entry:
   - `render_cosine` and `render_yaw`: the best cosine over the 72 renders and its yaw;
   - `rank`: the rank of the wine among the `full` items of the index (the best item of each
     wine);
   - `rank_with_renders`: the same rank when the score of this wine is the maximum of its
     index items and the 72 renders. This rank is optimistic: the other wines keep their
     index vectors.
7. Control: for each catalogue image of the other wines (2,318 `full` items), the maximum
   cosine over the 72 renders minus the cosine to the catalogue cut. This is the gain that
   the renders give to bottles that are not this wine.

## Checks of the set-up

1. The recomputed `rank` equals the rank of the earlier run in all 198 rows.
2. The 72 renders and the 432 embeddings had no failure. The run took 3 minutes.

## Results

The cosine of each photo (x) to each render (y). A dot marks the best render of a photo:

![Cosine of each photo to each render](zrotation-reconstruction-2026-10-01/chart-heatmap.png)

The best cosine of each photo: the catalogue cut (blue), the ±30° copies (orange), the 360°
renders (green), and the best other wine of the index (grey):

![Photos against the 360° renders](zrotation-reconstruction-2026-10-01/chart-by-model.png)

The gain of the renders for each photo (the best render minus the catalogue cut). The ink
line is the 95th percentile of the same gain for the catalogue images of the other wines:

![The gain of the renders and the control](zrotation-reconstruction-2026-10-01/chart-gain.png)

The 72 model inputs: [collage-renders.png](zrotation-reconstruction-2026-10-01/collage-renders.png)

Means over two sectors of the turn (front label in view: photos 5 to 15; back label in
view: photos 18 to 30), the control, and the photos with rank 1:

| Entry | Front: cut | Front: renders | Back: cut | Back: renders | Back: gain | Control: mean / p95 / max | Rank 1: cut → with renders (optimistic) | Photos above the control p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| naflex-p256 | 0.846 | 0.887 | 0.685 | 0.849 | +0.163 | +0.060 / +0.139 / +0.289 | 11 → 24 | 13 |
| naflex-p512 | 0.825 | 0.863 | 0.720 | 0.827 | +0.107 | +0.040 / +0.101 / +0.205 | 13 → 31 | 10 |
| naflex-p1024 | 0.855 | 0.875 | 0.744 | 0.848 | +0.104 | +0.041 / +0.098 / +0.188 | 13 → 32 | 12 |
| 256 | 0.827 | 0.888 | 0.664 | 0.770 | +0.105 | +0.057 / +0.145 / +0.306 | 7 → 14 | 4 |
| 384 | 0.848 | 0.877 | 0.722 | 0.829 | +0.107 | +0.073 / +0.167 / +0.300 | 12 → 31 | 4 |
| 512 | 0.861 | 0.890 | 0.753 | 0.848 | +0.096 | +0.057 / +0.127 / +0.239 | 12 → 33 | 1 |

## Findings

1. The renders follow the real turn. For NaFlex p256, p512, p1024 and fixed 384, 512, the
   best render moves by about 11° to 12° for each photo: about 280° at photos 3 to 5, near
   0° at photos 8 to 11, about 90° at photos 15 to 17, and near 180° at photos 22 to 28.
   NaFlex p512 and p1024 then reach about 260° at photos 32 and 33; fixed 384 and 512
   choose 110° to 120° there. NaFlex p1024 chooses 180° for each of the photos 22 to 28. So the models see the reconstructed back label in the back photos. Fixed 256 follows
   the turn less well: it stays at 315° to 325° for most of the photos 3 to 12.
2. The back views gain the most. Over photos 18 to 30, the mean cosine rises from 0.664 to
   0.753 (cut) to 0.770 to 0.849 (renders), a gain of +0.096 to +0.163. The front views gain
   less, +0.02 to +0.06: the reconstructed front is the 2020 edition, which also differs from
   the 2025 photos.
3. With the renders, the wine gets rank 1 on 14 to 33 of the 33 photos, against 7 to 13
   with the cut. This count is optimistic.
4. The control shows a generic part of the gain. The renders raise the cosine of the
   catalogue images of the other wines by +0.040 to +0.073 on average, +0.098 to +0.167 at
   the 95th percentile, and up to +0.31. On the back views, the gain of the photos is above
   the mean control gain, but near its 95th percentile. Only the NaFlex entries have many
   photos above that percentile (10 to 13 of 33); the fixed entries have 1 to 4.
5. The side renders cause most of the generic gain. For 5 of 6 entries, most of the top 5 %
   of the control gains come from the yaws 50° to 130° or 230° to 310°, where a render shows
   mostly dark glass and an edge of the label. For NaFlex p256, they come from the back
   yaws (135° to 225°).
6. So the renders carry a real signal (finding 1) and a generic lift (findings 4 and 5). In
   an index, 72 renders of one wine can attract photos of other wines, and a part of the
   rank-1 gain would go if the other wines had renders too. The reconstruction is manual and
   exists for this bottle alone, so a test with renders for each wine is not possible.
7. Limits. One bottle, one photo series, one camera for the renders. The control uses
   catalogue images, not photos. A false-match test against photos of other wines (for
   example the positive photos of the set `my`) is not done.

## Files of the artifact folder

- `results.csv`: one row for each entry and photo, with the measures of the method and the
  columns of the earlier run (`cosine`, `zmax_cosine`, `best_other_cosine`).
- `control.csv`: the control gain for each entry (mean, 95th percentile, maximum).
- `meta.json`: the camera, the yaws, the model folder, and the metadata of the earlier run.
- `vectors/<entry>.npz`: `yaws`, `renders` (72 x 1152), `photos` (33 x 1152), and `stored`
  (the index vector of the cut). All vectors are L2-normalised float32.
- `images/yaw_000.png` to `images/yaw_355.png`: the model inputs of the renders.
- `chart-heatmap.png`, `chart-by-model.png`, `chart-gain.png`, `collage-renders.png`.

## Reproduce

Run from the workbench root. The run sends 54 embedding requests (9 for each entry) and
takes about 3 minutes. It needs the output folder of `zrotation_similarity.py`.

```sh
python3 scripts/zrotation_reconstruction.py \
    --photos-from docs/reports/zrotation-similarity-2026-10-01 \
    --out docs/reports/zrotation-reconstruction-2026-10-01
```

The charts again, with no request:

```sh
python3 scripts/zrotation_reconstruction.py --out docs/reports/zrotation-reconstruction-2026-10-01 --plots-only
```

Options: `--yaw-step <degrees>`, `--batch <images>`, `--render-workers <N>`,
`--entries <names>`.
