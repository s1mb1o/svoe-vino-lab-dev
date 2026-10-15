# Testset photo transfer

`Move To testset >` lists existing testsets in the image context menu.
The current testset is disabled.
Choose another testset to move the photo to the same wine slug.
No Match and Drawer photos keep their special place.
The move keeps every annotation, comment, box, timestamp, proposal, and provenance field.
Image bytes and shared tags stay the same.
Set-level variant groups stay in their respective testsets.

A filename collision gets a unique name that keeps the original rank and confidence.
An existing assignment of the same image to the same place returns HTTP 409.
The source and destination entries stay intact in this case.
The source SHA-256 is required to reject a stale request.
The server moves the photo and comments in one transaction.
The page saves a pending photo comment before the move.
The page updates the source card and both testset counts after a successful move.
The result has an `Open destination` link.

Model and HTTP tests use temporary databases and localhost servers.
They cover full annotation retention, image reuse, filename collisions, comments with
foreign keys enabled or disabled, invalid requests, concurrent moves, cache refresh,
round trips, and rollback.
UI behavior tests use Node.js with controlled page dependencies.
They cover pending comments, busy state, failed requests, changed testsets, source
removal, viewer position, destination links, and keyboard submenu navigation.
The isolated browser preview blocks all live write requests.
Read the commands in [COMMANDS.md](../../COMMANDS.md).
