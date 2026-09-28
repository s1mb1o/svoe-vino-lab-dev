# Decision 003: Result photo card

Date: 2026-09-26

## Context

The recognition result must show an image and wine parameters.
The catalogue contains `image_url`, `category`, `color`, and `grapes`.
The catalogue does not contain a separate sugar field.
Some catalogue records do not contain an image.

## Options

### Give Telegram the catalogue image URL

This option has the least bot-side work.
Telegram must support the source image format and size.
The bot cannot validate the image before Telegram fetches it.

### Download and normalize the catalogue image

This option validates the response as an image.
This option converts WebP and other supported image formats to JPEG.
This option controls the image dimensions and file size.
This option can use the submitted safe photo as a fallback.

### Read the official image from a local dataset path

This option avoids an HTTP request.
The catalogue local path belongs to the source workstation.
The path is not portable to `gx10`.

## Decision

Download the official catalogue image through the shared HTTP client.
Allow only the configured official HTTPS host.
Limit the downloaded image size.
Validate the image with Pillow.
Normalize the image to JPEG before Telegram upload.
Use the submitted safe photo when the official image is unavailable.

Read color and grape data from the catalogue.
Infer the sugar class only from explicit terms in the slug or wine name.
Show `нет данных` when no explicit sugar term exists.

## Consequences

A successful answer usually shows the official wine image.
The answer always has an image when the submitted photo remains readable.
An official image network failure does not change the recognition result.
The sugar class can be absent for records without explicit source data.
