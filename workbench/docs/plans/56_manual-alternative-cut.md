# Plan 56: a manual cut for an alternative photo

Date: 2026-09-26. Session: drink-atlas-workspace-96 [6338a8].
Status: approved by the owner on 2026-09-26T22:51:46+0300. Done, not committed. Live on 8168 since 23:07:24.

Source: owner message of 2026-09-26T22:39:58+0300 and the answers after it. The text is
in [../owner-messages.md](../owner-messages.md). The alternative photos are the subject
of [plan 16](16_alternative-images.md).

## 1. Goal

1. SAM3 cuts each alternative photo automatically: the package cut for a full type
   (`full_front`, `full_back`), the label cut for a label type (`label_front`,
   `label_back`).
2. The owner can draw a polygon on the original photo. The server cuts the photo along
   the polygon. This manual cut replaces the automatic cut.
3. A manual cut stays until the owner resets it. No automatic run replaces it.

## 2. Decisions of the owner

| Question | Options | Answer |
|---|---|---|
| Which tool? | polygon mask; rectangle crop; rectangle and polygon; SAM3 box prompt | polygon mask |
| What does a manual cut cover? | the kind of the current type; both kinds | the kind of the current type |
| Where is the manual cut stored? | `image_derivative` with a marker; a new table and a schema file | `image_derivative` with a marker |
| May this session add hunks to the files of the stale sections f4 and `codex-side-sam3-fix`? | yes, separate hunks; no | yes, separate hunks |

## 3. The design

### 3.1 The row

1. A manual cut is a row of `image_derivative`. The key stays (`source_sha256`, `kind`).
   The kind is `package` for a full type and `label` for a label type
   (`alternatives.CUTS`).
2. `method` is `seg`. The cut has a transparent background, as a SAM3 `seg` cut.
3. `settings` starts with `derive.MANUAL_PREFIX` (`manual `). The full value is
   `manual polygon, edge blur 1.0 px; points [[x,y],...]`. The points are integers in the
   pixels of the original after its EXIF orientation. So the editor can load the
   polygon again.
4. `derive.is_manual(settings)` tells whether a row is a manual cut.
5. No schema change. The `CHECK` of `method` allows `seg`.

### 3.2 The override

1. `derive.derive_all` counts a manual `package` row as present. It does not process the
   original again.
2. `alternatives.has_current_cut` returns True for a manual row of each kind. So
   `process_image`, `store_alternative`, `set_type`, the patch upload, and
   `seed_label_cuts.py` keep the manual cut.
3. `seed_label_cuts.py` counts a manual `label` row as present in its report.
4. A type change to the other kind uses the cut of that kind: its manual cut, else its
   SAM3 cut. A change back reuses the manual cut.
5. A manual `label` cut removes the absence marker of `image_derivative_absence`
   (`write_processed_rows`).
6. The cut belongs to the file, not to the wine. The same file in another wine, or as
   a `main` image, shows the same cut. This is the rule of plan 16.
7. The embedding hash holds the SHA-256 of the processed file. So the next index build
   embeds the new cut. The save does not start a build.

### 3.3 The cut

1. `alternatives.polygon_cut(image, points)` draws the polygon as an `L` mask of the
   size of the original, with a Gaussian blur of `derive.EDGE_BLUR` px for a soft edge.
2. The alpha of an RGBA original limits the mask, as in `label_cut`.
3. The cut is the RGBA original with this alpha, cropped to the box of the alpha. The
   box is `box_left` to `box_bottom`.
4. The PNG keeps the ICC profile of the original (`derive.png_bytes`). The file goes to
   the derived folder of the store.
5. Rules of the points: 3 to `MAX_POINTS` (1000) points. Each point is a pair of finite
   numbers. The server rounds each value and clamps it to the image. The box of the
   points MUST be at least 2 px wide and 2 px high. Another value gives HTTP 400.

### 3.4 The routes

1. `POST /api/dataset-alternative-cut` with the JSON body `{"slug", "sha256", "points"}`
   stores the manual cut of the photo for the kind of its current type. The body limit
   is 64 KiB. The answer is the answer of the other alternative routes: `ok`, `slug`,
   `record`, `alternatives`, `type`, `kind`, `changed`.
2. `DELETE /api/dataset-alternative-cut?slug=<slug>&sha256=<sha256>` removes the manual
   cut of the kind of the current type. Then SAM3 processes the photo again. A cached
   SAM3 answer is used (plan 25). SAM3 does not answer: the photo has no cut, and the
   answer holds a warning. A photo with no manual cut gives `changed: false`.
3. HTTP 404: no wine, or no such alternative photo. HTTP 409: the type changed during
   the request.
4. `alternative_images` gives two more keys for each photo: `manual` (true or false)
   and `manual_points` (the points, or null).

### 3.5 The page

1. The image preview of an alternative photo on the lab server shows the button
   `Manual cut` in its head. A photo with a manual cut also shows `Remove manual cut`.
   This button removes the manual cut and runs the automatic segmentation again (owner
   message of 2026-09-26T22:57:59+0300).
2. `Manual cut` opens the editor. The preview shows the original. An SVG layer over
   the image shows the polygon. A manual cut loads its points.
3. A click adds a point at the end. A drag moves a point. A right-click on a point
   removes it. `Undo` (or Backspace) removes the last point. `Clear` removes all points.
   `Cancel` (or Escape) closes the editor with no change. `Save` needs 3 points.
4. In the editor, the arrows and the thumbnails are hidden. The arrow keys do nothing.
5. After `Save` or `Remove manual cut`, the preview shows the new processed file, and the card
   shows it too.
6. The badge of a manual cut is `manual`, on the card and on the thumbnail of the
   preview.
7. The layer uses fixed colours over the photo. The buttons and the bar use the theme
   colours, so the light and the dark theme both work.

## 4. Files

- `pipeline/derive.py`: `MANUAL_PREFIX`, `is_manual`, one line in `derive_all`.
- `pipeline/alternatives.py`: `has_current_cut`, `MANUAL_HEAD`, `MAX_POINTS`,
  `manual_points`, `polygon_cut`, `store_manual_cut`, `reset_manual_cut`, the docstring.
- `pipeline/seed_label_cuts.py`: the query of present label cuts.
- `pipeline/lab_server.py`: the docstring, `alternative_images`, `set_manual_cut`,
  `reset_manual_cut`, the route.
- `pipeline/pages/dataset.html`: the editor, the buttons, the badge.
- Tests: `tests/test_alternatives.py`, `tests/test_lab_server.py`,
  `tests/test_seed_label_cuts.py`.
- Docs: `docs/API.md`, `README.md`, `SMOKE_TESTS.md`, `ChangeLog.md`.

## 5. Risks

1. A browser that does not apply the EXIF orientation gives points in other pixels. The
   present Chrome, Safari, and Firefox apply it by default.
2. A manual cut is not re-made when the SAM3 settings change. This is the intent.
3. The `settings` value of a manual cut is long (up to about 12 KB). SQLite has no
   limit that this reaches.
