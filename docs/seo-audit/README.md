# SEO audit of chtozavino.ru

Audit date: **20 October 2026**. Market: Russia; language: Russian; engines: Google and Yandex. Source baseline: `cd8b063ecd000872567e543407b11926b45b3d37`. Source counts/line citations use that baseline unless marked as a later observation; [concurrent local changes](claude-review.md#concurrent-workspace-follow-up) are recorded separately.

**Follow-up:** [review of Claude's parallel findings](claude-review.md). All 15 original Lighthouse reports were found and checked against his summary. That adds laboratory evidence, a confirmed invalid favicon, directory-image/caching opportunities and a correction to the hackathon recommendation below. Field CWV remains unavailable.

**APK follow-up:** [0.3.0 independently verified](android-030-verification.md): full file size/SHA-256, embedded version/code/package, certificate fingerprint, production copy and JSON-LD agree. The previous artifact mismatch is resolved. HEAD 404 remains P3/S.

**Current execution priority:** [Pareto plan](pareto-priorities.md). Five open first-wave IDs remain: shared logo, shelf images, directory covers, shelf H1 and useful home/shelf SSR copy. Run bounded account/crawler checks alongside them; do not backfill the resolved APK package automatically. This is qualitative prioritization, not a forecast of an 80% SEO gain.

Production has a sound discovery foundation: SSR content, real navigation links, 16 sitemap URLs returning 200, distinct titles/descriptions and route canonicals. No sitewide indexing outage or field Core Web Vitals failure was established. Immediate work concerns avoidable image loading, useful task explanations and inconsistent indexing directives across the sitemap/application/edge. The current Android 0.3.0 artifact contract is verified. Producer details are intentionally noindex; expanding their search reach needs an editorial/product and Russian-law decision.

**Status after the audit (source, not production):** SEO-002 is fixed on `main` in `efee5427`. The shared logo SVG is a 2,810-byte vector. The live site changes after the next Web UI release.

## Scope, confidence and evidence

Source is Nuxt 4.5.2 / Vue 3.5.40 with file-based routes and Nitro Node SSR. Production checks around 17:28–17:36 UTC (20:28–20:36 MSK) include 41 primary HTTP observations, all 16 live XML entries, 53 build/static-resource GETs, 33 additional internal-link HEADs, 53 image HEADs and representative browser renders. Exact timestamps/methods are retained below. This is a bounded audit, not a crawl of every possible URL/catalogue item.

| ID | Artifact | Evidence |
|---|---|---|
| E01 | [http-pages.json](evidence/http-pages.json) | URL/status/safe headers/metadata/headings/links/JSON-LD/HTML hashes; filter requests by URL and variant |
| E02 | [resources.json](evidence/resources.json) | Decoded/transferred bytes, cache policies, preload relationships, link HEADs, five timings and PageSpeed failures |
| E03 | [supplementary-probes.json](evidence/supplementary-probes.json) | Image status/sizes, bounded APK GET, game-host sample and followed redirect |
| E04 | [browser.json](evidence/browser.json) | Rendered metadata/headings, client navigation and actual viewport dimensions |
| E05 | [provenance.json](evidence/provenance.json) | Revision, methods, scope and limits |
| E06 | [Claude Lighthouse validated excerpts](evidence/claude-lighthouse-validated.json) | Original hashes, settings, warnings and audited metrics from 15 supplied LHR reports; no independent rerun |
| E07 | [Claude review HTTP checks](evidence/claude-review-http.json) | Fresh favicon/HTML-error/account/cache observations |
| E08 | [Nitro favicon provenance](evidence/nitro-favicon-provenance.json) | Published dependency integrity and exact fallback source; [excerpt](evidence/nitro-favicon-source.txt) |
| E09 | [Hackathon policy follow-up](evidence/hackathon-policy-followup.json) | Three fresh GETs distinguish new local indexability edits from still-excluded production |
| E10 | [Android 0.3.0 verification](evidence/android-030-verification.json) | Complete production APK hash/version/package/certificate comparison with pinned main contract; original mismatch resolved, HEAD 404 remains |
| E11 | [Next-task state](evidence/next-task-state.json) | Fresh logo/shelf GETs: local 2,810-byte vector candidate, production still old logo/original shelf images/shared H1 |

**VERIFIED** means directly observed in the named production/source evidence. **LIKELY** means a supported inference needing confirmation. **REQUIRES VERIFICATION** identifies missing account/metric/artifact/crawler/legal evidence. Confidence is separate from kind: defects, optimizations, intentional policy, source/production drift and verification tasks are distinguished. Resource bytes do not prove ranking loss; HTTP 200 does not prove indexing.

P0 = widespread established outage/blocker (none found); P1 = immediate high-value work; P2 = next cycle; P3 = optional cleanup. Effort S ≈ up to one engineer-day; M ≈ 2–5 days; L >5 days, planning estimates only.

## Ten most important findings

| ID | Finding and practical implication |
|---|---|
| SEO-028 | **VERIFIED optimization:** directory card covers reuse larger artwork; both supplied runs estimate 976,413 wasted image bytes. Preserve frame geometry with derivatives. |
| SEO-002 | **VERIFIED production optimization, local candidate prepared:** live logo remains 171,311 decoded / 155,135 gzip bytes; concurrent local vector is 2,810 bytes. Review/release verification pending (E11). |
| SEO-003 | **VERIFIED optimization:** shelf thumbnails reuse original photographs; three originals total 2,313,438 bytes. Claude's validated lab runs record approximately 2.98 MB total transfer and simulated mobile LCP 15.0–15.9 s; field/before-after impact remains unmeasured. |
| SEO-004 | **VERIFIED payload / LIKELY opportunity:** home preloads 579,043 decoded JS bytes, including result/producer logic before a result exists. |
| SEO-005 | **VERIFIED defect:** presentation is in XML but receives an edge noindex header. |
| SEO-010 | **VERIFIED intentional constraint:** all 25 linked producer detail HEADs have noindex; two GETs confirm meta/header. A reviewed subset is a conditional content opportunity. |
| SEO-008 | **VERIFIED defect:** dish OG/Twitter identity points to home despite correct ordinary metadata/canonical. |
| SEO-009 | **VERIFIED content weakness:** shelf H1 repeats bottle-search H1 instead of identifying the shelf task. |
| SEO-006 | **VERIFIED status defect:** an unknown producer returns 200 with a missing-map message; current noindex mitigates the risk. |
| Claude SEO-022 | **VERIFIED defect:** `/favicon.ico` returns 78 ASCII data-URI bytes instead of an icon. The exact fallback exists in locked Nitro 2.13.4; add a real public asset. Existing linked SVG remains valid. |

Full developer tasks, source locations, side effects and acceptance procedures: [remediation-backlog.md](remediation-backlog.md).

SEO-007 was an accepted baseline policy: robots prevents fetching hackathon/noindex, explicitly requested in `webui/ResearchLog.md:949–957` at the baseline. New concurrent local edits record an owner-requested reversal; production still excludes the page at 18:26 UTC. Respect the newer local intent and verify its release separately. The original block was not an accidental defect.

## Deliverables

1. [technical-audit.md](technical-audit.md): framework, URL/source map, rendering/crawling/directives/schema and tests.
2. [on-page-audit.md](on-page-audit.md): actual metadata for all sitemap pages, Russian intent clusters and content/legal briefs.
3. [performance-audit.md](performance-audit.md): measured resource/timing data and specific loading fixes.
4. [deployment-audit.md](deployment-audit.md): Caddy/systemd/CI/container evidence, environment differences and APK root cause.
5. [remediation-backlog.md](remediation-backlog.md): detailed defects/opportunities/verification tasks, ordered by the current Pareto plan.
6. [seo-roadmap.md](seo-roadmap.md): 30/60/90-day implementation and measurement gates.

[claude-review.md](claude-review.md) reviews the additional issue drafts and distinguishes confirmed additions from optional or unsupported recommendations.

[pareto-priorities.md](pareto-priorities.md) gives the four remaining delivery packages and assigns all 30 drafts, including SEO-001 as core resolved/HEAD follow-up. [android-030-verification.md](android-030-verification.md) records the new release checks and limits.

The request named both `docs/set/` and `docs/seo-audit/`. This directory follows the explicit documentation-only permission in the mandatory rules. No duplicate report tree was created.

## Verification limits and workspace handling

No Search Console, Yandex Webmaster, analytics, crawler logs, CDN dashboard or running-server access was available. Rankings, volumes, selected engine canonicals, actual index coverage, verified-bot access and regional settings remain unknown. User-Agent tests do not authenticate crawlers.

Both PageSpeed API calls returned 429. The follow-up validated Claude's 15 original lab reports; their simulated LCP/CLS/scores are now reported separately from field metrics. No field LCP/INP/CLS result is available. My requested 390px browser viewport exposed 520 CSS px; Claude's provided headless configuration is 412px. Neither replaces real 360/390px phone checks.

My browser session already had age confirmation. I did not inspect/alter its storage/cookies or submit age confirmation. Claude's provided first-visit screenshot confirms the visible gate at the lab viewport; verified search-engine rendering still requires account checks. The browser skill explicitly prohibits “complete age-verification” on the user's behalf: [browser SKILL.md](</Users/ashmelev/.codex/plugins/cache/openai-bundled/browser/26.727.51351/skills/control-in-app-browser/SKILL.md>).

The deployment runbook records `09403930…`, not independent proof of the current running commit. Baseline source has 17 XML entries and Shelf Lens links; live XML has 16 and Shelf Lens returns 404. New concurrent local hackathon edits raise the local XML count to 18. These are source/release differences, not broken live sitemap entries. The initial audit did not download the APK. The later 0.3.0 check downloaded and hashed the full public file and inspected its manifest/certificate, without installation; see E10. Actual environment/credential files were not opened.

Concurrent report versions were preserved at `/tmp/chto-seo-concurrent-drafts/`. Their lab claims were initially held pending underlying reports; the follow-up found and validated those reports. See E06–E08 and the parallel-review document for the updated conclusions. Original E01–E05 evidence remains unchanged apart from appended provenance notes.

This audit/review changed only documentation/evidence. It made no application/build/dependency or production changes, inference/upload/account operation, deployment or commit. Other concurrent workspace changes were observed and left untouched; temporary audit scripts/evidence stayed under `/tmp`.
