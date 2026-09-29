# Rotation test of DINOv3 embeddings, 2026-09-29

Source: owner message of 2026-09-29T02:02:13+0300 ("in separate folder try same tests but
with dinov3 models"). Session: drink-atlas-workspace-b6. The method is the method of
[rotation-similarity-2026-09-29.md](rotation-similarity-2026-09-29.md), parts 1 to 4,
with the entries `gx10-dinov3-vitb16` (768 values) and `gx10-dinov3-vitl16` (1024 values).
The wine, the image, the rotations, the backgrounds, the query offset, and the reference
sets are the same. Artifacts (not in git): `docs/reports/rotation-dinov3-2026-09-29/`
(part 1 in the root, `multiref/` for part 2, `refsets/` for parts 3 and 4).

## Checks of the set-up

1. `prepare()` and the 0° white rebuild give the pixels of the stored index image.
2. The stored image, sent alone, gives the cosine 0.999932 (ViT-B/16) and 0.999787
   (ViT-L/16) to its index vector. The effect of one image in a request (NaFlex p256 of
   SigLIP2) is not present for DINOv3.
3. About 1,750 embeddings, 0 failures, about 2 minutes on the gateway.

## Part 1: one index vector

![Cosine by angle](rotation-dinov3-2026-09-29/chart-by-model.png)

| Entry | Background | 0° | 5° | 10° | 20° | 45° | 90° | 135° | 180° | 270° | 355° | Mean 5°–355° | Minimum (angle) | Rank > 1 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| dinov3-vitb16 | white | 1.000 | 0.930 | 0.873 | 0.770 | 0.674 | 0.753 | 0.506 | 0.622 | 0.732 | 0.926 | 0.645 | 0.479 (150°) | 0 of 72 |
| dinov3-vitb16 | black | 0.987 | 0.916 | 0.868 | 0.767 | 0.668 | 0.745 | 0.495 | 0.584 | 0.718 | 0.920 | 0.635 | 0.455 (150°) | 1 of 72 |
| dinov3-vitl16 | white | 1.000 | 0.860 | 0.741 | 0.652 | 0.606 | 0.807 | 0.531 | 0.776 | 0.800 | 0.874 | 0.634 | 0.530 (140°) | 22 of 72 |
| dinov3-vitl16 | black | 0.988 | 0.852 | 0.747 | 0.652 | 0.602 | 0.794 | 0.542 | 0.757 | 0.784 | 0.864 | 0.633 | 0.520 (145°) | 17 of 72 |

## Parts 2 to 4: reference sets

![Mean score of each reference set](rotation-dinov3-2026-09-29/refsets/chart-summary-mean.png)

![Score by the distance to the nearest reference angle](rotation-dinov3-2026-09-29/refsets/chart-tolerance.png)

Mean cosine over the 72 black queries and over the 72 white queries with the offset
+2.5°. The heading gives the range, the step, and the number of vectors:

| Entry | Query | 1 vector | 0°–45°, 5° (10) | 0°–90°, 5° (19) | 0°–90°, 1° (91) | 360°, 12° (30) | 360°, 9° (40) | 360°, 8° (45) | 360°, 5° (72) | 360°, 3° (120) | 360°, 1° (360) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| dinov3-vitb16 | black | 0.640 | 0.829 | 0.888 | 0.890 | 0.965 | 0.970 | 0.970 | 0.979 | 0.976 | 0.979 |
| dinov3-vitb16 | white +2.5° | 0.649 | 0.839 | 0.902 | 0.906 | 0.984 | 0.986 | 0.989 | 0.988 | 0.995 | 0.997 |
| dinov3-vitl16 | black | 0.638 | 0.910 | 0.937 | 0.940 | 0.967 | 0.973 | 0.974 | 0.987 | 0.982 | 0.987 |
| dinov3-vitl16 | white +2.5° | 0.639 | 0.917 | 0.945 | 0.950 | 0.979 | 0.983 | 0.987 | 0.985 | 0.993 | 0.996 |

Mean cosine by the distance to the nearest reference angle (all full-circle sets):

| Entry | Query | 0° | 0.5° | 1° | 2° | 3° | 4° | 6° |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| dinov3-vitb16 | white | 1.000 | 0.997 | 0.994 | 0.989 | 0.985 | 0.979 | 0.967 |
| dinov3-vitb16 | black | 0.979 | — | 0.975 | 0.971 | 0.967 | 0.962 | 0.946 |
| dinov3-vitl16 | white | 1.000 | 0.995 | 0.991 | 0.982 | 0.982 | 0.974 | 0.961 |
| dinov3-vitl16 | black | 0.987 | — | 0.980 | 0.972 | 0.971 | 0.963 | 0.953 |

## Findings

1. With one vector, DINOv3 is much more sensitive to a large rotation than SigLIP2. The
   mean over the rotated angles is 0.63–0.65 (SigLIP2: 0.77–0.85). The minimum is
   0.46–0.53 at 140° to 150° (SigLIP2: 0.70–0.78).
2. DINOv3 is less sensitive to the background. At 0°, black gives 0.987–0.988 (SigLIP2:
   0.968–0.983). Over all angles, black costs 0.010 (ViT-B/16) and 0.001 (ViT-L/16).
3. ViT-L/16 has peaks at 90°, 180°, and 270° (0.76–0.81), like SigLIP2. ViT-B/16 has a
   weak peak at 90° and 270° only (0.72–0.75); its 180° is 0.58–0.62.
4. Self-retrieval with one vector: ViT-B/16 keeps rank 1 at 143 of 144 angles, although
   its cosine is low, because its cosine to the other wines is low too. ViT-L/16 loses
   rank 1 at 22 (white) and 17 (black) angles, mostly at 120° to 250°.
5. With reference vectors over the full circle, DINOv3 reaches higher scores than
   SigLIP2. Step 1°: white with offset 0.996–0.997 (SigLIP2: 0.981–0.990), black
   0.979–0.987 (SigLIP2: 0.964–0.982). Step 12° (30 vectors): 0.979–0.984 and 0.965–0.967.
6. DINOv3 tolerates a small angle error better than SigLIP2: 0.995–0.997 at 0.5° and
   0.991–0.994 at 1° (SigLIP2: 0.979–0.989 and 0.967–0.982). So the loss of SigLIP2 in
   the first degree is not a loss of every model.
7. Partial ranges help DINOv3 less: 0°–45° gives 0.829–0.920, 0°–90° gives 0.888–0.950.
   The range matters more than the step, as for SigLIP2.
8. The limits of the SigLIP2 report apply: one wine, synthetic rotations of the index
   image, and no fair rank for the reference sets.

## Reproduce

```sh
D=docs/reports/rotation-dinov3-2026-09-29; E="gx10-dinov3-vitb16 gx10-dinov3-vitl16"
python3 scripts/rotation_similarity.py --out $D --entries $E
python3 scripts/rotation_similarity_plots.py $D
python3 scripts/rotation_multiref.py --out $D/multiref --entries $E
python3 scripts/rotation_refsets.py --out $D/refsets --entries $E
python3 scripts/rotation_refsets.py --out $D/refsets --entries $E --reuse-vectors --sets 0:359:3 0:359:8 0:359:9 0:359:12
```
