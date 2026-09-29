# Rotation test of SigLIP2 embeddings, 2026-09-29

Source: owner message of 2026-09-29T01:10:49+0300.
Session: drink-atlas-workspace-b6.
Scripts: [scripts/rotation_similarity.py](../../scripts/rotation_similarity.py) (the test)
and [scripts/rotation_similarity_plots.py](../../scripts/rotation_similarity_plots.py) (the
charts and the collages, in Russian; owner message of 2026-09-29T01:23:58+0300).
Artifacts (not in git): `docs/reports/rotation-similarity-2026-09-29/`.

## Question

How does the cosine similarity of one catalogue image to its own index vector change when
the bottle turns in steps of 5°? The test covers the NaFlex entries p256, p512, and p1024
and the fixed-size entries 256, 384, and 512. The rotated image is on a white background
(case a) and on a black background (case b). The index vector was built on a white
background.

## Method

1. Wine: `avtohtonnoe-vino-kryma-beloe-suhoe` ("Автохтонное Вино Крыма белое сухое",
   Валерий Захарьин). The script takes the first Active wine that has a `main` image, no
   `main_patched` image, and a `full` item in each of the six indexes.
2. Main image: `9253bb7435cabe995db0bd29d288ceae00ebc2735a88607db423e2decfc82cf4`. The
   index image of the view `full` is 270 x 1024 pixels. The SAM3 cut has the same size, so
   the index `resize` step has the scale 1.0.
3. Base image: the SAM3 cut of the package (RGBA) on white or on black. These are the steps
   of the view `full` (`segment`, `remove_background`, `white_background`, `resize`),
   with the background color as the only change.
4. Rotation: counter-clockwise, 0° to 355° in steps of 5° (72 angles). PIL `rotate` with
   `BICUBIC`, `expand=True`, and the background color as the fill. The canvas grows to hold
   the rotated image. The bottle is not scaled down: it keeps the pixel size of the index
   image. At 45°, the canvas is 916 x 915 pixels.
5. Embedding: the `base_url` of each entry in `config.yaml` (llama-swap 18081, no cache),
   8 images for each request. The NaFlex entries send `max_num_patches`.
6. Measure: the cosine to the stored `full` vector of the same image.
7. Extra measure: the rank of the wine among the `full` vectors of the index, with the
   best item of each wine. The index holds the test image itself, so this is a
   self-retrieval check. Rank 1 means that the rotated image is nearer to its own index
   vector than to each item of another wine.

The entry "siglip2-1024" of the owner message does not exist. The gateway serves the
fixed-size models 256, 384, and 512 only. The test uses 256, 384, and 512.

## Checks of the set-up

1. `embeddings.prepare()` gives the same pixels as the stored index PNG.
2. The 0° white image of the script gives the same pixels as the stored index PNG.
3. The 0° white image in a batch gives the cosine 1.000 for each entry (256: 0.99989).

## Results

The charts have Russian text. Under the angle axis, thumbnails show the position of the
bottle at that angle. All thumbnails have one common scale, and a black frame shows the
border of each image. An open circle marks an angle where another wine is nearer than
this wine (rank > 1).

One panel for each entry, white and black background:

![Cosine by angle, one panel for each entry](rotation-similarity-2026-09-29/chart-by-model.png)

The six entries together, white background:

![Cosine by angle, white background](rotation-similarity-2026-09-29/chart-models-white.png)

The six entries together, black background:

![Cosine by angle, black background](rotation-similarity-2026-09-29/chart-models-black.png)

Cosine to the indexed `full` vector at selected angles:

| Entry | Background | 0° | 5° | 10° | 20° | 30° | 45° | 60° | 90° | 135° | 180° | 225° | 270° | 315° | 355° |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| naflex-p256 | white | 1.000 | 0.904 | 0.874 | 0.838 | 0.827 | 0.795 | 0.814 | 0.917 | 0.778 | 0.879 | 0.803 | 0.901 | 0.787 | 0.888 |
| naflex-p256 | black | 0.968 | 0.894 | 0.866 | 0.825 | 0.825 | 0.791 | 0.801 | 0.902 | 0.735 | 0.869 | 0.759 | 0.864 | 0.775 | 0.883 |
| naflex-p512 | white | 1.000 | 0.895 | 0.868 | 0.854 | 0.798 | 0.755 | 0.768 | 0.886 | 0.741 | 0.870 | 0.760 | 0.861 | 0.773 | 0.888 |
| naflex-p512 | black | 0.969 | 0.868 | 0.861 | 0.834 | 0.790 | 0.731 | 0.753 | 0.854 | 0.707 | 0.841 | 0.730 | 0.817 | 0.757 | 0.873 |
| naflex-p1024 | white | 1.000 | 0.937 | 0.929 | 0.907 | 0.856 | 0.852 | 0.827 | 0.947 | 0.830 | 0.880 | 0.818 | 0.941 | 0.856 | 0.943 |
| naflex-p1024 | black | 0.981 | 0.930 | 0.922 | 0.879 | 0.824 | 0.816 | 0.788 | 0.926 | 0.786 | 0.871 | 0.772 | 0.919 | 0.822 | 0.937 |
| 256 | white | 1.000 | 0.924 | 0.889 | 0.843 | 0.822 | 0.779 | 0.784 | 0.872 | 0.744 | 0.912 | 0.763 | 0.864 | 0.768 | 0.929 |
| 256 | black | 0.983 | 0.918 | 0.901 | 0.854 | 0.817 | 0.781 | 0.780 | 0.864 | 0.734 | 0.907 | 0.755 | 0.867 | 0.757 | 0.919 |
| 384 | white | 1.000 | 0.943 | 0.928 | 0.870 | 0.860 | 0.833 | 0.816 | 0.937 | 0.799 | 0.921 | 0.809 | 0.912 | 0.849 | 0.930 |
| 384 | black | 0.981 | 0.935 | 0.920 | 0.850 | 0.845 | 0.816 | 0.803 | 0.929 | 0.769 | 0.900 | 0.781 | 0.904 | 0.832 | 0.924 |
| 512 | white | 1.000 | 0.951 | 0.933 | 0.891 | 0.868 | 0.848 | 0.831 | 0.943 | 0.764 | 0.910 | 0.809 | 0.918 | 0.845 | 0.938 |
| 512 | black | 0.978 | 0.933 | 0.916 | 0.852 | 0.846 | 0.810 | 0.795 | 0.931 | 0.756 | 0.885 | 0.773 | 0.905 | 0.821 | 0.921 |

Summary over the 71 rotated angles (5° to 355°) and the rank check over all 72 angles:

| Entry | Background | Mean 5°–355° | Minimum (angle) | Mean black − white | Angles with rank > 1 | Worst rank |
|---|---|---:|---:|---:|---:|---:|
| naflex-p256 | white | 0.824 | 0.762 (125°) | — | 17 of 72 | 3 |
| naflex-p256 | black | 0.804 | 0.732 (125°) | -0.020 | 22 of 72 | 6 |
| naflex-p512 | white | 0.794 | 0.722 (115°) | — | 67 of 72 | 22 |
| naflex-p512 | black | 0.769 | 0.703 (125°) | -0.025 | 69 of 72 | 33 |
| naflex-p1024 | white | 0.853 | 0.779 (230°) | — | 8 of 72 | 2 |
| naflex-p1024 | black | 0.819 | 0.721 (230°) | -0.034 | 23 of 72 | 2 |
| 256 | white | 0.806 | 0.730 (235°) | — | 0 of 72 | 1 |
| 256 | black | 0.801 | 0.730 (130°) | -0.006 | 0 of 72 | 1 |
| 384 | white | 0.846 | 0.772 (120°) | — | 0 of 72 | 1 |
| 384 | black | 0.830 | 0.756 (120°) | -0.016 | 0 of 72 | 1 |
| 512 | white | 0.844 | 0.762 (120°) | — | 2 of 72 | 2 |
| 512 | black | 0.823 | 0.749 (235°) | -0.021 | 4 of 72 | 3 |

The wine that takes rank 1 is nearly always
`valeriy-zaharin-avtohtonnoe-vino-kryma-avtorskiy-kupazh-bastardo-saperavi-kefesiya-bastardo-magarachskiy-krasnoe-suhoe-12`
(808 of 864 rows). It is a red blend of the same producer with the same label design. At
0° on white, the best other wine has the cosine 0.877 to 0.956. So this wine is a hard
case for the rank check.

## Collages of the rotation steps

The collages show the 72 model inputs for each background at one common scale. A black
frame shows the border of each image. The collages show how the canvas grows from
270 x 1024 pixels at 0° to 916 x 915 pixels at 45°.

- White background: [collage-white.png](rotation-similarity-2026-09-29/collage-white.png)
- Black background: [collage-black.png](rotation-similarity-2026-09-29/collage-black.png)

## Control: small angles and padding without rotation

The drop from 0° to 5° is large. A control run separates the rotation from the change of
the canvas. "Pad" puts the unrotated bottle in the centre of a canvas with the size of the
5° or the 45° image. The file `rotation-similarity-2026-09-29/control.txt` holds the
output.

| Case | naflex-p256 | naflex-p512 | naflex-p1024 | 256 | 384 | 512 |
|---|---:|---:|---:|---:|---:|---:|
| white, rotation 1° | 0.922 | 0.959 | 0.964 | 0.959 | 0.976 | 0.966 |
| white, rotation 2° | 0.930 | 0.938 | 0.969 | 0.962 | 0.972 | 0.964 |
| white, rotation 3° | 0.904 | 0.913 | 0.949 | 0.957 | 0.961 | 0.957 |
| white, rotation 4° | 0.911 | 0.896 | 0.935 | 0.916 | 0.946 | 0.945 |
| white, rotation 5° | 0.904 | 0.895 | 0.937 | 0.924 | 0.943 | 0.951 |
| white, pad to the 5° canvas (358 x 1045) | 0.925 | 0.930 | 0.956 | 0.960 | 0.969 | 0.954 |
| white, pad to the 45° canvas (916 x 915) | 0.814 | 0.813 | 0.896 | 0.850 | 0.884 | 0.909 |
| black, rotation 0° | 0.968 | 0.969 | 0.981 | 0.983 | 0.981 | 0.978 |
| black, rotation 5° | 0.894 | 0.868 | 0.930 | 0.918 | 0.935 | 0.933 |
| black, pad to the 5° canvas (358 x 1045) | 0.906 | 0.911 | 0.955 | 0.954 | 0.956 | 0.943 |
| black, pad to the 45° canvas (916 x 915) | 0.800 | 0.792 | 0.842 | 0.821 | 0.873 | 0.891 |

## Findings

1. A small rotation already costs much. At 5°, the cosine falls to 0.87 to 0.95. At 1°,
   it falls to 0.92 to 0.98. The fall is not linear in the angle.
2. Most of the fall comes from the canvas, not from the rotation. On white, the padded,
   unrotated bottle on the 5° canvas loses 0.03 to 0.08. On the 45° canvas, it loses 0.09
   to 0.19. The rotation adds 0.00 to 0.07 to this. A larger canvas has more background, and the
   model scales the image down to its patch budget, so the bottle gets fewer pixels.
3. The curves have peaks at 90°, 180°, and 270° (0.82 to 0.95). These rotations are
   lossless and the canvas stays tight. 85° and 95° are 0.01 to 0.07 lower than 90°.
   The minimum is near the diagonals, at 115° to 135° and 225° to 235° (0.70 to 0.78).
4. The black background costs 0.017 to 0.032 at 0°. Over all angles, it costs 0.006
   (fixed 256) to 0.034 (NaFlex p1024) on average. Fixed 256 is the least sensitive to the
   background. NaFlex p1024 is the most sensitive.
5. Highest mean cosine over the rotated angles: NaFlex p1024 on white (0.853), then fixed
   384 (0.846) and fixed 512 (0.844). NaFlex p512 has the lowest mean (0.794 white, 0.769
   black), lower than NaFlex p256.
6. Self-retrieval: fixed 256 and fixed 384 keep rank 1 at each angle on both
   backgrounds. Fixed 512 loses it at 195° to 210°. NaFlex p1024 loses it at 8 (white) and
   23 (black) angles, NaFlex p256 at 17 and 22. NaFlex p512 loses it already at 5° (black) and
   10° (white), and at 67 and 69 of 72 angles. A high cosine to the own vector does not give rank 1: the
   distance to the nearest other wine counts.
7. The result is for one wine and one image. Another bottle shape, label, or neighbour
   wine can give other numbers. The order of the entries in finding 6 is weak evidence.

## Part 2: 10 reference vectors (0° to 45°)

Source: owner messages of 2026-09-29T01:34:10+0300 and 01:34:20 ("сделай отдельные
графики": the charts of part 2 are separate files). Script:
[scripts/rotation_multiref.py](../../scripts/rotation_multiref.py). Artifacts (not in
git): `rotation-similarity-2026-09-29/multiref/`.

### Method of part 2

1. Reference side: the index image of the view `full` on white, rotated counter-clockwise
   from 0° to 45° in steps of 5° (10 images). The rotation method is the method of part 1.
   Each model gives 10 reference vectors.
2. Query side: the same 144 images as in part 1 (0° to 355°, white and black).
3. Score: the maximum cosine over the 10 reference vectors. The column `cosine_single` of
   `multiref/results.csv` keeps the cosine to the one indexed vector. It differs from part 1
   by 0.0005 or less.
4. Vectors: `multiref/vectors/<entry>.npz` holds `reference_angles`, `reference` (10 x
   1152), `query_angles`, `query_white` and `query_black` (72 x 1152 each), and `stored`
   (the indexed vector). All vectors are L2-normalised float32. The 0° reference vector
   gives the cosine 1.000000 to the indexed vector (fixed 256: 0.999888).
5. No request holds one image alone (see the side finding).
6. The script does not change the catalogue index.

Two limits:

- On white, a query at 0° to 45° has the same pixels as a reference image, so its score is
  1.000. The informative angles are 50° to 355° on white, and each angle on black.
- The rank is optimistic. Only this wine has the 10 reference vectors. The other wines
  keep their one indexed vector, so this wine gets an advantage.

### Charts of part 2

![10 reference vectors, one panel for each entry](rotation-similarity-2026-09-29/multiref/chart-by-model.png)

![10 reference vectors, white background](rotation-similarity-2026-09-29/multiref/chart-models-white.png)

![10 reference vectors, black background](rotation-similarity-2026-09-29/multiref/chart-models-black.png)

### Results of part 2

| Entry | Background | Mean 5°–355°, 1 vector | Mean 5°–355°, 10 vectors | Gain | Minimum, 1 vector | Minimum, 10 vectors | Mean 50°–355°, 10 vectors | Rank > 1, 1 vector | Rank > 1, 10 vectors (optimistic) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| naflex-p256 | white | 0.824 | 0.940 | +0.116 | 0.762 (125°) | 0.879 (180°) | 0.931 | 17 of 72 | 0 of 72 |
| naflex-p256 | black | 0.804 | 0.918 | +0.114 | 0.732 (125°) | 0.869 (180°) | 0.909 | 22 of 72 | 0 of 72 |
| naflex-p512 | white | 0.794 | 0.946 | +0.152 | 0.722 (115°) | 0.899 (180°) | 0.938 | 67 of 72 | 0 of 72 |
| naflex-p512 | black | 0.769 | 0.917 | +0.148 | 0.703 (125°) | 0.872 (70°) | 0.909 | 69 of 72 | 0 of 72 |
| naflex-p1024 | white | 0.853 | 0.951 | +0.099 | 0.779 (230°) | 0.887 (180°) | 0.944 | 8 of 72 | 0 of 72 |
| naflex-p1024 | black | 0.819 | 0.918 | +0.099 | 0.721 (230°) | 0.838 (230°) | 0.910 | 23 of 72 | 0 of 72 |
| 256 | white | 0.806 | 0.930 | +0.124 | 0.730 (235°) | 0.862 (85°) | 0.920 | 0 of 72 | 0 of 72 |
| 256 | black | 0.801 | 0.921 | +0.121 | 0.730 (130°) | 0.856 (85°) | 0.912 | 0 of 72 | 0 of 72 |
| 384 | white | 0.846 | 0.946 | +0.100 | 0.772 (120°) | 0.905 (245°) | 0.938 | 0 of 72 | 0 of 72 |
| 384 | black | 0.830 | 0.933 | +0.102 | 0.756 (120°) | 0.892 (275°) | 0.925 | 0 of 72 | 0 of 72 |
| 512 | white | 0.844 | 0.946 | +0.102 | 0.762 (120°) | 0.897 (135°) | 0.938 | 2 of 72 | 0 of 72 |
| 512 | black | 0.823 | 0.930 | +0.107 | 0.749 (235°) | 0.865 (235°) | 0.923 | 4 of 72 | 0 of 72 |

### Findings of part 2

1. The 10 reference vectors raise the mean over the rotated angles by 0.10 to 0.15. The
   minimum rises from 0.70–0.78 to 0.84–0.91. Over 50° to 355°, where the query is not a
   reference image, the mean is 0.91 to 0.94.
2. The owner observation holds approximately. In each quarter k to k + 90° (k = 0°, 90°,
   180°, 270°), the curve of one vector falls to a minimum and then rises to the next
   multiple of 90°. The minimum is at k + 25° to k + 55°, not always at k + 45°.
3. The angles 0° to 45° of the reference side also cover the other quarters. The best
   reference is often the angle whose canvas has the same size as the canvas of the query.
   The canvas at 180° − θ has the size of the canvas at θ. Example: at 170°, the best
   reference is 10° to 20°, and the cosine rises from 0.80–0.87 to 0.92–0.95.
4. The multiples of 90° do not gain. At 90°, 180°, and 270°, the best reference is
   mostly 0°, so the score stays at the score of one vector (0.86 to 0.95). 180° (the
   bottle upside down) is now the weakest angle of NaFlex p256, p512, and p1024 on white.
5. Fixed 256 stays the weakest near 85° to 95° and 265° to 275° (0.86 to 0.87).
6. The rank gives no information here: it is optimistic (see the limits). A fair rank
   needs the same 10 reference vectors for each wine of the catalogue.

## Part 3: six reference sets

Source: owner message of 2026-09-29T01:44:56+0300 ("сохрани отдельно": each set has its
own folder). Script: [scripts/rotation_refsets.py](../../scripts/rotation_refsets.py).
Artifacts (not in git): `rotation-similarity-2026-09-29/refsets/`.

### Method of part 3

1. Reference sets (start–end, step, number of vectors): 0°–45°, 5°, 10 (the set of part
   2, for comparison); 0°–90°, 5°, 19; 0°–355°, 5°, 72; 0°–45°, 1°, 46; 0°–90°, 1°, 91;
   0°–359°, 1°, 360. "0° to 360°" of the owner message is 0° to 355° or 0° to 359°,
   because 360° is 0°. The reference images are on white, as in part 2.
2. The script embeds the union of the reference angles (0° to 359°, step 1°, 360 images)
   one time for each entry. Each set takes its vectors from this union.
3. Query side: the 144 images of part 1 (0° to 355°, step 5°, white and black), and 72
   extra white queries with an offset of +2.5° (2.5°, 7.5°, ..., 357.5°).
4. Why the offset: a white query at a multiple of 5° has the pixels of a reference image
   in each set that holds its angle. In the sets 0°–355°/5° and 0°–359°/1°, each white
   query gets 1.000. The offset queries show the white case between the reference angles:
   the nearest reference is 2.5° away with the step 5° and 0.5° away with the step 1°.
5. Score: the maximum cosine over the vectors of a set. No rank is computed: the rank of
   part 2 was optimistic.
6. Each set folder `refsets/refs-<start>-<end>-step<step>/` holds `results.csv`,
   `meta.json`, `vectors/<entry>.npz` (the reference vectors of the set, the three query
   sets, and the indexed vector), and four charts: `chart-by-model.png` and
   `chart-models-{white,black,white_offset}.png`. `refsets/vectors/` holds all 360
   reference vectors. `refsets/summary.csv` and `refsets/chart-summary-{mean,min}.png`
   compare the sets.
7. The 0°–45°/5° set gives the scores of part 2 within 0.0004.
8. 3,456 embeddings, 0 failures, 2.5 minutes.

### Charts of part 3

![Mean score of each reference set](rotation-similarity-2026-09-29/refsets/chart-summary-mean.png)

![Minimum score of each reference set](rotation-similarity-2026-09-29/refsets/chart-summary-min.png)

### Results of part 3

Mean cosine over the 72 black queries (0° to 355°). The column heading gives the range,
the step, and the number of vectors:

| Entry | 1 vector | 0°–45°, 5° (10) | 0°–90°, 5° (19) | 0°–355°, 5° (72) | 0°–45°, 1° (46) | 0°–90°, 1° (91) | 0°–359°, 1° (360) |
|---|---:|---:|---:|---:|---:|---:|---:|
| naflex-p256 | 0.806 | 0.918 | 0.936 | 0.972 | 0.926 | 0.941 | 0.972 |
| naflex-p512 | 0.772 | 0.918 | 0.933 | 0.968 | 0.925 | 0.940 | 0.968 |
| naflex-p1024 | 0.821 | 0.919 | 0.937 | 0.964 | 0.925 | 0.941 | 0.964 |
| 256 | 0.803 | 0.922 | 0.943 | 0.981 | 0.925 | 0.946 | 0.982 |
| 384 | 0.832 | 0.933 | 0.950 | 0.982 | 0.937 | 0.953 | 0.982 |
| 512 | 0.825 | 0.931 | 0.950 | 0.980 | 0.937 | 0.954 | 0.980 |

Mean cosine over the 72 white queries with the offset +2.5° (2.5° to 357.5°):

| Entry | 1 vector | 0°–45°, 5° (10) | 0°–90°, 5° (19) | 0°–355°, 5° (72) | 0°–45°, 1° (46) | 0°–90°, 1° (91) | 0°–359°, 1° (360) |
|---|---:|---:|---:|---:|---:|---:|---:|
| naflex-p256 | 0.829 | 0.936 | 0.947 | 0.963 | 0.947 | 0.959 | 0.984 |
| naflex-p512 | 0.794 | 0.941 | 0.946 | 0.963 | 0.950 | 0.958 | 0.981 |
| naflex-p1024 | 0.855 | 0.945 | 0.954 | 0.967 | 0.955 | 0.965 | 0.986 |
| 256 | 0.809 | 0.925 | 0.942 | 0.967 | 0.932 | 0.952 | 0.988 |
| 384 | 0.846 | 0.942 | 0.956 | 0.974 | 0.948 | 0.966 | 0.990 |
| 512 | 0.846 | 0.944 | 0.959 | 0.976 | 0.952 | 0.966 | 0.990 |

The minimum and its angle for each set, entry, and query side are in
`refsets/summary.csv`.

### Findings of part 3

1. The range matters more than the step. 72 vectors over the full circle (step 5°) give a
   higher mean than 91 vectors over 0° to 90° (step 1°): black 0.964–0.982 against
   0.940–0.954, white with offset 0.963–0.976 against 0.958–0.966.
2. Each larger range adds to the score. From 0°–45° to 0°–90°: +0.005 to +0.021. From
   0°–90° to the full circle: +0.013 to +0.038.
3. The step changes the score of the white offset queries. Over the full circle, the step
   1° gives 0.981–0.990, and the step 5° gives 0.963–0.976. A reference 2.5° away from the
   query costs 0.014 to 0.021 more than a reference 0.5° away.
4. The black background sets a limit. Over the full circle, each black query has a
   reference at its own angle, and the step 1° adds 0.001 or less (0.964–0.982).
   The remaining loss comes from the background alone. More angles cannot remove it. A
   reference on black, or a query with the background removed, can remove it. This is not
   tested.
5. Worst case over the full circle with the step 1°: black 0.934–0.971, white with offset
   0.925–0.981 (`summary.csv`).
6. The cost: each reference vector is one more item in the index. The full circle with
   the step 5° makes the index of the view `full` 72 times larger, and the search takes
   more time in proportion.
7. The query images are rotations of the reference image itself. A real photo has other
   differences, so these scores are an upper limit of the effect of rotated references.
   A fair test of the rank needs the same reference sets for each wine of the catalogue.

## Part 4: full-circle sets with the steps 3°, 8°, 9°, and 12°

Source: owner message of 2026-09-29T01:56:01+0300. Script:
[scripts/rotation_refsets.py](../../scripts/rotation_refsets.py) with `--reuse-vectors`.

### Method of part 4

1. New sets: 0°–357°, step 3° (120 vectors); 0°–352°, step 8° (45); 0°–351°, step 9°
   (40); 0°–348°, step 12° (30). Each set has its own folder in `refsets/`, as in part 3.
2. All angles of these sets are in the 360 reference vectors of part 3. The script reads
   them from `refsets/vectors/<entry>.npz` and sends no request. The query vectors are the
   vectors of part 3.
3. `refsets/summary.csv` keeps the rows of part 3 and adds the new sets.
4. In these sets, a white query without offset is informative except where its angle is a
   multiple of the step: for example, 15°, 30°, ... for the step 3°.
5. The mean of a set depends on the distances from the query angles to the reference
   grid, and these distances depend on the step in an irregular way. Example: each black
   query (a multiple of 5°) has a reference at its own angle in the step 5°, but only
   every third black query has one in the step 3°. So the mean is not monotonic in the
   step. The file `refsets/tolerance.csv` and the chart `chart-tolerance.png` give the
   score by the distance to the nearest reference angle instead. They pool all queries of
   all full-circle sets (steps 1°, 3°, 5°, 8°, 9°, 12°).

### Charts of part 4

![Full-circle sets by step](rotation-similarity-2026-09-29/refsets/chart-full-circle-steps.png)

![Score by the distance to the nearest reference angle](rotation-similarity-2026-09-29/refsets/chart-tolerance.png)

### Results of part 4

Mean cosine of the full-circle sets over the 72 black queries:

| Entry | 1 vector | 1° (360) | 3° (120) | 5° (72) | 8° (45) | 9° (40) | 12° (30) |
|---|---:|---:|---:|---:|---:|---:|---:|
| naflex-p256 | 0.806 | 0.972 | 0.959 | 0.972 | 0.946 | 0.942 | 0.941 |
| naflex-p512 | 0.772 | 0.968 | 0.955 | 0.968 | 0.945 | 0.941 | 0.940 |
| naflex-p1024 | 0.821 | 0.964 | 0.954 | 0.964 | 0.944 | 0.946 | 0.942 |
| 256 | 0.803 | 0.982 | 0.972 | 0.981 | 0.960 | 0.959 | 0.953 |
| 384 | 0.832 | 0.982 | 0.973 | 0.982 | 0.965 | 0.964 | 0.959 |
| 512 | 0.825 | 0.980 | 0.972 | 0.980 | 0.964 | 0.963 | 0.961 |

Mean cosine of the full-circle sets over the 72 white queries with the offset +2.5°:

| Entry | 1 vector | 1° (360) | 3° (120) | 5° (72) | 8° (45) | 9° (40) | 12° (30) |
|---|---:|---:|---:|---:|---:|---:|---:|
| naflex-p256 | 0.829 | 0.984 | 0.977 | 0.963 | 0.965 | 0.962 | 0.957 |
| naflex-p512 | 0.794 | 0.981 | 0.974 | 0.963 | 0.964 | 0.964 | 0.960 |
| naflex-p1024 | 0.855 | 0.986 | 0.978 | 0.967 | 0.970 | 0.966 | 0.965 |
| 256 | 0.809 | 0.988 | 0.981 | 0.967 | 0.971 | 0.966 | 0.963 |
| 384 | 0.846 | 0.990 | 0.985 | 0.974 | 0.975 | 0.974 | 0.970 |
| 512 | 0.846 | 0.990 | 0.986 | 0.976 | 0.978 | 0.975 | 0.973 |

Mean cosine by the distance to the nearest reference angle, white queries (with and
without offset). At 0°, the query is the reference image. The row "queries" gives the
number of queries of each point for one entry:

| Entry | 0° | 0.5° | 1° | 1.5° | 2° | 2.5° | 3° | 4° | 5° | 6° |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| naflex-p256 | 1.000 | 0.983 | 0.967 | 0.964 | 0.960 | 0.960 | 0.957 | 0.955 | 0.959 | 0.934 |
| naflex-p512 | 1.000 | 0.979 | 0.973 | 0.964 | 0.960 | 0.960 | 0.958 | 0.957 | 0.961 | 0.946 |
| naflex-p1024 | 1.000 | 0.980 | 0.976 | 0.971 | 0.968 | 0.965 | 0.967 | 0.965 | 0.960 | 0.960 |
| 256 | 1.000 | 0.986 | 0.979 | 0.972 | 0.964 | 0.964 | 0.960 | 0.957 | 0.955 | 0.928 |
| 384 | 1.000 | 0.989 | 0.981 | 0.977 | 0.975 | 0.970 | 0.971 | 0.967 | 0.959 | 0.960 |
| 512 | 1.000 | 0.989 | 0.982 | 0.980 | 0.977 | 0.972 | 0.972 | 0.970 | 0.961 | 0.960 |
| queries | 191 | 166 | 94 | 70 | 46 | 118 | 46 | 37 | 12 | 6 |

The same for the black queries:

TOL| Entry | 1 vector | 1° (360) | 3° (120) | 5° (72) | 8° (45) | 9° (40) | 12° (30) |
|---|---:|---:|---:|---:|---:|---:|---:|
| naflex-p256 | 0.806 | 0.972 | 0.959 | 0.972 | 0.946 | 0.942 | 0.941 |
| naflex-p512 | 0.772 | 0.968 | 0.955 | 0.968 | 0.945 | 0.941 | 0.940 |
| naflex-p1024 | 0.821 | 0.964 | 0.954 | 0.964 | 0.944 | 0.946 | 0.942 |
| 256 | 0.803 | 0.982 | 0.972 | 0.981 | 0.960 | 0.959 | 0.953 |
| 384 | 0.832 | 0.982 | 0.973 | 0.982 | 0.965 | 0.964 | 0.959 |
| 512 | 0.825 | 0.980 | 0.972 | 0.980 | 0.964 | 0.963 | 0.961 |

### Findings of part 4

1. The score falls fastest in the first degree. On white: 0.979–0.989 at 0.5°, 0.967–0.982
   at 1°, 0.960–0.977 at 2°. Past 2°, the curve is almost flat: 0.950–0.972 at 3° to 4.5°.
   The points at 5° to 6° have few queries (6 to 12), so they are less certain.
2. On black, the same shape is 0.02 to 0.03 lower: 0.964–0.982 at 0°, 0.947–0.968 at 1°,
   0.934–0.958 at 4°.
3. So a coarser grid costs little after the first degrees. 30 vectors over the full
   circle (step 12°, the query is at most 6° from a reference) give a mean of 0.940–0.961
   on black and 0.957–0.973 on white with offset. 91 vectors over 0°–90° (step 1°, part 3)
   give 0.940–0.954 and 0.958–0.966. So a third of the vectors over the full circle gives
   the same or a higher mean. The range of the angles matters more than the step, as in
   part 3.
4. Fixed 384 and fixed 512 have the highest scores at each distance on white. From 0.5°
   to 4.5°, NaFlex p1024 and fixed 512 lose the least (0.014 and 0.018), and NaFlex p256
   and fixed 256 lose the most (0.033 and 0.028).

## Side finding: one image in a request

The NaFlex p256 model gives a different vector when a request holds one image. The stored
index image, sent alone, gives the cosine 0.994173 to its own index vector. The same
image in a batch of 2, 4, 8, or 16 gives 1.000000. The other entries give 0.99981 to
0.99999 when the image is alone. The index was built in batches of 16. The matcher
(`matcher/service.py`, `matcher/siglip2.py`) and the lab runs (`pipeline/embedding_run.py`,
one view) send one image in each request. So a query vector of NaFlex p256 comes from the
path that differs. This probe used one image only. The cause on the server is not known.

## Reproduce

Run from the workbench root. The script sends 145 requests to each entry. It changes no
file outside `--out`.

```sh
python3 scripts/rotation_similarity.py --out docs/reports/rotation-similarity-2026-09-29
python3 scripts/rotation_similarity_plots.py docs/reports/rotation-similarity-2026-09-29
```

The second script reads `results.csv`, `meta.json`, and `images/`. It sends no request.

Part 2 (10 reference vectors; about 40 s, 154 images for each entry):

```sh
python3 scripts/rotation_multiref.py --out docs/reports/rotation-similarity-2026-09-29/multiref
python3 scripts/rotation_multiref.py --out docs/reports/rotation-similarity-2026-09-29/multiref --plots-only
```

Part 3 (six reference sets; about 2.5 minutes, 576 images for each entry):

```sh
python3 scripts/rotation_refsets.py --out docs/reports/rotation-similarity-2026-09-29/refsets
python3 scripts/rotation_refsets.py --out docs/reports/rotation-similarity-2026-09-29/refsets --plots-only
```

Part 4 (no request; the vectors of part 3):

```sh
python3 scripts/rotation_refsets.py --out docs/reports/rotation-similarity-2026-09-29/refsets --reuse-vectors --sets 0:359:3 0:359:8 0:359:9 0:359:12
```

Options: `--slug <wine>`, `--step <degrees>`, `--batch <images>`, `--entries <names>`.
