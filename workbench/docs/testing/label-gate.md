# Experimental label gate

Select `siglip2-p512-rot5-label-first-gated` in the Testset Run dialog.
The preset uses the local rot5 catalogue and standard label mask segmentation.
The bottle view queries only full vectors. The label view queries only label vectors.

The gate first checks the prepared label crop. A rejected crop gets no embedding.
A usable crop gets a label embedding. Select the complete label ranking when its
top cosine is at least 0.90 and its lead over the second wine is at least 0.01.
Otherwise select the complete bottle ranking. Use the selected space's cosine as
the answer score. Do not average label and bottle scores.

## Crop checks

All thresholds below are trial settings. They are not calibrated probabilities.
The optional pipeline key `label_gate` holds these values. An empty mapping uses
the same defaults. The pipeline MUST provide both `full` and `label` query views.
The label view MUST start with `segment` and target `label`. This version supports
label crop, background, and resize steps only. It refuses additional padding or DIS
steps because the direct mask mapping does not support their geometry.

| Signal | Trial threshold | Measurement |
| --- | --- | --- |
| Detector score | At least 0.70 | Score of the selected main label |
| Native detail | Both sides at least 128 pixels | Main-label mask bounds in the source photo |
| Input detail | Both sides at least 128 pixels | Main-label mask bounds in the prepared input |
| Purity | At least 0.80 | Share of nonwhite input pixels inside selected label masks |
| Sharpness | At least 80 | Masked Laplacian variance at label width 256 |
| Package overlap | At least 0.80 when available | Share of the main-label rectangle inside the selected package rectangle |

For purity, a pixel is nonwhite when `min(R, G, B) < 245`.
White padding does not reduce purity. Masks include the main label and accepted body
labels from `alternatives.body_labels`. The mask is a detector estimate, not ground truth.
For sharpness, erode the main-label mask by three pixels to exclude its outline.
Measure Laplacian variance inside that mask after resizing the label bounds to width 256.
The gate checks native size separately so an enlarged small label cannot pass on size alone.

Record contact with the source frame as `source_frame_edges`.
Do not reject frame contact alone: a close-up of a complete label can touch the frame.
This version has no direct glare, occlusion, text-readability, or label-completeness check.
High detector confidence does not prove that a crop contains useful label detail.

## Trace and fallback

The matching details show `Label crop quality · Accepted` or
`Label crop quality · Rejected` in the step heading. Expand this step to see each
measurement, its recorded threshold, PASS/FAIL, and readable rejection reasons.
Missing measurements show `not measured`. `Select retrieval space` names the
selected space and shows label similarity and margin against their thresholds.
Crop acceptance does not mean that the label ranking was selected.
The trace stores measurements, rejection reasons, thresholds, label top cosine,
label margin, selected space, and disagreement between the two winning identities.
The label view is skipped when its quality fails. No skipped view appears as an
embedding input. The label cut remains available as segmentation evidence.
If label detection is unavailable, this preset can still use the bottle view.
If fewer than two label identities exist, the margin cannot be checked and the gate
uses the bottle view. `label_gate` cannot be combined with a `competitor` wrapper.

Existing presets keep their previous score rule. This preset has no barcode, VLM
rerank, or competitor wrapper.

## Label mask segmentation

Label selection v2 first keeps labels whose boxes are at least 50% inside the main
detected bottle (the largest bottle box). It then applies the bottle-shape exclusion
within that group. If every on-bottle label resembles the bottle, it retains the
largest on-bottle label: a close-up can contain a genuine label nearly as large as
the bottle. Shelf price tags and labels on neighbouring bottles cannot supply the
fallback. With no detected bottle, the largest-label rule remains available. Explicit
catalogue label close-ups keep their existing no-bottle-test rule.

New embedding runs record `sam3.label_selection_version: 2`. Historical runs without
this value retain the previous global label selection when reconstructed. The visual
input cache includes the selection version; live comparison preparation also includes
the selection code hash. Automatic label derivatives carry the new selection settings
so subsequent processing cannot reuse an old automatic cut as current. Manual cuts
remain current.

`alternatives.label_cut_of` keeps the masks of the main label
and accepted body labels. Combine the masks at the source resolution. Apply the
same edge refinement as a single label. Preserve the source alpha channel.
Keep the relative positions of the labels. The glass between the labels becomes
transparent. The embedding background step replaces transparent pixels with white.
A single label keeps the same image bytes as the existing preparation.

Mask union is the standard preparation for new query inputs and automatic catalogue
label derivatives. The versioned rule is `label mask union v1`. Old rectangular
derivatives need a refresh. Manual label cuts stay unchanged. The local rot5 index
uses new vectors for the changed full-photo label inputs. Other local indexes need
the same refresh before they can use these changed reference inputs. Unchanged
single-label derivatives keep their vectors.

New runs record `sam3.label_mask_union: true`. Historical runs without this flag
use `mask_union=False` when their inputs and segmentation steps are displayed.
The visual-input cache includes the flag. A historical crop cannot reuse a cached
mask-union preview. Historical results and recorded measurements stay unchanged.

The attached 2016 Victor Dravigny example has two accepted labels. Its measured
purity rises from 0.373856 to 0.906678. The saved 2020 query rises from 0.370230 to
0.914013. The Extra Brut reference rises from 0.379586 to 0.899783.
The correct Brut reference has one accepted label. Its input bytes stay unchanged.
All four previews use cached SAM3 masks. They send no request to a model service.
These results measure image preparation. They do not measure recognition accuracy.
After masking, purity mainly checks preparation against the detector mask.
It cannot prove that SAM3 selected the correct label.

## Validation

The unit tests use synthetic masks and images. They check white padding, unrelated
glass, native and input detail, blur, package association, malformed masks, missing
label detection, confidence routing, and exact preservation of bottle scores.
A competing-identity test makes the mean prefer one wine while the gate selects
another wine from the label ranking. Runner tests check which bytes reach the
model. Step-viewer tests check the recorded explanation and skipped-input display.
These tests send no data to configured model services.

The original Victor Dravigny query was replayed locally from its two saved vectors.
Its old rectangular label crop has about 37 percent purity and fails the 80 percent check.
The bottle ranking therefore stays at truth rank 6. Even with a passed crop check,
the saved label ranking has a lead of about 0.0011 and fails the 0.01 margin check.
A prepared tight front-label crop passes the local crop checks. Its retrieval rank
is unmeasured because its embedding has not been requested.

The later 2022 Brut reference preview matches the owner's attachment pixel-for-pixel
before the refresh. Its mask-union purity is 0.919023, compared with 0.353667 for
the old rectangle. Refresh the stored label derivative and its local label vector
together. Inference computes vectors through the configured SigLIP2 endpoint.
The endpoint model, configuration, and deployment stay unchanged.

Before selecting production thresholds, measure label and bottle decisions on a
separate labelled validation set. Compare routing precision, coverage, and errors
against the bottle baseline. Keep capture groups separate during calibration and
final evaluation. This one-query replay does not establish an accuracy gain.
