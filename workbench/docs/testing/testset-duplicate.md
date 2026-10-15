# Testset photo duplication

`Duplicate` creates an independent entry for the same stored image.
The action is in the image context menu.
The new card appears beside the source card.
The image SHA-256 and image-store object stay the same.
Image tags stay shared.
The source entry stays intact.

The new entry starts without a label.
The new entry keeps the source box and source URL.
The new entry does not copy comments, proposals, or deletion marks.
Use the existing move actions to move the new entry to the Drawer or another wine slug.
Set the new entry to `positive` after review.
The manual accepted-answer rule then accepts both positive wine slugs for the exact image.

The tests use temporary databases and localhost HTTP servers.
The tests verify image reuse, source preservation, unique names, concurrent requests,
shared tags, source boxes, independent moves, accepted answers, invalid requests,
stale image rejection, and rollback.
The UI checks verify adjacent insertion, repeated-click protection, changed testsets,
request errors, lightbox position, and the context menu.
The tests do not modify the live catalogue or call a model service.
Read the commands in [COMMANDS.md](../../COMMANDS.md).
