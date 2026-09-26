# Plan 49: a probe after a VLM timeout, and the dialog of the watcher

Date: 2026-09-26

Source: owner message of 2026-09-26T10:33:00+0300, and the answers of 15:18:00 and
15:35:00 (session drink-atlas-workspace-0d [ab062e]).

## 1. The defect

On 2026-09-26 the pill of `/dataset` showed
`VLM waiting: no answer from http://192.168.86.14:1808` for many hours.

- The service was healthy. Other requests got HTTP 200 in seconds.
- One detail request timed out on each attempt: the image
  `a902e43a5f7768f18c8faf50496ef5e4522b9facb312613e1f4cbc0b3893b236` (the `package`
  prompt, `bottle`). It timed out 45 times from 2026-09-25T23:02Z to 2026-09-26T07:38Z.
- vLLM decoded this one request for the full 300 s at about 22 tokens/s. That is about
  6,600 tokens. A normal answer of this image has about 380 tokens. The same request in
  another batch ended in 17 s and 21 s with a valid answer. So the long output depends on
  the batch. The text of the long output was not seen.
- `max_tokens` is 8192. At 22 tokens/s the service needs about 370 s to reach it. The
  client timeout `TIMEOUT_SECONDS` is 300 s. So the request never ended with
  `finish_reason` `length`, which counts against the image. It always ended as a timeout.
- `post` counted each timeout as a failure of the service (`counted=False`). The image
  never reached `max_attempts`. Each timeout also stopped all new requests for the
  backoff (30 s, doubled up to 600 s).
- The pill cut the error at 40 characters. The port `18081` showed as `1808`.

The watcher itself stored a valid answer at 2026-09-26T07:39:21Z, in a batch with other
requests.

## 2. The decisions of the owner

| Question | Answer |
|---|---|
| How is the stuck image fixed now? | A one-off run with the code of the watcher. |
| Which self-recovery? | A probe after a timeout. |
| Which probe? | A chat request of 1 token to the same model. Not `GET /v1/models`. |
| What does the amber pill show? | The full error, with no cut. |
| What does the dialog show? | The state and the full error, the images of the calls that run, the backoff and the next try, the last 30 lines of the watcher log. |

Options that the owner did not choose:

- Streaming with an idle timeout. More code: the answer is built from chunks, and the
  record of `model_cache` changes.
- A lower `max_tokens` of the detail. It depends on the decode speed, and a real long
  label can be cut.
- `GET /v1/models` as the probe. llama-swap answers it from its own configuration. It
  answers also when vLLM behind it hangs or loads (a cold start takes about 3.5 min).

## 3. The probe

- `post` marks a read timeout (`TimeoutError`: the service took the request and sent no
  answer in time) with `timed_out`. A connect timeout (`URLError`) is not a read
  timeout. It stays a failure of the service with no probe.
- After a read timeout, `ask` sends the probe: the text `ping`, `max_tokens` 1,
  `temperature` 0, thinking off, timeout `PROBE_TIMEOUT_SECONDS` (30 s). The probe sends
  no image and does not use `model_cache`.
- HTTP 200 from the probe: the model serves. The timeout counts against the image
  (`counted=True`). No backoff starts. After `max_attempts` (3) such timeouts the image
  is a failed image, as for an answer that fails the schema.
- Any other result of the probe: the timeout stays a failure of the service
  (`counted=False`), with the backoff, as before.
- The error text names the timeout, the full endpoint, and the time of the probe.

Risk: a service that serves short requests but is too slow for each image request makes
healthy images fail. A start of the watcher with `--retry-failed` sends them again.

## 4. The state of the watcher

`work/describe_images.status.json` gets these keys:

- `endpoint` (the chat URL of the `vlm` entry), `timeout_seconds`, `workers`.
- `running`: the calls that run, each with `sha256`, `stage`, and `started_at`.
- In the state `waiting`: `waiting_since` (the first failure of the service after the
  last success), `backoff_seconds` (for a failure of the service), `retry_at`, and
  `error_sha256` and `error_stage` (the image of the failure).

`GET /api/image-description-status` adds to each call of `running` and to `error_image`
the wine slug, the URL of the file that the VLM gets, the attempts and the last error of
the row, and the age of the call in seconds. `retry_in_seconds` is the time to the next
try. With `log=<N>` (1 to 200) the answer also holds `log_file` and `log`, the last `N`
lines of `work/describe_images.log`. The read of the log starts at most 256 KiB before
its end.

## 5. The page

- The pill shows the full error. A long text wraps; it is never cut.
- A click on the pill opens the dialog `VLM watcher`. The button `N details failed`
  keeps its own dialog.
- While the dialog is open, each poll (5 s) asks `?log=30` and draws the dialog again.
- A click on a thumbnail of the dialog opens the file in the image preview.

## 6. Tests

- `tests/test_describe_images.py`: a read timeout with a probe that answers counts; a
  read timeout with a probe that fails does not count and starts the backoff; a connect
  timeout sends no probe; the probe request; the new keys of the state.
- `tests/test_image_descriptions.py`: `watcher_status` adds the views of the calls; the
  log tail.
- `tests/test_lab_server.py`: the parameter `log`.
