# Plan 93: the VLM of the matcher and of the lab on the QwenCloud Token Plan

Date: 2026-09-30. Session: drink-atlas-workspace-5c.

## Source

- Owner message of about 2026-09-30T00:20+0100: switch the matcher from
  `qwen3.5-9b-nvfp4` to the QwenCloud Token Plan; find a cheap vision model that is better
  than qwen3.5; start to use it; compare the performance.
- Owner message of about 2026-09-30T00:35+0100: the README of each changed subproject
  MUST state how to configure the VLM. Work only in `svoe-vino-lab`.
- Owner answers of about 2026-09-30T16:00+0300:
  1. Comparison: replay the recorded VLM calls.
  2. Models: `qwen3.8-flash`, `deepseek-v4.1-flash`, `qwen3.8-max`.
  3. The fast path of `POST /v1/eval/predict`: decide after the data.
  4. Scope: the matcher and the workbench lab.

## Facts before the work

Read `../matcher/ResearchLog.md`, entry "QwenCloud Token Plan as the VLM of the re-rank:
first probe, 2026-09-30".

- Only `qwen3.8-flash`, `qwen3.8-max`, and `deepseek-v4.1-flash` of the Token Plan read
  an image.
- A cloud call of the matcher size takes 2.5 to 8 s. The gx10 call takes about 0.7 s.
- `deepseek-v4.1-flash` refuses `response_format` `json_schema`. It accepts
  `json_object`.
- The matcher sent no `Authorization` header and put the thinking switch into
  `chat_template_kwargs` alone.
- The lab already has the keys `thinking_field` and `key` in each entry of `vlm` of
  `config.yaml` (`pipeline/vlm_config.py`), and the entries `qwencloud-qwen3.8-max` and
  `qwencloud-qwen3.8-flash`.

## Steps

1. Matcher code: the `rerank` keys `thinking_field` (`chat_template_kwargs` |
   `top_level`, default `chat_template_kwargs`) and `key` (an exact `{env:NAME}`
   reference). The same names as in the lab. The defaults keep the present request.
   Tests: `matcher/tests/test_rerank_vlm.py`.
2. Recording (`work/token-plan-vlm-20260930/record.py`): the matcher cascade in process,
   `POST /v1/match` mode (no cut), the frozen catalogue of
   `work/performance-20260930/catalog`, the test set `my` (1,853 images) and the 84 frozen
   official queries. The VLM stage is a stub that saves the picture and the rule. A case
   is kept when the VLM answer decides the order of the window of the final answer.
3. Replay (`work/token-plan-vlm-20260930/replay.py`): each case to
   `qwen3.5-9b-nvfp4` (baseline), `qwen3.8-flash`, `deepseek-v4.1-flash`, and
   `qwen3.8-max`, with the payload of `matcher/rerank.py`. The prompts stay as they are.
   `deepseek-v4.1-flash` gets `json_object`.
4. Metrics: Top-1 right on the positive rows of the cases, false matches on the negative
   rows, invalid answers and errors, latency p50/p90/p95, and the calls that end before
   2.9 s from the request start (the recorded VLM start plus the latency). The R@1 of
   the whole set `my` with the case answers replaced.
5. The owner selects the model and the fast path with the numbers.
6. Switch: `matcher/config.yaml` (the `rerank` block) and the lab `config.yaml` (the
   `vlm:` values of `rerank-options`, `cluster_rules`, `image_description`). README of the
   matcher and of the workbench: the configuration of the VLM.

## Limits

- A replay isolates the model. It does not measure the queue effects of a real run.
- The cloud calls of the replay run with 4 workers. The latency can differ from one call
  at a time.
- The quota cost of each model on the Token Plan is not known.
- The gx10 prod deployment and `<workspace>/deploy/` stay unchanged: the owner limited
  the work to `svoe-vino-lab`. The prod switch needs the key in the env file of gx10.

## Result (2026-09-30)

- Steps 1 to 4 are done. The recording found 596 deciding re-rank cases on 1,937 images.
  The numbers are in `../matcher/ResearchLog.md`, entry "QwenCloud Token Plan as the VLM
  of the re-rank: replay of 596 cases".
- No Token Plan model was better than `qwen3.5-9b-nvfp4`: 409 of 544 right; `qwen3.8-flash`
  410, `qwen3.8-max` 409, `deepseek-v4.1-flash` 401. The cloud medians were 5.7 s, 7.7 s,
  and 2.2 s against 1.2 s.
- The PNG upload was slow: the matcher got `rerank.format: jpg` (JPEG quality 90). JPEG did
  not change the accuracy of `qwen3.5-9b-nvfp4` (407 against 409).
- Step 5: the owner kept `qwen3.5-9b-nvfp4` for the matcher and for the lab (about
  18:49+0300). Step 6 is thus limited to the README sections. `matcher/config.yaml` and
  the lab `config.yaml` are unchanged.
