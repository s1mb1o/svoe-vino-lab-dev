# Review of Claude's parallel SEO findings

Reviewed on 20 October 2026. This is a verification and reconciliation of Claude's work, not an application change. Current issue drafts are in [github-issues/README.md](github-issues/README.md): **30 drafts, IDs SEO-001–031 excluding SEO-007**. Their latest numbering mostly follows the main backlog; archived early drafts used different IDs. References below use the **current issue-draft IDs**.

The subsequent [Pareto plan](pareto-priorities.md) supersedes the execution order in this review. Historical evidence below is preserved; the later [APK 0.3.0 verification](android-030-verification.md) resolves the original mismatch and leaves only a minor HEAD task. Five first-wave IDs remain; confirmed favicon and other cleanup tasks stay outside them.

Claude's main findings agree with the audit: artifact mismatch, oversized logo/shelf imagery, eager result code, dish social tags, shelf H1, missing-producer status and intentional producer exclusions. His additional performance evidence is useful. Some proposed fixes need narrower scope, and `/hackaton` was incorrectly treated as an automatic remediation task in my initial audit.

## Evidence checked

| Evidence | Review result |
|---|---|
| [Claude's Lighthouse summary](github-issues/lighthouse-2026-10-20.json) | 15 runs: two mobile runs on seven URLs, one home desktop run. |
| Original Lighthouse result JSONs | Found under Claude's temporary scratchpad, not just the summary. LCP/CLS/performance score and final URL match the summary in **all 15**. Original hashes, settings and selected raw audits are preserved in [validated excerpts](evidence/claude-lighthouse-validated.json). No new Lighthouse run was made. |
| Fresh HTTP checks | [13 read-only GET/HEAD observations](evidence/claude-review-http.json), at approximately 18:14:45 UTC: favicon, HTML errors, account canonical and cache headers. |
| First-visit screenshot | [Original Lighthouse screenshot](evidence/claude-first-visit.jpg) confirms the visible age gate. Configuration is 412×823 CSS px, simulated mobile, storage reset enabled. This is not a physical-device test. |
| Nitro source | Published `nitropack@2.13.4` archive matches `webui/package-lock.json` SHA-512 integrity. [Source excerpt](evidence/nitro-favicon-source.txt), [provenance](evidence/nitro-favicon-provenance.json). No package was installed. |
| Recorded owner decision | `webui/ResearchLog.md:947–957` explicitly prioritizes a crawl block for `/hackaton`, accepting that a discovered URL may remain indexed. |

Original Lighthouse files were approximately 8.84 MB total. The validated JSON retains paths/SHA-256 plus relevant audit fields, omitting large screenshots and unnecessary request payloads. The original reports are temporary files; the evidence excerpts and screenshot are in this repository.

## Lighthouse: accept as laboratory evidence

| URL | Mobile performance scores | Simulated mobile LCP, seconds | CLS | Transferred bytes |
|---|---|---|---|---|
| `/` | 41 / 55 | 4.827 / 3.765 | 0 / 0.005 | 675,788 / 676,876 |
| `/shelf` | 42 / 42 | **15.918 / 15.018** | 0.003 / 0.003 | **2,984,775 / 2,984,866** |
| `/dish` | 52 / 55 | 4.688 / 3.898 | 0.003 / 0.003 | 720,292 / 704,433 |
| `/lineup` | 48 / 50 | 5.871 / 5.261 | 0.002 / 0.002 | 1,639,017 / 1,684,753 |
| `/lineup/abrau-durso` | 44 / 50 | 5.931 / 4.898 | 0.025 / 0.027 | 1,226,521 / 1,174,140 |
| `/android` | 49 / 52 | 4.961 / 4.660 | 0.004 / 0.004 | 712,592 / 749,079 |
| `/ideas` | 51 / 52 | 4.581 / 4.434 | 0.003 / 0.003 | 1,023,896 / 1,045,050 |

Home desktop: performance 70, simulated LCP 0.922 s, CLS 0.003. These are recorded lab runs, not field p75 and not a ranking measurement. No INP value was established.

Important qualifications:

- Mobile configuration uses simulated throttling, including a 4× CPU slowdown. Actual benchmarkIndex ranges from 660.5 to 1292.5. Home run 2 and directory run 1 explicitly warn that the machine's CPU is slower than Lighthouse expects. Absolute simulated LCP, not only TBT, needs this caveat.
- All runs are first visits with the age gate open. The observed LCP node is the inert `.site-shell`, whose pseudo-element uses the background image. Post-confirmation user experience needs a separate comparison; no age bypass is proposed.
- Modeled and observed trace timings differ. For home run 2, modeled LCP is 3765 ms and the raw observed trace LCP is 882 ms. They are different outputs of the configured run, not contradictory measurements to average together.
- A Lighthouse SEO score of 100 does not establish real search indexing, legal compliance, complete metadata quality or field CWV success.

The image findings are now corroborated by both independent HTTP/source checks and the original Lighthouse audits. This strengthens their priority. My initial report's lack-of-lab-data limitation is superseded by these provided reports; the lack of field data remains.

## Additional findings and verdicts

| Claude issue | Verdict | Evidence, required qualification and action |
|---|---|---|
| [SEO-019: global canonical/OG](github-issues/SEO-019.md) | **VERIFIED fallback behavior; optional architecture cleanup** | Fresh HTML requests confirm home canonical on noindex account and real 404 pages. All 16 submitted public pages already have their own canonical. A canonical is not a redirect, and a 404 remains a 404: no broad indexable-page canonical failure was shown. Remove risky home fallbacks or introduce an explicit route metadata contract as a small cleanup, with full route/error tests. Root: `webui/nuxt.config.ts:47,63`. |
| [SEO-020: webmaster accounts](github-issues/SEO-020.md) | **REQUIRES VERIFICATION; useful process task** | Missing meta/DNS tokens do not prove absence of verification: HTML files, other properties or ownership methods may exist. Obtain read-only account confirmation and actual coverage/query data. Do not describe registration as a confirmed defect. |
| [SEO-021: preload background](github-issues/SEO-021.md) | **VERIFIED discovery path; controlled optimization experiment** | Raw LHR identifies background URL, CSS discovery and modeled load delay. But `prioritize-lcp-image` reports **0 ms estimated savings**, despite its non-passing score; 1638 ms modeled load delay is not a promised preload saving. Test preload against the same gated/confirmed states and foreground-image competition. Do not add a global high-priority preload to presentation, where the background is disabled. Sources: `webui/app/assets/main.css:108–110`, `webui/nuxt.config.ts:62–66`. |
| [SEO-022: invalid favicon](github-issues/SEO-022.md) | **VERIFIED defect; root cause corrected** | GET returns 78 ASCII bytes beginning `data:image/gif;...` while MIME is `image/x-icon`. Exact body and MIME branch exist in Nitro's `dist/runtime/internal/renderer.mjs:18–23`. No matching favicon rule was found in the inspected Caddy snapshot. Add a genuine `webui/public/favicon.ico`; verify it supersedes the fallback. Do **not** require deleting a hypothetical edge rule. Existing linked SVG favicon is valid, so this does not prove that every browser/search favicon is broken. |
| [SEO-023: default English 404](github-issues/SEO-023.md) | **VERIFIED UX improvement, P3** | With `Accept: text/html`, production returns real 404 with default Nuxt English error copy and home canonical. The earlier JSON 404 result used different content negotiation; both observations can be correct. A proposed `webui/app/error.vue` should give Russian recovery navigation while preserving 404. Not a sitewide indexing blocker. |
| [SEO-024: image caching](github-issues/SEO-024.md) | **VERIFIED optimization** | One tested asset in each of `/icons`, `/line-wines`, `/product-line-maps`, `/dishes`, `/crocodile`, `/game-art`, `/wines` has no explicit Cache-Control; most have ETag/Last-Modified. Lack of explicit TTL is not absence of all browser caching. Add version-safe bounded TTLs in `webui/nuxt.config.ts` according to update frequency; fixed mutable filenames can remain stale. Do not apply the rule to HTML, private/API responses or `sw.js`. |
| [SEO-025: bot similarity](github-issues/SEO-025.md) | **Optional editorial improvement; reject numeric SEO threshold** | Shared template/platform substitution is evident in `webui/app/components/BotLanding.vue` and `webui/app/data/botLandings.ts`. A 0.61 shingle metric is not a search-engine duplicate decision; no evidence establishes that similarity must be below 0.4. Add truthful platform-specific help if useful, not arbitrary paraphrasing to meet that threshold. |
| [SEO-026: extra internal links](github-issues/SEO-026.md) | **Optional contextual navigation** | Existing SSR graph reaches all 16 submitted pages within two links. There is no orphan-page problem in that set. Relevant links from explanations are useful, but broad footer changes are not urgent crawl remediation. Source: `webui/app/app.vue:57–61`. |
| [SEO-027: landscape social image](github-issues/SEO-027.md) | **Optional presentation improvement** | Square app icon with Twitter `summary` is a coherent valid choice. A truthful landscape image can improve large previews, but existing shape is not a confirmed SEO defect. Source: `webui/nuxt.config.ts:10,48,51,54`. Preserve page-specific images. |
| [SEO-028: directory covers](github-issues/SEO-028.md) | **VERIFIED optimization worth adding** | Both raw directory runs report 976,413 potentially wasted image bytes (about 954 KiB). Fresh HEAD confirms the example cover is 252,778 bytes. `webui/app/pages/lineup/index.vue:40` renders it at card scale. Generate card derivatives through the existing frame/crop pipeline, preserving/updating geometry used in `webui/app/components/ProductLineImage.vue:14–23`. Keep originals for detail maps. Lazy loading alone does not fix oversized visible covers. Savings are an audit estimate, not a guaranteed page reduction. |
| [SEO-029: lastmod/HTML validators](github-issues/SEO-029.md) | **Optional; no defect** | Missing optional lastmod/ETag/Last-Modified is not invalid sitemap/SSR behavior. A page-file git date alone can miss changes in imported components/data/config. Add dates only when meaningful changes can be tracked accurately. Conditional HTML responses must respect variants/personalization; do not add global validators blindly. |
| [SEO-030: keyword title wording](github-issues/SEO-030.md) | **Optional test with query data** | Current titles are distinct and descriptive. The wording proposals are reasonable candidates, not proof of a required exact-match phrase or current ranking failure. Retain legal/factual accuracy and check real query/page data before replacing titles. |
| [SEO-031: SSR health dependency](github-issues/SEO-031.md) | **VERIFIED in source; production outage not observed** | `webui/app/components/ScannerPage.vue:3,31,37` awaits config; `webui/server/api/config.get.ts:11` awaits an uncached probe; `webui/server/utils/upstream-health.ts:13–24` allows a 2 s timeout. Keep descriptive copy stable and use a separate outage notice. A short cache/in-flight deduplication can help, but document stale availability, per-worker scope and endpoint keys. Do not promise warm response <100 ms for every environment. Verify unreachable/slow/recovering upstream on staging; no production inference/outage was induced. |

## Corrections to overlapping findings

**Hackathon policy, main SEO-007:** `webui/ResearchLog.md:949–957` explicitly requests robots exclusion and acknowledges the inability to read noindex. Preserve it as an accepted owner trade-off, not an automatic P2 fix. General noindex semantics remain correct; intent changes the recommendation. Claude correctly omitted an automatic issue draft.

**Subsequent concurrent change:** this paragraph describes the audit baseline. A newer local edit explicitly reverses that decision; see [the workspace follow-up](#concurrent-workspace-follow-up). Do not use the historical policy recommendation to revert the newer work.

**Age-gate snippets, SEO-016:** the markup and first-visit overlay are confirmed. Snippet contamination is only a risk: actual Google/Yandex snippets were not obtained. `data-nosnippet` on the gate div is a supported Google measure; Yandex documents `noindex` for excluding text. These changes can be considered without removing age verification, but they do not prove or solve a rendering/indexing block. Ensure correctly closed markers, Vue SSR support and unchanged layout/accessibility. Sources: [Google data-nosnippet](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag), [Yandex text exclusion](https://yandex.ru/support/webmaster/ru/adding-site/indexing-prohibition). A snippet marker is not a page-level noindex.

**Structured data, SEO-015:** shorter truthful `WebSite.name = 'Что за вино?'` is a reasonable brand cleanup. Google requires site-name markup on the homepage and says it need not be repeated on all pages; that does not establish that repeating the same entity elsewhere is invalid. Moving all graphs to home is optional, not a proven repair. [Google site-name specification](https://developers.google.com/search/docs/appearance/site-names).

**Shelf Lens, SEO-012:** source/production drift is confirmed, but not every undeployed feature is a production bug or authorization to deploy current main. Page/media/navigation/XML must ship together under an actual release decision. Production timestamps alone do not attest a commit.

**Shared H1/content, SEO-009/011:** retain the improvements, but call them relevance/usability work. Neither a 161-word count nor missing exact query verbs establishes a low-quality penalty. **APK, SEO-001:** that earlier size mismatch was real at the audit baseline. The subsequent [0.3.0 check](android-030-verification.md) verifies the complete production file/hash/manifest/certificate and metadata agreement; the primary issue is resolved, with HEAD 404 retained as P3/S.

## Recommended additions and order

1. Keep display logo and shelf derivatives among the first packages. APK identity has since been verified for 0.3.0; no replacement/reconciliation project remains. The lab results reinforce image priority.
2. Add **valid favicon** and **directory card derivatives** as concrete new tasks. The former is a missing public asset/framework fallback, not a demonstrated Caddy rule.
3. Add explicit, version-safe image caching. Measure result-code splitting and optional background preload under controlled conditions.
4. Keep SSR health resilience as a source-confirmed staging task. Preserve static task explanation alongside unavailable controls.
5. Keep snippet exclusion, metadata fallback cleanup, branded errors and brand-name schema as small reviewed improvements. Account access/field CWV remain verification tasks.
6. Respect recorded publication decisions, including the newer local hackathon reversal described below; preserve producer review exclusions unless deliberately revised. Do not impose arbitrary text-similarity targets, blanket schema removal, automatic feature deployment or a ranking forecast.

## Implementation and acceptance for accepted additions

These task IDs follow Claude's drafts. Effort uses the S/M/L definitions in the main README. Laboratory image savings are estimates; use comparable before/after runs to measure the delivered benefit.

| Task / priority / effort | Required implementation and source | Side effects and verification |
|---|---|---|
| SEO-022 / P2 / S | Add genuine `webui/public/favicon.ico`, keeping the valid SVG reference at `webui/nuxt.config.ts:64`. The missing public file currently exposes Nitro renderer fallback lines 18–23, preserved in E08. | Preserve the approved artwork and icon resolution. On staging then production, GET must return an icon that a decoder identifies, correct MIME and a successful response; inspect browser/Search favicon after recrawl. No Caddy deletion is supported by the evidence. |
| SEO-028 / P2 / M | At `webui/app/pages/lineup/index.vue:40`, use separate card-cover derivatives through index data (`webui/shared/data/product-line-index.json`). Follow `webui/docs/product-image-sizing.md:7–38`; preserve or recompute frame geometry consumed at `ProductLineImage.vue:14–23`. Keep detail originals. | Crop/scale changes can clip bottles or invalidate dimensions. Check all producer cards at mobile/desktop and 1×/2×, cover-error fallback and unchanged detail maps; run the existing producer-map checks in a development environment. Repeat directory Lighthouse with identical settings; compare transferred image bytes and the original 976,413-byte estimated waste. |
| SEO-024 / P3 / S | Extend `webui/nuxt.config.ts:161–174` with explicit image-folder TTLs after choosing versioned filenames or a bounded policy matching update frequency. All seven tested folders are listed in E07. | Mutable names can serve stale art. GET/HEAD one resource per changed rule; confirm headers, conditional requests and an actual warm browser visit. Confirm HTML, account/API responses and `sw.js` retain their existing policies. Test an asset replacement/update path. |
| SEO-031 / P2 / M | Keep task description stable in `ScannerPage.vue:31`, separate unavailable notices, and add bounded endpoint-keyed health caching/in-flight deduplication in `server/utils/upstream-health.ts:13–24` called by `server/api/config.get.ts:11`. Define TTL/recovery behavior first. | Stale availability can temporarily enable or disable controls; module caches are per worker. On staging, test healthy, slow, unreachable, recovering and concurrent requests. Assert stable SSR description, appropriate disabled controls, timeout behavior and bounded upstream calls. Compare TTFB distributions; no universal <100 ms requirement. |
| SEO-021 / P3 experiment / S | Evaluate a route-aware background preload for pages using `main.css:108`; exclude the presentation rule at line 110. Head insertion point is `nuxt.config.ts:62–66` or route-specific head composition. | A high-priority image can compete with CSS/fonts/foreground content. Compare at least three identical cold runs per variant and both age states on staging; inspect actual LCP candidate, load delay, LCP distribution and request priority. Retain only a demonstrated improvement without a regression; a passing audit alone is insufficient. |

## Concurrent workspace follow-up

At approximately **18:25–18:26 UTC**, the shared workspace changed during this review. HEAD had advanced to `7cb1044c1338f32b714e63c47b9b341872e51f37`, and local edits removed hackathon robots/meta/header exclusions, added the page to XML/HTML sitemaps and updated tests/specification. The new `webui/ResearchLog.md:3–11` records an owner-requested reversal of the September decision. I left these changes untouched and did not run their tests or deploy them. Original source citations above refer to the audit baseline `cd8b063e`; concurrent insertions shift some current line numbers.

A fresh [three-URL public check at 18:26:20 UTC](evidence/hackathon-policy-followup.json) still finds **production** `Disallow: /hackaton`, both noindex header/meta and a 16-entry XML without hackathon. Thus the newer local intent is not demonstrated as deployed. This is release/policy drift, not evidence that the original crawler block was accidental. Do not revert the local change based on the historical audit; verify its intended release separately.

After any separately authorized release of that change, GET `/hackaton`, `/hackaton/` and a query variant; check HTTP 200, self canonical, absence of both noindex layers, no robots disallow, sitemap inclusion and unchanged account/producer exclusions. Then inspect actual Google/Yandex coverage after recrawl. Source test updates alone do not establish index inclusion.

No issue was posted, no issue-creation script was run, and application source/production were unchanged by this review. Existing Claude issue drafts are preserved; this document records recommended corrections without silently rewriting them.

The subsequent user-requested APK 0.3.0 verification explicitly updated the SEO-001 draft/index and current priorities. Other Claude drafts were preserved; no issue was posted.
