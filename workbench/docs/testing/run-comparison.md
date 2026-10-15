# Run case comparison

Compare finished runs from saved query snapshots and results.
A current testset is not a historical source of labels.
Testset names alone do not establish compatibility.

The case identity uses image SHA-256 and wine placement.
Repeated assignments use the saved photo path for disambiguation.
A duplicate path with the same identity is ambiguous and MUST be rejected.
The annotation uses the saved label and the accepted-answer set.
The query order and query identifier can change between runs.

Exact snapshots permit the four pass/fail groups.
Different snapshots require explicit selection of unchanged cases.
Changed labels and cases absent from one run stay separate.
Operational errors and absent saved results do not establish recognition failure.
Negative-only labels and unlabelled cases do not establish recognition success.
The four groups contain only cases with a known pass/fail result in both runs.

Tests use private run fixtures and temporary HTTP servers.
They cover order changes, accepted vintages, repeated images, renamed testsets,
changed image bytes, changed labels, partial overlap, missing snapshots,
No Match, Top K, operational errors, API guards, pagination, cache invalidation,
HTML escaping, stale browser responses, and explicit common-case selection.
Check the live page with two completed runs. Do not rerun inference for comparison.

The read cache binds to metadata, queries, and results file identities.
A changed file invalidates the cache. A write during a read returns a conflict.
The cache has entry and byte limits. Run files remain unchanged.
A query snapshot and a result record are required for each scored comparison.
An unavailable image-store object does not prevent result comparison.
Use COMMANDS.md for the test command.
