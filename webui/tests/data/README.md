# Dish image fixture

`dinner-rotated.heic` is a byte copy of
`matcher/tests/data/heif/apple-rotated.heic` from this repository.
It is a synthetic macOS `sips` encoding of a 64×32 red/blue image with EXIF orientation 6.
The upright result is 32×64, red at the top and blue at the bottom.
Read the source description and orientation regression in `matcher/tests/test_siglip2.py`.
It contains no user photo or personal data.

The browser tests create JPEG, PNG and WebP fixtures in a canvas.
No uploaded user images are committed.
