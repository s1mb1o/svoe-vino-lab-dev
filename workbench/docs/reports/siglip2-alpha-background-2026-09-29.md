# The alpha channel and the background fill of the SigLIP 2 models, 2026-09-29

Source: owner message of 2026-09-29T11:12:54+0300. The ResearchLog entry "the SigLIP 2 models
of the gx10 gateway" (2026-09-25) measured the alpha channel with `dinov3-vitb16` alone and
states "The SigLIP 2 models were not measured". No report explained the choice of the white
background. This report measures the SigLIP 2 entries and states what the choice of white
rests on. Session: drink-atlas-workspace-c4. Script:
[scripts/alpha_background_probe.py](../../scripts/alpha_background_probe.py). Artifacts (not
in git): `docs/reports/siglip2-alpha-background-2026-09-29/` (`synthetic.csv`,
`catalogue.csv`, `results/<entry>.json`, `examples/`, `fills.png`, `synthetic.png`).

## Where the lab and the matcher fill the background

- The view `full` of the index: `segment`, `remove_background`, `white_background`,
  `resize` (variant C of plan 10). The config check refuses `remove_background` without a
  later `white_background` (`embeddings.ALPHA_ERROR`), and each model input with a
  transparent pixel is an item error (`embeddings.TRANSPARENT_ERROR`).
- The query pipelines `as-is`, `crop`, and `crop-seg` have the step `white_background`.
- The matcher: `siglip2.model_input` composites an RGBA photo on white;
  `main_scene.select_main_package` (`hand_selection: true`) composites the masked crop on
  white.
- So no path of the lab or of the matcher sends an RGBA image to the gateway today.
- The reason for white in plan 10 and in the owner answers: "A transparent area becomes
  white, as on the catalogue images." No measurement of another fill exists.

## Catalogue facts

- 1,926 of the 2,270 full catalogue images (85 %) have transparent pixels (1,157 with a
  mostly transparent border). 344 are opaque: the border is white (mean ≥ 245) for 143,
  light (200–245) for 105, and darker for 96.
- The SAM3 cut of a package (`data/catalog/cuts/`, RGBA) keeps colour under its transparent
  pixels. That colour differs between the cuts: the pixels of the original photo or a mix
  for 1,590 cuts, white for 362, black for 316; 2 cuts have no transparent pixel.

## Method

Entries: the 8 SigLIP 2 entries of `config.yaml` (NaFlex p256, p512, p1024; fixed 256,
384, 512; patch14-384; the timm `naflexvit` p256) and `gx10-dinov3-vitb16` as the control of
the 2026-09-25 measurement. Gateway: llama-swap 18081. No request holds one image alone.

- Part A, synthetic: one 256 × 512 RGBA image, a bottle with a label on transparent
  pixels. It is sent as RGBA with red, blue, and white under the transparent pixels, as the
  same images after Pillow `convert("RGB")` (the alpha channel dropped, the hidden colour
  visible), and composited on white.
- Part B, catalogue: 40 current `full` items of each index, spread over the sha256 order.
  The SAM3 cut is composited on white, black, grey 128, red, and blue, and sent raw as RGBA
  and as its RGB form. Every image gets the scale of the `resize` step of the white image.
  The white image equals the stored index PNG pixel for pixel for 40 of 40 items of each
  entry.

![The cut on each fill](siglip2-alpha-background-2026-09-29/fills.png)

## Results

Part A (cosine between two vectors of the synthetic image):

| Entry | RGBA red vs RGB red | RGBA blue vs RGB blue | red vs blue under alpha 0 | RGBA red vs white composite |
|---|---:|---:|---:|---:|
| NaFlex p256 | 1.0000 | 1.0000 | 0.9736 | 0.9267 |
| NaFlex p512 | 1.0000 | 1.0000 | 0.9864 | 0.9644 |
| NaFlex p1024 | 1.0000 | 1.0000 | 0.9666 | 0.9593 |
| fixed 256 | 1.0000 | 1.0000 | 0.9701 | 0.9537 |
| fixed 384 | 1.0000 | 1.0000 | 0.9799 | 0.9179 |
| fixed 512 | 1.0000 | 1.0000 | 0.9818 | 0.9551 |
| patch14-384 | 1.0000 | 1.0000 | 0.9717 | 0.9395 |
| naflexvit p256 (timm) | 1.0000 | 1.0000 | 0.9519 | 0.9495 |
| DINOv3 ViT-B/16 (control) | 1.0000 | 1.0000 | 0.9862 | 0.9791 |

Part B (40 catalogue cuts for each entry). The first column is the cosine of the fresh white
image to the stored index vector. The other columns are the mean (minimum) cosine of each
fill to the white image. The last column is the minimum cosine of a raw RGBA cut to its RGB
form:

| Entry | white vs index | black | grey 128 | red | blue | raw RGBA | raw RGBA vs its RGB |
|---|---:|---:|---:|---:|---:|---:|---:|
| NaFlex p256 | 0.9999 | 0.9726 (0.9487) | 0.9705 (0.9523) | 0.9651 (0.9415) | 0.9591 (0.9394) | 0.9586 (0.9233) | 1.000000 |
| NaFlex p512 | 1.0000 | 0.9741 (0.9441) | 0.9692 (0.9453) | 0.9660 (0.9309) | 0.9612 (0.9280) | 0.9615 (0.9196) | 1.000000 |
| NaFlex p1024 | 1.0000 | 0.9809 (0.9568) | 0.9750 (0.9520) | 0.9725 (0.9389) | 0.9668 (0.9183) | 0.9691 (0.9353) | 1.000000 |
| fixed 256 | 0.9998 | 0.9752 (0.9462) | 0.9685 (0.9286) | 0.9626 (0.9153) | 0.9516 (0.9103) | 0.9585 (0.9282) | 1.000000 |
| fixed 384 | 1.0000 | 0.9778 (0.9559) | 0.9757 (0.9383) | 0.9678 (0.9388) | 0.9568 (0.9105) | 0.9608 (0.9040) | 1.000000 |
| fixed 512 | 1.0000 | 0.9799 (0.9603) | 0.9789 (0.9633) | 0.9662 (0.9393) | 0.9555 (0.9198) | 0.9625 (0.9235) | 1.000000 |
| patch14-384 | 1.0000 | 0.9791 (0.9612) | 0.9768 (0.9451) | 0.9646 (0.9279) | 0.9497 (0.9060) | 0.9624 (0.9125) | 1.000000 |
| naflexvit p256 (timm) | 1.0000 | 0.9753 (0.9156) | 0.9774 (0.9591) | 0.9691 (0.9367) | 0.9631 (0.9420) | 0.9679 (0.9179) | 1.000000 |
| DINOv3 ViT-B/16 (control) | 1.0000 | 0.9791 (0.9514) | 0.9894 (0.9803) | 0.9832 (0.9731) | 0.9837 (0.9714) | 0.9581 (0.8398) | 1.000000 |

The wine of each item stays at rank 1 of the index for 39 or 40 of 40 items with every fill
and every entry.

## Findings

1. The gateway drops the alpha channel for each SigLIP 2 entry too. An RGBA image and its
   RGB form give the cosine 1.000000 (synthetic, and the minimum over 40 real cuts). The
   gateway does not composite on white: RGBA with red under the transparent pixels and the
   white composite give 0.918–0.964.
2. The SigLIP 2 models see the colour under a transparent pixel. Red and blue under the same
   transparent area give 0.952–0.986. The DINOv3 control gives 0.986 (the 2026-09-25 value
   0.975 is from another test image; the script of that test is not kept).
3. On real cuts, a fill other than white moves the vector by a mean cosine of 0.95–0.98
   (minimum 0.906). SigLIP 2 is more sensitive to a saturated fill than DINOv3 (red and
   blue: 0.950–0.973 against 0.983–0.984). For SigLIP 2, black and grey are the fills
   nearest to white; red and blue are the farthest.
4. A raw RGBA cut sent without `white_background` shows the model its hidden pixels: a mean
   cosine of 0.959–0.969 to the white image, minimum 0.904. The hidden colour differs from
   cut to cut in the catalogue (photo pixels, white, black), so an index without a fixed
   fill mixes backgrounds. The step `white_background` and the transparency check of the
   lab are necessary for SigLIP 2 too, and the matcher composite on white is necessary.
5. The choice of white itself rests on a convention, not on a measurement: plan 10 chose
   "on white, as on the catalogue images". Of the 344 opaque originals, 248 have a white or
   light border. This probe measures the cost of a fill that differs from the index fill
   (0.02–0.05 of cosine), not which fill gives the best retrieval. The rotation report
   ([rotation-similarity-2026-09-29.md](rotation-similarity-2026-09-29.md), part 1) gives the
   same cost for a black query against a white index at 0°: 0.017–0.032.
6. The self-retrieval rank does not separate the fills: the same image is in the index, so
   it stays at rank 1. A fill decision needs real photos.

## Limits and next step

- 40 cuts for each entry, one synthetic image. The cosine values are stable over the 9
  entries, but the minimum values depend on the sample.
- A retrieval test of the fill colour needs an index for each fill and query photos with the
  same fill: for example `…-naflex-p512` with black and grey 128 (2 × 2,270 index images)
  and the `crop-seg` query with the same fill on `my` (2 × 2,226 photos). Estimate: about
  9,000 embeddings, about 10 minutes of gateway time, and a fill option for the step
  `white_background` or a separate script. Not done.

## Reproduce

Run from the workbench root. The script calls the gx10 gateway; it changes no index.

```sh
python3 scripts/alpha_background_probe.py --samples 40
python3 scripts/alpha_background_probe.py --summary-only
```
