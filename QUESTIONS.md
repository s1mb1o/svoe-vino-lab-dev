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
