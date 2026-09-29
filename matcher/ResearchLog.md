# Research log

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
