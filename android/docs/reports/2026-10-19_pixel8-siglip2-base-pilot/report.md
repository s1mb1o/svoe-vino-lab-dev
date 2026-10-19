# Pixel 8 SigLIP2 Base pilot

Date: 2026-10-19

## Scope

This report measures this repository's experimental split exports.
The separate `siglip2-naflex-litert` v0.2.0 library has successful complete-graph GPU
measurements on Pixel 8 and realme RMX3890.
The results below do not apply to those model files.
Read [the implementation comparison](../../naflex-implementations.md).

## Result

No encoder variant passed all pilot gates.
No new full `my` run was started.

All four variants completed 30 measured requests.
All 120 requests returned HTTP 200.
All vectors were finite and had 768 dimensions.
No application process restarted.
No Android thermal status reached `SEVERE`.

The current fixed-224 GPU path failed the exact vector gate.
The current fixed-224 CPU path failed the latency gate.
Each NaFlex CPU path failed the latency gate.
Each tested NaFlex GPU path failed the exact vector gate.

## Device

- Device: Google Pixel 8.
- Serial: `41231FDJH002WZ`.
- Android: 17.
- SDK: 37.
- Application version: `0.1.4`.
- Build fingerprint:
  `google/shiba/shiba:17/CP2A.260705.006/15641320:user/release-keys`.

## Representative set

The deterministic set contains 30 images from `my`.
It contains 8 baseline Top-1 hits.
It contains 5 baseline near misses.
It contains 4 baseline ranked misses.
It contains 7 positive absent misses.
It contains 5 negative images.
It contains 1 `no_match` image.

The selector stratified the set by image area, aspect ratio, baseline outcome, and
baseline latency.
The source data did not contain stable glare or low-light labels.

See `selection.jsonl` for the exact query IDs and image hashes.

## Export parity

The NaFlex source was `google/siglip2-base-patch16-naflex`.
The source revision was `b53b807d3a2d5e2b3911292f2d69e5341cdc064c`.

| Variant | PyTorch split cosine | LiteRT cosine | LiteRT max error | Export gate |
| --- | ---: | ---: | ---: | --- |
| p256 standard | 0.99999994 | 0.99999976 | 0.00129485 | Fail |
| p256 5a | Not applicable | 0.99999988 | 0.00089574 | Pass |
| p512 standard | 1.00000000 | 0.99999988 | 0.00113583 | Fail |

The standard split retained the original attention pooling.
The 5a split compared the custom PyTorch foreground pooling with its LiteRT export.
The export gate required cosine at least `0.99999` and maximum error at most `0.001`.

The fixed-224 desktop verification used 32 catalogue samples.
Its minimum catalogue-to-LiteRT cosine was `0.99999905`.
Its mean catalogue-to-LiteRT cosine was `0.99999964`.

## Pixel 8 vector parity

| Variant | CPU/GPU cosine | Max error | Result |
| --- | ---: | ---: | --- |
| fixed p224 | 0.99913565 | 0.00458609 | Fail |
| NaFlex p256 standard | 0.95890638 | 0.03201315 | Fail |
| NaFlex p256 5a | 0.95890638 inherited | 0.03201315 inherited | Fail |
| NaFlex p512 standard | 0.92733709 | 0.06663840 | Fail |

The p256 5a variant uses the same backbone as p256 standard.
The pooling model runs on CPU.
Its GPU result therefore inherits the p256 backbone failure.

The GPU outputs were finite.
A finite-value check did not detect the mismatch.
The application now requires `gpu_compatible: true` in a NaFlex model pack before it
can use that GPU graph.
The pack builders write `gpu_compatible: false` by default.

## Pixel 8 runtime

The measured runtime used DIS GPU and SigLIP2 CPU.
The fixed-224 run used one warm-up request before the measured set.
The fixed-224 cold warm-up took `34.48` seconds.

| Variant | HTTP | Median | p95 | Maximum | Peak PSS | Battery | Thermal | Restarts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| fixed p224 | 30/30 | 9.27 s | 10.53 s | 11.00 s | 1.40 GiB | 36.8 to 36.8 C | None | 0 |
| NaFlex p256 standard | 30/30 | 11.78 s | 13.53 s | 36.97 s | 1.41 GiB | 34.3 to 35.4 C | None | 0 |
| NaFlex p256 5a | 30/30 | 11.80 s | 13.81 s | 45.04 s | 1.41 GiB | 35.6 to 36.3 C | None | 0 |
| NaFlex p512 standard | 30/30 | 22.22 s | 24.15 s | 46.05 s | 1.44 GiB | 36.4 to 37.0 C | None | 0 |

The p256 5a median was 0.16% slower than p256 standard.
The p256 5a memory difference was approximately 2.1 MiB.
The 5a pooling cost was negligible relative to the backbone.
The p512 median was 88.6% slower than p256 standard.

The pilot gate required median latency at most 3 seconds.
It required p95 latency at most 5 seconds.
It required maximum latency at most 10 seconds.
No CPU variant met these limits.

## Reference aggregation

The current fixed-224 Android pack has 2,093 reference vectors for 2,093 wines.
Each wine has exactly one reference vector.
For this pack, `top2-mean` equals `max` for every query.
The existing full `my` control result therefore applies to both aggregation modes.

The existing result is not a new passing pilot run.
It is context for the current production control.
Its run ID is
`2026-10-18T193540Z-lab-android-device-match-k20-my-pixel8-usb-current-patches-20261018`.
It processed 3,409 queries.
Positive Recall@1 was `0.3327`.
Positive Recall@5 was `0.5646`.
Positive Recall@10 was `0.6441`.
Positive MRR was `0.4402`.
It recorded 5 positive errors.
Its median latency was `1,699` ms.
Its p95 latency was `2,156` ms.

The old full run used the faster production path.
That path does not meet the new exact CPU/GPU vector gate.

## Decision

Keep fixed p224 as the production control.
Do not replace it with these NaFlex exports.
Do not enable the tested NaFlex GPU graphs.

The next pilot SHOULD reduce backbone cost before it changes pooling.
It SHOULD test int8 or mixed-precision Base NaFlex.
It SHOULD test a smaller encoder or a supported NPU path.
It SHOULD build a real multi-reference pack before it measures `top2-mean` accuracy.

## Validation

- `lintDebug`, `testDebugUnitTest`, and `assembleDebug` passed.
- Eight exporter and pack-builder Python tests passed.
- Sixteen Workbench remote-run tests passed.
- The final debug APK SHA-256 was
  `49c57470bfe03dabab7278ab29b4da8e2e442305f5cf128f1b877247664f260b`.
- The final debug APK installed on the Pixel 8.
- The final installed pack was the fixed-224 control.
- The debug HTTP server was off after the test.
- The ADB forwarding rule was removed.
- The temporary device packs and backups were removed.
- The cleanup released approximately 2.6 GiB.

## Artifacts

Tracked artifacts are in this directory.
Raw device results and logcat files are outside Git:

- `<workspace>/svoe-vino-lab/workbench/runs/2026-10-19-pixel8-pilot-base-fixed-p224-control/`
- `<workspace>/svoe-vino-lab/workbench/runs/2026-10-19-pixel8-pilot-base-naflex-p256-standard/`
- `<workspace>/svoe-vino-lab/workbench/runs/2026-10-19-pixel8-pilot-base-naflex-p256-5a/`
- `<workspace>/svoe-vino-lab/workbench/runs/2026-10-19-pixel8-pilot-base-naflex-p512-standard/`

Generated model files and pilot packs are outside Git under
`<workspace>/svoe-vino-lab/workbench/data/models/`.
