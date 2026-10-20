# Performance audit

Evidence: [E01 HTTP](evidence/http-pages.json), [E02 resources](evidence/resources.json), [E03 probes](evidence/supplementary-probes.json), [E04 browser](evidence/browser.json). Values refer to the observed production build, not an assumed local build. Bytes are decimal; KiB divides by 1024.

Follow-up laboratory evidence: [15 original Claude Lighthouse reports validated against his summary](evidence/claude-lighthouse-validated.json). Their results, warnings and interpretation are in [the parallel review](claude-review.md#lighthouse-accept-as-laboratory-evidence). No independent Lighthouse rerun was performed.

## What was measured

curl GETs used `--compressed`; asset sampling used up to four concurrent requests. `decoded_bytes` is decompressed body size and `metrics.size_download` transferred body size. These exclude request overhead, JavaScript execution, the complete browser waterfall and service-worker installation. Preload references are not proof of execution or unused code.

| Sample | Measurement | Meaning |
|---|---|---|
| Home HTML | 19,901 decoded bytes; crawl TTFB 98ms | Real SSR; not LCP |
| Shelf HTML | 20,407 decoded bytes; TTFB 90ms | Image opportunity dominates obvious cold-load bytes |
| Dish HTML | 35,550 decoded bytes; TTFB 85ms | SSR picker present |
| Directory HTML | 46,097 decoded bytes; TTFB 68ms | Real producer links/state |
| Fanagoria guide HTML | 351,674 decoded bytes | Large SSR guide/state; noindex. Browser sample had 182 image elements, no observed loaded broken images. |
| Five further sequential home GETs | TTFB 193,118,93,65,59ms; median **93ms** | One vantage, not an SLA, Russian-mobile percentile or CWV |

No controlled cold-cache/geographic test or CDN hit/miss measurement was obtained. TTFB includes applicable connection/TLS work; a static screenshot cannot measure paint/interaction/shift metrics.

## Core Web Vitals — SEO-017

| Metric | Result | Required next evidence |
|---|---|---|
| LCP | Field unavailable; supplied simulated mobile lab: home 3.765–4.827 s, shelf 15.018–15.918 s | Field p75 by device; compare age-gate and returning states under controlled conditions |
| INP | **Unavailable** | Field interactions; upload/picker/map/dialog long-task traces; TBT is not INP |
| CLS | Field unavailable; supplied lab range 0–0.027 | Field p75 and shift trace including font swaps/dynamic results |
| Lighthouse performance/SEO scores | Supplied original reports validated; home mobile performance 41/55, shelf 42/42 | Interpret as laboratory results, not index coverage or field compliance |

Both mobile/desktop PageSpeed API attempts returned **429 RESOURCE_EXHAUSTED** (E02 `extra`). No authenticated CrUX/Search Console/RUM data was available. Claude's subsequently located raw LHRs establish laboratory scores and `.site-shell`/background as the measured first-visit LCP candidate. All 15 summary LCP/CLS/performance scores match their original reports. They do not establish field CWV pass/fail. Two reports warn about slow CPU; simulated mobile uses a 4× CPU multiplier and a 412×823 viewport with the age gate open. Treat absolute simulated LCP as well as TBT with that limitation.

The background preload audit reports zero estimated savings despite flagging discovery/priority. A measured before/after experiment is needed before promising a particular gain or applying a global high-priority preload. The review also confirms directory cover oversizing (976,413 estimated wasted bytes) and missing explicit TTLs on sampled image folders; see [additional findings](claude-review.md#additional-findings-and-verdicts).

Future field targets: p75 LCP ≤2.5s, INP ≤200ms, CLS ≤0.1, separated by device. These are targets from [Google Web Vitals](https://web.dev/articles/vitals), not project measurements. **SEO-017: REQUIRES VERIFICATION, P2/M.** Inspect existing analytics before adding instrumentation. A proposed `webui/app/plugins/web-vitals.client.ts` is only needed if existing supported tooling cannot supply it; review privacy and dependencies first. Never send images, diary/account data or arbitrary user-input URLs as telemetry.

**Acceptance:** dated baseline, sample counts/device/network/cache conditions and actual trace artifacts. If field traffic is insufficient, state that and use lab results for engineering without claiming field compliance.

## SEO-002 — Shared logo is an oversized embedded bitmap

**VERIFIED optimization, P1/S; CWV impact LIKELY, unmeasured.** `https://chtozavino.ru/icons/product-logo.svg`: **171,311 decoded / 155,135 gzip transferred bytes** in E02. The 640×640 SVG contains one embedded raster URI with 171,028 base64 characters. The shared brand displays it at 44×44, bot example at 32×32.

Root: `webui/app/components/ProductBrand.vue:3`; `webui/public/icons/product-logo.svg`; favicon reference `webui/nuxt.config.ts:64` and PWA asset line 106. GET has ETag/Last-Modified but no explicit Cache-Control. This does not mean zero caching: heuristics/validation and PWA precaching can apply.

**Fix:** approved small 44/88px derivative or compact vector, content-versioned filename, version-safe bounded caching, and updated brand/favicon/PWA references. Minifying an SVG will not eliminate an embedded PNG's bytes. **Side effects:** sharpness/transparency, favicon and worker updates. **Verify:** light/dark 1×/2× visual comparison, GET bytes/headers and install/update cache checks. Proposed project display-logo budget ≤10KiB, not a search-engine rule.

## SEO-003 — Shelf thumbnails reference original recognition photographs

**VERIFIED resource/markup optimization, P1/S–M; cold-waterfall impact LIKELY.** Page: `https://chtozavino.ru/shelf`.

| Image | HEAD Content-Length |
|---|---:|
| `/reference/shelf-example-abrau-close.webp` | 678,658 |
| `/reference/shelf-example-abrau-wide.webp` | 898,762 |
| `/reference/shelf-example-sparkling-display.webp` | 736,018 |
| Unique total | **2,313,438** |

E01 markup renders a selected original plus three thumbnails with the original URLs, no lazy attribute or srcset. The selected URL is reused, not counted twice. Claude's raw Lighthouse runs subsequently corroborated approximately 2.98 MB total page transfer and 2,278,294 estimated wasted image bytes. Before/after savings remain to be measured; this is not a field LCP result.

Root: `webui/app/components/ShelfScanner.vue:69–72` uses `shelfExample.src`/`item.src`; `webui/shared/shelf.ts:7–33` has one source field. `webui/app/composables/useShelfScanner.ts:91–99` fetches that same source for recognition.

**Fix:** separate original recognition source, responsive display derivatives and thumbnails. Use display srcset/sizes and explicit thumbnail dimensions. Defer nonessential imagery, keeping a visible hero eager if the measured LCP calls for it.

```ts
// Proposed shape; keep recognition input separate from display quality.
{ recognitionSrc: '/reference/shelf-example-abrau-close.webp',
  display640: '/reference/shelf-example-abrau-close-640.webp',
  display1280: '/reference/shelf-example-abrau-close-1280.webp',
  thumbnail: '/reference/shelf-example-abrau-close-thumb.webp' }
```

**Side effects:** tiny derivatives must not feed recognition; preserve framing/aspect ratios and example switching. **Verify:** cold actual 390px/desktop trace selects suitable derivatives and small thumbnails; staging example action subsequently fetches original. Initial proposed budget ≤200KiB display + ≤15KiB per thumbnail, subject to visual QA.

## SEO-004 — Initial scanner JS contains result-only features

**VERIFIED preload payload; LIKELY optimization, P2/M.** E02 `asset_relations` ties assets to initial HTML references.

| Route | JS module-preload count | Decoded JS | Transferred JS | CSS count / decoded / transferred |
|---|---:|---:|---:|---|
| `/` | 14 | 579,043 | 176,380 | 5 / 92,300 / 20,890 |
| `/shelf` | 14 | 579,436 | 176,570 | 5 / 92,300 / 20,890 |
| `/dish` | 15 | 646,474 | 197,142 | 5 / 92,300 / 20,890 |
| `/lineup` | 9 | 376,433 | 110,097 | 2 / 67,875 / 15,165 |

Totals exclude prefetch-only chunks, HTML, images, fonts, analytics and SW downloads. They are not total page weight or the complete app bundle.

Home preloads `/_nuxt/DZf8cCLO.js` (146,110 decoded/19,880 gzip bytes) with producer lookup data and `BUN8dXRC.js` (91,183/27,591) with experience logic. Current `webui/shared/data/product-line-index.json` is 162,815 bytes, statically imported by `webui/shared/product-line-map.ts:1–12`. Source trace: `webui/app/components/ScannerPage.vue:34–37` → scanner components → `webui/app/components/PhotoScanner.vue:120`/`webui/app/components/ShelfScanner.vue:95` → `webui/app/components/WineExperiences.vue:3–6` static lookup/taste/label imports and dialog components. Production markers support the connection; an attested manifest is needed for exact chunk-to-current-commit identity.

**Fix:** lazy boundaries for inactive modes/result-only experience components; defer lookup/guide logic until needed. Keep primary copy/headings and published guides SSR. Full producer map JSON already loads dynamically (`webui/shared/product-line-map.ts:20–30`); preserve it.

```vue
<!-- Proposed PhotoScanner change; examine other result-only consumers too. -->
<LazyWineExperiences v-if="hasResult && wine"
  :key="slug" :wine="wine" :recognized="!mock" />
```

**Side effects:** first-use loading state, focus/cancellation/retry/offline behavior. A remaining shared import can keep a chunk eager. **Verify:** cold graph/long-task trace before/after, result chunks absent before a wine exists, guides fetched when needed, functional regression including accessible dialogs. Proposed initial home module-preload budget ≤400KiB decoded, subject to feasibility. No numerical CWV gain is promised.

## Existing optimizations and bounded follow-up checks

- **Compression/cache:** sampled text negotiates gzip; Caddy snapshot has `encode zstd gzip`. Hashed `/_nuxt/` assets are immutable for a year. `/reference/` and app screenshots have week-long rules (`webui/nuxt.config.ts:172–174`). No missing-compression or hosting-replacement defect is established.
- **Fonts:** local Playfair WOFF2 is 74,640 bytes with week caching. `webui/app/assets/main.css:1–7` uses swap. No preload is present; absence alone is not a defect. Inspect the waterfall/LCP/shift trace before preloading/subsetting; preserve Cyrillic coverage.
- **Images:** WebP, dimensions and below-fold lazy images exist on app/game pages. `webui/app/components/WineImage.vue:5–12` supports dimensions/async decoding/fallback but no srcset. Aside from measured shelf/logo issues, do not propose a blanket image-library rewrite without sizes/traces for the affected asset.
- **HEIC:** the observed worker wrapper is only 1,726 decoded bytes. `webui/nuxt.config.ts:141–142` excludes it from precache; `webui/scripts/prepare-dinner-decoder.mjs:4–9` prepares an on-demand decoder. No eager multi-megabyte decoder load was established.
- **Metrika:** asynchronous loader `webui/shared/metrika.ts:5–16`; SPA hit timing `webui/app/plugins/metrika.client.ts:15–25`. No measured blocking-time contribution was obtained; measure before changing analytics timing.
- **PWA:** `webui/nuxt.config.ts:102–159` precaches build assets and uses NetworkFirst navigation. `sw.js` revalidates (`max-age=0`), appropriately. SW install may fetch more than initial page references. Compare fresh install, returning visit and update separately after splitting code/assets.

Presentation video HEAD advertises 907,106,164 bytes, but `webui/app/pages/presentation.vue:43–48` uses metadata preload and the page is noindex. No full video was downloaded. Size alone does not prove that the whole file transfers at initial load; range/playback checks can be added if that presentation becomes a priority.

## Responsive verification limits

My requested 390×844 actually yielded **520 CSS px**; reset desktop width was 2167. At 520, sampled routes showed no document overflow. Claude's provided headless settings are 412×823, and the [original final screenshot](evidence/claude-first-visit.jpg) shows the age dialog. Neither check verifies physical 360/390px phones, post-confirmation interactions or field CWV. SEO-016/017 still require those comparisons.
