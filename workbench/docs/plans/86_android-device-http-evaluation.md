# Plan 86: Android device HTTP evaluation

Date: 2026-09-29

Status: implemented and verified.

## Purpose

The Android debug application MUST expose the on-device recognition pipeline to the
workbench.
The workbench MUST run a test set against a selected Android device on the LAN.
The release application MUST contain no HTTP server.

## Selected approach

Use NanoHTTPD 2.3.1 in the Android debug source set.
The dependency MUST use `debugImplementation`.
The debug application MUST start the server on TCP port 18088.
The server MUST listen on all device interfaces.
The application MUST stay open during a test run.

The server has no authentication.
This is acceptable only because the server exists in the debug variant.
The release variant MUST contain no server class and no NanoHTTPD dependency.

## Android API

The server MUST accept JPEG, PNG, and WebP files in the multipart field `image`.
The request body MUST be 20 MiB or less.
The server MUST process one inference at a time.
The server MUST use the installed built-in model pack.
The server MUST use the saved `Авто`, `GPU`, or `CPU` settings for DIS and SigLIP2.
The server MUST use the same `RecognitionEngine` as the application user interface.
The server MUST not use barcode or QR recognition.

`POST /v1/eval/predict` MUST return this object:

```json
{"slug":"wine-slug"}
```

`POST /v1/match?k=20` MUST return the matcher-compatible `MatchResult` object.
The value of `k` MUST be from 1 through 20.
Each candidate MUST contain `rank`, `slug`, `score`, and `wine`.
The wine object MUST contain every field of the matcher contract.
Unavailable Android catalogue fields MUST use `null` or an empty list.

`GET /healthz` MUST report the debug server and pack state.
An inference request MUST return HTTP 503 when the pack is not installed.
Malformed requests MUST return a JSON error.

## Workbench configuration

Add these two permanent pipeline entries to `config.yaml`:

- `android-device-eval-predict`
- `android-device-match-k20`

Each URL MUST contain the placeholder `{device_ip}` and port 18088.
Each entry MUST use one worker.

The remote pipeline schema MUST support `device_ip: true`.
The schema MUST require `{device_ip}` in the URL when this key is true.
The New Run dialog MUST show a device IP field only for such a pipeline.
The dialog MUST remember the last device IP in browser storage.
The server MUST validate an IPv4 address before it starts the run.
The job MUST pass the address to `run_job.py`.
The runner MUST replace `{device_ip}` before it creates the HTTP backend.
The resolved URL MUST be present in the run metadata.

## Tests

1. Test the Android response builders and `k` validation.
2. Test that the Android debug variant contains NanoHTTPD.
3. Test that the Android release variant does not contain NanoHTTPD.
4. Test the workbench pipeline schema and placeholder validation.
5. Test the New Run API and page field.
6. Test the job command and resolved URL.
7. Build and install the debug APK on the Pixel 8.
8. Check `/healthz` through the Pixel LAN IP.
9. Send one known image to each endpoint.
10. Run the selected workbench test set through both permanent pipelines.
11. Record accuracy and latency in the workbench and Android logs.

## Documentation

Update the Android README, specification, change log, research log, and smoke tests.
Update the workbench README, change log, research log, smoke tests, and command catalogue.
Record port 18088 in the machine port registry.

## Verification result

The debug APK built and installed on the Google Pixel 8 with serial `41231FDJH002WZ`.
`GET /healthz` returned HTTP 200 through ADB forwarding.
It reported pack `20260929-dis-main` and 2,093 wines.
The server listened on `*:18088`.
The host could not connect to the Pixel Wi-Fi address `192.168.86.51` because the
network blocked the incoming connection.
ADB forwarding supplied the equivalent host address `127.0.0.1` to Workbench.

The clean eval run answered 10 requests with zero errors.
It gave recall@1 0.3 and median latency 4,349 ms.
The clean match run answered 10 requests with zero errors.
It gave recall@1 0.3, recall@5 0.6, recall@10 0.9, and median latency 4,597 ms.
A live `POST /api/run-jobs` also completed one match request with zero errors.
Its `run.json` held the resolved device URL.

The three focused Workbench test modules passed 32, 16, and 27 tests.
Android `testDebugUnitTest` and `assembleDebug` passed.
Gradle found NanoHTTPD 2.3.1 in the debug runtime and no NanoHTTPD dependency in the
release runtime.
