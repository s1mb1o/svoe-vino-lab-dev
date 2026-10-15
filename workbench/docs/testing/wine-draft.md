# Add wine recognition and duplicate checks

The Add wine dialog reads a staged Main image with the configured `image_description`
VLM. Recognition uses a 45 second request timeout. One recognition request can run at
a time. A busy service returns HTTP 429. The current image retries with bounded
backoff. Cancellation stops pending retries. The user can cancel recognition or enter
fields after a failure. Recognition does not create catalogue rows or image files.

The form preserves user values and copied values. A new image clears only unchanged
values from the previous recognition. A response cannot fill a field that the user
changed during that request. Closing the dialog or replacing the image invalidates
outstanding responses. Unknown facts remain empty. An invalid or conflicting model year becomes empty.
Other recognized fields remain available. Review recognized facts before Save.

The Similar wines column searches every catalogue state. A candidate popup shows the
existing card and its state. Close returns to the draft. Copy values fills empty text
and select fields. When Year is empty, Copy values first uses a year in the draft Name.
Otherwise, Copy values uses the candidate year. It
preserves the staged image and the slug. The user can change the year after copying.

## Identity decisions

| Attribute | Equal | Conflict | Unknown |
|---|---|---|---|
| Name | Compare normalized identifying text. | Show only similar candidates. | Do not assert identity. |
| Grapes | Compare complete canonical sets. Preserve unmapped varieties. | Show only similar candidates. | Do not assert identity. |
| Sweetness | Compare one known canonical value. | Show only similar candidates. | Do not assert identity. |
| Producer, colour, wine category | Permit identity. | Show only similar candidates. | Do not veto otherwise established identity. |
| Year | Warn about an exact duplicate. Both absent years are equal. | Ask about a new vintage card. | Warn when one year is absent. |

Name comparison removes recognized colour and sweetness descriptors. It also removes
harvest years and common wine words. Names keep other product terms. A `generic` or
`no_year` tag prevents a number in that title from becoming a harvest year. Distinct
year tags or sweetness tags keep identity ambiguous. A year in the draft name that
conflicts with the Year control produces a validation error.

Canonical grapes use the existing attribute vocabulary. Unknown grape text remains in
the comparison. Case, accents, punctuation, and legal producer forms do not create
identity conflicts. The comparison does not translate proper wine names.

Similarity requires equal normalized names, or shared name tokens with a name ratio
of at least 0.62 or draft token coverage of at least 0.8. Candidates use a deterministic
score and slug order. The ribbon shows at most 16 candidates. The warning list and its
acknowledgement include every identity conflict, including candidates beyond that
limit. Short partial names can find longer catalogue titles. Partial names cannot
establish exact identity.

## Save and persistence

Save checks the current catalogue again. Exact duplicates require explicit
confirmation. Different years require explicit confirmation for a new vintage card.
One absent year has a separate confirmation. A failed check keeps the draft open.
The form blocks repeated saves until the request completes. The acknowledgement binds
the draft fields and every identity conflict. The create transaction checks again.
A new conflict invalidates the acknowledgement and returns HTTP 409.

Automatic slugs include the selected year when the name does not contain that year.
An occupied automatic slug receives a numeric suffix. A typed slug stays unchanged.
The server remains authoritative for slug uniqueness.

The manual and Atlas create paths accept optional `sweetness` and `vintage` fields.
The transaction stores `sweetness:<canonical>` and `vintage:YYYY` in `wine_tag`.
These tags are visible catalogue tags. No schema migration is required. Atlas form
values control creation. Draft checks also apply to Atlas creation from this dialog.
The Atlas flow does not start bottle recognition without a staged Main image.

## Verification

The tests use temporary databases and image roots. HTTP tests bind an ephemeral
loopback port. Model transports are mocked. The controller tests run actual JavaScript
with delayed responses and browser event fixtures. Manual browser checks cover the
live dialog, image recognition, popup, empty-only copy, focus, and narrow layouts.
A browser smoke check MUST NOT create a test card in the live catalogue.
