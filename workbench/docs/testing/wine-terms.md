# Shared wine term normalization

`pipeline/wine_terms.json` is the shared grape and sugar dictionary for label
Tesseract, label PaddleOCR, local comparison variants and legacy competitor OCR
actions. `pipeline/wine_terms.py` performs normalization; OCR workers only produce
raw text, confidence and geometry. New readers should call the shared verifier or
normalizer rather than create their own spelling dictionary.

Each term defines its stable attribute `id`, readable `canonical` spelling,
language/morphology `pattern` and explicitly reviewed `ocr_aliases`. The initial
dictionary contains 36 grape terms and 11 sugar classes, including broad grape
families and Müller-Thurgau. It is a vocabulary, not a complete catalogue.

| Recognized text | Canonical text | Attribute |
| --- | --- | --- |
| MYCKАТ / MYCKAT / МYСКАТ | мускат | muscat |
| Са8иньо бланк / Sauvignon Blanc | совиньон-блан | sauvignon_blanc |
| Каберне Савиньон / Cabernet Sauvignon | каберне-совиньон | cabernet_sauvignon |
| Müller-Thurgau / Мюллер Тургау | мюллер-тургау | muller_thurgau |
| БPЮT / BRUT | брют | brut |
| ЭКСТРА БPЮT / EXTRA BRUT | экстра-брют | extra_brut |
| ПОЛYСЛАДК0Е / semi sweet | полусладкое | semi_sweet |
| полу сухое / semi dry | полусухое | semi_dry |
| DEMI-SEC | деми-сек | demi_sec |
| EXTRA DRY | экстра-драй | extra_dry |

Normalization handles case, separators and Latin accents. Visual Latin/Cyrillic
lookalikes and `0`/`8` substitutions apply only when a complete token span matches
a dictionary term. Longer phrases win over components. Unknown words and numeric
suffixes remain unknown; there is no unrestricted fuzzy spelling correction.
Dates and numbers are retained but do not verify wine identity.

Distinct sugar classes remain distinct. In particular, demi-sec and extra dry are
not translated into Russian still-wine sugar classes. Broad Cabernet, Sauvignon
or Pinot evidence never invents a specific variety. Grape colours do not establish
wine colour. Normalization does not certify that an observed partial blend is an
exact product match.

Raw OCR caches remain keyed by their existing reader/image identity and are never
rewritten with corrected text. The verifier normalizes both the complete read and
the confidence-filtered read, preserving uncertain qualifiers and contradictory
fields. Corrections never raise confidence. Missing catalogue metadata stays neutral
when reordering: a more completely described neighbour cannot displace a compatible
visual winner solely through additional metadata. Explicit contradictions can move
candidates down, and a read named product line remains positive evidence.
Candidate cosine scores stay intact.

Run metadata and text evidence include dictionary and algorithm SHA-256 identities.
Matching details show normalized text and raw-to-canonical corrections with the
original confidence. Historical saved results keep their recorded evidence. After
editing the dictionary, restart the lab to load the new identity; future OCR
verification applies it to cached raw words without new image/model inference.

## Verification

Run the offline commands in [COMMANDS.md](../../COMMANDS.md), under Shared OCR wine
term normalization. Tests cover both readers' raw-cache reuse, owner examples,
mixed scripts, multilingual aliases, compound and ambiguous terms, low-confidence
qualifiers, bounded correction, legacy OCR actions, ranking without cosine changes,
and visible correction evidence in matching details. Matching-detail fixtures use
temporary loopback fake services; no real image is submitted.

The separate internal cached replay compares the old and new verifier on the same
saved bottle shortlists and OCR evidence. It reads catalogue metadata and writes
only derived evidence; it is not a new recognition run or held-out accuracy test.
