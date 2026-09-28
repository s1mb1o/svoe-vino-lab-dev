# Smoke tests

## MI1. Empty data directory

1. Start Matcher Inspector with an empty data directory.
2. Open `/`.
3. Confirm that the page shows no requests and no bundles.
4. Open `/healthz`.
5. Confirm that the response has status `ok`.

## MI2. Request archive

1. Send one valid image to the matcher.
2. Open Matcher Inspector.
3. Confirm that the request is the first request in the table.
4. Open the request.
5. Confirm that the page shows the input image and the complete request journal.

## MI3. Embedding bundle

1. Put one valid matcher embedding bundle below the matcher data directory.
2. Open Matcher Inspector.
3. Confirm that the bundle status is `Complete`.
4. Confirm that the model, views, vector shape, wine count, and manifest are correct.

## MI4. Incomplete embedding bundle

1. Copy a bundle to a test directory.
2. Remove one declared payload file from the copy.
3. Open Matcher Inspector.
4. Confirm that the bundle status is `Incomplete`.
5. Confirm that the page names the missing file.

## MI5. Read-only access

1. Start the container with `/data` mounted read-only.
2. Open the request and bundle pages.
3. Confirm that all pages work.
4. Confirm that the service creates no file in `/data`.

## MI6. System theme

1. Set the browser to a light system theme.
2. Confirm that the page uses the light theme.
3. Set the browser to a dark system theme.
4. Confirm that the page uses the dark theme.
