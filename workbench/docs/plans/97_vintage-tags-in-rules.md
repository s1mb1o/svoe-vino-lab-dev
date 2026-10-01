# Plan 97: the vintage tags of the wines in stage 2 of the cluster label rules

Date: 2026-10-01

Source: the owner message of about 2026-10-01T00:08:00+0300 and the answers of about
00:14 (`docs/owner-messages.md`).

## Request

```text
we agreed that we will not generate rules in cluster if difference is only year or missing year on package AND there is no year mentioned in any title.

However, check also tags, if there is year (ex. "2020") or tag "no_year" then handle this as like year was in title.
```

The owner selected these answers:

- A tag note goes only into the prompt of a cluster with a vintage tag.
- A tag `2020` and a tag `vintage:2020` count. The tag `no_year` counts too.
- The work was agreed with session e4, whose uncommitted hunks are in the same files.
- One stage 2 build of the example cluster runs after the change.

## Before the change

1. Rule 2a of `RULES_PROMPT` allows a vintage question only when the catalogue names of
   at least two cards state two different years.
2. `named_year` in the check keeps the expected year of a card only when its name or its
   slug holds the year. `vintage_facts` reads the name, the slug, and the label
   description.
3. The wine tags (table `wine_tag`, plan 63) did not reach stage 2.

## The rules

1. A vintage tag is a tag that matches `^(?:vintage:)?((?:19|20)\d{2})$`, or the tag
   `no_year` (`label_rules.YEAR_TAG`, `label_rules.NO_YEAR_TAG`).
2. A year tag counts as a year of the catalogue name. `named_year` keeps a year that a
   tag of the card holds.
3. `vintage_facts` puts a card with a year tag into `dated` with `where` = `in a tag`.
4. `vintage_facts` puts a card with the tag `no_year` and no year tag into `undated`.
   The tag wins over a year of the label description. A card with no description also
   counts.
5. A year of the name or of the slug wins over a tag. A tag wins over the label.
6. A cluster with a vintage tag gets the note `TAG_NOTE` in the stage 2 prompt, before
   the note `VINTAGE_NOTE` and before `Answer with one JSON object:`. The note lists the
   tags of each tagged card, for example `Card A: 2021; Card B: 2020`.
7. A cluster with a year tag and a `no_year` card also gets `VINTAGE_NOTE`, as a cluster
   with a year in a name and a card with no year does.
8. The rendered note enters `inputs_sha` as `tag_note`. A change of a vintage tag makes
   the rule of the cluster stale. A cluster with no vintage tag keeps its SHA, so its rule
   stays current. `RULES_PROMPT`, `CARD_BLOCK`, and `rules_sha` do not change.
9. `_run` reads `wine_tags.tags` from the lab database and puts the tags in the key `tags`
   of each `catalog` record. No function gets a new parameter.
10. `cluster-rules.json` records the template under `prompts.tag_note`.

## Files

- `pipeline/label_rules.py`: `TAG_NOTE`, `YEAR_TAG`, `NO_YEAR_TAG`, `vintage_tags`,
  `tag_note`, and changes in `vintage_facts`, `named_year`, `rules_content`,
  `inputs_sha`, `save_file`, and `_run`.
- `tests/test_label_rules.py`: the class `VintageTagTest`.

## Not changed

- `scripts/cluster_rules.py`, the port of `svoe-vino-testset`, does not read tags.
  `TAG_NOTE` is not in the prompt comparison of `PromptTest`.
- The matcher does not need a change. It reads the expected answers of the rule.
- The docstrings of `pipeline/wine_tags.py` and `pipeline/lab_server.py` still state that
  the pipeline does not read the tags. The stale section 1e of `ACTIVE_WORK.md` lists
  `wine_tags.py`, so the owner decides that edit.

## Example

The manual cluster `3889ddfd95bb` of `gx10-siglip2-so400m-patch16-naflex-p256` holds
`alma-valley-shardone-rezerv-beloe-suhoe-135` (tag `2021`) and
`alma-valley-shardone-rezerv-beloe-suhoe-14` (tag `2020`). Both names are
«Шардоне Резерв». Before the change, rule 2a did not allow a vintage question. After the
change, the prompt holds `Vintage tags. The reviewer tagged the vintage of some cards:
Card A: 2021; Card B: 2020. …`, and a vintage question with 2021 and 2020 is valid.
