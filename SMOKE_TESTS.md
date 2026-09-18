# Smoke tests

Manual test cases. Run them after a change to the tool.

## Labelling tool — `scripts/review_server.py`

Start the tool with `python3 scripts/review_server.py --no-browser`.
Use `H=http://127.0.0.1:8154` for the command line cases.

| # | Case | Expected result |
|---|---|---|
| 1 | Start the tool | The log states first the configuration: the path of `config.yaml`, `rootdir`, every configured path, and the work directory. It then states the wine count, the photo count, the loaded label count by label, and the URL. The start takes a few seconds, not minutes. |
| 2 | `curl -s -o /dev/null -w "%{http_code}" $H/` | `200` |
| 2a | Open `$H/` and look at the top right of the header | The navigation holds `Review` and `Runs`. `Review` is the marked link. A click on `Runs` opens `/runs`. |
| 2b | Drag a photo card to the sideboard at the right | The card leaves the row of its wine and stands in the panel. The counter beside `Sideboard` rises. No request is sent. |
| 2c | Drag the card from the sideboard to the row of another wine | The card stands again in the row of its own wine, with a dashed outline. Its button reads `→ <the target slug>`. The header states one more pending move. |
| 2d | Drag a held card to the row of the wine it comes from | The card stands again in that row. No move is recorded. |
| 2e | Press `put back` on a held card | The same result as case 2d. |
| 2f | Hold a photo, then reload the page | The sideboard is empty and the photo stands in its wine row. The sideboard lives in the browser tab alone. |
| 2g | Hold a photo with no target, then press `apply` | The recorded moves and the deletions are carried out. The held photo is not touched and `apply` states nothing about it. |
| 2h | Press the button `sideboard` in the header | The panel goes away. The table and the header use the whole width. |
| 2i | Press the button again, or the key `s` | The panel comes back. The header keeps the room free and no control of the header is covered. |
| 2j | Hold a photo, hide the panel | The button `sideboard` still states the count. |
| 2k | Hide the panel, then reload the page | The panel stays hidden. The choice is kept in the browser. |
| 2l | Hide the panel, then drag a photo card | The panel comes back by itself, because the photo needs a target on the screen. |
| 2m | Press `s` while the cursor stands in the search field | The letter is typed. The panel does not move. |
| 2n | Set the filter to `no candidate photos (catalogue gap)` and click the catalogue bottle of a row | The large view opens. It shows the bottle alone. The badge states `no candidate photo for this wine`. The comment field is closed. |
| 2o | Press `1`, `2`, `3`, `4` and `m` in that view | Nothing changes and no dialog opens. |
| 2p | Press `Down` and `Up` in that view | The view moves to the next and the previous wine of the filter. |
| 2q | Copy the address of that view and open it again | The same wine opens, with the filter `no candidate photos (catalogue gap)`. |
| 2r | Drop an image file on the row of a wine with no candidate photo | The photo is added. No message of refusal appears. The directory `my/<slug>/` is made. |
| 2s | Look at that row after the drop | It holds one card. It leaves the filter `no candidate photos (catalogue gap)` and it stands under the filter `all wines`. |
| 2t | Open `$H/?filter=nophotos` and drop an image on a row | The row stays in the table and keeps its place. The table is not drawn again and no other row moves. |
| 2u | Look at that row after the drop | It holds the new card, the line states `1 photo(s)`, and the text about the gap of the photo set is gone. |
| 2v | Select another filter and select `no candidate photos (catalogue gap)` again | The wine is gone from the list, because the filter runs again. A reload of the page does the same. |
| 2w | Search `cotes du don` with the filter `no candidate photos (catalogue gap)` | One row: `Цимлянский чёрный Côtes du Don`. The accent of the text is not typed. |
| 2x | Search `don cotes`, then `cotes du don tsimlyanskiy` | The same row. The order of the words does not matter and the words may stand apart in the text. |
| 2y | Search `chardonay` | The wines whose name holds `Chardonnay`. One letter is missing from the query. |
| 2z | Search `cimlyanskiy`, then `tsimlyanskiy`, then `czimlyanskoe` | Each query finds the wines of the others. The slugs write the letter `ц` in three ways. |
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
| 104 | Right-click a photo in the table | The menu holds `Copy Image`, `Copy Image URL`, `Download`, a line, and `Delete`. |
| 105 | Click `Copy Image` | The entry reads `copied` and the menu closes. A paste into an image editor shows the photo. |
| 106 | Click `Copy Image URL` | The entry reads `copied`. The clipboard holds `http://127.0.0.1:8154/img/photo?slug=...&file=...`. |
| 107 | Open the large view and right-click the candidate photo | The same menu opens with the same two entries. |
| 108 | Paste the copied address into another tab | The photo opens. |
| 109 | Click `copy` next to the name of a wine | The button reads `copied` for a moment. The clipboard holds the name, not the slug. |
| 110 | Look at a wine without a name | The line reads `unknown name` and carries no `copy` button. |
| 111 | Type `shardone` in `Find` | The address becomes `/?q=shardone`. |
| 112 | Reload that address | The field holds `shardone` and the table is filtered. |
| 113 | Set `Show` and `Sort` too | The address holds `q`, `filter` and `sort`. A control at its default is left out. |
| 114 | Empty the search | `q` leaves the address. |
| 115 | Open a photo while a search is active | The address holds both, `/?q=shardone#<slug>/<file>`. |
| 116 | Open `/?filter=nope` | The select stays at `all`. An unknown value is dropped. |
| 117 | Click `Group` under the bottle of a wine that is in no group | The dialog opens and states `in no group yet`. |
| 118 | Name a second wine that is in no group | Both rows stand next to each other in one colour. The group id starts with `m`. |
| 119 | Click `Group` on a third wine and name one of the two | The third wine joins the same group. The button reads `Group 3`. |
| 120 | Click `Group` on a wine of a generated group and name a wine that is in no group | The named wine joins the generated group. The id `g0NN` is kept. |
| 121 | Try to group two wines that are each already in a group | The dialog states both group ids and that a merge is not allowed. Nothing is written. |
| 122 | Group two wines that are already in one group | The dialog states `the two wines are already in one group`. Nothing is written. |
| 123 | Look at `manual-groups.json` | It holds one record per pair, with `a`, `b` and `ts`. |
| 124 | Run `python3 scripts/08_variants.py --no-image`, then reload the tool | Every pair made by hand is still in place. |
| 125 | Press Esc while the group dialog is open | The dialog closes. No pair is written. |
| 126 | Click `Download` in the menu of a photo | The menu closes and the browser saves the file. No tab opens. |
| 127 | Look at the saved file | Its name is `<slug>__<file>`, for example `abrau-dyurso-...__01_conf095.jpg`. |
| 128 | Download a photo of two different wines that hold the same file name | The two files stand apart in the download folder, because each name carries its slug. |
| 129 | Open the large view and click `Download` on the candidate photo | The same file is saved. |
| 130 | Click the tag `variant group of N` on a row | Only the wines of that group are listed. The count line names the group. |
| 131 | Look at the address | It holds `?group=g0NN`. |
| 132 | Reload that address | The same group alone is listed. |
| 133 | Look at the header while a group is shown | A chip `variant group <id> of N ×` stands beside `Find`. A plain view carries no chip. |
| 133a | Click that chip | Every wine is listed again and `group` leaves the address. |
| 133b | Click the tag `variant group of N` of the group you are already in | Every wine is listed again. The tag switches the group off. |
| 134 | Type a search, then click the tag of a group | The search field is cleared, so every member of the group reaches the screen. |
| 135 | Open `/?group=nope` | Every wine is listed. An unknown group id is dropped. |
| 136 | Type a search while a group is shown | The chip stays in the header. The address holds `q` and `group`. |
| 137 | Look at the `by name` line under a bottle | It carries no border and no background. It reads as a statement, not as a third button beside `Exclude` and `Group`. |
| 138 | Compare the four confidence states | `confirmed` is green, `assumed` is amber, `by hand` is blue, `no photo` is red. The text colour alone states it. |
| 139 | Look under a photo card | Two buttons stand there: `→ move` and `⧉ copy`. |
| 140 | Click `copy` under a photo | The move dialog opens with the head `Copy this photo to another wine`. The buttons read `copy` and `clear the copy`. The suggestions are the suggestions of the move. |
| 141 | Choose a target in that dialog | The card gets a dotted outline and the button reads `⧉ <slug>`. `review-labels.json` holds `copy_to`. The label of the photo is NOT lost. |
| 142 | Look at the header after that | It states `1 copy pending` with an `apply` button. The row states `1 copied`. |
| 143 | Click `copy` again and press `clear the copy` | The outline and the `copy_to` field are gone. The label of the photo stays. |
| 144 | Press `c` in the large view | The copy dialog opens for the photo on screen. `m` still opens the move dialog. |
| 145 | POST `/api/copy` with the slug of the photo itself | `{"error": "the target slug is the slug of the photo"}`. |
| 146 | POST `/api/copy` with a slug that does not exist | `{"error": "unknown target slug: ..."}`. Nothing is written. |
| 147 | Record a copy, then press `apply` and confirm | The warning names the copies first, then the moves. The file is written into the target wine. The source photo stays in its own wine, with its label. |
| 148 | Look at the copy in the target wine | It carries no label. Its comment reads `копия фотографии из <source slug>`. The entry holds `copied_from`. |
| 149 | Press `apply` a second time | Nothing is copied again. `copy_to` was dropped when the file was written. |
| 150 | Copy a photo to a wine that already holds a file of that name | The copy is named `<stem>_copy2.<ext>`. The report states the rename. |
| 151 | Record a copy and a move on one photo, then press `apply` | Both are carried out. The copy is made first, so the copy holds the picture and the source directory no longer does. |
| 152 | Record a copy, then mark the same photo for deletion, then press `apply` | The photo is deleted and is not copied. |
| 153 | Run `python3 scripts/09_apply_moves.py` | It states the recorded copies and the recorded moves, then `report only`. No file is touched. |
| 154 | Run it with `--apply` | The copies run before the moves. The report states how many files were copied and how many were moved. |
| 155 | Press `validate` in the header | A dialog opens with one line per check. Every check is on. The line states what the check reads and what it cannot find. |
| 156 | Take every check off and press `run` | The dialog states `choose at least one check` and stays open. |
| 157 | Press `run` with one check on | The button reads `checking...`. After a few seconds the dialog closes, the filter goes to `failed a check`, and the button `validate` is marked. |
| 158 | Look at the count line | It states how many findings were made, in how many wines, how many photos were read, and how long the run took. |
| 159 | Look at a wine in that view | Every reported photo carries a red outline and a pill at the top left. The pill states how many wines share the picture. |
| 160 | Point at the pill | The tooltip states the defect and names the other wine and the other file. |
| 161 | Look at a pair of wines of one variant group | The pill also reads `same group`. |
| 162 | Label a photo while that view is shown | The table does not change. The view holds until the filter is changed. |
| 163 | Change the filter, then set it back to `failed a check` | The same wines are shown again. The result lives in the tab. |
| 164 | Reload the page and set the filter to `failed a check` | The table is empty and the count line states `no check was run yet; press validate`. |
| 165 | `curl -s $H/api/checks` | `{"checks": [{"id": "shared_positive", "title": ..., "help": ...}]}`. No `run` field. |
| 166 | POST `/api/validate` with `{"checks": ["nope"]}` | `{"error": "unknown check: nope. The known checks are shared_positive"}`. |
| 167 | POST `/api/validate` with `{"checks": []}` | `{"error": "no check was chosen"}`. |
| 168 | POST `/api/validate` with no body | Every check runs. |
| 169 | Compare `review-labels.json` before and after a run | The file is not touched. A check only reads. |
| 170 | Mark one photo `positive` in two wines that hold the same picture, then run the check | Both wines are reported, and both photos are marked. |
| 171 | Make one of the two `negative`, then run the check again | The pair is no longer reported. |

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

## The OpenAPI document — `docs/openapi.yaml`

| # | Case | Expected result |
|---|---|---|
| O1 | `curl -s $H/openapi.yaml \| head -3` | The first line is `openapi: 3.1.0`. The media type is `application/yaml`. |
| O2 | `curl -s $H/openapi.json \| python3 -m json.tool \| head -3` | Valid JSON. The title is `Svoe Vino photo review API`. |
| O3 | Compare `/openapi.yaml` and `/openapi.json` | The two answer the same document. |
| O4 | Open `$H/docs` in a browser | Swagger UI lists every route, grouped by the tags `agent`, `images`, `spec`, `page`, and `runs`. |
| O5 | Set the operating system to the dark theme and reload `$H/docs` | The page is dark. The text stays readable. |
| O6 | Press `Try it out` on `GET /api/v1/stats` in `$H/docs` | The call answers `200` with the counters of the running tool. |
| O7 | Move `docs/openapi.yaml` away and call `/openapi.json` | `404` and `docs/openapi.yaml is not present`. Put the file back. |
| O8 | Break `docs/openapi.yaml` with a syntax error and call `/openapi.json` | `500` and `cannot read the document`. `/openapi.yaml` still answers `200`, because it does not parse the file. Put the file back. |
| O9 | Validate the document with `openapi-spec-validator` | No error. Run it after every change of a route. |
| O10 | Change a route of the server | `docs/openapi.yaml` states the change in the same commit. The document is written by hand. |

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

## The match runner — `scripts/match_run.py`

| # | Case | Expected result |
|---|---|---|
| M1 | `python3 scripts/match_run.py --list-backends` | Every backend of `backends.yaml` with its URL. |
| M2 | `python3 scripts/match_run.py --dry-run` | `query set: 1343 photos (negative 364, positive 979)`. The directory holds `run.json`, `queries.tsv`, and `queries.jsonl`, and nothing else. |
| M2a | `python3 scripts/match_run.py --dry-run` | The line `variant photos: 45 left out (--variants off)` and the line `excluded slugs: 0 in excluded-slugs.json; 0 photos left out` follow the query set. |
| M2b | `python3 scripts/match_run.py --dry-run --variants group` | `query set: 1388 photos (negative 364, positive 979, variant 45)`. The line `variant photos: 45 in the set; every slug of the variant group counts as a true match (--variants group)` follows. |
| M2h | `python3 scripts/match_run.py --backend official-api --dry-run` | The line `requests at the same time: 4`, and the source named after it as the key `workers` of the backend official-api. |
| M2i | `python3 scripts/match_run.py --backend official-api --dry-run --workers 1` | The line `requests at the same time: 1 (--workers)`. The command line wins over the key. |
| M2j | `python3 scripts/match_run.py --backend organizers --dry-run` | The line `requests at the same time: 1 (the default)`. |
| M3 | The header of `queries.tsv` | Exactly `query_id<TAB>image_path`. |
| M4 | A stub backend that always answers one slug S | R@1 equals the count of the positives of S divided by 979. The negatives of S count as `false_match_at_1`. Every other negative counts as `other_slug_at_1`, NOT as a success. |
| M5 | The same stub through `participant_test.sh --manifest runs/<id>/queries.tsv --images-dir dataset/my/photo` | Their `predictions.jsonl` and ours hold the same `query_id`, `image_path`, `image_sha256`, and `predicted_slug` for every row. |
| M6 | A stub that answers a ranked list with the true slug at rank 3 | `rank_histogram` holds the count under the key `3`. R@1 is smaller than R@5. |
| M7 | The same run with `--negative-strict` | The negatives whose slug stands deeper in the list move from `other_slug_at_1` to `false_match_in_top_k`. |
| M8 | A backend with `top_k: 1` | `recall_at_5` and `recall_at_10` are `null`, never `0`. |
| M9 | A backend that does not answer | Every row holds `error`, `predicted_slug` is `null`, and the run finishes. |
| M10 | `--backend nope` | The error names every known backend. |
| M11 | A backend with `headers: {X: env:NOT_SET}` | The run refuses to start and names the environment variable. |
| M12 | `run.json` of a backend that holds a header | The header name stays, the value is `(redacted)`. |
| M13 | Stop a run with Ctrl+C | `predictions.jsonl` and `results.jsonl` hold the rows that were already answered. |

## The repeat of a run — `--from-run`

| # | Case | Expected result |
|---|---|---|
| P1 | `--from-run <run> --dry-run` | The console states how many photos of the earlier run failed at depth 1, how many passed, and how many photos of the set were not in that run. |
| P2 | The same with `--rerun-depth 10` | Fewer positive photos and more negative photos than at depth 1. The rule is the same from both sides: a positive photo MUST be inside 10, a negative photo MUST NOT. |
| P3 | `--from-run <run> --only positive --rerun-depth 10` | Only the positive photos that were not in the first 10. |
| P4 | Repeat a run with the same backend | `recovered_at_1` is 0 and `still_failing` equals the number of the repeated photos. |
| P5 | Repeat with a backend that answers better | `recovered_at_1` is the number of the photos that stand at rank 1 now. |
| P6 | A row of `results.jsonl` of a repeat run | It holds `previous` with the earlier rank and outcome. |
| P7 | The `query_id` of a repeated photo | It equals the `query_id` of the same photo in the earlier run. The ids are not contiguous. |
| P8 | The name of the directory | It holds `repeat-d<K>`. |
| P9 | `--from-run` on a run whose photos all passed | `nothing to repeat`, and no directory of a run is written. |
| P10 | `--from-run /nowhere` | `no results.jsonl in the earlier run`. |
| P11 | `--rerun-depth 0` | The run refuses to start. |
| P12 | The page `/runs` on a repeat run | The tag `repeat d<K>` in the table, the warning above the cards, and a `before:` line under every photo. |

## The page of the runs — `/runs`

| # | Case | Expected result |
|---|---|---|
| R1 | Open `http://127.0.0.1:8154/runs` | The table of the runs, the newest first. The newest run with metrics opens by itself. |
| R1a | Look at the top right of the header | The navigation holds `Review` and `Runs`. `Runs` is the marked link. A click on `Review` opens `/`. |
| R2 | Click another run | The metrics and the photos change. The address holds the run id after `#`. |
| R3 | Reload the page with the `#` in the address | The same run opens. |
| R4 | Look at a row of a positive photo that was matched | The candidate of the true slug carries a green border. |
| R5 | Look at a row whose true slug never came back | A dashed green card stands at the front of the strip and states the expected wine. |
| R6 | Look at a row of a negative photo that matched | The candidate with the slug of the photo carries a red border. |
| R7 | Set the filter to `positive: the true slug is at rank 2 or deeper` | Only those photos are listed. The count line states how many. |
| R8 | Set the filter to `negative: the slug came back at rank 1` | Only the false matches are listed. |
| R9 | Press `load more` | The next 100 photos are added under the present ones. |
| R10 | Click a photo or a bottle | The large view opens. `Esc` closes it. |
| R11 | Click the column `match share` of the table of the runs | The runs stand by the match share, the smallest first. The header carries an arrow. |
| R12 | Click the same column again | The order turns around. |
| R13 | Click `started` | The newest run stands first. |
| R14 | Set `Sort` to `the most wrong first` | A false match of a negative photo stands first, then the photos whose true slug never came back. |
| R15 | Set `Sort` to `the rank of the true slug` | The photos with rank 1 stand first. The photos whose true slug never came back stand last. |
| R16 | Set `Sort` to `the slowest answer first`, then press `load more` | The order holds over the whole run, not over the 100 rows on the screen. |
| R17 | `GET /api/run?id=<run>&sort=nope` | The error names every accepted value. |
| R18 | Look at the first row of the cards | Match share, F1 top-1, F1 top-5, the share inside 3000 ms, the near-duplicate errors, and the false matches. |
| R19 | A run whose match share reaches 90% | The card is green. Below 90% it is red. |
| R20 | A run of a backend with `top_k: 1` | `F1 top-5` shows a dash, never a number. |
| R11 | `GET /api/run?id=../../etc` | `bad run id`. |
| R12 | `GET /api/run?id=nope` | `unknown run`. |
