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
| R53 | Open run `2026-09-23T084340Z-svm-label-gw-difference-hardcase-guard` and find the photo `abrau-dyurso-abrau-dyurso-pino-nuar-krasnoe-suhoe-13/01_conf095.jpg` | One frame in the accent colour holds the candidates #1, #2, and #3. Its tooltip reads `cluster c013 · mixed · 4 cards`. Candidate #6 `abrau-dyurso-kaberne-sovinon-krasnoe-suhoe-125` is in the same cluster but gets no frame, because #4 and #5 stand between. |
| R54 | Look at a row where one cluster card stands alone between cards of other clusters | That card gets no frame. |
| R55 | Rename `dataset/catalog-clusters.json`, then reload `/runs` | The page shows no cluster frame. Everything else works. |

## The catalogue clusters — `scripts/10_clusters.py` and `/clusters`

Read `docs/plans/04_catalog-clusters.md` for the rules.

| # | Case | Expected result |
|---|---|---|
| C1 | Run `python3 scripts/10_clusters.py` | The log states the two indexes with their card counts and build times, one line for each run with `used` and `stale`, the link counts, the cluster count, the sizes, and the output path. The script calls no service and ends in a few seconds. |
| C2 | Run `python3 scripts/10_clusters.py --show abrau-dyurso-pino-nuar-krasnoe-suhoe-12` | The card stands in one cluster with `abrau-dyurso-pino-nuar-krasnoe-suhoe-125` and `abrau-dyurso-abrau-dyurso-pino-nuar-krasnoe-suhoe-13`. The three pairs of these cards carry `name`. |
| C3 | Run it with `--min-confusions 1 --out <a scratch file>` | The largest cluster holds more than 30 cards. The default of 2 prevents this chaining. |
| C4 | Run it with `--no-confusion --no-label --out <a scratch file>` | The file holds no `label` link and no `confusion` link. `settings.signals` names `name` and `photo` alone. |
| C5 | Run it with `--photo-index /nope.npz` | The script stops with `the index file is not on disk`. It writes no file. |
| C6 | Run it with `--show vina-arpachina-arpachino-inohodets-aligote-beloe-ekstra-bryut-125` | The card is in no cluster. The cards of the line «Иноходец» share one name and hold different grapes, so the `name` signal does not join them. |
| C7 | Open `$H/clusters` | The header states the cluster count and the build time. The navigation marks `Clusters`. The count line states `255 of 255 clusters` for the build of 2026-09-22. |
| C8 | Open `$H/clusters#abrau-dyurso-pino-nuar-krasnoe-suhoe-12` | The page scrolls to the cluster of that card. The cluster and the card carry an outline. |
| C9 | Set `Kind` to `same wine` | Only the clusters with the tag `same wine` are listed. The count equals `counts.kinds.same-wine` of the file. |
| C10 | Set `Image` to `label` | Every card shows its label crop. A card with no crop shows its package and the mark `no label`. |
| C11 | Look at a link row of a cluster | The value of every signal that passed is bold. The column `name` states `same`, `grapes differ`, or a dash. |
| C12 | Click a thumbnail under `confused photos` | The large view of this page opens that photo. Its caption names the card of the photo, the card that the run answered, and the run. Its link `review` opens the photo in the review page, in a new tab. |
| C13 | Click `review` under a card | The review page opens that wine. |
| C14 | Move the cluster file away, then reload `/clusters` | The page states that no cluster file exists and names the command. `GET /api/clusters` answers `exists: false`. |
| C15 | Build the file again while the tool runs, then reload `/clusters` | The new build time shows. No restart is needed. |
| C16 | Open `/clusters` in the dark system theme and in the light system theme | Both themes are readable. A label crop stands on white in the dark theme. |
| C17 | Open `/clusters` at a width of 375 px | The page has no horizontal scroll. A link table scrolls inside its own box. |
| C18 | `curl -s $H/api/clusters` | `exists: true`, `clusters`, `counts`, `inputs`, `settings`, `rules`, and one record in `cards` for each card of a cluster. The route writes nothing. |
| C19 | Click the bottle of a card | The large view opens that picture on white. The caption names the card and states `image <i> of <n> · <cluster id> · cluster <k> of <m>`. The picture in the page carries an outline. |
| C20 | Press `Right` until the last image of the cluster, then press `Right` again | The view moves over the cards first, then over the confused photos. The last image holds, and the button `›` is dimmed. |
| C21 | Press `Left` at the first image | The first image holds, and the button `‹` is dimmed. |
| C22 | Press `Down` at the fifth image | The view opens the fifth image of the next cluster. The page scrolls to that cluster. |
| C23 | Press `Down` at an image whose place is after the end of the next cluster | The view opens the last image of the next cluster. |
| C24 | Press `Up` in the first cluster, and `Down` in the last cluster | The view holds. The button of that direction is dimmed. |
| C25 | Click the buttons `‹`, `›`, `↑`, and `↓` | They move as the four keys move. |
| C26 | Press `Esc`, then open the view again and click the dark ground | The view closes both times. The last image keeps its outline in the page. A click on the picture itself does not close the view. |
| C27 | Change a filter while the view is open | The view closes, because the blocks are drawn again. |
| C28 | `Cmd`-click a bottle | The picture opens in a new tab, and the large view does not open. |
| C29 | Step fast with `Right` over the confused photos | The caption never stands under the picture of the step before. The old picture is hidden until the new one is loaded. |

## The label rules of the clusters — `scripts/11_cluster_rules.py` and `/clusters`

Read `docs/plans/05_cluster-label-rules.md` for the rules. The cases L3, L9 and L10
call the VLM on gx10 and wait for its single slot.

| # | Case | Expected result |
|---|---|---|
| L1 | Run `python3 scripts/11_cluster_rules.py --dry-run` | The log states the clusters, the cards, the notes, `stage 1: qwen3.5-9b, thinking False   stage 2: qwen3.8-max, thinking True, 4 requests at a time`, and the counts of the descriptions and the rules that are not current. No VLM call is made. |
| L1a | Run `python3 scripts/11_cluster_rules.py --stage rules --cluster <slug>` in a shell without `QWENCLOUD_TOKEN_PLAN_API_KEY` | The rule records the error `the environment variable QWENCLOUD_TOKEN_PLAN_API_KEY is not set`, and the page states `failed`. |
| L2 | Run `python3 scripts/11_cluster_rules.py --cluster no-such-slug` | The script stops with `in no cluster: no-such-slug`. |
| L3 | Run it with `--cluster vinodelnya-vedernikov-fantom-3070-krasnostop-zolotovskiy-krasnoe-suhoe-145` twice | The first run describes the cards that are not current and builds one rule. The second run makes no VLM call: every description and the rule are current. |
| L4 | `curl -s $H/api/clusters` and find the cluster of `vinodelnya-vedernikov-fantom-3070-krasnostop-zolotovskiy-krasnoe-suhoe-145` | The cluster holds `key`, `notes`, `rule`, and `rule_status`. The rule holds a valid question with the answers `30/70`, `50/50`, and `70/30`. Each card record holds `description`. The top field `rules` names the two files and the model. |
| L5 | Open `$H/clusters#vinodelnya-vedernikov-fantom-3070-krasnostop-zolotovskiy-krasnoe-suhoe-145` | The block `Label rule` shows the mode `difference sheet`, the status `current`, the text of the differences, the sheet with one column for each card, and the rule text. A question about the alcohol value is struck; its tooltip gives the reason. |
| L6 | Click `label description` under a card | The description opens: the texts with their place, the numbers, the vintage, the colours, the design, the marks, and the bottle. A list reads as a comma list, not as JSON. |
| L7 | Type a note, click `Save note` | The status line reads `saved <time>`. `dataset/catalog-cluster-notes.json` holds the note with the slugs of the cluster. The status of the rule becomes `stale`. |
| L8 | Clear the text, click `Save note` | The note is gone from the file. The status of the rule is `current` again when no other input changed. |
| L9 | Click `Rebuild rule` | The line reads `building the rule… (5 to 30 s)` and both buttons are dimmed. The block is drawn again with a new build time and the status `current`. An unsaved note is saved first. |
| L10 | Click `Rebuild rule` in a second tab while the first build runs | The second tab reads `failed: another rule is being built; try again soon`. |
| L11 | `curl -s -X POST $H/api/cluster-note -d '{"slugs":["abrau-dyurso-pino-nuar-krasnoe-suhoe-12"],"text":"x"}'` | `400` `these slugs are not the slugs of one cluster`. |
| L12 | Set `Rule` to `with a note` | Only the clusters with a note are listed. `stale` lists the clusters whose inputs changed after the build. |
| L13 | Open `/clusters` in the dark system theme and in the light system theme | The block `Label rule`, the sheet, and the note editor are readable in both themes. |
| L15 | Open `$H/clusters#fanagoriya-primum-alveus-brut-2014-shardone-igristoe-bryut-beloe-12` and open `the cards of the letters` | The badges read `#1 · A` to `#9 · I`, the head of the sheet names the same letters, and the list names the card name and the slug of each letter: `B = #2 Primum Alveus Brut 2014 fanagoriya-primum-alveus-brut-2014-shardone-igristoe-bryut-beloe-12`. |
| L14 | Run `python3 scripts/cluster_rules_report.py runs/<a run of svm-label-gw-cluster-rules>` | The report states the metrics against the base run, the wins and the losses with the exact McNemar test, the table by mode, the replay without the `confusion` signal, the «Фантом» photos, the table of the score gaps, and the latency. It writes `cluster-rules-report.md` and `.json` into the run directory. |

The label-only rules of `docs/plans/06_label-only-cluster-rules.md`. The cases L16 to
L18 call no model. Run them from `scripts/` in `python3`, after
`import cluster_rules as cr; catalog = cr.load_catalog()`.

| # | Case | Expected result |
|---|---|---|
| L16 | `cr.check_rule({"questions": [{"question": "What colour does the wine show through the glass?", "answers": {"A": "red", "B": "rose"}}], "rule": "Clear glass is card B."}, {"A": "x-a", "B": "x-b"}, catalog)` | The question has `kind` `bottle` and `valid` false. The mode is `none`, not `verdict`, because the rule text names the glass. |
| L17 | `cr.check_rule({"questions": [{"question": "What vintage year is printed?", "answers": {"A": "2024", "B": "2025"}}]}, {"A": "aligote-barrel-2024", "B": "aligote-barrel-2025"}, catalog)`, then the same with the slugs `abrau-dyurso-pino-nuar-krasnoe-suhoe-12` and `abrau-dyurso-pino-nuar-krasnoe-suhoe-125` | The first question has `kind` `vintage`, keeps `2024` and `2025`, and is valid: the slugs state the years. The second question holds null for both cards and is not valid. |
| L18 | Build the stage 2 content of the cluster of `b-yu-rne-krasnostop-suhoe-krasnoe-classic` with `cr.rules_content` | Each picture is the label crop of `bottle_label_dir`. The captions of card E («ПИНО БЛАН») and card J («ВИОНЬЕ») read `the same catalogue picture as card J` and `... as card E`. The prompt text holds no key `"bottle"`. |
| L19 | Run `python3 scripts/11_cluster_rules.py --stage rules --cluster b-yu-rne-krasnostop-suhoe-krasnoe-classic --force` in a shell that holds `QWENCLOUD_TOKEN_PLAN_API_KEY`, and read the rule | No valid question names the glass, the liquid, the capsule, the cork, or the shape of the bottle. The grape answers are written as the label prints them: `КРАСНОСТОП`, `ШАРДОНЕ`, `МЕРЛО`. A vintage question, if the model asks one, is not valid. |
| L20 | Start the review tool again, open `$H/clusters`, and hover a struck question of kind `bottle` or `vintage` | The tooltip reads `not used: a feature outside the label: …` or `not used: the names of two cards do not state two different years`. |
| L21 | Copy the run `2026-09-23T224548Z-svm-label-gw-cluster-rules-qwen38max-rules-v2` to a scratch directory and run `python3 scripts/cluster_rules_report.py <copy> --rules work/catalog-cluster-rules.2026-09-24T082150.json` | Every number equals the report of the run. The new section `The two halves of the wines` reads: half A, 775 positives, R@1 0.8103 → 0.8284, 23 wins, 9 losses; half B, 825 positives, R@1 0.8206 → 0.8339, 24 wins, 13 losses. |
| L22 | For the cluster of `abrau-dyurso-pino-nuar-krasnoe-suhoe-12` (c013), take `letters` of the sorted slugs, and call `cr.check_rule` with a vintage question `{"A": "other", "B": "2023", "C": "2023", "D": "2024"}` and a grape question `{"A": "Пино Нуар", "B": "Каберне Совиньон", "C": "Пино Нуар", "D": "Пино Нуар"}`, with `catalog` and `cr.load_rules()["cards"]` | The vintage question keeps `other` for A and the label years 2023, 2023, and 2024, and it is valid. `cr.vintage_note(letters, catalog, cards)` names B, C, and D with their years `on the label`, and A as the card with no year. |
| L23 | The same call with the grape `Мерло` for card A | The vintage question holds null for every card and is not valid: the grape separates A from every card with a year, so A is not a vintage variant. |
