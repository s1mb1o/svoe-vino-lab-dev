# Main-label comparison and variant text

The opt-in presets `siglip2-p512-main-label-seg`, `siglip2-p512-main-label-text`,
`siglip2-p512-main-label-paddleocr`, and `siglip2-p512-main-label-gated` select the largest accepted SAM3 label mask alone.
Other labels, including a separate shoulder emblem, are excluded from this input.
The alpha mask removes glass around the label before a white background is applied.
Queries and full-image references use the same selection and preparation functions.

The separate supplementary directory is
`data/catalog/embeddings/gx10-siglip2-so400m-patch16-naflex-p512-rot5-main-label/`.
It stores label vectors only. Standard bottle and label indexes and catalogue
derivatives remain unchanged. Each supplementary record stores the original standard
embedding hash and its new prepared-input hash. A missing or changed reference makes
the backend refuse the stale supplement and request a rebuild.

The prepare step reads cached SAM3 detections only. Legacy single-mask references
and manual cuts already have an isolated label and are reused. Label close-up
references preserve their existing no-preprocessing contract. Only inputs whose
pixels change are submitted for new embeddings. Prepared files have timestamps
before the cutoff required by `internal/AGENTS.md`.

Preparation and inference are separate CLI operations: `main_label_match.py
--prepare` performs local preparation; `--build` sends the changed inputs to the
configured inference endpoint and publishes the separate local index. It never
changes a remote service. Run these from the workbench root using the embedding
Python environment and the existing config.

The `-seg` preset measures visual main-label retrieval alone. The `-text` preset
also runs local Tesseract with `rus+eng`. It recognizes explicit sugar, grape,
wine-colour and product-line terms with confidence at least 70. It distinguishes
brut from extra brut and semi-sweet from sweet. An uncertain qualifier invalidates
its field alone. Unreadable text, no supported compatible candidate, or reader
failure preserves the visual order.

Text verification operates inside a ten-candidate shortlist and never introduces
a wine. It uses fields that differ among shortlisted candidates. Brand names and
dates provide no variant evidence. Reliable contradictions rank after compatible
and unknown candidates. Missing catalogue metadata does not penalize a visual
winner; compatible and unknown candidates retain visual order. A read product-line
term can promote its explicitly named candidate. A contradiction in one field takes
precedence over matches in other fields. Original cosine scores stay unchanged. Scores are therefore not descending
after a text reorder. These attribute checks do not establish complete wine
identity. Matching details show the read attributes, active fields, each candidate's
expected attributes and field-level match, conflict, unknown or unused status.

Russian, English and common transliterated names share explicit aliases through
the engine-independent dictionary in
`pipeline/wine_terms.json`; see [shared wine term normalization](wine-terms.md).
Raw OCR lines, confidence and polygons stay unchanged, and matching details show
the normalized text and corrections with their original confidence.
Accents in `Rosé` and `Réserve` are normalized. An explicit catalogue-name sugar term
precedes a legacy slug's broad sugar suffix. Ambiguity within the name remains
unknown. Broad grape reads, such as Cabernet, do not
choose between Cabernet Franc and Cabernet Sauvignon. A partial grape read can
match a listed blend. A missing grape establishes a contradiction only when the
catalogue grape list is complete and fully understood. An incomplete grape list
or a grape inferred only from the wine name remains insufficient for that claim.
Grape colours, such as Muscat White and Traminer Rose, do not establish wine colour.
Descriptive colour fields, such as golden or ruby, are not categorical wine colours.

Product-line aliases currently include Reserve, Grand Reserve, Kosher and
Collection. A read product-line term can support a named candidate. An absent term
in a label or catalogue name remains unknown. It does not prove that a wine is
unreserved or non-kosher. Common product terms that occur in all shortlisted
names do not distinguish variants. French `demi-sec` and `extra dry` remain
separate explicit classes. They are not translated into Russian still-wine sugar
classes. See the official [Champagne dosage terms](https://www.champagne.fr/en/about-champagne/how-champagne-is-made/dosage).

The `-paddleocr` preset replaces Tesseract with local PaddleOCR 3.7.0. It uses
PP-OCRv5 mobile detection and the East Slavic recognizer
`eslav_PP-OCRv5_mobile_rec`, which supports Russian and English. It keeps the
same ten-candidate window and trial 70/100 confidence threshold. PaddleOCR scores
belong to recognized lines and are multiplied by 100; they are not calibrated
against Tesseract word confidence or retrieval cosines. Complete recognized lines,
polygons, engine/model identity, original visual ranks, and the resulting order
are recorded in matching details. The text step shows the reordered answer and
its attribute match/conflict status while preserving visual scores.

PaddleOCR runs in the separate Python 3.12 environment
`work/main-label-paddle/venv/`, with package pins in `requirements-paddleocr.txt`.
The lab interpreter does not import PaddlePaddle. Public weights are installed
locally under `work/main-label-paddle/models/`. The `label_ocr.py` worker requires
these local model directories for normal inference; only explicit bootstrap mode
may download weights. Model hosting is never used for image inference. OCR
results use a separate cache keyed by image content, model identity, package
versions, and reader schema. Missing models, invalid output, or reader failure
preserves the visual order and records the failure.

The official [PaddleOCR model documentation](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/OCR.html)
describes the East Slavic model and recognized-line score fields. The two local
pilot results are recorded under the internal evidence directory; they do not
establish general catalogue accuracy.

The `-gated` preset retains the existing trial crop-quality and confidence gate.
It selects the complete main-label ranking when the gate passes, otherwise the
complete bottle ranking. It does not average their scores. Usable label text can
then verify variants inside the selected shortlist. A poor-quality label has no
text input. Trial thresholds need broader calibration before a default change.

Historical runs lacking `sam3.label_focus: main` reconstruct their original
preparation. New run details record the selected rule, prepared-input hash,
supplementary reference images, and text evidence. Candidate-image details also read
each view from its recorded index, preserving standard bottle previews while showing
the exact main-label reference PNGs.

## Verification

The synthetic main-label and variant-attribute tests check separated masks,
confidence filtering, compound sugar and grape terms, broad grape families, blends,
colour ambiguity, product-line presence, multiple-field contradictions, unchanged
cosine values, stable ties, absent text, and stale reference rejection.
Existing runner, pipeline, gate, and matching-detail tests
check that the standard paths remain unchanged. Embedding-run command tests use
only a fake loopback gateway. Live model calls are a separate, explicitly approved
experiment and their results belong in the internal evidence directory.
