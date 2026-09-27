# Smoke tests

Manual test cases. Run them after a change to the tool.

## Labelling tool — `scripts/review_server.py`

Start the tool with `python3 scripts/review_server.py --no-browser`.
Use `H=http://127.0.0.1:8154` for the command line cases.

| # | Case | Expected result |
|---|---|---|
| 1 | Start the tool | The log states first the configuration: the path of `config.yaml`, the dataset, `rootdir`, every configured path, and the work directory. It then states the wine count, the photo count, the loaded label count by label, and the URL. The start takes a few seconds, not minutes. |
| 2 | `curl -s -o /dev/null -w "%{http_code}" $H/` | `200` |
| 2a | Open `$H/` and look at the top right of the header | The navigation order is `Dataset`, `Clusters`, `Embeddings`, `Testset`, `Runs`. `Testset` is the marked link. A click on `Dataset` opens `/dataset`. |
| 2b | Drag a photo card to the sideboard at the right | The card leaves the row of its wine and stands in the panel. The counter beside `Sideboard` rises. No request is sent. |
| 2c | Drag the card from the sideboard to the row of another wine | The card stands again in the row of its own wine, with a dashed outline. Its button reads `→ <the target slug>`. The header states one more pending move. |
| 2d | Drag a held card to the row of the wine it comes from | The card stands again in that row. No move is recorded. |
| 2e | Press `put back` on a held card | The same result as case 2d. |
| 2f | Hold a photo, then reload the page | The sideboard is empty and the photo stands in its wine row. The sideboard lives in the browser tab alone. |
| 2r | Open `$H/` with the filter `all wines` | The table holds one row per catalogue card: 2103 rows for `official-real-photos`, 2106 for `default`. The header states the same count. A wine with no candidate photo shows the note `no directory my/<slug>`. |
| 2s | Set the filter to `not fully labelled`, `no label yet`, or `has no positive photo` | The list holds the wines that carry photos alone. A card with no photo is not listed. |
| 2t | Search a wine that holds no candidate photo, with the filter `all wines` | The wine is found. The search needs no other scope. |
| 2u | Drag a photo onto the row of a wine that holds no directory, then press `apply` | The directory is made and the photo stands in it. The row loses the note `no directory`. |
| 2p | Start the tool with `patch_dir` set | The start report holds the line `patch_dir` and, after the wine counts, `patched catalogue photos: <n>` with the slugs. `<n>` equals the count of image files in that directory. A file that is not an image, such as `README.md`, is not counted. |
| 2p0 | Put a patch whose extension is not the extension of the official photo, for example `<slug>.png` against a `.webp` | The wine takes the `.png`, and the `.webp` of `dataset/photo/<slug>/` is not used. The match is made on the slug alone. |
| 2p1 | Search `bukovinka` in the review table | The catalogue bottle carries the mark `PATCHED` in its top right corner. The tooltip states that the photo is a correction from `patch_dir`. |
| 2p2 | `curl -s "$H/img/bottle?slug=bukovinka" \| shasum -a 256` | The digest equals the digest of `patched-official-2026-09-17/bukovinka.webp`. The photo of the catalogue record is never served. |
| 2p3 | `GET /api/patched` | The four slugs, and the configured `dir`. |
| 2p4 | Press `move` on a photo and read the picker | A patched target carries a small dot in the top right corner of its thumbnail, not the word. The tooltip states the meaning. |
| 2p5 | Open `/runs` and find an answer that holds a patched slug | The candidate card carries the mark `PATCHED`. |
| 2p6 | Put a new file `<slug>.webp` in `patch_dir`, then press `reload` | The wine takes the new photo and the mark, with no restart. |
| 2p7 | `curl -s -D - -o /dev/null "$H/img/bottle?slug=bukovinka"` | The answer holds `Cache-Control: no-cache` and an `ETag`. |
| 2p8 | Repeat case 2p7 with `-H 'If-None-Match: <the ETag of 2p7>'` | `304 Not Modified`, with no body. |
| 2p9 | Replace a file in `patch_dir`, press `reload`, then reload the browser page | The new photo is shown at once. The browser does not show the old photo. |
| 2pa | `curl -s -D - -o /dev/null "$H/img/photo?slug=<slug>&file=<file>"` | The answer holds `Cache-Control: public, max-age=86400`. A query photo keeps the long cache. |
| 2p7 | Put a file whose name is no slug of the catalogue in `patch_dir`, then start the tool | The start report warns and names the file. The tool starts. |
| 2p8 | Set `patch_dir` to a path that is not on disk, then start the tool | The tool warns on the error stream and starts with no patch. It does not show a corrected photo that it could not read. |
| 2p9 | Look at a wine with no patch | No mark. The row is as it was before this feature. |
| 2pb | Open `/dataset` and look at the right side of a row | The row holds an `Alternative photos` area. It states the number of active photos and holds a drop target. |
| 2pc | Drop two supported images on the alternative area | Both images appear as candidates. No file is written under `alternative_dir`. |
| 2pd | Press `Cancel` after case 2pc | Both candidates disappear. No file is written. |
| 2pe | Drop two images and press `Apply` | Both files appear under `alternative_dir/<slug>/` as sequential `NN_manual.<extension>` files. The header count and the active count rise by two. |
| 2pf | Mark one active alternative for removal, then press `Cancel` | The active image stays in place. |
| 2pg | Mark one active alternative for removal, then press `Apply` | The image leaves the active list and moves to `alternative_dir/.trash/<slug>/`. |
| 2ph | Add an alternative, then load `svoe-vino-matcher/config.yaml` | `Config.photos` includes the main picture and the alternative under the same slug. The photo-index file name differs from the name before the addition. |
| 2h | Put an image file directly in `dataset/my/photo/`, then start the tool and open `$H/` | The photo stands in the sideboard with a dashed frame. The line under it reads `inbox` and the file name. The counter beside `Sideboard` counts it. |
| 2i | Put a file that is not an image, and a directory, in the same place | Neither is shown. The sideboard holds the image files alone. |
| 2j | Drag an inbox card to a wine row | The card stays in the sideboard, its frame takes the accent colour, and it states `→ <the slug>`. The header counts one more pending move. No request is sent. |
| 2k | Press `clear` on that card, or drag it back to the sideboard | The target is taken away. The card stays in the sideboard and the pending count falls. |
| 2l | Drag an inbox card to a wine row and press `apply` | The confirmation names the move out of the inbox. The file then stands in `my/<slug>/` with its own name, the row shows it, and the sideboard no longer holds it. The report names `my/<file> -> <slug>/<file>`. |
| 2m | The label file after case 2l | The photo holds an entry with no label, the comment `перенесён в <slug> из входящих my/`, and `moved_from: "my/"`. |
| 2n | Put a file in the inbox whose name is already taken in the target wine, then move it | The file lands as `<stem>_moved2<ext>`. Neither photo is lost. |
| 2o | Drag an inbox card to a row, then reload the page before `apply` | The photo stands again in the sideboard with no target. The target lives in the tab alone. |
| 2p | `curl -s -o /dev/null -w "%{http_code}" "$H/img/inbox?file=../../config.yaml"` | `404`. The route serves the files of the inbox alone. |
| 2q | POST `/api/apply-moves` with `{"inbox": [{"file": "x.png", "to": "no-such-wine"}]}` | `inbox_failed` names the pair and the reason `the target is not a slug of the catalogue`. The file stays in the inbox. |
| 2r | Drag one or more image files from the desktop to the sideboard | The sideboard gets a dashed accent outline during the drag. Each file appears as an inbox card. Each file lies directly in `my/`. No wine, label, score, or comment is set. |
| 2s | Reload after the external drop | The new inbox cards stay. They are ready for later distribution to wine rows. |
| 2t | Drop the same file name on the sideboard two times | The second file gets the suffix `_inbox2`. The first file does not change. |
| 2u | Drop a non-image file on the sideboard | The page states that the file cannot be added. No inbox file is written. |
| 2v | Drag an image from another public browser page to the sideboard | The server fetches the image. It appears as a durable inbox card. A local or private network address is refused. |
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
| 13b | Set a filter, slug scope, search, and sort. Press `export CSV`. | One CSV file downloads. It contains only the wines in the table, in the table order. It records the active view settings. Each candidate photo has one record. A wine with no candidate photo has one record with empty photo fields. |
| 13c | Open the exported file in a spreadsheet. | Cyrillic text is correct. A comma, quote, or line break in a note stays in one cell. Text that starts with `=`, `+`, `-`, or `@` does not run as a formula. |
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
| 165 | `curl -s $H/api/checks` | Five checks: `shared_positive`, `photo_too_small`, `photo_below_model_input`, `candidate_is_catalog_photo`, `catalog_photo_twin`, each with `title` and `help`. No `run` field. |
| 166 | POST `/api/validate` with `{"checks": ["nope"]}` | `{"error": "unknown check: nope. The known checks are candidate_is_catalog_photo, catalog_photo_twin, photo_below_model_input, photo_too_small, shared_positive"}`. |
| 167 | POST `/api/validate` with `{"checks": []}` | `{"error": "no check was chosen"}`. |
| 168 | POST `/api/validate` with no body | Every check runs. |
| 169 | Compare `review-labels.json` before and after a run | The file is not touched. A check only reads. |
| 170 | Mark one photo `positive` in two wines that hold the same picture, then run the check | Both wines are reported, and both photos are marked. |
| 171 | Make one of the two `negative`, then run the check again | The pair is no longer reported. |
| 172 | Run `photo_too_small` alone | Every reported photo has a long side under 256 px. The pill states the size, for example `280x280`. The tooltip states the size and the threshold. On the set of today the list is empty. |
| 173 | Run `photo_below_model_input` alone | Every reported photo has a long side of 256 to 447 px. A tall product shot such as 142 by 600 px is not reported. |
| 174 | Run both size checks together | No photo is in both lists. The count line adds the two counts. |
| 175 | Mark a small photo `unusable`, then run the check again | The photo is no longer reported. |
| 176 | Look at a photo that a size check reports | The finding holds `width`, `height`, `long_side`, and `tag`. A tall product shot such as 142 by 600 pixels is NOT reported. |
| 177 | Run the size checks with no Pillow in the environment | One finding states that Pillow is not installed. The server does not fail. |
| 178 | Run `candidate_is_catalog_photo` alone | The run takes about 50 seconds. On the set of 2026-09-18 it reports 282 photos in 241 wines. |
| 179 | Look at a photo that this check reports | The pill reads `catalogue render`. The tooltip states the difference of the two signatures and the threshold `10.0`. |
| 180 | Compare the reported photo with the bottle photo in column 1 | The two show the same picture. The size or the encoding may differ. |
| 181 | Look at the finding of a reported photo | It holds `same_bytes`, `difference`, and `tag`. `difference` is under `10.0`, and it is `0` when `same_bytes` is true. |
| 182 | Copy a catalogue bottle photo into `my/<slug>/` of its own wine, then run the check | The copy is reported with `same_bytes: true` and `difference: 0`. |
| 183 | Save that copy at half the size as JPEG, then run the check again | The copy is reported with `same_bytes: false` and `difference` about `0.3`. |
| 184 | Save it again at a quarter of the size as PNG, at the same size at JPEG quality 70, and with a wider white margin | Every one is reported. The measured values are `0.35`, `0.18`, and `0.12`. |
| 185 | Copy the bottle photo of a DIFFERENT wine into `my/<slug>/` | It is NOT reported. The check never compares across wines. |
| 186 | Flatten a transparent bottle photo on BLACK and copy it in | It is NOT reported. This is a known limit: the check composites on white. |
| 187 | Mark a reported photo `unusable`, then run the check again | The photo is no longer reported. |
| 188 | Run the check on a wine with no catalogue bottle photo | The wine is never reported. The check needs a bottle photo to compare against. |
| 189 | Compare `review-labels.json` before and after the run | The file is not touched. The check only reads. |
| 190 | Run `candidate_is_catalog_photo` with no Pillow in the environment | One finding states that Pillow is not installed. The server does not fail. |
| 191 | Run `catalog_photo_twin` alone | The run takes about 43 seconds. On the catalogue of 2026-09-17 it reports 70 findings over 162 wines. |
| 192 | Count the tags of the findings | 27 findings carry `same pic` and 43 carry `twin`. The 27 cover 55 wines. |
| 193 | Look at a wine that the check reports | A badge sits under the bottle photo in column 1, not on a card. It reads the tag and the size of the cluster, for example `same pic ×2`. |
| 194 | Hover the badge | The tooltip states the measured distance and the limit, and it names the other wines of the cluster. |
| 195 | Open the row of each wine of a `same pic` cluster | The bottle photo in column 1 is the same picture in every row. |
| 196 | Look at the finding of a `same pic` cluster | It holds `slugs`, `bottle: true`, `same_picture: true`, `same_bytes`, `distance` under `0.05`, and `tag: "same pic"`. It holds no `photos`. |
| 197 | Look at the finding of a `twin` cluster | `same_picture` is false, `distance` is from `0.05` to `1.0`, and `tag` is `twin`. The badge takes the colour of a variant, not of a defect. |
| 198 | Open the row of each wine of a `twin` cluster | The bottle photos are different pictures of a bottle that looks nearly the same. They are one producer line. |
| 199 | Find a cluster of more than two wines | One finding holds every slug of it. The pairs are not reported one by one. `fanagoriya-primum-alveus` gives a cluster of 8. |
| 200 | Look for a card that has no directory in `my/` among the reported wines | Such a card is shown; the strip states `no directory my/<slug>`. The filter `failed a check` admits a catalogue-only card. |
| 201 | Label a candidate photo of a reported wine, then run the check again | The result does not change. The check reads the catalogue photo alone. |
| 202 | Mark every candidate photo of a reported wine `unusable`, then run the check again | The wine is still reported. The check does not read a candidate photo. |
| 203 | Compare `review-labels.json` before and after the run | The file is not touched. The check only reads. |
| 204 | Run `catalog_photo_twin` with no numpy in the environment | One finding states that numpy is not installed. The server does not fail. |
| 205 | Run `catalog_photo_twin` with no Pillow in the environment | One finding states that Pillow is not installed. The server does not fail. |

## The NULL wine — a photo that matches no card

| # | Case | Expected result |
|---|---|---|
| N1 | Open `$H/` | The first row of the table is the NULL wine. It carries a dashed `NULL` box in place of a bottle photo, the name `NULL — no match in the catalogue`, and no `Group` button. |
| N2 | Set any filter, any sort, any search word | The NULL row still stands first. No filter and no search take it away. The line `N of M wines shown` does not count it. |
| N3 | Drag a photo card onto the NULL row | The card is marked as moved and its button reads `→ NULL`. The header counts one more pending move. |
| N4 | Press `apply` | The file lies in `<photo_dir>/__null__/` and stands in the NULL row. Its comment states that it came from its wine and that the catalogue holds no card for it. |
| N5 | Open the large view of a photo and press `0` | The same result as case N3. Press `0` again: the pending move is cleared. |
| N6 | Right-click a card | The menu holds `No match in the catalogue (NULL)`. A card that already carries the move holds `Keep this photo on this wine` instead. |
| N7 | Press `move` on a card and read the dialog | The last entry is `NULL`, under the wines that the photo may show. |
| N8 | Press the label buttons of a card of the NULL row | Two buttons alone: `positive` and `unusable`. |
| N9 | `curl -X POST $H/api/label -d '{"slug":"__null__","file":"<file>","label":"negative"}'` | `400`. The error states that a photo of the NULL wine takes `positive` or `unusable` alone. |
| N10 | `curl -X POST $H/api/copy -d '{"slug":"<wine>","file":"<file>","to":"__null__"}'` | `400`. The error states that a photo cannot be copied to the NULL wine. |
| N11 | Read the header counters | The photos of the NULL wine are not in `labelled X/Y`. They are counted apart as `no match`, with the pending ones in brackets. |
| N12 | Start the tool with no `__null__` directory on disk | The NULL row is there and takes a drop. The directory is made by `apply`. |
| N13 | Drag an inbox photo of the sideboard onto the NULL row, then press `apply` | The file moves into `<photo_dir>/__null__/`. |

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
| C1 | `python3 -c "import sys; sys.path.insert(0,'scripts'); import common; common.print_config()"` | The path of `config.yaml`, the line `dataset`, `rootdir`, the 9 configured paths, and the work directory. |
| C2 | Start the tool from another directory, such as `cd /tmp && python3 <abs path>/scripts/review_server.py --no-browser` | The same paths as in C1. The work directory line states `/tmp`. The tool finds the photo set. |
| C3 | Set `photo_dir` to a directory that does not exist, then start the tool | The line of `photo_dir` gets the mark `(absent)`. The tool stops with `error: photo set not found`. |
| C4 | Set `catalog_file` to an absolute path | The path stays as it is. It is not joined to `rootdir`. |
| C5 | Remove a key from `config.yaml`, then run C1 | The earlier default path is used. No error is raised. |
| C6 | `python3 scripts/08_variants.py --help` after a change of `variant_groups_file` | The script writes the groups to the configured file. The review tool reads the same file. |
| C7 | Add a second entry to `dataset`, then `python3 scripts/review_server.py --no-browser` | The line `dataset` reads `default   (of 2: default, <the other name>)`. The paths are those of `default`. |
| C8 | `python3 scripts/review_server.py --no-browser --dataset <the other name>` | Every dataset path is that of the other entry. `catalog_file` and `backends_file` do not change. The tool reads the photo set and the labels of that dataset alone. |
| C9 | `python3 scripts/match_run.py --dataset <the other name> --dry-run` | The same paths. The run directory stands under the `runs_dir` of that dataset, and `run.json` holds `options.dataset`. |
| C10 | `--dataset nope` on either script | The script stops with `unknown dataset `nope`` and names every dataset of the file. |
| C11 | A `config.yaml` with the paths at the top level and no `dataset` key | Every script stops at once with `the key `dataset` is missing`. The error names the top-level keys that belong in a dataset entry. |
| C12 | A `dataset` list with no entry named `default` | Every script stops and states that a script with no `--dataset` uses that name. |
| C13 | A dataset entry that holds `catalog_file`, or two entries with one name, or an entry with no `name` | Every script stops and names the fault. |

## The failure set — the dataset `vlmrerank-8b-failed`

| # | Case | Expected result |
|---|---|---|
| F1 | `python3 -c "import sys; sys.path.insert(0,'scripts'); import common; print(common.dataset_names())"` | `['default', 'official-real-photos', 'vlmrerank-8b-failed']` |
| F2 | `python3 scripts/match_run.py --dataset vlmrerank-8b-failed --dry-run` | The console states `query set: 171 photos (positive 171)` and `left out: excluded slug 9`. The run directory stands under `dataset/vlmrerank-8b-failed/runs/`. Remove that directory after the check. |
| F3 | `python3 scripts/review_server.py --dataset vlmrerank-8b-failed --port 8167 --no-browser`, then `curl -s http://127.0.0.1:8167/api/rows` | 108 rows hold photos, with 180 photos in total. The map `labels` holds 180 entries, and each entry carries `positive`. The start does not change `review-labels.json`. |
| F4 | Open `http://127.0.0.1:8167/runs` | The table lists the runs of `dataset/vlmrerank-8b-failed/runs/` alone. No run of `default` is listed. |
| F5 | `python3 -c "import json,hashlib; d='dataset/vlmrerank-8b-failed/'; s=json.load(open(d+'selection.json')); print(sum(hashlib.sha256(open(d+'photo/'+p['image_path'],'rb').read()).hexdigest()!=p['image_sha256'] for p in s['photos'] if p['copied']))"` | `0`. Each copied photo has the SHA-256 that the source run recorded. |

## The picture selector — `package` / `label` / `label box`

The cases need `bottle_label_dir` and `bottle_label_box_dir` in `config.yaml`.

| # | Case | Expected result |
|---|---|---|
| P1 | Start the tool | The log states `label crops: <n> from <dir>` and `label box crops: <n> from <dir>`. It then states how many wines carry a package picture and no label crop. |
| P2 | Open `$H/` | The tool bar holds the control `Image` between `Slugs` and `Find`. Its value is `package`. Column 1 shows the whole bottle. |
| P3 | Set `Image` to `label` | Column 1 shows the label alone, on white. The table does not reload; the pictures change. |
| P4 | Set `Image` to `label box` | Column 1 shows the bounding box of the label. A rim of the bottle stands at the corners. |
| P5 | Set `Image` to `label`, then find `fizz` | The two Abrau Fizz cans show the printed face of the can. A can carries no separate label, so its face IS its label. |
| P5a | Set `Image` to `label`, then find a wine whose row states `no label` | The row shows the PACKAGE picture with the mark `no label` in the bottom right corner. |
| P6 | Hover the mark `no label` | The tooltip states that the wine has no label crop and that the package picture is shown. |
| P7 | Set `Image` to `label`, then open a wine in the large view | The big catalogue picture is the label crop, on white. The caption reads `catalogue label`. |
| P8 | Set `Image` to `label`, then press `move` on a photo | The target list shows the label crop of every target. A target with no crop carries a dot in the bottom right corner of its thumbnail. |
| P9 | Set `Image` to `label`, then look at the address | The query string holds `img=label`. Open that address again: the table opens on the label crops. |
| P10 | `curl -s -o /tmp/a -w "%{content_type}" "$H/img/bottle?slug=esse-shardone-otbornoe-beloe-suhoe-12&kind=label"` | `image/png`. The file is RGBA and its alpha channel holds the mask. |
| P11 | The same call with `&kind=labelbox` | `image/png`, RGB, the same size as P10. |
| P12 | The same call with `&kind=nonsense`, and with no `kind` | Both answer the package picture of the wine. |
| P13 | `curl -s "$H/img/bottle?slug=abrau-dyurso-fizz-beloe-bryut&kind=label"` | The package picture, because this wine has no crop. The answer is not a 404. |
| P14 | Take the two keys out of `config.yaml`, then start the tool and open `$H/` | The control `Image` is not shown. Every picture is the package picture. |
| P15 | Set `bottle_label_dir` to a directory that does not exist | The tool prints a warning at the start and serves every wine its package picture. It does not stop. |
| P16 | Build the crops again, then `GET /api/reload` | The new crops are served without a restart of the tool. |

## Cropped catalogue photos — `bottle_cropped_dir`

The cases need `bottle_cropped_dir` in `config.yaml`. `$C` is
`svoe-wino-hackaton/dataset/derived/official-2026-09-17/cropped`.

| # | Case | Expected result |
|---|---|---|
| K1 | Start the tool | The configuration lines name `bottle_cropped_dir`. The log states `cropped catalogue photos: 2093 from <dir>` and no warning about a patch that changed after its crop. |
| K2 | `curl -s -o /tmp/k2.png "$H/img/bottle?slug=a-gordienko-m-nikolaev-pino-nuar-krasnoe-suhoe-135"`, then `cmp /tmp/k2.png $C/a-gordienko-m-nikolaev-pino-nuar-krasnoe-suhoe-135.png` | `image/png`, and the two files are identical. |
| K3 | `curl -s "$H/api/v1/wine/bukovinka"` | `patched` is `true`, and `bottle_path` names `$C/bukovinka.png`. The crop of a patch keeps the mark. |
| K4 | Open `$H/` | Column 1 shows each bottle without its transparent or white border. The mark `patched` stands on the patched wines. |
| K5 | Change a patch file after the build of the crops, then `GET /api/reload` | The tool serves the patch with its border for that wine. The next start of the tool prints a warning that names the slug and `build_cropped.py`. |
| K6 | Take `bottle_cropped_dir` out of `config.yaml`, then start the tool | Every picture is the patch or the catalogue photo, with its border. |
| K7 | Set `bottle_cropped_dir` to a directory that does not exist | The tool prints a warning at the start and serves the pictures with their border. It does not stop. |
| K8 | `python3 -c "import sys, json; sys.path.insert(0, 'scripts'); import common; c = json.loads(open(common.CATALOG_FILE).readline()); print(common.catalogue_picture(c['slug'], c, common.load_cropped_bottles(), common.load_patches()))"` | A path in `$C`. `scripts/08_variants.py` and `scripts/03_embed.py` embed the same file. |

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
| E15 | Set `Show` to `excluded from the benchmark`, with `Slugs` on `all` | Only the excluded wines are shown. The count is the same as under E5. |
| E16 | Set `Show` to `included in the benchmark` | The excluded wines are not shown. Every catalogue card with no directory in `my/` stays in the table. |
| E17 | Exclude a card that has no directory in `my/`, then set `Show` to `excluded from the benchmark` | The card is in the table. The filter asks about the card, not about its photos. |
| E18 | Set `Show` to `excluded from the benchmark` and `Slugs` to `included` | The table is empty. The count line reads `0 of <n> wines shown · the control Slugs stands on included and takes every row away`. |
| E19 | Copy the address of the view of E15 and open it again | The same view opens, with `Show` on `excluded from the benchmark`. |

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
| M14 | `python3 scripts/match_run.py --photos-dir <a directory of photos> --dry-run` | The line `photos directory: <the absolute path>`, then `query set: N photos (unlabelled N)`, then `no ground truth: the run records the candidates and states no correctness`. No line about the variant photos and no line about the excluded slugs. |
| M15 | The same with a directory that holds subdirectories and one file that is not an image | The walk is recursive. `image_path` of `queries.jsonl` holds the path against the directory. The line `left out:` names `not an image`. |
| M16 | `--photos-dir DIR` with `--only positive`, or with `--variants group`, or with `--from-run <run>` | The runner stops. The error names the option and states that it needs the photo set of the project. |
| M17 | `python3 scripts/match_run.py --backend <a backend> --photos-dir DIR --limit 5` | The name of the run directory holds `dir`. `run.json` holds `options.photos_dir`. Every row of `results.jsonl` holds `label: "unlabelled"`, `slug: ""`, `truth: []`, `rank_of_truth: null`, and the outcome `answered` or `no_answer`. |
| M18 | `metrics.json` of that run | Every share is `null`. The block `unlabelled` holds `n`, `answered`, `no_answer`, `errors`, `top_score_median`, and `score_margin_median`. The block `latency_ms` holds the usual numbers. |
| M19 | `summary.md` of that run | It states `A run of a plain directory`, names the directory, and holds no share and no recall. |

### The photos with no match

| # | Case | Expected result |
|---|---|---|
| M20 | Put two photos in `<photo_dir>/__null__/`, then `python3 scripts/match_run.py --dry-run` | The query set holds `no_match 2`. `queries.jsonl` gives each row `label: "no_match"`, `slug: "__null__"`, and `truth: []`. |
| M21 | The same with `--only no_match` | The set holds those two photos alone. |
| M22 | The same with `--only positive` | The set holds no `no_match` photo. |
| M23 | Label one of them `unusable`, then repeat M20 | The set holds one photo. `left out:` names `unusable 1`. |
| M24 | Put `__null__` in `excluded-slugs.json`, then repeat M20 | The set holds no `no_match` photo, and `left out:` counts them under `excluded slug`. |
| M25 | A stub backend that answers nothing | Every `no_match` row holds the outcome `no_answer`. `metrics.json` gives `no_match.rejection_rate` the value `1.0`. |
| M26 | A stub backend that always answers one slug | Every `no_match` row holds the outcome `false_match_at_1`. `rejection_rate` is `0.0`, and `false_match_scores.max` holds the score of the answer. |
| M27 | `summary.md` of such a run | It holds the section `Photos with no match in the catalogue` with `n`, `Refused (correct)`, `Rejection rate`, and `False match at rank 1`. |
| M28 | Open `/runs` and choose the filter `no match: the backend answered a card anyway` | The list holds exactly the `no_match` photos that got an answer. |

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

## The Dataset page — `/dataset`

| # | Case | Expected result |
|---|---|---|
| D1 | Open `$H/dataset` | The header states `2103 of 2103 records · 15 patches`. The document holds all 2,103 records in the order of `catalog.jsonl`. `Dataset` is the marked navigation link. |
| D2 | Look at the first row | The original catalogue bottle stands at the left. The second image place is a drop target for a patch. The main fields match the first record of `catalog.jsonl`. The wine description is not visible. It stays in `full catalog.jsonl record`. |
| D3 | Set `Show` to `with a patch` | The page shows 15 records. Each row shows the original catalogue image and the patch image next to it. |
| D4 | Search `Пино Нуар`, then search the full first slug | The page shows records that contain every search word in any JSON field. |
| D5 | Open `full catalog.jsonl record` | The formatted JSON has every source field. It does not have the internal `_patched` or `_index` fields. |
| D6 | Click `copy` beside a slug | The clipboard gets the full slug. The button reads `copied` for a short time. |
| D7 | Inspect the controls and scroll through the list | There is no `Rows`, `Previous`, or `Next` control. All records that pass the filter stay in one continuous list. Images below the viewport have `loading="lazy"`. |
| D8 | `GET /api/dataset` | The answer holds the catalogue, patch, alternative, barcode, and Atlas binding paths and counts, plus 2,103 records. Every record has `_patched`, `_barcodes`, `_atlas_product_uuid`, and `_atlas_binding_source`. |
| D9 | Compare `GET /img/catalog?slug=bukovinka` and `GET /img/patch?slug=bukovinka` | The first body equals `local_path` of the catalogue record. The second body equals `patch_dir/bukovinka.webp`. |
| D9a | Click a catalogue image or a patch image | A modal opens over the Dataset page. It shows the image on a checkerboard inside a visible boundary. The header shows the natural pixel dimensions and an `open raw image` link. No new tab opens. |
| D9b | Request `/img/catalog?slug=bukovinka` with `Accept: text/html`, then request it with `raw=1` | The first answer is the HTML preview. The second answer is the original image body even when the request accepts HTML. |
| D9c | Press the preview arrow buttons, then press the Left and Right keys | The preview moves through images of the same kind in the current filtered and sorted list. It does not close or change the Dataset scroll position. |
| D9d | Press Escape or the preview close button | The preview closes. The Dataset page stays at its earlier scroll position. |
| D9e | Open a tall image in the preview | The full checkerboard frame fits below the header. The preview has no horizontal or vertical scrollbar. |
| D9f | Click a catalogue image, then press the Right key | The address bar shows `/dataset/<slug>` of the wine that the preview shows. A patch image gives `/dataset/<slug>/patch`. The Right key changes the path and adds no history entry. |
| D9g | Close the preview, then press Forward and Back of the browser | The close gives the path `/dataset`. Forward opens the same preview again. Back closes it. The Dataset page stays at its earlier scroll position. |
| D9h | Open `/dataset/bukovinka` in a new tab, then `/dataset/no-such-wine`, then `/dataset/a/b` | The first opens the catalogue image preview over the card of the wine; the close shows that card. The second shows the plain page at `/dataset`. The third answers 404. |
| D10 | `GET /img/patch` with a slug that has no patch | `404`. The server reads no file outside `patch_dir`. |
| D11 | Drop an image on a row that has no patch | The drop target shows the candidate, its file name, `Apply`, and `Cancel`. No file appears in `patch_dir`. |
| D12 | Press `Cancel` on a patch candidate | The candidate is discarded. The row shows the empty drop target again. No file changes. |
| D13 | Drop an image and press `Apply` | The server writes `<slug>.<extension>` in `patch_dir`. The row shows the patch. The patch count increases by one. Old crop and label images for the slug move to `.trash` in their directories. |
| D14 | Press `Remove` on an existing patch | The row states that removal is pending. The patch file stays in `patch_dir`. |
| D15 | Press `Cancel`, then press `Remove` and `Apply` | Cancel keeps the patch. Apply moves it into `patch_dir/.trash`. Old crop and label images move to their `.trash` directories. The row becomes a drop target. |
| D16 | Press `Validate` | A dialog describes the slug set, the downloaded SHA-256, and the source image on each `wine_slug` page. All checks are selected. |
| D17 | Select only the slug check and press `Run selected` | The dialog shows progress. It then shows the catalogue count, the website count, and the lists of missing and extra slugs. |
| D18 | Run the image check | The progress names each completed slug. The result counts exact matches, byte mismatches, errors, and skipped records. A mismatch record holds both SHA-256 values and both sizes. |
| D19 | Run the page check | The result compares the source image file name with the file name of `og:image` on each wine page. A mismatch names both files and the page URL. |
| D20 | Close the dialog while a check runs, then open it | The job continues. The dialog shows the current progress or the completed result. |
| D21 | `GET /api/dataset-validation` | The answer holds `running`, `selected`, `progress`, and `results`. The route starts no work. |
| D22 | `POST /api/dataset-validation` with `{"checks":["slugs"]}` | The answer is `202`. A second POST while the job runs answers `409`. An empty list or an unknown check answers `400`. |
| D23 | Press `+` beside `Barcodes` in one row | A text input and the save checkmark and cancel cross icons appear. No file changes. |
| D24 | Enter a barcode and press the cancel cross icon | The input row closes. The barcode file does not change. |
| D25 | Enter a new barcode and press the save checkmark icon | The barcode appears in the row. `barcode_file` contains it under the correct `wine_slug`. The header count increases by one. |
| D26 | Add a second barcode to the same slug | The code map stores both values. Both values appear in the row. |
| D27 | Add a barcode that another slug already has | The server answers `400`. The page shows the error. The file does not change. |
| D28 | Search for a saved barcode | The page shows the slug that owns the value. |
| D28a | Look at a saved barcode | A small red `×` button stands before the number. The `copy` button stands after it. |
| D28b | Press the red `×`, then cancel the confirmation | The barcode stays visible. The barcode file does not change. |
| D28c | Press the red `×`, then confirm | Only that barcode disappears. The count and header total fall by one. The QR code and the other fields of the wine record do not change. |
| D28d | Remove the last barcode of a wine | The structured wine record stays in the code map with `barcode: null`. |
| D28e | Press `+` beside `QR URLs`, enter a public HTTP or HTTPS wine page, and press the save checkmark icon | The normalized URL appears with `×`, `copy`, and `open`. The shared code map stores it in `qr_code`. The header QR URL total rises by one. |
| D28f | Press `open` on a saved QR URL | The URL opens in a new tab. |
| D28g | Add the same normalized QR URL to another wine | The server answers `400`. The code map does not change. |
| D28h | Press the red `×` on a QR URL and confirm | Only that URL disappears. Other QR URLs, barcodes, and record fields do not change. The last removal writes `qr_code: null`. |
| D28i | Search for a saved QR URL | The page shows the slug that owns the URL. |
| D29 | Look at `Atlas Core product` for a slug in `atlas_matches_file` | The row shows the product UUID and marks the source `automatic`. |
| D29a | Press `open` after the Atlas Core product UUID | A new tab opens `http://127.0.0.1:8157/products/<uuid>` for that exact UUID. |
| D30 | Press `+` for an unbound slug | A UUID input and the save checkmark and cancel cross icons appear. No file changes. |
| D31 | Enter a UUID and press the cancel cross icon | The input closes. The manual binding file does not change. |
| D32 | Enter a valid UUID and press the save checkmark icon | The row shows the UUID and marks it `manual`. `atlas_bindings_file` contains the slug and UUID. |
| D33 | Press `edit` on an automatic binding and save another UUID | The manual overlay gets the new UUID. The automatic match file does not change. The row shows the manual UUID. |
| D34 | Enter text that is not a UUID | The server answers `400`. The page shows the error. No file changes. |
| D35 | Search for an Atlas product UUID | The page shows every Svoe Vino slug bound to that product. |

## The Embedding page — `/embedding`

| # | Case | Expected result |
|---|---|---|
| E1 | Open `$H/embedding` | The page shows every catalogue record in one continuous list. `Embeddings` is the marked navigation link. The navigation order is `Dataset`, `Clusters`, `Embeddings`, `Testset`, `Runs`. |
| E2 | Look at the first row | The left column identifies the wine. The first matrix column holds the cropped main package image above the segmented main label. Both cells have a checkerboard. |
| E2a | Set `Show` to `Patched image` | The page shows only records whose main catalogue image has a patch. |
| E3 | Add an alternative image and its `<source-file-stem>.png` label, then reload | A new matrix column shows the full additional image above its segmented label. |
| E4 | Remove one prepared label and reload | The cell states `label not prepared`. It does not show the package image as a fallback. |
| E5 | Press `Ignore` on a main image | The image becomes grayscale, and the cell gets a dashed border. The button becomes `Use`. `embedding_ignore_file` holds `main` and the wine slug. |
| E6 | Press `Use` on that image | The cell returns to the active state. Its ignore record is absent. |
| E7 | Ignore one main label and one additional image | The other two image kinds of the wine stay active. The matcher leaves only the two named inputs out. |
| E8 | Change one ignore decision and load the matcher config | `Config.index_id` returns a different name. An old index cannot be reused. |
| E9 | `GET /api/embedding` | The answer holds 2,103 records and the source paths and counts. Each prepared image states `available` and `ignored`. |
| E10 | POST an unknown slug, kind, or file to `/api/embedding-ignore` | `400`. The ignore file does not change. |

## The embedding-dependent Clusters page — `/clusters`

Use `H=http://127.0.0.1:8168`. Read [plan 30](docs/plans/30_embedding-clusters.md).

| # | Case | Expected result |
|---|---|---|
| LC1 | `python3 -m unittest discover -s tests -p 'test_cluster*.py'`, then `test_build_clusters.py` | 26 and 3 tests `OK`. |
| LC2 | Open `$H/clusters` | `Clusters` is the marked navigation link. The configuration with `clusters.json` opens. The summary names the file, build time, vector file, dimension, item states, thresholds, and counts. |
| LC3 | Choose `full`, `label`, and `combined`; in `combined`, choose `Image` `full` and `label` | Each selection changes the clusters. Each card shows one image: `full` shows the package cut, and `label` shows the label cut, each with its transparent background on a checkerboard (LC21). The select `Image` is disabled in `full` and `label`. In `combined`, `Image` chooses the view of the image. The address keeps `name`, `space`, and `image=label` for a `label` choice in `combined`. |
| LC4 | Look at an edge row | The row gives the exact wine pair, each signal, cosine, image type, source SHA-256 prefix, and links to the two prepared images that produced the highest cosine. |
| LC5 | Find a wine with `main_patched` | The effective patch occurs. The replaced `main` image does not occur. |
| LC6 | Find a cluster whose edge uses an additional image | The evidence names `full_front`, `full_back`, `label_front`, or `label_back`. A label-only image never occurs in full evidence. |
| LC7 | Change `full_threshold` in the block `clusters:` of `config.yaml`, then press `Build clusters` | The request finishes with `Clusters built`. `settings` of `data/embeddings/<name>/clusters.json` holds the two thresholds of `config.yaml` and `min_cluster_size`. The summary shows them. The page has no threshold input and no input "Minimum size". |
| LC8 | Change an embedding input after LC7, then reload | The artifact is marked `stale`. A new build makes it `current`. |
| LC9 | Write and clear a reviewer note | `cluster-notes.json` in the selected embedding directory changes atomically. The other embedding directories do not change. |
| LC10 | Click a prepared image; use the arrow buttons, the Left and Right keys, then the Up and Down keys; press Esc | The preview shows the selected image. The arrow buttons and Left and Right move inside the cluster of the image and wrap at its ends. Up and Down open image 1 of the previous or the next cluster, and wrap from the last cluster to the first. The page behind does not scroll. Esc closes it. |
| LC11 | Open `$H/clusters#<slug>` | The component that contains the slug gets an outline and scrolls into view. |
| LC12 | Use light and dark system themes, then a width of 390 px | Both themes are readable. The member cards use one column at 390 px. The edge table scrolls inside its box. |
| LC13 | `curl -s $H/api/clusters` | One record per configured embedding. The selected entry states whether its artifact exists, whether it is stale, and the counts of all three spaces. |
| LC14 | `curl -s $H/api/clusters/gx10-siglip2-so400m-patch16-naflex-p256` | The answer holds `artifact`, `cards`, and `status`. The artifact holds separate `full`, `label`, and `combined` spaces. |
| LC15 | Set `full_threshold: 0.5` in `config.yaml`, then press `Build clusters` | In less than 2 s the page shows `full_threshold 0.5 gives more than 20000 links; raise full_threshold`. `clusters.json` keeps its size and its time. Set the value back. |
| LC16 | Set `max_cluster_size: 5`, then press `Build clusters` | The error names the space and the size, for example `the full space has a cluster of 6 wines, more than 5; raise the threshold`. `clusters.json` does not change. Set the value back. |
| LC17 | Set `min_cluster_size: 3`, then press `Build clusters` | No cluster has fewer than 3 wines. `links` of each space does not change. Set the value back to 2 and build again. |
| LC18 | `curl -s -X POST -d '{"full_threshold": 0.9}' $H/api/clusters/<name>/build` | HTTP 400 with `the thresholds come from the block clusters of config.yaml`. No file changes. |
| LC19 | Put an unknown key, for example `min_size: 2`, into the block `clusters:`, then press `Build clusters` | HTTP 400 with `clusters: unknown key: min_size`. Remove the key. |
| LC20 | Open the preview in a window of 1920x1200 and of 390x844 | The dialog has no scroll bar. The whole image is visible under the head, also when the head wraps to more lines. |
| LC21 | Open `$H/clusters?name=gx10-siglip2-so400m-patch16-naflex-p256&space=combined#vinodelnya-vedernikov-fantom-5050-krasnostop-zolotovskiy-krasnoe-suhoe-145` in the light and the dark theme; click a card image | Each card image is the cut from `/images/<folder>/<sha256>.png`, not the prepared image of `/embeddings/…`. The area around the bottle or the label shows a checkerboard. The preview shows the same cut. `curl -s $H/api/clusters/<name>` gives `cut_url` for each image of `cards`; the cut file is an RGBA PNG. The links of an edge row open the prepared images on white. |

## The label rules of the clusters — `pipeline/build_label_rules.py`

Use `N=gx10-siglip2-so400m-patch16-naflex-p256` and `H=http://127.0.0.1:8168`. Read
[plan 45](docs/plans/45_cluster-label-rules.md). A run that calls the VLM needs a row in
`/Users/ashmelev/Admin/GPU_TASKS.md` first.

| # | Case | Expected result |
|---|---|---|
| LR1 | `python3 tests/test_label_rules.py` and `python3 tests/test_build_label_rules.py` | 19 and 13 tests `OK`. |
| LR2 | `python3 pipeline/build_label_rules.py --name $N --dry-run` | A JSON summary with `todo` for each stage and `calls: 0`. `cluster-rules.json` does not change. |
| LR3 | `python3 pipeline/build_label_rules.py --name $N --cluster vinodelnya-vedernikov-fantom-5050-krasnostop-zolotovskiy-krasnoe-suhoe-145` | At most 3 stage 1 calls and 1 stage 2 call. The rule `a29e59138ed4` has mode `sheet` and a valid ratio question with 30/70, 50/50, and 70/30. The alcohol question is not valid. |
| LR4 | Run LR3 again | `todo: 0` for both stages, no call. |
| LR5 | Open `$H/clusters?name=$N&space=combined#vinodelnya-vedernikov-fantom-5050-krasnostop-zolotovskiy-krasnoe-suhoe-145` | The block `VLM difference rule` shows `current` and the rule. The view `label` shows the same rule for the same members. The view `full` shows no rule. |
| LR6 | Change the note of that cluster and press `Save note` | The status shows `Saved · rebuilding the rule…`. Within about 20 s (longer while a full rule build runs) it shows `Rule rebuilt`, and the rule block shows `current` and the new rule. `data/embeddings/$N/label-rules.log` holds the command with `--cluster … --wait` and one stage 2 call, no stage 1 call. An open image preview stays open. |
| LR10 | Press `Save note` while a full run of `build_label_rules.py` runs | The rebuild waits for the full run, then builds the rule. The page keeps `Saved · rebuilding the rule…` until then, at most 5 minutes; then it names the log. |
| LR7 | Set `rules_max_images: 2` in the block `label_rules`, then run LR3 with `--stage rules --force` (the limit is not an input of a current rule) | The rule gets the error `the cluster needs 3 images, one for each card, and label_rules.rules_max_images is 2 …`, and no call goes out. Set the value back to 20. |
| LR8 | A service that accepts fewer images than a cluster needs | The run stops with exit status 2. The message names the vlm entry, `at most N image(s)`, `--limit-mm-per-prompt`, and `label_rules.rules_max_images`. |
| LR9 | Put an unknown key, for example `size: 2`, into the block `label_rules` | `error: label_rules: unknown key: size`, exit status 2. Remove the key. |

## The cluster re-rank — the key `rerank` of a pipeline

Read [plan 48](docs/plans/48_cluster-rerank.md). A run that calls the VLM needs a row in
`/Users/ashmelev/Admin/GPU_TASKS.md` first.

| # | Case | Expected result |
|---|---|---|
| RR1 | `python3 tests/test_cluster_rerank.py` | 19 tests `OK` (one test skips when `svoe-vino-matcher` is not next to the lab). |
| RR2 | Open the dialog `Run>` of `$H/testset` | `rerank-siglip2-512-crop` and `barcode-rerank-siglip2-512-crop` are in the list with no error. |
| RR3 | `~/.venvs/svoe-vino-lab/bin/python pipeline/embedding_run.py --name rerank-siglip2-512-crop --set my --limit 20 --label smoke` | The run ends with exit status 0. In `results.jsonl`, a photo whose rank-1 card and another card of its cluster stand in the top 5 holds `explain` with `kind: cluster_rules` on those cards, and its trace ends with the step `cluster_rules`. |
| RR4 | Open that run on `$H/runs` | A row with the step shows the box `VLM`: the mode, the cluster, the time or `from the cache`, the answers, and the scores. |
| RR5 | Run RR3 again | The VLM answers come from the cache (`cached: true`); the ranks do not change. |
| RR6 | Put `rules: missing` into the key `rerank` of a pipeline | The pipeline gets the error `rerank.rules names missing, which is not an entry of the key embeddings`; the other pipelines stay. Set the value back. |

## The header state of the lab pages — `localStorage`

Use `H=http://127.0.0.1:8168`. Each page keeps its header controls in its own key
`svl.<page>.header`.

| # | Action | Expected |
|---|---|---|
| HS1 | On `$H/dataset`, `$H/embedding`, `$H/clusters`, `$H/testset`, and `$H/runs`, change each select of the header and type a search text; then open the same page from the navigation (no query string) | Each control shows the value of the last visit. |
| HS2 | Open `$H/embedding?filter=stale&q=x` and `$H/runs?configuration=` | The values of the URL win over the stored values. |
| HS3 | On `/testset`, choose a filter, for example `Verdict`; then open `$H/testset?sort=slug` | Each control that the address does not hold shows its default. The stored filter does not come back. After that, a bare `$H/testset` shows the last view. |
| HS4 | In the browser console, run `localStorage.setItem("svl.testset.header", JSON.stringify({set: "no-such-set"}))`, then reload `$H/testset` | The page opens the default set and shows no error. |
| HS5 | On `/clusters`, choose `combined` and `Image` `label`; open `$H/clusters?space=combined`, then `$H/clusters` | The address with `space` shows `Image` `full`. The bare address shows `label`. |

## The page of the runs — `/runs`

| # | Case | Expected result |
|---|---|---|
| R1 | Open `http://127.0.0.1:8154/runs` | The table of the runs, the newest first. The newest run with metrics opens by itself. |
| R1a | Look at the top right of the header | The navigation order is `Dataset`, `Clusters`, `Embeddings`, `Testset`, `Runs`. `Runs` is the marked link. A click on `Dataset` opens `/dataset`. |
| R2 | Click another run | The metrics and the photos change. The address holds the run id after `#`. |
| R3 | Reload the page with the `#` in the address | The same run opens. |
| R4 | Look at a row of a positive photo that was matched | The candidate of the true slug carries a green border. |
| R5 | Look at a row whose true slug never came back | A dashed green card stands at the front of the strip and states the expected wine. |
| R6 | Look at a row of a negative photo that matched | The candidate with the slug of the photo carries a red border. |
| R7 | Set the filter to `positive: the true slug is at rank 2 or deeper` | Only those photos are listed. The count line states how many. |
| R8 | Set the filter to `negative: the slug came back at rank 1` | Only the false matches are listed. |
| R9 | Press `load more` | The next 100 photos are added under the present ones. |
| R10 | Click a photo or a bottle | The large view opens. `Esc` closes it. |
| R10a | Click the matched photo in a row of `2026-09-24T145415Z-svm-barcode-siglip2-448-upscale` that used visual matching | A strip under the large image shows the 448 by 448 input of the embedding model. The preview has an `Embedding` badge. |
| R10b | Click an image in the model input strip | That derived image becomes the large image. |
| R10c | Click query `q-000021` of that run | The large view states that the barcode or QR lookup answered the photo and that no embedding model ran. |
| R10d | Click query `q-000005` of `2026-09-23T224548Z-svm-label-gw-cluster-rules-qwen38max-rules-v2` | The strip shows the whole-photo and label embedding inputs. It also shows the difference and cluster-rule inputs with `VLM` badges. |
| R10e | Click a candidate bottle after a matched photo | The model input strip is absent. It does not show inputs from the previous matched photo. |
| R11 | Open a run made with `--photos-dir` | A note above the cards states `A run of a plain directory`, with the photo count, the count with a candidate, the count with none, the errors, the median top score, and the median gap. Every share card holds a dash. |
| R12 | Look at a row of that run | The photo is shown. The tag reads `unlabelled` and the second tag reads `answered`. The line under the photo holds the path of the file, `no ground truth`, and the latency. No candidate carries a green or a red border. |
| R13 | Rename or move the photos directory, then open that run again | The rows stay, and every photo shows the broken-image mark. The answers are still readable. |
| R14 | `curl -s -o /dev/null -w "%{http_code}" "$H/img/runphoto?id=<run>&file=../../../etc/hosts"` | `404`. The route serves no file outside the directory of the run. |
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
| R21 | Look at a row of a negative photo whose photo is also `positive` for another wine | The candidate of that other wine carries a dashed green border. The left column states `true wine: <slug>`, its rank, and the rank of the forbidden slug. |
| R22 | Look at such a row where the true wine stands above the forbidden wine | The row carries no tag `negative_above_positive`. |
| R23 | Set the filter to `negative: the wrong wine stands above the true wine` | Only the rows whose forbidden wine stands above the true wine are listed. Each carries the red tag `negative_above_positive`. |
| R24 | Look at a row whose true wine never came back | A dashed green card stands after the last candidate, set apart by a gap, and states `true wine`. |
| R25 | Set the filter to `set defect: one photo is positive for two wines` | The rows of the photos that two positive slugs share are listed, with every label. Each carries the red tag `twin_conflict`. |
| R26 | `GET /api/run?id=<run>&filter=negative_above_positive` | Every row holds `twin.verdict` `below`. |
| R27 | Open a run made before this feature | The marks are there. The field `twin` is added when the run is read, not when it is written. |
| R28 | Set the filter to `positive: the true slug is not in the top 5` | Only the photos whose true slug stands at rank 6 or deeper, or never came back, are listed. |
| R29 | Compare the counts of `not in the top 5` and `the true slug never came back` | The first count is never smaller than the second. |
| R30 | Open `/runs#2026-09-23T193559Z-svm-label-gw-cluster-rules-partial-3-rules` and set the filter to `rule step: the VLM answered for the top cluster` | 35 rows. Each row shows a box `VLM` under the frame of the top cluster: the mode, the cluster id, the time or `from the cache`, the questions with the answers, the scores, and the line about the order. |
| R31 | Set the filter to `rule step: the VLM answer changed the order` | 17 rows. The last line of each box names the card that the answer moved to rank 1, and its rank before. |
| R32 | Look at the box of a run made before the matcher recorded the questions | The box states that the question text comes from the current rule of the cluster. A run made after that change shows the questions of the run itself and no such line. |
| R33 | Look at a row with the box next to other candidates | The other candidates keep their height and stand at the top of the strip. |
| R30 | A backend with `top_k: 5` | `not in the top 10` and `not in the top 5` hold the same rows, because no candidate stands deeper than 5. |
| R31 | Set the filter to `positive: the true slug is at rank 2 to 5` | Only the photos whose true slug came back at rank 2, 3, 4, or 5 are listed. A photo whose true slug never came back is not listed. |
| R32 | Add the counts of `correct at rank 1`, `rank 2 to 5`, and `not in the top 5` | The sum equals the count of the positive photos of the run. |
| R11 | `GET /api/run?id=../../etc` | `bad run id`. |
| R12 | `GET /api/run?id=nope` | `unknown run`. |
| R33 | Click the matched photo of a row, then press `Right` | The large view moves to the first card of the candidate strip of that row. |
| R34 | Press `Right` until the last card, then press `Right` again | The last image holds. The view does not turn around to the matched photo. |
| R35 | Press `Left` at the matched photo | The matched photo holds. The view does not turn around to the last card. |
| R36 | Press `Down` | The view moves to the next photo row and keeps the place in the row. The table scrolls to that row. |
| R37 | Press `Down` at a place that is deeper than the new row | The view opens at the last image of the new row. |
| R38 | Press `Up` at the first row, or `Down` at the last row | The view holds at the same image. |
| R39 | Press an arrow key while the large view is closed | The page scrolls as usual. The keys do not act. |
| R40 | Make a run against a matcher pipeline that owns an index | `run.json` holds `embeddings` with `built_at`, `built_at_unix`, `source` `meta`, `index_file`, and `pipeline`. |
| R41 | Open that run in the page | The detail header states `Embeddings last built <date> (pipeline <name>, index <file>)`. |
| R42 | Make a run against a wrapper pipeline, for example `ocr-…` or `barcode-…` | `embeddings` names the `embed` pipeline that holds the vectors, and `answering_pipeline` names the wrapper. |
| R43 | Make a run against `official-api` | `built_at` is null and `reason` states `pipeline `official-api` reports no index`. The page prints the reason, not a blank. |
| R44 | Make a run against an ensemble | `built_at` is null, `reason` states that an ensemble reads the index of every member, and `members` holds one block per member. |
| R45 | Make a run while the matcher is stopped | The run still starts. `embeddings.reason` states that `/v1/info` did not answer. |
| R46 | Make a run against a matcher older than 2026-09-21 | `reason` states that the pipeline reports no index, because the old server sends no `embeddings` block. |
| R47 | Open a run made before this feature | The detail header states `Embeddings: not recorded`. |
| R48 | Rebuild the index, restart the matcher, and make a second run of the same backend | The two runs show two different `built_at` values, so a rebuild between them is visible. |
| R49 | Run `--backend svm-siglip2-448-prepatch` | `run.json` `embeddings` names `siglip2-12041b8834.npz` with its 2026-09-18 build time and `pinned_by_backend: true`, NOT the index the pipeline owns. |
| R50 | Compare that run with `svm-siglip2-448` in the page | The two detail headers state two different build dates, so the reader can see the runs read different vectors. |
| R51 | Pin an index the server does not offer | The run still starts, and `embeddings.reason` states that the pipeline does not offer that index. |
| R52 | Pin an index on a backend whose pipeline owns none | `embeddings.reason` states that the pipeline owns no index. The server answers 400 for every photo. |
| R53 | Open the run `2026-09-25T220729Z-lab-siglip2-p256-crop-my` and find the photo `abrau-dyurso-abrau-durso-brut-rose-reserve-pino-nuar-beloe-bryut-12/01_conf095.jpg` | Candidates #1 and #2 share one frame in the accent colour. Its tooltip reads `cluster <id> · mixed · 2 wines` (the id comes from the current build of `gx10-siglip2-so400m-patch16-naflex-p256`), plus `· stale` when the inputs changed after the build. |
| R54 | Look at a row where one cluster card stands alone between cards of other clusters | That card gets no frame. |
| R55 | Click `cluster <id> details` in that frame | `/clusters` opens with `name=gx10-siglip2-so400m-patch16-naflex-p256`, `space=combined`, and the cluster of the first card of the frame. |
| R56 | `curl -s "$H/api/run-clusters?id=<a run of vino-svoe-search-by-photo>"`, then open that run | `embedding` is `null` and `clusters` is empty. The page shows no cluster frame. Everything else works. |
| R57 | `curl -s "$H/api/run-clusters?id=<a run of dinov3-vitb16-crop>"` while `data/embeddings/gx10-dinov3-vitb16/` holds no `clusters.json` | `embedding` is `gx10-dinov3-vitb16`, `exists` is `false`, and `clusters` is empty. |
| R58 | `curl -s "$H/api/run-clusters?id=none"` | HTTP 404, `unknown run`. |

## The catalogue clusters (retired)

Plan 43 retired the catalogue clusters, `scripts/10_clusters.py`,
`scripts/11_cluster_rules.py`, `scripts/cluster_rules_report.py`, and the page
`/clusters` of the review tool on 2026-09-26. The former cases C1 and after and L1 to L23
are in the git history of this file.

| # | Case | Expected result |
|---|---|---|
| CR1 | `ls dataset/catalog-cluster*.json scripts/10_clusters.py scripts/11_cluster_rules.py scripts/cluster_rules_report.py` | No such file. The files are in `../.attick/svoe-vino-lab/`. |
| CR2 | Start `SVOE_VINO_REVIEW_CONFIG=$PWD/config.old.yaml python3 scripts/review_server.py --port <free port> --no-browser` (the lab `config.yaml` has no `dataset` key), then request `/clusters`, `/api/clusters`, and `/runs` | `/clusters` and `/api/clusters` answer HTTP 404. `/runs` answers HTTP 200 and shows no cluster frame. The navigation of the review tool pages has no link `Clusters`. |
| CR3 | Open `data/embeddings/gx10-siglip2-so400m-patch16-naflex-p256/cluster-notes.json` | The key `a29e59138ed4` holds the Fantom note (30/70, 50/50, 70/30) with `updated_at` `2026-09-24T09:22:03+0300`. `/clusters?name=gx10-siglip2-so400m-patch16-naflex-p256` shows it on that cluster. |

## The lab database — `pipeline/labdb.py` and `pipeline/import_catalog.py`

Read `docs/plans/07_sqlite-lab-database.md` and `tests/data/README.md`. Use a scratch
database for cases D1 to D10: `DB=/tmp/lab-smoke/lab.sqlite3`,
`CSV=../svoe-wino-hackaton/dataset/official-2026-09-17/strapi_output0709.csv`, and
`V=tests/data/strapi_output0709`.

| # | Case | Expected result |
|---|---|---|
| D1 | `python3 pipeline/import_catalog.py --db $DB $CSV` before the database exists | `error: no database at …`, exit 1. No file is made. |
| D2 | `python3 pipeline/labdb.py $DB` | `(created)`, `schema version: N`, where N is the number of the last file of `pipeline/schema/` (14 on 2026-09-25), `tables: image, image_derivative, wine_atlas_binding, wine_catalog, wine_code, wine_comment, wine_favorite, wine_image` at schema 14 (2026-09-25); a later schema file MAY add a table. |
| D3 | `python3 pipeline/import_catalog.py --db $DB $CSV` | `rows read: 4147`, `duplicate rows: 2044`, `wines in the CSV: 2103`, `values trimmed: 198`, `empty grapes: 2`, `added: 2103`, `states: Active 2103, Disabled 0, Removed 0`, `result: imported`. |
| D4 | Repeat case D3 | `added: 0`, `restored: 0`, `removed: 0`, `result: no change`. |
| D5 | Import `$V.v2-add-remove.csv` | `added: 2`, `removed: 3`, `states: Active 2102, Disabled 0, Removed 3`. |
| D6 | Import `$V.v3-add-remove.csv` | `added: 1`, `restored: 1`, `removed: 2`, `states: Active 2102, Disabled 0, Removed 4`. |
| D7 | Import `$V.v4-changed-field.csv` | `error: 1 wines of the CSV differ from the database, …: shato-pino-shary-kolduna-glyu-glyu-vione-krasnoe-suhoe-10 (Active): region 'Кубань' -> 'Крым'`, exit 1. The states do not change. |
| D8 | Import `$CSV` again | `added: 0`, `restored: 4`, `removed: 3`, `states: Active 2103, Disabled 0, Removed 3`. The 3 removed wines are the fake wines. |
| D9 | Set the state of one wine to `Disabled` with `sqlite3`, then import `$CSV` | `result: no change`. The wine stays `Disabled`. |
| D10 | Open a database at schema version 2 with `python3 pipeline/labdb.py <path>` | `schema version: N`, where N is the number of the last file of `pipeline/schema/` (14 on 2026-09-25), the tables of D2. Each wine is `Active`. The table `catalog_source` is gone. |
| D10a | Open a database at schema version 3 that holds `Removed` wines with `python3 pipeline/labdb.py <path>` | `schema version: N`, where N is the number of the last file of `pipeline/schema/` (14 on 2026-09-25). Each `Removed` wine has `removed_by` = `import`. The order of the rows does not change. |
| D10b | Set a wine to `Removed` with `removed_by` = `person`, then import `$CSV` | `kept removed by a person: 1: <slug>`, `result: no change`. The wine stays `Removed`. |
| D11 | Compare `wine_catalog` of a database after case D3 with `catalog.jsonl` of the same delivery, column by column; a NULL `grapes` counts as `""` | The slug sets are equal. No value differs. |
| D12 | `python3 -m unittest discover -s tests -p 'test_labdb.py'`, then the same with `test_import_catalog.py` | 14 tests `OK`, then 22 tests `OK`. |
| D13 | `git -C ../svoe-wino-hackaton status --short -- dataset/official-2026-09-17` after cases D1 to D11 | No line. The import and `tests/data/make_catalog_variants.py` do not change the delivery. |

## The images of a wine — `pipeline/seed_images.py`

Read `docs/plans/08_seed-images.md`. Use a new scratch database for cases I1 to I8:
`IDB=/tmp/lab-images/lab.sqlite3`. Make it with `python3 pipeline/labdb.py $IDB` and
`python3 pipeline/import_catalog.py --db $IDB $CSV`. The store is
`STORE=/tmp/lab-images/images/main`.
`UP=../svoe-wino-hackaton/dataset/official-2026-09-17/prod-svoe-vino-strapi/prod-svoe-vino/strapi/uploads`.

| # | Case | Expected result |
|---|---|---|
| I1 | `python3 pipeline/seed_images.py --db $IDB $UP` | 57 lines `no match: <slug>: …` above the report. `upload files indexed: 6241`, `wines: 2103`, `matched: 2046 (name-identical 23, name-unique 2023)`, `no match: 57 (different bytes 52, no candidate 5)`, `conflicts: 0`, `errors: 0`, `rows added: 2046`, `pixel sizes filled: 0`, `no pixel size: 0`, `files written: 2018`, `processed: 2018 (crop 1876, seg 142)`, `no processing, SAM3 did not answer: 0`, `processed files written: 2018`, `result: stored`. Exit 0. No internet access; 142 requests to SAM3 on gx10. Each row of `image` has `width` and `height`. |
| I2 | Repeat case I1 | `rows added: 0`, `rows unchanged: 2046`, `files written: 0`, `files in the store already: 2018`, `processed already: 2018`, `processed files written: 0`, `result: no change`. No request to SAM3. |
| I2a | On a new scratch database, run case I1 with `--sam3 http://127.0.0.1:9` | One wait of about 30 s for the first image that needs SAM3. `no processing, SAM3 did not answer: 143`, exit 0. Then run case I1 again with no option: `processed: 143 (crop 1, seg 142)`. |
| I2b | `sqlite3 $IDB 'PRAGMA foreign_key_check'` after case I1 | No line. |
| I3 | Compare the name of each file in `$STORE` with the SHA-256 of its bytes | 2,018 files. Each name before the extension is the SHA-256. No `.tmp` file. |
| I4 | Delete one file of `$STORE`, then repeat case I1 | `files written: 1`, `rows unchanged: 2046`. The file is back. |
| I5 | Write other bytes into one file of `$STORE`, then repeat case I1 | A line `error: <slug>: …: the stored bytes do not agree with the name; the file stays`. `errors: 1` or more, exit 1. The file keeps the other bytes. |
| I6 | `python3 pipeline/seed_images.py --db /tmp/lab-images/none.sqlite3 $UP` | `error: no database at …`, exit 1. No file is made. |
| I7 | `python3 -m unittest discover -s tests -p 'test_seed_images.py'` | 25 tests, `OK`. `test_derive.py`: 14 tests, `OK`. No test calls the real SAM3 service. |
| I7a | Set `width` and `height` of each `main` row of `image` to NULL with `sqlite3`, then repeat case I1 | `pixel sizes filled: 2046`, `result: stored`. Each row has its size again. |
| I8 | `git -C ../svoe-wino-hackaton status --short -- dataset/official-2026-09-17` after cases I1 to I6 | No line. The script does not change the delivery. |
| I9 | `git status --short data/` in `svoe-vino-lab` | No line. Git ignores `data/`. |

## The patched main images — `pipeline/seed_patched.py`

Read step 5 of `docs/plans/07_sqlite-lab-database.md`. Use a copy of the lab database:
`sqlite3 -readonly data/lab.sqlite3 ".backup /tmp/lab-patched/lab.sqlite3"`, and
`PDB=/tmp/lab-patched/lab.sqlite3`, `PF=../svoe-wino-hackaton/dataset/patched-official-2026-09-17`.

| # | Case | Expected result |
|---|---|---|
| P1 | `python3 pipeline/seed_patched.py --db $PDB $PF` | `skipped: README.md is not a patch file`, `patch files: 15`, `unknown slugs: 0`, `errors: 0`, `rows added: 15`, `files written: 15`, `processed: 15 (crop 15)`, `processed files written: 15`, `result: stored`. Exit 0. |
| P2 | Repeat case P1 | `rows unchanged: 15`, `files written: 0`, `files in the store already: 15`, `result: no change`. |
| P3 | Copy `$PF` to `/tmp/lab-patched/pf`, write other bytes into `bukovinka.webp`, and run the script on the copy | `replaced: bukovinka: <old> -> <new> (bukovinka.webp)`, `rows replaced: 1`. The old file stays in `images/patched/`. |
| P4 | Delete `bukovinka.webp` from the copy, and run the script on the copy | `rows kept with no file in the folder: 1: bukovinka`, `result: no change`. The row of `bukovinka` stays (plan 14). |
| P5 | Start the lab server on `$PDB`, and read `_patch_url` of `bukovinka` in `/api/dataset` | `/images/patched/68caeb4d02d51839b59f4c6f91fe8d5bf92c8ad3ddb507a62b057fcf56127368.webp`. A GET of it answers 200, `image/webp`, 110,188 bytes. `main_image_url` stays the `main` image (the card shows both, plan 14). |
| P6 | Compare the SHA-256 and the time of each file of `$PF` before and after case P1 | No change. The script only reads the patch folder. |
| P7 | `python3 -m unittest discover -s tests -p 'test_seed_patched.py'` | 14 tests, `OK`. |
| P8 | Repeat case P1 on a database that holds `main_patched` rows, with no `--force` | `error: wine_image already holds N rows of the type main_patched; a second run adds back the patches that a person removed on the page; give --force to add the missing rows anyway`. Exit 1. Nothing changes. With `--force` the run is case P2. |

## The lab server — `pipeline/lab_server.py`

Start the server with `python3 pipeline/lab_server.py --no-browser`.
Use `H=http://127.0.0.1:8168`. `config.yaml` MUST name the database
`svoe-vino-lab/data/lab.sqlite3`, and that database MUST be at the schema version N of
the last file of `pipeline/schema/` (16 on 2026-09-25).

| # | Case | Expected result |
|---|---|---|
| S1 | Start the server | The log states the config path, `database_file`, `schema version: N`, `wines: 2103 (Active 2103, Disabled 0, Removed 0)`, the disabled pages, and the URL `$H/dataset`. |
| S2 | Set `database_file` to a path with no file, then start the server | `error: no database at …`, exit 1. |
| S3 | Start the server on a database at schema version 3 | `error: the database has schema version 3 and this code needs version N; run python3 pipeline/labdb.py …`, exit 1. |
| S4 | Open `$H/dataset` | The header reads `2103 of 2103 records · 0 patches · 0 alternatives · 23 GTINs · 3 QR URLs · 367 Atlas bindings`. No source panel stands above the list. The first card is `Автохтонное Вино Крыма белое сухое`. |
| S4a | Set the schema version of the database to 3 while the server runs, then reload `$H/dataset` | The header reads `could not read the dataset`. The list reads `The dataset is not available. Cannot read /api/dataset: …` with the `labdb.py` command. |
| S5 | Look at a card of `$H/dataset` | The slug with a `copy` button is the first line, above the name. Then producer, category and region, and grapes. No line `Colour: …`. The bottle image of the wine, or `no catalogue image` for a wine with no row in `wine_image`. The editors for GTINs, QR URLs, the Atlas binding, and alternative photos stay on the card. No `site page` link and no `source image` link. |
| S6 | Search `Автохтонное` | 9 cards. |
| S7 | Switch the system to dark mode and reload `$H/dataset` | The page is dark. |
| S8 | Click `Clusters` and `Testset` | Each one shows `The page <name> is disabled for now.` with the full navigation. The link of the page is marked. `Runs` opens the Runs page (section RN). |
| S8a | Look at the navigation of `$H/dataset`, `$H/embedding`, and `$H/runs` | The order is `Dataset`, `Embeddings`, `Clusters`, `Testset`, `Runs`. |
| S9 | `curl -s -o /dev/null -w "%{http_code}" $H/api/runs` | `200` (plan 23). `$H/api/rows` stays `503`. |
| S10 | `curl -s $H/api/dataset \| python3 -c "import json,sys; print(len(json.load(sys.stdin)['records']))"` | `2103`. |
| S11 | Open `$H/dataset`, then the Dataset page of the review tool (8154) | The header of 8168 has no `Validate`, and the page sends no `GET /api/dataset-validation`. The review tool still shows `Validate`. |
| S12 | `python3 -m unittest discover -s tests -p 'test_lab_server.py'` | 49 tests on 2026-09-25, `OK`. |
| S13 | Look below the catalogue image of an `Active` wine | Two buttons: `Disable` and `Remove`. |
| S14 | Press `Disable` | The card shows the tag `disabled` and the buttons `Enable` and `Remove`. The database holds `Disabled`. |
| S14a | Look at the card of S14, then press `Enable` | After `Disable`, the `main` image of the card is gray at once; its badge `crop` or `seg` keeps its colour. The patch slot and the alternative photos keep their colours. After `Enable`, the image has its colours again. The file in `data/images/` does not change. |
| S15 | Press `Enable` | The tag goes away. The buttons are `Disable` and `Remove`. The database holds `Active`. |
| S16 | Press `Remove` | The card leaves the view `All (except Removed)`. The database holds `Removed` and `removed_by` = `person`. |
| S17 | Set `State` to `Removed` | The list holds the removed wines alone. Each card shows `removed by import` or `removed by person`, and one button: `Restore`. |
| S17a | Set `State` to `Disabled` | The list holds the disabled wines alone. Press `Enable` on one: the card leaves the view. |
| S18 | Press `Restore` | The card leaves the view `Removed`. The database holds `Active` and a NULL `removed_by`. |
| S19 | `curl -s -X POST -H 'Content-Type: application/json' -d '{"slug":"bukovinka","action":"enable"}' $H/api/wine-state` on an `Active` wine | HTTP 409: `the wine bukovinka is Active; enable needs Disabled`. |
| S20 | Switch the system to dark mode and look at a `Disabled` and a `Removed` card | The tags and the buttons are readable in dark mode. |
| S21 | Press `Disable`, then `Enable`, on a card in the view with all 2,103 cards | Each change shows in well under one second. The list does not flash, and the scroll position stays. |
| S22 | Open `$H/dataset#<slug>` for a card near the end of the list | The card stands at the top, just below the header. |
| S23 | Open `$H/dataset` after `pipeline/seed_images.py` ran on the database | 2,046 cards show a bottle image. The `src` of each image starts with `/images/main/`. 57 cards show `no catalogue image`. The captions: `main · name-unique` 2,023, `main · name-identical` 23, `main` 57. |
| S24 | Set `Show` to `without a catalogue image` | 57 cards. |
| S25 | Click the image of the first card | The large view opens with the image, `1 / 2046`, and its size in pixels. The arrows step to the next image. |
| S26 | `curl -sI $H<main_image_url of one record>` | HTTP 200, `Content-Type: image/webp`, `Cache-Control: public, max-age=31536000, immutable`. |
| S27 | `curl -s --path-as-is -o /dev/null -w "%{http_code}" $H/images/main/../../lab.sqlite3`, and the same for a name of 64 zeros | `404` each time. |
| S28 | Set `Sort` to `image size, smallest first` | The first card is `monte-garu-beloe-polusladkoe`. The pixel count of each card image is not smaller than the one above it. The 57 cards with no image stand at the end. |
| S29 | Set `Sort` to `image size, largest first` | The first card is `usadba-mezyb-shishka-merlo-vione-rozovoe-suhoe-125`. The 57 cards with no image stand at the end. |
| S31 | Look at a card after case I1 | The image is the processed file: its `src` starts with `/images/cropped/`. A badge `crop` or `seg` stands at the top left of the image. The badges: `crop` 1,903, `seg` 143. |
| S32 | Open the large view of a `seg` card and read the link `open raw image` | The link names the original in `/images/main/`, not the processed file. |
| S33 | Switch the system to dark mode and look at the badges | Both badges are readable. |
| S30 | Click the slug of a card | A new tab opens `https://vino-svoe.ru/wines/<slug>`. The `copy` button next to the slug still copies the slug. |

## The alternative photos of the lab server — `/api/dataset-alternative`

Read `docs/plans/16_alternative-images.md`. Use a copy of the lab database, as in section P,
and start a lab server on it. SAM3 on gx10 MUST answer. `W=chateau-tamagne-select-blanc-brut`.
Make two test photos from one catalogue image: the whole bottle, and a crop of its label.

| # | Case | Expected result |
|---|---|---|
| AL1 | Open `$H/dataset` and search `$W` | `Alternative photos` reads `0 active` and `Drop photos here`. No card reads `alternative_dir is not configured`. `/api/dataset` holds `"alternative_editor": true` and no key `alternative_dir`. |
| AL2 | Choose both test photos at once | Two cards read `processing`. After about 3 s the full bottle has `FF` filled and the badge `seg` or `crop`; the label crop has `LF` filled and the badge `seg` (the label cut). The head reads `2 active`; the page header counts `2 alternatives`. |
| AL3 | Press `FF` on the label crop | The card is dimmed while the server works. The badge stays `seg`, and the picture shows the package cut. `image_derivative` of the file holds the settings of `derive.py`. |
| AL4 | Press `FB` on the full bottle | The type changes in well under a second, with no new cut. |
| AL5 | Press `LF` on the label crop again | The label cut comes back. The settings of `image_derivative` are `alternatives.SETTINGS_LABEL_CLOSE_UP`. |
| AL6 | Reload the page | The types and the cuts stay. |
| AL7 | Press `×` on one photo, then `Apply` | The photo goes away; the head reads `1 active`. The file stays in `data/images/additional/`. `Cancel` instead keeps the photo. |
| AL8 | Drop the same file on the same wine again | Nothing changes; the photo stays once. |
| AL9 | Drop a photo while SAM3 does not answer | The page shows the warning `no detection: …` and `The photo is stored with no processed file. …`. The type is `FF` (`full_front`), with no badge. |
| AL10 | Switch the system to dark mode | The badges and the buttons, the filled one too, are readable. |
| AL11 | `python3 -m unittest discover -s tests -p 'test_alternatives.py'` | 27 tests, `OK`. |
| AL12 | `sqlite3 -readonly data/lab.sqlite3 "PRAGMA user_version"` | `12` or more. `wine_image` refuses the old type names `front`, `back`, `front_full`, `back_label`. |
| AL13 | Drop a photo of the back label of a bottle, with a clear barcode on it | The photo gets `LB` (or `FB` for a whole bottle seen from the back). |
| AL14 | Drop a front photo of a bottle on a shop shelf with price tags | The photo gets `FF` or `LF`: a barcode beside the bottle does not count. |
| AL15 | Click an alternative photo of the live wine `avtohtonnoe-vino-kryma-beloe-suhoe` (three photos on 2026-09-25) | The image preview opens at `/dataset/<slug>/alternative/<sha256>` of that photo. The title reads `alternative photo (<type>) · <name>`, for example `alternative photo (full front)`. The position counts every alternative photo of the list, for example `2 / 3`. The preview shows the processed file. `open raw image` names the original. |
| AL16 | Press Right, Left, Down, and Up in the preview of AL15 | Each key steps one photo, also into the photos of the next wine. The path follows. No history entry is added. Back after the close of the preview gives `/dataset`. |
| AL17 | Look at the thumbnails of AL15, then open `/dataset/<slug>` and `/dataset/<slug>/patch` of the same wine | All three previews show the same thumbnails: `main`, `main · processed`, `patched`, `patched · processed`, then `alternative 1 FB`, `alternative 1 FB · processed`, and so on for each photo, in the order of the upload. The thumbnail of the image in view is marked. A photo with no processed file reads `none` at `… · processed`. |
| AL18 | Open the preview of AL15 at a width of 1400 px and of 800 px | The thumbnails stand in one row. The row scrolls sideways, and the marked thumbnail is in view. The image keeps its height; no thumbnail is cut at the bottom. |
| AL19 | Open `$H/dataset/<slug>/alternative/` followed by 64 zeros, then `$H/dataset/<slug>/alternative/abc` | The first shows the plain page at `/dataset`. The second answers 404. |
| AL20 | Click an alternative photo on the review tool (`scripts/review_server.py`) | The photo opens in a new tab. The review tool has no preview of an alternative photo. |
| AL21 | In the preview of AL15, click `main`, then `patched · processed`, then `alternative 3 FF` | Each click switches the preview fully. `main`: the title reads `catalogue image`, the path is `/dataset/<slug>`, the position counts the catalogue images, and `main` stays marked. Right then opens the catalogue image of the next wine. `patched · processed`: the title reads `patch image`, the path ends in `/patch`, and `open raw image` names the `/images/patched/…` original. `alternative 3 FF`: the path ends in `/alternative/<sha256>` of that photo, and the position reads `3 / 3`. The thumbnails keep their place. |
| AL22 | Drop the patch file of a patched wine as an alternative photo, where SAM3 calls it a label | The patch slot keeps its package cut; the alternative photo shows its label cut. `image_derivative` holds two rows for the file: `package` and `label`. |
| AL23 | Stop the SAM3 service, press `LF` on a full photo | The page warns `The photo got no cut of its new kind. …`. The card shows the photo as it is. Press `FF`: the package cut comes back at once, with no SAM3 call. |
| AL24 | Drop a photo while SAM3 does not answer; start SAM3; drop the same file again | The second drop changes no row and processes the photo: the badge appears. |
| AL25 | Drop two photos, mark an existing photo with `×`, press `Cancel` | The mark goes away. Both uploads finish. |
| AL26 | Press a type button, and press `×` of the same photo while the card is dimmed | `×` is disabled until the type change is done. |
| AL27 | Drop a phone photo with a long side above 1,536 px | `image.width` and `image.height` of the file are its real size, not the size of the SAM3 copy. |
| AL28 | Open `$H/dataset/vysokij-bereg-risling-zelenaya-seriya/alternative/d9f847bd293aca369dd9232a8550afc78d98b73f617494165ee4fe7e22536b06` and click `label_back · processed` | The cut shows the whole back label with the barcode, not the QR sticker alone. `image_derivative` of the photo (kind `label`) holds `alternatives.SETTINGS_LABEL_CLOSE_UP` and the box 102, 61, 1247, 1553. |

## The patch editor of the lab server — `/api/dataset-patch`

Read `docs/plans/14_patch-editor.md`. Use a copy of the lab database, as in section P, and
start a lab server on it. `W=chateau-tamagne-select-blanc-brut` (a wine with a `main`
image), `PF=../svoe-wino-hackaton/dataset/patched-official-2026-09-17`.

| # | Case | Expected result |
|---|---|---|
| PE1 | Open `$H/dataset` and search `$W` | The patch editor reads `Drop an image here` / `or choose a file`. No card reads `patch_dir is not configured`. `/api/dataset` holds `"patch_editor": true` and no key `patch_dir`. |
| PE2 | Choose `$PF/bukovinka.webp` in the editor of `$W` | The page sends the file at once, with no `Apply` step. While the server works, the editor shows the candidate, the file name, and a disabled `Processing…`. |
| PE3 | Wait for the answer of PE2 | The editor shows the processed patch with the badge `crop`, the mark `patched`, and the red `Clear`. The left image stays the `main` image, caption `main · name-unique`, so the two stand side by side. The header counts `1 patches`. `wine_image` holds `main_patched` for `$W` with `source_name` `bukovinka.webp`. The file is in `data/images/patched/`. |
| PE4 | Reload the page, search `$W`, and click the patch image | The patch stays. The preview opens at `/dataset/$W/patch` with the `/images/patched/…` file, `240 × 1035 px`. |
| PE5 | Switch the system to dark mode and look at the card of PE3 | The editor, the mark `patched`, and the red `Clear` are readable. |
| PE6 | Press `Clear` | No `Apply` step. The editor shows `Clearing…`, then reads `Drop an image here` again. The left image stays the `main` image. The header counts `0 patches`. The file stays in `data/images/patched/`. |
| PE7 | Drop a JPEG with a white background while SAM3 answers | The patch slot gets the badge `seg`. |
| PE8 | Drop a JPEG with a white background while SAM3 does not answer | The page shows the warning `The patch is stored with no processed file. …`. The patch slot shows the patch with no badge. |
| PE8a | Drop a patch while SAM3 finds a label | `image_derivative` gets a `package` row and a `label` row for the patch SHA-256. The next label embedding build does not report `no label cut yet` for the patch. |
| PE8b | Drop a bottle or can patch while SAM3 finds no label | The patch and its package cut stay stored. The page shows `The patch is stored with no label cut. A label-view embedding cannot be generated.` No `label` derivative row or absence row exists. |
| PE8c | Drop a packet or box patch while the label prompt finds no label | The patch and its package cut stay stored. `image_derivative_absence` gets a `label` row with the reason. The page shows no missing-label warning. |
| PE9 | Choose a GIF file | The page shows `Cannot apply the patch change: the image is GIF; a patch MUST be JPEG, PNG, or WebP`. The candidate stays with `Apply` and `Cancel`. The database does not change. |
| PE10 | `curl -s -X DELETE "$H/api/dataset-patch?slug=$W"` on a wine with no patch | HTTP 404: `the wine … has no patch`. |
| PE11 | `python3 -m unittest discover -s tests -p 'test_patches.py'` | 15 tests, `OK`. |
| PE12 | Open `$H/dataset/avtohtonnoe-vino-kryma-beloe-suhoe` (a wine with a patch) | The image stands in the vertical center of the stage. Thumbnails of 120 px stand at the bottom: `main`, `main · processed` with the badge `crop`, `patched` with the badge `PATCH`, and `patched · processed` with the badge `seg`. Two thumbnails of each alternative photo follow (section AL). `main · processed` is marked. |
| PE13 | Click each of the first four thumbnails of PE12 | The preview shows that image. The size follows: `main` 317 × 1200 px, `main · processed` 287 × 1090 px, `patched` 480 × 640 px, `patched · processed` 243 × 559 px. The mark moves. The thumbnails keep their place. `open raw image` names `/images/main/…` for the first two, and `/images/patched/…` for the last two. |
| PE14 | Open `$H/dataset/avtohtonnoe-vino-kryma-beloe-suhoe/patch` | The same thumbnails as PE12. `patched · processed` is marked. `open raw image` names the `/images/patched/…` original, not the processed file. |
| PE15 | Open `$H/dataset/$W` (a wine with no patch and no alternative photo) | Two thumbnails: `main` and `main · processed` with the badge `crop`. |
| PE16 | Repeat PE12 in dark mode and at a width of 390 px | The thumbnails and the badges are readable. At 390 px the thumbnails stand in one row above the arrows, and the row scrolls sideways. |
| PE17 | Press Down, then Up, in the preview of PE12 | Down opens the next wine (`/dataset/aligote-barrel-2024` in the default view); Up opens `avtohtonnoe-vino-kryma-beloe-suhoe` again. Left and Right still work. |
| PE18 | Search `fanagoriya-100-ottenkov-krasnogo-kaberne-kaberne-sovinon-krasnoe-suhoe-135` | Its crop cut nothing, so the card shows the `/images/main/…` original with no badge. The preview shows `main · processed` as `none`. |
| PE19 | Measure the buttons below the images of a patched card | The patch `Clear` has the width and the height of the `Remove` of the main image (77 × 24 px at 1400 px) and stands at the right edge of the patch slot. `Disable` and `Remove` of the main image have one width. |
| PE20 | Drop a patch, and drop a second file on the same wine while `Processing…` shows | The page says `The previous patch of this wine is still processing. …`. The first patch is stored. |
| PE21 | `POST /api/dataset-patch` with a small PNG of 15000 × 15000 px | HTTP 413: `the image has 15000 × 15000 pixels; the limit is 100000000 pixels`. Nothing is stored. |
| PE22 | Send a JSON body with a lone surrogate, for example `{"slug":"a\ud800","action":"disable"}`, to `POST /api/wine-state` | HTTP 400: `the body holds a lone surrogate character`. |

## The GTINs and QR URLs of a wine — `pipeline/seed_codes.py` and the Dataset editors

Read [plan 11](docs/plans/11_wine-codes.md). Use `H=http://127.0.0.1:8168`. Case WC1 starts on a
database at schema version 8 with an empty table `wine_code`.

| # | Case | Expected result |
|---|---|---|
| WC1 | `python3 pipeline/seed_codes.py --db data/lab.sqlite3 ../svoe-vino-matcher/dataset/code-map.json` | `values: gtin 23, qr_url 3`, `slugs with no wine: 0`, `added: gtin 23, qr_url 3`, `result: seeded`. |
| WC2 | Run WC1 again, then run it again with `--force` | First `error: wine_code already holds … rows; …; give --force to add the missing rows anyway`, exit 1. Then `added: gtin 0, qr_url 0`, `result: no change`. |
| WC3 | `python3 -m unittest discover -s tests -p 'test_codes.py'`, then the same with `test_seed_codes.py` | 13 tests `OK`, then 11 tests `OK`. |
| WC4 | Search `agrolayn-mountain-eagle-viognier` on `$H/dataset` | `GTINs 2`: `04640005351194` and `04640005350852`. |
| WC5 | Search `kuban-vino-shato-tamane`, and look at `QR URLs` | `https://chateautamagne.ru/ru/catalog/wine/111`, with no `URL:` prefix. |
| WC6 | Press `+` of `GTINs`, and type `4630171630090` | The line below the input reads `wrong check digit 0; expected 4` in red. The checkmark icon is disabled. Enter sends no request. |
| WC7 | Change the value to `4630171630094` | The line reads `GTIN-14: 04630171630094`. The checkmark icon is enabled. |
| WC8 | Type `4631168664979` on a second wine, and press the checkmark icon | The GTIN `04631168664979` is saved. Two wines have it. The header count of GTINs grows by 1. |
| WC9 | Type the same GTIN again on the same wine, as `04631168664979` | An alert: `the wine … already has the gtin 04631168664979`. |
| WC10 | Look at a card of `$H/dataset` | The card has the editors `GTINs` and `QR URLs`. It has no editor `Barcodes`. The header line has no count of barcodes. |
| WC11 | `curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d '{"slug":"shardone-2","barcode":"INT-42"}' $H/api/dataset-barcode` | `503`. The table `wine_code` gets no row. |
| WC12 | Press the red `×` of a GTIN, and confirm | That GTIN alone goes away. The other wine keeps its row of the same GTIN. |
| WC13 | Switch the system to dark mode during WC6 | The red line is readable. |
| WC14 | `curl -s -X POST -H 'Content-Type: application/json' -d '{"slug":"shardone-2","gtin":"4680140700220"}' $H/api/dataset-gtin` | HTTP 400: `wrong check digit 0; expected 8`. |
| WC15 | Press `+` of `GTINs` on a card far down the list, save a valid GTIN, then remove it | Each step changes the card at once, in much less than 1 s. The list keeps its scroll position. The header count of GTINs changes by 1. |
| WC16 | Press `+` of `GTINs`, type `46301716300941`, then type one more digit. Then clear the input and paste `4630171630094123` | The 15th digit does not enter; the input holds 14 characters. The paste keeps its first 14 characters, `46301716300941`. |
| WC17 | `python3 pipeline/labdb.py $DB` on a database at version 25, then `sqlite3 $DB 'SELECT count(*), count(modified_at) FROM wine_code'` | `schema version: 26` or later. The row count does not change. The second number is `0`: an old row keeps NULL. |
| WC18 | On `$H/dataset`, hover over a GTIN that is older than schema 026 | The tooltip reads `added: unknown`. |
| WC19 | Save a new GTIN or a new QR URL, hover over it, then reload the page and hover again | Both tooltips read `added YYYY-MM-DD HH:MM` in local time. `SELECT modified_at FROM wine_code WHERE value = '<value>'` gives the same time in UTC with `Z`. A remove of the new value keeps the tooltips of the other values. |
| WC20 | `curl -s $H/api/dataset`, and look at one record | The record has `_code_times` with the keys `gtin` and `qr_url`. Each value of `_gtins` and of `_qr_urls` is a key of its map. The lists `_gtins` and `_qr_urls` still hold strings. |

## The Atlas Core product of a wine — `pipeline/seed_atlas_bindings.py` and the Dataset editor

Read [plan 15](docs/plans/15_atlas-binding.md). Use `H=http://127.0.0.1:8168` and
`D=../svoe-wino-hackaton/dataset/derived/official-2026-09-17`. Case AB1 starts on a
database at schema version 9 with an empty table `wine_atlas_binding`.

| # | Case | Expected result |
|---|---|---|
| AB1 | `python3 pipeline/seed_atlas_bindings.py --db data/lab.sqlite3 --matches $D/atlas-matches.jsonl --manual $D/atlas-bindings.manual.jsonl` | `rows: automatic 364, manual 3`, `slugs with no wine: 0`, `differs: 0`, `added: automatic 364, manual 3`, `result: seeded`. |
| AB2 | Run AB1 again, then run it again with `--force` | First `error: wine_atlas_binding already holds 367 rows; …`, exit 1. Then `added: automatic 0, manual 0`, `result: no change`. |
| AB3 | `python3 -m unittest discover -s tests -p 'test_atlas_bindings.py'`, then the same with `test_seed_atlas_bindings.py` | 6 tests `OK`, then 9 tests `OK`. |
| AB4 | Open `$H/dataset` | The header reads `… 367 Atlas bindings`. The `+` or `edit` button of `Atlas Core product` is enabled on each card. |
| AB5 | Search `vaynkraft-pino-nuar-krasnoe-suhoe-13` | `Atlas Core product` reads `bound · manual`. A red `×` stands before the UUID. |
| AB6 | Look at a wine that reads `bound · automatic` | A red `×` stands before the UUID. `copy` and `open` stand after the UUID. |
| AB7 | Press `+` on a wine that reads `not bound`, enter `00000000-1111-4222-8333-444444444444`, and press the checkmark icon | The card reads `bound · manual` at once. The header count grows by 1. |
| AB8 | Press the red `×` of the binding of AB7, and confirm | The card reads `not bound`. The header count falls by 1. |
| AB9 | Press `edit` on a wine that reads `bound · automatic`, enter another UUID, save, then press the red `×` and confirm | After the save, `bound · manual` with the new UUID. After the remove, `bound · automatic` with the old UUID. |
| AB10 | Enter `not-a-uuid` and press the checkmark icon | An alert: `product_uuid is not a valid UUID`. The card does not change. |
| AB11 | `curl -s -X DELETE "$H/api/dataset-atlas-binding?slug=<a wine that reads not bound>"` | HTTP 404: `the wine … has no Atlas binding`. |
| AB12 | Switch the system to dark mode during AB5 | The red `×` and the source label are readable. |
| AB13 | Press the red `×` of a wine that reads `bound · automatic`, and confirm `Remove the automatic Atlas binding …?` | The card reads `not bound`. The header count falls by 1. The row is gone from `wine_atlas_binding`. |
| AB14 | Press `+`, then paste `http://127.0.0.1:8157/products/183060ee-bf30-4253-af5d-39e0e4ca25c6` with Cmd+V | The input reads `183060ee-bf30-4253-af5d-39e0e4ca25c6`. The input does not read the cut URL `http://127.0.0.1:8157/products/18306`. A trailing slash, a query, or another host gives the same UUID. Nothing is saved until the checkmark icon or Enter. |
| AB15 | Press `+`, then paste `http://127.0.0.1:8157/wines/183060ee-bf30-4253-af5d-39e0e4ca25c6` | The paste is not changed. The input holds the first 36 characters. A save gives the alert `product_uuid is not a valid UUID`. |

## Two or more Atlas Core products of a wine — plan 54

Read [plan 54](docs/plans/54_atlas-binding-list.md). The cases replace AB4, AB5, AB7 to
AB9, AB11, and AB13 on the lab server. Use `H=http://127.0.0.1:8168`. The database is at
schema version 25 or later. Make the write cases on a copy of the database, or remove
the test UUIDs after the check.

| # | Case | Expected result |
|---|---|---|
| AL1 | `python3 pipeline/labdb.py data/lab.sqlite3` on a database at version 24 | `schema version: 25`. Each wine keeps its effective row: the manual row, else the automatic row. On 2026-09-26: 363 automatic and 5 manual rows; the automatic row of `vysokij-bereg-risling-zelenaya-seriya-1` is gone. `PRAGMA foreign_key_check` prints nothing. |
| AL2 | `curl -s $H/api/dataset` | Each record has `_atlas_products`, a list of `{product_uuid, source}`. No record has `_atlas_product_uuid`. `atlas_bindings` is the count of rows. |
| AL3 | Look at `Atlas Core product` of a wine with one automatic UUID | The head shows `1` and `+`. The row shows `×`, the UUID, `automatic`, `copy`, and `open`. |
| AL4 | Press `+`, enter a second UUID in upper case, and press Enter | The card shows 2 rows in add order: the automatic UUID, then the new UUID in lower case with `manual`. The head shows `2`. The header count grows by 1. |
| AL5 | Press `+` again and enter the automatic UUID of AL4 | An alert: `… already has the Atlas product …`. The card does not change. |
| AL6 | Press the red `×` of the automatic UUID, and confirm `Remove the automatic Atlas binding <uuid>?` | The manual UUID stays. The head shows `1`. |
| AL7 | Search the manual UUID of AL4 | The page shows the wine of AL4. |
| AL8 | `curl -s -X DELETE "$H/api/dataset-atlas-binding?slug=<slug>"` with no `product_uuid` | HTTP 400: `product_uuid MUST be a string`. |
| AL9 | `curl -s -X DELETE "$H/api/dataset-atlas-binding?slug=<slug>&product_uuid=<a UUID the wine does not have>"` | HTTP 404: `the wine … has no Atlas product …`. |
| AL10 | Switch the system to dark mode during AL4 | The source labels, `×`, `copy`, and `open` are readable. |
| AL11 | `python3 -m unittest discover -s tests -p 'test_atlas_bindings.py'`, then `test_seed_atlas_bindings.py` | 8 tests `OK`, then 11 tests `OK`. |

## The comments of a wine — the Dataset editor `Comments`

Read [plan 17](docs/plans/17_wine-comments.md). Use `H=http://127.0.0.1:8168`. The
database is at schema version 11 or later.

| # | Case | Expected result |
|---|---|---|
| CM1 | `python3 -m unittest discover -s tests -p 'test_comments.py'` | 9 tests `OK`. The comment tests of `test_lab_server.py` pass too. |
| CM2 | Open `$H/dataset` | The header ends with `· N comments`. Each card has the editor `Comments` after `Atlas Core product`. A wine with no comment reads `no comment`. |
| CM3 | Press `+` of `Comments`, type two lines (Enter between them), and press Cmd+Enter | The comment shows at once: the local time `YYYY-MM-DD HH:MM`, the source `user`, and the text on two lines. The count and the header grow by 1. |
| CM4 | Add a second comment to the same wine with the checkmark icon | The new comment is the last one. The list is in time order, the oldest first. |
| CM5 | Press `+`, type a text, and press Esc | The field closes. No comment is added. |
| CM6 | Put the mouse on the time of a comment | The title shows the stored UTC time, for example `2026-09-25T08:18:04Z`. |
| CM7 | Set `Show` to `with comments` | The list holds the wines with at least one comment alone. |
| CM8 | Search a word of a comment | The wine of that comment is in the list. |
| CM9 | Press the red `×` of the first comment of CM4, and confirm | The other comment stays. The count and the header fall by 1. A reload shows the same list. |
| CM10 | `curl -s -X POST $H/api/dataset-comment -H 'Content-Type: application/json' -d '{"slug":"<slug>","text":"checked","source":"script"}'` | HTTP 200. After a reload, the comment shows the source `script`. |
| CM11 | `curl -s -X POST $H/api/dataset-comment -H 'Content-Type: application/json' -d '{"slug":"<slug>","text":" "}'` | HTTP 400: `the comment is empty`. |
| CM12 | `curl -s -X DELETE "$H/api/dataset-comment?slug=<slug>&id=999999"` | HTTP 404: `the wine … has no comment 999999`. |
| CM13 | Switch the system to dark mode during CM4 | The comment boxes, the time, the source label, and the input field are readable. |
| CM14 | Open the Dataset page of the review tool (`scripts/review_server.py`) | No editor `Comments`, no `comments` in the header, and no value `with comments` in `Show`. |

## The favorite wines — the star of the Dataset page

Read [plan 19](docs/plans/19_favorites.md). Use `H=http://127.0.0.1:8168`. The database
is at schema version 13 or later.

| # | Case | Expected result |
|---|---|---|
| FV1 | `python3 -m unittest discover -s tests -p 'test_favorites.py'` | 4 tests `OK`. The favorite tests of `test_lab_server.py` pass too. |
| FV2 | Open `$H/dataset` | The header ends with `· N favorites`. Each card has a `☆` at the top right of the text column, next to the alternative photos. No text runs under it. `State` has the value `Favorites` after `Removed`. |
| FV3 | Press `☆` on a card | It becomes an amber `★` at once. The header count grows by 1. |
| FV4 | Press the `★` of FV3 | It becomes `☆`. The header count falls by 1. |
| FV5 | Set `State` to `Removed`, press `☆` on a removed wine, then set `State` to `Favorites` | The list holds each favorite, also the removed wine. |
| FV6 | In the `Favorites` view, press `★` on a card | The card leaves the list at once. |
| FV7 | Reload the page | The stars and the count stay as they were. |
| FV8 | `curl -s -X POST $H/api/dataset-favorite -H 'Content-Type: application/json' -d '{"slug":"<slug>","favorite":"yes"}'` | HTTP 400: ``favorite` MUST be true or false``. |
| FV9 | Switch the system to dark mode during FV3 | The `☆` and the amber `★` are readable. |
| FV10 | Open the Dataset page of the review tool (`scripts/review_server.py`) | No star, no `favorites` in the header, and no value `Favorites` in `State`. |

## The wine type — the select `Type` of the Dataset page

Read [plan 52](docs/plans/52_wine-beverage-type.md). Use `H=http://127.0.0.1:8168`. The
database is at schema version 23 or later.

| # | Case | Expected result |
|---|---|---|
| WT1 | `python3 tests/test_beverage_types.py` | 5 tests `OK`. The wine type tests of `test_lab_server.py` pass too. |
| WT2 | Open `$H/dataset` | Each card has `Type [not set]` at the end of the category line. The row of `Advanced Filters:` holds `Type` after `Identifier`, with `All`, `Wines`, `Sparkling Wines`, and `Not set`. |
| WT3 | Set `Type` of a card to `Sparkling wine` | The select is disabled for a moment, then shows `Sparkling wine`. A reload keeps the value. |
| WT4 | Set the filter `Type` to `Sparkling Wines` | The list holds only the wines with `Sparkling wine`. `Advanced Filters:` has the accent. |
| WT5 | In the view `Sparkling Wines`, set a card to `Wine` | The card leaves the list at once. |
| WT6 | Set the filter to `Not set` | The list holds the wines with no type. A card that gets a type leaves the list. |
| WT7 | Set a card to `not set` | `wine_beverage_type` has no row for the wine. |
| WT8 | Reload the page with the filter at `Wines` | The filter comes back as `Wines`, and `Advanced Filters:` has the accent. The row stays closed. |
| WT9 | `curl -s -X POST $H/api/dataset-beverage-type -H 'Content-Type: application/json' -d '{"slug":"<slug>","beverage_type_code":"440"}'` | HTTP 400: ``beverage_type_code` MUST be "4", "44", or null``. A body with no key `beverage_type_code` gives the same answer. |
| WT10 | Switch the system to dark mode during WT3 | The select and the filter are readable. |
| WT11 | Open the Dataset page of the review tool (`scripts/review_server.py`) | No select on the cards, and no `Type` in the advanced row. |

## The lab embeddings — `pipeline/build_embeddings.py` and `/embedding`

Use `P=~/.venvs/svoe-vino-lab/bin/python` and `N=gx10-siglip2-so400m-patch16-naflex-p256`.
Use `H=http://127.0.0.1:8168`.

| # | Case | Expected result |
|---|---|---|
| EB1 | `python3 -m unittest discover -s tests -p 'test_*embedding*.py'` | 50 tests, `OK`. |
| EB2 | `$P pipeline/build_embeddings.py --name $N` on an empty `data/embeddings/$N/` | The first line is `start` with `items` 4036 and `todo` 4036. The last line is `done`. `index.json` holds 2,018 items of the view `full`; `failures` holds the 2,018 label items with `no label cut yet`. `images/` holds 2,018 PNG files `<sha256>_full.png`. |
| EB3 | Run EB2 again | `start` states `current` 2018. No `progress` line sends an image to gx10: `built` stays 0. The PNG files keep their time stamps. |
| EB4 | Start EB2 on an empty directory, and press Ctrl+C after about 30 s | The lines `stopping` and `stopped` follow. `index.json` holds the finished items. `build.lock` is gone. |
| EB5 | Run EB2 after EB4 | `start` states `current` equal to the items of EB4. The build ends with `done`. |
| EB6 | Change `max_num_patches` of `$N` to 257, and run EB2 | Each full item is built again. Set the value back to 256 after the test. |
| EB7 | Delete one `images/<sha256>_full.png`, and run EB2 | `built` is 1. |
| EB8 | Put `remove_background` with no `white_background` in a view, and run EB2 | Exit 2. The `error` line states `the gateway drops the alpha channel`. |
| EB9 | Start a second `$P pipeline/build_embeddings.py --name $N` while EB2 runs | Exit 3. The `error` line names the PID of the first build. |
| EB10 | Open `$H/embedding` | HTTP 200. `Embeddings` is the marked navigation link, the second after `Dataset`. The combobox lists the 11 entries of `config.yaml` as `<name> — <current> / <items>`. |
| EB11 | Select `$N` after EB2 | Each wine row shows the card image column: the prepared `full` image with the badge `current`, and the `label` cell with the badge `failed` and `no label cut yet`. Each cell has a checkerboard background. |
| EB12 | Press `Build` on an entry with no files | A job row with a progress bar appears. `Build` is disabled, `Stop` is enabled. At the end the grid reads again. |
| EB13 | Press `Stop` during EB12 | The job reads `stopping`, then the message `last build stopped`. A second `Build` continues the build. |
| EB14 | Press `Build` on two entries | Two job rows run at the same time. |
| EB15 | Restart the lab server while a build runs, and reload the page | The job row shows the running build again. |
| EB16 | Switch the system to dark mode | The page, the badges, and the job rows are readable. |
| EB17 | Look at the source panel of `$N` | The count after `failed` is red when it is above zero. The row `Directory` ends with the software versions and does not name the endpoint. |
| EB18 | Press `open` on the row `Directory` | Finder opens `data/embeddings/$N/`. For an entry whose directory is not on disk yet, the page shows `Cannot open the directory of …: the directory of … is not on disk yet`. |
| EB19 | Select `$N` after EB2, and press `Log` | A dialog `Build log · $N` opens. The checkbox `Show progress and request` is on. Each line of `build.log` shows, each as `time · event · fields`; `done` is green. The count reads `<all> of <all> lines`. |
| EB20 | Clear the checkbox of EB19, then press `Refresh`, then press Esc | The `progress` and `request` lines go away. The `item_failed` lines stay. Each `item_failed` line names the full `source_sha256` (64 characters, not cut), the view, `wine <slug>`, `name <wine name>`, `image_type <type>`, and the error, in red. A file of more wines adds `other_wines [...]`. `Refresh` reads the file again and scrolls to the end. Esc closes the dialog; a click on the backdrop closes it too. |
| EB21 | Select an entry with no build yet | `Log` is disabled. `curl -s $H/api/embeddings/<that entry>/log` answers `404` and `<name> has no build log yet`. |
| EB22 | Let a build end with a Python traceback, and press `Log` | The traceback lines show as they are, with their indent, in red. |
| EB23 | Select `$N`, and click the first `full` image | The preview of `/dataset` opens: `full · <wine name>`, `<slug> · Card image · <type> · current`, `1 / <count>`, the size in px, and `open raw image` to the original. The thumbnail `card · full` is marked. The URL holds `preview=<sha256>_full`. |
| EB24 | Press Right, then Down, then Left in EB23 | Each key steps to the `full` image of the next or the previous column; after the last column of a wine, the first column of the next wine. The position and the marked thumbnail follow. |
| EB25 | Click the thumbnail `card · original` in EB23 | The original shows. `open raw image` names it. A thumbnail of a `failed` item with no image reads `failed` and is not a button. |
| EB26 | Press Back in EB23, then Forward | Back closes the preview and removes `preview=` from the URL. Forward opens it again. |
| EB27 | Copy the URL of EB23, and open it in a new tab | The page opens with the preview open. Esc closes it and removes `preview=`. |
| EB28 | Set `Show` to `with a failed image`, and step through a preview | The arrows step over the wines of the filtered list alone. |
| EB29 | Cmd+click a prepared image | The image opens in a new tab. No preview opens. |
| EB30 | Open EB23 in dark mode, and at a width of 390 px | The preview is readable. At 390 px the dialog fills the screen, the thumbnails are one row that scrolls sideways, and the arrows stand at the bottom. |
| EB31 | `python3 -m unittest discover -s tests -p 'test_seed_label_cuts.py'` | 8 tests, `OK`. No test calls the real SAM3 service. |
| EB32 | `python3 pipeline/seed_label_cuts.py --db data/lab.sqlite3 --limit 5` | `to do` names the full originals with no label cut. `label cuts written: 5` (less when SAM3 finds no label). `result: done`. |
| EB33 | Run the seed with no `--limit` | One `progress:` line for each 50 originals. At the end `result: done`. A packet or box with no separate label gets a row of `image_derivative_absence`. A bottle or can with no detected label gets no row. |
| EB34 | Run EB33 again | The seed reports real cuts in `label cuts present` and markers in `label not applicable present`. It skips both groups. It retries the bottle and can misses only. No cut or marker is written again. |
| EB34a | Build `$N`, then inspect a packet or box with a label-absence row in `GET /api/embeddings/$N` | The `full` cell stays `current`. The `label` cell is `not_applicable` and states the reason. The item total excludes that label cell. No duplicate label vector exists. |
| EB35 | Press `Build` on `$N` after EB33 | The build makes each `label` item. The `label` cell of a card image shows the prepared label with the badge `current`. |
| EB36 | Look at a `current` cell and a `failed` cell of `$N` | The `current` cell has the badge `vector` at the bottom left; the `failed` cell has none. The preview of the `current` cell names `vector` in its second line. |
| EB37 | Press `Build` on an entry whose gateway model is not loaded on gx10 | The job row reads `0 / <todo> · waiting for the model · <time>` in amber after 3 s, and the time counts up. When the first batch returns, the phase goes away and `done` grows by the batch size. |
| EB38 | Let the gateway answer HTTP 503 during a build | The job row reads `retry 1 in 2 s: HTTP 503 from …` (the full error in the tooltip). `build.log` holds one `retry` line for each wait. |
| EB39 | Open `Log` after EB37 | The `request` lines are hidden while the checkbox is on; the `retry` lines show. |
| EB40 | Open `$H/embedding` in a window 1,440 px wide | The header has two rows. Row 1: `Embeddings`, `Configuration` with the combobox, `Build`, `Stop`, `Log`, the message of the last build, and the navigation at the right. Row 2: `Show` and `Search`. The header shows no line `N of M wines · … items · current …`; the row `Items` of the source panel shows the counts. A window narrower than about 1,410 px puts the navigation in its own row. |
| EB41 | Start two builds, then look at the job rows | Each `running` row starts with a small icon button `×` in the muted text color, not red, its title `stop the build of <name>`. |
| EB42 | Select another entry in `Configuration`, then press `×` on the row of the first build | The page sends `POST /api/embeddings/<first name>/stop`. The row reads `stopping` with a disabled `×`, then the row goes away. The message line of the first entry reads `last build stopped: …; Build continues it`. The other build runs on. |
| EB43 | Make the window 390 px wide during EB41 | The `×` button stays small in a narrow column at the left of the row; the name, the state, the bar, the counts, and the elapsed time are at its right. The job rows fit the window. |
| EB44 | `python3 -m unittest discover -s tests -p 'test_alternatives.py'` | 41 tests, `OK` (2026-09-26). `BodyLabelsTest`: a second label of the same width counts; a neck label, a part of the main label, a narrow label, a small label, and a label on another bottle do not. The absence rule accepts a packet or box and rejects a bottle. |
| EB45 | `sqlite3 data/lab.sqlite3 "SELECT method, count(*) FROM image_derivative WHERE kind = 'label' GROUP BY 1"` after EB33 | Most rows `seg`; the photos with a second body label `crop`: 111 `crop` and 1,910 `seg` on 2026-09-25. Each row has the settings `alternatives.SETTINGS_LABEL`. |
| EB46 | Open the `label` cut of a wine with two labels one above the other (a row `crop` of EB45) | The cut holds both labels and the glass between them, with no transparent part. |
| EB47 | Open the `label` cut of a wine with a neck label and one body label | The cut is the segment of the body label alone (`seg`), as before. |

## The website import — `pipeline/import_website.py`

Read [plan 18](docs/plans/18_import-website.md). A real run sends requests to
`api.vino-svoe.ru` and takes some minutes.

| # | Case | Expected result |
|---|---|---|
| IW1 | `python3 -m unittest discover -s tests -p 'test_import_website.py'`, then the same with `test_website_import_routes.py` | 33 tests `OK`, then 6 tests `OK`. No test sends a request to the internet. |
| IW2 | `python3 pipeline/import_website.py --db data/lab.sqlite3` while the website has a changed text or a changed main image | Exit 1. The `error:` line states `the import stops, and nothing changed`, and one line follows for each problem: `<slug> (<state>): the text changed: <field> <old> -> <new>` or `<slug>: the main image changed: stored … website …`. `data/lab.sqlite3` and `data/images/` do not change. |
| IW3 | Run IW2 when the website shows no changed text and no changed image | Exit 0. The report states `added`, `restored`, `removed`, and `main images stored` with the slugs, and `result: imported`. Each changed wine has one comment of the source `script` on `/dataset`. |
| IW4 | Run IW3 again | `result: no change`. No new comment. |
| IW5 | Set a wine `Removed` on `/dataset` during IW3, before the line `images: 2105/2105` | Exit 1: `the database changed during the import; run the import again`. |
| IW6 | Open `/dataset` on the lab server | The bar shows `Import from website`. The review tool (`scripts/review_server.py`) does not show it. |
| IW7 | Press `Import from website`, then `Compare` | The button shows the progress, for example `Website: images 300/2105`. After about 10 minutes the dialog opens with the sections `Conflicts`, `New wines on website`, `Missing on the website`, `Back on the website`, and `Missing main images, taken from website`. `data/lab.sqlite3` does not change. |
| IW8 | In the dialog of IW7, leave one conflict with no choice | `Apply` stays enabled. The status line states `N conflicts have no choice. Apply skips them.` |
| IW9 | Choose each conflict, clear one checkbox, and press `Apply` | The button shows `Website: applying…`. The dialog then lists the counts. `Reload the page` shows the new states. Each changed wine has a comment of the source `script`. `website_refusal` holds a row for each choice `database`. A cleared checkbox gets no row. |
| IW10 | Run `python3 pipeline/import_website.py --db data/lab.sqlite3` after IW9 | No stop on a refused conflict. The report states `skipped by a refusal: N`. |
| IW11 | Set `Sort` to `changed in the lab, newest first` after IW9 | The wines of IW9 come first. A wine with no time goes last. |
| IW12 | Switch the system to dark mode, and open the dialog | The dialog, the rows, and the choices are readable. |
| IW13 | In the dialog of IW7, look at a wine with two conflicts, for example `alma-valley-locantita-merlot-cabernet-franc` | One card holds both conflicts. The heading states `Conflicts 12 · 9 wines`. The card border stays marked until each conflict of the card has a choice. |
| IW14 | Click a wine slug in a conflict or in a change row | A new tab opens `https://vino-svoe.ru/wines/<slug>`. The checkbox of the row does not change. A row of `Missing on the website` shows the slug as plain text. |
| IW15 | Click an image in a change row or in a conflict | A large view of the image opens with its file name. The checkbox or the radio button does not change. Esc or a click closes the large view, and the dialog stays open. |
| IW16 | In the dialog of IW7, look at the section `Missing on the website`, in light and in dark mode, then click the sign of one row | Each row shows a red prohibition sign on top of the wine image. No other section shows the sign. The click opens the large view of the image without the sign. The checkbox of the row does not change. |
| IW17 | In the dialog of IW7, look at a conflict of the main image, in light and in dark mode | Each image of the conflict shows its pixel size under it, for example `300×493`, on the `database` side and on the `website` side. The size equals the width and the height of the file. A text conflict and the rows of the changes show no size. |
| IW18 | On `/dataset`, press `Import from website`, then `×`, then Forward, then Back, then Esc | The open dialog makes the path `/dataset/website-import`. `×`, Back, and Esc close the dialog and give `/dataset`. Forward opens the dialog again. |
| IW19 | Open `http://127.0.0.1:8168/dataset/website-import` in a new tab, then press `×` | The dialog opens with the newest run in its present state (a running job, the conflicts and changes, or the result). The list shows all records; no image preview opens. `×` gives `/dataset`. |
| IW20 | After an apply, press `Reload the page` in the result | The page loads again as `/dataset`; the dialog does not open again. |
| IW21 | In the dialog of IW7, leave one conflict with no choice, and press `Apply` | The result lists the conflict id under `conflicts with no choice, not written`. The wine keeps its field or its main image. The wine gets no comment and no row in `website_refusal`. The next `Compare` shows the conflict again. |
| IW22 | Open the dialog of IW7 in light and in dark mode, and at a width of 390 px | The section `Possible renames` follows `Conflicts`. Each row shows a wine of `Missing on the website` with the red sign, an arrow, a wine of `New wines on website`, and the matched rules (`same image`, `slug distance N`, `same name and producer`). The rows have no checkbox. Both wines of a row stay in their own sections. The run `20260926T074810` shows 4 rows. |
| IW23 | In the dialog of IW7, clear the checkboxes of one new wine, one missing wine, and one main image, and press `Apply` | The result lists the three change ids under `cleared changes, not written`. No wine is added or removed, and no main image is stored for them. They get no comment and no row in `website_refusal`. The next `Compare` shows the three changes again. |

## The manual wines — the Dataset button `Add wine`

Read [plan 20](docs/plans/20_add-wine.md). Use `H=http://127.0.0.1:8168`. A wine that
AW3 adds stays in the database: use a scratch database, or remove the wine with
`Remove` after the check.

| # | Case | Expected result |
|---|---|---|
| AW1 | `python3 -m unittest discover -s tests -p 'test_manual_wines.py'`, then the same with `test_import_catalog.py` | 12 tests `OK`, then 22 tests `OK`. No test calls the real SAM3 service. |
| AW2 | Open `$H/dataset` and press `Add wine` | The dialog `Add wine` opens. The image zone is a tall column at the left of the fields. The slug field starts with a fixed `__`. `Category` lists the categories of the records. `Save` is off. |
| AW3 | Fill each required field, type `Test Wine` as the slug, then `test-wine` | `Test Wine` gets a red border. `Save` stays off until the slug is `test-wine` and an image is dropped or chosen; the image shows as a thumbnail. |
| AW4 | Press `Save` after AW3 | The dialog closes. The list ends with the card `__test-wine`: the slug is plain text with no link, the image caption reads `main · manual`, and the image has the badge `crop` or `seg`. The header count grows by 1. |
| AW5 | Press `Add wine`, fill the form again with the slug `test-wine`, and press `Save` | The dialog stays open with `Cannot add the wine: the database holds a wine with the slug __test-wine already`. |
| AW6 | Press Esc, then open the dialog again | The dialog closes, and it opens again with the values of AW5. |
| AW7 | Drop a GIF file on the image zone | `Choose a JPEG, PNG, or WebP image up to 20 MB.` The image stays as it was. |
| AW8 | `curl -s -X POST $H/api/wine -H 'Content-Type: application/json' -d '{"slug":"no-prefix"}'` | HTTP 400: `the slug 'no-prefix' MUST start with __ …`. |
| AW9 | Run `import_catalog.py` with the official CSV on a scratch database that holds a manual wine | The manual wine stays `Active`. `removed: 0` for it. |
| AW10 | Switch the system to dark mode during AW3 | The dialog, the fields, the fixed prefix, and the image zone are readable. |
| AW10a | Make the window 390 px wide during AW3 | The image zone stands above the fields. The page has no horizontal scroll. |
| AW11 | Open the Dataset page of the review tool (`scripts/review_server.py`) | No button `Add wine`. `Validate` stays at the right. |
| AW12 | Open the dialog with an empty form and type the name `Южный Лес, 2021` | The slug reads `yuzhnyy-les-2021` while you type. |
| AW13 | Type `my-own` in the slug field after AW12, then change the name | The slug stays `my-own`. Empty the slug field and change the name: the slug follows the name again. |
| AW14 | Save a wine with an empty `Description` | HTTP 200. `sqlite3 data/lab.sqlite3 "SELECT description FROM wine_catalog WHERE wine_slug = '__<slug>'"` prints an empty line (NULL). |
| AW15 | `python3 pipeline/labdb.py data/lab.sqlite3` on a database at version 13 | `schema version: 14`. The row counts of `wine_catalog`, `wine_image`, `wine_code`, `wine_atlas_binding`, `wine_comment`, and `wine_favorite` do not change. `PRAGMA foreign_key_check` prints nothing. |
| AW16 | `curl -s -X POST $H/api/wine -H 'Content-Type: application/json' -d '{"slug":"__null__"}'`, then a valid body with `"image_name":5` | HTTP 400 `the slug __null__ is reserved`, then HTTP 400 that names the field `image_name`. |

## The test sets — `pipeline/import_testsets.py`

Read [plan 12](docs/plans/12_testsets-benchmark.md). The import copies about 760 MB to
`data/images/testset/` the first time.

| # | Case | Expected result |
|---|---|---|
| TS1 | `python3 -m unittest discover -s tests -p 'test_import_testset*.py'`, then the same with `test_benchmark.py` | 13 tests `OK`, then 8 tests `OK`. |
| TS2 | `python3 pipeline/labdb.py data/lab.sqlite3` on a database at version 15 | `schema version: 16` or later. The tables `test_photo`, `test_set`, and `test_variant` are there, and `test_photo_comment` from schema 022 on (schema 022 drops `test_excluded` and `test_wine_note`, plan 51). The row counts of `image`, `wine_image`, and `image_derivative` do not change. `PRAGMA foreign_key_check` prints nothing. |
| TS3 | `python3 pipeline/import_testsets.py --db data/lab.sqlite3` | Exit 0 and `sets imported: 3`. `my`: `photos: 4043`, `files directly in photo/, left out: 12`. `official-real-photos`: `photos: 100`. `vlmrerank-8b-failed`: `photos: 180` (values of 2026-09-25). |
| TS4 | `sqlite3 data/lab.sqlite3 "SELECT set_name, count(*) FROM test_photo GROUP BY 1"` after TS3 | `my\|4043`, `official-real-photos\|100`, `vlmrerank-8b-failed\|180`. |
| TS5 | Run TS3 again | `files written: 0` for each set. The counts of TS4 do not change. |
| TS6 | `python3 pipeline/import_testsets.py --db data/lab.sqlite3 --source /tmp` | Exit 1: `error: no photo directory for the sets my, official-real-photos, vlmrerank-8b-failed in /tmp`. Nothing changes. |
| TS7 | Set one label on `/testset` (a copy of the database), then run TS3 on that copy | Exit 1: `the set my holds edits of the Testset page (the last at …)`. The label of the page stays. With `--force`, the label of the file comes back and `test_set.edited_at` is NULL. |
| TS8 | On a copy of the database after TS3: `python3 pipeline/export_testset.py --db <copy> --set my --out /tmp/x`, then compare `labels` and `note` of `/tmp/x/review-labels.json` with the files of `svoe-vino-testset/dataset/my/` | Since plan 51: each entry with a comment holds `comments` (a list of `{created_at, source, text}`) in the place of `comment`; the other fields are equal, field for field. The file holds no `wines`, and the export writes no `excluded-slugs.json`. The same for `official-real-photos` and `vlmrerank-8b-failed`. |

## The Testset page of the lab server — `/testset`

Read [plan 24](docs/plans/24_testset-page.md). Each click writes to the database. Run the
write cases on a copy: start `python3 pipeline/lab_server.py --port 8174 --no-browser
--config <scratch config>` with a config whose `database_file` names a copy of
`data/lab.sqlite3` and whose `data/images` is a link to the live image store.

| # | Case | Expected result |
|---|---|---|
| TP1 | `python3 -m unittest discover -s tests -p 'test_testset*.py'`, then `test_export_testset.py` | `OK`. |
| TP2 | `curl -s -o /dev/null -w '%{http_code} %{redirect_url}' http://127.0.0.1:8168/` | `302 http://127.0.0.1:8168/dataset`. |
| TP3 | Open `/testset` | The title `Test set [my (4043 photos) ▾] 2105 wines, 4043 photos`, and `labelled 2556/4043 photos` (2026-09-25). The first table row is `No Match` (plan 36); the right sidebar is the Drawer. The navigation marks `Testset`. The link `Testset` of each other page leads here. |
| TP4 | Choose `official-real-photos` in the combobox of the title | The header shows `100 photos`. The address holds `?set=official-real-photos`. |
| TP5 | Click `D` on a card, then `D` again | The card turns yellow, then plain. Each click answers HTTP 200. A reload keeps the state. |
| TP6 | Open a photo, press `2`, type a comment, press Cmd+Enter | The status says `negative sample`. The panel `Comments on this photo` lists the comment with the source `user`; the state says `added`, and the field is empty. The card gets the comment badge. |
| TP7 | In the large view press `b` and drag on the photo | A yellow frame stays on the photo. The side panel says `saved: box l, t, r, b`. After `Esc` the card has the badge `box`, and `Marks` `a box` lists the wine. `Clear box` removes it. |
| TP8 | Right-click a card, `Delete`; then `Keep this photo` | The card gets `del` and turns gray; then it is plain again. No file moves. |
| TP9 | Remove a wine that has photos on `/dataset`, then open `/testset` | The row of the wine stays, with the badge `Removed`. After `Restore` on `/dataset` the badge goes away, and the labels are the same. |
| TP10 | Click `+` of `Comments` in a wine row, type a text, press Cmd+Enter | The row lists the wine comment with the source `user`; a reload keeps it. `/dataset` shows the same comment. The row has no `Exclude` button and no note field (plan 51). |
| TP11 | Open `/testset?set=my#<slug>/<file>` | The large view opens at that photo, with its comments and its box. |
| TP12 | The system theme dark; a window of 390 px | The dark colours. No horizontal scroll. The header scrolls away; the large view starts below the status. |
| TP13 | Drag one JPEG file from the Finder onto the sidebar | The sidebar gets a dashed frame during the drag. After the drop, the photo stands in the sidebar with its Finder name and no label; the counter of the sidebar goes up by 1. A reload keeps it. |
| TP14 | Drag a different image file from the Finder onto a wine row | The row gets a dashed frame. After the drop, the photo is a card of that wine with no label; the counts of the row change. |
| TP15 | Drag the file of TP13 onto the sidebar again, then onto a wine row | The sidebar: an alert `1 of 1 file(s) not stored: … holds this image already as <name>`. The wine row: the card is added with the name of TP13. |
| TP16 | Drag a HEIC file, a PDF, or a file of more than 20 MB from the Finder onto the sidebar | An alert names each refused file and its reason. Nothing is added. |
| TP17 | Drop a Finder file on the header, not on a target | Nothing happens. The browser does not open the file, and the page stays. |
| TP18 | Drag a photo card of a wine onto the sidebar | `POST /api/testset-move` with `to` `__drawer__`, HTTP 200. The card leaves the row and stands in the sidebar with no label and the line `from <slug>`. The title still counts the same photos. The stats line ends with `last edit <time>`. The navigation stays in the title row at 1,440 px. |
| TP19 | Drag the sidebar card of TP18 onto another wine row | The card leaves the sidebar and is a card of that wine with no label. A file name that the row holds already gets `_moved<N>`. No file moves in `data/images/`. |
| TP20 | Click a card of the row `No Match`, then press `1` | The large view reads `No Match ·` and `No Match: <n> of <m> labelled`. After `1`: `confirmed: no card of the catalogue shows this wine`; the card turns green. `2` does nothing there. |
| TP21 | Open a photo of a wine in the large view | The position reads `wine <i> of <n>`; `<n>` is the count of the wine rows of the table, without `No Match` and the Drawer. |
| TP22 | Press `0` in the large view of a wine photo | The photo moves to the Drawer; the large view shows the next photo. |
| TP23 | Add a comment to a photo; then add a wine comment | After the photo comment, the stats line shows the new `last edit` time. The wine comment does not change it: a wine comment belongs to no set (plan 51). |
| TP24 | Look at the filter row of `/testset` | Three selects `Progress`, `Verdict`, and the button `Additional settings`; `Marks` and `Clusters` stand in the row of the button (TP36). There is no `Show`, no `Slugs`, and no `Wine`. `Progress` holds `all`, `not fully labelled`, `no label yet`, `partly labelled`, `fully labelled`, `no candidate photos`. `Verdict` holds `any`, `positive`, `no positive`, `negative`, `unusable`, `different design`. `Marks` holds `any`, `a comment`, `an agent proposal`, `a deletion mark`, `a box`. `Clusters` holds `No` and each embedding with a `clusters.json`: on 2026-09-26 `gx10-siglip2-so400m-patch16-naflex-p256 (168 clusters)`. |
| TP25 | Set `Progress` to `partly labelled` and `Verdict` to `negative` | The table holds the wines that pass both axes. On 2026-09-26 in `my`: 62 of 2105 (184 for `partly labelled` alone, 357 for `negative` alone). The address holds `filter=partial&verdict=has_neg`. |
| TP26 | Set `Progress` to `no candidate photos`, then `Verdict` to `no positive` | First 412 rows (2026-09-26, `my`), then 0. A wine with no photo in the set shows only when `Verdict`, `Marks`, and `Wine` stand on `any`. |
| TP27 | Open an address of the old single select: `/testset?filter=has_pos`, `?filter=noted` | The value goes to its axis: `Verdict` `positive`, `Marks` `a comment`. The address changes to `verdict=has_pos`, `marks=noted`. The count equals the count of the old option. |
| TP28 | Set `Verdict` and `Marks`, then click the tag `variant group of N` of a row | Every axis goes back to its first value. The table shows the group alone. |
| TP29 | Open `/testset?filter=excluded`, then `/testset?slugs=excluded` | Each time the full list: 2105 of 2105 wines (2026-09-26, `my`). The address drops the old key. No row is red: the exclusion went away (plan 51). |
| TP30 | Open `Additional settings` and choose `gx10-siglip2-so400m-patch16-naflex-p256` in `Clusters` | The count line reads `393 of 2105 wines shown · 168 clusters of gx10-siglip2-so400m-patch16-naflex-p256` (2026-09-26, `my`). The row `No Match` stays first. Then 168 header rows, each `<id> · <n> of <n> wines shown · <signals>`, for example `c032 · 2 of 2 wines shown · full + label`. The rows of one cluster stand together below their header. The address holds `cluster=<embedding>`. |
| TP31 | Keep the cluster of TP30 and set `Verdict` to `positive` | 145 wines in 82 clusters (2026-09-26). Some headers read `1 of 2`: a cluster shows in part. A wine in no cluster is not listed. |
| TP32 | Click the first photo of the first wine of TP31 | The large view reads `wine 1 of 145`. The Up and Down keys step over the wine rows and skip the header rows. |
| TP33 | Click `open on /clusters` of a header | A new tab opens `/clusters` with the view `combined`. The same cluster (same id) is marked and scrolled into view. |
| TP34 | Reload `/testset` with no query after TP30 | `Clusters` comes back on the embedding of TP30, and the table is grouped again. `?cluster=<embedding>` opens the same view; `?filter=grouped` and `?filter=removed` open with `Clusters` on `No`. |
| TP35 | Width 390 px and the dark theme with a cluster chosen | The header rows are readable in both themes. No horizontal scroll. |
| TP36 | Open `/testset` with an empty localStorage | The second row is hidden. The button reads `Additional settings`. A click shows the row with `Marks` and `Clusters` and marks the button; a second click hides it. A reload keeps the open state. |
| TP37 | Choose an embedding in `Clusters`, then `a comment` in `Marks`, then hide the row | The button reads `Additional settings · 1`, then `· 2`. With the row hidden, the count stays. |
| TP38 | With `Clusters` on `No`, open `Sort` | `cluster size, largest first` is disabled. `?sort=cluster_size` alone opens with `slug A-Z`. |
| TP39 | Choose an embedding in `Clusters` and `cluster size, largest first` in `Sort` | The first headers read `c001 · 8 of 8`, then the clusters of 6 (`c002`, `c003`, `c004` on 2026-09-26). Each size stands before a smaller size; a tie goes by the id. Inside a cluster the rows go by slug. The address holds `sort=cluster_size`. |
| TP40 | Set `Clusters` back to `No` after TP39 | `Sort` goes to `slug A-Z`, and `cluster size, largest first` is disabled again. |

### The row "No Match" and the Drawer

Read [plan 36](docs/plans/36_no-match-row-and-drawer.md). Run the write cases on a copy, as
above.

| # | Case | Expected result |
|---|---|---|
| NM1 | Open `/testset?set=official-real-photos` | The first table row is `No Match`, with a dashed box `NO MATCH` and the slug `__null__`. The sidebar title reads `Drawer`. The header button reads `drawer <n>`. |
| NM2 | Set any filter, any sort, any search word | The row `No Match` still stands first. The line `N of M wines shown` does not count it. |
| NM3 | Drag a wine card onto the sidebar | The card stands in the Drawer, with no label buttons and the line `from <slug>`. The stats line reads `1 in the Drawer`. |
| NM4 | Drag the card of NM3 onto the row `No Match` | `POST /api/testset-move` with `to` `__null__`. The card has `V` and `×`. The stats line reads `1 in No Match`. The large view status reads `No Match: a run expects no card for this photo`. |
| NM5 | Right-click a card of the Drawer, then a card of `No Match`, then a wine card | The Drawer: `Move to a wine…` and `Move to No Match`. `No Match`: `Move to a wine…` and `Move to the Drawer`. A wine card: `Move to the Drawer` and `Move to No Match`. |
| NM6 | `curl -s -X POST http://127.0.0.1:8174/api/testset-label -d '{"set":"official-real-photos","place":"__drawer__","file":"<file>","label":"positive"}'` on a Drawer photo | HTTP 400: `a photo of the Drawer takes no label`. |
| NM7 | Put one photo in `No Match` with no label and one in the Drawer, then run `python3 -c "import sys; sys.path.insert(0,'pipeline'); import benchmark as b; c=b.open_database('<copy>'); r,s=b.build_queries(c,'<copy>','official-real-photos'); print([x['image_path'] for x in r if x['slug']=='__null__'], dict(s))"` | The `No Match` photo is a row with the label `no_match`. The counts hold `drawer: 1`. Checked on 2026-09-26 on a copy. |
| NM8 | Open the page in the dark theme and at a width of 390 px | The row `No Match` and the Drawer follow the theme. The Drawer stands above the table as a strip. No horizontal scroll. |

### The comments of a photo and of a wine (plan 51)

Read [plan 51](docs/plans/51_testset-comments.md). Run the write cases on a copy, as above.
`$H` is the address of that copy.

| # | Case | Expected result |
|---|---|---|
| PC1 | `python3 tests/test_testsets.py`, `test_import_testset.py`, `test_export_testset.py`, `test_testset_routes.py`, `test_testset_from_run.py`, `test_testset_retention.py`, `test_labdb.py`, `test_benchmark.py` | Each `OK`. |
| PC2 | `sqlite3 data/lab.sqlite3 "SELECT count(*) FROM test_photo_comment; SELECT count(*) FROM wine_comment WHERE text LIKE 'Excluded from the benchmark: %'"` after the migration of 2026-09-26T18:50 | `1594` and `10`. The tables `test_wine_note` and `test_excluded` and the column `test_photo.comment` are gone. |
| PC3 | Open `/testset?set=my`, find `vysokij-bereg-risling-zelenaya-seriya-2` | `Comments 1`: the otzovik link of the old wine note, the time `2026-09-15 22:19`, the source `user`. |
| PC4 | Open `/testset?set=my#abrau-dyurso-abrau-estates-roze-kaberne-sovinon-rozovoe-suhoe-12/01_agent.jpg` | The panel `Comments on this photo 1` lists the old comment of the photo with the source `script`. |
| PC5 | In the panel of PC4 type a text, press `Esc`, then `Esc` again | The view closes, and the text is a new comment of the photo: a new open lists 2 comments. The same after `Esc` and an arrow key. |
| PC6 | Click `×` of a comment in the panel, then `OK` | The comment goes away; the count and the badge of the card follow. |
| PC7 | `curl -s -X POST $H/api/testset-photo-comment -H 'Content-Type: application/json' -d '{"set":"my","place":"<slug>","file":"<file>","text":" "}'` | HTTP 400: `the comment is empty`. |
| PC8 | `curl -s -X POST $H/api/testset-exclude -d '{}'` | HTTP 503: the route is gone. |
| PC9 | Export a set of the copy (TS8) with an old `excluded-slugs.json` in `--out` | The old file stays as it was. `review-labels.json` holds `comments` lists and no `wines`. |
| PC10 | Run `official-real-photos` with `Run>` | The 4 wines of the old exclusions (for example `fanagoriya-ona-skazala-da-beloe-bryut`) have queries in `queries.jsonl`. |
| PC11 | The dark theme and a width of 390 px, with the panel of PC4 open | The comment list and the field follow the theme. No horizontal scroll. |

## The button `Run>` of the Testset page — `pipeline/run_jobs.py` and `pipeline/run_job.py`

Read [plan 32](docs/plans/32_testset-run-button.md). `$H` is `http://127.0.0.1:8168`.
Plan 34 replaces the rows RJ2, RJ4, and RJ9: read the section "The pipelines".

| # | Case | Expected result |
|---|---|---|
| RJ1 | `python3 -m unittest discover -s tests -p 'test_run_jobs.py'` | 14 tests `OK` (2026-09-25). |
| RJ2 | Open `$H/testset?set=official-real-photos` and click `Run>` | A dialog `Run the set official-real-photos` with `80 queries in the set official-real-photos` (2026-09-25). Each configuration of `config.yaml` has a row. `vino-svoe-search-by-photo` (`svoe-vino-ru`) and `mock` (`mock`) can be chosen; the 11 embedding configurations are grey with `no runner yet`. `Start` is off until a row is chosen. |
| RJ3 | Press `Esc`, then open the dialog again and click outside the panel | `Esc` closes the dialog; a click outside the panel closes it too. While the dialog is open, the keys of the page (`s`, `1` to `4`) do not act. |
| RJ4 | Choose `mock`, leave the fields empty, `Start` | The dialog closes. A job row `mock · official-real-photos` shows `running`, then `done` with `80 / 80 · recall@1 …`, the elapsed time, and `open run`. `open run` opens `/runs?configuration=mock#<run id>`. The row goes away 60 s after the end. |
| RJ5 | Choose `vino-svoe-search-by-photo`, `first N queries` 5, `workers` 1, `Start` | The row counts `1 / 5` to `5 / 5` (about 3 to 10 s per photo on 2026-09-25), then `done`. The run directory is `runs/<stamp>-lab-vino-svoe-search-by-photo-official-real-photos/` with `answered: 5`. |
| RJ6 | Start `vino-svoe-search-by-photo` with no limit, then click `×` after some photos | The state goes to `stopping`, then `stopped` with `stopped after N of 80 photos` and `open run`. `run.json` holds `answered` = N. |
| RJ7 | While a run of a configuration runs, open the dialog again | The row of that configuration is grey with the note `running`. A second `POST /api/run-jobs` of it answers HTTP 409. |
| RJ8 | Reload the page while a job runs | The job row comes back with the same counts. |
| RJ9 | `curl -s -X POST $H/api/run-jobs -d '{"configuration":"gx10-dinov3-vitb16","set":"my"}'` | HTTP 400 with `... (backend openai): no runner yet`. |
| RJ10 | Switch the system to dark mode and repeat RJ2 and RJ4 | The dialog and the job row are dark. |
| RJ11 | Look at a running job row, then at the same row after the end; repeat in a window 390 px wide | A running or stopping row starts with a small icon button `×` in the muted text color, not red; a stopping row has it disabled. An ended row has an empty first cell and `open run` in the last cell, so the names of all rows start at the same place. At 390 px the first cell is a narrow column at the left of the row. |

## The Runs page of the lab server — `/runs` and `pipeline/mock_run.py`

Read [plan 23](docs/plans/23_runs-page.md). `$H` is `http://127.0.0.1:8168`.
Plan 34 replaces the rows RN4, RN5, RN7, RN12, RN13, RN14, and RN17: read the section
"The pipelines". The pipeline `mock` and `pipeline/mock_run.py` are removed, so RN1 to RN3
cannot run; RN6, RN8, and RN10 use the 2 old mock runs.

| # | Case | Expected result |
|---|---|---|
| RN1 | `python3 -m unittest discover -s tests -p 'test_run_files.py'`, then the same with `test_run_routes.py` and `test_mock_run.py` | 6, 7, and 14 tests `OK` (2026-09-25). |
| RN2 | `python3 pipeline/mock_run.py --set my --seed 20260925` | A new directory `runs/<stamp>-lab-mock-my/`. The console states `seed: 20260925`, `positive: 1625`, a recall@1 near 0.09, and a recall@5 near 0.45 (values of 2026-09-25). |
| RN3 | `python3 -c "import json; print(json.load(open('runs/<id of RN2>/run.json'))['configuration'])"` | `mock`. |
| RN4 | Open `$H/runs` | The table of the runs, the newest first, with the column `configuration`. The filter `Configuration` holds `every run — N`, each entry of `config.yaml` with its count, `mock — 1` or more, and `no configuration — N`. The newest run with metrics opens by itself. |
| RN5 | Choose `mock` in `Configuration` | The table holds the mock runs alone, and `k of N run(s)` stands next to the filter. The page address holds `?configuration=mock`. The first mock run opens. Reload: the filter keeps `mock`. |
| RN6 | Look at the photo rows of a mock run | Each row shows the test photo and 10 candidate images with falling scores. Some rows have the true wine at rank 1 (green frame at #1), some at a deeper rank, some `expected` (absent). No image is broken. |
| RN7 | Choose `no configuration` | The runs before 2026-09-25 alone. When the open run leaves the table, the first run with metrics of the table opens. |
| RN8 | Click the photo of a row of a mock run | The large view opens. Below the image: `This run sent no request to a model, so it has no model input.` |
| RN9 | Click the photo of a row of a run of `svm-siglip2-448` | The large view shows the model inputs, as in the review tool, or the error of `scripts/run_model_inputs.py` when the matcher config is not there. |
| RN10 | Choose `Show` = `negative: the wrong wine stands above the true wine` on a mock run | Rows with a red frame on the slug of the negative label above the dashed green frame of the true wine. |
| RN11 | Switch the system to dark mode and reload `$H/runs` | The page is dark. |
| RN12 | Open `$H/embedding` and choose `mock` | The selector has the label `Configuration`. The entry `mock` has the items of the other entries (`mock — 0 / N` before its first build). The details read `Model: random-unit-vectors`. |
| RN13 | Press `Build` for `mock` | The build runs as for any entry: progress, `Stop`, `Log`. No request goes to gx10. At the end `current` is the count of the items that got an image, and `index.json` in `data/embeddings/mock/` states `dim` 256. A second `Build` makes nothing again. |
| RN14 | Open `$H/runs` in a window 1,440 px wide | `Configuration` stands in the header, right after the title `Match runs N run(s)`. |
| RN15 | Look below the table of the runs | `1–25 · page 1 of <p>`, `prev` off, `next`, and `per page` 25. `next` shows the next 25 runs; on the last page `next` is off. |
| RN16 | Choose `per page` 50, reload | The table shows 50 runs; after the reload the page size is still 50. `all` shows every run. |
| RN17 | Choose a configuration with no run | `no run of this configuration`; `prev` and `next` are off. |
| RN18 | Open `$H/runs#<id of a run of ER2>` and look at the photo rows | In each row, each candidate card has the height of the tallest card of the row. In a row with a cluster frame, the cards outside a frame start and end at the level of the cards in the frame. A long slug, for example a `novyy-svet-…` slug, is not cut: its row is taller. |
| RN19 | Open `$H/runs` and look at the header | `Testset` stands right after `Pipeline`. It holds `All — N`, `my — k`, `official-real-photos — k`, and `no test set — k` (2026-09-26: 139, 28, 28, 83). The table has the column `testset`. |
| RN20 | Choose `my` in `Testset`, then a pipeline in `Pipeline` | The table holds the runs of set `my` alone, then the runs of that pipeline on set `my` alone. The page address holds `?set=my` and `?configuration=<name>`. `no test set` shows the runs of `scripts/match_run.py` alone, with `—` in the column `testset`. |
| RN21 | Choose `official-real-photos`, reload `$H/runs`, then open `$H/runs?set=my` | After the reload the filter keeps `official-real-photos`. The address `?set=my` wins over the stored value. |
| RN22 | `python3 -m unittest discover -s tests -p 'test_run_steps.py'`, then the same with `test_embedding_run.py` and `test_benchmark.py` | 10, 38, and 14 tests `OK` (2026-09-26, plan 41). |
| RN23 | Open `$H/runs#2026-09-26T044622Z-lab-local-siglip2-p256-crop-my-trace-probe`, click the query photo of the first row | The step popup opens: `Round 0` to `Round 2`, the cards `00 Input photo` to `05 Score`. Each round shows `elapsed … · sum of steps …`. The card `01 Package cut` has the pill `cached` and a time. The cards have a purple or blue left stripe. Only `00 Input photo` is open. |
| RN24 | In the popup of RN23, open `01 Package cut`, `02 View full`, and `04 Search, space full` | The photo with a pink box, the cut on a checker plate, the model input with `same as the run`, and 10 candidate cards with a cosine of 4 decimals. A click on an image opens the large view above the popup; `Esc` closes the large view, a second `Esc` closes the popup. |
| RN25 | In the popup, press the arrow key down, then up | The popup shows the next photo, then the first photo again. The open cards stay open. |
| RN26 | Open a run of `svm-label-gw-cluster-rules`, choose `Show` = `rule step: the VLM answered for the top cluster`, click a query photo | The cards `Matcher inputs`, `Search` (the order before the re-rank, with the time of the whole request), `Difference words`, and `VLM cluster rule` (the questions with the answers, the scores, the time). A moved card shows ▲n or ▼n. An older embedding run shows its steps with `—` and `time not recorded`. |
| RN27 | Open `$H/runs#2026-09-26T173050Z-lab-barcode-siglip2-512-crop-my`, press `load more` once, click the query photo of `q-000117`, then of `q-000014` | The header of the popup has a line under the path: `slug: abrau-dyurso-imperial-kyuve-pino-nuar-rozovoe-bryut-125` for the positive photo, `forbidden slug: abrau-dyurso-abrau-dyurso-pino-nuar-krasnoe-suhoe-13` for the negative photo. The label is grey, the slug is monospace. At 390 px the popup has no horizontal scroll (2026-09-26). |
| RN28 | Open `$H/runs#2026-09-26T173050Z-lab-barcode-siglip2-512-crop-my/abrau-dyurso-imperial-kyuve-pino-nuar-rozovoe-bryut-125/01_conf095.jpg` in a new tab | The run loads and the step popup of `q-000117` opens, with no click. The URL keeps the photo path. The row is on page 2, so the arrow keys do not move the popup. Escape closes the popup and the URL is `#2026-09-26T173050Z-lab-barcode-siglip2-512-crop-my` again (2026-09-27). |
| RN29 | On the same run, click the query photo of `q-000001`, then press the arrow key down | The URL becomes `#<run>/a-gordienko-m-nikolaev-pino-nuar-krasnoe-suhoe-135/01_manual.jpg`, then `…/02_manual.jpg`. A new tab with that URL opens the popup of `q-000002`, and the arrow keys work, because the row is on page 1. `#<run>/no-such-slug/x.jpg` opens the run with no popup and no page error (2026-09-27). |

## The remote configuration — `pipeline/remote_run.py`

Read [plan 31](docs/plans/31_remote-configuration.md). `$H` is `http://127.0.0.1:8168`.
Plan 34 replaces the rows RM4, RM5, and RM7 to RM10: read the section "The pipelines".

| # | Case | Expected result |
|---|---|---|
| RM1 | `python3 -m unittest discover -s tests -p 'test_remote_run.py'` | 15 tests `OK` (2026-09-25). |
| RM2 | `python3 pipeline/remote_run.py --name vino-svoe-search-by-photo --set my --limit 3 --workers 1 --label smoke` | A new directory `runs/<stamp>-lab-vino-svoe-search-by-photo-my-smoke/`. Each row of `results.jsonl` has `http_status` 201 and 10 candidates with `score: null`. On 2026-09-25 the 3 photos had the true wine at rank 1. |
| RM3 | `python3 -c "import json; m=json.load(open('runs/<id of RM2>/run.json')); print(m['configuration'], m['backend']['kind'])"` | `vino-svoe-search-by-photo remote`. |
| RM4 | `python3 pipeline/remote_run.py --name mock --set my` | `error: the configuration mock has the backend mock; this script runs the backend svoe-vino-ru alone`, exit code 1. |
| RM5 | Open `$H/runs` and choose `vino-svoe-search-by-photo` in `Configuration` | The table holds the runs of the configuration alone. The photo rows show the test photo and the candidate images. |
| RM6 | Click the photo of a row of a run of RM5 | The large view opens. Below the image: `This run sent the photo as it is to the remote matcher https://api.vino-svoe.ru/v1/wines/search-by-photo. The matcher reports no model input.` |
| RM7 | Open `$H/embedding` and choose `vino-svoe-search-by-photo` | The option reads `vino-svoe-search-by-photo — remote matcher`. `Build`, `Stop`, and `Log` are hidden, and the bar reads `remote matcher: no build`. The details show the URL, the request keys, `full: the photo as it is, no step`, and the command of a run with a `copy` button. The list reads `A remote matcher has no model inputs of the catalogue.` |
| RM8 | `curl -s -X POST $H/api/embeddings/vino-svoe-search-by-photo/build` | HTTP 400 with the text `... is a remote matcher (backend svoe-vino-ru); it holds no vectors. Make a run: ...`. |
| RM9 | Choose another entry on `$H/embedding` after RM7 | `Build`, `Stop`, and `Log` are visible again. |
| RM10 | Switch the system to dark mode and repeat RM7 | The page is dark. |

## The embedding runner — `pipeline/embedding_run.py`

Read [plan 33](docs/plans/33_embedding-run.md). `$H` is `http://127.0.0.1:8168`. `$P` is
`siglip2-p256-crop`, a pipeline of the backend `embedding`. Its key `embedding` names `$E`,
the entry `gx10-siglip2-so400m-patch16-naflex-p256`. The owner removed the first pipeline,
which had the name of `$E`, at about 01:07 on 2026-09-26. ER2 and ER3 send requests to
SAM3 and to the gateway of gx10.

| # | Case | Expected result |
|---|---|---|
| ER1 | `python3 -m unittest discover -s tests -p 'test_embedding_run.py'` | 33 tests `OK` (2026-09-26, with the 9 tests of plan 38; row CI1). No request goes to gx10. |
| ER2 | `python3 pipeline/embedding_run.py --name $P --set official-real-photos --limit 3 --label smoke` | The first line names the index of `$E` and the item counts, for example `4039 current items; 2 stale, 2 missing, 4 failed items stay out`. A new directory `runs/<stamp>-lab-$P-official-real-photos-smoke/`. Each row of `results.jsonl` has `http_status` 200 and 10 candidates. A cold start of the model can make the first request wait (51 s on 2026-09-25); a photo takes about 4 s. |
| ER3 | Run ER2 again, then `find data/cache/sam3 -name '*.json' -mmin -2 \| wc -l` | `0`: the second run sends no SAM3 request. |
| ER4 | `python3 -c "import json; m=json.load(open('runs/<id of ER2>/run.json')); print(m['configuration'], m['backend']['kind'], m['embeddings']['index_file'])"` | `$P embedding $E/vectors-<8 hex>.npy`. |
| ER5 | A row of `results.jsonl` of ER2 | Each candidate holds `slug`, `score`, `rank`, and the cosine of each view of the pipeline: `full` alone for `$P`. `score` is the mean of the view cosines. A pipeline with no key `views` has the views of its entry, so its candidates also hold `label` when the photo has a label cut. |
| ER6 | `python3 pipeline/embedding_run.py --name nope --set my` | `error: config.yaml has no pipeline nope`, exit code 1. |
| ER7 | Open `$H/runs`, choose `$P` in `Pipeline`, and click the photo of a row | The large view shows one model input with the badge `Embedding`: `full`, the box of the package with its own background. A run of the removed pipeline of 2026-09-25 (under `no pipeline`) shows `full` (the package on white) and `label` (the label on white); a photo with no label cut there shows `full` alone and the note `The view label has no input: SAM3 found no label.` |
| ER8 | `python3 pipeline/embedding_run.py --name vino-svoe-search-by-photo --set my` | `error: the pipeline vino-svoe-search-by-photo has the backend svoe-vino-ru; this script runs the backend embedding alone`, exit code 1. |

## The catalogue inputs of a candidate — plan 38

Read [plan 38](docs/plans/38_candidate-inputs.md). `$H` is `http://127.0.0.1:8168`. `$R` is
a run of `siglip2-p256-as-is` made after plan 38.

| # | Case | Expected result |
|---|---|---|
| CI1 | `python3 -m unittest discover -s tests -p 'test_embedding_run.py'` | 33 tests `OK` (2026-09-26); the class `CandidateItemsTest` holds 9. No request goes to gx10. |
| CI2 | `python3 pipeline/embedding_run.py --name siglip2-p256-as-is --set my --limit 30 --label probe`, then read the first row of `results.jsonl` | Each candidate holds `items`. For `q-000001`, rank 1 `fanagoriya-100-ottenkov-…` has 3 `full` items (0.8141, 0.5488, 0.5293) and 3 `label` items with `cosine` null. |
| CI3 | Open `$H/runs#$R` and click the image of the candidate at rank 1 of the first row | The large view opens. The strip shows the note `score 0.8141: the mean of the best cosine of each view (full 0.8141)`, then 6 items: `full · 0.8141` with the badge `best`, `full · 0.5488`, `full · 0.5293`, and 3 dim items `label · not compared`. The last note reads `The query has no view label, so the run did not compare these items.` |
| CI4 | Click the second item of CI3 | The PNG of that item becomes the large image. The view stays open. |
| CI5 | Press the right arrow key in the view of CI3 | The view shows the candidate at rank 2, and the strip shows its items (`full · 0.7794`). |
| CI6 | Open the run `2026-09-25T220722Z-lab-siglip2-p256-as-is-my` and click a candidate image | The strip shows the items of the present index with `no cosine` and the note `This run recorded no cosine of each item, because it ran before plan 38. …`. |
| CI7 | Click a candidate image of a run of `vino-svoe-search-by-photo` | The large view opens with no strip, as before plan 38. |
| CI8 | Click the photo of a row of `$R` | The strip shows the model input of the photo (`full`), as before plan 38. |
| CI9 | Repeat CI3 in the dark theme and in the light theme | The notes and the cosines are readable in both themes. |

## A new test set from the misses of a run — plan 44

Read [plan 44](docs/plans/44_testset-from-run-misses.md). `$H` is `http://127.0.0.1:8168`.
`$R` is `2026-09-25T235549Z-lab-local-siglip2-p256-crop-my-bench40`. NT7 and NT8 write a new
test set into `data/lab.sqlite3`.

| # | Case | Expected result |
|---|---|---|
| NT1 | `python3 tests/test_testset_from_run.py` | 6 tests `OK` (2026-09-26). |
| NT2 | `curl -s "$H/api/testset-from-run?id=$R"` | `set` `my`, `name` `my-1` while the database holds no `my-1`. `r1`: `selected` 419, `copied` 419. `r5`: `selected` 144, `copied` 144. Each count of `left_out` is 0 (2026-09-26). |
| NT3 | Open `$H/runs#$R` | The button `New testset…` stands after `Metrics of $R` and is on. Its tooltip names the test set `my`. |
| NT4 | Open a run whose column `testset` holds `—`, then a dry run | The button is off. Its tooltip states the reason. |
| NT5 | Press `New testset…` on `$R` | The dialog `New test set from the misses of a run` shows `R@1 misses — the true slug is not at rank 1 · 419 photo(s)` (chosen), `R@5 misses — the true slug is not in the top 5 · 144 photo(s)`, the note `419 positive photo(s) selected, 419 to copy.`, and `Name` `my-1`. |
| NT6 | Choose `R@5 misses` | The note reads `144 positive photo(s) selected, 144 to copy.` |
| NT7 | Type `my` into `Name` and press `Create` | The error `the test set my exists already`. The dialog stays open. |
| NT8 | Type a free name and press Enter | `The new test set <name> holds N photo(s): …`, a link to `/testset?set=<name>`, the line `Copied too: …`, and the button `Close`. The link opens the set on `/testset` with N photos. |
| NT9 | Close the dialog and press `New testset…` again | `Name` holds the next free name. |
| NT10 | Press `Esc`; open the dialog again and click outside the panel | The dialog closes each time. While it is open, the arrow keys do not move the page. |
| NT11 | Repeat NT5 in the dark theme | The dialog is dark. Each text is readable. |
| NT12 | Run the set of NT8 with `Run>` on `/testset` | The run takes each photo of the set; since plan 51 no slug is excluded. Its R@1 is the share of the misses of `$R` that the pipeline answers correctly now. |

## The pipelines — the key `pipeline` and `pipeline/pipelines.py`

Read [plan 34](docs/plans/34_pipeline-section.md). `$H` is `http://127.0.0.1:8168`. The
rows PL1 to PL14 replace the rows RJ2, RJ4, RJ9, RN4, RN5, RN7, RN12, RN13, RN14, RN17,
RM4, RM5, and RM7 to RM10. The owner removed the pipeline `mock` and
`pipeline/mock_run.py` on 2026-09-26 (owner message of 00:26:27), so the rows RN1 to RN3
cannot run; RN6, RN8, and RN10 use the 2 old mock runs. The test counts of RJ1 and RM1
changed too.

| # | Case | Expected result |
|---|---|---|
| PL1 | `python3 -m unittest discover -s tests -p 'test_pipelines.py'`, then the same with `test_run_jobs.py`, `test_remote_run.py`, and `test_run_routes.py` | 29, 14, 13, and 7 tests `OK` (2026-09-26). |
| PL2 | `python3 -c "import sys; sys.path.insert(0, 'pipeline'); import pipelines; print([(n, p.backend) for n, p, e in pipelines.load().entries])"` | `[('vino-svoe-search-by-photo', 'svoe-vino-ru'), ('siglip2-p256-as-is', 'embedding'), ('siglip2-p256-crop', 'embedding')]` (since about 01:07 on 2026-09-26: the owner removed the pipeline `gx10-siglip2-so400m-patch16-naflex-p256`). |
| PL3 | After a restart of 8168: open `$H/testset?set=official-real-photos` and click `Run>` | The dialog lists the three pipelines of PL2 alone, with the notes `svoe-vino-ru` and `embedding`. No entry of `embeddings` has a row. `Start` is off until a row is chosen. |
| PL4 | `curl -s "$H/api/run-configurations?set=official-real-photos"` | The three pipelines with `runnable: true`. `siglip2-p256-as-is` and `siglip2-p256-crop` have `workers: 1`. A pipeline of the backend `embedding` whose entry has no index has `runnable: false` and the reason `no index: build it on /embedding`. |
| PL5 | Start a pipeline of the backend `embedding` in the dialog, for example `siglip2-p256-crop` with `first N queries` 3 | The job row counts `1 / 3` to `3 / 3`, then `done`. The runner uses `~/.venvs/svoe-vino-lab/bin/python` (`embedding_python`): `lsof -bnPw -p <pid> \| grep -c .venvs/svoe-vino-lab` is above 0 (a framework Python shows the Homebrew path in `ps`). The run sends SAM3 and embedding requests to gx10. |
| PL6 | `curl -s -X POST $H/api/run-jobs -d '{"configuration":"gx10-dinov3-vitb16","set":"my"}'` | HTTP 404 with `config.yaml has no pipeline gx10-dinov3-vitb16`: an entry of `embeddings` is not a pipeline. |
| PL7 | Open `$H/runs` in a window 1,440 px wide | `Pipeline` stands in the header, right after the title `Match runs N run(s)`. The table has the column `pipeline`. |
| PL8 | Open the filter `Pipeline` of `$H/runs` | `All — N` (owner answer of 2026-09-26T01:19:00+0300), each pipeline of `config.yaml` with the count of its runs, and `no pipeline — N`. No entry of `embeddings`, no `mock`, and no item `(not a pipeline)`. On 2026-09-26 at 01:23: `All — 92`, `vino-svoe-search-by-photo — 3`, `siglip2-p256-as-is — 1`, `siglip2-p256-crop — 0` (its first run was not finished), `no pipeline — 88`: the 2 runs of the removed pipeline `gx10-siglip2-so400m-patch16-naflex-p256` and the 2 mock runs count there. |
| PL9 | Choose `vino-svoe-search-by-photo` in `Pipeline` | The table holds the runs of that pipeline alone. The page address holds `?configuration=vino-svoe-search-by-photo`. Reload: the filter keeps the value. |
| PL10 | Choose `no pipeline` | The runs whose `run.json` has no key `configuration` or a name that is not a pipeline, for example the 2 mock runs of 2026-09-25. |
| PL11 | Choose a pipeline with no run | `no run of this pipeline`; `prev` and `next` are off. |
| PL12 | Open `$H/embedding` and `$H/clusters` | Each combobox lists the 11 entries of `embeddings` alone: no `mock` and no `vino-svoe-search-by-photo`. |
| PL13 | `curl -s -X POST $H/api/embeddings/mock/build` | HTTP 404 with `config.yaml has no embedding mock`. |
| PL14 | `python3 pipeline/remote_run.py --name siglip2-p256-as-is --set my` | `error: the pipeline siglip2-p256-as-is has the backend embedding; this script runs the backend svoe-vino-ru alone`, exit code 1. `python3 pipeline/remote_run.py --name mock --set my` gives `error: config.yaml has no pipeline mock`. |
| PL15 | In the dialog of PL3, choose `siglip2-p256-as-is`, `first N queries` 3, `Start` | The job ends with `3 / 3`. The run sends no SAM3 request and one image for each photo. `run.json` holds `backend.views.full` = `white_background`, `resize`. On `/runs`, the model input of a row is the whole photo, 1024 px on the long side. |
| PL16 | The same with `siglip2-p256-crop` | The job ends with `3 / 3`. The model input of a row is the box of the package with its own background, 1024 px on the long side. A photo with no package found gets the border cut of the white rule. |
| PL17 | Put `views: {full: {steps: [{step: resize, max_size: 1024}, {step: segment, target: package}]}}` into a copy of a pipeline of the backend `embedding` and load the copy with `pipelines.load` | The entry has the error: view full: the first step MUST be segment. |

## The barcode step — the key `barcode` and `pipeline/barcode.py`

Read [plan 42](docs/plans/42_barcode-step.md). `$H` is `http://127.0.0.1:8168`.

| # | Case | Expected result |
|---|---|---|
| BC1 | `~/.venvs/svoe-vino-lab/bin/python -m unittest discover -s tests -p 'test_barcode.py'` | 28 tests `OK` (2026-09-26). With system `python3`: 28 tests, `OK (skipped=5)`; the decoder tests need zxing-cpp. |
| BC2 | `~/.venvs/svoe-vino-lab/bin/python -c "import importlib.metadata as m; print(m.version('zxing-cpp'))"` | `2.3.0`. |
| BC3 | `python3 -c "import sys; sys.path.insert(0, 'pipeline'); import pipelines; s = pipelines.load(); print(sum(1 for n, p, e in s.entries if p and p.barcode), [n for n, p, e in s.entries if e])"` | `22 []`: 22 twins `barcode-<pipeline>`, and no entry with an error. |
| BC4 | Put `barcode: {formats: [UPCE]}` into a copy of a twin and load the copy with `pipelines.load` | The entry has the error `barcode: unknown format UPCE`. |
| BC5 | After a restart of 8168: open `$H/testset?set=my` and click `Run>` | The dialog lists the 22 twins. A twin is runnable when the entry of its pipeline has an index. |
| BC6 | Start `barcode-siglip2-p256-as-is` on the set `my` with `first N queries` 10 | The job ends with `10 / 10`. `run.json` holds `backend.barcode` with `engine: zxing-cpp` and the count of the codes. A photo with a code of `wine_code` has candidates with `source`, `code`, `read`, and `format`, and score 1.0. |
| BC7 | On `/runs`, open the model inputs of a row that the code lookup answered | No input, and the note `The code lookup answered this photo: gtin ...`. A candidate of that row shows the note `The code lookup gave this wine`. |

## The cache of the model calls — `pipeline/model_cache.py` and `pipeline/gdino.py`

Read [plan 25](docs/plans/25_model-call-cache.md). `<photo>` is a file of `data/images/main/`.

| # | Case | Expected result |
|---|---|---|
| MC1 | `python3 -m unittest discover -s tests -p 'test_model_cache.py'`, then the same with `test_gdino.py` and `test_derive.py` | 12, 4, and 17 tests `OK` (2026-09-25). No directory `data/cache/` appears from a test. |
| MC2 | `python3 pipeline/gdino.py <photo> --texts "wine bottle"`, two times | The first output states `"cache": "miss"`, the second `"cache": "hit"` with the same instances. The second run takes about 0.2 s. One file is new in `data/cache/grounding-dino-base/`. |
| MC3 | MC2 with `--threshold 0.4`, then with `--model mm-gdino-base` | Each first run states `miss`. The second model gets its own directory `data/cache/mm-gdino-base/`. |
| MC4 | Open one record of MC2 | The keys `v`, `key`, `request`, `created`, `ms`, `answer`. `request` holds `endpoint` (the full URL), `model`, `params`, `prompt`, and `images` (one sha256 of 64 hex digits). No image bytes, no key. |
| MC5 | `python3 -c "import sys; sys.path.insert(0, 'pipeline'); import derive; print(derive.Sam3Client().segment(derive.open_image(sys.argv[1])[0]).getbbox())" <photo>`, two times, each with `time` | The same box two times. The first run takes about 1 s, the second about 0.2 s: the second run sends no request. After both runs, `data/cache/sam3/` holds one new file. |
| MC6 | `python3 pipeline/gdino.py <photo> --gateway http://127.0.0.1:9` | `error: the Grounding DINO service ... did not answer`, exit status 1, after about 30 s of retries. No file is new in `data/cache/`. |
| MC7 | `rm -r data/cache/grounding-dino-base/`, then MC2 one time | `"cache": "miss"`: the request goes to gx10 again. |

## The checkbox `Use caches` of the dialog `Run>` — `model_cache.READ` and `run_job.py --no-cache`

Read [plan 39](docs/plans/39_use-caches-checkbox.md). `$H` is `http://127.0.0.1:8168`.

| # | Case | Expected result |
|---|---|---|
| UC1 | `python3 -m unittest discover -s tests -p 'test_model_cache.py'`, then the same with `test_derive.py`, `test_run_files.py`, `test_benchmark.py`, and `test_run_jobs.py` | 13, 18, 7, 13, and 16 tests `OK` (2026-09-26). |
| UC2 | Open `$H/testset?set=my` and click `Run>` | The row of `first N queries` and `workers` holds the checkbox `Use caches`, checked. After a reload, the box is checked again. |
| UC3 | Clear `Use caches`, choose `siglip2-p256-crop`, `first N queries` 3, `Start` | The event `start` in `work/run-jobs/siglip2-p256-crop/job.log` holds `"use_cache": false`, and `ps` shows `run_job.py ... --no-cache`. Each of the 3 photos sends a SAM3 request: 3 records of `data/cache/sam3/` get a new `created`. `run.json` of the run holds `"use_cache": false`. On 2026-09-26 at 01:51, through `POST /api/run-jobs`: 3 records written again, median 1,300 ms. |
| UC4 | UC3 with `Use caches` checked | The event `start` and `run.json` hold `"use_cache": true`. The job sends no SAM3 request: no record of `data/cache/sam3/` gets a new `created`. The median latency is lower than in UC3. On 2026-09-26 at 01:51: no record written, median 116 ms. |
| UC5 | Open `$H/runs` | The run of UC3 has the tag `no cache` after its id, with a title. The run of UC4 and the runs before 2026-09-26 have no tag. |
| UC6 | `curl -s -X POST $H/api/run-jobs -d '{"configuration":"vino-svoe-search-by-photo","set":"my","use_cache":"no"}'` | HTTP 400 with `use_cache MUST be true or false`. No job starts. |
| UC7 | Switch the system to dark mode and repeat UC2 and UC5 | The checkbox and the tag follow the dark theme. |

## The checkbox `Disable barcode fast path` of the dialog `Run>` — `run_job.py --no-barcode`

Read [plan 53](docs/plans/53_disable-barcode-checkbox.md). `$H` is `http://127.0.0.1:8168`.

| # | Case | Expected result |
|---|---|---|
| NB1 | `python3 tests/test_run_jobs.py`, then `python3 tests/test_run_files.py` | 21 and 8 tests `OK` (2026-09-26). |
| NB2 | `curl -s "$H/api/run-configurations?set=my"` | Each pipeline has the key `barcode`: true for each `barcode-*` pipeline, false for the others. |
| NB3 | Open `$H/testset?set=my` and click `Run>` | The checkbox `Disable barcode fast path` stands after `Use caches`, unchecked and greyed. After a reload, it is unchecked again. |
| NB4 | Choose `siglip2-p256-crop`, then `barcode-siglip2-p256-crop` | The box is greyed for the first, with the title `The pipeline siglip2-p256-crop has no barcode step.`, and enabled for the second. |
| NB5 | Check the box, choose `barcode-siglip2-p256-as-is`, `first N queries` 3, `Start` | `ps` shows `run_job.py ... --no-barcode`. The event `start` in `work/run-jobs/barcode-siglip2-p256-as-is/job.log` and `run.json` hold `"use_barcode": false`. The key `backend` of `run.json` has no key `barcode`, and its label has no `after the code lookup`. The step popup of a photo on `/runs` has no step `barcode`. |
| NB6 | NB5 with the box unchecked | The event `start` and `run.json` hold `"use_barcode": true`, and the command has no `--no-barcode`. |
| NB7 | NB5 with `siglip2-p256-as-is` (the box is greyed) | The body of `POST /api/run-jobs` has no `use_barcode`. The event `start` holds `"use_barcode": null`; `run.json` has no key `use_barcode`. |
| NB8 | Open `$H/runs` | The run of NB5 has the tag `no barcode` after its id, with a title. The runs of NB6 and NB7 have no tag. |
| NB9 | `curl -s -X POST $H/api/run-jobs -d '{"configuration":"barcode-siglip2-p256-as-is","set":"my","use_barcode":"no"}'` | HTTP 400 with `use_barcode MUST be true or false`. No job starts. |
| NB10 | Switch the system to dark mode and repeat NB3, NB4, and NB8 | The checkbox, its greyed state, and the tag follow the dark theme. On 2026-09-26 at 19:53, NB3, NB4, NB8, and the request bodies of NB5 to NB7 passed in a browser check with `POST /api/run-jobs` intercepted, in light and dark mode. |

## The VLM inferences — the key `vlm` and `pipeline/vlm_config.py`

Read the section "The VLM inferences" of `README.md`.

| # | Case | Expected result |
|---|---|---|
| VL1 | `python3 -m unittest discover -s tests -p 'test_vlm_config.py'` | 19 tests `OK` (2026-09-25). The test also checks that `config.yaml` and `config.old.yaml` hold the same `vlm` section. |
| VL2 | `SVOE_VINO_REVIEW_CONFIG=config.old.yaml python3 -c "import sys; sys.path.insert(0, 'scripts'); import cluster_rules as c; print(c.MODEL, c.API, c.RULES_MODEL, c.RULES_API, c.RULES_KEY_ENV)"` | `qwen3.5-9b llama.cpp qwen3.8-max qwencloud QWENCLOUD_TOKEN_PLAN_API_KEY`. |
| VL3 | Put `url: x` into `cluster_rules` of a copy of `config.old.yaml`, and run VL2 with the copy | The import stops with `cluster_rules: the keys vlm and rules_vlm replace the old keys url`. |
| VL4 | Put `key: sk-test` into an entry of a copy of `config.old.yaml`, and run VL2 with the copy | The import stops with `key MUST be null or {env:NAME}`. The message does not hold `sk-test`. |
| VL5 | `python3 scripts/04_verify.py --help` with `SVOE_VINO_REVIEW_CONFIG=config.old.yaml` | The help of `--backends` states that a name is an entry of the key `vlm`, for example `qwen3-vl-32b:12`. |
| VL6 | One chat request to the entry `qwen3.5-9b-nvfp4` with one small image, `chat_template_kwargs.enable_thinking: false`, and JSON mode | HTTP 200, `finish_reason: stop`, the JSON answer, no reasoning text. On 2026-09-25 at about 16:21 the answer took 19.9 s. |

## The image descriptions — `image_description` and `pipeline/describe_images.py`

Read [plan 26](docs/plans/26_image-description.md) and the section "The image descriptions"
of `README.md`. `H=http://127.0.0.1:8168`.

| # | Case | Expected result |
|---|---|---|
| ID1 | `python3 -m unittest discover -s tests -p 'test_image_descriptions.py'`, then the same with `test_describe_images.py` | 11 and 18 tests `OK` (2026-09-25). No test writes into `data/cache/`. |
| ID2 | Open `$H/dataset` | Each image of a card (main, patch, alternative photo) has a button `✎` in its bottom right corner. The button of an image with a set value has the accent color. Its title lists the four values. |
| ID3 | Press `✎` of a main image | A dialog opens with the original image, three selects, three checkboxes, and a status line (`Created by`, `VLM: pending`, `filled at … by …`, or `failed … times`). The image preview does not open. |
| ID4 | Check `unknown`, then `front_label` | Each check clears the other kind: `unknown` stands alone. |
| ID5 | Set `package_type: tetra_pak`, press Save | The dialog closes. The button of the card gets the accent color. `sqlite3 data/lab.sqlite3 "SELECT package_type, created_by, vlm_at FROM image_description WHERE sha256 = '<sha256>'"` gives `tetra_pak|manual|` before the VLM run. |
| ID6 | Wait for the watcher, or run `python3 pipeline/describe_images.py --sha <sha256>` while no watcher runs | The row keeps `tetra_pak`. The other three values are filled. `vlm_at` is set. `vlm_answer` holds the full answer. The log line ends with `package_type kept`. |
| ID7 | Press Esc, Cancel, or the backdrop in the dialog | The dialog closes with no change. |
| ID8 | Restart 8168 with SIGTERM | The start report names the pid of the watcher. After the stop, `pgrep -f describe_images` finds no process. |
| ID9 | Light and dark theme, and a width of 390 px | The dialog fits; the image stands above the fields at 390 px. No horizontal scroll. |
| ID10 | Open `$H/dataset` while the watcher works | The pill left of `Add wine` reads `VLM <described> / <linked> · <seconds> s` with a green dot that pulses. The numbers grow within 5 s. The title names the pid, the wine of the image in work, the counts, the speed, and the last step. |
| ID11 | `curl -s $H/api/image-description-status` | JSON with `state`, `pid`, `vlm`, `sha256`, `slug`, `seconds_per_image`, `linked`, `described`, `failed`, `pending`. |
| ID12 | Stop 8168 with SIGTERM, start it with `image_description.watch: false`, open `$H/dataset` | The pill reads `VLM watcher not running` with an empty dot. |
| ID13 | Width 390 px | The pill and the buttons wrap in the bar. No horizontal scroll. |
| ID14 | Open `✎` of a main image that the VLM filled, then open `Raw VLM reply` | One line with the model, `finish_reason`, the tokens, the time, and the cache time, then the reply text. Closed sections `Prompt`, `Full response body (JSON)`, and `Request fields (JSON)`. |
| ID15 | Open `✎` of an image that the VLM did not fill | No block `Raw VLM reply`. |
| ID16 | `curl -s "$H/api/image-description-reply?sha256=<64 zeros>"`, then with `sha256=XYZ` | HTTP 404 `no image with the sha256 …`, then HTTP 400 `` `sha256` MUST be 64 lower-case hex digits ``. |
| ID17 | Press `Advanced Filters:`, then again | A second row with `Package` shows, then hides. |
| ID18 | Choose `Package: can` | The header reads `<n> of <total> records`; each card shows a wine whose patched image, else main image, has `package_type` `can`. The button `Advanced Filters:` is marked, also with the row closed. |
| ID19 | Choose `Package: not described` | The wines whose deciding image has no `package_type`, and the wines with no image. |
| ID20 | Width 390 px with the filter row and the dialog block open | No horizontal scroll. |
| ID21 | Open the select `Package` | `All`, then only the values that at least one wine has, in the order of `image_descriptions.VALUES`, then `not described` when a wine has no value. On 2026-09-25: `bottle`, `can`, `tetra_pak`, `box`, `not described` (2,009, 11, 21, 6, and 57 wines). |
| ID22 | Choose `Package: box`, then save the last `box` wine as `keg` in the dialog | The select now holds `keg`. It keeps `box` while `box` is chosen; after a reload `box` is gone. |
| ID23 | Choose `Identifier: has GTIN`, then `has QR URL`, then `has Drink Atlas` | Each card shows a wine with at least one GTIN, at least one QR URL, or an Atlas Core product (manual or automatic). The button `Advanced Filters:` is marked. On 2026-09-26: 22, 3, and 367 of 2,103 records. |
| ID24 | Choose `Identifier: has Drink Atlas` and `Package: bottle` | The two filters apply together: a card MUST match both. |
| ID25 | Choose `Identifier: has GTIN`, then reload | The select keeps `has GTIN`, the filter applies, and the button `Advanced Filters:` is marked. |
| ID26 | Press `✎` of an image | Below `content_roles`, a select `presentation_mode` with `— not set —`, `on_package`, `flat_surface`, `other`, `unknown`. The title of `✎` lists five values. |
| ID27 | Set `presentation_mode: flat_surface`, press Save, open `✎` again | The select shows `flat_surface`. `sqlite3 data/lab.sqlite3 "SELECT presentation_mode FROM image_description WHERE sha256 = '<sha256>'"` gives `flat_surface`. A later VLM answer does not change it. |
| ID28 | `curl -s -X POST -H 'Content-Type: application/json' -d '{"sha256":"<sha256>","values":{"presentation_mode":"table"}}' $H/api/image-description` | HTTP 400 `presentation_mode MUST be one of on_package, flat_surface, other, unknown`. No row changes. |
| ID29 | `tail work/describe_images.log` after schema 024 | Each class line holds the fifth value after `content_roles`, for example `["front_label"] on_package 7.1 s`, and ends with `package_type kept, subject_scope kept, package_view kept, content_roles kept` for a row of the 024 queue. |
| ID30 | `sqlite3 data/lab.sqlite3 "SELECT count(*), count(vlm_at), count(presentation_mode) FROM image_description"` after the 024 queue | The three counts are equal. On 2026-09-26 at 20:19 the queue held 2,091 rows. |

## The image details — `image_detail` and stage 2 of `pipeline/describe_images.py`

Read [plan 29](docs/plans/29_image-details.md) and the section "The image details" of
`README.md`. `H=http://127.0.0.1:8168`.

| # | Case | Expected result |
|---|---|---|
| DT1 | `python3 -m unittest discover -s tests -p 'test_image_details.py'`, then the same with `test_describe_images.py` | 13 and 38 tests `OK` (2026-09-25). No test calls the real VLM or writes into `data/cache/`. |
| DT2 | `curl -s $H/api/image-description-status` | The JSON also holds `stage`, `details_eligible`, `details_done`, `details_failed`, `details_pending`. On 2026-09-25: `details_eligible` 2,015. |
| DT3 | Open `$H/dataset` while stage 2 works | The pill reads `VLM details <done> / <eligible> · <seconds> s` with a pulsing green dot. Its title has a line `Details <done> of <eligible> · pending … · failed …`. |
| DT4 | `tail work/describe_images.log` while stage 2 works | Lines `<sha12> detail ok package bottle, <n> texts, <s> s`. |
| DT5 | `sqlite3 data/lab.sqlite3 "SELECT json(answer) FROM image_detail WHERE vlm_at IS NOT NULL LIMIT 1"` | One JSON object with the keys `texts`, `numbers`, `vintage`, `colours`, `design`, `marks`, and the key of the `package_type` (for example `bottle`). A `label` row has no seventh key. |
| DT6 | Set `package_type` of a detailed image to `can` in the dialog `✎` | `details_done` drops by one; the watcher sends the image again with `one wine can` and the key `can`. The row then holds `package_type` `can`. |
| DT7 | Set `subject_scope: multiple_packages` for an image with no detail | The image leaves `details_eligible`. The watcher sends no detail request for it. |
| DT8 | Stop 8168, set `image_description.details: false`, start 8168 | The watcher runs stage 1 alone. `details_pending` stays. |
| DT9 | `curl -s $H/api/image-detail-failures` | The JSON holds `max_attempts`, `log_file` (`work/describe_images.log`), and `failures`. Each failure has `wine_slug`, `prompt_kind`, `package_type`, `input_url`, `vlm_attempts`, `vlm_error`, `updated_at`, and `log`. The count equals `details_failed` of DT2. On 2026-09-25: 1 failure, `usadba-mezyb-shishka-merlo-vione-rozovoe-suhoe-125`, 3 attempts, 4 log entries. |
| DT10 | Click `N details failed` in the pill of `$H/dataset` | The dialog `Failed details` opens. Each image shows a thumbnail, the slug with `FAILED`, the prompt kind, the type, the attempts, the time, and an open block `Last error`. The closed block `Log · N entries` holds the whole cut answer of each failed call. `Escape`, `×`, `Close`, and a click outside close it. |
| DT11 | Press `Tab` to the button `N details failed` and wait 10 s | The button keeps the focus while the pill text stays the same. |
| DT12 | Click the thumbnail in the dialog `Failed details` | The image preview shows `the file that the VLM got · <slug>`, the sha256 of the file, and its size (1851 × 6279 px on 2026-09-25). The arrows are off, there are no thumbnails, and the page path stays. The first `Escape` closes the preview alone; the dialog stays open. A Cmd-click opens the file in a new tab. |
| DT13 | Set `max_tokens: 0` on the `vlm` entry of `image_description.vlm`, then run `python3 pipeline/describe_images.py --once` | `error: vlm entry qwen3.5-9b-nvfp4: max_tokens MUST be a positive integer`. Nothing is sent. |
| DT14 | Add `detail_max_tokens: 4096` under `image_description`, then run `python3 pipeline/describe_images.py --once` | The error names `detail_max_tokens` and says that `max_tokens` of the vlm entry replaced it. |
| DT15 | Read a record of `data/cache/qwen3.5-9b-nvfp4/` written after 2026-09-25T23:28 for a detail request (`response_format.type` `json_schema`) | `request.params.max_tokens` is 8192. A class record keeps 300. |

## The VLM workers — `image_description.workers`

Read [plan 35](docs/plans/35_vlm-workers.md). `H=http://127.0.0.1:8168`.

| # | Case | Expected result |
|---|---|---|
| VW1 | `python3 -m unittest discover -s tests -p 'test_describe_images.py'`; restart 8168 with `image_description.workers: 8`; after 5 min read `work/describe_images.log` and the pill of `$H/dataset` | 48 tests `OK` (2026-09-26), `WorkersTest` among them. The start line holds `workers 8`. The speed on the pill (the wall time per image) is at most half of the mean `<s> s` of the detail lines of the same minutes (the time of one call). On 2026-09-26: 2.1 s on the pill against a mean call of 16.0 s. After a `timed out` line, no new call starts for 30 s, and the calls that run finish (00:42:29 to 00:42:59). |

## The probe after a VLM timeout and the dialog of the watcher — plan 49

Read [plan 49](docs/plans/49_vlm-timeout-probe.md). `H=http://127.0.0.1:8168`.

| # | Case | Expected result |
|---|---|---|
| VP1 | `python3 tests/test_describe_images.py PostTimeoutTest TimeoutProbeTest` | 7 tests `OK` (2026-09-26). |
| VP2 | `python3 tests/test_image_descriptions.py WatcherStatusTest LogTailTest` | `OK`; the views of the calls, the wait, and the log tail. |
| VP3 | `python3 -c "import sys; sys.path.insert(0, 'pipeline'); import yaml, describe_images as d, vlm_config; c = yaml.safe_load(open('config.yaml')); print(d.probe(vlm_config.entry(c, d.settings(c)['vlm'])))"` | A time in seconds. On 2026-09-26: 0.12 s against `qwen3.5-9b-nvfp4` on gx10. |
| VP4 | After a restart of 8168: `curl -s $H/api/image-description-status` | The JSON also holds `max_attempts`, `endpoint` (the full chat URL, with the port `18081`), `timeout_seconds` 300, `workers`, `running` (a list), `waiting_since`, `backoff_seconds`, `retry_at`, `retry_in_seconds`, and `error_image`. No key `log`. |
| VP5 | `curl -s "$H/api/image-description-status?log=30"`; then `?log=0` and `?log=x` | The first answer adds `log_file` (`work/describe_images.log`) and `log`, 30 lines, oldest first. The other two answer HTTP 400 with "`log` MUST be a whole number from 1 to 200". |
| VP6 | A watcher in the state `waiting`: look at the pill of `$H/dataset` | The pill shows the full error, for example `VLM waiting: no answer from http://192.168.86.14:18081/v1/chat/completions in 300 s: timed out; …`. A long error wraps into lines; no character is cut. |
| VP7 | Click the text of the pill | The dialog `VLM watcher` opens: `State`, `Endpoint`, the error, `Backoff and retry` (in `waiting`), `Requests that run · N of 8`, and `Watcher log` with 30 lines. The page asks `?log=30` every 5 s while the dialog is open. A click on a thumbnail opens the preview; Escape closes the preview first, then the dialog. |
| VP8 | Click `N details failed` in the pill | The dialog `Failed details` opens, not the dialog `VLM watcher`. |
| VP9 | Light and dark system theme, width 1280 px and 375 px | The badge `WAITING` is amber, as the pill. No horizontal page scroll; no section of the dialog is wider than the dialog. On 2026-09-26 a Playwright check with a synthetic `waiting` answer passed 88 of 88 checks. |
| VP10 | An image whose request times out while the probe answers | `work/describe_images.log` holds `<sha12> detail failed: no answer from … in 300 s: timed out; a probe of the model answered in <s> s, so the failure counts against the image` (no `(not counted)`). No backoff follows; other images go on. After 3 such lines the image is in `N details failed`. |

## The seed and the restore — `pipeline/seed_from_testset.py`

Read [plan 28](docs/plans/28_seed-from-testset.md). Use a test database, not
`data/lab.sqlite3`. A full run asks SAM3 on gx10 for each image that `data/cache/sam3/`
does not hold (about 0.6 s for each image).

| # | Case | Expected result |
|---|---|---|
| SD1 | `python3 -m unittest discover -s tests -p 'test_seed_from_testset.py'` | 10 tests, `OK`. |
| SD2 | `python3 pipeline/seed_from_testset.py --db data/lab-test.sqlite3` with no file `data/lab-test.sqlite3` | Eight lines `== step N of 8`, each with `exit status 0`. The table of row counts has `-` in the column `old`. `backup: none; …`. `result: … holds the state of svoe-vino-testset`. |
| SD3 | Run SD2 again | The column `old` holds the counts of SD2. `backup: …/data/backups/lab-test-<UTC time>.sqlite3`. The counts of `new` equal the counts of SD2. |
| SD4 | Stop SD2 with Ctrl+C during a step | The script stops. `data/lab-test.sqlite3` does not change. `data/lab-test.sqlite3.seeding` stays; the next run prints `delete the partial database of an earlier run`. |
| SD5 | After SD3: `sqlite3 data/lab-test.sqlite3 "SELECT set_name, count(*) FROM test_photo GROUP BY 1"` | `my\|4043`, `official-real-photos\|100`, `vlmrerank-8b-failed\|180` (values of 2026-09-25). |
| SD6 | Remove `data/lab-test.sqlite3`, its `.seeding` file, and `data/backups/lab-test-*` | The live `data/lab.sqlite3` did not change during SD2 to SD5. |

## The Health page — plan 46

Read [plan 46](docs/plans/46_health-page.md). Use `H=http://127.0.0.1:8168`. The button
`Check` sends a real call of 1 token to each model that runs on gx10 and to each cloud
entry.

| # | Case | Expected result |
|---|---|---|
| HL1 | `python3 tests/test_health.py` | 28 tests, `OK`. |
| HL2 | Open `$H/health` | The cards `Server`, `Database`, `Image description watcher`, `Jobs`, and one card for each llama-swap gateway. The table lists each endpoint of `config.yaml` as `not checked`. The link `Health` is last in the navigation and marked. |
| HL3 | Press `Check` | The button is disabled. Each row gets its result when its answer comes; the message counts the rows. At the end: `<N> endpoints, checked in <s> s: …` with the count of each status, and the status part loads again. |
| HL4 | `curl -s http://192.168.86.14:18081/running` before and after HL3 | The same models run after the check: the check loads no model. A model that ran has `ok` with its answer time; a model that did not run has `idle`. |
| HL5 | Press `Check` two times | The second check gives the same statuses. No llama.cpp model stops (each chat request holds a new random token). |
| HL6 | Open `details` of a row | Each request of the check with its HTTP code and its time. |
| HL7 | `curl -s -X POST $H/api/health/check -d '{"kind":"vlm","name":"nope"}'` | HTTP 404: `config.yaml has no vlm endpoint nope`. |
| HL8 | Open `$H/health` with the system theme dark, then light | Both themes are readable. The badges use the colours of `theme.css`. |
| HL9 | Open `$H/health` at a width of 390 px | No horizontal scroll of the page. The table scrolls in its own box. |

## The Recognize page — plan 55

Read [plan 55](docs/plans/55_recognize-page.md). Use `H=http://127.0.0.1:8168`. A pipeline
of gx10 sends one SAM3 request and one embedding request for each photo; llama-swap loads
its embedding model when it does not run. A pipeline of the backend `local` runs on this
Mac.

| # | Case | Expected result |
|---|---|---|
| RC1 | `python3 -m unittest discover -s tests -p 'test_recogni*.py'`, then the same with `test_lab_pages.py` | 16 and 4 tests `OK` (2026-09-26). |
| RC2 | Open `$H/recognize` | The select `Pipeline` lists the pipelines of the backend `embedding`. A pipeline with no index is disabled and states its reason. The message states `<N> of <M> pipelines can run`. The link `Recognize` stands between `Runs` and `Health` and is marked. |
| RC3 | Choose `local-siglip2-p256-crop`, drop the photo `a-gordienko-m-nikolaev-pino-nuar-krasnoe-suhoe-135/01_manual.jpg` of set `my` on the page | The message counts the seconds. The answer shows `Round 0` to `Round 2`, the cards `00 Input photo` to `05 Score`, and the total line. The head line shows `#1 a-gordienko-m-nikolaev-pino-nuar-krasnoe-suhoe-135` and `process … (start of Python, build of the backend …, recognition …)`. Only `00 Input photo` is open. |
| RC4 | Choose `barcode-local-siglip2-p256-crop`, press `Recognize` with the photo `abrau-dyurso-abrau-estates-kaberne-po-belomu-kaberne-sovinon-beloe-suhoe-105/02_manual.jpg` of set `my` | Only the cards `00 Input photo` and `01 Decode codes, whole photo`. The head line has the tag `code lookup`. |
| RC5 | Click the drop area, choose a file | The file dialog opens. The chosen file goes to the pipeline at once, and the drop area shows its preview and its name. |
| RC6 | Change the pipeline while a photo is loaded, then reload the page, then open `$H/recognize?pipeline=local-siglip2-p256-as-is` | The change sends nothing and enables `Recognize`. After the reload the select keeps the pipeline. The address wins over the stored value. |
| RC7 | Open a card, click an image | The card opens and closes with a click. The image opens in the large view; a click or `Esc` closes it. |
| RC8 | `curl -s -X POST "$H/api/recognize?pipeline=nope" --data-binary @<photo>`, then the same with `pipeline=local-siglip2-p256-crop` and `--data-binary 'text'` | HTTP 400 `config.yaml has no pipeline nope`, then HTTP 400 `the body is not an image that Pillow can read`. |
| RC9 | Open `$H/recognize` with the system theme dark, then light, and at a width of 390 px | Both themes are readable. No horizontal scroll of the page at 390 px. |
| RC10 | Recognize the same photo two times, then `ls work/recognize/` | One file `<sha256>.<ext>` for the photo. The second upload keeps the file. |
| RC11 | Open the step popup on `/runs` (RN23, RN24) | The popup looks and works as before the move of the step view to `steps.css` and `steps.js`. |

## The text export of the lab database — plan 50

Read [plan 50](docs/plans/50_lab-db-text-export.md) and the skill
[`backup-lab-db`](.claude/skills/backup-lab-db/SKILL.md). Use a scratch directory `$T`.

| # | Case | Expected result |
|---|---|---|
| DX1 | `python3 tests/test_db_export.py` | 8 tests, `OK`. |
| DX2 | `python3 pipeline/db_export.py export --out $T/one` | `export: … (schema 21, 17 tables, <N> rows)` in less than 2 s. `$T/one` holds `schema.sql`, `after-rows.sql`, and 17 files in `rows/`. `data/lab.sqlite3` does not change. |
| DX3 | `python3 pipeline/db_export.py restore --from $T/one --db $T/r.sqlite3`, then `export --db $T/r.sqlite3 --out $T/two`, then `diff -r $T/one $T/two` | The same row counts as DX2. `diff` prints no line. |
| DX4 | Run the restore of DX3 again | `error: … exists already; the restore writes a new file alone`, exit status 1. `$T/r.sqlite3` does not change. |
| DX5 | `head -2 $T/one/rows/wine_code.jsonl` | Each line is one JSON object. The first key is `rowid`. The rows are in the order of `wine_slug`, `kind`, `value`. |
| DX6 | Run the skill `backup-lab-db` two times with no change of the database between the runs | The first run makes one commit that changes `db-export/` alone. The second run prints `no change since the last export` and makes no commit. `git diff --cached --name-only -- db-export` prints no line after each run. |
| DX7 | `git check-ignore -v data/cache/x data/lab.sqlite3 data/images/cropped/x data/images/main/x.webp data/images/patched/x.png` | The first three paths are ignored. The two image paths print no line: git keeps them. |
| DX8 | Add a file to `data/images/patched/`, then run the skill | The commit holds the new file. The message has `1 A data/images/patched`. |
\n
## The manual cut of an alternative photo — plan 56

Read [plan 56](docs/plans/56_manual-alternative-cut.md). `$H` is the lab server. Use a
wine with one alternative photo of the type `FF`.

| # | Case | Expected result |
|---|---|---|
| MC1 | `python3 -m unittest discover -s tests -p 'test_alternatives.py'` | 54 tests, `OK`. |
| MC2 | Open the preview of the photo | The head shows `Manual cut`. `Remove manual cut` is not there. |
| MC3 | Press `Manual cut` | The preview shows the original. The arrows and the thumbnails go away. The bar reads `0 points. …`. |
| MC4 | Click 4 points around the bottle, drag one point, right-click one point | The polygon follows. The hint counts 4, then 3 points. `Save cut` is enabled at 3 points. |
| MC5 | Press Left, Right, then Backspace | The arrow keys do nothing. Backspace removes the last point. |
| MC6 | Add points again and press `Save cut` | The preview shows the cut on the checkerboard. The card and the thumbnail show the badge `manual`. `Remove manual cut` is there. |
| MC7 | Press `Manual cut` again, then Escape | The editor loads the saved polygon. Escape closes the editor, and the preview stays open. |
| MC8 | Press `FB`, then `LF`, then `FF` on the card | `FB` keeps the manual cut. `LF` shows the SAM3 label cut, with no badge `manual`. `FF` shows the manual cut again. |
| MC9 | Drop the same photo on the wine again | Nothing changes. The manual cut stays. |
| MC10 | Press `Remove manual cut` and confirm | The badge `manual` goes away. The preview shows the SAM3 cut. `image_derivative.settings` of the photo is `derive.SETTINGS_SEG` again. |
| MC11 | Switch the system to dark mode and repeat MC3 and MC6 | The bar, the buttons, and the badge are readable. The polygon is visible on the photo. |
\n
## The option `Add new testset …` of `/testset` — plan 57

Read [plan 57](docs/plans/57_testset-new.md). `$H` is the lab server. Each case MAY make
a set in `data/lab.sqlite3`; no route removes it.

| # | Case | Expected result |
|---|---|---|
| NS1 | `python3 -m unittest discover -s tests -p 'test_testset*.py'` | All tests `OK`. |
| NS2 | Open `$H/testset` and open the combobox `Test set` | The last option reads `Add new testset …`. |
| NS3 | Choose `Add new testset …` | A dialog opens with the focus in `Name`. The combobox still shows the current set. The address does not change. |
| NS4 | Type `My Set`, then `my` | The error line reads `A name holds 0-9, a-z, _ and - alone.`, then `The set my exists already.`. `Create` stays disabled. |
| NS5 | Press Escape; open the dialog again and click outside the panel | Each closes the dialog. No set is made. |
| NS6 | Type a free name, for example `smoke-new`, and press Enter | The dialog closes. The page shows `smoke-new (0 photos)` and the address holds `?set=smoke-new`. The combobox lists it before `Add new testset …`. |
| NS7 | Drop one image file on a wine row of the new set | The photo appears; the count reads `1 photos`. |
| NS8 | Switch the system to dark mode and repeat NS3 | The dialog, the field, and the error line are readable. |
| NS9 | Open `Run>`, press Escape; open it again and click outside | The Run> dialog closes each time, as before plan 57. |

## The pipeline `siglip2-p256-crop-seg`

Owner message of 2026-09-26T23:24:00+0300. `$H` is the lab server.

| # | Case | Expected result |
|---|---|---|
| CS1 | `python3 -m unittest discover -s tests -p 'test_barcode.py'` | All tests `OK`. The twin test counts 26 plain pipelines. |
| CS2 | Open `$H/recognize` and open the select `Pipeline` | `siglip2-p256-crop-seg` comes directly after `siglip2-p256-crop`, and `barcode-siglip2-p256-crop-seg` directly after `barcode-siglip2-p256-crop`. Both are enabled. |
| CS3 | Choose `siglip2-p256-crop-seg` and drop the photo `a-gordienko-m-nikolaev-pino-nuar-krasnoe-suhoe-135/01_manual.jpg` of set `my` | The card `View full` reads `segment → remove_background → white_background → resize`. Its image shows the bottle on white, with no room behind it. `#1` is `a-gordienko-m-nikolaev-pino-nuar-krasnoe-suhoe-135` (cosine 0.9098 on 2026-09-26). |
| CS4 | Choose `siglip2-p256-crop` and press `Recognize` | The image of `View full` keeps the background inside the box. The cosine of `#1` is lower (0.8463 on 2026-09-26). |
| CS5 | Choose `barcode-siglip2-p256-crop-seg` and press `Recognize` with the same photo | The card `Decode codes, whole photo` comes first. With no code hit, the rounds and `#1` are the rounds and `#1` of CS3. |

## Shared codes — plan 58

Owner message of 2026-09-26T23:54:53+0300, answers of 23:59:00. `$H` is the lab server.
Belmas 135 is `belmas-winery-viogner-katya-vione-beloe-suhoe-135`. Belmas 122 is
`belmas-winery-viognier-belmas-vione-beloe-suhoe-122`. Both have the GTIN
`04630171632036` and the QR URL `https://belmaswinery.com/`.

| # | Case | Expected result |
|---|---|---|
| SC1 | `python3 -m unittest discover -s tests -p 'test_barcode*.py'` | All tests `OK`. |
| SC2 | Open `$H/dataset` and find Belmas 135 | The GTIN `04630171632036` and the QR URL `https://belmaswinery.com/` each show the badge `2 wines` at the right of `copy` (of `open` for the QR URL). The tooltip reads `Also on: <slug of Belmas 122>`. A click on the badge does nothing. |
| SC3 | Find Belmas 122 | The same two badges. The tooltip names Belmas 135. |
| SC4 | Find a wine with a GTIN of one wine | The GTIN has no badge. |
| SC5 | Switch the OS to dark mode and reload | The badges use the amber colour of the dark theme. The text is readable. |
| SC6 | Open the page at 390 px width | The badges wrap inside the card. The page has no horizontal scroll. |
| SC7 | On `$H/recognize`, choose `barcode-siglip2-p256-crop` and drop a photo of Belmas 122 with the EAN-13 `4630171632036` in view (for example, draw the code beside the test photo `belmas-winery-viognier-belmas-vione-beloe-suhoe-122/01_agent.webp` with `ean13` of `tests/test_barcode.py`) | The card `Decode codes, whole photo` lists the 2 wines of the code. The SAM3, view, embed, search, and score cards follow. The answer holds Belmas 122 and Belmas 135 alone, with cosine scores (122 first, 0.6993, on 2026-09-27). |
| SC8 | The same photo on `siglip2-p256-crop` | No code step. Neither Belmas wine is in the top 5 (2026-09-27). |
| SC9 | A photo with the QR code of `https://belmaswinery.com/` alone | The barcode step has no hit. The normal match runs, as on the twin with no `barcode`. The trace step `barcode` holds `shared_qr`. |

## Filter `Alternatives`

Owner message of 2026-09-27T00:39:59+0300. `$H` is the lab server.

| # | Case | Expected result |
|---|---|---|
| AF1 | Open `$H/dataset` and press `Advanced Filters:` | The row holds `Package`, `Identifier`, `Type`, and `Alternatives`. `Alternatives` shows `All`. |
| AF2 | Choose `Alternatives: has alternative photos` | Each card has at least one photo under `Alternative photos`. The header reads `<n> of <total> records`. `Advanced Filters:` has the accent. On 2026-09-27: 11 of 2,103 records. |
| AF3 | Reload the page | The select keeps `has alternative photos`, the filter applies, and `Advanced Filters:` has the accent. |
| AF4 | Choose `All` | Each record except the removed ones shows again. The accent goes away. |
| AF5 | Light and dark system theme, width 1280 px and 375 px | The select uses the colours of the theme. No horizontal page scroll. On 2026-09-27 a Playwright check passed 48 of 48 checks. |


## Barcode scan cache and profile workers

Owner request of 2026-09-27T01:01:41+03:00. Use a short run for each check.

| # | Case | Expected result |
|---|---|---|
| BC1 | Open `Run>` and select `barcode-rerank-siglip2-512-crop`. Leave `workers` empty. | The default is 4. A new run records `workers: 4`. |
| BC2 | Set `workers` to 1 or 2 and start a short run. | The explicit count overrides the profile default. |
| BC3 | Run the same photos twice with `Use caches` on. Include a photo with no readable code. | The second run reuses barcode results. Its barcode trace has `cached: true`. Matches remain the same. |
| BC4 | Turn `Use caches` off and repeat a short run. | The barcode scan runs again. The trace has `cached: false`. Fresh results replace cache records. |
| BC5 | Change the wine mapping for a decoded code and start another short run. | The cached code uses the new wine lookup. A stored wine match is never reused. |
| BC6 | Remove a previously unique code mapping or make the code shared. Repeat its photo. | A partial cached scan continues through the remaining tiles when necessary. |
| BC7 | Use four workers on repeated photos. | Each answer has the correct codes. Cache files remain valid JSON. |

## Barcode variant benchmark

Use a completed run with barcode traces. Use a new output directory.
The harness is `scripts/benchmark_barcode_variants.py`.

| # | Case | Expected result |
|---|---|---|
| BV1 | Run `python3 -m unittest discover -s tests -p 'test_barcode_variants.py'`. | All 11 tests pass without real image scans or model calls. |
| BV2 | Supply an unfinished run or a log from another run. | The harness refuses before decoding. |
| BV3 | Run all variants with `--limit 2`. | Nine summaries appear. Warm-cache variants make zero native decoder calls. |
| BV4 | Compare `full`, `whole1`, `whole`, and `tiles3` on a photo with no match. | Maximum native call counts are 70, 1, 2, and 20. |
| BV5 | Compare `photo4` with `full`. | Match selection keeps the original pass order. At most four decoder calls run concurrently. |
| BV6 | Resume an interrupted measurement with `--resume`. | Saved photos are skipped. An incomplete timing segment prevents a false total-throughput claim. |
| BV7 | Change the decoder settings or lookup before a resume. | The manifest rejects the incompatible resume. |

## Label retrieval tower

Profile: `barcode-rerank-siglip2-512-crop-label`.

| # | Case | Expected result |
|---|---|---|
| LT1 | Open `Recognize` or the `Run>` dialog. | The new profile is runnable. The Run dialog defaults to four workers. |
| LT2 | Inspect the profile and the referenced embedding entry. | The `full` steps equal the original crop profile. The `label` steps equal the catalogue label steps. |
| LT3 | Recognize a photo with a visible label and no unique catalogue code. Inspect its trace. | `sam3-label` finds a region. The embedding step has `full` and `label`. Each space has its own `search` step and top-k list. |
| LT4 | Recognize a photo for which SAM3 finds no label. | The label view is skipped. The full view still ranks candidates. |
| LT5 | Recognize a photo with a unique catalogue code. | The barcode answer bypasses both towers. |

On 2026-09-27, both live profile-list APIs reported the new profile as runnable.
Synthetic photos verified LT3 and LT4 with fake SAM3 and embedding models.
No GPU inference was used for these checks.

## Button `↻` of an alternative photo

Owner message of 2026-09-27T00:51:44+0300, answers of 00:56:00. `$H` is the lab server.

| # | Case | Expected result |
|---|---|---|
| RC1 | `python3 -m unittest discover -s tests -p 'test_alternative_recut.py'` | All tests `OK`. |
| RC2 | Open `$H/dataset` and find a wine with alternative photos | Each photo has `↻` in the bottom left corner, and `✎` in the bottom right corner. The tooltip reads `Segment again with SAM3, with no cache read`. |
| RC3 | Press `↻` on the `FF` photo `b6e13a6d…` of `aratti-shardone-beloe-suhoe` | The card is dimmed while the request runs. Then the thumbnail shows the bottle, not the paper behind it (the bottle-first rule of 2026-09-27). The SAM3 record of the photo in `data/cache/sam3/` has a new `created` time. |
| RC4 | Press `↻` on the `LB` photo `d9f847bd…` of `vysokij-bereg-risling-zelenaya-seriya` | The label cut keeps the box 102, 61, 1247, 1553 and the close-up rule (`SETTINGS_LABEL_CLOSE_UP`), not the QR sticker. |
| RC5 | A photo with a manual cut | `↻` is disabled. The tooltip reads `Remove the manual cut first (in the preview)`. |
| RC6 | Stop SAM3, or set a wrong `sam3.endpoint`, and press `↻` | An alert reads `Cannot segment the photo again: SAM3 did not answer; the cut stays: …`. The thumbnail keeps its cut. |
| RC7 | Light and dark system theme | The button uses the colours of `✎`. The hover has the accent colour. |


## Crop, bulk, and sequential recognition experiments

Read `docs/reports/2026-09-27_barcode-benchmark-plan.md` before a real measurement.
Never run these measurements while the saved stage-1 process is active.

| # | Case | Expected result |
|---|---|---|
| EX1 | Run `test_barcode_crops.py`, `test_bulk_cache_benchmark.py`, and `test_recognition_latency.py` through unittest discovery. | Mock tests pass with no model calls. |
| EX2 | Supply an active stage-1 PID, an incomplete variant, or a different baseline. | The next-stage harness refuses before image processing. |
| EX3 | Resume crop scans after an unrelated SAM3 cache write. | Saved geometry remains valid and is not recomputed. |
| EX4 | Edit a saved crop checkpoint or change the code lookup. | The crop harness refuses. |
| EX5 | Run paired complete bulk cold/warm passes after GPU preflight. | Query coverage stays 2228. Warm barcode scans make zero native calls. Model errors and input drift prevent a successful comparison. |
| EX6 | Use process and persistent demo modes with fake backends. | Children keep cache reads disabled. Persistent reuse charges backend construction only on its first request. |
| EX7 | Trigger a worker watchdog or a persistent SAM3 failure. | The harness saves the failure and sends no next photo. |
| EX8 | Read the CLI demo summary. | Its scope excludes HTTP and step-view work. It does not claim a hard 3-second timeout. |
| EX9 | Run `test_recognition_http.py` and the CLI worker tests. | The fake route keeps upload, cache, and response identities separate for every request. No socket or model is needed. |
| EX10 | Simulate an HTTP timeout, then resume. | The timed failed observation stays in the denominator and is not silently replaced by a successful retry. |
| EX11 | Create a persistent worker during exceptional handler shutdown. | Final cleanup closes that late worker before restoring server globals. |
| EX12 | Run fresh crop variants with a fake SAM3 client. | Every required region uses a fresh call. The response charges segmentation. Whole-photo hits skip it. A SAM3 failure blocks fallback inference. |
| EX13 | Run the saved real socket control with fake inference. | Four HTTP responses keep the full route shape, use distinct upload/cache directories, and reconstruct identical input views. Both servers and all fake workers close. |
| EX14 | Run `test_summarize_barcode_bulk.py`, then report completed bulk artifacts to new paths. | Query-ID joins preserve reordered results. Incomplete, mismatched, or nonterminal variants cannot be reported as complete. Timing scopes stay separate. |
| EX15 | Run `test_prepare_rerun_label_inputs.py` and the default dry run. | Only missing active label inputs are selected. External endpoints, stale gates, changed source bytes, and concurrent/manual cuts cannot authorize a write. Every request rechecks the gate. Setup failures close resources. |

All five experiment test modules passed 68 tests on 2026-09-27.
A real HTTP socket control remains required before model measurements.


### EX16. Offline HTTP benchmark report

Run `python3 -B -m unittest discover -s tests -p test_summarize_recognition_http.py`.
The fixture suite has ten tests.
The reporter reads saved HTTP artifacts only.
Check fixed selection denominators, missing sessions, failed and censored requests,
positive and negative labels, and the conflicting-label sensitivity analysis.
Check separate first-request and later-request costs.
Do not infer a warm remote model from request order.
Check upload, step-view, and per-query stage costs.
A partial three-row snapshot of the real pilot produced all eight session entries.
Unmeasured rows remain unmeasured. They are not successes.


### EX17. Internal profile queue dispatcher

Run `python3 -B -m unittest discover -s tests -p test_run_internal_profile_queue.py`.
The fixture suite has 25 tests.
Check external-profile rejection, private endpoints, and a fresh input-bound gate.
Check that an existing attempt suppresses another POST.
Check the live input fingerprint again after durable intent.
Check uncertain launch reconciliation, stale PID commands, and active-job exclusion.
Check saved query/result/prediction coverage, trace failures, and terminal metrics.
Check that source, labels, configuration, index, rules, and lookup changes fail the gate.
Default real inspection MUST leave the production queue hash unchanged.
Do not execute a real profile before all benchmark comparisons finish.


### EX18. Offline internal profile queue report

Run `python3 -B -m unittest discover -s tests -p test_summarize_internal_profile_queue.py`.
The fixture suite has ten tests.
The reporter reads the saved queue and archived attempts only.
Keep all 54 profile rows, including the external profile that lacks authorization.
Keep failed, unavailable, unstarted, and uncertain attempts visible.
Do not display an unverified `done` row as a complete result.
Show signed quality differences for the label profile and its counterpart.
Require both profiles to have validated completion before that comparison.
Output requires a new directory.
The reporter MUST NOT launch a job, inspect a live PID, call a service, or change the queue.

Queue runner regression: a single confirmed `Z` process status is terminated execution.
Matching lifecycle events and complete artifacts are still required.
Malformed or multi-line process output MUST NOT prove termination.
HTTP report regression: missing child timings MUST NOT become zero-duration observations.
The failed HTTP request stays in the selected quality and deadline denominators.

## Height of Alternative photos

Owner message of 2026-09-27T19:30:17+0300. `$H` is the lab server.

| # | Case | Expected result |
|---|---|---|
| AH1 | Open `$H/dataset` in a window wider than 860 px. Find a wine with 9 alternative photos, for example `fanagoriya-primum-alveus-brut-2017-shardone-igristoe-bryut-beloe-12` | `Alternative photos` shows the 3 rows of photos and the row of the drop and paste tiles. The grid has no scroll bar. |
| AH2 | A wine with more than 12 alternative photos | The grid shows 4 full rows of photos (620 px). The other rows are available with a scroll of the grid. |
| AH3 | A window of 860 px or less | The grid has 4 columns and no height limit, as before. |

## Badge of a shared Atlas Core product

Owner message of 2026-09-27T20:08:45+0300. `$H` is the lab server. The badge follows the
rule of plan 58 (section "Shared codes — plan 58"): it counts the Active wines.

| # | Case | Expected result |
|---|---|---|
| AS1 | Open `$H/dataset` and find `balaklava-muskat` | The Atlas Core product `cc7bfa6c-17a7-4c6c-91f2-89c966260704` shows the badge `2 wines` after `open`. The tooltip reads `Also on: balaklava-muskat-beloe-polusladkoe`. A click on the badge does nothing. |
| AS2 | Find `balaklava-muskat-beloe-polusladkoe` | The same badge. The tooltip names `balaklava-muskat`. |
| AS3 | Find `nebbiolo` (an automatic UUID) | The order is `automatic`, `approve`, `copy`, `open`, `2 wines`. |
| AS4 | Find `abrau-dyurso-victor-dravigny-bryut` | Its UUID `28ccaee8-…` has no badge: the other wine of that UUID is Removed. |
| AS5 | Remove the UUID of AS1 on one card | The other card loses its badge with no reload. Add the UUID again: both cards show the badge again. |
| AS6 | Light and dark system theme; a window of 390 px | The badge uses the amber colours of the GTIN badge. It wraps inside the card. On 2026-09-27, 64 Atlas badges show on 30 shared UUIDs. |
