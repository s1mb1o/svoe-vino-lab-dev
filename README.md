# svoe-vino-testset

Test data for the Svoe Vino wine scanner.

- `eval/` is the official evaluation set from the organizers. It holds 3 photos.
- `my/` is a larger set built by this project. It holds real-world photos found on the web.
- `scripts/` holds the five pipeline stages and the driver.
- `work/` holds the state database, the downloaded candidates, and the logs. It is disposable.
- `config.yaml` holds the paths that point out of this project.
- `backends.yaml` defines the match backends.
- `runs/` holds one directory per match run. It is the history of the measurements.
- `excluded-slugs.json` names the slugs that are out of the benchmark.
- `manual-groups.json` names the variant pairs that a reviewer made by hand.

## Configuration

`config.yaml` in the project root holds the configuration. `scripts/common.py` reads it.

| Key | Constant in `common.py` | Meaning |
|---|---|---|
| `rootdir` | `ROOTDIR` | Root directory of the workspace. Every relative path of the configuration is resolved against it. |
| `catalog_file` | `CATALOG_FILE` | Catalogue of the vino-svoe.ru wines, one JSON record per line. |
| `photo_dir` | `PHOTO_DIR` | Photo set. One directory per wine slug. |
| `trash_dir` | `TRASH_DIR` | A deleted photo is moved here, not unlinked. |
| `label_file` | `LABEL_FILE` | Labels of the review tool. |
| `variant_groups_file` | `VARIANT_GROUPS_FILE` | Variant groups. `scripts/08_variants.py` writes this file. |
| `manual_groups_file` | `MANUAL_GROUPS_FILE` | Variant pairs made by hand in the review tool. `scripts/08_variants.py` never writes this file. |
| `excluded_slugs_file` | `EXCLUDED_SLUGS_FILE` | Excluded slugs. The photos of an excluded slug are not used for benchmarking. |
| `backends_file` | `BACKENDS_FILE` | The match backends of `scripts/match_run.py`. |
| `runs_dir` | `RUNS_DIR` | One directory per match run. |

```yaml
rootdir: /Volumes/T7_2TB/Projects-T7_2TB/drink-atlas-workspace
catalog_file: svoe-wino-hackaton/dataset/derived/official-2026-09-17/catalog.jsonl
photo_dir: svoe-vino-testset/dataset/my/photo
trash_dir: svoe-vino-testset/work/trash
label_file: svoe-vino-testset/dataset/my/review-labels.json
variant_groups_file: svoe-vino-testset/dataset/my/variant-groups.json
manual_groups_file: svoe-vino-testset/dataset/my/manual-groups.json
excluded_slugs_file: svoe-vino-testset/dataset/my/excluded-slugs.json
backends_file: svoe-vino-testset/backends.yaml
runs_dir: svoe-vino-testset/runs
```

An absolute value stays as it is. An absent key gives the earlier default path.
`common.rootpath(path)` resolves any other relative path against `rootdir`.
`scripts/review_server.py` and `scripts/08_variants.py` take every path from these
constants. `scripts/review_server.py` prints the configuration and the work directory
at start:

```
configuration: .../svoe-vino-testset/config.yaml
  rootdir              : /Volumes/T7_2TB/Projects-T7_2TB/drink-atlas-workspace
  catalog_file         : .../svoe-wino-hackaton/derived/catalog.jsonl
  photo_dir            : .../svoe-vino-testset/my
  ...
work directory: /Volumes/T7_2TB/Projects-T7_2TB/drink-atlas-workspace
```

A path that does not exist gets the mark `(absent)`.

## Result

| Measure | Value |
|---|---|
| Wines in the catalogue | 2,018 |
| Wines with at least 1 photo | 844 (42%) |
| Wines with 3 or more photos | 386 (19%) |
| Wines with no photo | 1,174 (58%) |
| Photos in `my/` | 2,016 |
| Vision checks made | 25,172 |
| Acceptance rate | 8.6% |

`my/` is written by stage 5. Re-run `python3 scripts/05_report.py --keep 4`
after any later pass, or the directory keeps the content of the previous run.

## The `my/` set

The set covers the 2,018 wines in `wines.jsonl` of the `vino-svoe.ru` dump.
Each wine has its own directory `my/<slug>/`.
A file name is `<rank>_conf<NNN>.<ext>`. `NNN` is the model confidence in percent.

The set contains real-world photos only. A studio catalogue render is excluded.
Two filters remove studio renders: a border-whiteness measure, and a vision model judgement.

A wine has fewer than 3 photos when the web holds fewer than 3 usable photos of it.
`REPORT.md`, `report.html`, and `report.csv` list every wine and every gap.

## Pipeline

| Stage | Script | Work |
|---|---|---|
| 1 | `01_search.py` | Collect candidate image URLs from Yandex Images and DuckDuckGo |
| 2 | `02_download.py` | Rank candidates by text relevance, then download the best ones |
| 3 | `03_embed.py` | SigLIP2 embedding, cosine similarity against the catalogue photo |
| 4 | `04_verify.py` | `qwen3-vl-32b` pairwise check: same wine, and studio or not |
| 5 | `05_report.py` | Copy accepted photos to `my/`, write the report |
| 6 | `06_topup.py` | Reopen wines that have fewer than 3 photos for a deeper pass |
| 7 | `07_api_check.py` | Ask the official recognizer about each accepted photo |

Run every stage through the driver:

```bash
python3 scripts/run_pipeline.py --chunk 150 --per-wine 20 --top 8 --vlm-workers 6
python3 scripts/05_report.py
```

Finish the set with one command:

```bash
scripts/finalize.sh
```

Stage 1 runs on its own because it is slow and independent:

```bash
python3 scripts/01_search.py --workers 4
```

Every stage is resumable. State lives in `work/state.db`.
Stages 3 and 4 use the llama-swap service on gx10 (`http://192.168.86.14:18081`).

## Manual labelling tool

`scripts/review_server.py` is a browser tool for manual labelling.
It answers one question for each candidate photo: what is this photo for this slug?

```bash
python3 scripts/review_server.py            # opens http://127.0.0.1:8154/
python3 scripts/review_server.py --no-browser --port 8154
```

### The four labels

| Label | Key | Meaning | Stays in the set |
|---|---|---|---|
| `positive` | `1` | The photo shows the wine of this slug. | Yes, as a positive sample |
| `negative` | `2` | The photo shows a different wine. | Yes, as a negative sample of this slug |
| `unusable` | `3` | No bottle, unreadable, or a duplicate. | No |
| `variant` | `4` | This wine in another bottle: another vintage, another alcohol value, or another package design. | Yes, as a variant sample |

A `variant` label answers the case that `positive` and `negative` both fit badly:
the photo holds the same wine, but the bottle on it is not the bottle of this slug.
Read the section "Variant groups" for the reason that such a case is common.

A `negative` label is a wanted result, not waste. The set needs negative samples,
so a `negative` photo is kept and is marked with its own colour. `unusable` is the
only label that takes a photo out of the set. A photo with no label is not
reviewed yet.

### The table

The page holds one table row per wine.
Column 1 holds the catalogue bottle photo of the wine from the strapi dump.
The next column holds the candidate photos of `my/<slug>/`.
Each candidate photo has four buttons: `V`, `N`, `x`, and `D`.
The buttons stand in the order of the keys `1`, `2`, `3`, `4`.
The same button again clears the label.
A `copy` button next to the slug puts the slug on the clipboard.
A `move` button under a photo sends the photo to another wine slug.
A `copy` button under a photo gives the photo to another wine slug as well,
and leaves the photo where it is.

The page has thirteen sort orders, twenty-two filters, and a text search.
Sort by `unlabelled first` to continue an unfinished pass.
Sort by `confidence, lowest first` to check the weakest evidence first.
Filter by `has no positive photo` to find the wines that still need a good photo.

#### The text search

The search reads the slug, the name, the producer, the region, and the grapes. It
takes the query apart into words and asks for each word on its own, so the order of
the words does not matter. Four rules make a word meet the text:

1. A word of the text holds the word of the query. `vivandie` finds `Vivandiere`.
2. The accents are folded on both sides. `cotes` finds `Côtes du Don`.
3. A word of four letters or more also meets a word of the text that stands one
   letter away from it. `chardonay` finds `Chardonnay`.
4. A word in Cyrillic is looked for in its Latin form as well, because the slug is
   Latin. The canonical form puts the spellings of the slugs together, so
   `cimlyanskiy`, `tsimlyanskiy`, and `czimlyanskoe` find each other.

The transliteration was checked against the catalogue on 2026-09-17. Of the Cyrillic
words of the wine names, 96.0 percent stand in the slug exactly as the table writes
them, and the rules above reach 1.6 percent more. The rest do not match, because the
slugs do not follow one rule; `b-yu-rne` for `Бюрнье` is an example.

The search does NOT open a scope of its own. A catalogue card that holds no
candidate photo stays out of the table under most filters, also when it meets the
query. Select `no candidate photos (catalogue gap)` to search those cards.

### The note about a wine

The wine column holds a text field under the data of the wine. The field takes a note
about the **whole wine**, not about one photo: what this wine is, how it differs from
its variants, what a later reviewer MUST watch for.

The field is one line high until it holds a text. It opens to a larger box while it
holds a text or while the cursor is in it. The text is saved after a pause of 700 ms
and again when the cursor leaves the field. The table is not drawn again while the
note is saved, so the cursor stays where it is. An empty field removes the note.

A note about a wine is at most 4000 characters. It is stored in the top level map
`wines` of `review-labels.json`, keyed by the slug, apart from the labels:

```json
"wines": {
  "vysokij-bereg-risling-zelenaya-seriya-1": {
    "comment": "Зеленая серия: три варианта, различать по цвету колпачка",
    "ts": "2026-09-15T22:17:41+0300"
  }
}
```

The count `wine_notes` states how many wines hold a note. A note of a wine that `my/`
no longer holds is dropped at start, as a label is.

The comment panel of the large view is a different thing: it belongs to one photo and
one slug. Use the field of the wine column for a statement about the wine itself.

### Variant groups

The catalogue holds one slug per bottle, not one slug per wine. The same wine of
another vintage, or of another alcohol value, gets its own slug and its own
catalogue photo. The two photos then hold the same label design in two colours, so
a reviewer can mix them up. Example:

```
https://vino-svoe.ru/wines/abrau-dyurso-pino-nuar-krasnoe-suhoe-12
https://vino-svoe.ru/wines/abrau-dyurso-pino-nuar-krasnoe-suhoe-125
```

`scripts/08_variants.py` finds such slugs and writes the file that `variant_groups_file` names in `config.yaml`:

```bash
python3 scripts/08_variants.py --no-image      # metadata step only, runs at once
python3 scripts/08_variants.py                 # metadata step and image step
python3 scripts/08_variants.py --threshold 0.93
```

The script joins two slugs in two ways:

1. Metadata. The same `producer` and the same `name` in `catalog.jsonl`.
   This step is exact and costs nothing. It gives 28 groups over 63 wines of `my/`.
2. Image. The cosine similarity of the SigLIP2 embeddings of the two catalogue
   bottle photos, at or above `--threshold`. This step needs the llama-swap service
   on gx10. It finds the pairs that step 1 misses. Every run embeds the bottle photos
   again, because the script keeps no embedding cache. Use `--no-image` to skip the
   step.

The image step MUST NOT run while stage 4 of the pipeline runs. Both use the same
llama-swap service, and a request for `siglip2` makes the service drop
`qwen3-vl-32b` and load `siglip2`. The pipeline then stalls.

The review tool reads the variant groups at start. The rows of one group
stand next to each other, whatever the sort, and share one background colour. The
filter `has a similar wine (variant group)` shows only the wines of a group.
A wine with no group keeps the normal background.

#### Grouping two wines by hand

The generated groups miss a pair whose producer or name differs in the catalogue.
The `Group` button under the bottle photo joins the wine to another wine. The
button states the size of the group that the wine is in now.

The tool writes one pair to the file that `manual_groups_file` names. A group is a
connected component over the generated groups and these pairs, so:

- Two wines that are in no group make a new group. Its id starts with `m`.
- A wine that is in no group joins the group of the wine you name. The generated id
  of that group is kept.
- Two wines that are **each already in a group** are refused, with the two group ids
  in the message. A merge of two groups is a larger decision, and one pair cannot
  undo it. Take one wine out of its group first, by hand in the file.
- A pair that names two wines of one group changes nothing and says so.

`scripts/08_variants.py` never writes `manual_groups_file`, so a new run of the
script keeps every pair made by hand.

A perceptual hash was tried first and was dropped: a bottle photo is mostly bottle,
so the hash of the silhouette hides the label. Read `ResearchLog.md` for the numbers.

### Moving a photo to another wine slug

A search result often shows the right wine in the wrong bottle, so the photo belongs
to another slug. The `move` button under the photo, and the `m` key in the large
view, open the move dialog.

The dialog offers the five wines that the photo most likely belongs to, each with its
catalogue bottle photo, its name, and its producer. The order is:

1. a member of the variant group of this wine,
2. the same producer,
3. a wine whose name shares words with this wine, then the same grape and the same
   category.

A click on a row records the move. A field below takes any of the 2,103 catalogue
slugs, with completion. `clear the move` removes a recorded move. `Esc` and `cancel`
close the dialog and change nothing.

#### The sideboard

The panel at the right of the page is the sideboard. It is a second way to move a
photo, for the case where the target wine is not yet known.

1. Drag the card of a photo to the panel. The photo leaves the row of its wine and
   waits in the panel. Nothing is sent to the server.
2. Scroll to another wine and drag the card to its row. The tool records the move,
   exactly as the `move` button does.
3. A drop on the row of the wine that the photo comes from puts the photo back.
   The button `put back` on the card does the same.

A card that stands in a wine row may also be dragged straight to another wine row.
The rule is the same for every card.

**Hide it or show it.** The button `sideboard` at the right of the header hides the
panel and shows it again, and so does the key `s` and the `×` in the head of the
panel. The button always states how many photos the panel holds, so a photo is not
forgotten while the panel is hidden. The choice is kept in the browser and holds
over a reload. A drag of a photo card shows the panel again by itself, because the
photo needs a target on the screen.

While the panel is shown, the header and the table keep the room free at the right
edge. While it is hidden, the page uses the whole width.

The sideboard lives in the browser tab. A reload empties it, a second tab does not
see it, and the server never learns about it. A photo in the sideboard keeps its
label until a target is chosen and `apply` runs. `apply` carries out the recorded
moves and states nothing about a photo that still waits in the sideboard.

#### The move is recorded, not performed

The tool does NOT move the file when the move is recorded. The target is written to
the label file as `reassign_to`, and the card gets a dashed outline. The header then
states `N moves pending` with an `apply` button.

The files move when `apply` is pressed, or when the script is run:

```bash
python3 scripts/09_apply_moves.py            # report only
python3 scripts/09_apply_moves.py --apply    # move the files
```

Both use the same functions of `review_server.py`, so both act the same way.

#### What a move does to the annotation

A moved photo loses its **label**. The label judged the photo against the old wine,
so it says nothing about the new wine. The photo MUST be reviewed again.

The **comment** is kept, and one line is put in front of it:

```
до переноса в <new slug> был в <old slug> с таким комментарием:
<the earlier comment>
```

A photo with no comment gets the first line alone. The entry also gets the field
`moved_from`, and `reassign_to` is dropped, so a second run moves nothing.
A file name that is taken in the target directory gets a `_moved2` suffix.

### Copying a photo to a second wine slug

One picture sometimes shows two wines. The same label stands on two bottles of a
variant group, and the photo is a true photo of both. A move is then wrong, because
a move takes the photo away from the first wine. The `copy` button under the photo,
and the `c` key in the large view, open the same dialog in copy mode.

The dialog is the dialog of the move, with the same five suggestions and the same
field for any slug. `clear the copy` removes a recorded copy.

#### The copy is recorded, not performed

The tool does NOT copy the file when the copy is recorded. The target is written to
the label file as `copy_to`, and the card gets a dotted outline. The header then
states `N copies pending` with an `apply` button. The same `apply` button, and the
same script, carry out the copies, the moves, and the deletions:

```bash
python3 scripts/09_apply_moves.py            # report only
python3 scripts/09_apply_moves.py --apply    # move and copy the files
```

The copies run before the moves, because a move takes the source file away.

#### What a copy does to the annotation

The source photo does NOT change. It keeps its slug, its label, and its comment.
The field `copy_to` is dropped when the copy is written, so a second run copies
nothing.

The copy is a new candidate photo of the target wine. It carries **no label**,
because a label judges one photo against one wine, and the wine is another one now.
The copy MUST be reviewed against its new wine. Its comment is one line:

```
копия фотографии из <source slug>
```

The entry of the copy also gets the field `copied_from`. The copy keeps the file
name of the source, which holds the confidence value of the source wine. That value
says nothing about the target wine. A file name that is taken in the target
directory gets a `_copy2` suffix.

A photo that carries both a copy and a `delete` mark is deleted and is not copied.

### Validating the photo set

The button `validate` in the header opens a dialog with one line per check. Choose
the checks and press `run`. A check only reads. It writes no file and no label.

The table then shows only the wines that fail at least one check, and it holds that
view until you change the filter. The count line states how many findings were made
and how long the run took. Every photo that a check reports carries a red outline and
a pill at the top left; the pill states how many wines share the picture, and its
tooltip names the other wine and the other file.

The result lives in the browser tab. A reload empties it, and the filter
`failed a check` then shows nothing until a new run.

#### The checks

| id | What it reports |
|---|---|
| `shared_positive` | One picture that carries the label `positive` under two or more slugs. |

`shared_positive` reads every candidate photo and compares the bytes. One picture
cannot show two wines, so such a pair is a defect of the set: either one label is
wrong, or the two catalogue cards are one wine. A pair of wines that are in one
variant group is reported too, and the pill states `same group`, because a variant
group is the same wine in two bottles and the group itself may be wrong.

A re-encoded copy or a resized copy of the same picture has other bytes, and this
check does not find it.

One run reads the 2,543 candidate photos, about 510 MB, and takes about 2.5 seconds.
The result is not cached. The lock is held only long enough to take the rows and the labels, so
a label of the reviewer is not blocked while a check runs.

#### Adding a check

The checks live in `scripts/review_server.py`, above `plan_deletes`. Write a function
`check_<name>(rows, labels, groups)` that answers a list of findings, and name it in
`CHECKS` with an `id`, a `title`, and a `help` text. A finding MUST hold `check` and
`why`, and it SHOULD hold `photos` (a list of `{slug, file}`) or `slugs`. The dialog
reads `GET /api/checks`, so a new check reaches the page with no change of the page.

### Adding a photo by drag and drop

Drag an image file from the file manager onto the row of a wine, and the tool adds
the file to `my/<slug>/`. The row is outlined while the file is over it. Several
files at a time are accepted, and a file that is not an image is refused.

A hint at the bottom of the window states the two ways to drop while a file is over
the page:

- **On the row of a wine.** The file goes to that wine at once.
- **Anywhere beside the table.** A dialog asks for the wine. Type a part of a slug, a
  name, or a producer, and the dialog offers five wines with their bottle photo. A
  click on one adds the files and scrolls the table to that wine. The field also
  completes from the slugs of `my/`.

The table is NOT drawn again after a drop. Only the row of the wine is brought up to
date: its cards, its photo count, and its mark. A row therefore stays where it is,
also when it no longer matches the selected filter. Under the filter `no candidate
photos (catalogue gap)` the wine would leave the table as soon as its first photo
lands, and the next row would jump under the pointer. Reload the page to filter
again.

A drop on a row works for every wine of the table, also for a wine with no candidate
photo. Such a wine is a card of the catalogue with no directory in `my/`. The write
makes the directory, and the wine becomes a wine of the review set: it leaves the
filter `no candidate photos (catalogue gap)` and enters the counters.

The dialog for a drop beside the table names only the wines that already have a
directory in `my/`. To give a first photo to a wine of the catalogue, drop the file
on its row.

#### From another browser tab

A picture dragged from another browser tab, such as a shop page or an image search,
is accepted the same way, on a row or beside the table.

Such a drag carries no file. It carries the address of the picture, as
`text/uri-list`, as an `<img>` element in `text/html`, or as plain text. The browser
may not read the bytes of another site, so the **server** fetches the address through
`POST /api/fetch-image`. A `data:` address is decoded without a request.

The media type comes from the first bytes of the file, not from the answer of the
host. Several picture hosts send no `Content-Type` or a wrong one; the first bytes
are the only reliable statement. An address that does not answer with a picture is
refused, and the reason names what the host sent.

The server refuses an address that is not `http` or `https`, and an address whose
host resolves to a loopback, private, link-local, reserved, or multicast address. A
dragged link MUST NOT reach a service of this machine or of the local network.

The request carries a browser user agent string, because many picture hosts refuse a
plain Python agent. A host can still refuse the request; the tool then states the
error and adds nothing.

The new file is named `<next number>_manual.<extension>`, so it sorts after the
photos that the pipeline found and is easy to tell apart. It carries no `conf`
value. A file is at most 20 MB, and the type MUST be JPEG, PNG, WebP, GIF, or BMP.

### The large view

A click on a candidate photo opens the large view. The large view shows two images
side by side: the catalogue bottle at the left, the candidate photo at the right.
The two images stay next to each other in the middle, also on a wide monitor.
A click on the catalogue bottle in the table opens the same view at the first photo.
A click on a large image does not close the view.

A wine with no candidate photo opens too. The view then shows the catalogue bottle
alone, the candidate side stays empty, and the badge states `no candidate photo for
this wine`. This is the state of every wine of the filter `no candidate photos
(catalogue gap)`. The keys `1` to `4` and `m` do nothing there, because there is no
photo to label and no photo to move. The comment field is closed for the same
reason: a comment belongs to a photo. A wine with neither a candidate photo nor a
catalogue bottle does not open, and `Down` and `Up` step over it.
A click on the background closes the view. `Esc` also closes it.

The large view holds the keyboard. The keys are:

| Key | Work |
|---|---|
| `Right` / `Left` | Go to the next or the previous photo of this wine. The keys stop at the ends. |
| `Down` / `Up` | Go to the next or the previous wine, at its first photo. |
| `1` | Label `positive`. `1` again clears the label. |
| `2` | Label `negative`. `2` again clears the label. |
| `3` | Label `unusable`. `3` again clears the label. |
| `4` | Label `variant`, this wine in another design. `4` again clears the label. |
| `m` | Move this photo to another wine slug. |
| `Esc` | Close the large view. |

The `Up` and `Down` keys follow the order that the table shows, so the sort and the
filter also control the keyboard pass. Sort by `unlabelled first`, open the first
photo, then work with `1`, `2`, `3`, `Right`, and `Down` only.
A badge at the top of the large view states the label of the photo on screen.
The caption under the candidate photo states the place in the wine and the label
progress of the wine.
The table row behind the large view scrolls with the keys, so the place is held when
the view closes.

### The comment panel

The large view holds a panel at the right. The panel takes a free text comment about
one photo and one wine slug: what is wrong, what is unclear, what the next reviewer
MUST check. The text belongs to the pair, not to the wine, so every photo has its own
comment.

The text is saved as it is typed, after a pause of 600 ms. A move to another photo,
a close of the view, and a close of the page flush the pending text first. The state
line under the field states `typing...`, `saving...`, `saved`, or the error.
The `clear` button empties the field and removes the comment.

A photo with a comment carries a round badge in the top right corner of its card in
the table. Hold the pointer over the badge to read the whole text; the panel that
opens keeps the line breaks and scrolls when the text is long. The row states
`N noted`.
The filter `holds a comment` lists the wines that hold a comment.

While the cursor is in the field, the keys `1` to `4`, the arrows, and `m` do not
act. Press `Esc` once to leave the field, and `Esc` again to close the large view.

A comment is at most 4000 characters. The tool refuses a longer text and writes
nothing.

### The address of one photo

The large view writes its place into the address of the page:

```
http://127.0.0.1:8154/#<slug>/<photo file name>
http://127.0.0.1:8154/#agora-saperavi/02_conf095.jpg
```

Copy the address to point another person at one photo. Open such an address and the
tool opens the large view at that photo. The filter and the search are cleared when
the wine is not in the current view, so a pasted address always opens.
The address is written with `replaceState`, so the arrow keys do not fill the history.

### The label file

Every click is written to `review-labels.json` at once. The format is:

```json
{
  "version": 2,
  "updated": "2026-09-15T14:14:12+0300",
  "counts": { "positive": 1, "negative": 1, "unusable": 0, "variant": 0,
              "labelled": 2, "reassigned": 1, "commented": 1, "wine_notes": 1 },
  "wines": { "<slug>": { "comment": "a note about the whole wine", "ts": "..." } },
  "labels": {
    "<slug>": {
      "<photo file name>": { "label": "positive", "ts": "..." },
      "<other photo>": { "label": "negative", "reassign_to": "<other slug>",
                         "comment": "same label, but the capsule differs",
                         "ts": "..." }
    }
  }
}
```

The tool reads the file again at the next start, so a pass can stop and continue.
A label whose photo is no longer in `my/` is dropped at start.

The tool reads the slug-to-bottle-photo map from the file that `catalog_file` names in
`config.yaml`. The default value is `svoe-wino-hackaton/derived/catalog.jsonl`.
`../svoe-wino-hackaton/scripts/build_catalog.py` writes that file.
4 of the 814 wines have no catalogue bottle photo. The row states the reason.

The tool uses the Python standard library and `PyYAML`. `PyYAML` reads `config.yaml`.

## Excluded slugs

Some slugs of the `vino-svoe.ru` catalogue hold an error. The most frequent error is a
wrong bottle photo: the card shows a different wine. The bottle photo is the reference
of the benchmark, so a wrong reference shifts the metrics of the whole test set.

Such a slug is excluded. `excluded-slugs.json` names every excluded slug and states the
error. The photos of an excluded slug stay on the disk, but they MUST NOT be used for
benchmarking.

The review tool holds an `Exclude` button under the bottle photo of each row. An
excluded row is red. The control `Slugs` filters the table to `all`, `included`, or
`excluded`.

Read `docs/excluded-slugs.md` for the format of the file and for the rule of a consumer.

## The match runner

`scripts/match_run.py` sends every annotated photo to one recognizer and writes the
answer into `runs/<UTC time>-<backend>/`. One directory is one run, so two backends or
two versions of one backend are compared side by side.

```bash
python3 scripts/match_run.py --list-backends
python3 scripts/match_run.py --backend official-api
python3 scripts/match_run.py --backend organizers --limit 50 --label smoke
python3 scripts/match_run.py --dry-run          # build the manifests, call nothing

# repeat only what failed in an earlier run
python3 scripts/match_run.py --backend my-service --from-run runs/<run id>
python3 scripts/match_run.py --backend my-service --from-run runs/<run id> --rerun-depth 10
```

`--from-run` asks the backend only about the photos that failed before, so the answer to
"did the change help?" costs one request per failure instead of one per photo.
`--rerun-depth K` states how many candidates count as an answer: 1 repeats every photo
that was not correct at rank 1, and 10 repeats every photo whose true slug was not in the
first 10. The shares of such a run cover the repeated photos only, and every file of the
run states it.

The query set holds 979 `positive` photos and 364 `negative` photos. A `positive` photo
is correct when the recognizer answers with its slug. A `negative` photo shows a
different wine, so the recognizer is wrong when that slug stands at rank 1. `variant`
photos stay out unless `--variants` asks for them. A photo of an excluded slug never
enters the set.

The run directory holds `predictions.jsonl` in the exact format of the organizers, so
the same run serves as the submission. It also holds `results.jsonl` with every
candidate and its score, `metrics.json` with R@1, R@5, R@10, the rank histogram, and the
negative outcomes, and `summary.md` for a human.

`backends.yaml` defines a backend. A token MUST NOT stand in that file: a header value
`env:NAME` is read from the environment.

The navigation at the top right of the header holds `Review` for `/` and `Runs` for
`/runs`. Both pages hold it.

The metrics follow the specification of the task: the share of the matches against its
target of 90 to 100 percent, the F1 of the top-1 and of the top-5 cards, the share of
the answers inside the SLA of 3 seconds, the gap between the first and the second
candidate, and the near-duplicate errors, which the specification names as the main
source of the mistakes.

The review tool shows the runs at `http://127.0.0.1:8154/runs`: the table of the runs,
the metrics of the selected run, and one row per photo with the candidates that came
back. A click on a column sorts the runs; the control `Sort` orders the photos, for
example the most wrong first. The expected wine carries a green border, and the wine that a negative photo MUST
NOT match carries a red one.

Read `docs/match-runner.md` for every file, every field, and every option.

## The agent API

`scripts/review_server.py` answers an HTTP API under `/api/v1/` for an agent, such as
Claude Code. Read `docs/API.md` for every route and every field.

`docs/openapi.yaml` holds the same contract in machine-readable form, for every route
of the server. Open `http://127.0.0.1:8154/docs` in a browser to read it, or fetch
`/openapi.yaml` or `/openapi.json` to feed a client generator.

The idea: an agent walks the wines that hold no confirmed photo, searches the web for
a real-world photo, checks it against the catalogue bottle, and writes a **proposal**.
The reviewer confirms the proposals later, in the same page.

```bash
curl -s "http://127.0.0.1:8154/api/v1/wines?filter=needs_positive&limit=1"
curl -s "http://127.0.0.1:8154/api/v1/wine/<slug>"
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"slug":"<slug>","url":"<picture>","proposed":"positive","confidence":0.9,
       "source_url":"<page>","comment":"the label and the capsule match"}' \
  http://127.0.0.1:8154/api/v1/propose
```

An agent MUST NOT write a label. A proposal is not counted in `labelled`. The card of
a proposed photo has a dashed border and a tag with the confidence, and the filter
`holds a photo proposed by an agent` lists them. The reviewer answers with the keys
`1` to `4`, and only then the photo holds a label.

The skill `wine-hunt` in `.claude/skills/wine-hunt/` holds the working instructions
for the agent: which queries to use, what to compare, and when NOT to propose.

## Reports

- `report.html` — thumbnails for visual review. Open it in a browser.
- `REPORT.md` — the same table in Markdown.
- `report.csv` — machine-readable form.

Rows are sorted with the weakest evidence first: wines with fewer than 3 photos,
then the lowest confidence, then the average confidence.

## Search engines

Yandex Images is the primary engine. It answers about 30 results per query.
Three queries run per wine: `site:irecommend.ru`, `site:otzovik.com`, and a plain review query.
DuckDuckGo is secondary. It rate-limits this host quickly and disables itself for 15 minutes.

Search results are noisy. A query for one wine often returns a different wine of the same
grape or the same producer. Stage 4 is the filter that removes them.

## Working data location

`work/raw` and `work/thumbs` are symbolic links to `/Volumes/Storage/svoe-vino-testset-work/`.
The volume `/Volumes/T7_2TB` was full when the set was built.
The database keeps absolute paths, so the links MUST stay in place.

## The `api_rank` column

`report.csv` carries `imgN_api_rank` for each photo. It is the rank of the expected slug
in the answer of the official recognizer, and `0` means the recognizer missed the wine.
Use it to split easy photos from hard photos. It is not a correctness label:
the recognizer misses many photos that are correct but hard.
