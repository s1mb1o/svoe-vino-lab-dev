# GitHub issue drafts — SEO audit 2026-10-20

Target repository: `s1mb1o/svoe-vino-lab-dev`. Not created yet. Labels use only existing repository labels.

Each file: line 1 is the title, line 2 is an HTML comment with labels; the rest is the body.
Create them with `sh create-issues.sh` (asks nothing, creates all; run only after review).

IDs SEO-001 to SEO-018 match `../remediation-backlog.md`. SEO-007 (`/hackaton` robots conflict) has no draft: the owner chose it on 2026-09-29 (`webui/ResearchLog.md:949`).
IDs SEO-019 to SEO-031 originated as additional findings; directory covers SEO-028 are now in the detailed backlog. Current execution tiers are in [the Pareto plan](../pareto-priorities.md). The subsequent [0.3.0 verification](../android-030-verification.md) explicitly updates SEO-001 only; its artifact mismatch is resolved.

| ID | Priority | Effort | Status | Labels | In backlog | Title | File |
|---|---|---|---|---|---|---|---|
| SEO-001 | P3 residual | S | VERIFIED 0.3.0 artifact/metadata match; HEAD 404 remains | bug | yes | Android 0.3.0 artifact verified; remaining download HEAD returns 404 | [SEO-001.md](SEO-001.md) |
| SEO-002 | P1 | S | VERIFIED | bug | yes | The 171 KB logo (PNG inside SVG) loads on every page and is shown at 44 px | [SEO-002.md](SEO-002.md) |
| SEO-003 | P1 | S | VERIFIED | bug | yes | /shelf loads three 2560×1928 example photos (2.26 MB) at first paint; lab LCP 15–16 s | [SEO-003.md](SEO-003.md) |
| SEO-020 | P1 | S | REQUIRES VERIFICATION | enhancement | no | Confirm chtozavino.ru in Yandex Webmaster and Google Search Console; submit the sitemap | [SEO-020.md](SEO-020.md) |
| SEO-004 | P2 | S | VERIFIED | enhancement | yes | Lazy-load result-only components on / and /shelf (WineExperiences, WineAlternatives) | [SEO-004.md](SEO-004.md) |
| SEO-005 | P2 | S | VERIFIED (edge layer LIKELY) | bug | yes | /presentation is in sitemap.xml but the edge sends X-Robots-Tag: noindex | [SEO-005.md](SEO-005.md) |
| SEO-006 | P2 | S | VERIFIED | bug | yes | Unknown producer map /lineup/<id> returns 200 instead of 404 | [SEO-006.md](SEO-006.md) |
| SEO-008 | P2 | S | VERIFIED | bug | yes | /dish sends the home page link preview (og:url, og:title, og:description) | [SEO-008.md](SEO-008.md) |
| SEO-009 | P2 | S | VERIFIED | bug | yes | /shelf repeats the home page H1 «Найти вино по фото» | [SEO-009.md](SEO-009.md) |
| SEO-010 | P2 | M | VERIFIED (owner decision needed) | question, enhancement | yes | Decide: index the reviewed producer maps /lineup/<producer> or enrich /lineup | [SEO-010.md](SEO-010.md) |
| SEO-011 | P2 | M | VERIFIED | enhancement | yes | Home page: add a short server-rendered section «Как определить вино по фото этикетки» | [SEO-011.md](SEO-011.md) |
| SEO-012 | P2 | S | VERIFIED | bug | yes | Release main: /shelf-lens returns 404 on production | [SEO-012.md](SEO-012.md) |
| SEO-013 | P2 | S | VERIFIED | enhancement | yes | Add a post-deploy SEO HTTP check; fix stale assertions in check-contract.mjs | [SEO-013.md](SEO-013.md) |
| SEO-016 | P2 | S | VERIFIED presence, LIKELY impact | enhancement | yes | Exclude the 18+ age-gate text from search snippets (data-nosnippet, Yandex <noindex>) | [SEO-016.md](SEO-016.md) |
| SEO-017 | P2 | M | REQUIRES VERIFICATION | enhancement | yes | Get a field Core Web Vitals baseline (LCP, INP, CLS) before more performance work | [SEO-017.md](SEO-017.md) |
| SEO-018 | P2 | M | REQUIRES VERIFICATION (legal/editorial) | question | yes | Russian alcohol-advertising review of public copy before widening SEO content | [SEO-018.md](SEO-018.md) |
| SEO-019 | P2 | S | VERIFIED | bug | no | Global canonical and og:url point to the home page on every page without an override | [SEO-019.md](SEO-019.md) |
| SEO-021 | P2 | S | VERIFIED | enhancement | no | Preload the LCP background image /reference/background.webp | [SEO-021.md](SEO-021.md) |
| SEO-022 | P2 | S | VERIFIED (edge layer LIKELY) | bug | no | /favicon.ico returns 78 bytes of text with Content-Type image/x-icon | [SEO-022.md](SEO-022.md) |
| SEO-031 | P2 | S | VERIFIED in source, not observed on production | bug | no | /shelf server HTML says «временно недоступен» when the recognition upstream is down; 2 s health check per SSR request | [SEO-031.md](SEO-031.md) |
| SEO-014 | P3 | S | VERIFIED | enhancement | yes | Optional URL normalization: trailing slash, upper case, UTM (Clean-param), single-hop http://www redirect | [SEO-014.md](SEO-014.md) |
| SEO-015 | P3 | S | VERIFIED | enhancement | yes | JSON-LD: keep WebSite/WebApplication on the home page only; use «Что за вино?» as the site name | [SEO-015.md](SEO-015.md) |
| SEO-023 | P3 | S | VERIFIED | bug | no | Replace the default English Nuxt 404 page with a Russian error page | [SEO-023.md](SEO-023.md) |
| SEO-024 | P3 | S | VERIFIED | enhancement | no | Add Cache-Control to static image folders (icons, line-wines, product-line-maps, …) | [SEO-024.md](SEO-024.md) |
| SEO-025 | P3 | S | VERIFIED | enhancement | no | Make the Telegram and MAX bot landing pages less similar | [SEO-025.md](SEO-025.md) |
| SEO-026 | P3 | S | VERIFIED | enhancement | no | Link /lineup, the bots and the games from the home page or footer | [SEO-026.md](SEO-026.md) |
| SEO-027 | P3 | S | VERIFIED | enhancement | no | Social preview: use a 1200×630 og:image instead of the square app icon | [SEO-027.md](SEO-027.md) |
| SEO-028 | P3 | M | VERIFIED | enhancement | no | /lineup: use card-size cover images (954 KiB oversize) | [SEO-028.md](SEO-028.md) |
| SEO-029 | P3 | S | VERIFIED | enhancement | no | Optional: accurate lastmod in sitemap.xml and Last-Modified/ETag on HTML | [SEO-029.md](SEO-029.md) |
| SEO-030 | P3 | S | VERIFIED | enhancement | no | Titles: use the label-recognition and pairing query wording | [SEO-030.md](SEO-030.md) |
