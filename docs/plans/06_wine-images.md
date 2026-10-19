# Static wine images on chtozavino.ru

Date: 2026-10-19.
Branch: `feature/wine-images`.
Base: `4360ce40` (`main`).
Status: Draft. The open questions at the end MUST have owner answers before implementation.

## Goal

Serve one image of each catalogue wine from chtozavino.ru as a static file. Every component
that knows a wine slug can build the image address without a request to another service.
The published files MUST agree with the catalogue database. A deploy MUST check this.

## Owner decisions (2026-10-19)

- D1. The address of a wine image is built from the slug (option 1 of the discussion).
- D2. The image of a wine is its `main_patched` image. A wine with no `main_patched` image
  uses its `main` image.
- D3. Two sizes: a long side of at most 1600 px, and a long side of at most 400 px.
- D4. The check runs at each deploy of images and at each deploy of the matcher catalogue.
  A failed check stops the deploy.
- D5. An Active wine with no image gets a placeholder image at its address.
- D6. The scope includes the wine images in the Dinner Lens result cards.
- D7. Claude draws the placeholder: a neutral grey bottle silhouette on a transparent
  background. The owner reviews it.
- D8. The images use `max-age` of 1 hour.

## Current state

- The matcher builds `image_url` from the `source_name` of the `main` image:
  `https://api.vino-svoe.ru/v1/img/str-api/1920/1920/resize/uploads/<source_name>`
  (`matcher/catalog.py`). The bundle builder uses the same rule
  (`workbench/pipeline/matcher_bundle.py`). The matcher ignores `main_patched` for the card.
- The Telegram bot and the MAX bot download `image_url` with `CatalogImageLoader`
  (`im-core/src/chto_za_vino_core/result_card.py`). The loader accepts only HTTPS and only
  the host `api.vino-svoe.ru`. When the download fails, the bot sends the photo of the user.
- The portal shelf (`webui/shared/shelf.ts`) shows `image_url` of the matcher card.
- The portal route `/api/wines/[slug]` (`webui/server/utils/wine-metadata.ts`) reads
  `https://api.vino-svoe.ru/v1/wines/<slug>` at each request. It returns a 640 px image of
  the source site. `PhotoScanner.vue` shows it.
- Dinner Lens returns `wine_slug` and `source_url`. It returns no image. Its dataset
  `pairing-dataset.v4.json` holds 2,093 wine slugs. All of them are Active in the lab
  database.
- The lab database (`svoe-vino-lab-submission/workbench/data/catalog/catalog.sqlite3`,
  schema 32) holds 2,198 Active wines: 24 with `main_patched`, 2,193 with `main`, 5 with no
  image. The originals use 172 MB. The largest original has 60.2 MP. Formats: WebP 2,202,
  PNG 16, JPEG 8. All Active slugs match `^[a-z0-9_-]+$`; the longest has 139 characters.
- The 5 Active wines with no image come from the official CSV delivery
  (`svoe-wino-hackaton/dataset/official-2026-09-17/strapi_output0709.csv`). The delivery does
  not hold the photo files that the CSV names. The wines are not on vino-svoe.ru
  (`/v1/wines/<slug>` answered HTTP 404 on 2026-10-19). They have no vectors, no codes, and no
  Dinner Lens entry. The matcher therefore cannot answer them. The slugs:
  `vibes-silvaner-barrel-fermented-2022`, `polusladkoe-krasnoe-zb-vajn-frizzante`,
  `polusladkoe-krasnoe-zolotaya-balka`, `polusuhoe-rozovoe-zb-vajn-frizzante`,
  `suhoe-beloe-zb-vajn-frizzante`. Issue #69 finds images for them.
- The `main` image of `vibes-vermentino-viognier-barrel-fermented-2022` (from vino-svoe.ru)
  shows the label «Silvaner 2022 Barrel Fermented». It is the missing image of
  `vibes-silvaner-barrel-fermented-2022`. Issue #69 also covers this error.
- The table `wine_image` has no time column and no trigger. A changed patch does not change
  a date in the database. A date is therefore not a reliable sync check.
- `copy_catalog.py --no-images` makes the prod catalogue copy for gx10. The copy holds the
  rows of `wine_image` and the view `matcher_wine_image`, but no image files.
- Claudette runs Caddy for chtozavino.ru. The game site uses a release directory and a
  `current` symlink (`chtozavino-deploy/claudette/wine-game.md`).

## Public addresses

| Address | Content | `Cache-Control` |
|---|---|---|
| `https://chtozavino.ru/img/wines/1600/<slug>.webp` | Image, long side ≤ 1600 px | `public, max-age=3600` |
| `https://chtozavino.ru/img/wines/400/<slug>.webp` | Image, long side ≤ 400 px | `public, max-age=3600` |
| `https://chtozavino.ru/img/wines/manifest.json` | Manifest | `no-cache` |

- Caddy serves these paths as static files. Caddy MUST NOT send them to the portal.
- An address of a slug that is not Active returns HTTP 404.
- A changed image keeps its address. A client sees the new image after `max-age`.

## Selection rule

For each Active wine of the view `matcher_wine`:

1. Use the row of `matcher_wine_image` with `image_type` `main_patched` or `main`. The view
   already replaces `main` with `main_patched`.
2. If the wine has no such row, use the placeholder.

The rule reads only the fixed views. No schema change is necessary.

## Image derivatives

- Open the original with Pillow. Reject an original above 100,000,000 pixels
  (the limit of `patches.py`).
- Apply the EXIF orientation. Remove all metadata.
- Keep the alpha channel when the original has one.
- Reduce the image so that the long side is at most the size. Do not enlarge a smaller image.
- Write WebP with the Pillow default quality.

## Placeholder

- One source file in the repository: `workbench/assets/wine-image-placeholder.svg` (D7, Q4).
- The publish step makes the two sizes of it. It writes them at the addresses of each Active
  wine with no image.
- The placeholder MUST look correct on a light and on a dark background, because it is a raster
  image in both themes.

## Manifest

```json
{
  "format": "svoe-vino-wine-images",
  "version": 1,
  "created_at": "2026-10-19T12:00:00Z",
  "catalog": {"sha256": "<sha256 of catalog.sqlite3>", "schema": 32, "active_wines": 2198},
  "sizes": [1600, 400],
  "placeholder_sha256": "<sha256 of the placeholder source>",
  "wines": {
    "<slug>": {
      "source": "main | main_patched | placeholder",
      "source_sha256": "<sha256 of the original, or null for the placeholder>",
      "files": {
        "1600": {"sha256": "...", "width": 0, "height": 0, "bytes": 0},
        "400": {"sha256": "...", "width": 0, "height": 0, "bytes": 0}
      }
    }
  }
}
```

- `catalog.sha256` is for information. A catalogue copy can have other bytes than the lab
  database. The check uses the fields of each wine.

## Scripts

### `workbench/scripts/build_wine_images.py`

`build_wine_images.py --db <catalog.sqlite3> --out <new directory>`

- It reads the views and the image store of the database (`images/<folder>/<sha256>.<ext>`).
- It writes `1600/`, `400/`, `manifest.json`, and `SHA256SUMS` into a new directory.
- It fails when an original file is missing or when its SHA-256 differs from the database.

### `workbench/scripts/check_wine_images.py`

The check compares a manifest with a catalogue database. It returns a non-zero exit code and
a list of the differences.

- `--db <catalog.sqlite3> --release <directory>`: the full local check.
  - The manifest holds exactly the Active slugs of the database.
  - `source` and `source_sha256` of each wine agree with the selection rule.
  - Each file exists, and its SHA-256 and size agree with the manifest.
  - The directory holds no other file.
- `--db <catalog.sqlite3> --url https://chtozavino.ru/img/wines/ [--sample N]`: the public check.
  - It downloads `manifest.json` and applies the manifest rules above.
  - It downloads all placeholder files and `N` random files (default 50). It checks their
    SHA-256.
  - With `--catalog-update`, a manifest slug that is not Active in the database is a warning,
    not an error. Read "Deploy order".

## Deploy on Claudette

- Release: `/srv/svoe-vino-lab/prod/wine-images/releases/<UTC time>/`.
- Active release: `/srv/svoe-vino-lab/prod/wine-images/current`, a relative symlink.
- Keep the last three releases. A rollback changes the symlink.
- Caddy: a `handle /img/wines/*` block in the site `chtozavino.ru`, before the portal
  `handle`. It strips the prefix, uses `root` = `current`, and runs `file_server`.

Procedure:

1. Build the release on the Mac from the lab database. Run the full local check.
2. Send the release with `rsync` into a new release directory.
3. On Claudette, run `sha256sum -c SHA256SUMS` in the release directory.
4. Change the symlink `current`.
5. Run the public check.
6. Record the release in `chtozavino-deploy` (a new file `claudette/wine-images.md`).

A prod deploy MUST have the approval of the owner (rule 1 of `chtozavino-deploy`).

## Deploy order

- Images first, then the consumers. The order of the consumers: the web UI, then the bots
  (the new allowed host), then the matcher (the new `image_url`). A bot with the old allowed
  host rejects the new address and sends the photo of the user.
- A catalogue update for the matcher on gx10: publish the image release from the same database
  first. Then run the public check with `--catalog-update` against the new catalogue copy.
  A failed check stops the catalogue deploy.
- Between the image release and the catalogue update, the old catalogue can answer a wine that
  the new catalogue made non-Active. Its address returns HTTP 404. The bot then sends the photo
  of the user. This window is accepted.

## Consumer changes

1. `matcher/catalog.py`: `image_url` = `https://chtozavino.ru/img/wines/1600/<slug>.webp`
   for a wine with an image. For a wine with no image, see Q1. Read the selection from
   `matcher_wine_image`, not from `main_source_name`.
2. `workbench/pipeline/matcher_bundle.py`: the same rule for the bundle cards.
3. `im-core/src/chto_za_vino_core/result_card.py`: the default `allowed_host` becomes
   `chtozavino.ru`. The Telegram bot and the MAX bot use the default.
4. `webui/server/utils/wine-metadata.ts`: `image` = `/img/wines/1600/<slug>.webp`. The route
   keeps the other fields of the source site. A missing source image no longer rejects a wine.
5. `webui/app/components/DinnerScanner.vue`: each result card shows
   `/img/wines/400/<slug>.webp`.
   - `alt=""`, because the wine name is in the card heading next to the image.
   - Fixed `width` and `height`, `loading="lazy"`, `decoding="async"`.
   - A light image tile in both themes, because the originals have light backgrounds.
   - VoiceOver and TalkBack MUST read the card as before (issue #35).

Out of scope: the 12 demo wines of `/ideas` (`webui/server/data/wines.json`, local files
`/wines/<slug>.webp`) and the producer line maps (`/product-line-maps/...`).

## Tests

- `build_wine_images.py`: selection rule, `main_patched` over `main`, placeholder, size
  limits, no enlargement, alpha, EXIF orientation, missing original, wrong SHA-256.
- `check_wine_images.py`: each difference type, `--catalog-update` warnings, extra files.
- Matcher: card `image_url` for `main`, `main_patched`, and no image.
- im-core: the loader accepts `chtozavino.ru` and rejects `api.vino-svoe.ru`.
- Web UI: `/api/wines/[slug]` image address; Dinner Lens card image in light and dark themes;
  an accessibility check of the card.
- `SMOKE_TESTS.md`: create it with the image smoke tests (the repository has no such file).

## Documentation

`ChangeLog.md`, `ARCHITECTURE.md`, `chtozavino-deploy` (`claudette/wine-images.md`, Caddyfile,
the catalogue update procedure), `infra/services/svoe-vino-webui` and
`infra/services/svoe-vino-matcher`.

## Open questions

- Q1. A wine with no image: the matcher card gets `image_url` = `null` (the bot then sends the
  photo of the user, as now), or the placeholder address? Recommendation: `null`. The static
  address still gives the placeholder to the components that build the address from the slug.
- Q4. The web UI MUST show a placeholder when an image does not load (`<img>` `error` event).
  This covers HTTP 404, network errors, and the deploy window. The web UI already does this for
  food images (`FoodRecommendations.vue`) and line map images (`ProductLineMap.vue`). Keep the
  placeholder files on the server (D5), or remove them and let each client show its own
  placeholder? Today no consumer can get one of the 5 wines with no image (see "Current
  state").
