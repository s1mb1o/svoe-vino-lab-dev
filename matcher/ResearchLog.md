# Research log

## Organizers' eval script against the local matcher, 2026-09-29

The matcher ran on this Mac on port 8158 with `matcher/config.yaml` (pipeline
`siglip2-p512-as-is`, bundle `matcher/data/gx10-siglip2-so400m-patch16-naflex-p512`,
2,094 wines). `SIGLIP2_ENDPOINT` was the gx10 gateway `http://192.168.86.14:18081`, with
`siglip2-so400m-patch16-naflex` already loaded. `eval/participant_test.sh` ran with the
organizers' arguments and port 8158. Exit code 0. Every photo got a slug.

| `query_id` | Photo (by eye) | `predicted_slug` | `latency_ms` | Wine in the bundle |
|---|---|---|---:|---|
| q-000001 | Табия, Пино Нуар полусухое 2025 | `usadba-mezyb-shishka-pino-nuar-rozovoe-suhoe-115` | 499 | No: Табия has 9 wines, no Pinot Noir |
| q-000002 | Массандра, Мускатель белый 2023 | `massandra-muskat-rozovyy-pozdnego-sbora-rozovoe-sladkoe-10` | 311 | Yes: `massandra-muskatel-belyy-belye-sorta-vinograda-beloe-sladkoe-16` |
| q-000003 | Aristov, Donum XXIV брют 2023 | `abrau-dyurso-victor-dravigny-extra-brut-shardone-beloe-bryut-125` | 416 | No: no Donum wine |

- The organizers keep the correct answers. The photo names come from a visual check of the
  labels, not from the organizers.
- q-000002 is a miss of a wine that the bundle holds. The answer has the same producer.
- q-000001 and q-000003 show wines outside the bundle. No slug of the bundle can be correct
  for them. The mock answers `tabia_pino_nuar` and `donum_xxiv` of
  `matcher/tests/config.yaml` are not catalogue slugs either.
- The script has `--max-time 10`. A cold SigLIP2 model on the gateway can take longer than
  that for the first request. Check `GET /running` on the gateway before a run.

## Backend cascade on gx10 dev: first measurements, 2026-09-29

Plan 85 of the workbench. The dev matcher on gx10 (port 29000, revision `f199e4d`,
pipeline `cascade-p512-rot5`, `answer_at_seconds` 2.9, `timeout_seconds` 9.5) got the
photos one at a time from `workbench/pipeline/remote_run.py` on the Mac. The latency is
the client time on the LAN.

`official-real-photos` (81 photos, 60 positive, 21 negative; 12 MP WebP files):

| `packages_first` | R@1 | False match at 1 | Latency median | p95 | max | Within 3 s |
|---|---:|---:|---:|---:|---:|---:|
| false | 90.0 % | 5 | 2,025 ms | 2,907 ms | 2,934 ms | 81 of 81 |
| true | 88.3 % | 5 | 2,509 ms | 2,908 ms | 2,967 ms | 81 of 81 |

- Lab references on the same set: the present prod pipeline `siglip2-p512-as-is` 81.7 %,
  `barcode-rerank-siglip2-p512-crop` 91.7 %, the best lab run 93.3 % (other settings).

`my` (run `2026-09-29T135022Z-lab-matcher-dev-cascade-predict-my-plan85`, 2,232 photos:
1,653 positive, 579 negative; 96 photos of 6 MP or more, the others small):

- R@1 83.3 % (1,377 of 1,653); false match at 1: 101 of 579. The client latency: median
  902 ms, p95 2,905 ms. The server answered each request within 2,904 ms; 116 answers came
  at the cut.
- The same 1,647 positives and 579 negatives as the lab runs (join by `image_path`; the set
  holds 1,853 distinct images in 2,232 rows):

  | Lab run | Lab R@1 | Cascade R@1 | Right only in the lab | Right only in the cascade | False match: lab, cascade |
  |---|---:|---:|---:|---:|---:|
  | `siglip2-p512-as-is` (the present prod) | 74.26 % | 83.42 % | 72 | 223 | 115, 101 |
  | `siglip2-p512-rot5-crop` (plan 82) | 79.60 % | 83.42 % | 30 | 93 | 100, 101 |
  | `barcode-rerank-siglip2-p512-crop` | 83.85 % | 83.42 % | 44 | 37 | 110, 101 |
  | `barcode-rerank-siglip2-512-crop`, the best lab run | 85.55 % | 83.42 % | 121 | 86 | 91, 101 |

  The 6 new positives: 3 right.
- The answer sources (positives right of positives; negatives with a false match):
  crop 1,437 (961 of 1,087; 75), VLM re-rank 641 (327 of 444; 22), crop at the cut 113
  (54 of 82; 4), a code of the package, the label, or the photo 30 (28 of 30; 0), the
  whole photo 11 (7 of 10; 0).
- The stages: SAM3 median 613 ms (p90 771 ms); the crop embedding median 69 ms; the
  full-photo scan median 175 ms; 641 VLM calls completed (median 1,178 ms, p90
  1,816 ms), 114 were cut.
- One client timeout (`q-001534`, a photo of 346 × 1200 px): the server answered HTTP 200
  after 1,179 ms with the right slug (the uvicorn access line at 14:22:54.944 UTC), but the
  client got no answer in 15 s. The next request worked. The log has no exception. The
  cause was not found.
- Answer sources with `packages_first: false`: crop 41 (27 of 29 positives right), whole
  photo at the cut 19 (12 of 14), VLM re-rank 14 (11 of 12), crop at the cut 7 (4 of 5).
- `packages_first: true` is worse: both SAM3 requests came back late (median 1,114 ms and
  1,224 ms against 986 ms for one request), and 24 photos fell back to the whole photo
  (against 19). The default stays `false`.
- SAM3 is the limit. In the run, `sam3_full` took a median 986 ms; 18 of 81 calls were
  still running at the cut (about 2.8 s). The SAM3 statistics of the same 5 minutes: an
  average queue wait of 1,031 ms at a load of 32 %. A cancelled call closes the
  connection, but the SAM3 server finishes the job, so the next photo waits behind it.
  The cuts came in streaks. Correction after the run at 2.8 s (below): the same 81 photos
  gave a load of 17 % and a queue wait of 17 ms there, with no cut SAM3 call. So other
  SAM3 work probably ran during this run; the abandoned jobs were not the main cause.
- The run with `answer_at_seconds: 2.8` (`…-plan85-aa28`, 14:45 UTC, `packages_first:
  false`): R@1 90.0 % (54 of 60, the same as at 2.9 s), false match at 1: 3 of 21,
  latency median 1,697 ms, p95 2,808 ms, max 2,820 ms, 81 of 81 within 3 s. Sources: crop
  56 (36 of 39 positives right), crop at the cut 16 (11 of 13), VLM re-rank 8 (6 of 7),
  whole photo at the cut 1 (1 of 1). SAM3: 81 of 81 completed, median 1,018 ms. The VLM:
  15 of 23 calls were cut, against 6 of 20 at 2.9 s; a cut call had run a median 1.25 s,
  a completed call takes a median 1.34 s. On these 12 MP photos, the earlier cut thus
  stops more re-ranks. Here it did not change R@1. The lower latency against the run at
  2.9 s comes mostly from the quiet SAM3, so the two runs do not isolate the effect of the
  cut on the latency.
- A direct probe of 12 of these photos, one request at a time, with the six nouns: a SAM3
  copy of 1,600 px took a median 0.70 s (max 4.23 s on one photo with many instances); a
  copy of 1,008 px (the model input size) took a median 0.59 s (max 1.00 s on the same
  photo). A smaller copy removes the heavy tail that starts the queue.
- On the host, for the three official sample photos (12 MP, 1.25 MB): about 150 ms until
  the stages start (upload, decode, archive), SAM3 about 0.9 s, the crop embedding about
  0.1 s, the crop scans 0.15–0.25 s; the answer at 1.32 s from the request headers.
- The public edge from this Mac (`https://chtozavino.ru/healthz`, 10 samples): DNS 3 ms,
  TCP 6–11 ms, TLS 14–23 ms, the tunnel round trip 8–15 ms. A client far from Princess
  pays about three round trips outside the server clock; the reserve of 0.1 s covers a
  round trip of up to about 30 ms.
- The same URL from `alphavps-bg` (Bulgaria; ping round trip 68.5 ms; curl 7.81, TLS 1.3,
  HTTP/2), 13 samples: DNS 28–166 ms, TCP about 70 ms, the TLS handshake 150–260 ms (2 to
  4 round trips), the first byte 75–80 ms later, the total 0.33–0.56 s for a GET with
  no body. A client at this distance loses about 0.35–0.55 s outside the server clock;
  an answer at the cut of 2.9 s then arrives after about 3.3–3.45 s. The reserve MUST
  follow the network position of the harness.
- The owner thinks that the harness runs in Russia (2026-09-29T17:18:57+0300). Two
  Moscow hosts, 10 samples each, the same URL:
  - `claudette` (Selectel Moscow `ru-7a`; ping 0.46 ms, so Princess is in the same
    Selectel site): the total 49–53 ms with a cached DNS answer, 66–101 ms with a DNS
    lookup. The TLS handshake alone takes about 43 ms at this distance: it is CPU work,
    mostly of the client (curl 8.5, OpenSSL 3.0.13), not network time.
  - the reg.ru host `u3067741` (another provider; curl 7.61, OpenSSL 1.1.1k; TCP connect
    3–5 ms): the total 39–53 ms for 7 samples, and 101, 166 (DNS lookup 116 ms), and
    193 ms (TCP 54 ms, TLS 99 ms) for 3 samples.
  - A Moscow client thus loses about 40–55 ms outside the server clock, up to about
    190 ms on an outlier. The reserve of 0.1 s covers the typical case. A cut answer is
    late on an outlier.
- An estimate from the stage times of the official run (`packages_first: false`): a cut
  at 2.8 s instead of 2.9 s changes the answer source of about 1 of the 81 photos
  (crop to whole). No stage of the other photos ended between 2.8 s and 2.9 s.
- Caddy on Princess streams the request body to the upstream (`reverse_proxy` without
  `request_buffers`; `request_body` sets only `max_size`). So the upload time counts in
  the server clock. This is the documented Caddy default; it was not measured, because
  a body test through the edge needs the Basic password.
- The VLM cancellation works (plan 85, verification 8). A cut closes the connection to
  llama-swap, llama-swap closes its connection to vLLM, and vLLM stops the request. Two
  checks on the real runs:
  - The vLLM access log of 13:41 to 13:46 UTC has one line "200 OK" for each of the 14
    completed VLM calls, 20 to 40 ms before the end of the stage. The 7 cancelled calls
    have no line. One of them ran 1.66 s before the cut; a completed call takes 1.1 to
    1.7 s.
  - A poller on gx10 read `vllm:num_requests_running` from the vLLM port 8001 each 0.2 s
    for 320 s of the run on `my` (73 VLM calls: 68 completed, 5 cancelled after 1.8 to
    2.2 s). After each cut, the gauge fell to 0 within 0.2 s. It was never above 1.
  - The counter `vllm:request_success_total{finished_reason="abort"}` stayed 0. It does
    not count these aborts. Do not use it for this check.
- A cancelled VLM call had run a median 1.3 s (max 1.7 s) at the cut. A completed call
  takes a median 1.3 s. So many cut calls were close to their answer.

## Backend cascade: design facts, 2026-09-29

Plan 85 of the workbench. Sources: the lab runs on `my`, the gx10 service documents in
`~/Admin/gx10/docs/inference/`, and the version-controlled copy of the gx10 SAM3 server.

- The gx10 SAM3 server puts the requests that arrive within 15 ms in one batch
  (`_worker_loop`). `_run_jobs` sets `done` for every request of the batch after the whole
  batch. So a second, packages-only request for the same photo comes back at the same
  moment as the full request, and both come later (about 1.0 s of encoder time for two
  images against 0.71 s for one). `packages_first` is off by default; a benchmark A/B
  decides.
- `/segment` takes one noun and gives no `label`; `/segment_multi` encodes the image one
  time for all nouns and labels each instance. The hand selection sent five nouns to
  `/segment` and so gave HTTP 502 on any detection (fixed on 2026-09-29).
- The rot5 index of plan 82 holds only the view `full`. The group gate of `c88464f` needs
  the view `label`, so a `cascade` pipeline takes `group_embedding` for the group route.
- The load of `cascade-p512-rot5` from the lab catalogue: 1.2 s, 165,456 rows of 1,152
  values for 2,105 wines, a peak of 2.6 GB of memory (Mac). One ranking over the rotated
  rows takes 16 ms after the first call (68 ms). The p512 rule files hold 208 clusters
  (166 sheet, 42 verdict) of 516 wines; `wine_code` gives 124 values of Active wines, 7
  of them shared.
- The lab latencies that shaped the budget: uncached SAM3 median 1.5 s, p95 5.9 s (1
  worker, with `hand`); SigLIP2 44–87 ms; `zxing-cpp` scans 10–200 ms; a VLM re-rank call
  0.9–1.5 s at idle, median 2.7 s at 4 in parallel. So at 2.9 s the VLM is often not
  done, and the whole-photo ranking answers when SAM3 is slow.

## Conditional model readiness, 2026-09-29

Three options were considered.
The first option made `/healthz` call each model dependency.
The second option kept `/healthz` as liveness and added `/readyz` for dependency checks.
The third option checked only a lightweight model-list endpoint.

The matcher uses the second option.
Docker uses `/readyz` for its healthcheck.
The mock pipeline makes no external request.
The SigLIP2 pipeline sends one small embedding request.
A pipeline with `hand_selection: true` also sends one small SAM3 request.

This decision keeps liveness available during a model outage.
It also validates the configured model and embedding dimension.
Each dependency probe has an eight-second timeout.
The Docker healthcheck has a 20-second timeout because a hand-selection probe can use
both dependencies in sequence.

## Reproducible container dependencies, 2026-09-29

The dependency input has exact direct versions in `requirements.txt`.
This file does not lock transitive versions or distribution hashes.

Three options were considered.
The first option keeps the direct requirements and adds a generated lock file.
The second option replaces the direct requirements with one large locked file.
The third option adds `pyproject.toml` and `uv.lock`.

The matcher uses the first option.
`requirements.txt` stays the editable dependency input.
`requirements.lock` contains the complete Python 3.11 Linux graph and distribution hashes.
Docker and `matcher/tests/run_ci.sh` use pip with `--require-hashes`.
The Docker base image uses an OCI digest.

This decision keeps dependency updates explicit.
An update MUST regenerate the lock file and validate the Docker build.
The lock file targets the Python 3.11 Linux container and CI environment.
Local environments with a different Python version use `requirements.txt`.

## Group match acceptance, 2026-09-29

The first group implementation forced one catalogue result for every retained segment.
On the close owner example, two Martini bottles received unrelated wine slugs with scores from 0.673 to 0.704.
Similar Abrau-Durso packages also produced high but ambiguous full-bottle scores.
A single score threshold could not identify all of these errors.

The matcher now keeps the selected SAM3 label crop.
It ranks the bottle crop against the bundle view `full`.
It ranks the label crop against the bundle view `label`.
It accepts a candidate only when the two views agree and the score or margin rules pass.
The rule is conservative because a false wine card is worse than an unmatched bottle.

The bundled close example has 47 raw detections, 10 retained segments, and 3 accepted matches.
The bundled wide example has 77 raw detections, 33 retained segments, and 1 accepted match.
The bundled display example has 92 raw detections, 24 retained segments, and 3 accepted matches.
The accepted close results are two visible Victor Dravigny Brut Rose bottles and one Udelnoe Vedomstvo bottle.
The Martini segments now have `match: null`.
The accepted display results include two Chateau Tamagne bottles and one Inkerman Muscat bottle.

The group endpoint records matched and unmatched counts in the request audit.
The public response contract did not change.
The single-image endpoints did not change.

## Group segment quality, 2026-09-29

A production shelf photo returned 47 `wine bottle` segments.
The unwanted segments included rear bottles without visible labels, mirror reflections, and small edge fragments.
The SAM3 confidence scores of useful and unwanted segments overlapped.
A confidence threshold could not separate the two classes.

The matcher now sends one `segment_multi` request for `wine bottle` and `wine label`.
It keeps a bottle only when a label of useful size is inside the bottle mask.
It removes bottom-edge fragments.
It also compares each bottle height with the median height of bottles that start in the same shelf band.
This relative comparison keeps useful bottles in shelf bands at different distances.

The owner shelf photo now returns 10 useful segments from 47 raw bottle detections.
The rejected set includes the reported rear bottles 3, 5, 7, and 8.
It includes reflections 25 through 29.
It includes small detections 31 through 47.
Two other owner shelf photos returned 33 of 84 and 25 of 98 raw bottle detections.

This logic runs only in `POST /v1/group/match`.
The single-image endpoints do not import or call this logic.

## Group photo matching, 2026-09-28

The existing Web UI shelf implementation established the SAM3 request contract.
The request uses `wine bottle`, detection threshold 0.4, mask threshold 0.5, and full-frame PNG masks.

SAM3 detector boxes can extend outside the image.
SAM3 masks can contain disconnected fragments outside a detector box.
The matcher clamps each detector box and removes mask pixels outside that box.

A shelf can contain many bottles.
Sequential embedding requests increase network latency for every bottle.
The OpenAI-compatible embedding contract accepts an input array.
The SigLIP2 backend now sends all bottle crops in one request and validates one indexed vector per crop.

The production SigLIP2 service accepts at most 64 inputs in one request.
A shelf photo produced 93 bottle crops and caused an HTTP 400 response from SigLIP2.
The matcher now splits larger logical batches into transport requests of at most 64 inputs.
The matcher preserves the input order across these requests.

The response returns a normalized preview.
This preview makes the coordinates and masks independent of browser EXIF behavior.
The response returns cropped transparent masks instead of full-frame masks.
This choice reduces response size and supports direct UI overlays.

The detailed contract is in `docs/group-match.md`.
