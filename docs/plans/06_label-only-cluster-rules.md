# 06 — Label-only rules for the catalogue clusters

Date: 2026-09-24.
Status: approved and implemented on 2026-09-24. The benchmark result is in the section
"Result".

This plan changes stage 2 of `docs/plans/05_cluster-label-rules.md`. The terms of plan
05 are the terms of this plan.

## Goal

1. Stage 2 uses only features that are printed on the label.
2. Stage 2 uses a vintage year only when the card data states it.

## Why

- Some catalogue pictures are drawings, not photos. In a drawing, only the label is
  drawn correctly. The project owner stated this on 2026-09-24.
- The re-rank sends the label crop of the query on white. It cannot see the glass, the
  liquid, the capsule, or the shape of the bottle.
- 5 valid questions of the rules of 2026-09-23 asked for the colour of the wine through
  the glass: c006, c046, c089, c111, and c116. 45 photos of the run
  `2026-09-23T224548Z-svm-label-gw-cluster-rules-qwen38max-rules-v2` used one of them.
  The VLM answered `not visible` for 29 of them. A replay without these questions
  changes no rank-1 card.
- The vintage answer differed from the expected year in 59 % of the answers
  (`ResearchLog.md`, 2026-09-24). Only 17 of the 146 expected years were in the name
  or the slug of the card. A replay without the vintage questions gave R@1 0.8375
  against 0.8313, with 14 losses against 22. That replay is post hoc.

## Decisions of the owner

| Question | Options | Decision |
|---|---|---|
| How stage 2 is limited to the label | a label prompt and label crops; a label prompt only; a code filter only | a label prompt and label crops |
| The vintage policy in the same rebuild | yes; no | yes |
| The vintage variants: where a year of a dated card comes from | the card names only; the names and the catalogue labels | the names and the catalogue labels |
| The rebuild for the vintage variants | the mixed clusters only; all 255 rules | the mixed clusters only |

The owner added the rule of the vintage variants on 2026-09-24, during the rebuild:
when cards differ only by the vintage year, and one card states no year, that card is
the card of every vintage that no other card states.

## Changes

Stage 2, `scripts/cluster_rules.py`:

1. The picture of each card is the label crop of `bottle_label_dir`. The crop is RGBA,
   and its alpha channel is the label mask. It goes on white, scaled to a long side of
   768 pixels, UP or down. This is the view that the re-rank sends for a query. 629 of
   the 630 cluster cards have a label crop. A card with no label crop sends its
   catalogue picture, and its caption states that.
2. The label description goes into the prompt without the key `bottle`. Stage 1 does
   not change, so every description stays current.
3. The prompt:
   - The pictures are label pictures. Some catalogue pictures are drawings, and a
     drawing shows only the label correctly.
   - The task names the label. The query model sees only the label.
   - Rule 1: a person MUST be able to answer each question by looking at the label
     alone.
   - Rule 1a: use only features that are printed on the label. Do not ask about the
     glass, the colour of the liquid, the capsule, the cork, or the shape of the bottle.
   - Rule 2: the colour of the wine as the label states it. The capsule colour moves
     to rule 1a. The vintage year follows rule 2a.
   - Rule 2a: ask about the vintage year only when the catalogue names of at least two
     cards state two different years. Take each expected year from the name.
   - Rule 3: write a name, a grape, or another text exactly as the label prints it, in
     its own alphabet. When the picture of a card is the picture of another card, write
     the text as the catalogue data writes it. A sugar level or a colour uses the
     words of rule 2.
   - Rule 12: the example rule text holds a ratio, not a year.
4. The caption of a card that shares its catalogue picture with another card of the
   cluster names that card. It says that the catalogue can reuse a picture, and that
   the catalogue data wins where the picture contradicts it. 43 cards of 21 clusters
   share a picture with another card of their cluster.
5. The code checks of `check_rule`:
   - A question of kind `bottle` is never valid. The kind comes from the words of the
     question: the glass, the liquid, «through the», the capsule, the cork, the shape
     or the colour of the bottle, «wine in the bottle».
   - A question of kind `vintage` keeps the expected year of a card only when the name
     or the slug of the card holds every year of the answer. The question is valid when
     two cards keep two different years.
   - A rule text that names a feature of kind `bottle` gives mode `none`, not
     `verdict`.
   - A valid `vintage` question counts as a feature for the rule of the alcohol value.
6. `RULES_SHA` holds the setting of the picture and the three captions.
   `rule_inputs_sha` holds the path of the label crop of each card. Every rule of
   2026-09-23 is therefore stale.
7. The vintage variants:
   - A card states a year in its name, in its slug, or on its label (the key `vintage`
     of its label description). A year of the name wins over a year of the label. A
     card states no year when its name, its slug, and its description give none. A
     card with an unreadable label year, a year after the current year, or no
     description is in neither group.
   - A mixed cluster holds cards that state a year and cards that state none: 43 of
     the 255 clusters on 2026-09-24. Only the prompt of a mixed cluster gets the note
     `VINTAGE_NOTE`. The note names the years of each card and the cards with no year.
     It tells the model to give a card with no year the answer "other" when the cards
     differ only by the vintage year.
   - `check_rule` keeps the mark `other` only for a card that states no year, and only
     when no other question of the rule separates that card from every card with a
     year. The questions of kind `alcohol` do not count, because the alcohol value can
     change between vintages. When a mark stays, a vintage question keeps the year on
     the label of a card, as a bare year. Else rule 2a applies.
   - The note enters `rule_inputs_sha` only for a mixed cluster. The rules of the
     other clusters therefore stay current.

The matcher, `svoe-vino-matcher/svm/cluster_rules.py`:

- `compared_answer`: in a question of kind `vintage`, an answer that holds one year
  counts as that year when a card expects it, and as `other` when no card expects it.
  In the run v2, the query VLM wrote the year instead of `other` in 4 of the 5 answers
  about a year that no card listed. A text such as «урожай 2023» counts as 2023.
- `options_of` lists `other` once, also when a card expects it.
- `tests/test_cluster_rules.py` holds four new cases. The 26 cases pass.

Other files:

- `scripts/review_server.py`: the tooltip of a struck question names the reason for the
  kinds `bottle` and `vintage`.
- `scripts/cluster_rules_report.py`: the option `--rules` names the rules file of a run
  for the post hoc score. A new section gives the paired numbers for each half of the
  wines. The half of a wine is the SHA-1 of its slug, modulo 2.
- `svoe-vino-matcher` does not change. The re-rank reads the field `valid` of each
  question, and it sends the label crop already.

The rules file of 2026-09-23 is kept as
`work/catalog-cluster-rules.2026-09-24T082150.json`. The file
`dataset/catalog-cluster-rules.json` is not in git, so this copy is the only record of
the rules of the run v2.

## Changes during the implementation

1. The first test build of c001 wrote the grape names in a Latin transliteration:
   «Krasnostop», «Chardonne», «Merlo». The labels print «КРАСНОСТОП», «ШАРДОНЕ», and
   «МЕРЛО». The rules of 2026-09-23 used the printed alphabet. The query VLM would have
   to map the printed text to a Latin option, and an answer in the printed alphabet
   would match no option. Rule 3 now asks for the printed text in its own alphabet.
2. The test build of c001 gave card E («БЮРНЬЕ.ПИНО БЛАН») the text «ВИОНЬЕ». The
   catalogue picture of card E is the picture of card J («БЮРНЬЕ.ВИОНЬЕ»), byte for
   byte. The rule of 2026-09-23 took «Пино Блан» from the name. Item 4 of "Changes" was
   added. After it, c108 («Красностоп Резерв» and «Гренаш», one shared picture) was
   separated by the grape and by the mark «Резерв». c001 kept E and J as
   indistinguishable, also after the second sentence of rule 3. The tuning stopped
   there, so that the prompt does not fit one cluster.
3. The model still asked a vintage question about years that only the picture shows
   (c001, q3). The code check removed every year of it, and the question is not valid.
4. The first stage 2 run was stopped after about 7 rules, before items 1 and 2. Its
   rules became stale and were built again.
5. The second stage 2 run was stopped at 09:59 after 182 rules, when the owner added
   the rule of the vintage variants. 152 rules of clusters that are not mixed stayed
   current. Two rules failed with HTTP 400 «Download multimodal file timed out» of
   QwenCloud; the client does not repeat a 4xx answer, so the next run built them
   again. The third run built 103 rules: the 43 mixed clusters, 58 rules that were not
   built yet, and the 2 failed rules.
6. The test labels of c013 do not follow the rule of the vintage variants. c013 holds
   «Абрау-Дюрсо Пино Нуар» (no year), «Каберне Совиньон» (2023 on the label),
   «Пино Нуар» (2023 on the label), and «Пино Нуар» (2024 on the label). On the 8
   positive photos of its three Pinot Noir cards, by the years that the query VLM read
   in the run v2, the rule and the test labels give the same card for 2 photos. The
   owner chose the rule with this fact known.

## The benchmark

- A row in `/Users/ashmelev/Admin/GPU_TASKS.md` comes first. The run asks the gx10
  gateway for two SigLIP 2 embeddings for each photo and asks `qwen3.5-9b` when the step
  acts.
- One `match_run.py` run of 2,181 photos, backend `svm-label-gw-cluster-rules`, one
  request at a time, against the Mac server on 127.0.0.1:8164 with the rebuilt rules.
- The report of `scripts/cluster_rules_report.py` against the base run
  `2026-09-23T121203Z-svm-label-gw-difference-alpha-patches`.
- A paired comparison against the run v2 with `scripts/compare_runs.py`.
- Both halves of the wines. The vintage policy was chosen after a replay over all
  wines, so neither half is free of that choice. The halves show whether the effect is
  the same in both halves.

## Known limits

- A label crop cuts off the text outside the main label, such as a neck label. The
  re-rank sends the same kind of crop, so it cannot read such a text either.
- `rule_inputs_sha` holds the path of a label crop, not its bytes. A crop that is cut
  again under the same path does not make a rule stale.
- The review tool and the matcher server read the code and the rules at start. Both
  MUST be started again to use them.
- The model does not always keep the prompt. The code enforces the rules of the kinds
  `serial`, `bottle`, `vintage`, and `alcohol`. It does not enforce the rule about a
  design, a colour shade, or a background: the test build of c001 asked for the
  background colour of the label.
- A label year comes from stage 1, the local `qwen3.5-9b`. A year that stage 1 did not
  report makes a dated card look like a card with no year. 309 of the 630 cluster
  cards have no label vintage in their description. The model of stage 2 checks the
  years in the label crops, and the guard of `check_rule` needs a card with a year
  that differs from the card only by the vintage.
- The post hoc score of `scripts/cluster_rules_report.py` does not know the year
  mapping of `compared_answer`. For a question with `other`, it undercounts the
  evidence for the card with no year.

## Open questions

Status on 2026-09-24. Each question waits for a decision of the owner. The facts are
in `ResearchLog.md`, 2026-09-24. No label, no catalogue file, and no rule was changed
for these questions.

### Q1. A photo of a vintage that no card states, when every card states a year

Facts:

- c129 holds `esse-mama-marselan-krasnoe-suhoe-115` («MaMa», 11.5 %, «CRIMEA 2022» on
  the catalogue label) and `esse-mama-marselan-krasnoe-suhoe-135` («МаМа», 13.5 %,
  «CRIMEA 2024»). The two labels differ only by the year and by the colour shade.
- The photo `esse-mama-marselan-krasnoe-suhoe-135/01_conf095.jpg` shows «CRIMEA 2020».
  The query VLM read 2020 also on `esse-mama-marselan-krasnoe-suhoe-115/02_conf095.jpg`
  and `.../03_conf095.jpg`. The test labels therefore put two photos of 2020 on the
  2022 card and one photo of 2020 on the 2024 card.
- No card of c129 states no year, so the rule of the vintage variants does not apply.
  A rule that picks one card for 2020 loses at least one of the three photos.

Options:

1. Label a photo of an unlisted vintage `variant`, and join the cards in
   `dataset/my/manual-groups.json`. The label `variant` means «this wine in another
   bottle: another vintage, another alcohol value, or another package design».
   `scripts/08_variants.py` did not join these two cards, because «MaMa» and «МаМа»
   differ by the alphabet. A run with `--variants off` leaves such photos out. A run
   with `--variants group` counts each card of the group as right. **Recommended.**
2. The nearest stated year wins: 2020 goes to the 2022 card. This agrees with 2 of
   the 3 labels. A year at the same distance from two stated years has no answer.
3. The newest card wins: 2020 goes to the 2024 card. This agrees with 1 of the 3
   labels.
4. No change: the base order decides.

### Q2. The verdict rules that decide by a label year alone

Facts:

- 16 of the 33 rules of mode `verdict` tell the cards apart by a label year alone:
  c049, c070, c073, c122, c129, c130, c158, c162, c167, c168, c205, c219, c220, c229,
  c240, and c254. Their clusters hold 39 test photos.
- In mode `sheet`, `check_rule` removes a year that only the picture shows. The rule
  text of mode `verdict` keeps such a year. The vintage policy of this plan therefore
  does not reach these 16 rules.
- The owner decided that a year on the catalogue label counts for the vintage
  variants.

Options:

1. When every card of a cluster states a year and the cards differ only by the
   vintage, a vintage question of mode `sheet` keeps the label years. The year mapping
   of the matcher then applies. About 16 rules are built again. **Recommended.**
2. Mode `none` for these rules: the base order decides.
3. No change.

### Q3. The test labels of c013

Facts: by the rule of the vintage variants, a Pinot Noir photo with a year that no card
lists belongs to «Абрау-Дюрсо Пино Нуар». The test labels put such photos on the other
Pinot Noir cards. The rule and the labels agree on 2 of the 8 Pinot Noir photos. The
owner chose the rule with this fact known.

Options:

1. Relabel the photos of an unlisted year to «Абрау-Дюрсо Пино Нуар».
2. Label them `variant`, as in option 1 of Q1.
3. No change: the benchmark counts them as losses.

### Q4. The shared catalogue pictures

Facts: 43 cards of 21 clusters share one catalogue picture, byte for byte, with another
card of their cluster. The caption of stage 2 helped c108, but c001 kept «ПИНО БЛАН»
and «ВИОНЬЕ» indistinguishable. Examples: «Красностоп Резерв» and «Гренаш»;
«Пухляковский» and «Рислинг»; «Шёпот цветов» and «Ветер в травах».

Question: patch the catalogue pictures of these cards? A patch is the only fix that
gives the model the true label of each card.

### Q5. The rules file in git

Facts: `dataset/catalog-cluster-rules.json` is not in git. The rules of the run v2 exist
only as `work/catalog-cluster-rules.2026-09-24T082150.json`, and `.gitignore` ignores
`work/`.

Question: commit the current rules file, and keep the rules of the run v2 in a tracked
place?

### Q6. The other improvements of the review of 2026-09-24

Facts from the run v2, in `ResearchLog.md`:

- 67 of the 270 positive misses have a rank-1 card in no cluster, so the step does not
  act. 45 of them have the true card of the producer of the rank-1 card.
- 34 misses got `not visible` for every question. A grape question decided at least 15
  of them, and a ratio question 11.

Options: a trigger for a rival of the same producer within a margin, with one record
of label attributes for each card; a second look with the whole photo or a larger crop
when every answer is `not visible`. Both options wait for the result of this plan.

## Result

Measured on 2026-09-24. Run
`runs/2026-09-24T080721Z-svm-label-gw-cluster-rules-label-only-rules`, 2,180 photos
(1,599 positive, 581 negative), the 255 rules of this plan (221 `sheet`, 33 `verdict`,
1 `none`), the local `qwen3.5-9b` at query time. The report is
`cluster-rules-report.md` of the run.

Against the base run `2026-09-23T121203Z-svm-label-gw-difference-alpha-patches`, on
2,180 paired photos:

| Metric | Base | Label-only rules |
|---|---:|---:|
| R@1 of 1,599 positives | 0.8161 | 0.8355 |
| MRR | 0.8836 | 0.8959 |
| R@5 | 0.9656 | 0.9656 |
| Negatives rejected (581) | 0.8262 | 0.8451 |

- Positives: 61 wins, 30 losses, exact McNemar p 0.002. Negatives: 12 wins, 1 loss,
  p 0.003.
- Half A of the wines: R@1 0.8103 → 0.8297, 33 wins, 18 losses, p 0.049. Half B:
  0.8216 → 0.8410, 28 wins, 12 losses, p 0.017. The effect is the same in both halves.
- Without the clusters that only the `confusion` signal joins (replay): R@1 0.8255,
  36 wins, 21 losses, p 0.063.

Against the rules of 2026-09-23 (the run v2), on 2,180 shared photos:

- Positives: R@1 0.8318 → 0.8355, +0.0038, 27 wins, 21 losses, p 0.47.
- Negatives: 0.8399 → 0.8451, 4 wins, 1 loss, p 0.38.
- The difference to the run v2 is therefore not significant. The label-only rules
  are at least as good as the rules of 2026-09-23, and they keep the vintage policy
  and the label-only policy of the owner.

Details:

- The step acted on 894 photos. Mode `sheet`: 834 photos, 127 changes, 71 wins and 29
  losses over both labels. Mode `verdict`: 60 photos, 6 changes, 2 wins and 2 losses.
- c032, the first cause of the losses of the run v2, gives 4 wins and 0 losses against
  the run v2: the year that only the picture shows no longer moves a card.
- The 20 clusters with a vintage question with `other` give 13 wins and 11 losses
  against the base. Against the run v2 they give 10 wins and 6 losses. The test labels
  of such clusters do not always follow the rule of the vintage variants: see Q3.
- c013: the photo `abrau-dyurso-kaberne-sovinon-krasnoe-suhoe-125/04_agent.jpg` is
  right now. The Pinot Noir photos of the years 2019, 2020, and 2022 go to «Абрау-Дюрсо
  Пино Нуар», as the rule says, and the test labels count them as losses. On
  `abrau-dyurso-abrau-dyurso-pino-nuar-krasnoe-suhoe-13/02_conf095.jpg` the rule gave the
  true card the best score, but that card stood at base rank 6, outside the window.
- c129: the two photos of 2020 got the verdict `unsure`, so the base answer stayed.
- A replay with a window of 10 instead of 5 adds 1 win: R@1 0.8361. A wider window is
  not worth a change.
- Latency: median 2,669 ms where the step acted, 171 ms elsewhere; 675 VLM calls with a
  median of 2,574 ms; 84.5 % of the photos within the 3,000 ms SLA. The gx10 GPU was
  quiet (0 % at the pre-flight), so this latency is not comparable with the loaded host
  of the run v2.

The answers by question type, on the positive photos where the step acted in mode
`sheet` and the true card is in the cluster. The rules differ from the rules of the run
v2, so a comparison of the two runs by type is only an indication.

| Type | Answers | Correct | `not visible` | The value of another card | Run v2: correct |
|---|---:|---:|---:|---:|---:|
| yes/no mark | 267 | 77 % | 10 % | 13 % | 86 % |
| sugar level | 197 | 83 % | 11 % | 3 % | 86 % |
| name or line text | 132 | 85 % | 5 % | 8 % | 94 % |
| grape | 116 | 89 % | 9 % | 0 % | 67 % |
| vintage with `other` | 73 | 41 % | 11 % | 45 % | — |
| wine colour | 44 | 82 % | 9 % | 5 % | 74 % |
| ratio or blend | 15 | 53 % | 40 % | 0 % | 34 % |
| vintage from the names | 8 | 12 % | 0 % | 50 % | — |

- The grape answers improved most: 89 % correct against 67 %, and `not visible` 9 %
  against 25 %. The rules now write the grape as the label prints it, and stage 2 saw
  the label crops.
- In a vintage question with `other`, 45 % of the answers give the value of another
  card. In c013 the test labels cause such answers: a photo of a year that no card
  lists is labelled with a dated card (Q3). The other 19 clusters were not checked
  one by one.
