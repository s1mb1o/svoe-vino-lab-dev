# Production matcher stress test

Date: 2026-09-29

## Result

The production matcher passed the bounded stress test.
No request caused an HTTP 500 response.
No request caused a transport error.
The container stayed healthy.
The container restart count stayed at zero.

The queue rejected overload with HTTP 503.
Each overload response contained `Retry-After: 1`.
The health endpoint stayed available during overload.

## Target

The test used `http://192.168.86.14:28000`.
The deployed matcher revision was `013ab56`.
The pipeline was `siglip2-p512-as-is`.

The test used the direct LAN endpoint.
The test did not use the public HTTPS edge.
The test did not change matcher configuration.
The test did not restart a service.
The test did not run a sustained soak test.

GX10 had other active inference work during this test.
The test therefore used short request waves.

## Preflight and postflight

Before the test, the matcher container was healthy.
The container used approximately 135 MiB of memory.
The restart count was zero.
The sampled GPU utilization was 0 percent.

After the test, the matcher container was healthy.
The container used approximately 192 MiB of memory.
The restart count was zero.
The sampled GPU utilization was 0 percent.
The matcher log contained no `ERROR`, traceback, or HTTP 500 event from the test period.

## Functional checks

The test sent the three official WebP fixtures to `POST /v1/eval/predict`.
Each image was 3024 by 4032 pixels.
Each request returned HTTP 200.
The request times were 0.666 seconds, 0.685 seconds, and 0.676 seconds.

The test sent one official WebP fixture to `POST /v1/match?k=4`.
The request returned HTTP 200 in 0.509 seconds.
The response contained four ordered candidates.
Each candidate contained a wine card.
The first candidate equaled the `POST /v1/eval/predict` result.

The test sent the same WebP fixture to `POST /v1/group/match`.
The request returned HTTP 200 in 1.000 seconds.
The response contained three bottle detections.
Each bottle contained a box, a PNG mask, and a catalogue match.
The response size was 545,483 bytes.

The test also sent small valid JPEG, PNG, and WebP images.
Each format returned HTTP 200.
A valid WebP with multipart type `application/octet-stream` also returned HTTP 200.
The service validated the image bytes instead of trusting the multipart type.

## Invalid input checks

All expected invalid-input checks passed.

| Input | Expected status | Actual status |
|---|---:|---:|
| `GET` on the prediction endpoint | 405 | 405 |
| Missing `image` field | 422 | 422 |
| Wrong multipart field | 422 | 422 |
| Empty image | 400 | 400 |
| Non-image bytes with a JPEG name | 422 | 422 |
| Damaged WebP | 422 | 422 |
| Valid GIF | 415 | 415 |
| `k=0` | 422 | 422 |
| `k=21` | 422 | 422 |
| `k=x` | 422 | 422 |

The test declared a 1 GiB request body and sent no body bytes.
The service returned HTTP 413 in 1.3 ms.
This result confirms early `Content-Length` rejection.

## Large image checks

The configured image limit was 40,000,000 pixels.

The test sent an 8000 by 5000 WebP.
This image had exactly 40,000,000 pixels.
The service returned HTTP 200 in 0.638 seconds.

The test sent an 8001 by 5000 WebP.
This image had 40,005,000 pixels.
The service returned HTTP 413 in 3.6 ms.
The response stated that the image pixel count exceeded the configured limit.

## Parallel request checks

Each wave sent one valid 256 by 192 WebP per client.
Each wave was a short burst.
The table shows latency only for HTTP 200 responses.

| Concurrent clients | HTTP 200 | HTTP 503 | Median latency | Maximum latency | Maximum health latency |
|---:|---:|---:|---:|---:|---:|
| 1 | 1 | 0 | 94 ms | 94 ms | 31 ms |
| 2 | 2 | 0 | 78 ms | 96 ms | 5 ms |
| 4 | 4 | 0 | 98 ms | 191 ms | 6 ms |
| 8 | 8 | 0 | 153 ms | 244 ms | 5 ms |
| 16 | 15 | 1 | 264 ms | 426 ms | 7 ms |
| 32 | 16 | 16 | 253 ms | 456 ms | 16 ms |

The first overload rejection occurred in the 16-client wave.
The 32-client wave rejected half of the requests.
All 17 overload responses contained `{"detail":"matcher is busy"}`.
All 17 overload responses contained `Retry-After: 1`.

The test collected 29 health samples during the waves.
All 29 samples returned HTTP 200.

## Operational note

The matcher archives each accepted image request.
This test added 56 accepted requests to the production request archive.
The archived source images use approximately 6.14 MiB before audit metadata.
The request archive has no automatic retention policy.

## Conclusion

The matcher handled valid JPEG, PNG, and WebP input correctly.
The matcher rejected invalid and oversized input correctly.
The matcher stayed responsive during bounded overload.
Clients SHOULD retry HTTP 503 after the stated one-second delay.

