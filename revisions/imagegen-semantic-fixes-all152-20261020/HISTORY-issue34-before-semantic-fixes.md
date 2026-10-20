<!-- issue-34-imagegen-all152-current-20261020 -->
## Additional current-code comparison: 152 generated scenes

**All 152 selected originals were tested with scene-v1, semantic-v2 and DIS: 456 fresh outputs, 456 crops.** [Review every original, proposed target/mask and selector crop](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/0127f6a867a40a60112a45ade58122a7713d26e1/revisions/imagegen-all152-current-20261020/README.md) · [Explicit scene-v1 failure flags](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/0127f6a867a40a60112a45ade58122a7713d26e1/revisions/imagegen-all152-current-20261020/SCENE-V1-FAILURES.md) · [semantic-v2 failure flags](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/0127f6a867a40a60112a45ade58122a7713d26e1/revisions/imagegen-all152-current-20261020/SEMANTIC-V2-FAILURES.md) · [Pinned source/configuration](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/0127f6a867a40a60112a45ade58122a7713d26e1/revisions/imagegen-all152-current-20261020/protocol.json).

These are separate development cohorts. Fifty scenes have persisted scene approval; 102 scenes, including GP11 and SP01, remain exploratory. **All mask shapes/owners are pending review. No confirmed mask accuracy or crop-usability score is claimed.**

| Provisional cohort | scene-v1 target agreement | semantic-v2 target agreement | DIS |
|---|---:|---:|---|
| 50 scene-confirmed, masks pending | 39/50 | 41/50 | No native target ID |
| 102 pending scenes, exploratory | 79/102 | 81/102 | No native target ID |

Across 152 unique originals, target agreement is 118/152 for scene-v1 and 122/152 for semantic-v2. Isolation proxies are satisfied in **119/152 scene-v1, 105/152 semantic-v2 and 17/152 DIS** outputs. Target agreement does not establish a useful crop. The selected-label audit finds **six partially retained proposal masks across five cases**; these remain unresolved, with shapes and ownership unreviewed. [Exact label audit](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/0127f6a867a40a60112a45ade58122a7713d26e1/revisions/imagegen-all152-current-20261020/selected-label-mask-audit.json).

**109 relevant regression tests pass** on the pinned runtime. All 12,006 source-dataset files and historical reports are unchanged. The original 100 diverse-case records/hashes are unchanged after adding GP11/SP01. Exact duplicates are not counted twice; GP02 and its AGORA edit GP11 share one scene group. These generated development images do not establish independent real-world accuracy. [Verification](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/0127f6a867a40a60112a45ade58122a7713d26e1/revisions/imagegen-all152-current-20261020/verification.json) · [Deduplication](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/0127f6a867a40a60112a45ade58122a7713d26e1/revisions/imagegen-all152-current-20261020/deduplication.json).

SAM3-based selectors were rerun on frozen review proposals; optional live detector/tracker recovery was not exercised. DIS ran fresh on the original RGB images with its pinned CPU model. The preceding 50 images reproduce the exact saved crops. The fallback and label-crop functions are unchanged. All 152 case pages include source images, every mask proposal and all three crops directly on GitHub.


<!-- issue-34-localization-fixes-20261020 -->
## Frozen localization comparison · 20 October 2026

**Seven of the eight original localization mismatches were fixed in this frozen run. `real-117719` remains an unresolved quality failure and annotation conflict; this issue stays open.**

[Current 216-case gallery](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/a07057a6401deb76d85c8da2ecd98182a3d5b56b/revisions/localization-fixes-20261020/README.md) · [All eight investigated cases](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/a07057a6401deb76d85c8da2ecd98182a3d5b56b/revisions/localization-fixes-20261020/INVESTIGATION.md) · [Explicit scene-v1 failure index](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/a07057a6401deb76d85c8da2ecd98182a3d5b56b/revisions/localization-fixes-20261020/SCENE-V1-FAILURES.md) · [Before/after comparison](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/a07057a6401deb76d85c8da2ecd98182a3d5b56b/revisions/localization-fixes-20261020/evidence/revision-diff.json) · [452-test receipt](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/a07057a6401deb76d85c8da2ecd98182a3d5b56b/revisions/localization-fixes-20261020/evidence/receipt.json) · [Source patch](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/a07057a6401deb76d85c8da2ecd98182a3d5b56b/revisions/localization-fixes-20261020/implementation.patch).

- **Fixed `hc-025`, `hc-035`, `hc-039`, `hc-041`, `hc-056`:** a stable narrow neck and visible broad body support a conservative bilateral outline fit. It only expands small horizontal bbox asymmetries; it does not consult the photo center or other candidates. The original exact fallback ordering is unchanged.
- **Fixed `real-166918`:** a fixed central 160px PNG scan recovers the previously missed tiny bottle. Crop-edge fragments are rejected unless there is enough interior context. Requests contain RGB and English bottle nouns, never GT.
- **Fixed `real-397354`:** detector-seeded interactive masks are filtered for overlap and bounded displacement before predicted-quality ranking. The usable localization changes the exact distance ordering. The crop retains the original detector rectangle so paper is preserved.
- **Still FAIL `real-117719`:** semantic-v2 returns a dark **20 × 24 px** bottle fragment; scene-v1 returns an overexposed **27 × 58 px** crop. Neither provides a readable label, and the scene has no clear intended bottle. This remains an unresolved product-quality failure. Incomplete frozen annotations also conflict with exact center fallback; that conflict does not establish a good result. Frozen targets and fallback stay unchanged. [Original photo, masks and both crops](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/a07057a6401deb76d85c8da2ecd98182a3d5b56b/revisions/localization-fixes-20261020/cases/real-117719.md).

**Validation:** 452 matcher tests pass, including 12 new regression methods. All 369/369 semantic outputs return crops; all 298/298 selected-subject label checks retain 100%. All 1,424 robustness probes return crops and retain 100% of selected labels, with no new intent/label regressions. The report checks 480 filter scopes and 4,646 image assets; Chrome verifies the corrected cards and the remaining FAIL.

| Separate development cohort | Before semantic-v2 | Revised | scene-v1, shared enhanced inputs |
|---|---:|---:|---:|
| Live policy target + required fallback | 30/38 | **37/38** | 20/38 target ID |
| Live passive intent | 112/112 | 112/112 | 98/112 |
| Live explicit interaction | 14/14 | 14/14 | 6/14 |
| Controlled policy target + fallback | 33/33 | 33/33 | 20/33 target ID |
| Rule fixtures | 50/50 | 50/50 | Contract N/A |

All 319 original primary caches, frozen targets, GT masks and previous reports are byte-identical. Eight enhancement records are separately hashed, shared by both algorithms. The fallback and assignment-scoring ASTs are unchanged. The preceding implementation fails the seven new regression replays. All 99 new RGB-only diagnostic responses, including rejected box/edge/mirror/grid proposals, are retained. This is correlated development coverage, not independent accuracy. The variant remains optional; no production rollout is included.


## Original requirements and historical revisions

The earlier functionality description, examples and revision notes are preserved verbatim in the [dated historical issue body](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/45ecdcb8cde6fcd5581bdf97e4b0dda1af30edd9/history/issue-34-before-localization-20261020.md). Earlier discussion comments and immutable comparison galleries remain available. Each comparison is pinned to its own source revision and inputs; the generated-scene comparison is a separate development cohort.
