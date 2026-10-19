# Issue 34 localization fixes · 20 October 2026

[Tracking issue](https://github.com/s1mb1o/svoe-vino-lab-dev/issues/34)

All **216 cases** from frozen `main-selector-hardcases-v2`: **166 photo inputs** (153 native renders and 13 real photos) and **50 diagnostic geometry fixtures**. Each case has original input pixels, an annotated mask overlay, every available binary mask, both selectors' saved crops and keep masks, and recorded expected results. No local files, custom viewer or downloaded archive is required: open the case links below.

# Localization and small-bottle recovery · 20 October 2026

**Seven of the remaining eight mismatches are fixed. One frozen annotation-set conflict remains scored as a failure.** This is a new version; all prior reports, targets, masks and primary detector responses remain unchanged.

## Changes

**Upright outline localization** resolves `hc-025`, `hc-035`, `hc-039`, `hc-041` and `hc-056`. Small mask asymmetries made nearly identical bottle boxes choose the opposite member of an exact GT tie. A stable narrow neck plus visible broad body now supports a conservative bilateral outline fit. It only expands the box horizontally, by at most max(2 pixels, 5% of its width). The fit uses the bottle mask and image bounds; it never consults the photo center, another candidate or GT. Rectangular, rotated, unstable-neck and substantially amodal inputs retain their geometry. This is detector localization, with the exact fallback function unchanged.

**Small-object recovery** resolves `real-166918`: the original model missed the tiny held bottle. A fixed central 160-pixel crop, sent as PNG to the same project service, recovers it. Only complete interior detections are added; a crop-edge fragment is rejected unless it has max(2 pixels, 5% crop-side) context. English nouns are `wine bottle`, `bottle`, `bottle held in hand`. Source pixels and complete masks are projected back; no target or label text is supplied to the detector.

**Tracker localization** resolves `real-397354`. In small-bottle fallback scenes with two near-equal leading distances, three positive points are derived from each original visible mask and sent to the interactive tracker on a local RGB crop. Implausible masks are filtered for overlap and bounded edge displacement **before** choosing the highest predicted quality. Filtering before ranking ensures that a high-overlap but invalid proposal cannot hide an admissible mask. The accepted geometry changes the exact distance ordering. The original detector rectangle remains in the crop's RGB retention guard, including unseen paper. No pixel-distance epsilon or left preference is added.

The byte adapter shares one original timeout deadline across at most two localizations and one central scan. Optional failure or exhausted time preserves a valid primary crop. Supplied instance lists never trigger inference. Existing empty-input generic recovery remains unchanged. Both algorithms receive exactly the same effective detector inputs in the paired comparison. scene-v1's ranker and target metrics are unchanged; its crop geometry can reflect the shared enhanced inputs.

## Validation

**452 matcher tests pass**, including **12 new regression methods**. The seven new failure replays fail on the preceding implementation/primary-input revision and pass on the declared new selector/enhanced-input revision. All **369/369 semantic results return crops**, and **298/298 selected-subject label checks retain 100% of annotated pixels**. All **1,424 robustness probes** return crops and retain 100% of selected labels, without new intent/label regressions. Those probes cover native scenes; real detector recovery is checked separately.

The comparison has **216 cases and 738 rows**. The report verifier checks **480 filter scopes and 4,646 image assets**, followed by Chrome layout and corrected/residual-card inspection. The source patch reconstructs all 13 reviewed files exactly from base `05000460eac75994ae63c7cdeb881e8c4d489fab`. `_fallback`, complete-label logic and assignment-scoring ASTs are unchanged. The only crop-path change adds retention of the original detector rectangle after tracker refinement.

All **319 primary detector caches**, targets and GT masks remain byte-identical. Every file in the original v2 bundle (6,423), the 19 October revision (5,806), and the preceding 20 October revision (5,818) matches its frozen manifest. Eight enhancement records are separately hashed. A total of **99 RGB-only diagnostic requests** are retained, including unsuccessful box, edge, mirror and grid proposals; **16 cached responses** are used by the declared small-object pipeline.

| Mode / cohort | Before semantic-v2 | Revised semantic-v2 | scene-v1, shared inputs |
|---|---:|---:|---:|
| controlled / passive_intent | 104/104 | 104/104 | 88/104 |
| controlled / interaction | 14/14 | 14/14 | 5/14 |
| controlled / policy_targets | 33/33 | 33/33 | 20/33 |
| controlled / no_target | 2/2 | 2/2 | 2/2 |
| live / passive_intent | 112/112 | 112/112 | 98/112 |
| live / interaction | 14/14 | 14/14 | 6/14 |
| live / policy_targets | 30/38 | 37/38 | 20/38 |
| live / no_target | 2/2 | 2/2 | 2/2 |
| fallback / rule_conformance | 50/50 | 50/50 | not scored |

Metrics are separate development cohorts. Policy scores require both the frozen target and required fallback mode. Geometry fixtures specify a semantic-v2 contract. These correlated scenes and non-adjudicated real targets do not establish independent intent or recognition accuracy. Real photos have no invented label GT.

## Remaining failure: real-117719

The frozen annotated target is COCO instance `1492244`, detected as `d37`. Restricting the candidate set to the annotated subset makes it the exact fallback winner. The real image also contains genuine unannotated bottles closer to the center. The enhanced `d96` has visible pixels at the photo center and no matching polygon. Exact fallback therefore chooses `d96`; it cannot choose `d37` while retaining those independently detected eligible bottles and the same rules. This remains **FAIL**, with a crop, and is not converted into an accuracy gain by deleting detections or changing GT. The original primary-only input also failed for the same annotation-subset reason, choosing `d7`.

[Residual geometry and annotated-subset counterfactual](evidence/residual-failures.json) · [Seven corrected cases](evidence/revision-diff.json) · [Regression proof](evidence/regression-proof.json) · [Enhancement policy](evidence/enhancement-policy.json) · [Enhanced inputs](evidence/detector-enhancement.json) · [Investigation](evidence/detector-investigation.json) · [Receipt](evidence/receipt.json) · [Source patch](implementation.patch) · [Exact patch verification](evidence/patch-verification.json) · [HTML comparison source](evidence/comparison-report.html).

The optional variant remains disabled by default. No production rollout is part of this change.


[All eight investigated cases](INVESTIGATION.md) · [Exact source patch](implementation.patch) · [New detector helper](implementation/matcher/selector_detection.py) · [New regression tests](implementation/matcher/tests/test_selector_localization.py).

## How failures are marked

- **SCENE-V1 FAIL / WRONG TARGET**: the frozen photo result does not match the declared target. Policy-defined choices and explicit interactions remain labeled by cohort; they are not independent user-intent accuracy.
- **EXPECTED LABEL LOSS**: retained pixels of the expected target's annotated labels fall below the existing 98% threshold. This can occur with a correct target or a wrong target. Real photos without label GT are not assigned fabricated label scores.
- **UNCERTAINTY MODE FAILURE**: semantic-v2 violates a required fallback/confident mode even if its selected ID matches.
- **CONTRACT N/A**: geometry fixtures define the new semantic-v2 contract; legacy scene-v1 target differences are shown, not counted as failures against an unsupported contract.
- A wrong selection that preserves its own label is still a wrong target. Crop coverage and distractor retention do not establish physical wine identity.

## Groups

| Group | Cases | scene-v1 photo cases with a target or label failure | Open all examples |
|---|---:|---:|---|
| Whole labels, not logos | 8 | 1 | [hierarchy](groups/hierarchy.md) |
| Label-only photographs | 8 | 8 | [closeup](groups/closeup.md) |
| Tap and capture reticle | 8 | 3 | [intent](groups/intent.md) |
| Hand association | 10 | 1 | [hands](groups/hands.md) |
| Scale, edges and orientation | 10 | 1 | [framing](groups/framing.md) |
| Intent despite poor readability | 9 | 5 | [readability](groups/readability.md) |
| No clear main bottle | 9 | 5 | [ambiguity](groups/ambiguity.md) |
| Secondary labels and physical context | 9 | 4 | [context](groups/context.md) |
| Grip ownership and occluding packages | 4 | 2 | [grip-ownership](groups/grip-ownership.md) |
| Two hands: one or two subjects | 4 | 4 | [multiple-grips](groups/multiple-grips.md) |
| Horizontal bottle versus a wine tool | 4 | 1 | [tools](groups/tools.md) |
| Pointing, reaching and gripping | 4 | 4 | [touch-grip](groups/touch-grip.md) |
| Projected contact across depth | 4 | 0 | [depth-contact](groups/depth-contact.md) |
| Real bottle inside packaging versus printed artwork | 4 | 2 | [gift-box](groups/gift-box.md) |
| Clear gift packaging | 4 | 1 | [clear-packaging](groups/clear-packaging.md) |
| Poster and mirror duplicate | 4 | 2 | [depictions](groups/depictions.md) |
| Label omissions connected to the silhouette | 4 | 4 | [open-label-gaps](groups/open-label-gaps.md) |
| Tags and paper outside the bottle body | 4 | 4 | [extended-labels](groups/extended-labels.md) |
| Overlapping bottles and label owners | 8 | 5 | [label-ownership](groups/label-ownership.md) |
| Small wine information beside large signage | 4 | 4 | [signage](groups/signage.md) |
| Photo center through an occluder | 5 | 3 | [center-occlusion](groups/center-occlusion.md) |
| Explicit tap against hand and mask gaps | 4 | 4 | [tap-conflicts](groups/tap-conflicts.md) |
| Three bottles: foreground versus photo center | 14 | 5 | [foreground-three](groups/foreground-three.md) |
| Bottle format versus camera distance | 3 | 1 | [format-depth](groups/format-depth.md) |
| Separate shelves and support planes | 3 | 1 | [support-planes](groups/support-planes.md) |
| Hands projected at bottle ends | 3 | 1 | [terminal-hands](groups/terminal-hands.md) |
| Real bottles crossing printed panels | 3 | 0 | [nested-panels](groups/nested-panels.md) |
| Foreground intent among crowded and occluded bottles | 3 | 0 | [occlusion-crowds](groups/occlusion-crowds.md) |
| Additional real photographs | 5 | 0 | [real](groups/real.md) |
| Deterministic fallback fixtures | 11 | contract N/A | [fallback](groups/fallback.md) |
| Review regression fixtures | 39 | contract N/A | [review](groups/review.md) |

## Every case

| Case | Group | scene-v1 | semantic-v2 |
|---|---|---|---|
| [hc-001](cases/hc-001.md) | hierarchy | Recorded checks pass | Recorded checks pass |
| [hc-002](cases/hc-002.md) | hierarchy | Recorded checks pass | Recorded checks pass |
| [hc-003](cases/hc-003.md) | hierarchy | Recorded checks pass | Recorded checks pass |
| [hc-004](cases/hc-004.md) | hierarchy | Recorded checks pass | Recorded checks pass |
| [hc-005](cases/hc-005.md) | closeup | **FAIL** controlled: WRONG TARGET | Recorded checks pass |
| [hc-006](cases/hc-006.md) | closeup | **FAIL** controlled: WRONG TARGET | Recorded checks pass |
| [hc-007](cases/hc-007.md) | closeup | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-008](cases/hc-008.md) | closeup | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-009](cases/hc-009.md) | intent | Recorded checks pass | Recorded checks pass |
| [hc-010](cases/hc-010.md) | intent | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-011](cases/hc-011.md) | intent | Recorded checks pass | Recorded checks pass |
| [hc-012](cases/hc-012.md) | intent | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS, live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-013](cases/hc-013.md) | hands | Recorded checks pass | Recorded checks pass |
| [hc-014](cases/hc-014.md) | hands | Recorded checks pass | Recorded checks pass |
| [hc-015](cases/hc-015.md) | hands | Recorded checks pass | Recorded checks pass |
| [hc-016](cases/hc-016.md) | hands | Recorded checks pass | Recorded checks pass |
| [hc-017](cases/hc-017.md) | framing | Recorded checks pass | Recorded checks pass |
| [hc-018](cases/hc-018.md) | framing | Recorded checks pass | Recorded checks pass |
| [hc-019](cases/hc-019.md) | framing | Recorded checks pass | Recorded checks pass |
| [hc-020](cases/hc-020.md) | framing | **FAIL** live: EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-021](cases/hc-021.md) | readability | Recorded checks pass | Recorded checks pass |
| [hc-022](cases/hc-022.md) | readability | **FAIL** live: EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-023](cases/hc-023.md) | readability | **FAIL** live: EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-024](cases/hc-024.md) | readability | Recorded checks pass | Recorded checks pass |
| [hc-025](cases/hc-025.md) | ambiguity | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS, live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-026](cases/hc-026.md) | ambiguity | **FAIL** live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-027](cases/hc-027.md) | ambiguity | Recorded checks pass | Recorded checks pass |
| [hc-028](cases/hc-028.md) | ambiguity | Recorded checks pass | Recorded checks pass |
| [hc-029](cases/hc-029.md) | context | Recorded checks pass | Recorded checks pass |
| [hc-030](cases/hc-030.md) | context | **FAIL** live: EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-031](cases/hc-031.md) | context | **FAIL** live: WRONG TARGET | Recorded checks pass |
| [hc-032](cases/hc-032.md) | context | Recorded checks pass | Recorded checks pass |
| [hc-033](cases/hc-033.md) | grip-ownership | Recorded checks pass | Recorded checks pass |
| [hc-034](cases/hc-034.md) | grip-ownership | **FAIL** live: EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-035](cases/hc-035.md) | multiple-grips | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS, live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-036](cases/hc-036.md) | multiple-grips | **FAIL** live: EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-037](cases/hc-037.md) | tools | **FAIL** live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-038](cases/hc-038.md) | tools | Recorded checks pass | Recorded checks pass |
| [hc-039](cases/hc-039.md) | touch-grip | **FAIL** live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-040](cases/hc-040.md) | touch-grip | **FAIL** live: EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-041](cases/hc-041.md) | depth-contact | Recorded checks pass | Recorded checks pass |
| [hc-042](cases/hc-042.md) | depth-contact | Recorded checks pass | Recorded checks pass |
| [hc-043](cases/hc-043.md) | gift-box | Recorded checks pass | Recorded checks pass |
| [hc-044](cases/hc-044.md) | gift-box | **FAIL** live: WRONG TARGET | Recorded checks pass |
| [hc-045](cases/hc-045.md) | clear-packaging | Recorded checks pass | Recorded checks pass |
| [hc-046](cases/hc-046.md) | clear-packaging | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS, live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-047](cases/hc-047.md) | depictions | Recorded checks pass | Recorded checks pass |
| [hc-048](cases/hc-048.md) | depictions | **FAIL** live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-049](cases/hc-049.md) | open-label-gaps | **FAIL** controlled: EXPECTED LABEL LOSS, live: EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-050](cases/hc-050.md) | open-label-gaps | **FAIL** controlled: EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-051](cases/hc-051.md) | extended-labels | **FAIL** live: EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-052](cases/hc-052.md) | extended-labels | **FAIL** live: EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-053](cases/hc-053.md) | label-ownership | Recorded checks pass | Recorded checks pass |
| [hc-054](cases/hc-054.md) | label-ownership | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS, live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-055](cases/hc-055.md) | signage | **FAIL** live: EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-056](cases/hc-056.md) | signage | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS, live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-057](cases/hc-057.md) | center-occlusion | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS, live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-058](cases/hc-058.md) | center-occlusion | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS, live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-059](cases/hc-059.md) | tap-conflicts | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS, live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-060](cases/hc-060.md) | tap-conflicts | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS, live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-061](cases/hc-061.md) | foreground-three | Recorded checks pass | Recorded checks pass |
| [hc-062](cases/hc-062.md) | foreground-three | Recorded checks pass | Recorded checks pass |
| [hc-063](cases/hc-063.md) | foreground-three | Recorded checks pass | Recorded checks pass |
| [hc-064](cases/hc-064.md) | foreground-three | Recorded checks pass | Recorded checks pass |
| [hc-065](cases/hc-065.md) | foreground-three | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS, live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-066](cases/hc-066.md) | foreground-three | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS, live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-067](cases/hc-067.md) | label-ownership | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS, live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-068](cases/hc-068.md) | label-ownership | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS, live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-069](cases/hc-069.md) | foreground-three | Recorded checks pass | Recorded checks pass |
| [hc-070](cases/hc-070.md) | hierarchy | Recorded checks pass | Recorded checks pass |
| [hc-071](cases/hc-071.md) | hierarchy | Recorded checks pass | Recorded checks pass |
| [hc-072](cases/hc-072.md) | hierarchy | Recorded checks pass | Recorded checks pass |
| [hc-073](cases/hc-073.md) | hierarchy | **FAIL** controlled: EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-074](cases/hc-074.md) | closeup | **FAIL** controlled: WRONG TARGET | Recorded checks pass |
| [hc-075](cases/hc-075.md) | closeup | **FAIL** controlled: WRONG TARGET | Recorded checks pass |
| [hc-076](cases/hc-076.md) | closeup | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-077](cases/hc-077.md) | closeup | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-078](cases/hc-078.md) | intent | Recorded checks pass | Recorded checks pass |
| [hc-079](cases/hc-079.md) | intent | Recorded checks pass | Recorded checks pass |
| [hc-080](cases/hc-080.md) | intent | Recorded checks pass | Recorded checks pass |
| [hc-081](cases/hc-081.md) | intent | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS, live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-082](cases/hc-082.md) | hands | Recorded checks pass | Recorded checks pass |
| [hc-083](cases/hc-083.md) | hands | **FAIL** live: EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-084](cases/hc-084.md) | hands | Recorded checks pass | Recorded checks pass |
| [hc-085](cases/hc-085.md) | hands | Recorded checks pass | Recorded checks pass |
| [hc-086](cases/hc-086.md) | framing | Recorded checks pass | Recorded checks pass |
| [hc-087](cases/hc-087.md) | framing | Recorded checks pass | Recorded checks pass |
| [hc-088](cases/hc-088.md) | framing | Recorded checks pass | Recorded checks pass |
| [hc-089](cases/hc-089.md) | framing | Recorded checks pass | Recorded checks pass |
| [hc-090](cases/hc-090.md) | readability | Recorded checks pass | Recorded checks pass |
| [hc-091](cases/hc-091.md) | readability | **FAIL** live: EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-092](cases/hc-092.md) | readability | **FAIL** live: EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-093](cases/hc-093.md) | readability | Recorded checks pass | Recorded checks pass |
| [hc-094](cases/hc-094.md) | ambiguity | Recorded checks pass | Recorded checks pass |
| [hc-095](cases/hc-095.md) | ambiguity | Recorded checks pass | Recorded checks pass |
| [hc-096](cases/hc-096.md) | ambiguity | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-097](cases/hc-097.md) | ambiguity | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS, live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-098](cases/hc-098.md) | context | Recorded checks pass | Recorded checks pass |
| [hc-099](cases/hc-099.md) | context | **FAIL** live: EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-100](cases/hc-100.md) | context | **FAIL** live: WRONG TARGET | Recorded checks pass |
| [hc-101](cases/hc-101.md) | context | Recorded checks pass | Recorded checks pass |
| [hc-102](cases/hc-102.md) | grip-ownership | Recorded checks pass | Recorded checks pass |
| [hc-103](cases/hc-103.md) | grip-ownership | **FAIL** live: EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-104](cases/hc-104.md) | multiple-grips | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS, live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-105](cases/hc-105.md) | multiple-grips | **FAIL** live: EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-106](cases/hc-106.md) | tools | Recorded checks pass | Recorded checks pass |
| [hc-107](cases/hc-107.md) | tools | Recorded checks pass | Recorded checks pass |
| [hc-108](cases/hc-108.md) | touch-grip | **FAIL** live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-109](cases/hc-109.md) | touch-grip | **FAIL** live: EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-110](cases/hc-110.md) | depth-contact | Recorded checks pass | Recorded checks pass |
| [hc-111](cases/hc-111.md) | depth-contact | Recorded checks pass | Recorded checks pass |
| [hc-112](cases/hc-112.md) | gift-box | Recorded checks pass | Recorded checks pass |
| [hc-113](cases/hc-113.md) | gift-box | **FAIL** live: WRONG TARGET | Recorded checks pass |
| [hc-114](cases/hc-114.md) | clear-packaging | Recorded checks pass | Recorded checks pass |
| [hc-115](cases/hc-115.md) | clear-packaging | Recorded checks pass | Recorded checks pass |
| [hc-116](cases/hc-116.md) | depictions | Recorded checks pass | Recorded checks pass |
| [hc-117](cases/hc-117.md) | depictions | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS, live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-118](cases/hc-118.md) | open-label-gaps | **FAIL** controlled: EXPECTED LABEL LOSS, live: EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-119](cases/hc-119.md) | open-label-gaps | **FAIL** controlled: EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-120](cases/hc-120.md) | extended-labels | **FAIL** live: EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-121](cases/hc-121.md) | extended-labels | **FAIL** live: EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-122](cases/hc-122.md) | label-ownership | Recorded checks pass | Recorded checks pass |
| [hc-123](cases/hc-123.md) | label-ownership | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS, live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-124](cases/hc-124.md) | signage | **FAIL** live: EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-125](cases/hc-125.md) | signage | **FAIL** live: EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-126](cases/hc-126.md) | center-occlusion | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS, live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-127](cases/hc-127.md) | center-occlusion | Recorded checks pass | Recorded checks pass |
| [hc-128](cases/hc-128.md) | tap-conflicts | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS, live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-129](cases/hc-129.md) | tap-conflicts | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS, live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-130](cases/hc-130.md) | foreground-three | Recorded checks pass | Recorded checks pass |
| [hc-131](cases/hc-131.md) | foreground-three | Recorded checks pass | Recorded checks pass |
| [hc-132](cases/hc-132.md) | foreground-three | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS, live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-133](cases/hc-133.md) | foreground-three | Recorded checks pass | Recorded checks pass |
| [hc-134](cases/hc-134.md) | foreground-three | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS, live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-135](cases/hc-135.md) | foreground-three | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS, live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-136](cases/hc-136.md) | label-ownership | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS, live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-137](cases/hc-137.md) | label-ownership | Recorded checks pass | Recorded checks pass |
| [hc-138](cases/hc-138.md) | foreground-three | Recorded checks pass | Recorded checks pass |
| [hc-139](cases/hc-139.md) | format-depth | Recorded checks pass | Recorded checks pass |
| [hc-140](cases/hc-140.md) | format-depth | Recorded checks pass | Recorded checks pass |
| [hc-141](cases/hc-141.md) | format-depth | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS, live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-142](cases/hc-142.md) | support-planes | Recorded checks pass | Recorded checks pass |
| [hc-143](cases/hc-143.md) | support-planes | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS, live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-144](cases/hc-144.md) | support-planes | Recorded checks pass | Recorded checks pass |
| [hc-145](cases/hc-145.md) | terminal-hands | Recorded checks pass | Recorded checks pass |
| [hc-146](cases/hc-146.md) | terminal-hands | Recorded checks pass | Recorded checks pass |
| [hc-147](cases/hc-147.md) | terminal-hands | **FAIL** live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-148](cases/hc-148.md) | nested-panels | Recorded checks pass | Recorded checks pass |
| [hc-149](cases/hc-149.md) | nested-panels | Recorded checks pass | Recorded checks pass |
| [hc-150](cases/hc-150.md) | nested-panels | Recorded checks pass | Recorded checks pass |
| [hc-151](cases/hc-151.md) | occlusion-crowds | Recorded checks pass | Recorded checks pass |
| [hc-152](cases/hc-152.md) | occlusion-crowds | Recorded checks pass | Recorded checks pass |
| [hc-153](cases/hc-153.md) | occlusion-crowds | Recorded checks pass | Recorded checks pass |
| [real-180751](cases/real-180751.md) | real | Recorded checks pass | Recorded checks pass |
| [real-417632](cases/real-417632.md) | real | Recorded checks pass | Recorded checks pass |
| [real-541773](cases/real-541773.md) | real | Recorded checks pass | Recorded checks pass |
| [real-166426](cases/real-166426.md) | real | Recorded checks pass | Recorded checks pass |
| [real-116208](cases/real-116208.md) | real | Recorded checks pass | Recorded checks pass |
| [real-25394](cases/real-25394.md) | hands | Recorded checks pass | Recorded checks pass |
| [real-312192](cases/real-312192.md) | framing | Recorded checks pass | Recorded checks pass |
| [real-402720](cases/real-402720.md) | framing | Recorded checks pass | Recorded checks pass |
| [real-520871](cases/real-520871.md) | context | Recorded checks pass | Recorded checks pass |
| [real-22705](cases/real-22705.md) | hands | Recorded checks pass | Recorded checks pass |
| [real-166918](cases/real-166918.md) | ambiguity | **FAIL** live: WRONG TARGET | Recorded checks pass |
| [real-117719](cases/real-117719.md) | readability | **FAIL** live: WRONG TARGET | **FAIL** live: WRONG TARGET |
| [real-397354](cases/real-397354.md) | center-occlusion | Recorded checks pass | Recorded checks pass |
| [fb-center-mask](cases/fb-center-mask.md) | fallback | Contract N/A; fallback: target differs | Recorded checks pass |
| [fb-nearest](cases/fb-nearest.md) | fallback | Contract N/A; fallback: target differs | Recorded checks pass |
| [fb-left](cases/fb-left.md) | fallback | Contract N/A; fallback: target differs | Recorded checks pass |
| [fb-upper](cases/fb-upper.md) | fallback | Contract N/A; fallback: target differs | Recorded checks pass |
| [fb-overlap](cases/fb-overlap.md) | fallback | Contract N/A; fallback: target match | Recorded checks pass |
| [fb-stable-id](cases/fb-stable-id.md) | fallback | Contract N/A; fallback: target match | Recorded checks pass |
| [fb-pixel-distance](cases/fb-pixel-distance.md) | fallback | Contract N/A; fallback: target differs | Recorded checks pass |
| [fb-no-candidates](cases/fb-no-candidates.md) | fallback | Contract N/A; fallback: target match | Recorded checks pass |
| [fb-low-confidence](cases/fb-low-confidence.md) | fallback | Contract N/A; fallback: target match | Recorded checks pass |
| [fb-tap-miss](cases/fb-tap-miss.md) | fallback | Contract N/A; fallback: target differs | Recorded checks pass |
| [fb-reticle-unresolved](cases/fb-reticle-unresolved.md) | fallback | Contract N/A; fallback: target match | Recorded checks pass |
| [fb-missed-tap-hand](cases/fb-missed-tap-hand.md) | review | Contract N/A; fallback: target match | Recorded checks pass |
| [fb-missed-tap-single](cases/fb-missed-tap-single.md) | review | Contract N/A; fallback: target match | Recorded checks pass |
| [fb-missed-tap-reticle](cases/fb-missed-tap-reticle.md) | review | Contract N/A; fallback: target differs | Recorded checks pass |
| [fb-mask-tap-over-label-box](cases/fb-mask-tap-over-label-box.md) | review | Contract N/A; fallback: target differs | Recorded checks pass |
| [fb-multi-hit-pool](cases/fb-multi-hit-pool.md) | review | Contract N/A; fallback: target match | Recorded checks pass |
| [fb-tiny-hand-distractor](cases/fb-tiny-hand-distractor.md) | review | Contract N/A; fallback: target differs | Recorded checks pass |
| [fb-secondary-label-hole](cases/fb-secondary-label-hole.md) | review | Contract N/A; fallback: target match | Recorded checks pass |
| [fb-label-context](cases/fb-label-context.md) | review | Contract N/A; fallback: target differs | Recorded checks pass |
| [fb-unequal-two-grips](cases/fb-unequal-two-grips.md) | review | Contract N/A; fallback: target match | Recorded checks pass |
| [fb-box-around-hand](cases/fb-box-around-hand.md) | review | Contract N/A; fallback: target differs | Recorded checks pass |
| [fb-body-grip-enclosure](cases/fb-body-grip-enclosure.md) | review | Contract N/A; fallback: target match | Recorded checks pass |
| [fb-different-hands-unequal](cases/fb-different-hands-unequal.md) | review | Contract N/A; fallback: target match | Recorded checks pass |
| [fb-two-hands-one-subject](cases/fb-two-hands-one-subject.md) | review | Contract N/A; fallback: target match | Recorded checks pass |
| [fb-unlabeled-strip-conflict](cases/fb-unlabeled-strip-conflict.md) | review | Contract N/A; fallback: target match | Recorded checks pass |
| [fb-exterior-label-strip](cases/fb-exterior-label-strip.md) | review | Contract N/A; fallback: target match | Recorded checks pass |
| [fb-label-gap-tap](cases/fb-label-gap-tap.md) | review | Contract N/A; fallback: target match | Recorded checks pass |
| [fb-three-foreground](cases/fb-three-foreground.md) | review | Contract N/A; fallback: target differs | Recorded checks pass |
| [fb-three-weak-depth](cases/fb-three-weak-depth.md) | review | Contract N/A; fallback: target match | Recorded checks pass |
| [fb-background-magnum](cases/fb-background-magnum.md) | review | Contract N/A; fallback: target match | Recorded checks pass |
| [fb-three-tap-background](cases/fb-three-tap-background.md) | review | Contract N/A; fallback: target match | Recorded checks pass |
| [fb-held-carton-only](cases/fb-held-carton-only.md) | review | Contract N/A; fallback: target match | Recorded checks pass |
| [fb-orphan-label-beside-bottle](cases/fb-orphan-label-beside-bottle.md) | review | Contract N/A; fallback: target match | Recorded checks pass |
| [fb-centered-label-closeup-with-bottle](cases/fb-centered-label-closeup-with-bottle.md) | review | Contract N/A; fallback: target differs | Recorded checks pass |
| [fb-tap-orphan-label](cases/fb-tap-orphan-label.md) | review | Contract N/A; fallback: target differs | Recorded checks pass |
| [fb-dominant-label-price-conflict](cases/fb-dominant-label-price-conflict.md) | review | Contract N/A; fallback: target differs | Recorded checks pass |
| [fb-separate-shelf-levels](cases/fb-separate-shelf-levels.md) | review | Contract N/A; fallback: target match | Recorded checks pass |
| [fb-truncated-background-peer](cases/fb-truncated-background-peer.md) | review | Contract N/A; fallback: target match | Recorded checks pass |
| [fb-bystander-hand-three](cases/fb-bystander-hand-three.md) | review | Contract N/A; fallback: target differs | Recorded checks pass |
| [fb-held-unlabelled-carton](cases/fb-held-unlabelled-carton.md) | review | Contract N/A; fallback: target match | Recorded checks pass |
| [fb-lying-foreground-three](cases/fb-lying-foreground-three.md) | review | Contract N/A; fallback: target differs | Recorded checks pass |
| [fb-unowned-label-logo-mask](cases/fb-unowned-label-logo-mask.md) | review | Contract N/A; fallback: target match | Recorded checks pass |
| [fb-weak-wrap-strong-grip](cases/fb-weak-wrap-strong-grip.md) | review | Contract N/A; fallback: target differs | Recorded checks pass |
| [fb-multiple-grips-unheld-foreground](cases/fb-multiple-grips-unheld-foreground.md) | review | Contract N/A; fallback: target differs | Recorded checks pass |
| [fb-owner-and-uncertain-background](cases/fb-owner-and-uncertain-background.md) | review | Contract N/A; fallback: target match | Recorded checks pass |
| [fb-held-neck-dominant-paper](cases/fb-held-neck-dominant-paper.md) | review | Contract N/A; fallback: target differs | Recorded checks pass |
| [fb-held-neck-pending-logo](cases/fb-held-neck-pending-logo.md) | review | Contract N/A; fallback: target match | Recorded checks pass |
| [fb-point-contact-near-center-bottle](cases/fb-point-contact-near-center-bottle.md) | review | Contract N/A; fallback: target match | Recorded checks pass |
| [fb-opposed-background-midbody](cases/fb-opposed-background-midbody.md) | review | Contract N/A; fallback: target match | Recorded checks pass |
| [fb-enclosing-label-panel](cases/fb-enclosing-label-panel.md) | review | Contract N/A; fallback: target differs | Recorded checks pass |

## Evidence and attribution

[Frozen cases](evidence/cases.json) · [Saved comparison](evidence/comparison.json) · [Current receipt](evidence/receipt.json) · [Photo sources and external samples](evidence/external-samples.json) · [Uploaded source file hashes](source-manifest.json).

The source files in `assets/` are byte-for-byte copies. `overlays/` and `previews/` are derived presentation figures; their colors and resizing are not new ground truth. Original annotation ownership, mask hashes, image hashes, source provenance and saved outputs remain in each case JSON.

COCO attribution and the exact source license accompany every real case. Native artwork/source geometry has no blanket redistribution license assertion; these materials are uploaded to the existing private repository for the requested review. Transparent packaging and mirror examples are proxies. Exact detector checkpoint revision was not disclosed in the frozen release.

The revised selector passes 452 matcher tests, including twelve new regression methods in this revision. The current receipt and revision audit provide crop and label counts. Original targets and primary detector inputs remain frozen; optional enhancement inputs are separately hashed; no production rollout is part of this gallery.


**Taxonomy caveat:** `real-402720` is a bottle-framing regression, not a verified wine-intent positive. The frozen target description may misidentify the beverage; it is preserved as historical source data, not endorsed by this gallery.
