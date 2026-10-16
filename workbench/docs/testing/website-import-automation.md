# Website import automation

GitHub issue: https://github.com/s1mb1o/svoe-vino-lab-dev/issues/7.

## Entry points

The Dataset Website import dialog has three operations.

- Compare only prepares a report without catalogue writes.
- Check and update adds valid new wines and applies approved image improvements.
- Check and apply safe updates processes a saved report and writes safe updates. A stale snapshot requires a new comparison.

An incomplete new wine remains a warning. Other valid new wines can be added.
An inconsistent source list still stops the comparison. A partial list cannot establish absence.
The exact slug `shmelev_shmeleva_risling` is exempt from missing-source removal.
The exemption also applies when an older prepared report contains that removal.

## Image decision

A changed URL or checksum does not establish an improvement.
SAM3 supplies package and label boxes. Detector confidence MUST be at least 0.65.
The boxes are converted from detector pixels to upright source pixels.
Multiple packages, missing labels, or invalid boxes require manual review.
The reviewer keeps native crop pixels. It does not enlarge the crop.
Each crop axis MUST increase by at least 5 percent. Each crop area MUST increase by at least 15 percent.
Both package and label crops MUST pass these limits.
A gain above 4 times in either crop axis requires manual review.
This conservative upper bound is not a calibrated detector of interpolation.

The first VLM request reads the new package without catalogue metadata.
The second request compares old/new package crops and old/new label crops.
It receives the independent reading and expected catalogue data as data.
Automatic approval requires a positive identity decision and positive required-field decisions.
Missing independent identity fields cannot be supplied from expected metadata.
An independent grape, colour, or vintage contradiction blocks approval.

Readability and sharpness cannot be worse or uncertain. At least one MUST improve.
Artifacts, incomplete packaging, or an uncertain enlargement judgement block approval.
A near-identical enlargement also blocks approval. The mean RGB difference threshold is 1/255.
That check uses a bounded comparison image and does not change the stored crop.
These are conservative model and pixel checks. They do not prove physical capture resolution.
An uncertain case requires manual review.

Inputs above 64 megapixels require manual review. Model requests use the existing configured input limit.
Source hashes and a metadata hash bind each decision. A changed catalogue snapshot blocks a stale write.
The previous Main image remains an additional full-front photo. Its original file and checksum stay unchanged.
Existing additional-photo controls can make it Main again.

## Manual decisions

DATABASE records the existing persistent refusal while the source value stays equal.
WEBSITE applies the selected source value. Bulk WEBSITE does not select image replacements.
Do nothing sends `skip`. It does not change the field, image, refusal, or source acknowledgement.
Unselected and skipped image warnings remain in the result. The next comparison can show them again.
Other selected changes can still be applied.

## Verification

The isolated tests use temporary databases and fake model services.
They check native coordinate scaling, padding, enlargement, wrong-wine warnings,
model failure, positive automatic writes, retained originals, idempotence, stale reports,
protected absence, explicit deferral, HTML escaping, and bulk-choice safety.
Use COMMANDS.md for executable commands.

A bounded live service check MAY use the public Muscat/Merlot example.
Keep its model results separate from deterministic fixtures. Do not apply the result to the live catalogue.
Preserve source bytes and timestamps.

## Review safeguards

Independent product and producer names must match after explicit term normalization
and deterministic transliteration. Unknown names are not fuzzy matches.
An explicit mismatch in any model field blocks an automatic replacement.
A stored manual patch requires manual review of the new Main image and the patch together.
A possible source slug rename remains a manual addition.
An existing image hash or an equal product/producer name also requires manual review.
These duplicate checks include Removed wines, other additions in the batch,
and the candidate images of existing wine conflicts. Automatic updates do not duplicate these entries.
Source-image warnings prevent source-time acknowledgement for that wine.

The post-write snapshot is computed inside the write transaction before COMMIT.
A later manual edit cannot be absorbed into the remaining prepared report.
The snapshot includes wine tags and manual patch identities.
Multiple prior Main images can remain linked because the photo primary key includes the image hash.
A failed automatic write has a visible failure state. Passing checks alone does not mean that a replacement was applied.
Compare again and New compare remain read-only operations.

A crash after the database commit can leave a stale prepared report.
The next action fails closed. Use Compare again to create a current report.
