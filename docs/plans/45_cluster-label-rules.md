# 45 — Label rules of the embedding clusters

Date: 2026-09-26.
Status: approved by the owner on 2026-09-26T10:19:00+0300 and implemented on
2026-09-26. The section "Result" holds the run.
Written by drink-atlas-workspace-39 [fb59ad], also named CLUSTERS [fb59ad].
Source: the owner message of 2026-09-26T09:07:24+0300, the answers of 09:27:00, and the
answers of 10:19:00 in [owner-messages.md](../owner-messages.md).

## Goal

1. Stage 1: a VLM describes the label of each card of each cluster.
2. Stage 2: a VLM finds where the labels of one cluster differ. It writes 1 to 3
   questions with the expected answer of each card, and a plain text rule.
3. The code checks the answer of stage 2 and sets the mode of the rule: `sheet`,
   `verdict`, or `none`.
4. The pages `/clusters` and `/runs` show the rules. They do not change them.

These items are not in this plan:

- the re-rank at query time (owner answer of 09:27:00: rules only);
- an edit of a rule, or a rebuild of one rule, on the page;
- a background job of the lab server.

## Decisions of the owner

| Question | Answer |
|---|---|
| Approach | A: a command of the lab, a port of stages 1 and 2 of `svoe-vino-testset` (09:27:00) |
| Storage | `data/embeddings/<name>/cluster-rules.json`, the contract of plans 30 and 43 (09:27:00) |
| Clusters | the view `combined`, in the rule space `label` (09:27:00) |
| Re-rank | not in this plan (09:27:00) |
| Stage 1 | `qwen3.5-9b-nvfp4`, thinking off, the catalogue picture enlarged to a long side of 2048 pixels, no card data (09:07:24) |
| Stage 2 | `qwen3.5-9b-nvfp4`, the label cut of each card at 768 pixels, the card data, the stage 1 descriptions, the notes (09:07:24) |
| Q1, the image limit | The owner set `--limit-mm-per-prompt` of `qwen3.5-9b-nvfp4` to 20. The code checks the number of images against the limit and gives a meaningful error when a request fails because of it (10:19:00). |
| Q2, the thinking of stage 2 | Off, and configurable in `config.yaml`, with a comment there (10:19:00) |
| Checks | no bottle number; no feature outside the label; no year that the catalogue name does not state; the alcohol value only when no other feature differs (09:07:24) |

## Facts

Measured on 2026-09-26. The probe details are in `ResearchLog.md`, 2026-09-26.

- `qwen3.5-9b-nvfp4` runs on vLLM behind llama-swap 18081. `max_model_len` is 32,768
  tokens.
- Before the change of the owner, the service accepted 1 image in one prompt: HTTP 400,
  `At most 1 image(s) may be provided in one prompt.` After the change (about 10:30), a
  request with 3 images gets HTTP 200, and a request with 21 images gets HTTP 400 with
  `At most 20 image(s)`.
- Stage 1 probe, the 3 cards of the «Фантом» cluster: HTTP 200, 14.1 to 18.3 s, 339 to 445
  completion tokens, valid JSON. Card B read the ratio mark as `9/9`; the catalogue name
  states `50/50`. Cards A and C read no ratio.
- Stage 2 probe with one image (a montage of the 3 label cuts), before the change of the
  limit: with thinking, 2 of 2 answers reached `max_tokens` 12,000 after about 505 s and
  held reasoning alone. Without thinking: 12.5 s, valid JSON, a valid ratio question.
- The package cut of a card image has a median long side of 1,049 pixels. 76 % are under
  2,048 pixels, so the enlargement of stage 1 changes most pictures. The details of
  plan 29 send the same prompt text with at most 1,536 pixels and no enlargement.
- The label cut has a median long side of 415 pixels. 79 % are under 768 pixels.
- 43 cards of 21 clusters share their main image, byte for byte, with another card of
  their cluster.
- The watcher of plan 29 sends its detail calls to the same model, with up to 8 calls at
  the same time.

## Terms

The terms of `svoe-vino-testset/docs/plans/05_cluster-label-rules.md` apply.

- **card**: one wine of the catalogue, addressed by its slug.
- **cluster**: one cluster of the view `combined` of `clusters.json`.
- **cluster key**: the first 12 hexadecimal digits of the SHA-1 of the sorted slugs.
- **effective main image**: the `main_patched` image of a wine, else its `main` image.
- **label description**: the answer of stage 1 for one card.
- **difference sheet**: the questions of stage 2, with the expected answer of each card.
- **rule text**: the plain text rule of stage 2.
- **cluster rule**: the whole checked answer of stage 2 for one cluster.
- **mode**: `sheet`, `verdict`, or `none`.
- **note**: the text of the reviewer about one cluster, from `cluster-notes.json`.

## Step 0: current clusters

`pipeline/build_clusters.py --name gx10-siglip2-so400m-patch16-naflex-p256` builds
`clusters.json` again before the first rule run, because the artifact of 01:06 was stale.
A cluster with the same members keeps its key, so its note and its rule stay.

## Stage 1: the label description of each card

- One VLM call for each card of a cluster whose description is not current.
- The picture: the cut of the kind `package` of the effective main image, else the
  original. It goes upright, on white, as PNG, scaled UP or down to `describe_side`
  (2,048 pixels).
- The prompt: `DESCRIBE_PROMPT` of `svoe-vino-testset/scripts/cluster_rules.py`, verbatim.
  The call sends no card data.
- The request: `temperature` 0, `response_format` `json_object`, `max_tokens` 1,500,
  thinking off, timeout 300 s.
- The call goes through `pipeline/model_cache.py`. The cache stores an answer only when it
  holds a JSON object and `max_tokens` did not cut it off.
- A description is current when the SHA-256 of the sent file and the settings SHA of
  stage 1 are unchanged. The settings SHA holds the prompt, the entry, the model, the
  thinking flag, and the long side.
- An answer with `finish_reason: length` is sent once more with `repetition_penalty`
  1.15 and twice the limit. The probe checked that the service accepts the key.

## Stage 2: the rule of each cluster

- One VLM call for each cluster whose rule is not current.
- A cluster with more than 26 cards gets an error record and no call, because the
  letters are A to Z.
- A cluster with more images than `rules_max_images` (20) gets an error record and no
  call. The error names the number of images, the key, and the vlm entry.
- When the service refuses the number of images (HTTP 400, `At most N image(s) may be
  provided in one prompt`), the run stops with exit status 2. The message names the vlm
  entry, the limit of the service, the number of images of the request,
  `--limit-mm-per-prompt`, and `label_rules.rules_max_images`.
- The letters Card A, Card B, and so on follow the sorted slugs.
- The message: for each card its caption and one image, then the text. The image is the
  cut of the kind `label` of the effective main image, on white, scaled UP or down to
  `rules_max_side` (768). A card with no label cut sends its package cut with
  `CAPTION_NO_LABEL`. A card that shares its main image with another card of the cluster
  gets `CAPTION_SHARED`.
- The text: `RULES_PROMPT`, `CARD_BLOCK`, the captions, and `VINTAGE_NOTE` of
  `svoe-vino-testset/scripts/cluster_rules.py`, verbatim. `CARD_BLOCK` holds the name,
  the producer, the category, the grapes, and the alcohol value of the slug. The label
  description goes in without the key `bottle`.
- The note: `clusters.note_for` gives the exact note of the cluster key, else the note
  with the largest overlap.
- The request: `temperature` 0, `response_format` `json_object`, thinking off,
  `max_tokens` 2,500, timeout 300 s. `rules_thinking`, `rules_max_tokens`, and
  `rules_timeout_s` change it.
- The token budget: the prompt estimate MUST stay at or below `rules_context_tokens`
  minus `rules_max_tokens` minus 1,024. Else the pictures shrink by the factor 0.75, down
  to 256 pixels.
- Up to `rules_workers` calls run at the same time (2).

### The check

The code ports `check_rule` of `svoe-vino-testset/scripts/cluster_rules.py`:

| `kind` | Detected by | Effect |
|---|---|---|
| `serial` | «serial», «batch», «lot», «bottle number», «Бут. №», «Тираж», «№» | never valid |
| `bottle` | the glass, the liquid, «through the», the capsule, the cork, the shape or the colour of the bottle | never valid |
| `alcohol` | «alcohol», «abv», «% vol», or every answer is a percentage | valid only when no `feature` or `vintage` question is valid |
| `vintage` | «vintage», «harvest», «урож», «year», or every answer is a year | a year stays only when the name or the slug of the card states it; the vintage variants of plan 06 of `svoe-vino-testset` apply |
| `feature` | every other question | normal |

- A question is valid when its text is not empty, at least two cards hold two different
  non-null answers, and its kind is not `serial` or `bottle`.
- The mode is `sheet` when a question is valid. Else it is `verdict` when the rule text
  is not empty and names no `bottle` feature. Else it is `none`.
- The code adds `evidence` to each question: for each card with a non-null answer, the
  SHA-256 of the file that stage 2 sent for that card (plan 30).

### Current rules

- A rule is current when its `inputs_sha` is unchanged. `inputs_sha` holds the slugs,
  the card data, the SHA-256 of the stage 1 picture and of the stage 2 picture of each
  card, the SHA of each description, the note, the settings SHA of stage 2, and the
  vintage note when it applies. The settings SHA holds the prompts, the captions, the
  entry, the model, the thinking flag, and the long side.
- A rule also stores `input_hash`, the input hash of `clusters.json` at the time of the
  build. The page compares it (plan 30).
- A run after a cluster build writes the new `input_hash` into each rule whose
  `inputs_sha` is unchanged. This makes no VLM call.

## The file `cluster-rules.json`

```json
{
  "version": 1,
  "note": "Label descriptions and cluster rules of one embedding. …",
  "updated_at": "2026-09-26T12:00:00+0300",
  "settings": {"vlm": "qwen3.5-9b-nvfp4", "rules_vlm": "qwen3.5-9b-nvfp4", "describe_sha": "…", "rules_sha": "…"},
  "prompts": {"describe": "…", "rules": "…", "card": "…", "captions": ["…"], "vintage": "…"},
  "cards": {"<slug>": {"source_sha256": "…", "picture_sha256": "…", "picture_kind": "package",
                       "sent_size": [541, 2048], "settings_sha": "…", "description": {},
                       "error": null, "ms": 14100, "cached": false}},
  "spaces": {"label": {"<cluster key>": {
    "key": "…", "slugs": ["…"], "letters": {"A": "<slug>"}, "input_hash": "…",
    "inputs_sha": "…", "note": "…", "built_at": "…", "vlm": "qwen3.5-9b-nvfp4",
    "prompt": "<the text of the request>", "raw_reply": "<the content of the answer>",
    "mode": "sheet", "differences": "…",
    "questions": [{"id": "q1", "question": "…", "kind": "feature", "valid": true,
                   "answers": {"<slug>": "30/70"}, "evidence": {"<slug>": ["<sha256>"]}}],
    "rule": "…", "indistinguishable": [], "answer": {}, "error": null, "ms": 0, "usage": {}}}}
}
```

- `clusters.load_rules` reads `spaces` alone, so the key `cards` does not change it.
- The write is atomic. The lock file `cluster-rules.json.lock` keeps two runs apart.
- A rule of a cluster that no longer exists stays in the file.

## The command

```bash
python3 pipeline/build_label_rules.py --name <embedding>
python3 pipeline/build_label_rules.py --name <embedding> --stage describe
python3 pipeline/build_label_rules.py --name <embedding> --cluster <slug>
python3 pipeline/build_label_rules.py --name <embedding> --dry-run
python3 pipeline/build_label_rules.py --name <embedding> --force
```

- `--stage` is `describe`, `rules`, or `all` (the default).
- `--cluster <slug>` builds the one cluster that holds that card.
- `--dry-run` lists the work of a run, and makes no call and no write.
- `--force` builds again also a current description or rule.
- The command stops when `clusters.json` does not exist.
- The command does only the work that is not current. A stopped run resumes.
- The command prints a JSON summary. Exit status 0: every record is valid; 1: a record
  holds an error; 2: the run did not start or stopped.

## The configuration

The block `label_rules:` of `config.yaml` holds 14 keys, each with a comment in the file:
`vlm`, `thinking`, `describe_side`, `describe_max_tokens`, `describe_workers`,
`timeout_s`, `rules_vlm`, `rules_thinking`, `rules_max_side`, `rules_max_images`,
`rules_max_tokens`, `rules_context_tokens`, `rules_workers`, and `rules_timeout_s`.

- `vlm` and `rules_vlm` name entries of the key `vlm`. `rules_vlm` null takes `vlm`.
- An unknown key, a value of a wrong type, or `rules_context_tokens` not above
  `rules_max_tokens` + 1,024 stops the command.
- The name is not `cluster_rules`, because `scripts/cluster_rules.py` reads that key.

## The pages

- `pipeline/clusters.py`, `detail`: the views `combined` and `label` show the rules of the
  space `label` (`RULE_SPACE_OF`). The view `full` shows the rules of the space `full`.
  Before, the view `combined` looked for a space `combined`, which `load_rules` never
  gives.
- The rule of a cluster is `stale` on the page when its `input_hash` differs from the
  artifact, or when it stored a `note` that differs from the present note of the cluster.
- `pipeline/pages/clusters.html` does not change. `ruleHtml` shows the rule as JSON,
  without `prompt` and `raw_reply`.
- `/runs` does not change. `GET /api/run-clusters` reads `mode` and `questions` of the
  space `label`, and the VLM box shows the questions whose `valid` is true.

## Code

| File | Change |
|---|---|
| `pipeline/label_rules.py` | new: the configuration, the prompts, the VLM call, both stages, the check, the file, the run |
| `pipeline/build_label_rules.py` | new: the command |
| `pipeline/clusters.py` | `RULE_SPACE_OF`; `detail`: the rule space of a view; the stale rule |
| `pipeline/cluster_routes.py` | the note route starts the rule rebuild (change 7) |
| `pipeline/pages/clusters.html` | the note save polls the rule and swaps its block (change 7) |
| `tests/test_cluster_routes.py` | the note route starts the rebuild; a failure to start keeps the note |
| `config.yaml` | the block `label_rules:` with its comments |
| `tests/test_label_rules.py` | new, 19 tests: the prompts equal the prompts of `scripts/cluster_rules.py`; the check; the image limit; the cache; the pictures; the configuration |
| `tests/test_build_label_rules.py` | new, 14 tests: the run with a fake VLM, and the wait for a running build |
| `README.md`, `COMMANDS.md`, `SMOKE_TESTS.md` (LR1 to LR9), `ChangeLog.md`, `ResearchLog.md` | own hunks |

`scripts/cluster_rules.py` does not change. Plan 43 keeps it for its tests.

## Changes during the implementation

1. The module names are `label_rules.py` and `build_label_rules.py`, not
   `cluster_rules.py` and `build_cluster_rules.py`. The tests put `pipeline/` and
   `scripts/` on the path, so a second module `cluster_rules` could hide the first.
2. The owner raised the image limit of the service to 20 (Q1). So stage 2 sends one
   image for each card, as `svoe-vino-testset` does, and the prompt stays verbatim. The
   montage of the draft is not implemented.
3. Stage 2 runs without thinking (Q2). `rules_thinking` switches it on.
4. A `repetition_penalty` retry doubles `max_tokens`. For stage 2 the retry stays inside
   the context of the model.
5. `docs/API.md` does not change. It does not describe `GET /api/clusters/<name>`, and
   `GET /api/run-clusters` keeps its answer.
6. Step 0 at 10:33:43: 163 clusters with 382 wines in the view `combined` (168 with 393
   before). 161 cluster keys stayed, the «Фантом» key `a29e59138ed4` among them. A copy
   of the file of 01:06 is `work/clusters.naflex-p256.before-plan45.json`.
7. A note change rebuilds the rule (owner message of 2026-09-26T11:08:00+0300, answer
   "Background rebuild" of 11:11:00). `POST /api/clusters/<name>/note` writes the note and
   starts `build_label_rules.py --cluster <first slug> --wait` as a separate process, as
   an embedding build does; its output goes to `data/embeddings/<name>/label-rules.log`.
   The answer holds `rule_rebuild`: `{started, pid, log}`, or `{started: false, error}`;
   a failure to start keeps the note. `--wait` waits for a running rule build (a try
   every 2 s, at most 1 h). The run now reads its inputs after it holds the lock. The page
   shows «Saved · rebuilding the rule…», polls the detail every 3 s for at most 5 min, and
   swaps in only the rule block of that cluster when the rule is current («Rule rebuilt»).

## The run

1. A row in `/Users/ashmelev/Admin/GPU_TASKS.md` comes first.
2. Step 0: the cluster build.
3. A smoke run of the «Фантом» cluster: `--cluster
   vinodelnya-vedernikov-fantom-5050-krasnostop-zolotovskiy-krasnoe-suhoe-145`.
4. The full run.
5. A check of `/clusters` in the light and the dark theme.
6. `ResearchLog.md`: the modes, the valid questions by kind, the errors, and the times.

## Risks

- The quality of the rules of the 9B model is not measured. In `svoe-vino-testset` the
  rules of `qwen3.8-max` replaced the first rules of `qwen3.5-9b` before a benchmark.
  This plan has no benchmark, because it has no re-rank.
- Small print. The probe read `9/9` for the ratio mark of «Фантом 50/50».
- The shared service. The watcher of plan 29 and this command wait for each other.
- A loop of the model: an answer can reach `max_tokens`.

## Result

Measured on 2026-09-26. Details: `ResearchLog.md`, 2026-09-26.

- The full run of 10:35 to 11:16 (2,511 s): 382 descriptions and 163 rules, 0 errors.
  Modes: 139 `sheet`, 24 `verdict`, 0 `none`. 223 valid `feature` questions; the check
  struck 27 `vintage`, 9 `alcohol`, and 17 `feature` questions.
- One call: stage 1 median 15.6 s, stage 2 median 8.9 s.
- The note rebuild on the page (11:15:48): the process waited for the full run, then
  built the «Фантом» rule in 12.5 s; the page showed «Rule rebuilt» after 67 s. The new
  rule asks for the ratio and for the colour of the small box, as the new note asks.
  The colour of card B is wrong: «dark blue» for a dark burgundy box.
- Weak `verdict` rules exist, for example «All three cards have identical labels…», as in
  `svoe-vino-testset` (plan 06 there, Q2).
