# Research log

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
