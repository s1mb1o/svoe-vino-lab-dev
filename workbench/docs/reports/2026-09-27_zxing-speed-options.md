# ZXing scan speed options

Date: 2026-09-27.
This investigation changes no production code or configuration.
The installed decoder is zxing-cpp 2.3.0.

## Current scan

The barcode step reads the whole source photo before package or label processing.
It applies EXIF orientation and flattens transparency on white.
The profile resizes the long side to 1600 pixels.
It also enlarges a smaller photo to that size.
Each region uses `LocalAverage` and `FixedThreshold`.
The formats are EAN13, Code128, and QRCode.
Code128 results must contain a valid GTIN-13.
The decoder disables `try_downscale` and leaves `try_rotate` enabled.
A unique wine match stops the scan after a region.
With no unique match, the decoder scans 9 tiles and then 25 tiles.
The maximum is 35 regions and 70 calls to `read_barcodes`.
The barcode cache now skips these calls when it has sufficient valid results.
Read `pipeline/barcode.py` and the `barcode-options` anchor in `config.yaml`.

## Measured pass limits

The source is the run `2026-09-26T213857Z-lab-barcode-rerank-siglip2-512-crop-my`.
The snapshot contained 1692 completed photos.
The sample contains all 18 unique barcode hits in that snapshot.
The sample also contains 24 evenly spaced photos without a barcode hit.
The sample is selected. It does not measure unbiased recall.
The measurement bypassed the scan cache and used the installed decoder.
The measurement recorded each call until the existing unique-match stop.
The shorter variants use prefixes of those same calls.
Times include image opening, scaling, and decoder calls.
Times exclude tile construction and most Python lookup overhead.
Concurrent activity on the host can affect the times.

| Scan | Maximum calls per photo | Known unique matches recovered | Time for 42 photos, seconds |
|---|---:|---:|---:|
| Whole photo, LocalAverage | 1 | 15/18 | 19.127 |
| Whole photo, both binarizers | 2 | 17/18 | 20.142 |
| Whole photo and 3 by 3 tiles | 20 | 17/18 | 24.981 |
| Whole photo, 3 by 3 and 5 by 5 tiles | 70 | 18/18 | 34.908 |

The 5 by 5 tiles recover the additional match of `q-000955`.
The 3 by 3 tiles recover no additional unique match in this sample.
This result does not prove that those tiles are unnecessary for other photos.

## Parallel calls for one image

The Python binding releases the GIL around `ReadBarcodes`.
The image buffer handling occurs before that release.
The library documents thread safety.
The inspected decode paths use sequential loops and have no internal worker pool.
The Python API has no `threads` argument.
A caller can submit independent tile or binarizer calls to a thread pool.

The control below uses 70 calls on each of three photos without a unique match.
It compares a sequential loop with a persistent pool of four threads.
Each variant runs twice, with the order reversed on the second repetition.
The table shows the mean wall time.
Image preparation and tile creation occur before these timers.
Every decoded result was identical between the variants.

| Query | Sequential seconds | Four-thread seconds | Speed factor |
|---|---:|---:|---:|
| q-001478 | 0.6742 | 0.3077 | 2.19 |
| q-001549 | 0.2453 | 0.0626 | 3.92 |
| q-001621 | 0.3299 | 0.1086 | 3.04 |

Four image workers already permit four concurrent decodes.
Four decode threads inside each of four image workers can create 16 concurrent decodes.
A shared bounded decode pool can prevent this multiplication.
A parallel implementation must preserve pass order when it chooses the first unique match.
It must also preserve the ordered scan batches in the cache.

## Crop choices

A bottle rectangle can remove unrelated image regions.
A barcode rectangle can reduce the decode area further.
Use source pixels and retain a margin around the code.
The label crop is less reliable as the only search region.
`pipeline/alternatives.py` selects `label` instances for that crop.
It identifies `barcode` instances separately.
The chosen label can therefore exclude a barcode or QR sticker.
A masked label crop can also alter the pixels near a code.
These crop choices were inspected in code. Their speed and recall were not benchmarked.
A new SAM3 call adds cost. Use an existing crop when one is available.

## Suggested next experiment

1. Keep two whole-photo passes as the initial scan.
2. On a miss, test source-pixel bottle or barcode rectangles with a margin.
3. Keep the 5 by 5 scan as an optional exhaustive fallback until the full corpus is checked.
4. Use a shared pool of four decode workers for interactive single-image latency.
5. Compare the result with the existing four-image worker mode for bulk throughput.

Do not enable `is_pure` for a normal bottle photo.
The API reserves that option for a perfectly aligned isolated barcode.
The Python 2.3.0 binding does not expose `try_harder` or `try_invert`.
Converting RGB to grayscale once can avoid repeated conversions, but it changes the
FixedThreshold input: the current C++ path uses the green channel for that binarizer.
Test this change separately before treating it as equivalent.

## Primary sources

- [Python binding v2.3.0](https://github.com/zxing-cpp/zxing-cpp/blob/v2.3.0/wrappers/python/zxing.cpp): GIL release at lines 135-137 and Python options at lines 405-414.
- [README v2.3.0](https://github.com/zxing-cpp/zxing-cpp/blob/v2.3.0/README.md): thread-safety statement.
- [ReaderOptions v2.3.0](https://github.com/zxing-cpp/zxing-cpp/blob/v2.3.0/core/src/ReaderOptions.h): internal defaults and option meanings.
- [ReadBarcode v2.3.0](https://github.com/zxing-cpp/zxing-cpp/blob/v2.3.0/core/src/ReadBarcode.cpp): luminance preparation and sequential decode path.
