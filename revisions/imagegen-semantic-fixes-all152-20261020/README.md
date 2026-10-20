# Current three-selector comparison: 152 generated scenes

**All 456 outputs return a crop. No human-approved mask accuracy or crop-usability score is claimed.**

**The complete matcher regression suite passes on the pinned source.** [Test log](regression-tests.log) · [Artifact verification](verification.json) · [Browser checks](browser-verification.json). Verification means that the evidence is complete and unchanged; it does not mark every selection successful.

Fresh scene-v1 and semantic-v2 replays use identical frozen primary proposals plus fixed RGB-only auxiliary context masks; original primary proposal order and IDs are unchanged. DIS runs fresh on every original using its pinned CPU model. The 152 auxiliary detector requests were made without targets or annotations; this is a detector-plus-selector update. No tracker or central recovery is exercised in this comparison.

Implementation revision: `2026-10-20-imagegen-selection-isolation-and-label-bounds`. Exact bytes and configuration: [protocol](protocol.json), [runtime](runtime/matcher), [contract preservation](contract-preservation.json).

The first 50 scenes have persisted scene approval, with masks pending. The other 102 are exploratory pending scenes, including GP11 and SP01. Scene approvals do not approve masks. Targets, proposal shapes and owners remain unreviewed geometry.

All 152 source hashes are unique. GP02 and its reference-image edit GP11 share a scene group; no independent train/test split is claimed. The first 50 images were already used in development. Rejected, blocked and canceled attempts remain provenance only.

A target-ID match does not establish a useful crop. Retention and isolation below are diagnostic mask proxies. Label completeness, ownership, legibility and crop usefulness require human review for all 456 outputs. **No flag means only that these automatic checks found no failure.**

| Cohort | Selector | Images | Target agreement | Isolation proxy satisfied |
|---|---|---:|---:|---:|
| All unique sources (development) | scene-v1 | 152 | 118/152 | 119/152 |
| All unique sources (development) | semantic-v2 | 152 | 152/152 | 152/152 |
| All unique sources (development) | dis-v1 | 152 | n/a | 17/152 |
| 50 scene-confirmed; masks pending | scene-v1 | 50 | 39/50 | 39/50 |
| 50 scene-confirmed; masks pending | semantic-v2 | 50 | 50/50 | 50/50 |
| 50 scene-confirmed; masks pending | dis-v1 | 50 | n/a | 6/50 |
| 102 pending scenes; exploratory | scene-v1 | 102 | 79/102 | 80/102 |
| 102 pending scenes; exploratory | semantic-v2 | 102 | 102/102 | 102/102 |
| 102 pending scenes; exploratory | dis-v1 | 102 | n/a | 11/102 |

## Change from the preserved baseline

| Selector | Baseline target agreement | Current target agreement | Baseline isolation proxy | Current isolation proxy |
|---|---:|---:|---:|---:|
| scene-v1 | 118/152 | 118/152 | 119/152 | 119/152 |
| semantic-v2 | 122/152 | 152/152 | 105/152 | 152/152 |
| DIS | N/A | N/A | 17/152 | 17/152 |

There are 30 corrected semantic target disagreements, 47 corrected isolation failures, and zero regressions against the baseline. All 152 scene-v1 crops and all 152 fresh DIS crops reproduce their baseline bytes. The selector and fixed RGB-only auxiliary detector evidence changed together; this is not a ranker-only ablation. [Exact before/after](baseline-diff.json).

The attached-label audit changes from 232 proposals (226 complete, six partial) to 174 proposals (174 complete). Background shelf paper no longer inherits the foreground owner. Every returned attached mask is preserved in full, including outlying pixels; all source proposal masks remain available. This does not approve true label ownership, completeness or legibility.

[Functionality and safeguards](FUNCTIONALITY.md) · [Source patch](implementation.patch) · [Frozen fallback/target/scorer checks](contract-preservation.json) · [Test/source hashes](test-verification.json).

The separate **real-117719 quality case remains unresolved**. On its exact frozen enhanced input, semantic-v2 keeps selected ID `d96` and `fallback_center_contains`, and returns original 640 × 425 px context instead of the historical 20 × 24 px fragment. No readable label or clear intended bottle is claimed. [Before/after original and crops](supplementary/real-117719/README.md).

## Review every case

The selected-label audit checks 174 semantic-v2 attached label masks: 174 fully retained, 0 partially retained. The exact attached-label set changes when background shelf paper receives a different owner. Every returned attached mask is audited in full, including outlying pixels. This is not a human label-completeness score. [Exact audit](selected-label-mask-audit.json).

FAIL below means a disagreement with a target proposal or a failed isolation/label-retention proxy. Pending scenes remain provisional. Each page contains original RGB, proposed target overlay, every mask, all three selector crops and exact decisions.

| Case | Annotation cohort | scene-v1 | semantic-v2 | DIS isolation proxy |
|---|---|---|---|---|
| [pilot-v1:FG01](cases/pilot-v1--FG01.md) | Scene confirmed; masks pending | No flag | No flag | Failure |
| [pilot-v1:FG02](cases/pilot-v1--FG02.md) | Scene confirmed; masks pending | No flag | No flag | Failure |
| [pilot-v1:FG03](cases/pilot-v1--FG03.md) | Scene confirmed; masks pending | No flag | No flag | Failure |
| [pilot-v1:FG04](cases/pilot-v1--FG04.md) | Scene confirmed; masks pending | No flag | No flag | Failure |
| [pilot-v1:FG05](cases/pilot-v1--FG05.md) | Scene confirmed; masks pending | No flag | No flag | Failure |
| [pilot-v1:HA01](cases/pilot-v1--HA01.md) | Scene confirmed; masks pending | No flag | No flag | Failure |
| [pilot-v1:HA02](cases/pilot-v1--HA02.md) | Scene confirmed; masks pending | **FAIL** | No flag | Failure |
| [pilot-v1:HA03](cases/pilot-v1--HA03.md) | Scene confirmed; masks pending | No flag | No flag | Failure |
| [pilot-v1:HA04](cases/pilot-v1--HA04.md) | Scene confirmed; masks pending | **FAIL** | No flag | Failure |
| [pilot-v1:HA05](cases/pilot-v1--HA05.md) | Scene confirmed; masks pending | **FAIL** | No flag | Failure |
| [pilot-v1:LA01](cases/pilot-v1--LA01.md) | Scene confirmed; masks pending | **FAIL** | No flag | Failure |
| [pilot-v1:LA02](cases/pilot-v1--LA02.md) | Scene confirmed; masks pending | No flag | No flag | Satisfied |
| [pilot-v1:LA03](cases/pilot-v1--LA03.md) | Scene confirmed; masks pending | No flag | No flag | Satisfied |
| [pilot-v1:LA04](cases/pilot-v1--LA04.md) | Scene confirmed; masks pending | No flag | No flag | Satisfied |
| [pilot-v1:LA05](cases/pilot-v1--LA05.md) | Scene confirmed; masks pending | No flag | No flag | Failure |
| [pilot-v1:OW01](cases/pilot-v1--OW01.md) | Scene confirmed; masks pending | **FAIL** | No flag | Failure |
| [pilot-v1:OW02](cases/pilot-v1--OW02.md) | Scene confirmed; masks pending | **FAIL** | No flag | Failure |
| [pilot-v1:OW03](cases/pilot-v1--OW03.md) | Scene confirmed; masks pending | **FAIL** | No flag | Failure |
| [pilot-v1:OW04](cases/pilot-v1--OW04.md) | Scene confirmed; masks pending | No flag | No flag | Failure |
| [pilot-v1:OW05](cases/pilot-v1--OW05.md) | Scene confirmed; masks pending | No flag | No flag | Satisfied |
| [pilot-v1:VI01](cases/pilot-v1--VI01.md) | Scene confirmed; masks pending | **FAIL** | No flag | Failure |
| [pilot-v1:VI02](cases/pilot-v1--VI02.md) | Scene confirmed; masks pending | No flag | No flag | Failure |
| [pilot-v1:VI03](cases/pilot-v1--VI03.md) | Scene confirmed; masks pending | No flag | No flag | Failure |
| [pilot-v1:VI04](cases/pilot-v1--VI04.md) | Scene confirmed; masks pending | No flag | No flag | Failure |
| [pilot-v1:VI05](cases/pilot-v1--VI05.md) | Scene confirmed; masks pending | No flag | No flag | Failure |
| [pilot-v1:AM01](cases/pilot-v1--AM01.md) | Scene confirmed; masks pending | **FAIL** | No flag | Failure |
| [pilot-v1:AM02](cases/pilot-v1--AM02.md) | Scene confirmed; masks pending | No flag | No flag | Failure |
| [pilot-v1:AM03](cases/pilot-v1--AM03.md) | Scene confirmed; masks pending | No flag | No flag | Failure |
| [pilot-v1:AM04](cases/pilot-v1--AM04.md) | Scene confirmed; masks pending | No flag | No flag | Failure |
| [pilot-v1:AM05](cases/pilot-v1--AM05.md) | Scene confirmed; masks pending | No flag | No flag | Failure |
| [hardcases-v2:PT01](cases/hardcases-v2--PT01.md) | Scene confirmed; masks pending | **FAIL** | No flag | Failure |
| [hardcases-v2:PT02](cases/hardcases-v2--PT02.md) | Scene confirmed; masks pending | No flag | No flag | Failure |
| [hardcases-v2:PT03](cases/hardcases-v2--PT03.md) | Scene confirmed; masks pending | **FAIL** | No flag | Failure |
| [hardcases-v2:PT04](cases/hardcases-v2--PT04.md) | Scene confirmed; masks pending | **FAIL** | No flag | Failure |
| [hardcases-v2:DP01](cases/hardcases-v2--DP01.md) | Scene confirmed; masks pending | No flag | No flag | Failure |
| [hardcases-v2:DP02](cases/hardcases-v2--DP02.md) | Scene confirmed; masks pending | **FAIL** | No flag | Failure |
| [hardcases-v2:DP03](cases/hardcases-v2--DP03.md) | Scene confirmed; masks pending | No flag | No flag | Failure |
| [hardcases-v2:DP04](cases/hardcases-v2--DP04.md) | Scene confirmed; masks pending | **FAIL** | No flag | Failure |
| [hardcases-v2:GL01](cases/hardcases-v2--GL01.md) | Scene confirmed; masks pending | No flag | No flag | Failure |
| [hardcases-v2:GL02](cases/hardcases-v2--GL02.md) | Scene confirmed; masks pending | No flag | No flag | Failure |
| [hardcases-v2:GL03](cases/hardcases-v2--GL03.md) | Scene confirmed; masks pending | No flag | No flag | Failure |
| [hardcases-v2:GL04](cases/hardcases-v2--GL04.md) | Scene confirmed; masks pending | No flag | No flag | Failure |
| [hardcases-v2:DK01](cases/hardcases-v2--DK01.md) | Scene confirmed; masks pending | No flag | No flag | Failure |
| [hardcases-v2:DK02](cases/hardcases-v2--DK02.md) | Scene confirmed; masks pending | No flag | No flag | Failure |
| [hardcases-v2:DK03](cases/hardcases-v2--DK03.md) | Scene confirmed; masks pending | **FAIL** | No flag | Failure |
| [hardcases-v2:DK04](cases/hardcases-v2--DK04.md) | Scene confirmed; masks pending | No flag | No flag | Satisfied |
| [hardcases-v2:BG01](cases/hardcases-v2--BG01.md) | Scene confirmed; masks pending | **FAIL** | No flag | Failure |
| [hardcases-v2:BG02](cases/hardcases-v2--BG02.md) | Scene confirmed; masks pending | No flag | No flag | Failure |
| [hardcases-v2:BG03](cases/hardcases-v2--BG03.md) | Scene confirmed; masks pending | No flag | No flag | Failure |
| [hardcases-v2:BG04](cases/hardcases-v2--BG04.md) | Scene confirmed; masks pending | No flag | No flag | Failure |
| [diverse-v3:PN01](cases/diverse-v3--PN01.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:PN02](cases/diverse-v3--PN02.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:PN03](cases/diverse-v3--PN03.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:PN04](cases/diverse-v3--PN04.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:PN05](cases/diverse-v3--PN05.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:PN06](cases/diverse-v3--PN06.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:PN07](cases/diverse-v3--PN07.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:PN08](cases/diverse-v3--PN08.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:PN09](cases/diverse-v3--PN09.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:PN10](cases/diverse-v3--PN10.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:HP01](cases/diverse-v3--HP01.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:HP02](cases/diverse-v3--HP02.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:HP03](cases/diverse-v3--HP03.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:HP04](cases/diverse-v3--HP04.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:HP05](cases/diverse-v3--HP05.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:HP06](cases/diverse-v3--HP06.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:HP07](cases/diverse-v3--HP07.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:HP08](cases/diverse-v3--HP08.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:HP09](cases/diverse-v3--HP09.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:HP10](cases/diverse-v3--HP10.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:GP01](cases/diverse-v3--GP01.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:GP02](cases/diverse-v3--GP02.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:GP03](cases/diverse-v3--GP03.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:GP04](cases/diverse-v3--GP04.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:GP05](cases/diverse-v3--GP05.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:GP06](cases/diverse-v3--GP06.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:GP07](cases/diverse-v3--GP07.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:GP08](cases/diverse-v3--GP08.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:GP09](cases/diverse-v3--GP09.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:GP10](cases/diverse-v3--GP10.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:PD01](cases/diverse-v3--PD01.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:PD02](cases/diverse-v3--PD02.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:PD03](cases/diverse-v3--PD03.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:PD04](cases/diverse-v3--PD04.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:PD05](cases/diverse-v3--PD05.md) | Scene and masks pending — exploratory | No flag | No flag | Satisfied |
| [diverse-v3:PD06](cases/diverse-v3--PD06.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:PD07](cases/diverse-v3--PD07.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:PD08](cases/diverse-v3--PD08.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:PD09](cases/diverse-v3--PD09.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:PD10](cases/diverse-v3--PD10.md) | Scene and masks pending — exploratory | No flag | No flag | Satisfied |
| [diverse-v3:WP01](cases/diverse-v3--WP01.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:WP02](cases/diverse-v3--WP02.md) | Scene and masks pending — exploratory | No flag | No flag | Satisfied |
| [diverse-v3:WP03](cases/diverse-v3--WP03.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:WP04](cases/diverse-v3--WP04.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:WP05](cases/diverse-v3--WP05.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:WP06](cases/diverse-v3--WP06.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:WP07](cases/diverse-v3--WP07.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:WP08](cases/diverse-v3--WP08.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:WP09](cases/diverse-v3--WP09.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:WP10](cases/diverse-v3--WP10.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:OC01](cases/diverse-v3--OC01.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:OC02](cases/diverse-v3--OC02.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:OC03](cases/diverse-v3--OC03.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:OC04](cases/diverse-v3--OC04.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:OC05](cases/diverse-v3--OC05.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:OC06](cases/diverse-v3--OC06.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:OC07](cases/diverse-v3--OC07.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:OC08](cases/diverse-v3--OC08.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:OC09](cases/diverse-v3--OC09.md) | Scene and masks pending — exploratory | No flag | No flag | Satisfied |
| [diverse-v3:OC10](cases/diverse-v3--OC10.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:LT01](cases/diverse-v3--LT01.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:LT02](cases/diverse-v3--LT02.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:LT03](cases/diverse-v3--LT03.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:LT04](cases/diverse-v3--LT04.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:LT05](cases/diverse-v3--LT05.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:LT06](cases/diverse-v3--LT06.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:LT07](cases/diverse-v3--LT07.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:LT08](cases/diverse-v3--LT08.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:LT09](cases/diverse-v3--LT09.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:LT10](cases/diverse-v3--LT10.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:SZ01](cases/diverse-v3--SZ01.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:SZ02](cases/diverse-v3--SZ02.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Satisfied |
| [diverse-v3:SZ03](cases/diverse-v3--SZ03.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:SZ04](cases/diverse-v3--SZ04.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Satisfied |
| [diverse-v3:SZ05](cases/diverse-v3--SZ05.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:SZ06](cases/diverse-v3--SZ06.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:SZ07](cases/diverse-v3--SZ07.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:SZ08](cases/diverse-v3--SZ08.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Satisfied |
| [diverse-v3:SZ09](cases/diverse-v3--SZ09.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:SZ10](cases/diverse-v3--SZ10.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:LB01](cases/diverse-v3--LB01.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:LB02](cases/diverse-v3--LB02.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:LB03](cases/diverse-v3--LB03.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:LB04](cases/diverse-v3--LB04.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:LB05](cases/diverse-v3--LB05.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:LB06](cases/diverse-v3--LB06.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:LB07](cases/diverse-v3--LB07.md) | Scene and masks pending — exploratory | No flag | No flag | Satisfied |
| [diverse-v3:LB08](cases/diverse-v3--LB08.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:LB09](cases/diverse-v3--LB09.md) | Scene and masks pending — exploratory | No flag | No flag | Satisfied |
| [diverse-v3:LB10](cases/diverse-v3--LB10.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:CT01](cases/diverse-v3--CT01.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:CT02](cases/diverse-v3--CT02.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:CT03](cases/diverse-v3--CT03.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:CT04](cases/diverse-v3--CT04.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:CT05](cases/diverse-v3--CT05.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:CT06](cases/diverse-v3--CT06.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:CT07](cases/diverse-v3--CT07.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:CT08](cases/diverse-v3--CT08.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:CT09](cases/diverse-v3--CT09.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:CT10](cases/diverse-v3--CT10.md) | Scene and masks pending — exploratory | **FAIL** | No flag | Failure |
| [diverse-v3:GP11](cases/diverse-v3--GP11.md) | Scene and masks pending — exploratory | No flag | No flag | Failure |
| [diverse-v3:SP01](cases/diverse-v3--SP01.md) | Scene and masks pending — exploratory | No flag | No flag | Satisfied |

[scene-v1 failure index](SCENE-V1-FAILURES.md) · [semantic-v2 failure index](SEMANTIC-V2-FAILURES.md) · [Interactive local report](report.html) · [CSV](comparison.csv) · [Exact results](results.json) · [Historical prediction differences](historical-comparison.json) · [Pending usability review](crop-usability-review-pending.json)
