# Matcher smoke tests

## Single image regression

- Send a known image to `POST /v1/eval/predict`.
- Confirm that the response contains the expected `slug`.
- Send the same image to `POST /v1/match`.
- Confirm that the response contains ranked candidates and wine cards.

## SigLIP2 failures

- Make SigLIP2 return HTTP 500. Confirm HTTP 502 from both single-image endpoints.
- Make SigLIP2 return invalid JSON. Confirm HTTP 502.
- Make SigLIP2 exceed its request timeout. Confirm HTTP 504.
- Confirm that each audit record contains the same response status as the API.

## Damaged images and the pixel limit

- Select a SigLIP2 pipeline. Cut a JPEG in half.
- Send the damaged JPEG to `POST /v1/eval/predict` and to `POST /v1/match`.
- Confirm HTTP 422 with `image file is invalid or damaged` from both endpoints.
- Confirm that SigLIP2 gets no request and that each audit record has status 422.
- Set `SVOE_VINO_MATCHER_MAX_IMAGE_PIXELS=89478486`. Confirm that the matcher does not
  start and that the error names the Pillow limit.

## Liveness and readiness

- Select a mock pipeline. Confirm HTTP 200 from `/healthz` and `/readyz` without a
  model endpoint.
- Select a SigLIP2 pipeline. Confirm that `/readyz` sends one small embedding request.
- Stop SigLIP2. Confirm HTTP 503 from `/readyz` and HTTP 200 from `/healthz`.
- Enable `hand_selection`. Confirm that `/readyz` checks SAM3 before SigLIP2.
- Disable `hand_selection`. Remove `SAM3_ENDPOINT`. Confirm HTTP 200 from `/readyz`
  while SigLIP2 is available.
- Confirm that Docker uses `/readyz` as its healthcheck URL.

## Reproducible image

- Build the matcher image on Linux from the `matcher` directory.
- Confirm that the base image resolves to the digest in `matcher/Dockerfile`.
- Confirm that pip uses `matcher/requirements.lock` with `--require-hashes`.
- Change one hash in a temporary lock file. Confirm that the image build fails.

## Group match

- Configure a version 2 matcher bundle.
- Set `SAM3_ENDPOINT` to the canonical SAM3 base URL.
- Send a shelf photo to `POST /v1/group/match`.
- Confirm that the response contains `image`, `detected_count`, `truncated`, and `bottles`.
- Confirm that each bottle has an `id`, `segmentation_score`, normalized `box`, transparent PNG `mask`, and best `match`.
- Render each mask inside its box over `image.preview`.
- Confirm that the mask follows the correct bottle.
- Confirm that each returned bottle has a visible label.
- Confirm that rear bottles without visible labels are absent.
- Confirm that mirror reflections and small edge fragments are absent.
- Confirm that useful bottles from different shelf bands remain present.
- Confirm that background pixels in matcher crops are white.
- Confirm that one logical embedding batch contains one bottle crop and one label crop for each retained segment.
- Confirm that a candidate must agree across the `full` and `label` bundle views.
- Confirm that foreign products and ambiguous variants have `match: null`.
- Confirm that a high-confidence two-view candidate keeps its wine card.
- Confirm that each returned wine card links to its catalogue page.
- Use a shelf photo that produces more than 64 bottle crops.
- Confirm that the matcher splits the SigLIP2 requests and returns one group response.

## Hand-aware single-image selection

- Set `hand_selection: true` in the selected SigLIP2 pipeline. Set `SAM3_ENDPOINT`.
- Restart the test matcher. Send a photo of a held package with shelf bottles behind it.
- Check both `POST /v1/match` and `POST /v1/eval/predict`.
- Confirm that SAM3 receives `wine bottle, can, packet, box, hand` in the field
  `texts` of one `POST <SAM3_ENDPOINT>/segment_multi` request, and that the answer
  is HTTP 200 (a `/segment` request gives no labels and HTTP 502).
- Confirm that the embedding input contains the selected package with white pixels
  outside its mask. A hand overlap is a heuristic, not a guaranteed correct selection.
- Send a photo without a hand. Confirm that scene ranking still selects a package.
- Make SAM3 return no packages. Confirm that the original image reaches preprocessing.
- Send a shelf photo to `POST /v1/group/match` while the option is still enabled.
- Confirm that SAM3 receives only `wine bottle, wine label`, once per successful group
  request.
- Confirm that every retained bottle gets a gated match or `match: null`, and that no
  crop triggers hand selection.
- Set `hand_selection: false` and restart the test matcher. Confirm that both
  single-image endpoints work without `SAM3_ENDPOINT` and use the full photo.
- With the option enabled, remove `SAM3_ENDPOINT`. Confirm HTTP 503 on both
  single-image endpoints. Confirm HTTP 502 for an invalid mask and HTTP 504 for a timeout.

## Group failures

- Remove `SAM3_ENDPOINT`.
- Confirm that `POST /v1/group/match` returns HTTP 503.
- Use an invalid bearer token.
- Confirm that the request returns HTTP 401 before SAM3 receives a request.
- Make SAM3 return invalid dimensions or a non-PNG mask.
- Confirm that the matcher returns HTTP 502 and does not return fake bottles.

## Backend cascade and the time budget

Plan 85 of the workbench. Read [docs/cascade.md](docs/cascade.md).

- Make a catalogue copy with both embeddings (`copy_catalog.py --embedding
  …-naflex-p512-rot5 --embedding …-naflex-p512 --no-images`). Select
  `cascade-p512-rot5` and enable `matcher.fast_answer`. Set `SIGLIP2_ENDPOINT`,
  `SAM3_ENDPOINT`, `QR_SCANNER_ENDPOINT`, and `VLM_ENDPOINT`. Read `/running` of the
  gateway first; the VLM needs about 3.5 min for a cold start.
- Confirm HTTP 200 from `/readyz`. Confirm that the gateway log shows no VLM request for it.
- Send a photo of one bottle to `POST /v1/eval/predict`. Confirm the answer and, in
  `request.json`, `decision.source` and a `stages` list with `scan_full`, `sam3_full`,
  `whole`, `crop:1`, `scan_package`, and `scan_label`.
- Send a photo whose package shows a barcode of a catalogue wine. Confirm
  `decision.source` `code_package` or `code_label`, and `decision.reason` `final`.
- Send a photo of a wine of a cluster with a rule. Confirm a stage `vlm:<cluster>`. When
  the VLM is slower than `answer_at_seconds`, confirm `decision.reason` `answer_at`, the
  stage status `cancelled`, and that the VLM stops the request
  (`vllm:num_requests_running` of `/upstream/qwen3.5-9b-nvfp4/metrics` falls to 0).
- Send the same photo to `POST /v1/match`. Confirm that it waits for the VLM, that the
  scores never increase, and that each candidate has a card.
- Run `matcher/tests/participant_test.sh` against the matcher. Confirm that each answer
  comes within 3 s from the client side.
- Stop SAM3 (or point `SAM3_ENDPOINT` to a closed port). Confirm that
  `POST /v1/eval/predict` still answers from the whole photo (`decision.source` `whole`).
