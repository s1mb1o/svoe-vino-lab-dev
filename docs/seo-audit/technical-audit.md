# Technical SEO audit

Baseline: source `cd8b063ecd000872567e543407b11926b45b3d37`, 20 October 2026. [README](README.md) defines scope, confidence and E01–E05. This report uses the recorded public HTTP/browser evidence; a local implementation is not proof of a deployed implementation.

**APK follow-up:** [E10 / 0.3.0 verification](android-030-verification.md) supersedes the historical SEO-001 artifact mismatch: exact file identity now agrees with page/schema and remote main, with HEAD 404 retained as P3/S. Other observations below retain their original sampling dates.

## Framework, rendering and discovery

`webui/package.json:34–39` declares Nuxt 4.5.2, Vue 3.5.40 and Vue Router 5.2.0. `webui/nuxt.config.ts:176` selects Nitro `node-server`. No `ssr: false` or prerender list was found. This is server rendering with client hydration; recognition, recommendations, dialogs and account functions are interactive. No separate SEO library is declared; metadata uses `useHead`/`useSeoMeta`. `@vite-pwa/nuxt` supplies PWA support.

**VERIFIED production:** home, shelf, dish, producer directory and application pages contain their real headings/copy in initial HTML. The Nuxt payload reports `data-ssr="true"`. Normal, Googlebot-string, YandexBot-string and mobile-string home responses were 200 with identical decoded SHA-256 `24d9e556af21429204ea69bea9ec8af22902f35c2a614832c9e9f32d330fe2cf`. These are User-Agent parity checks, not authenticated bot visits. E01 preserves exact records.

**VERIFIED browser:** primary headings/canonicals on sampled routes agree with SSR. A client-side `/dish` → `/shelf` link updated title/canonical correctly. No console warning/error appeared in the sampled Fanagoria-page log. E04 describes the existing age-confirmed session and actual viewport widths. No general hydration failure was demonstrated.

Result-only copy requires an interaction and is absent from the initial home page. That is normal for tool results, but explanatory landing content should not depend on uploading a photograph (SEO-011).

## Public URL to implementation map

All main-host paths expand to `https://chtozavino.ru`. Shared layout/navigation/age shell: [webui/app/app.vue](../../webui/app/app.vue#L33), lines 33–63. Shared head/JSON-LD: [webui/nuxt.config.ts](../../webui/nuxt.config.ts#L33), lines 33–99. Pages use file-based routing under `webui/app/pages/`.

| Public path | Source implementation | Metadata/policy | Verified production observation |
|---|---|---|---|
| `/` | `webui/app/pages/index.vue:1–7` → `webui/app/components/ScannerPage.vue` → `webui/app/components/PhotoScanner.vue` | `webui/nuxt.config.ts:7–99`; page title line 2 | 200, SSR, self canonical; XML |
| `/shelf` | `webui/app/pages/shelf.vue` → `webui/app/components/ScannerPage.vue:34–37` → `webui/app/components/ShelfScanner.vue`/`ShelfUnavailable.vue` | page lines 2–5 | 200, available UI; XML |
| `/dish` | `webui/app/pages/dish.vue` → `webui/app/components/ScannerPage.vue:35` → `webui/app/components/DinnerScanner.vue` | page lines 2–5 | 200, SSR picker; inherited home social tags; XML |
| `/lineup` | `webui/app/pages/lineup/index.vue:1–51`; `webui/shared/data/product-line-index.json` | page lines 5–8 | 200, 25 real producer links; XML |
| `/lineup/{producer}` | `webui/app/pages/lineup/[producer].vue:11–32`; `webui/shared/product-line-map.ts:20–30`; `webui/app/components/ProductLineMap.vue` | page lines 17–18; config line 163 | Two GET samples 200/meta+header noindex; 25 detail HEAD samples noindex; not XML |
| `/android` | `webui/app/pages/android.vue`; `webui/shared/android.ts:1–13` | page lines 6–39 | 200, SoftwareApplication; XML; earlier mismatch now resolved for 0.3.0 (E10) |
| `/iphone` | `webui/app/pages/iphone.vue` | page lines 3–35 | 200; native app described, TestFlight next step; XML |
| `/telegram-bot`, `/max-bot` | respective pages → `webui/app/components/BotLanding.vue`; `webui/app/data/botLandings.ts` | component lines 19–52 | 200, route-specific metadata; XML |
| `/ideas` | `webui/app/pages/ideas.vue`; `webui/app/components/WineExperiences.vue` | page lines 4–7 | 200; implemented/demo/planned sections distinguished; XML |
| `/game` | `webui/app/pages/game.vue` | page lines 2–7 | 200 SSR landing; links separate game project; XML |
| `/crocodile` | `webui/app/pages/crocodile.vue`; `webui/app/data/crocodile-cards.ts` | page lines 4–7 | 200; printable links returned 200 HEAD; XML |
| `/presentation` | `webui/app/pages/presentation.vue:1–74` | page lines 8–18; external Caddy snapshot lines 48–55 | 200 with edge noindex, nevertheless XML |
| `/terms`, `/privacy`, `/contacts` | respective pages → `webui/app/components/LegalPage.vue` | component lines 13–20; `webui/app/app.vue:20–24` | 200, individual metadata, no initial age dialog; XML |
| `/sitemap` | `webui/app/pages/sitemap.vue`; `webui/app/data/sitemap.ts:12–55` | page lines 4–22 | 200, crawlable HTML map, CollectionPage; XML |
| `/account`, `/max` alias | `webui/app/pages/account.vue:8–11`; `webui/server/middleware/max-host.ts` | config lines 165–168 | account 200/noindex/no-store; main-host max 302 to account; not XML |
| `/hackaton` | `webui/app/pages/hackaton.vue` | page line 13; config 164,169; `webui/public/robots.txt:5` | 200/noindex, robots-disallowed; not XML |
| `/shelf-lens` | `webui/app/pages/shelf-lens.vue`; `webui/server/routes/shelf-lens-video/[filename].ts` | page lines 2–6; local XML line 16 | 404 production, absent from live XML; local source only |
| `/wines`, `/wines/` | `webui/nuxt.config.ts:170–171` | permanent redirect rules | 308 to home |
| `/wines/{slug}` | `webui/server/routes/wines/[slug].get.ts:1–3`; `webui/shared/catalog.ts:30–31` | `sendRedirect(...,308)` | Real sample 308 to matching vino-svoe.ru wine page |
| `/downloads/{filename}` | `webui/server/routes/downloads/[filename].get.ts:5–30` | runtime artifact target | 0.3.0 GET 200/full hash and metadata match; HEAD 404 remains (E10) |
| `/robots.txt`, `/sitemap.xml` | static files in `webui/public/` | manually maintained; HTML list in `webui/app/data/sitemap.ts` | Both 200/correct content types |

API handlers reside under `webui/server/api/` and compatibility handlers under `webui/server/routes/v1/`. They are not landing pages and are disallowed in robots. `/api/config` reported upstream/available shelf/dinner modes; no recognition request was submitted. Private provider/token values remain server-side and were not inspected.

## Crawling, indexing and URL consistency

E01 contains valid XML with **16 production URLs**, all GET 200. Fifteen have no observed noindex; `/presentation` has one. This is directive eligibility, not proof of indexing. Source XML has 17 because of Shelf Lens. Optional `lastmod`, `priority` and `changefreq` are not missing requirements. The robots Sitemap URL is correct. [Yandex sitemap guidance](https://yandex.ru/support/webmaster/ru/controlling-robot/sitemap) supports canonical sitemap URLs without guaranteeing index inclusion.

All 16 URLs are reachable in the sampled SSR link graph within two links from home, commonly via `/sitemap`. No orphan among these URLs is established. All producer cards are real anchor links. No broken internal GET content link was proven: APK HEAD 404 does not imply a broken GET download. The 53 discovered image URLs returned 200 HEAD; this is not a crawl of every image exposed by interaction.

| Test | Observed result | Assessment |
|---|---|---|
| `http://chtozavino.ru/` | 308 to HTTPS same host | Correct |
| HTTPS www root/dish | 308 to HTTPS non-www, path retained | Correct |
| HTTP www dish with `utm_source` | Two redirects, final 200 non-www, query retained | Correct; optional hop reduction |
| `/dish/`, `/shelf/`, `/android/`, `/lineup/` | 200, non-slash canonical | Consolidation exists; optional SEO-014 |
| Home/dish with UTM | 200, query-free canonical | Correct |
| Arbitrary unknown top-level URL | 404 `application/json` to the tested request | Correct status; no sitewide soft-404 fallback established |
| Unknown producer | 200/noindex missing-map page | SEO-006 |

Producer `?wine=` links select a wine (`webui/app/pages/lineup/[producer].vue:15–18`); canonicals omit the query. Do not strip functional parameters in a generic URL cleanup. Parameter combinations were not exhaustively crawled. [Google canonical guidance](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls) treats canonicalization as signals, not guaranteed selection; the sampled variants already have appropriate signals.

## SEO-005 — XML advertises an edge-excluded presentation

**VERIFIED defect, P2/S.** URL: `https://chtozavino.ru/presentation`. E01 GET is 200 with `X-Robots-Tag: noindex, nofollow, noarchive`, and live XML includes it. E02 material HEAD checks have the same exclusion.

Source: `webui/public/sitemap.xml:30–32`; `webui/app/data/sitemap.ts:46–48`; `webui/app/pages/sitemap.vue:19–21`. Nuxt page metadata does not exclude presentation. The matching local edge policy is `../chtozavino-deploy/snapshots/claudette/etc/caddy/Caddyfile:48–55`; its effective running version is not attested. Root cause: separate sitemap and edge publication decisions.

**Fix:** preserve the intentional presentation exclusion and remove its XML entry. Separate human navigation from indexable sitemap state; adapt `webui/tests/sitemap.test.ts:30–49`, which currently requires equality. A useful noindex page can remain in the HTML map. If publication is intentionally changed instead, review the entire edge/material matcher; editing a page meta tag cannot override the header.

**Side effects:** avoid exposing presentation materials unintentionally; keep CollectionPage aligned with the intended HTML map. **Verify:** every XML URL GET 200/self canonical/no noindex; presentation separately remains noindex; human navigation still works.

## SEO-006 — Missing producer maps return 200

**VERIFIED defect, P2/S.** E01: `https://chtozavino.ru/lineup/seo-audit-not-found-20261020` returns 200 with a missing-map message. Noindex currently limits index risk; an actual Google soft-404 classification is unknown.

Root: `webui/app/pages/lineup/[producer].vue:13` converts a missing result to null; line 32 renders fallback with no status change. `webui/shared/product-line-map.ts:20–22` resolves unknown IDs to undefined. After loading, reject unknown IDs:

```ts
if (!line.value) {
  throw createError({ statusCode: 404, statusMessage: 'Producer map not found' })
}
```

Distinguish an unknown ID from a transient loader error. **Side effects:** preserve a usable client error page/navigation. **Verify:** unknown GET 404; known guides 200 with existing policy; client navigation never leaves the previous producer/title visible.

## SEO-007 — Robots exclusion prevents observing hackathon noindex

**VERIFIED accepted owner policy; actual indexing REQUIRES VERIFICATION.** `/hackaton` is both robots-disallowed and noindex (E01). Source: `webui/public/robots.txt:5`, `webui/app/pages/hackaton.vue:13`, `webui/nuxt.config.ts:164,169`. A crawler prevented from fetching cannot read noindex. [Google noindex documentation](https://developers.google.com/search/docs/crawling-indexing/block-indexing).

The parallel review located the baseline decision in `webui/ResearchLog.md:949–957`: retain direct access for organizers, prioritize crawler exclusion and accept the index-removal trade-off. My initial automatic removal recommendation missed that intent. Subsequently, concurrent local edits removed exclusions and the new ResearchLog entry explicitly records an owner-requested reversal. Production still had all exclusions at 18:26 UTC. Respect that newer local intent; do not revert it based on the historical policy. Verify the intended release with robots/header/meta/XML and engine coverage, separately from this audit. See [workspace follow-up and acceptance](claude-review.md#concurrent-workspace-follow-up).

## SEO-010 — Producer search coverage is intentionally disabled

**VERIFIED intentional policy, conditional P2/M opportunity.** All 25 linked detail HEADs in E02 have noindex. E01 GET Fanagoria/Abrau confirms both header/meta and real guide content. E04 confirms rendered Fanagoria. `/lineup` itself is indexable by observed directives.

Source: `webui/nuxt.config.ts:162–163` calls details review pages; `webui/app/pages/lineup/[producer].vue:17` repeats noindex/nofollow. They are absent from XML by design. This is not an accidental block to remove automatically.

After SEO-018, define an explicit publication-ready allowlist. Make both header and meta follow that state; supply complete guide social metadata/self canonicals, add approved guides to XML and maintain factual intros/references. Keep review guides excluded. Fix SEO-006 first.

**Side effects:** wider public information exposure and more crawl/image volume. **Verify:** approved pages GET 200 without noindex in either layer, included in XML, genuine source-referenced content in SSR; review pages still noindex; actual index inclusion checked after recrawl. Demand and ranking benefit are not measured.

## SEO-012 and SEO-013 — Release drift and missing end-to-end guard coverage

**SEO-012: VERIFIED drift; release intent REQUIRES VERIFICATION, P2/M.** `/shelf-lens` and its slash variant are 404; production XML/footer omit it. Source `webui/app/pages/shelf-lens.vue:2–6`, `webui/public/sitemap.xml:16`, `webui/app/data/sitemap.ts:30`, `webui/app/app.vue:59`, `webui/app/pages/ideas.vue:10` add it. These source links are not evidence of broken production links today.

Treat page/media/routes/images/XML/HTML navigation as one release contract. **Verify** staging page/media and video ranges, then the attested production revision/URL set only after a separately authorized release; alternatively keep the feature consistently unpublished. **Side effects:** media payload and PWA update compatibility. No release is performed by the audit.

**SEO-013: VERIFIED stale source assertions; LIKELY broader release-coverage gap, P2/M.** `webui/tests/seo.test.ts:8–69` checks source strings. `webui/tests/sitemap.test.ts:18–49` cannot see Caddy headers. `webui/scripts/check-contract.mjs:40–41` expects old age-loading markup; lines 79–82 expect 302 although source and production use 308. The script was not run; these assertions are stale by inspection. It requires mock mode (line 12) and submits evaluator images (line 18): never use it as a production SEO smoke command.

`.gitlab-ci.yml:26–40` runs Web UI checks. The inspected GitHub matcher/MCP/runner-smoke workflows do not provide a general Web UI build, although the deploy runbook identifies GitHub main as production source. External/manual release checks may exist; their absence is not proven.

Add a separate proposed `webui/scripts/check-seo-http.mjs`, maintain mock assertions separately, and wire appropriate build/staging/public-response checks into the actual release process. Attest a build revision without exposing private configuration. Test status/redirect/canonical/title/H1/header+meta robots/XML/artifact contract. **Verify:** seeded edge-noindex-in-sitemap or wrong package fails; valid staging manifest passes; no uploads/inference/account operations. **Side effects:** bounded deterministic checks, no costly model invocation or private endpoint leakage.

## SEO-014 — Optional URL normalization

**VERIFIED behavior, P3/S.** `webui/nuxt.config.ts:161–175` has compatibility redirects but no general slash rule; external Caddy snapshot lines 9–17 handles www. Existing canonicals already consolidate variants.

If beneficial, a proposed `webui/server/middleware/canonical-url.ts` can normalize only known GET/HEAD HTML routes, retaining queries and excluding APIs/downloads/static directories. A single-hop HTTP-www redirect is optional. **Side effects:** directory semantics, functional queries and PWA caches. **Verify:** no loops, correct query/host/path, unchanged POST/API/media behavior. This is not an indexing emergency.

## Age verification, JavaScript and indexability — SEO-016

**Implementation VERIFIED; crawler outcome REQUIRES VERIFICATION, P2/S investigation.** `webui/app/app.vue:6–29,35,63` renders the real page under an inert shell plus age dialog. `webui/shared/age.ts:5–7` handles prior confirmation before paint; `webui/app/components/AgeGate.vue:8–11,16–37` requires successful local storage; `webui/app/assets/main.css:619–620,763` controls overlay fit. Legal pages bypass the gate by route (app lines 20–24). E01 anonymous HTML contains underlying content and gate without redirecting all pages to one consent URL.

An overlay does not prove an indexing block. [Google's mandatory-interstitial guidance](https://developers.google.com/search/docs/appearance/avoid-intrusive-interstitials) explicitly discusses retaining underlying content. This audit does not establish the legal necessity of this exact design or recommend removing adult protections.

E04 used a previously confirmed session; no cookies/storage were inspected or changed and no new confirmation was submitted. Requesting 390px produced actual 520px. **Verify:** owner-run fresh-profile 360/390px screenshots, storage-denied handling and pre-confirmation legal access; Search Console live URL inspection plus Yandex rendered HTML/screenshot should retain the route's own title/H1/content/links. If incomplete, investigate a legally reviewed documented remedy; do not add a User-Agent-only bypass.

[Yandex's SSR/rendering controls](https://yandex.ru/support/webmaster/ru/yandex-indexing/rendering) should be inspected before changing account settings. Do not globally disable JS rendering or inject rotor timers without comparing the SSR portal and separate CSR game host.

## Structured data — SEO-015

**VERIFIED JSON parsing, P3/S review opportunity.** Every JSON-LD block on the 16 fetched sitemap pages parsed; E01 retains the data. This is not a Schema.org/Rich Results Test pass.

| Type | Source | Assessment / verification |
|---|---|---|
| WebSite + WebApplication | `webui/nuxt.config.ts:72–99` | Stable IDs refer to home tool. Repeating a named site entity is not inherently invalid; validate name/URL/content association. |
| SoftwareApplication | `webui/app/pages/android.vue:24–39`; `webui/app/pages/iphone.vue:23–35` | Free software offer, not free wine. Android artifact truth verified for 0.3.0 under E10; retain accurate release updates. |
| WebPage/about SoftwareApplication | `webui/app/components/BotLanding.vue:33–51` | Fits a bot information page; compare name/platform/URL with visible content. |
| CollectionPage | `webui/app/pages/sitemap.vue:15–22` | Fits actual navigation collection; preserve consistency after SEO-005. |

No app review/aggregate rating was found. Google's app enhancement requires one, so enhancement eligibility is not established. Do not fabricate ratings. [Google software-app specification](https://developers.google.com/search/docs/appearance/structured-data/software-app).

If a visible breadcrumb hierarchy is later added to approved guides, matching BreadcrumbList may be appropriate, tested against [Google's breadcrumb specification](https://developers.google.com/search/docs/appearance/structured-data/breadcrumb). Do not add a winery LocalBusiness for a place this service does not operate, fictional alcohol Offers, Recipe schema to a pairing picker, or promise FAQ/HowTo rich results. **Verify:** Schema.org Validator, Rich Results Test and visible-content comparison; save actual outcomes. Semantic truth matters more than adding types.

## Verification recipes

Use GET for status/metadata conclusions; HEAD is supplementary and demonstrably differs for the APK.

```sh
curl --compressed -sS -D /tmp/seo-dish.headers -o /tmp/seo-dish.html https://chtozavino.ru/dish
curl --compressed -sS -D /tmp/seo-presentation.headers -o /tmp/seo-presentation.html https://chtozavino.ru/presentation
curl -sS https://chtozavino.ru/robots.txt
curl -sS https://chtozavino.ru/sitemap.xml
```

Parse HTML/XML, asserting a single canonical, intended title/description/H1/social metadata, robots in both layers, and real navigation URLs. Compare SSR and client navigation in both directions. Cap APK status probes as described in [deployment audit](deployment-audit.md); do not download a large binary merely to inspect headers. Source tests and the sitemap alone cannot establish the effective edge policy.
