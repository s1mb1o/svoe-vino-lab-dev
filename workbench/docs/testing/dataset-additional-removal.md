# Dataset additional-image removal

The × button removes one additional image immediately on the lab server.
The page sends one `DELETE /api/dataset-alternative` request with `slug` and `sha256`.
The page needs no confirmation and no Apply step.
The page disables the image actions while the request runs.
A failed request keeps the image visible and reports the error.
The wine, main image, other additional images, and stored image bytes stay present.
The file review editor keeps its staged Apply workflow.

Eight UI tests check the actual page functions and click handler in Node.js.
They cover immediate requests, exact image selection, retained staged changes,
HTTP errors, network errors, repeated clicks, disabled controls, and the file review editor.
Existing route tests check the stored assignment and retained image file.
The browser check uses a private SQLite copy and the exact owner screenshot image.
The browser check does not delete a live image assignment.
Read the commands in [COMMANDS.md](../../COMMANDS.md).
