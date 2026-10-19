# Load producer maps on demand

Date: 2026-10-19.
Base: GitHub `main` `b476c855`.
Status: Implemented on 2026-10-19. The owner approved option A, D1 generated committed index, D2 keep the precache.

## Problem

The scanner pages `/` and `/shelf` load the data of all 19 producer maps before the first interaction.
`shared/product-line-map.ts` imports every map JSON file. `WineExperiences.vue` imports this module statically.

Measured on 2026-10-19 with the production build of `b476c855`:

- The first-load JavaScript of `/` is 296 KB gzip in 12 files.
- The map data chunk is 181 KB gzip (1.3 MB raw). It is 61% of the first-load JavaScript.
- One producer map is 4.8 to 22.2 KB gzip (Kuban-Vino is the largest).
- A resolution index (producer names, aliases, slug prefixes, slugs) is 9.4 to 13.2 KB gzip.

The first load grows with each new producer. Most visitors never open a map.

## Constraints

- Keep one JSON file per producer in `shared/data/product-line-maps/`.
- Keep an explicit registry. Nitro does not transform `import.meta.glob` in shared modules.
- Keep the resolution rules: an exact slug or alias first, then the producer name or alias, then the slug prefix.
- The result card MUST show the producer name and the "your wine is on the map" state before the map loads.
- `/lineup/<producer>` MUST keep server-side rendering.
- The MCP server MUST serve the same maps as the Web UI.
- The service worker precaches `_nuxt/**/*.js`. Product images are not precached.
- Accessibility: a loading state MUST be announced to screen readers. Focus rules of the map stay unchanged.

## Options

### A (recommended). Small index in the page, one lazy chunk for each producer

- A generated index file holds, for each producer, the ID, name, aliases, slug prefixes, and the slug of each product and alias. The page imports only this index (about 13 KB gzip).
- The registry exposes `loadProductLine(id)`. It has one explicit `import('./<id>.json')` for each producer. Vite makes one chunk for each producer.
- `resolveProductLine` uses the index. It returns the producer and the product ID without the map data.
- `WineExperiences.vue` loads the map when the user opens «Путеводитель по линейке». It starts the load on pointer enter and focus of that action. The dialog shows an announced loading state until the map is ready.
- `/lineup/<producer>` loads its map with `useAsyncData`. The server renders the map.
- Map validation moves from module load to the tests and the build (`prebuild`). A test checks that the index matches the maps.
- The MCP server reads the producer list from the index file. It no longer parses `index.ts`.

Effect: the first load of `/` drops to about 128 KB gzip. Opening a map downloads 5 to 22 KB gzip.
Cost: medium. It changes the shared module, the registry, `WineExperiences.vue`, the review page, the tests, the MCP loader, and the documents.

### B. Small index in the page, one lazy chunk with all maps

- The same index as A.
- One dynamic import loads all 19 maps when a user opens any map.

Effect: the same first load as A. Opening the first map downloads about 181 KB gzip.
Cost: lower than A. It does not stop the growth for users who open a map.

### C. Static JSON files and `fetch`

- The build copies each map to `public/product-line-maps/<id>.json`. The page fetches the file when the user opens the map.
- The server reads the files from Nitro server assets for `/lineup/<producer>`.

Effect: the same first load as A. Map files get their own HTTP caching.
Cost: highest. It adds a copy step, HTTP cache rules, service worker rules for offline use, and two load paths (server and client).

## Decisions inside option A

- **D1. Index source.** (Recommended) A committed generated file `shared/data/product-line-maps/index.json`, written by `npm run line-maps:index`, with a test that fails when the file is out of date. Alternative: a Vite virtual module that builds the index during the build. It has no committed copy, but it adds a custom build plugin for Vite and Nitro.
- **D2. Offline precache.** (Recommended) Keep the precache of all `_nuxt` chunks. The service worker downloads the map chunks in the background after the first visit, and offline behavior stays unchanged. Alternative: exclude the map chunks. Then offline use shows only the maps that the user opened before.

## Implementation steps

1. Create a branch from GitHub `main`.
2. Add the index generator, `index.json`, and the sync test.
3. Change the registry to `loadProductLine(id)` with explicit dynamic imports. Keep the core module unchanged.
4. Change `resolveProductLine` and `findProducerLine` to use the index. Add `loadProductLine` to `shared/product-line-map.ts`.
5. Change `WineExperiences.vue`: prefetch on pointer enter and focus, load on open, announced loading state, center the map after it renders.
6. Change `/lineup/[producer].vue` to `useAsyncData`.
7. Move map validation to the tests. Keep `prebuild` running the map tests.
8. Change the MCP loader to read `index.json`. Update the MCP tests, README, and CI paths.
9. Add a bundle check script. It fails when a map data chunk is in the first-load closure of `/` or `/shelf`.
10. Update `ChangeLog.md`, `ResearchLog.md`, `SMOKE_TESTS.md`, `CLAUDE.md`, the MCP documents, and `ASSESSMENT.md` F-24 if entry points change.
11. Run the unit tests, the type check, the build, the bundle check, the MCP tests, and the browser suites `test:line-map` and `test:producer-maps`.
12. Codex review. Then push to GitHub `main` when the owner asks.

## Acceptance checks

- The first-load closure of `/` and `/shelf` contains no map data chunk. The index is at most 15 KB gzip.
- For every slug and alias in every map, index resolution gives the same result as full-map resolution. The same holds for every catalog record of the MCP snapshot.
- Opening the map from a single-bottle result and from a shelf result downloads exactly one producer chunk.
- The recognized wine is selected and centered after the map loads, in Chromium and WebKit.
- The loading state is announced. Focus moves and returns as before.
- `/lineup/<producer>` returns server-rendered map content.
- A broken map fails the tests and the build.
- The MCP tests pass with the index registry.

## Implementation notes

- The index is `shared/data/product-line-index.json`, outside the map folder. Each JSON file in `shared/data/product-line-maps/` is then a map. The browser suites and the scripts read that folder.
- TypeScript infers a literal type with every slug key for the index. The module casts the index through `unknown`. The index test checks the content.
- The browser suite `test:line-map` failed on `main` at its shelf step before this change. The mode switch became a link with the mode pages. A separate commit fixes the step.
- Codex review: one P2 finding claimed that Chromium caches a failed chunk import. A local check in Chromium and WebKit showed a new request and a successful retry. The browser suite now covers a blocked chunk and a retry. The retry also returns focus to the dialog heading.
- Results: `/` dropped from 296 KB to 139 KB gzip of first-load JavaScript (same method). The 19 map chunks are 4.7 to 21.6 KB gzip. The index is 13 KB gzip.

## Risks

- Dynamic JSON imports in a shared module may behave differently in the Nitro server build. Step 6 checks the server-rendered review page first.
- Asynchronous loading can break the centering on the first open. The browser suites cover this case.
- The generated index can drift from the maps. The sync test and `prebuild` stop such a build.
