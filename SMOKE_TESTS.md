# Smoke tests

Manual test cases. Run them after a change to the tool.

## Labelling tool — `scripts/review_server.py`

Start the tool with `python3 scripts/review_server.py --no-browser`.
Use `H=http://127.0.0.1:8154` for the command line cases.

| # | Case | Expected result |
|---|---|---|
| 1 | Start the tool | The log states first the configuration: the path of `config.yaml`, `rootdir`, every configured path, and the work directory. It then states the wine count, the photo count, the loaded label count by label, and the URL. The start takes a few seconds, not minutes. |
| 2 | `curl -s -o /dev/null -w "%{http_code}" $H/` | `200` |
| 3 | `curl -s $H/api/rows` | JSON with 814 rows and 1,892 photos. Each row has `slug`, `name`, `producer`, `photos`, `min_conf`, `has_bottle`. |
| 4 | Open the page in a browser | One row per wine. The bottle photo is at the left. The candidate photos are at the right. Every photo has three buttons: `V`, `N`, and `x`. |
| 5 | Scroll the page | Photos load as the rows come into view. The page stays responsive. |
| 6 | Click `V` on one photo | The card turns green. The `V` button fills. The counter at the top right grows by one. |
| 7 | Click the same `V` again | The label is cleared. The card returns to the neutral colour. The counter falls by one. |
| 8 | Click `N` on a photo that holds a `V` | The card turns blue and is NOT dimmed. A negative sample is kept, so it MUST NOT look like waste. Only one of the three buttons is filled. |
| 8a | Click `x` on a photo | The card turns grey and is dimmed. This is the only label that takes the photo out of the set. |
| 9 | `cat review-labels.json` after a click | The file holds `"label"` with one of `positive`, `negative`, `unusable`, a timestamp, and the `counts` block. The file is written at once, with no extra step. |
| 10 | Stop the tool and start it again | The log states the loaded label count by label. The page shows the same green, blue, and grey cards. |
| 11 | Change the sort to `unlabelled first` | Wines with no label come first. Fully labelled wines come last. |
| 12 | Change the sort to `confidence, lowest first` | The wine with the lowest `conf` value in its file names comes first. |
| 13 | Change the filter to `has no positive photo` | Every listed wine holds no green card. The count line states how many wines are shown. |
| 13a | Change the filter to `has a negative sample` | Every listed wine holds at least one blue card. |
| 14 | Type a producer name in the search field | Only the matching wines stay. The search covers slug, name, producer, region, and grape. |
| 15 | Click a candidate photo | The large view opens. The catalogue bottle is at the left. The candidate photo is at the right. Each image has a caption. |
| 15a | Click one of the two large images | The view stays open. |
| 15b | Click the background of the large view, then press `Esc` on the next open | The view closes in both cases. |
| 15c | Click a candidate photo of a wine that has no catalogue bottle photo | Only the candidate photo is shown. The layout does not break. |
| 15d | Click the catalogue bottle in the table | The large view opens at the first photo of that wine. |
| 15e | On a wide monitor, open the large view | The two images stand next to each other in the middle. They do not sit at the two edges. |
| 15f | Press `Right`, then `Left` | The candidate photo changes inside the wine. The catalogue bottle does not change. The caption counts `photo N of M`. |
| 15g | Press `Right` at the last photo, `Left` at the first | The view stays at the same photo. |
| 15h | Press `Down`, then `Up` | The wine changes. The catalogue bottle changes. The view opens at the first photo of that wine. The table behind scrolls to the same wine. |
| 15i | Set the filter to `no verdict yet`, then press `Down` | The keys move only through the wines that the table shows. |
| 15j | Press `1` | The badge states `positive — this wine`. The card turns green. The counter grows. `review-labels.json` holds `"label": "positive"`. |
| 15k | Press `1` again | The badge states `not labelled`. The label is cleared. |
| 15l | Press `2` on a photo that holds a `1` label | The badge states `negative sample — a different wine`. Only one label is held. |
| 15o | Press `3` | The badge states `unusable — not in the set`. The card turns grey and dims. |
| 15m | Press `1`, then `Right`, then `Left` | The image does not flicker. The badge holds the correct label of each photo. |
| 15n | Press an arrow key while the large view is closed | The page scrolls as usual. The keys do not act. |
| 16 | Find a wine with no catalogue bottle photo | Column 1 states `no bottle photo` or `not in catalogue`. There are 4 such wines. |
| 17 | `curl -s "$H/img/photo?slug=agora-saperavi&file=01_conf095.jpg"` | `200`, content type `image/jpeg`. |
| 18 | `curl -s "$H/img/photo?slug=agora-saperavi&file=../../CLAUDE.md"` | `404`. The tool serves no file outside `my/`. |
| 19 | POST a label for a photo that does not exist | `{"error": "unknown photo"}`. The file is not changed. |
| 20 | POST a label other than `positive`, `negative`, `unusable`, or empty | `{"error": "label MUST be one of 'positive', 'negative', 'unusable', or empty"}`. |
| 21 | Delete one labelled photo from `my/`, then restart the tool | The log states `dropped 1 label(s)`. The counts fall by one. |
| 22 | Open the page with the system theme set to dark, then to light | The page follows the system theme in both directions. |
| 23 | Narrow the window to about 400 px | The row stacks into two blocks. The page does not scroll sideways. |
| 24 | Open the large view | The address of the page becomes `#<slug>/<photo file name>`. |
| 25 | Press `Right`, then `Esc` | The address follows the photo, then the fragment is removed. |
| 26 | Copy the address, open it in a new tab | The large view opens at the same photo of the same wine. |
| 27 | Set a filter that hides one wine, then open that wine by its address | The filter and the search are cleared, and the view opens. |
| 28 | Open an address whose slug or file name does not exist | The page opens as usual, with no large view and no error. |
| 29 | Press the browser Back button after many arrow presses | The page does not step through every photo. The address is written with `replaceState`. |
| 30 | Run `python3 scripts/08_variants.py --no-image` | It reports 28 groups over 63 wines and writes `derived/variant-groups.json`. |
| 31 | Restart the tool | The log states `variant groups: 28   wines in a group: 63`. |
| 32 | Find `abrau-dyurso-pino-nuar-krasnoe-suhoe-12` | Its row and the row of `...-125` stand next to each other and share a background colour. Both rows carry the tag `variant group of 2`. |
| 33 | Change the sort, then look at the same pair | The two rows stay next to each other in every sort order. |
| 34 | Set the filter to `has a similar wine (variant group)` | 63 wines are shown, in 28 coloured blocks. |
| 35 | Look at two groups that stand next to each other | Their background colours differ. |
| 36 | Press `4` in the large view | The badge states `this wine, different design`. The card turns amber and is not dimmed. |
| 37 | Click `copy` next to a slug | The button reads `copied` for a moment. The clipboard holds the slug. |
| 38 | Click `move` under a photo and type a target slug | The card gets a dashed outline and the button reads `-> <slug>`. `review-labels.json` holds `reassign_to`. |
| 39 | Click `move` again and clear the field | The outline and the `reassign_to` field are gone. The label of the photo is NOT lost. |
| 40 | Press `m` in the large view | The same question is asked for the photo on screen. |
| 41 | Type a target slug that does not exist | `{"error": "unknown target slug: ..."}`. Nothing is written. |
| 42 | Type the slug of the photo itself | `{"error": "the target slug is the slug of the photo"}`. |
| 43 | Run `python3 scripts/09_apply_moves.py` | It lists every recorded move and states `report only`. No file is moved. |
| 44 | Run it again with `--apply`, then a third time | The files are moved. The third run states `already done` and moves nothing. |
| 45 | Label a photo, then move it, then clear the label | The `reassign_to` field stays. The entry is removed only when both fields are gone. |
| 46 | Open the large view | A panel stands at the right of the two images. It names the slug and the file. |
| 47 | Type a comment, then wait a second | The state line goes `typing...`, `saving...`, `saved`. `review-labels.json` holds the `comment` field. |
| 48 | Type `1` inside the field | The character `1` is written. The photo is NOT labelled. |
| 49 | Press `Esc` in the field, then `Esc` again | The first press leaves the field. The second closes the large view. |
| 50 | Type a comment and press `Right` at once, without a pause | The text is saved before the next photo opens. Return to the photo; the text is there. |
| 51 | Type a comment and close the view at once | The text is saved. |
| 52 | Click in the panel, on the field, and on the `clear` button | The large view stays open. |
| 53 | Press `clear` | The field empties, the comment is removed, and the label of the photo stays. |
| 54 | Look at a commented photo in the table | The card carries a bar at the left. The tooltip holds the comment. The row states `N noted`. |
| 55 | Set the filter to `holds a comment` | Only the wines with a comment are shown. |
| 56 | POST a comment of more than 4000 characters | `{"error": "comment is longer than 4000 characters"}`. Nothing is written. |
| 57 | Add a comment to a photo that holds no label, then clear the comment | The entry of the photo is removed. The labels of the other photos of the wine stay. |
| 58 | Narrow the window to about 900 px | The panel moves under the images. The page does not scroll sideways. |
| 59 | Record a move, then look at the header | It states `1 move pending` with an `apply` button. |
| 60 | Press `apply` and confirm | The file is moved. A report names every move. The table is rebuilt and the counter is gone. |
| 61 | Look at the moved photo in its new wine | It carries no label. Its comment starts with `до переноса в ... был в ...`. |
| 62 | Press `apply` with nothing pending | The button is not shown. |
| 63 | Run `python3 scripts/09_apply_moves.py --apply` twice | The second run states `nothing to move`. |
| 64 | Click `move` under a photo | A dialog opens with five wines, each with its bottle photo, name, and producer. |
| 65 | Look at the first row of the dialog for a wine of a variant group | It is a member of that group and carries the tag `variant group`. |
| 66 | Click a row of the dialog | The move is recorded and the dialog closes. |
| 67 | Type a slug in the field and press Enter | The same. |
| 68 | Press `clear the move`, then `cancel` on the next open | The move is removed; the second open changes nothing. |
| 69 | Press `Esc` in the dialog | The dialog closes. The large view stays open. |
| 70 | Press `1` while the dialog is open | The photo is NOT labelled. |
| 71 | Drag an image file onto the row of a wine | The row is outlined, then the photo appears at the end of the row as `NN_manual.<ext>`. |
| 72 | Drag two images at once | Both are added. |
| 73 | Drag a file that is not an image | The tool refuses it and states so. |
| 74 | Drag an image larger than 20 MB | The tool refuses it and states so. |
| 75 | Drag an image onto a page area that is not a row | Nothing happens. The browser does not open the file. |
| 76 | Write a comment on a photo, then look at its card | A round badge stands in the top right corner of the card. |
| 77 | Hold the pointer over the badge | A panel opens with the whole comment. The line breaks are kept. |
| 78 | Move the pointer from the badge onto the panel | The panel stays open and can be scrolled. |
| 79 | Clear the comment from the panel of the large view | The badge is gone at once, with no page reload. |
| 80 | Look at a photo that was moved by `apply` | Its badge holds the line `до переноса в ... был в ...`. |
| 81 | Drag a file over the page | A hint appears at the bottom of the window. |
| 82 | Drop a file beside the table | A dialog asks for the wine and names the dropped files. |
| 83 | Type three letters of a producer in the dialog | Up to five wines are offered, each with its bottle photo. |
| 84 | Click one of them | The photos are added and the table scrolls to that wine. |
| 85 | Type a slug that has no directory in `my/` | The dialog states that and adds nothing. |
| 86 | Press `Esc` in the dialog | The dialog closes and nothing is added. |
| 87 | Press `1` while the dialog is open | The photo behind is NOT labelled. |
| 88 | Drag a picture from another browser tab onto the row of a wine | The picture is fetched and added as `NN_manual.<ext>`. |
| 89 | Drag a picture from another tab beside the table | The dialog opens and names the address. |
| 90 | Drag a picture whose host sends no `Content-Type` | The type is read from the first bytes and the picture is added. |
| 91 | Drag a link to a page that is not a picture | The tool states `the address does not answer with a picture` and adds nothing. |
| 92 | POST `/api/fetch-image` with `http://127.0.0.1:8154/` | `the address points at a local host`. |
| 93 | POST `/api/fetch-image` with a host on the local network | The same refusal. |
| 94 | POST `/api/fetch-image` with `file:///etc/passwd` | `only an http or https address can be fetched`. |
| 95 | Drag selected text, not a picture | Nothing is added and no error box appears. |
| 96 | Look at the wine column | A one line field stands under the data of the wine. |
| 97 | Click the field and type a note | The field opens larger. After a pause the text is in `review-labels.json` under `wines`. |
| 98 | Type and keep typing for ten seconds | The table is not drawn again. The cursor stays in the field. |
| 99 | Click outside the field at once after typing | The text is saved. |
| 100 | Reload the page | The note is in the field, and the field is open. |
| 101 | Empty the field | The note is removed and `wine_notes` falls by one. |
| 102 | Type `1` in the field | The character is written. No photo is labelled. |
| 103 | Sort or filter the table while a note is saved | The note is not lost. |

## The agent API — `/api/v1/`

| # | Case | Expected result |
|---|---|---|
| A1 | `GET /api/v1/stats` | The wine count, the photo count, the counts, `variant_groups`, `excluded_wines`, and `excluded_photos`. |
| A2 | `GET /api/v1/wines?filter=needs_positive&limit=2` | Only the wines with no positive photo. `total` states the size of the queue. |
| A3 | `GET /api/v1/wine/<slug>` | The catalogue fields, `bottle_path`, `photos` with an absolute `path` each, and `variant_group`. |
| A4 | Read a `path` from A3 with a file tool | The picture opens. |
| A5 | `GET /api/v1/wine/<slug>/photos?label=positive` | Only the confirmed photos. |
| A6 | `GET /api/v1/wine/nope` | `404` and `unknown wine slug`. |
| A7 | `POST /api/v1/propose` with a picture address | `ok`, the file is `NN_agent.<ext>`, and `counts.proposed` grows. |
| A8 | Look at `counts.labelled` after A7 | It did NOT grow. A proposal is not a label. |
| A9 | `POST /api/v1/propose` with `confidence: 5` | `confidence MUST be between 0 and 1`. |
| A10 | `POST /api/v1/propose` with `proposed: "maybe"` | The error names the four labels. |
| A11 | Look at the proposed card in the page | A dashed border and a tag with the confidence. |
| A12 | Set the filter `holds a photo proposed by an agent` | Only the wines with a proposal are shown. |
| A13 | Press `1` on a proposed photo | It holds a label now, and `counts.labelled` grows. |
| A16 | `POST /api/v1/propose` with a local address | The address is refused, as in test 92. |
| A17 | `POST /api/v1/search-by-image` | `unknown API path`. The matching is the work of an external application. |

## Configuration — `config.yaml`

| # | Case | Expected result |
|---|---|---|
| C1 | `python3 -c "import sys; sys.path.insert(0,'scripts'); import common; common.print_config()"` | The path of `config.yaml`, `rootdir`, the 6 configured paths, and the work directory. |
| C2 | Start the tool from another directory, such as `cd /tmp && python3 <abs path>/scripts/review_server.py --no-browser` | The same paths as in C1. The work directory line states `/tmp`. The tool finds the photo set. |
| C3 | Set `photo_dir` to a directory that does not exist, then start the tool | The line of `photo_dir` gets the mark `(absent)`. The tool stops with `error: photo set not found`. |
| C4 | Set `catalog_file` to an absolute path | The path stays as it is. It is not joined to `rootdir`. |
| C5 | Remove a key from `config.yaml`, then run C1 | The earlier default path is used. No error is raised. |
| C6 | `python3 scripts/08_variants.py --help` after a change of `variant_groups_file` | The script writes the groups to the configured file. The review tool reads the same file. |

## Excluded slugs — `excluded-slugs.json`

| # | Case | Expected result |
|---|---|---|
| E1 | Press `Exclude` under the bottle photo of one row, then cancel the question | Nothing changes. The file is not written. |
| E2 | Press `Exclude` and state a reason | The row turns red. The button reads `Excluded`. The reason stands under the button. |
| E3 | `cat excluded-slugs.json` after E2 | The slug is a key of `excluded`, with `reason` and `ts`. `count` is 1. |
| E4 | Press `Excluded` and confirm | The red colour goes away. The entry is removed from the file. |
| E5 | Set `Slugs` to `excluded` | Only the excluded wines are shown. The count line states their number. |
| E6 | Set `Slugs` to `included` | The excluded wines are not shown. |
| E7 | Set `Slugs` to `all` | Every wine is shown again. This is the default value. |
| E8 | `curl -s -X POST -H "Content-Type: application/json" -d '{"slug":"<slug>"}' $H/api/exclude` | `a reason is needed to exclude a slug`. |
| E9 | The same call with an unknown slug | `unknown wine slug`. |
| E10 | `curl -s "$H/api/v1/wines?limit=500"` after E2 | The excluded wine is NOT in the list. |
| E11 | The same call with `&include_excluded=1` | The wine is in the list, with `"excluded": true`. |
| E12 | `curl -s "$H/api/v1/stats"` after E2 | `excluded_wines` and `excluded_photos` are not zero. |
| E13 | Stop the tool and start it again | The log states the number of the excluded slugs and of their photos. The rows are red again. |
| E14 | An excluded wine that is also in a variant group | The red colour wins over the colour of the group. |
