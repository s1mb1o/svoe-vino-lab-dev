# Base NaFlex p512 main-pipeline validation

Date: 2026-10-19

## Scope

Application: `chtozavino.alolalab.com`, version `0.2.0`, version code `6`.
Working copy: `/Volumes/Storage/svoe-vino-final/code/svoe-vino-lab-android`.
The default query path is full image, no segmentation, complete Base NaFlex p512,
standard attention pooling, and maximum reference cosine.
The vector dimension is 768.
DIS and YOLO remain optional query modes.

This integration uses the released `siglip2-naflex-litert` v0.2.0 AAR.
The library SHA-256 is
`323f9392dfe32879951be58c3ae6e9b903d6e00f2a550104f201a198fcc7d6a4`.
The model SHA-256 is
`9cd7a00df9818bebe9e505e7a84647334587f88101300dd14b4bce1e39165005`.
The profile SHA-256 is
`1ac1a7a3a88074c04fc1559c9d0ae350820a8f681bc84f6176ef2aaed786683c`.
Read [the pack contract](../model-pack.md) for the revision and remaining hashes.

## Catalogue

The new format 6 pack contains 2,093 wines and 2,093 reference vectors.
Each wine has one unrotated reference from the verified complete-graph frozen index.
The source index contains 2,193 rows.
All 2,093 existing application wines occur in the source index.
Every selected float32 row is byte-exact with its source row.
The maximum L2 norm error is `1.7881393432617188e-7`.
The metadata, codes, DIS model, YOLO model, and display archive match the previous pack.
All 2,093 display images pass SHA-256, transparent WebP, and 1,024-pixel checks.

The pack does not contain a 72-angle p512 reference index.
Do not reuse the old fixed Base/224 or split-runtime vectors.
The frozen reference index uses package-cut images.
Optional query segmentation does not change these reference vectors.

Pack size: 402,692,669 bytes.
Pack SHA-256:
`4307a92be20fc53bec18f922ae80b60d92fc219c2a8e22f981f8c8778117a128`.
The same pack is present as an uncompressed asset in both APK variants.
Generated packs and model weights remain outside Git.

## Host checks

- 64 debug unit tests passed.
- 61 release unit tests passed.
- 16 Python pack and export tests passed.
- `lintDebug` and `lintRelease` passed.
- `assembleDebug` and `assembleRelease` passed.
- Gradle verified the pinned AAR and format 6 built-in contract.
- Contract tests rejected wrong pipeline, runtime, revision, profile, pooling, patch
  limit, and vector dimension.
- Export tests rejected incompatible indices, corrupt vectors, missing wines, and
  changed model files.
- Worker tests verified same-thread execution across callers and error propagation.
- Accelerator tests rejected zero, non-finite, wrong-size, and incompatible vectors.
- Pack upgrade tests selected format 6 instead of old fixed or split packs.

Debug APK: `android/app/build/outputs/apk/friendly/chtozavino-0.2.0-debug.apk`.
Size: 448,054,591 bytes.
SHA-256: `a11767bc3a3f2199cb836f155cce376601ae596f001647b3e37260781ba30b0e`.

Release APK: `android/app/build/outputs/apk/release/app-release-unsigned.apk`.
Size: 414,916,342 bytes.
SHA-256: `f6dbfe72e5d2bff1de98cee3ac8948c3b3f9553d1a477575be6425c1feb4ccb6`.
The release APK is unsigned.
Do not publish or install it as a signed production release.

## Device checks

Pixel 8 serial `41231FDJH002WZ` became available after host validation.
`adb install -r` installed the debug APK over version 0.1.4 successfully.
The installation did not clear application data.
No private settings or history backup was exported.
The owner unlocked the phone and confirmed the full-image pipeline.
The installed pack upgraded to `20261019-base-naflex-p512-complete`.
The main screen did not request the previously accepted 18+ choice again.
Settings showed 2,093 wines, Base NaFlex p512, no segmentation, and automatic GPU.
The debug HTTP server was off before the test.
The test enabled the server through settings and used ADB forwarding on port 18088.
Health reported runtime `naflex-complete`, dimension `768`, patch budget `512`,
standard pooling, maximum aggregation, and segmenter `NONE`.

### Vector agreement

The same transparent reference PNG passed on CPU and GPU.
Its size was 260 by 999 pixels.
Its alpha range was 0 through 255.
Its image SHA-256 was
`91fd91b66af7cd0ccf548d04773927fdcb35add1ecf519d9669e1ac85c620678`.
Both paths returned `a-gordienko-m-nikolaev-pino-nuar-krasnoe-suhoe-135` at rank 1.
The reference similarity was approximately `1.0`.
CPU/GPU cosine was `0.9999999999384342`.
Maximum component error was `0.000003904104232788086`.

Fourteen pilot images had cached vectors from the matching complete desktop graph.
The cache identity matched the model and profile hashes above.
All fourteen device vectors passed comparison.
Minimum desktop/device cosine was `0.9999999999289232`.
Maximum component error was `0.0000015003606677055359`.
The check did not launch another desktop GPU job.

### Thirty-image GPU pilot

The pilot reused the exact thirty-image selection from the earlier split pilot.
All thirty input file SHA-256 checks passed.
The set contained 24 positive, 5 negative, and 1 no-match query.
The model was warm after the CPU/GPU comparison.
Every request used the complete p512 GPU encoder without segmentation.
All 30 requests returned HTTP 200.
Every vector contained 768 finite values.
Maximum L2 norm error was `5.242277356654057e-8`.
The application PID remained `18681` throughout the pilot.
No process restart, native abort, or fatal application exception occurred.
The GPU delegate covered all 1,988 graph nodes in one partition.

| Measurement | Median | P95 | Maximum |
| --- | ---: | ---: | ---: |
| Server processing, ms | 514.8 | 748.8 | 768.7 |
| Client wall time, ms | 581.0 | 992.6 | 1439.4 |
| Embedding stage, ms | 437.5 | 676.9 | 697.0 |

Server processing includes preprocessing, inference, search, and debug previews.
It excludes HTTP upload and source image decoding.
Client wall time includes the HTTP call and source image decoding.
These measurements do not include a fresh model-session load.
The first GPU request in the preceding parity check took 2,704.7 ms on the server.
That request included model-session initialization.

Peak sampled process PSS was 947,487 KiB, or 925.3 MiB.
PSS does not measure the complete GPU allocation peak.
The maximum Android thermal status was `NONE` (`0`).
The battery temperature changed from 36.5 to 36.8 degrees Celsius.
The pilot passed the existing runtime, memory, thermal, and process-stability gates.

The accepted positive Top-1 count was 17 of 24.
The accepted positive Top-5 count was 21 of 24.
The accepted positive Top-10 count was 22 of 24.
The selection deliberately contains only eight old-baseline Top-1 hits.
These counts are not a full `my` accuracy estimate.

`/v1/eval/predict` and `/v1/match?k=1` also returned the correct reference wine.
The server was then disabled through settings.
The local health request stopped accepting connections.

Read [the machine-readable measurements](2026-10-19_base-p512-default-measurements.json).
Raw responses, vectors, runtime samples, and app-only logs are in
`/Volumes/Storage/svoe-vino-final/artifacts/android-base-p512-20261019/`.
The pilot results are in its `pixel8-p512-complete-gpu/results.jsonl` file.
The CPU/GPU comparison is in its `pixel8-vector-parity.json` file.

### UI and persistence

The document picker imported the same transparent PNG from Downloads.
The preview decoded without an application exception.
UI recognition returned `Пино Нуар` at `Сходство: 100%`.
The technical text reported full image without segmentation and SigLIP2 GPU.
Its embedding stage took 3,319 ms after the HTTP encoder was closed.
This stage included a new GPU model-session load.
Search took 80 ms.
The process remained PID `18681` through this UI recognition.
The saved screenshot is `pixel8-p512-ui-result.png` in the artifact directory above.

The test then deliberately force-stopped and reopened the application.
The new PID was `24675`.
The main screen opened without an 18+ prompt or a new compatibility check.
The test wine and its 100-percent score remained visible in history.
No private history content was exported.
The HTTP server remained disabled after this cold restart.
The test removed its Downloads image, temporary UI dump, and ADB forwarding rule.
The generated history record remains on the phone.

## Measurement limits

The earlier `85/99` Eval Top-1 result belongs to the separate benchmark application
and its 2,193-row index.
It is not a new accuracy result for this wine application or its 2,093-row pack.
Read [the implementation comparison](../naflex-implementations.md) for that result.
The integration checks did not include full `my`.
The subsequent [full my benchmark](2026-10-19_pixel8-base-p512-full-my.md) completed
3,409 requests with the same APK and pack.
That report records retrieval gains, a negative-case regression, and sustained
thermal status `SEVERE`.
The integrated application passed device vector, GPU runtime, and transparent PNG
endpoint checks.
CPU/GPU parity used one reference image.
Desktop/device parity used fourteen pilot images, not all thirty.
UI recognition and history persistence passed on the transparent PNG reference.
HEIC input, EXIF orientation, and optional segmentation were not retested in this change.
