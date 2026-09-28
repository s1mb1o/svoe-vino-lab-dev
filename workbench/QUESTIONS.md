# Open questions

This file holds the questions that the owner postponed.
Each question has a state: `open` or `answered`.
When the owner answers a question, record the answer and the date here.
Also record the answer in [docs/owner-messages.md](docs/owner-messages.md).

## Q1. The source of the label image of an embedding

State: answered on 2026-09-25 (owner messages 2026-09-25T00:51:21+0300 and
2026-09-25T01:01:05+0300). Asked on 2026-09-25. The owner postponed the answer first.
Plan: [docs/plans/10_embeddings-page.md](docs/plans/10_embeddings-page.md).

Answer:

- A SAM3 cut of the label makes the label image of a full image (a front or a back of
  the whole package). The variants are D (the box crop), E (D with the background
  removed), and F (E on white). The view `label` of an embedding uses F.
- The cut runs at import, next to the package cut of plan 09. It runs one time for each
  source file.
- The close-up images `front_label` and `back_label` go to the view `label` as they are.

The text below is the question as it was asked.

An embedding can have more than one view of a source image.
The view `full` is the whole package.
The view `label` is the label alone. The file name is `<source_sha256>_label.png`.
The question: which step makes the label image?

| # | Option | Notes |
|---|---|---|
| 1 | A SAM3 cut of the label, as `svoe-wino-hackaton/scripts/build_labels.py` does. | That script sends the nouns `wine bottle label` and `label`, and the noun `wine bottle`. It keeps the largest label mask that is not the bottle. It writes two variants: the mask applied on RGBA, and a box crop alone. |
| 2 | The image type `label_front` of the table `wine_image`. | On 2026-09-25 the table holds no row of this type. |
| 3 | Another source. | The owner names it. |

Until the owner answers:

- The configuration check rejects a view `label`.
- Each embedding has the view `full` alone.

## Q2 to Q11. The benchmark of the embedding entries (plan 40)

State: answered on 2026-09-26 by the session drink-atlas-workspace-e2 [9e7fe4]. The owner
message of 2026-09-26T01:43:59+0300 asks the session to answer its own questions and to
log them here. The owner MAY change an answer. Plan:
[docs/plans/40_embedding-benchmark.md](docs/plans/40_embedding-benchmark.md).

| # | Question | Answer of the session | Reason |
|---|---|---|---|
| Q2 | What is "commit all"? | One commit of every pending change of `svoe-vino-lab`, after each live session that changes the project sent "finished". | The owner asked for it. `runs/` and `data/` stay out: `.gitignore` holds them. |
| Q3 | What is "basic pipeline"? | The two forms of the owner message of 2026-09-26T00:45:33+0300: `as-is` and `crop`. | The owner named them "basic runner configs". |
| Q4 | What are "all variants of embeddings"? | The 11 entries of the key `embeddings` of `config.yaml`. | These are the embedding variants of the lab. The gateway also serves `wemm-embed-*` and `qwen3-embed-*`; they are not entries, and `qwen3-embed-*` is a text model. |
| Q5 | Which test sets? | `my` (2,209 queries) and `official-real-photos` (80 queries). | `my` is the set of the two basic runs of 01:07. `official-real-photos` has the runs of `vino-svoe-search-by-photo`, the baseline of the present recognizer. |
| Q6 | Is a run of `vino-svoe-search-by-photo` on `my` part of the benchmark? | No. | That run sends 2,209 photos to the external API of vino-svoe.ru. The report uses the runs on `official-real-photos`. |
| Q7 | What happens to the entry with no index (`gx10-siglip2-so400m-patch16-512`)? | Build its index first. | The gateway serves the model; the owner asked for all variants. |
| Q8 | What happens to the indexes of 2026-09-25 with 4 missing items? | Add the missing items with `build_embeddings.py` first. | Each run then compares the same catalogue. |
| Q9 | Is a third pipeline with the steps of the entry (package cut, background removed, view `label`) part of it? | No. | The owner named the two basic forms. The view `label` of the photos of `my` needs about 2,209 new SAM3 calls. |
| Q10 | How many photos at a time? | 4 for a gx10 entry; 1 for the entry of the backend `local`. | The gateway serves one model at a time; the Mac prepares the next photos meanwhile. The backend `local` takes one request at a time. |
| Q11 | Which metric ranks the entries? | R@1 of the positive photos of `my`. The report also gives R@5, R@10, MRR, the false match at 1, and the latency. | R@1 is the answer that a user sees. |

## Q12. The stale sections of `ACTIVE_WORK.md` after the commit 1dd3006

State: answered on 2026-09-26 by the session drink-atlas-workspace-e2 [9e7fe4], under the
owner message of 2026-09-26T01:43:59+0300 (the session answers its own questions).
Rule 21 of `AGENTS.md` says: ask the owner before the removal of a stale section.

Question: the sections of 5c [cbb143], a9 [79efd8], 3b [d30290], and 28 [5ddfae] are stale
(their sessions are not in the `ListAgents` answer). Their work is in the commit 1dd3006.
Do they stay?

Answer: remove them. Rule 20 removes a section when its work is committed, and a stale
section keeps other sessions from their files. The ChangeLog bullets and the commit
1dd3006 record their work.

## Q13. The commit of the work of plan 40

State: answered on 2026-09-26 by the session drink-atlas-workspace-e2 [9e7fe4], under the
owner message of 2026-09-26T01:43:59+0300.

Question: the owner asked for "commit all" before the benchmark. Does the work of the
benchmark (the pipelines, the plan, the report, the logs) get a commit too?

Answer: yes, one commit of the files of this session alone, after the report. The owner
wants a committed tree. A hunk of another session stays out of this commit.
