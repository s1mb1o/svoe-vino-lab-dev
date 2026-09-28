# Scan codes in an additional image

Date: 2026-09-28

## Goal

The Dataset page MUST scan each uploaded additional image for a QR code and a barcode.
The lab server MUST use the existing `qr-scanner` service.
The lab server MUST store each valid result in the code fields of the wine.

## Service contract

The client MUST read the service URL from `QR_SCANNER_ENDPOINT`.
The client MUST send `POST <QR_SCANNER_ENDPOINT>/scan`.
The request MUST send the image in the multipart field `image`.
The request MUST send `engine=auto`.

The client MUST read the `instances` list of the response.
Each instance MUST have a non-empty `text` and `format` string.
A format that normalizes to `qrcode` is a QR code.
Each other format is a barcode.

## Code rules

The lab server MUST use `codes.clean("gtin", value)` for a barcode.
The lab server MUST use `codes.clean("qr_url", value)` for a QR code.
The lab server MUST ignore a barcode that is not a valid GTIN.
The lab server MUST ignore a QR code that is not an HTTP or HTTPS URL.
The lab server MUST remove duplicate normalized results from one scan.

The lab server MUST add a missing result to `wine_code`.
The lab server MUST keep an existing result unchanged.
The lab server MUST permit one result to belong to more than one wine.
The lab server MUST invalidate the stored barcode scans of the test photos of the wine
after it adds at least one result.

## Upload behavior

The scan MUST occur for each `POST /api/dataset-alternative` request.
The scan MUST also occur when the image bytes are already linked to the wine.
The scan MUST occur outside a database write transaction.
The code writes MUST finish before the server builds the response record.
The response record MUST contain the new `_gtins` and `_qr_urls` values.
The existing Dataset page MUST render these values without a separate UI change.

A scanner failure MUST NOT remove or reject a valid additional image.
The response MUST contain a warning when the scanner is not configured or does not
answer.
The warning MUST state that the photo was stored without new code fields.

## Verification

Unit tests MUST verify the remote request contract and response checks.
Unit tests MUST verify GTIN and QR URL normalization.
Unit tests MUST verify duplicate and invalid results.
An integration test MUST verify that an upload fills both code fields.
An integration test MUST verify that a repeated upload does not add duplicate rows.
An integration test MUST verify that a scanner failure keeps the image.

The focused tests MUST make no network request.
The complete workbench test suite SHOULD pass before the server restart.
