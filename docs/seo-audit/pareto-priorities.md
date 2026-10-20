# Pareto priorities

Prioritization date: 20 October 2026. This changes the execution plan, not the application or the audit observations. It uses the production/source evidence in the [audit](README.md) and [Claude review](claude-review.md); no new production measurements were made for this prioritization.

**First wave: five open issue IDs, delivered as four packages.** The originally selected sixth ID, SEO-001, is now reconciled for production 0.3.0: full-file hash, size, manifest and published metadata match. Only minor HEAD 404 remains outside the first wave; see [verification](android-030-verification.md). Do not automatically replace completed work with another task. The shared image work has the clearest measured opportunity; task-page explanations address core search intent. This is qualitative 80/20 prioritization, not a claim of 80% traffic, rankings or revenue, nor a measured share of engineering hours.

There is no established sitewide indexing outage. All 16 submitted URLs returned 200 with distinct titles/descriptions and route canonicals at the audit baseline. That makes a broad rendering, routing or metadata rewrite a weaker first investment than the scoped work below.

**Latest status, 19:43:56 UTC:** [E11 current-state check](evidence/next-task-state.json) confirms the vector logo is prepared locally at **2,810 bytes**, while production still returns the **171,311-byte** embedded-bitmap SVG. Finish its review/release verification separately; do not redo the asset work. The next implementation task is **SEO-003 shelf display/thumbnail derivatives**: live markup still uses the full originals, and the shelf H1 still repeats home. No release was performed by this audit.

## First wave

Source locations refer to baseline `cd8b063e`; later concurrent edits can move line numbers. Effort follows the main README: S up to one engineer-day, M approximately 2–5 days, planning estimates only. Keep at most two implementation packages active. The APK reconciliation package is no longer open first-wave work.

| Order | Issue / package | Scoped implementation and source | Reason to do it now | Effort | Acceptance |
|---|---|---|---|---|---|
| 1 | **SEO-002: shared logo** | Replace the display asset with a small approved derivative/compact vector. `webui/app/components/ProductBrand.vue:3`, `webui/public/icons/product-logo.svg`, `webui/nuxt.config.ts:64,106`. Update versioned references/PWA handling. | A 44px logo transfers **155,135 gzip bytes** across shared pages. Broad reach, small change, measured bytes. | S | Proposed display budget ≤10KiB, subject to visual QA; compare 1×/2× and both themes, cold GET bytes, worker updates and favicon references. No promised LCP/ranking gain. |
| 2 | **SEO-003: shelf display images** | Separate display derivatives/thumbnails from recognition originals. `webui/app/components/ShelfScanner.vue:69–72`, `webui/shared/shelf.ts:7–33`, `webui/app/composables/useShelfScanner.ts:91–99`. | Three originals total **2,313,438 bytes**. Supplied mobile lab runs transfer about **2.98 MB** and report LCP **15.0–15.9s**. Large confirmed cold-load opportunity on a core tool. | S–M | Cold mobile/desktop traces select smaller display assets; recognition still receives originals on staging. Preserve framing, dimensions and switching. Compare like-for-like lab runs; bytes saved do not prove the same LCP saving. |
| 3 | **SEO-028: directory card covers** | Use card derivatives in `webui/app/pages/lineup/index.vue:40` and `webui/shared/data/product-line-index.json`. Preserve/recompute frame geometry consumed by `webui/app/components/ProductLineImage.vue:14–23`; keep detail originals. | Both original directory lab runs estimate **976,413 wasted image bytes**. Reuse the image work while its implementation context is current. | M | Compare cold transferred image bytes and the sizing audit; visually check all cards, clipping, 1×/2×, cover-error fallback and unchanged detail maps. Follow `webui/docs/product-image-sizing.md`. |
| 4 | **SEO-009 + SEO-011: task clarity** | Give shelf its own H1 and add concise factual SSR explanations to **home and shelf first**. `webui/app/components/ScannerPage.vue:29–45`. Explain inputs, results, catalogue limits and uncertain/no-match behavior; retain the working tool first. | Core photo/label/shelf intent is already served by tools, but explanatory copy is sparse and the shelf H1 repeats home. A focused content change is cheaper than new landing-page families. Demand/ranking uplift remains unmeasured. | S + M | One task-specific SSR/rendered H1, useful explanation without JS, truthful product facts, existing editorial/legal acceptance and actual 360/390px QA. No word-count or exact-match keyword quota. Compare real page/query data after recrawl when available. Dish expansion/new guides remain later scope. |

The open first-wave IDs are **002, 003, 028, 009, 011**. This is five IDs across four packages because the task-copy changes are grouped. Detailed fixes/side effects remain in the [backlog](remediation-backlog.md), [performance audit](performance-audit.md), [on-page audit](on-page-audit.md), [deployment audit](deployment-audit.md) and [accepted Claude additions](claude-review.md#implementation-and-acceptance-for-accepted-additions).

Image work includes appropriate cache/version handling for the assets it changes. A separate blanket image-folder caching project is not required to start. The 2.31 MB originals, 976 KB estimated waste and logo bytes refer to different routes/methods: do not sum them into an invented sitewide saving.

## Small checks alongside delivery

- **SEO-020 / 016 / 017:** confirm existing Google Search Console/Yandex Webmaster access and inspect home, shelf and dish coverage/rendered content; obtain existing query/device/field data if available. Account absence and an age-gate indexing block are unproven. Missing field data does not stop the measured image work. Start with access/inspection, not a new telemetry plugin or a monitoring platform.
- **SEO-013:** retain a dated before/after response and resource check with each future release, including XML/noindex, route metadata and the APK contract. Keep it read-only. The broader script/CI/revision-attestation project is next-wave scope; do not run the mock evaluator contract against production.
- **SEO-018:** apply the existing page-specific factual/legal review requirement to new copy. Broad producer-publication review is conditional work; it need not hold up image-only changes. Keep age protections and current producer exclusions.

These are bounded verification/dependency work, not extra first-wave implementation projects. They do not authorize this documentation task to create accounts, post issues, change infrastructure or deploy.

## Decision for all 30 drafts

This table covers each current draft exactly once. It supersedes earlier execution ordering, while historical defect/confidence statements and evidence remain intact. SEO-007 has no issue draft and is tracked separately as publication-policy/release verification.

| Tier | IDs | Decision |
|---|---|---|
| **NOW — five IDs** | SEO-002, SEO-003, SEO-028, SEO-009, SEO-011 | Implement the four remaining scoped packages above. |
| **CORE RESOLVED / FOLLOW-UP — one ID** | SEO-001 | Production 0.3.0 artifact/metadata identity verified. Remaining HEAD 404 is P3/S, outside the first wave; no APK replacement/reconciliation task. |
| **NEXT — eight IDs** | SEO-004, SEO-005, SEO-006, SEO-008, SEO-013, SEO-016, SEO-017, SEO-020 | Complete the small response/metadata corrections and sustained release checks after the first wave. Start the bounded account/crawler/metric checks alongside it. Split result JS only after a fresh waterfall/trace shows the remaining bottleneck; defer a broad rewrite. |
| **CONDITIONAL — four IDs** | SEO-010, SEO-012, SEO-018, SEO-031 | Producer indexing needs publication/legal decisions; Shelf Lens needs an actual product/release decision. Investigate health caching when staging or production timing demonstrates its benefit; the two-second source timeout is not an observed outage. Focused new-copy review still applies now. |
| **DEFER — twelve IDs** | SEO-014, SEO-015, SEO-019, SEO-021, SEO-022, SEO-023, SEO-024, SEO-025, SEO-026, SEO-027, SEO-029, SEO-030 | URL/schema/fallback cleanup, preload experiments, favicon/branded errors, broad TTLs, bot rewrites, extra links, social art, optional dates and title variants have weaker demonstrated first-wave returns. Reopen when evidence or a closely related planned edit makes the marginal work worthwhile. |

Favicon is a real defect, but the linked SVG already works; it is not evidence of a broad discovery failure. Dish OG is a real preview defect with no demonstrated direct ranking effect. Unknown producer 200s are already noindex. All 16 submitted URLs are reachable within two links. These distinctions keep cheap cosmetic/correctness work from displacing the larger measured opportunities.

For SEO-007, follow the newer recorded local publication intent; do not reintroduce the historical hackathon block. The last production check still saw exclusions. Verify any separately authorized release against [the recorded acceptance procedure](claude-review.md#concurrent-workspace-follow-up), rather than assuming local edits are deployed.

## Reprioritization and completion

Promote a newly demonstrated indexing/access blocker on a core landing page above this queue. Otherwise, finish the image changes and scoped copy before starting another architecture project. If fresh traces after image changes identify JS/health latency as the remaining major constraint, promote SEO-004/031. Use actual query/page evidence to choose producer coverage, dish explanations or Shelf Lens next; none has measured demand in this audit.

The remaining first wave is complete when smaller display assets are verified without recognition/visual regressions and home/shelf explanations render correctly. The APK contract was attested by the 0.3.0 follow-up; no new reconciliation work is needed for that release. Keep dated comparable measurements, including age-gate/cache/device state and Lighthouse CPU warnings. Field CWV, indexing and search growth need their own evidence; the initial laboratory numbers do not establish them.
