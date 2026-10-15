# Dataset attribute comparison

The comparison reads catalogue values and independent printed image evidence.
The patch is the active image when present. Main evidence stays separate.
A missing value does not deny a claim. Unknown and stale evidence cannot establish a conflict.
Sweetness comparisons use beverage class and conservative overlapping ranges.
A partial grape list cannot establish a complete blend. Reserve tiers keep qualifiers.
Barrel claims retain explicit duration and oak type. Label artwork does not establish
beverage colour, barrel ageing, or certification.

The SQLite migration adds immutable observations, persistent jobs, and queue settings.
An observation records original and actual input hashes, extraction key, facts, source,
model, and time. The extraction key binds the prompt, schema, model configuration, and
image size. The normalizer works from stored printed values. No metadata is overwritten. The raw metadata stays visible while image facts update.
Polling requires a fresh active worker and an unpaused queue. Removed images and inactive workers do not cause perpetual polling.
A live worker discovers new inputs at its poll interval, independently of free model slots.
Existing VLM observations from older recipes require an explicit refresh. Main/patch disagreement is a separate filter.

The watcher adds an attributes stage after existing stages. The `attributes` option of
`image_description` defaults to true. Existing inputs first reuse saved VLM label text.
Manual descriptions and old descriptions for another crop are not used as automatic
evidence. New or changed inputs use the configured VLM. Missing facts can be extracted
with the Dataset Actions menu. A per-card action requests a new image analysis.
A Dataset GET makes no queue write and no inference call.

A generation token prevents an old response from finishing a refreshed job. The worker advertises its active extraction key and heartbeat in SQLite.
A snapshot of original/input identities identifies baseline images. Link rowids are not used.
A model change does not automatically re-extract existing observations. Earlier VLM facts
stay stale until an explicit request. Cached-text facts have an independent version.
Discovery uses a set-based operation at most once per poll interval.
A dead lease
expires after 15 minutes. A lease that expires three times fails. Service outages reuse
the watcher backoff. Malformed responses have bounded counted retries. Invalid quoted attributes become Unknown.
Exhausted failures require an explicit retry. Pause and cancel
controls affect image fact jobs only. Existing image stages continue.

Tests use temporary databases, stub model calls, and local HTTP servers. They check
source preservation, shared images, input replacement, refresh races, lease recovery,
field semantics, strict evidence validation, API guards, filters, and escaped UI text.
Use COMMANDS.md for executable commands.

The missing-facts batch preserves completed VLM observations, including Unknown values.
An individual refresh or an explicit all-input batch can request a new analysis.
The request generation enters the model request so an explicit refresh can produce a
new answer. Semantically inconsistent individual attributes become Unknown.
Wrong structures and malformed JSON remain bounded image failures.
The client checks the raw heartbeat time. A cached worker-active flag cannot sustain polling.
The pause button label is initialized from stored queue state.
