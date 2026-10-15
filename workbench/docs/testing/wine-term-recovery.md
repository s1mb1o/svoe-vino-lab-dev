# Wine term recovery experiment

`pipeline/wine_term_recovery.py` is an opt-in prototype. The live matcher does not
import this module. The prototype reads the shared wine dictionary. It does not
define a second dictionary. It expands the current finite language patterns into
273 aliases for 47 canonical identities. Unsupported pattern syntax MUST fail.

The experiment compares the existing verifier, whitespace recovery, guarded
Damerau-Levenshtein recovery, and guarded Levenshtein recovery. Both fuzzy variants
use the same thresholds. The vocabulary search does not depend on the shortlist.

## Recovery policy

- Exact aliases and vocabulary-bounded visual lookalikes remain first-class evidence.
- Adjacent fragments MAY form one term. A cross-word join requires a shared line ID
  or compatible geometry. A string from one OCR line MAY contain internal spaces.
- Commas, semicolons, slashes, and line breaks prevent fragment joins.
- Short names of four or fewer letters require exact letters. Longer names permit
  one edit. Names of at least 12 letters permit two edits. Fuzzy similarity MUST
  reach 0.85. The margin over another canonical identity MUST reach 0.10.
- Length and letter-count bounds exclude aliases whose similarity cannot reach
  0.75. If no runner reaches 0.75, the reported margin is a lower bound.
- An exact term MUST NOT absorb unrelated letters. A compound MAY recover its
  damaged qualifier before a shorter component is accepted.
- Known sugar qualifiers MUST NOT change identity. For example, `semi sec` MUST
  NOT become `demi-sec`. An uncertain qualifier leaves the sugar field unknown.
- Verification applies new recovery only at the configured minimum OCR confidence.
  A joined term keeps the minimum confidence of its source words. Raw words,
  confidence, and geometry remain unchanged.
- Fuzzy evidence MAY support a match. Fuzzy evidence MUST NOT create a new
  contradiction. An independent exact contradiction remains effective.
- Broad grape families remain broad. A grape-name colour does not establish wine
  colour. Unknown candidate metadata remains neutral. Candidate scores stay intact.

The `recover`, `recover_words`, and `verify` functions return correction evidence.
This evidence includes the canonical identity, alias, method, distance, similarity,
runner identity, source word indexes, original confidence, and algorithm hashes.

## Frozen replay

`scripts/replay_wine_term_recovery.py` reads the frozen query manifest, catalogue,
and raw OCR cache. It checks cache and catalogue identities before the replay. It
checks source hashes again after the replay. Each output directory contains source
hashes, code snapshots, per-query results, and aggregate metrics.

The runner uses the original verifier for the exact baseline. It caches pure
parsing functions inside its own process. It does not change the live process.
Missing labels and reader failures retain the visual order. The runner does not
run inference, modify annotations, or change catalogue data.

The result has 2,553 queries per reader. It includes 2,007 positive queries and 546
named-negative queries. A named-negative query excludes one wine. Another predicted
wine is not a proven correct identification. Producer groups remain in one
descriptive partition. The cohort has prior development use. Neither partition is
new held-out evidence. Development examples informed the recovery guards.

Real OCR spans do not have independently transcribed truth. Correction precision
therefore remains `null`. Ranking fixes, ranking regressions, and new contradictions
against accepted positive truths can be measured. The all-shortlist-conflict count
is a diagnostic that excludes fields with fuzzy corrections. It does not apply a
new abstention policy. The existing catalogue-completeness assumption remains in
use; full parser coverage does not prove that a source gives a complete blend.

The saved Tesseract cache has no line geometry. Its separate words therefore cannot
join across OCR items. Future reader output SHOULD preserve line IDs and boxes.

Run the commands in [COMMANDS.md](../../COMMANDS.md), under Wine term recovery
experiment. Use a new output directory when code or input hashes change. An
existing directory with different identities MUST reject the replay.
