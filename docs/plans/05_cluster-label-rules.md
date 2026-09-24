# 05 — Label rules for the catalogue clusters

Date: 2026-09-23.
Status: approved and implemented on 2026-09-23. The project owner selected the four
decisions below. The benchmark result is in the section "Result".

## Goal

1. A VLM describes the label of each card of each catalogue cluster.
2. A VLM finds where the labels of one cluster differ. It writes a rule that tells the
   cards apart.
3. The reviewer adds a note to a cluster. The note goes into the rule.
4. The page `/clusters` of the review tool shows the descriptions, the rule, and the
   note of each cluster.
5. A re-rank step asks the VLM to read the query label with the rule. The step acts
   only when the top candidates belong to one cluster.
6. A benchmark measures the re-rank.

## Decisions of the owner

| Question | Options | Decision |
|---|---|---|
| Rule format and query decision | a question sheet; a rule text and a VLM verdict; the sheet with a verdict fallback | the sheet with a verdict fallback |
| Thinking mode of the VLM | off everywhere; on for the rule stage only; on everywhere | off everywhere |
| Leakage of the `confusion` signal | report both; clusters without `confusion` only; all clusters only | report both |
| The cluster file | rebuild with the indexes of 2026-09-23; keep the file of 2026-09-22 | rebuild |

## Facts

The measurements are in `ResearchLog.md`, 2026-09-23.

- The VLM is `qwen3.5-9b` on the llama-swap gateway of gx10,
  `http://192.168.86.14:18081/v1/chat/completions`. It is llama.cpp with the
  Q4_K_M weights, 1 slot, and a context of 32,768 tokens. It is pinned and always
  resident. The enrichment worker of `drink-atlas-enrichment` uses the same slot.
- The model is a thinking model. One label description took 28.3 s with thinking,
  and 3.0 s with `chat_template_kwargs.enable_thinking: false`.
- The gateway refuses a WebP data URL with HTTP 400. A PNG data URL works.
- The catalogue photo of «Фантом 30/70» has 264 x 1000 pixels. The ratio box is
  about 15 pixels wide. Both probes read wrong numbers in the box. A rule for such a
  cluster MUST therefore come from the card data and from the note of the reviewer.
- The best run is `2026-09-23T121203Z-svm-label-gw-difference-alpha-patches`:
  R@1 0.8156, 295 misses of 1,600 positives. In 179 misses the true card is in the
  cluster of the answer. This is the ceiling of the re-rank.
- 48 links of the cluster file hold the `confusion` signal alone. That signal comes
  from match runs over the same test photos. 60 of the 179 misses need such a link.
- With a window of 5, the re-rank acts on about 906 of 2,181 queries.

## Terms

- **card**: one card of the catalogue, addressed by its slug.
- **cluster**: one group of cards of `dataset/catalog-clusters.json`.
- **cluster key**: the SHA-1 of the sorted slugs of a cluster, first 12 hex digits.
- **label description**: the answer of stage 1 for one card.
- **difference sheet**: the questions of stage 2, with the expected answer of each
  card.
- **rule text**: the plain text rule of stage 2.
- **cluster rule**: the whole answer of stage 2 for one cluster.
- **mode**: `sheet`, `verdict`, or `none`. It states how the re-rank uses the cluster
  rule.
- **note**: the free text of the reviewer about one cluster.
- **window**: the first 5 positions of the base list.

## Step 0: the cluster file

- `config.yaml` names the indexes `gateway-6e12e149fe` (photo) and
  `gateway-b57810da3d` (label). The best run used these two indexes.
- `scripts/10_clusters.py` builds the file again. The runs of the `confusion` signal
  stay the same.

## Stage 1: the label descriptions

- One VLM call for each card of a cluster.
- The input is the catalogue picture of the review tool, `common.catalogue_picture`:
  the crop, then the patch, then the photo of the record. The picture is sent as PNG,
  scaled to a long side of 2048 pixels, UP or down. See item 2 of "Changes during the
  implementation".
- The call sends NO card data. The description holds what the model sees, and
  nothing else.
- The prompt asks for JSON: the texts with their place, the numbers with their place,
  the vintage, the colours, the design, the marks, and the bottle. A text that is too
  small to read MUST be given as `unreadable`.
- `response_format` is `json_object`. Thinking is off. `temperature` is 0.
- A description is current when the SHA-256 of the picture and the SHA-256 of the
  prompt are unchanged.

## Stage 2: the cluster rule

- One VLM call for each cluster.
- The input: the pictures of all cards, each marked with a letter; for each card the
  name, the producer, the category, the grapes, the alcohol value of the slug, and the
  label description; the note of the reviewer.
- The long side of each picture is at most 768 pixels. The call MUST stay inside the
  context. A cluster that does not fit is sent with smaller pictures.
- The prompt asks for JSON:
  - `differences`: a short text about where the labels differ;
  - `questions`: 1 to 3 questions about the label, each with the expected answer of
    each card, or null when the card does not show the feature;
  - `rule`: a plain text rule;
  - `indistinguishable`: the groups of cards that no visible feature separates.
- The note of the reviewer is correct. The card data is correct. The prompt states both.
- The alcohol value can change between two vintages of one wine. The prompt allows it
  only when no other feature differs.
- The code checks the answer:
  - A question is valid when at least two cards hold two different non-null answers.
  - The mode is `sheet` when at least one question is valid.
  - Else the mode is `verdict` when the rule text is not empty.
  - Else the mode is `none`.
- A cluster rule is current when the slugs, the label descriptions, the card data,
  the note, and the prompt are unchanged. The file keeps the SHA-256 of these inputs.

## The files

Both files are in `svoe-vino-testset/dataset/`, next to `catalog-clusters.json`.

| File | Writer | Content |
|---|---|---|
| `catalog-cluster-notes.json` | the review tool only | the notes of the reviewer |
| `catalog-cluster-rules.json` | `scripts/11_cluster_rules.py` and the review tool | the label descriptions and the cluster rules |

- A note keeps the slugs of its cluster at the time of writing. A note belongs to the
  current cluster that shares the most slugs with it. So a note survives a new build
  of the clusters. The page states when the slugs changed.
- The rules file keeps each cluster rule by its cluster key. A rule of a cluster that no
  longer exists stays in the file and is not shown.
- The label descriptions are kept by slug. A new build of the clusters reuses them.
- Each write is atomic. A lock file stops two writers of the rules file at the same
  time.

## The page `/clusters`

- `GET /api/clusters` adds three fields to each cluster: `note`, `rule`, and the
  status of the rule. It adds the label description to each card record.
- The status of a rule is `none`, `error`, `stale`, or `current`.
- `POST /api/cluster-note` stores or clears the note of one cluster. Body:
  `{slugs, text}`. An empty text clears the note.
- `POST /api/cluster-rule` builds the rule of one cluster again. Body: `{slug}`. It
  describes the cards that have no current description first. It takes about 5 to 30
  seconds.
- Each cluster block shows the note editor, the mode, the difference sheet as a table,
  the rule text, and the button `Rebuild rule`. Each card shows its description.
- The page follows the system colour scheme.

## The re-rank

A new pipeline kind `cluster_rules` in `svoe-vino-matcher` wraps a base pipeline, as
the kind `difference` does.

- The base is `difference-ensemble-gateway-photo-label` of `config.label.yaml`.
- The trigger: the rank-1 card is in a cluster, and at least one other card of that
  cluster is in the window.
- The input of the VLM is the SAM3 label crop of the query, from the crop cache of
  `gateway-siglip2-label`, flattened on white. A query with no crop sends the whole
  picture. The picture is scaled to a long side of 1536 pixels, UP or down.
- Mode `sheet`: the VLM answers the questions of the sheet. Each question lists its
  options: the expected answers of the cards, `other`, and `not visible`. The code
  compares the answers with the expected answers:
  - an equal answer gives +1 to the card;
  - a different answer gives -1 to the card;
  - a null expected answer, or the answer `not visible`, gives 0.
- Mode `verdict`: the VLM gets the rule text and the description of each card of the
  cluster, with a letter. It answers one letter, or `unsure`.
- The VLM always sees all cards of the cluster, not only the cards of the window. The
  answer therefore does not depend on the window, and a replay can change the window
  without a new call.
- Only the cards of the cluster inside the window change their order. A card of the
  window with a strictly better score moves up. A tie keeps the base order. Every other
  candidate keeps its position, and every position keeps its score.
- Fail-safe: a VLM failure, an answer that is not JSON, a cluster of mode `none`, or no
  winner returns the base list. A VLM failure MUST NOT fail the request.
- A cache keeps each VLM answer. The key is the SHA-256 of the picture and of the
  request settings. A second run therefore makes no call.
- `explain=1` gives the cluster, the mode, the answers, the scores, and the base rank.

## The benchmark

- One `match_run.py` run of 2,181 photos, backend `svm-label-gw-cluster-rules`, one
  request at a time, against the Mac server on 127.0.0.1:8164.
- The backend asks for `explain=1`. `match_backends.parse_answer` keeps the field.
- A row in `/Users/ashmelev/Admin/GPU_TASKS.md` comes first.
- The report:
  - R@1, R@5, and MRR against the base run
    `2026-09-23T121203Z-svm-label-gw-difference-alpha-patches`, with
    `scripts/compare_runs.py`;
  - the wins, the losses, and the exact McNemar test;
  - the same numbers by mode;
  - the same numbers over the clusters that exist without the `confusion` signal. A
    replay of the recorded answers gives this set. It needs no new call;
  - the 17 positive «Фантом» photos;
  - the 581 negative photos;
  - the base score gap of each win and of each loss;
  - the median latency and the number of VLM calls.

## Files

| File | Change |
|---|---|
| `svoe-vino-testset/config.yaml` | the two new indexes; the block `cluster_rules` |
| `svoe-vino-testset/scripts/cluster_rules.py` | new: the prompts, the VLM client, stage 1, stage 2, the files |
| `svoe-vino-testset/scripts/11_cluster_rules.py` | new: the command line of the two stages |
| `svoe-vino-testset/scripts/review_server.py` | the fields of `/api/clusters`, the two POST routes, the page |
| `svoe-vino-testset/scripts/match_backends.py` | keep `explain` |
| `svoe-vino-testset/scripts/cluster_rules_report.py` | new: the replay and the report |
| `svoe-vino-testset/backends.yaml` | new backend `svm-label-gw-cluster-rules` |
| `svoe-vino-matcher/svm/vlm.py` | new: the chat client with the answer cache |
| `svoe-vino-matcher/svm/cluster_rules.py` | new: the trigger, the scores, the order |
| `svoe-vino-matcher/svm/pipelines/cluster_rules.py` | new: the wrapper kind |
| `svoe-vino-matcher/config.label.yaml` | new pipeline `cluster-rules-difference-gateway` |
| `svoe-vino-matcher/tests/test_cluster_rules.py` | new: the unit tests of the scores and the order |
| the documents of both projects | README, API, OpenAPI, SMOKE_TESTS, ChangeLog, ResearchLog |

## Risks

- The VLM reads a small text wrong. The probe read wrong numbers in the «Фантом» box.
  A wrong answer at query time moves the wrong card up. The measurement counts these
  losses by base score gap.
- The VLM answers `other` or `not visible` often. The re-rank then keeps the base
  order. This costs no new error.
- Position bias in mode `verdict`. The letters follow the sorted slugs, not the base
  order.
- Latency. A query that triggers the re-rank waits about 3 to 8 seconds for the VLM.
  The benchmark measures it.
- The shared slot. The enrichment worker and this job wait for each other.

## Changes during the implementation

The probes are in `ResearchLog.md`, 2026-09-23.

1. Step 0 changed nothing in the clusters. The build with the indexes of 2026-09-23
   holds the same 255 clusters and the same links as the build of 2026-09-22.
2. Stage 1 scales the picture to a long side of 2048 pixels, UP or down, and not to at
   most 1536. At 312 x 1000 pixels the model read «урож. 2024» as 2021 and «ФАНТОМ» as
   PHANTOM. At 2048 it read both right. The cost is about 19 s for one card.
3. The prompt of stage 2 got four rules: compare the wine names and the grape names
   first; never use a bottle number; the descriptions can hold errors; two texts that
   differ only by their alphabet are the same text. The first probe made a false
   question from PHANTOM, and a question from «Бут. №».
4. The code enforces two rules. Each question gets a `kind`: `serial`, `alcohol`, or
   `feature`. A `serial` question is never valid. An `alcohol` question is valid only
   when no `feature` question is valid.
5. A rule has a fifth status, `error`: the last build failed.
6. An answer that reaches `max_tokens` is asked once more with `repeat_penalty` 1.15 and
   `max_tokens` 3000. One description of the batch looped for 45 s.
7. `Rebuild rule` saves an unsaved note first.
8. The query side scales the crop to a long side of 1536 pixels, UP or down, for the
   reason of item 2.
9. The owner changed two decisions on 2026-09-23, after the first rules:
   - Stage 2 uses `qwen3.8-max` of the QwenCloud Token Plan, with thinking, 4 requests
     at a time, because it runs once. Stage 1 and the re-rank keep the local
     `qwen3.5-9b` with thinking off. The owner named the local model «qwen3.6-9B»; the
     gateway holds no such model, so the local 9B model stays.
   - The prompt of stage 2 keeps only major differences: the vintage year, the grapes,
     a kosher mark, the wine name or the line name, the colour and the sugar level of
     the wine, a blend ratio, a reserve or edition mark, and the volume. A design, a
     colour shade, a background, a font, a pattern or a capsule colour is not used
     unless the note of the reviewer names it.
   `qwen3.8-max` did not read small print better than the local model: at 2048 pixels
   it read «урож. 2024» as 2021, also with thinking (94 s), where `qwen3.5-9b` read 2024.
   Stage 1 therefore stays local.
10. A mark that only some cards carry, such as a kosher mark, gets a yes/no question
    with "yes" or "no" for each card. The first rules of `qwen3.8-max` gave such a mark
    to one card and null to the others, and the check «two different non-null answers»
    struck every kosher question. Every rule was built again.

## Result

Measured on 2026-09-24. Run
`runs/2026-09-23T224548Z-svm-label-gw-cluster-rules-qwen38max-rules-v2`, 2,181 photos,
156 rules of `qwen3.8-max` (132 `sheet`, 24 `verdict`), the local `qwen3.5-9b` at query
time, against the base run `2026-09-23T121203Z-svm-label-gw-difference-alpha-patches`.
The report is `cluster-rules-report.md` of the run.

| Metric | Base | Re-rank |
|---|---:|---:|
| R@1 of 1,600 positives | 0.8156 | 0.8313 |
| MRR | 0.8833 | 0.8929 |
| R@5 | 0.9656 | 0.9656 |
| Negatives rejected (581) | 0.8262 | 0.8399 |

- Positives: 47 wins, 22 losses, exact McNemar p 0.004. Negatives: 11 wins, 3 losses,
  p 0.057.
- The step acted on 906 of 2,181 photos and changed the order of 110. Mode `sheet`: 811
  photos, 47 wins and 18 losses over both labels; mode `verdict`: 95 photos, 11 wins and
  7 losses. One VLM call failed.
- Without the clusters that only the `confusion` signal joins (replay): R@1 0.8244,
  27 wins, 13 losses, p 0.038. This is the number that the test photos did not shape.
- The post hoc score («an answer that no card expects gives no evidence»): 45 wins and
  20 losses, p 0.003; without the `confusion` clusters 25 and 11, p 0.029. It does not
  change the result.
- «Фантом»: 4 of 17 positive photos right in the base, 10 with the rule of the note.
- The base score gap of a change: below 0.02 below rank 1, 44 wins and 13 losses; at
  0.05 or more, 1 win and 5 losses.
- Latency: median 3,757 ms where the step acted, 283 ms elsewhere; 77.6 % of the photos
  within the 3,000 ms SLA (97.9 % for the base). The gx10 GPU stood at 95 % from other
  jobs, so a VLM call took 5.4 s (median) instead of about 2.4 s on a quieter host.

The two main causes of the losses:

1. A vintage that only the catalogue photo shows. c032 holds «Аристов. Кюве Александр.
   Блан Де Блан» (18 months, the photo shows 2022) and «... Blanc de Blancs 36» (36
   months, 2021). Four positive photos of the first card show 2021, so the rule moved
   them to the second card. The months of ageing separate the two cards, and the VLM
   answered `not visible` for them. A year that the card data does not state is not a
   stable feature of a card: the next bottle can carry the next vintage.
2. A «no» for a mark that the VLM does not see. c246: the positive photo of «Совиньон
   Блан. Авторская технология» got «no» for «АВТОРСКАЯ ТЕХНОЛОГИЯ».

Candidate changes, each chosen after this run and therefore post hoc, to be measured
on one half of the wines and reported on the other half:

- use a vintage year only when the name or the slug of the card states it;
- in a yes/no question, count only «yes» as evidence;
- a margin guard near 0.05, as `group.max_gap` of the kind `difference`.

## Later

- A margin guard, as in `docs/plans/02_sibling-difference-rerank.md` of
  `svoe-vino-matcher`, chosen on one half of the wines and checked on the other half.
- The verdict fallback also for a query in mode `sheet` when every answer is
  `not visible`.
