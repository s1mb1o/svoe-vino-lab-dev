# 30/60/90-day SEO roadmap

Starts from implementation kickoff, not an assumed deployment date. The [Pareto plan](pareto-priorities.md) controls scope: five open first-wave IDs after verified APK 0.3.0 reconciliation, with bounded checks alongside them. The split is qualitative, not a forecast of 80% growth or 20% of engineering hours. This plan did not execute releases, open accounts or create automations. [Backlog](remediation-backlog.md) contains locations, evidence and tests.

## Days 1–30: deliver the five remaining first-wave tasks

| Timing | Owner | Work | Completion evidence |
|---|---|---|---|
| First | Frontend | SEO-002: small shared display logo | Cold bytes, 1×/2×/theme QA and PWA/reference update checks |
| Next, same image work | Frontend | SEO-003/028: shelf display/thumbnail and directory-card derivatives | Smaller transferred bytes; originals retained for recognition/detail; frame geometry, card fallback and cold mobile/desktop checks |
| First cycle, after copy review | Frontend + editor | SEO-009/011: shelf-specific H1 and concise factual SSR explanations on home/shelf | Useful no-JS text, correct mode H1, factual/legal acceptance and actual 360/390px QA; no new page family |
| Bounded checks alongside delivery | SEO + release | SEO-020/016/017: existing account/coverage/render/metric checks; SEO-013: dated read-only release acceptance | Existing access confirmed or documented unavailable; observations saved without building new telemetry/CI platforms |

Day-30 gate: verify the five remaining scoped first-wave tasks before adding another implementation project. Keep at most two packages active. SEO-001 artifact identity is verified for 0.3.0; do not reserve another first-wave implementation package for it. New explanatory copy uses the existing SEO-018 factual/legal acceptance; broader producer-publication review is not a prerequisite for image-only work. After any separately authorized release, preserve bounded public acceptance and comparable measurements. Missing field data does not stop the measured image work.

## Days 31–60: correct remaining responses and follow measured bottlenecks

| Work | Owner | Acceptance / dependency |
|---|---|---|
| SEO-005/006/008: presentation XML/noindex, missing-producer 404, dish OG | Frontend + SEO | Correct public responses and client navigation; preserve intentional exclusions; no preview-to-ranking claim |
| SEO-001 residual: optional HEAD correctness, P3/S | Frontend/release | GET works and file identity is already verified. HEAD 200 with matching headers/no body; no APK replacement project. |
| SEO-013: harden release acceptance | Release/frontend | Read-only HTTP check and revision/artifact contracts; stale mock checks handled separately; no evaluator calls against production |
| SEO-004: result-only JS split if traces support it | Frontend/performance | Compare fresh post-image waterfall/long tasks; retain SSR and result/offline/accessibility behavior |
| SEO-016/017/020: deepen existing access/coverage/metric checks | SEO/performance | Actual rendered/index evidence and dated metrics/sample limits; no automatic instrumentation project |

Day-60 gate: remaining verified response defects addressed, releases checkable and the next constraint demonstrated. Promote an unexpected confirmed core-page indexing blocker immediately. Investigate SEO-031 health resilience if staging/production timing supports it; source timeout alone is not a measured outage.

## Days 61–90: choose conditional expansion from evidence

| Work | Evidence | Decision / verification |
|---|---|---|
| Query/landing match and SEO-011 follow-up | Real Google/Yandex photo/label/shelf/pairing/apps/bots/producer page-query exports | Choose dish explanations or a genuine guide gap from evidence; no automatic article/page expansion |
| SEO-010/018 or SEO-012, if warranted | Publication/legal decisions and actual demand/product intent | Choose a reviewed producer subset or Shelf Lens release; preserve review exclusions and ship page/media/navigation/XML together |
| Guide index outcomes, only if published | Selected canonicals, crawled/rendered copy, actual exclusions/indexed URLs | Fix demonstrated barriers; no fixed indexing timetable promised |
| Performance outcomes | Field p75 by device if sufficient, otherwise clearly labeled lab traces | Optimize measured LCP/long tasks/shifts; lab data alone is not field compliance |
| Deferred cleanup/experiments | Evidence from the [full tier assignment](pareto-priorities.md#decision-for-all-30-drafts) | Do not schedule by calendar alone; favicon, schema/slash/preload/social/title work needs a concrete benefit or low marginal cost in an existing change |
| Release/publication upkeep | Attested revision, safe HTTP smoke, artifact manifest and edge policy | Every future release traceable; source-only assertions not production proof |

## Baselines and targets

| Measure | Audit baseline | Target / interpretation |
|---|---|---|
| Live XML status | 16/16 GET 200 | All intentionally submitted URLs 200; count can change |
| XML with noindex | 1, presentation | Zero contradictions after policy reconciliation |
| Unique title/description | 16/16 each | Preserve completeness; no needless blanket rewrite |
| Producer exclusions | 25/25 detail HEADs; 2 GET confirmations | Publication state follows review, no arbitrary all-25 indexing target |
| APK 0.3.0 follow-up | 753,111,053 bytes; SHA-256/version/code/package and certificate fingerprint match release record, page and schema | Original mismatch resolved; HEAD 404 remains P3/S. [E10 verification](android-030-verification.md). |
| Shared logo | 155,135 gzip bytes | Proposed ≤10KiB display derivative with QA |
| Shelf originals referenced | 2,313,438 unique bytes | Suitable display/thumbnails; originals only when needed for inference |
| Directory cover sizing | 976,413 estimated wasted bytes in both supplied runs | Appropriate card derivatives; compare actual cold transfer and visual/geometry QA, not guaranteed audit-estimate savings |
| Home JS module preloads | 579,043 decoded / 176,380 transferred | Proposed ≤400KiB decoded, then actual user metrics; excludes SW/prefetch |
| Actual phone width | Browser minimum observed 520px | Recorded 360/390px fresh/returning checks |
| Field CWV/rankings/clicks | Unavailable; Claude laboratory reports now validated separately | Obtain field evidence; do not present simulated lab scores as field p75 or growth forecast |

Future field goals: p75 LCP ≤2.5s, INP ≤200ms, CLS ≤0.1 by device, as documented in the performance report. Record deployment/date/cache/device/sample context. Demand, device mix, concurrent changes and engine recrawl can overlap; avoid claiming causation from one short traffic comparison. A documented no-change-needed outcome is valid for verification tasks.
