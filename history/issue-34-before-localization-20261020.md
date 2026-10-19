# Historical issue #34 body before the localization revision

Captured before the 20 October 2026 localization update. The text below is preserved verbatim as historical requirements and evidence. Statements about earlier test counts, remaining failures, local files or publication status refer to those earlier revisions, not the current update.

---

<!-- issue-34-detector-fixes-20261020 -->
## Current detector investigation · 20 October 2026

**Three of the remaining eleven mismatches are fixed; eight remain unresolved.** [Current 216-case comparison](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/0a13813afde5225f658a4e289eab87a08f223eab/revisions/detector-fixes-20261020/README.md) · [Investigation of all eleven](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/0a13813afde5225f658a4e289eab87a08f223eab/revisions/detector-fixes-20261020/INVESTIGATION.md) · [scene-v1 failures](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/0a13813afde5225f658a4e289eab87a08f223eab/revisions/detector-fixes-20261020/SCENE-V1-FAILURES.md) · [Source patch](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/0a13813afde5225f658a4e289eab87a08f223eab/revisions/detector-fixes-20261020/implementation.patch) · [440-test receipt](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/0a13813afde5225f658a4e289eab87a08f223eab/revisions/detector-fixes-20261020/evidence/receipt.json).

- **Fixed `hc-145/live` and `hc-146/live`:** independent box/mask disagreement was clipping visible detector pixels and shifting geometry. Small discrepancies now use exact visible-mask bounds, with the reported box and geometry source exposed. Substantial amodal/occlusion boxes remain intact. The original exact fallback chooses the declared target; no near-tie epsilon, GT lookup or new tie preference is used.
- **Fixed `real-520871/live`:** the wine-specific primary response is empty. The standalone byte adapter makes one generic `bottle` recovery pass within the original timeout budget. Empty/unavailable recovery retains the valid full-frame fallback. Both empty native controls still return zero bottles. Supplied instances/cascade replay never trigger another request. Generic bottle detection does not establish beverage identity.

**440 tests pass; 369/369 crops; 298/298 selected-label checks at 100%; 1,424 robustness probes with 100% selected-label retention and no new intent/label regressions.** The saved 19 October code fails the new two recorded winner regressions. HTML verification covers 480 scopes and 4,644 assets, followed by Chrome inspection. [Before/after audit](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/0a13813afde5225f658a4e289eab87a08f223eab/revisions/detector-fixes-20261020/evidence/revision-diff.json).

| Live cohort | semantic-v2 before | revised | scene-v1 with shared recovery inputs |
|---|---:|---:|---:|
| Passive intent | 111/112 | 112/112 | 98/112 |
| Explicit interaction | 14/14 | 14/14 | 6/14 |
| Policy target + required fallback | 28/38 | 30/38 | 20/38 ID matches |
| No-target negatives | 2/2 | 2/2 | 2/2 |

**Joint failures 11 → 8, zero new joint regressions.** Controlled cohorts and all 50 rule fixtures still pass. Both algorithms receive the same separately frozen recovered carafe detection in this comparison, so scene-v1's passive ID count changes 97 → 98 from detector coverage alone; its algorithm and all other output PNGs are unchanged. Earlier scene-v1 results remain frozen below. No production rollout or independent accuracy claim.

**Still failing:** native `hc-025/035/039/041/056` retain detector-vs-GT tie disagreements; `real-397354` retains a near-distance geometry mismatch; `real-117719` has nearer visible detections absent from the incomplete annotation subset; `real-166918`'s tiny target remains undetected, including four overlapping image-tile probes. Lossless wine/generic prompts, local RGB crops, unbounded mask tightening and GrabCut were tested and unsuccessful proposals retained. No GT-shaped candidates were manufactured or genuine nearer detections silently removed. [Exact residual boxes, mask links, distances and IoUs](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/0a13813afde5225f658a4e289eab87a08f223eab/revisions/detector-fixes-20261020/evidence/residual-failures.json).

All targets, GT masks, 319 primary prediction caches and the fallback/crop/assignment function bodies are unchanged. All 6,423 original-v2 files and 5,806 files of the 19 October revision still match their manifests. New recovery responses have a separate hash binding checked before replay. [Preservation proof](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/0a13813afde5225f658a4e289eab87a08f223eab/revisions/detector-fixes-20261020/evidence/frozen-preservation.json) · [Unchanged contracts](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/0a13813afde5225f658a4e289eab87a08f223eab/revisions/detector-fixes-20261020/evidence/unchanged-contract-source.json).

Earlier material below is historical; use this revision and its new comment for present results.

---

<!-- issue-34-semantic-v2-fixes-20261019 -->
## Current revision: semantic-v2 fixes · 19 October 2026

**[Review the revised 216-case comparison](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/3a927638f8ef94188e47147b197dcbb61c0faba8/revisions/semantic-v2-20261019/README.md)** · **[scene-v1 failures](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/3a927638f8ef94188e47147b197dcbb61c0faba8/revisions/semantic-v2-20261019/SCENE-V1-FAILURES.md)** · **[source patch](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/3a927638f8ef94188e47147b197dcbb61c0faba8/revisions/semantic-v2-20261019/implementation.patch)** · **[validation receipt](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/3a927638f8ef94188e47147b197dcbb61c0faba8/revisions/semantic-v2-20261019/evidence/receipt.json)**

Fixed foreground selection with reversed occluded-bottle axes, non-bottle scale distractors and truncated shelf peers; false grip priority for a slender unlabelled tool; false confidence from neck/base hand projection and separate shelf planes; and dominant labelled edge framing. Explicit tap priority, complete labels and deterministic always-crop fallback remain covered by regression tests.

**430 tests pass**, including eight new regression methods covering 23 saved detector rows. The previous implementation fails 24 regression subtests. **369/369 results return crops; 298/298 selected-subject label checks retain 100%.** All 1,424 robustness probes return crops and retain 100% of selected labels, with no new intent/label regressions. Selected-label retention does not imply the selected target is correct.

| Mode / cohort | semantic-v2 before | revised | scene-v1 unchanged |
|---|---:|---:|---:|
| controlled / passive_intent | 100/104 | 104/104 | 88/104 |
| controlled / interaction | 14/14 | 14/14 | 5/14 |
| controlled / policy_targets | 30/33 | 33/33 | 20/33 |
| controlled / no_target | 2/2 | 2/2 | 2/2 |
| live / passive_intent | 107/112 | 111/112 | 97/112 |
| live / interaction | 14/14 | 14/14 | 6/14 |
| live / policy_targets | 27/38 | 28/38 | 20/38 |
| live / no_target | 2/2 | 2/2 | 2/2 |
| fallback / rule_conformance | 50/50 | 50/50 | not scored |

Semantic scores require the declared target plus required confidence/fallback mode where constrained. scene-v1 photo scores are target-ID matches; rule fixtures are a semantic-v2 contract only. Cohorts remain separate development coverage, not a combined accuracy estimate.

**Joint failures: 23 → 11; 12 fixed, zero new joint regressions.** [Full before/after audit](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/3a927638f8ef94188e47147b197dcbb61c0faba8/revisions/semantic-v2-20261019/evidence/revision-diff.json).

**Eleven live failures remain explicitly unresolved:** nine disagreements between detector and GT fallback geometry (`hc-025`, `035`, `039`, `041`, `056`, `145`, `146`, `real-397354`, `real-117719`); no eligible detection in `real-520871`; and a detector/GT assignment gap in `real-166918`. [Review exact boxes, masks, center/distance ordering and IoUs](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/3a927638f8ef94188e47147b197dcbb61c0faba8/revisions/semantic-v2-20261019/evidence/residual-failures.json). Each residual case page also links the original detector masks. The independently computed exact detector fallback agrees with the selector; forcing the frozen GT winner requires changing inputs, annotations or the agreed policy.

**Tradeoffs exposed:** `hc-145/live` and `hc-146/live` previously matched the target via an incorrect confident grip. Fixing confidence makes the required fallback honest and exposes detector-vs-GT target ordering. Their ID/expected-target label scores decrease; selected-subject labels remain complete. These are visible failures, not reported as passes.

The original 216 cases, GT, scorer, 319 detector caches and all 6,423 frozen-v2 manifest files are unchanged. scene-v1 decisions and emitted PNG bytes are unchanged. No new model calls or production rollout. The review patch applies to `05000460eac75994ae63c7cdeb881e8c4d489fab`; [application and tested-source hashes](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/3a927638f8ef94188e47147b197dcbb61c0faba8/revisions/semantic-v2-20261019/evidence/patch-verification.json).

Updated group contact sheets and links to every case are in the new revision comment below. Earlier galleries and prose below are **historical evidence**, including earlier failure counts and now-fixed `hc-152`; use the current revision above for present results.

---

## Historical frozen-v2 review and discussion

<!-- issue-34-github-gallery-v2 -->
## Review every photo, mask and selector crop on GitHub

**[Open the complete 216-case gallery](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/README.md)** · **[Where scene-v1 fails](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/SCENE-V1-FAILURES.md)**

All **166 photo inputs** (153 native renders + 13 real photos) and **50 geometry fixtures** are now hosted in this private GitHub repository. Every case links its input, annotated mask overlay, all original binary masks, both selectors' emitted crops/keep masks and label crop views, with controlled and live results where recorded. Expand the gallery comments below for group contact sheets picturing every case, then open any case for full-size evidence; no local paths or downloads are required.

**scene-v1 failures are explicitly marked in red on comparison cards and in the case tables:**

- **WRONG TARGET:** the frozen result misses the declared subject; intent, interactions and geometry-policy cohorts remain identified separately.
- **EXPECTED LABEL LOSS:** less than 98% of the expected subject's annotated label pixels survive, including cases where the target ID is correct. Real photos without label GT are not given fabricated scores.
- Geometry fixtures show legacy target differences as **CONTRACT N/A**, because their new semantic-v2 contract was not a scene-v1 capability. semantic-v2 target and uncertainty-mode failures remain visible too.

The failure index contains **77 photo inputs with a scene-v1 target or label failure in at least one saved mode** (107 case/mode rows). Within those rows, 79 miss the declared target and 96 lose expected-label pixels; the categories overlap. These are development check counts, not a combined accuracy estimate.

### Examples of scene-v1 failures

[**hc-049 — expected-label loss despite selecting the target**](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/cases/hc-049.md)

[![hc-049 scene-v1 label loss](https://github.com/s1mb1o/svoe-vino-lab-dev/raw/bec518e03dbf005b085448a98a1aa2933e48e409/previews/hc-049.jpg)](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/cases/hc-049.md)

[**hc-037 — wrong subject in a pouring-bottle scene**](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/cases/hc-037.md) · [**hc-012 — explicit-reticle target missed**](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/cases/hc-012.md) · [**hc-152 — failure remains in both selectors**](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/cases/hc-152.md)

### All case groups

| Group | Cases | Review photos, masks and crops |
|---|---:|---|
| `hierarchy` | 8 | [Open all 8 examples](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/groups/hierarchy.md) |
| `closeup` | 8 | [Open all 8 examples](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/groups/closeup.md) |
| `intent` | 8 | [Open all 8 examples](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/groups/intent.md) |
| `hands` | 10 | [Open all 10 examples](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/groups/hands.md) |
| `framing` | 10 | [Open all 10 examples](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/groups/framing.md) |
| `readability` | 9 | [Open all 9 examples](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/groups/readability.md) |
| `ambiguity` | 9 | [Open all 9 examples](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/groups/ambiguity.md) |
| `context` | 9 | [Open all 9 examples](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/groups/context.md) |
| `grip-ownership` | 4 | [Open all 4 examples](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/groups/grip-ownership.md) |
| `multiple-grips` | 4 | [Open all 4 examples](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/groups/multiple-grips.md) |
| `tools` | 4 | [Open all 4 examples](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/groups/tools.md) |
| `touch-grip` | 4 | [Open all 4 examples](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/groups/touch-grip.md) |
| `depth-contact` | 4 | [Open all 4 examples](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/groups/depth-contact.md) |
| `gift-box` | 4 | [Open all 4 examples](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/groups/gift-box.md) |
| `clear-packaging` | 4 | [Open all 4 examples](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/groups/clear-packaging.md) |
| `depictions` | 4 | [Open all 4 examples](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/groups/depictions.md) |
| `open-label-gaps` | 4 | [Open all 4 examples](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/groups/open-label-gaps.md) |
| `extended-labels` | 4 | [Open all 4 examples](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/groups/extended-labels.md) |
| `label-ownership` | 8 | [Open all 8 examples](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/groups/label-ownership.md) |
| `signage` | 4 | [Open all 4 examples](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/groups/signage.md) |
| `center-occlusion` | 5 | [Open all 5 examples](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/groups/center-occlusion.md) |
| `tap-conflicts` | 4 | [Open all 4 examples](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/groups/tap-conflicts.md) |
| `foreground-three` | 14 | [Open all 14 examples](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/groups/foreground-three.md) |
| `format-depth` | 3 | [Open all 3 examples](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/groups/format-depth.md) |
| `support-planes` | 3 | [Open all 3 examples](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/groups/support-planes.md) |
| `terminal-hands` | 3 | [Open all 3 examples](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/groups/terminal-hands.md) |
| `nested-panels` | 3 | [Open all 3 examples](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/groups/nested-panels.md) |
| `occlusion-crowds` | 3 | [Open all 3 examples](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/groups/occlusion-crowds.md) |
| `real` | 5 | [Open all 5 examples](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/groups/real.md) |
| `fallback` | 11 | [Open all 11 examples](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/groups/fallback.md) |
| `review` | 39 | [Open all 39 examples](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/groups/review.md) |

Original assets and case pages are pinned to commit `bec518e03dbf005b085448a98a1aa2933e48e409`; compact group contact sheets are pinned to `47610240673a94366a5ec70678dcd0ae14b77b74` on `issue-34-review-assets-v2`, an assets-only branch. [Source hashes](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/source-manifest.json) and [gallery validation](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/bec518e03dbf005b085448a98a1aa2933e48e409/gallery-validation.json) preserve the frozen inputs. Original images, masks, targets and predictions were not changed; only review figures and navigation were added. The older local-only artifact notes below predate this upload.

Gallery comments: [Part 1](https://github.com/s1mb1o/svoe-vino-lab-dev/issues/34#issuecomment-6275563090) · [Part 2](https://github.com/s1mb1o/svoe-vino-lab-dev/issues/34#issuecomment-6275563796) · [Part 3](https://github.com/s1mb1o/svoe-vino-lab-dev/issues/34#issuecomment-6275564419).

---

## Consolidated functionality and case examples — 19 October 2026

Source: [Define wine bottle selection rules — shared conversation](https://chatgpt.com/s/cx_6ad66c67f3088191a0fc28edc06316e7). This is the existing tracking issue for that conversation; no duplicate issue is needed. This guide consolidates the product behavior, optional matcher integration, all 28 declared test groups, fallback edge cases, and subsequent dataset requirements. Earlier experiment notes are preserved below with their original counts and limitations.

### Functionality and integration

Choose the intended physical wine bottle or wine package in a photograph, then supply a recognition crop that retains its complete visible labels. The hierarchy is **physical bottle/package → complete label → artwork, text, logo or code**. A prominent logo, readable brand name or strong recognition match must not independently decide the subject.

The implementation is an **experimental, optional `semantic-v2` variant**, comparable with the existing `scene-v1` selector. It is disabled by default. In the selected `siglip2` or `cascade` pipeline entry:

```yaml
input_selector:
  enabled: true
  variant: semantic-v2
```

The implementation also accepts `variant: scene-v1` for comparison. Example: `code/svoe-vino-lab-main-selector/matcher/config.main-selector.example.yaml`. The standalone SigLIP2 path requests bottle/label/hand/package detections once; cascade reuses its existing detections and maps boxes and masks into the oriented image together. Group matching continues to return all bottles. The new enabled selector cannot be combined with legacy `hand_selection: true`.

Core behavior:

1. A unique explicit tap selects its owning bottle or label. A tap on artwork resolves to its physical owner. A missed tap continues through the remaining checks. Multiple tap hits restrict selection to those alternatives.
2. A reliably associated grip can establish the subject, including an off-center or poorly readable bottle. Resolve each hand independently; box overlap or contact alone does not prove a grip. Two hands on different bottles cannot manufacture unique intent.
3. A sufficiently distinct explicit capture reticle and supported foreground prominence are subsequent cues. Foreground evidence can override photo-center proximity. Size, lower position, focus or readable text alone must not certify physical camera distance.
4. If the evidence does not resolve the subject, **still return a crop**, using the deterministic fallback below and explicitly recording uncertainty.
5. Preserve source RGB within the subject rectangle and complete associated label regions, including blank paper, borders, artwork, neck/secondary labels, direct glass printing and protruding tags. Do not generate hidden pixels or text. A label-only close-up or uncertain enclosing panel can require the full frame as context.
6. Return the selected instance, candidate alternatives, reason, crop/label boxes and label views. Explainability includes `selection_mode`, `fallback_trigger`, `crop_scope`, `tap_status`, candidate `grip_evidence` and `panel_context`. Ranking scores are not calibrated intent probabilities. A successful response returns a crop; malformed input or dependency failures remain errors.

**Interface scope:** tap and reticle arguments are supported by the selector API and evaluation harness. The YAML matcher-input switch enables automatic preprocessing; it does not itself add a mobile tap UI or new request fields.

### Always-crop fallback, including every tie case

Apply this only after the preceding intent checks cannot resolve a subject. Center means the **photo center after orientation**, not the reticle or the center of the candidate set.

| Situation / example | Handling |
|---|---|
| One candidate's visible mask covers the photo-center pixel (`fb-center-mask`) | Select that candidate even if another bbox center is nearer. |
| Several masks cover the center (`fb-overlap`) | Restrict to those candidates, then choose the nearest bbox center. This includes detector-overlap cases; opaque visible GT layers need not physically overlap. |
| No mask covers the center (`fb-nearest`) | Choose the bbox center nearest the photo center by Euclidean **pixel** distance. |
| Equal distances (`fb-left`) | Choose the leftmost bbox center. |
| Equal distance and horizontal center (`fb-upper`) | Choose the uppermost bbox center. |
| Identical geometry (`fb-stable-id`) | Use the stable numeric source index within that detector response, not lexical ordering of `d10` and `d2`. Identical candidates are not promised a persistent physical ID across independent detector responses. |
| Non-square image or exact tie (`fb-pixel-distance`) | Use integer doubled bbox-center coordinates, avoiding aspect-ratio distortion and floating-point tie drift. Visible center coverage is tested at `(W // 2, H // 2)`; bbox endpoints are exclusive. |
| No usable candidate, including all detections rejected as low confidence (`fb-no-candidates`, `fb-low-confidence`) | Return the complete oriented working image; no selected subject is invented. |
| Missed or unresolved interaction (`fb-missed-tap-hand`, `fb-missed-tap-reticle`, `fb-multi-hit-pool`, `fb-reticle-unresolved`) | Continue valid hand/reticle checks, respect the tap candidate pool, then fall back using the photo center. |

The result distinguishes a confident selection from `selection_mode: fallback`. Full-frame context may preserve distractor labels too; a returned crop does not imply isolated identity or a correct target.

### Examples for all 28 declared test groups

These are the **required handling contracts**, with concrete fixture/photo IDs. They are not a claim that every expanded example currently passes; confirmed exceptions are listed immediately afterward. Additional views vary framing, lighting and rotation while retaining their parent scenario IDs.

| # / group | Example cases | Required handling |
|---|---|---|
| 1. `hierarchy` | `hc-001/002`: huge red/black logo; `hc-003`: holes in a predicted label | Select the bottle and retain the whole visible label, including white paper and text; never reduce the crop to the logo. |
| 2. `closeup` | `hc-005/006/007`: front/back label close-up or label touching the frame edge | Do not require a neck, cap or full outline. Preserve full-frame context when a safe enclosing bottle is unavailable. |
| 3. `intent` | `hc-009/010/011`: tap the left/right bottle or explicitly aim at one bottle | Resolve unique tap ownership first; honor a sufficiently distinct reticle through its separate intent rule. |
| 4. `hands` | `hc-013/014/015`: off-center neck/body grip; hand bbox crosses the shelf | Prefer a uniquely supported held subject; inspect visible contact and grip geometry rather than promoting every overlapping bottle. |
| 5. `framing` | `hc-017/018/019`: foreground off-center, cut-off top or side | Keep the intended foreground/held subject when its evidence remains clear. Frame-edge contact alone must not reject it. |
| 6. `readability` | `hc-021/022/023`: rear label, glare or dim foreground bottle | Keep the intended subject even when a background label is easier to read; preserve observed pixels without reconstructing text. |
| 7. `ambiguity` | `hc-025/026/027`: equal pair, equal trio or two held bottles | Mark fallback and apply center → nearest → left → upper → numeric source ID; always emit a crop. |
| 8. `context` | `hc-029/030/031`: neck paper, printing on glass or bottle artwork on a carton | Preserve secondary information and the physical package. An enclosing printed panel is context, not proof of another real bottle. Glass-only/empty controls return the full image when no eligible subject exists. |
| 9. `grip-ownership` | `hc-033/034`: carton behind a hand versus real body grip enclosed by the bottle bbox | Associate the hand with the physical held subject; enclosure alone must neither establish a carton grip nor invalidate a real body grip. |
| 10. `multiple-grips` | `hc-035/036`: different bottles with unequal hand-contact areas; two hands on one bottle | Different owners remain ambiguous regardless of contact-area imbalance. Two hands may support one shared subject if positive grip evidence exists. |
| 11. `tools` | `hc-037/038`: horizontal pouring bottle versus a sampling tool | Retain a real horizontal bottle; do not treat a held tool as the wine merely because it contacts a hand. |
| 12. `touch-grip` | `hc-039/040`: pointing finger versus wrapped grip | Pointing/contact alone cannot produce confident grip priority. Use supported grip evidence or an explicitly marked fallback. |
| 13. `depth-contact` | `hc-041/042`: hand projected behind a bottle versus physical neck grip | Do not equate projected adjacency with depth/contact certainty. Preserve ambiguity when visible evidence cannot resolve it. |
| 14. `gift-box` | `hc-043/044`: bottle inside an open box versus illustration on a closed carton | Preserve the real bottle and its labels in the open box; preserve the physical carton/panel context for printed artwork. |
| 15. `clear-packaging` | `hc-045/046`: window gift bag or reflective wrapping | Retain the complete visible label despite packaging graphics. Transparent/refraction examples are proxies, not exact physical glass GT. |
| 16. `depictions` | `hc-047/048`: large poster or mirror duplicate next to a real bottle | Prefer the physical subject when distinguishable; otherwise fall back without claiming certainty. The mirror fixture is a staged reflection proxy. |
| 17. `open-label-gaps` | `hc-049/050`: omitted secondary paper or a main-label strip connected to the silhouette edge | Preserve original RGB across the subject rectangle; enclosed-hole filling alone cannot recover an exterior-connected omission. |
| 18. `extended-labels` | `hc-051/052`: hanging neck tag or peeling flap outside the body | Expand the crop to include complete associated label regions, including protruding paper. |
| 19. `label-ownership` | `hc-053/054`: touching labels; rear label inside front bottle's bbox | Associate labels with their physical owners; a shared rectangle alone must not merge two wines. Preserve context when ownership remains uncertain. |
| 20. `signage` | `hc-055/056`: small vintage label beside a large price card; promotional strip bridging bottles | Preserve wine information without letting nearby price/signage determine the subject. A genuinely ambiguous bridge uses fallback. |
| 21. `center-occlusion` | `hc-057/058`: foreground glass blocks the center pixel versus a bottle mask covering it | Test the actual visible mask, not an amodal bbox. If no eligible mask covers the center, use nearest-center fallback. |
| 22. `tap-conflicts` | `hc-059/060`: tap a rear bottle while another is held; tap white paper omitted from the bottle mask | Honor a unique explicit tap. Use associated complete-label context to resolve a missing-mask tap; a real mask hit takes priority over another label's rectangle. |
| 23. `foreground-three` | `hc-061/062/063`: off-center foreground, overlap or frame edge; `hc-064/065`: weak depth or large rear magnum; `hc-066`: rear tap; `hc-069`: lying foreground | A clearly dominant foreground bottle beats two rear bottles near center and keeps its full visible labels. Weak depth/size conflicts fall back. A unique rear tap overrides foreground prominence. Horizontal pose alone does not reject the foreground bottle. |
| 24. `format-depth` | `hc-139/140/141`: half bottle versus magnum, distant magnum or held small bottle | Do not infer distance from bottle size alone. Supported grip can select a smaller subject; unresolved scale/depth conflict uses fallback. |
| 25. `support-planes` | `hc-142/143/144`: raised rear shelf, lying lower-shelf bottle or staggered platforms | Lower position in the image is insufficient evidence of camera proximity across different support planes; unresolved depth uses fallback. |
| 26. `terminal-hands` | `hc-145/146/147`: hand behind neck/base versus genuine tilted pouring grip | A projected rear hand must not receive confident grip priority. A genuine supported pouring grip can. This remains a known confidence failure for some end-contact geometry. |
| 27. `nested-panels` | `hc-148/149/150`: real bottle before a poster, filled/amodal panel-mask fault or rolled view | Preserve original bottle/label context. A background panel filled across the foreground must not be treated as reliable physical identity evidence; this remains an open detector/ownership limitation. |
| 28. `occlusion-crowds` | `hc-151/152/153`: five bottles plus glass, seven plus bucket or crossing labels | Select the intended subject when evidence supports it; retain all its visible label pixels. Otherwise use explicit fallback. Do not generate occluded label content. |

### Current evidence and observed exceptions

The later v2 dataset, not the earlier v1 counts below, contains **166 photo inputs**: 153 native renders and 13 real COCO photos, plus **50 separately scored geometry fixtures** and **1,621 binary masks**. The expansion added 92 inputs: 69 additional views, 15 new scenarios and 8 real photos.

Its frozen receipt records **125 passing focused selector/integration/metric tests**; **369/369 semantic-v2 result rows return crops**; **297/297 assigned selected-subject label checks retain 100% of annotated pixels**. These are saved results, not tests rerun for this issue edit. Preserving the wrong bottle's labels still counts as a target failure. Real photos have no fabricated hand/label GT. Controlled GT-derived detections, live saved detector responses, interactions, passive intent, policy targets and geometry fixtures have separate denominators. Neither old v1 scores nor correlated synthetic views establish independent production accuracy.

The v2 expansion explicitly exposes **18 new case/mode problem rows across 12 inputs**, with no post-prediction target reassignment or selector tuning:

| Observed case | What currently happens / remaining work |
|---|---|
| `hc-085`, `hc-093` | Both controlled and live fall back to another bottle; the expected subject's labels are lost even though the selected subject's labels survive. Improve subject/hand robustness without changing the frozen targets. |
| `hc-107` | Controlled replay confidently selects a contacted tool. Physical object discrimination remains incomplete. |
| `hc-143` | Both modes confidently apply `foreground_scale_and_lower_base` to a lower-shelf bottle where the required result is fallback. Support-plane ambiguity still needs resolution. |
| `hc-145`, `hc-146` | Selected ID happens to match, but both modes wrongly claim confident hand selection for rear end-contact. Correct ID and correct uncertainty mode are separate contracts. |
| `hc-152` | Crowded bucket scene falls back to a different bottle in both modes. Crop presence and full selected-label retention do not fix that decision failure. |
| `real-312192`, `real-520871`, `real-166918`, `real-117719`, `real-397354` | Saved live decisions mismatch the declared target or cannot be assigned to it. Some COCO competitor polygons are incomplete, so geometric policy results are conditional on available GT. Keep those limits visible. |

Other open limitations from the reviews include filled/amodal panel masks suppressing real bottle identity, large palm-front grips falling back after footprint caps, and unseen-real calibration. Keep the variant opt-in until independent photo evaluation and downstream recognition/latency checks justify a default change.

### Photorealistic v3 follow-up from the same conversation

This is the requested generator/harness workflow, **not a claim of a completed or owner-approved v3 release**:

- Controlled multi-instance recipes with separate instance IDs, transforms and layer order, including two copies of the same wine and zero-bottle controls. First family: two rear bottles near center plus one off-center foreground bottle, mirrored left/right, with similar-size and larger-rear controls.
- Reviewed complete front/back/neck/secondary-label masks for every scored competitor; permit corrected PNG imports. Preserve construction, detector, manual, reviewed and approximate provenance. A correctly transformed logo-only source mask is still not complete-label GT.
- Validate realized inventory, visibility, contact and placement on final rasterized masks. Preserve rejected attempts and reasons. Model-drawn background bottles and unreviewed SAM3 masks cannot silently become exhaustive independent GT; transparent visibility remains approximate.
- Declare intent, interactions, ambiguity and fallback target before selector predictions. Independently implement the policy oracle, cross-check all 38 v2 ambiguous cases and separately test empty candidates, rasterized ties and boundaries. Zero candidates explicitly expect a full-frame crop.
- Recommended architecture: generation/review in the service, shared schemas plus recipe/oracle/validation/freeze/export CLI in the generator repository; imported corrected PNGs rather than a required built-in editor. Agent proposals and actual owner approvals are distinct records. The conversation recommends batch sign-off before evaluation; an agent must not fabricate it.
- Start with an 8–12-image smoke batch for review, then at least 25 accepted photos. Exact ties remain controlled fixtures for the first milestone. Dataset recipe variants and derived probes are counted separately from independent photos.
- Export a new version without mutating frozen v1/v2 evidence. For the current harness, normalize images and all masks consistently: long side at most 1600 pixels and no residual EXIF orientation; exclusive-endpoint boxes and validated COCO RLE.
- Harness integration must cover `generated_photo` validation, declaration/hash freeze, prediction collection, controlled/live replay and HTML reporting with nonzero source denominators and correct attribution. The shared review specifically identified that changing validation alone would still skip or miscount generated photos.
- Do not infer that 2,028 catalogue records have rectangular masks from their conditional legacy settings description: that was rule metadata, and all eight masks sampled in the review were nonrectangular. Review each source asset rather than converting that metadata count into a mask-quality claim.

Generator implementation remains a separate workstream; adding this specification to the issue does not authorize generation, deployment, changing selector policy, or approving a batch.

### Source and artifact locations

These are **local workspace paths**, not uploaded GitHub attachments:

- Selector and optional adapter: `code/svoe-vino-lab-main-selector/matcher/semantic_selector.py`, `matcher/input_selector.py`, `matcher/service.py`, `matcher/cascade.py`, and `matcher/cascade_run.py` in that checkout.
- Complete current group descriptions: `datasets/main-selector-hardcases-v2/protocol.json`.
- HTML examples, masks, expected results and paired selectors: `/Volumes/Storage/svoe-vino-final/datasets/main-selector-hardcases-v2/report.html`.
- Frozen dataset evidence: `datasets/main-selector-hardcases-v2/README.md`, `receipt.json`, `cases.json`, `additional-findings.json`, `comparison.json`, declarations and manifests in that directory; portable package at `/Volumes/Storage/svoe-vino-final/datasets/main-selector-hardcases-v2.zip`.
- Generator handoff: `code/bottle-scene-gen/MISSING_FUNCTIONALITY_FOR_SELECTOR_DATASET.md`; implementation plan: `code/bottle-scene-gen/docs/plans/03_selector-hardcase-dataset.md`; review corrections: `planning/selector-bottle-scene-gen-plan-review-20261019/`.

The source and dataset work described here remain experimental; this issue edit publishes documentation, not source code, datasets, or a production rollout. New implementation directives and selection guidance in this guide are in English; original source identifiers and the earlier issue text below are preserved.

---

## Earlier experiment notes — preserved verbatim

The following section records the earlier v1 implementation/reviews. Its counts, metrics, local-code status and limitations belong to that evidence snapshot; the v2 summary above has its own frozen scope.

Экспериментальный `semantic-v2` исправлен для оставшихся сохранённых hand-confidence и printed-panel случаев. Он доступен рядом с `scene-v1`; дефолт не переключён. Код локальный, без commit/push/PR.

## Что исправлено

**Уникальный контакт больше не означает доказанный хват.** После независимого разрешения владельцев каждой руки требуется положительная геометрия: пересечение переднего контура, существенное покрытие передней области, локальный передний контакт или противоположные контакты у конца бутылки. Последний вариант сохраняет реальный пример наливания `real-541773`, у которого нет передних пикселей руки. В `grip_evidence` записаны измерения; историческое поле `confirmed_hand_owner` означает владельца контакта, а не подтверждение физического хвата.

- `hc-039` (указание) и `hc-041` (рука сзади в проекции) теперь используют **fallback в controlled и live**, в том числе при поворотах 90/180/270°.
- Положительные контроли `hc-033/040/042` и реальное наливание сохраняют выбор по руке. В `hc-016` controlled отсутствие контакта больше не выдаётся за хват. После замечания Claude восстановлена hand-priority для настоящих body grips `hc-020/024` live: локальный передний контакт ≥12% руки на участке 10–50% оси бутылки, занимающий не более 10% видимой площади маски бутылки. Off-center регрессии добавляют другую бутылку в центр кадра; удерживаемый предмет всё равно выбирается.
- Это геометрические development-эвристики, не обученная классификация позы или восстановление глубины. Стекло, обрезанная рука и незнакомые позы могут оставаться неоднозначными.

**Панель с изображением бутылки сохраняется как контекст.** Если бумажная маска содержит полный силуэт бутылки с запасом по всем сторонам, вложенный рисунок не считается отдельной физической бутылкой. Требуется совпадение видимых масок; одного большого bounding box недостаточно. В `hc-031` live остаётся полный `context_frame`, исчезают уверенный приоритет label-панели и отдельный кандидат нарисованной бутылки. Tap/явный прицел сохраняют приоритет, но бумага не обрезается.

**Исправлена отдельная ошибка оценки.** Старый evaluator искал для выбранного `wine label` только GT-этикетки, хотя в `hc-031` эта маска почти точно покрывает картон #200. Теперь максимальный IoU считается по всем размеченным регионам при IoU ≥0,30 независимо от предсказанного класса, одинаково для обоих селекторов; регион этикетки/печати сопоставляется его GT-родителю. Старый crop уже покрывал картон. Поэтому переход исходных passive-метрик semantic-v2 **25/26 → 26/26 является исправлением измерения, не приростом точности селектора**. `assignment-audit.json` пересчитывает те же старые выборы и отдельно показывает реальные изменения поведения. Для scene-v1 также переоценён `hc-046`: назначенный ID изменился, оценка «неверно» осталась.

**Контрпример из седьмого review воспроизведён и исправлен.** У `hc-039` controlled исходный span 0,575602 — всего на 0,075602 выше порога 0,50. Удаление только участка маски руки около бутылки (RGB и GT неизменны) даёт span 0,446961 и front/hand 0,148239: прежний recall-cue ошибочно объявлял хват. Новое ограничение front/bottle ≤0,10 отклоняет этот пример: отпечаток указующей руки около 34%, у `hc-020/024` около 6,6%/4,1%. В `grip-span-verification.json` сохранены точная трансформация, обе версии исходников, before/after, маска и crop. HTML показывает этот отдельный derived-контроль; он не считается новой фотографией или независимой accuracy. Проверено и удаление всего хвоста маски руки: front/hand растёт до 31,5% и обходил прежний broad-cue. Для bottle-кандидатов broad-front теперь ограничен front/bottle ≤25%; плоская упаковка сохраняет прежний контракт, владение контактом и наличие wine label не меняют приоритет. Обе версии detector-fragmentation теперь используют fallback при всех четверть-оборотах. Это development-порог, не общий grip classifier: небольшой указующий палец и сегментационные ошибки всё ещё могут имитировать хват.

## Обязательный crop и полные этикетки

Успешный ответ всегда содержит crop. После tap, руки, явного прицела и переднего плана неразрешённый выбор следует неизменному правилу:

1. Видимая маска содержит центр фотографии.
2. Иначе — ближайший центр bbox по евклидовому расстоянию в пикселях.
3. Точное равенство: левее → выше → меньший числовой ID.
4. Нет допустимых кандидатов — полное изображение после EXIF.

Сохраняются исходные пиксели полного прямоугольника предмета и связанных этикеток: бумага, текст, логотип, бирки и отогнутые края. Крупная непривязанная бумага сохраняет полный контекст на всех путях выбора, включая руку и tap. Скрытые пиксели и текст не генерируются. `selection_mode`, `fallback_trigger`, `crop_scope`, `tap_status`, `grip_evidence` и `panel_context` объясняют результат. Полный контекст может удерживать чужой текст; уверенный ID не обещает изолированный crop.

## Набор и контракты

- **124 случая, 831 бинарная маска:** 69 нативных рендеров, 5 прежних реальных COCO-фото и 50 отдельно оцениваемых geometry fixtures. В расширении остаются 37 рендеров, включая 7 трёхбутылочных сцен: передняя вне центра, перекрытие, край, слабая глубина, magnum сзади, tap назад и лежащая передняя. Все 7 проходят controlled/live.
- Все **74 фото, их GT, исходные маски и 143 prediction caches неизменны**. Новых запросов к моделям и новых real-photo примеров нет. Ранее найденные внешние источники остаются в HTML как неоцениваемый shortlist.
- Добавлены 3 geometry-контроля: неподтверждённый боковой контакт против центральной бутылки, противоположные контакты сзади в середине корпуса и панель со вложенным рисунком.
- **6 старых прямоугольных fixtures имели контракт «уникальное соседство = хват».** Контракт явно версионирован до исправления: при отсутствии положительных признаков теперь применяется геометрический fallback. Старые winner/reason/mode сохранены рядом с новыми в HTML и в историческом снимке. Изменения этих продуктовых policy-fixtures не считаются улучшением photo accuracy. Цели фотографий не менялись.
- Portable unit-тесты содержат замороженные маски существующих сцен, а не ответы, полученные новым запросом. Они проверяют геометрию на одноцветном canvas; HTML replay использует исходные RGB-фото и фиксированную GT.

## Текущие live-метрики

| Когорта: совпадение выбранного региона с GT | scene-v1 | semantic-v2 |
|---|---:|---:|
| Исходные пассивные цели | 25/26 | 26/26 |
| Новые пассивные цели — development-рендеры | 19/25 | 25/25 |
| Исходные взаимодействия | 3/4 | 4/4 |
| Новые взаимодействия | 0/3 | 3/3 |
| Исходные policy targets | 4/6 | 5/6 |
| Новые policy targets | 2/9 | 5/9 |
| Исходный no-target | 1/1 | 1/1 |

Для semantic-v2 все **15/15 live policy-случаев правильно помечены fallback**. Совместный контракт **ID + fallback = 10/15 live**, как и до исправления; controlled теперь **13/13**, ранее 11/13. Для legacy совместный контракт не применяется и не показывается как нулевой score.

Live `hc-039/041` остаются **ID-mismatch**: точные GT-ничьи выбирают левую бутылку, а немного асимметричные detector boxes делают правую ближе к центру. Раньше левый ID совпадал за счёт ошибочно уверенного выбора по руке. Теперь применяется правильный fallback; GT не подгонялась. `hc-025/035/056` также сохраняются как несовпадения GT/detector-геометрии. Все видны в HTML, включая неполное сохранение ожидаемого GT-предмета при выборе другой бутылки. Полнота этикеток фактически выбранного предмета проверяется отдельно.

Сохранение ≥98% пикселей GT-этикеток в passive: исходные **18/22 → 22/22**, новые **13/25 → 25/25**. Это не измерение распознавания конкретного вина. Когорты намерения, взаимодействия, policy, no-target и fixtures, а также уверенность и crop scope остаются раздельными.

## Проверки

- **332/332 matcher tests**, **108/108 focused tests**, **50/50 rule contracts**.
- Отдельная проверка фактического RGB crop: **134/134** фото-результата с label GT сохраняют **100%** размеченных пикселей этикеток выбранного предмета. Для пяти реальных фото label GT отсутствует.
- Все **193/193** основных результатов semantic-v2 возвращают crop. Во всех **592/592** штатных robustness-пробах (8 преобразований × 37 сцен × 2 режима) crop присутствует, сохранение этикеток выбранного предмета ≥98%; все 28 intent-defined случаев расширения сохраняют предмет при каждом преобразовании в обоих режимах.
- Проверены размеры/SHA-256/RLE/владельцы масок, 11 read-only source scenes и 37 заранее объявленных рецептов. Тестовые данные также входят в source/hash receipt.
- HTML проверен офлайн: данные, JS и **2450** изображений. Browser visual check ранее заблокирован политикой URL приложения; обхода не было.
- Ранний прогон 328 тестов под нагрузкой replay имел один timeout-sensitive сбой существующего cascade-теста. Отдельная проверка и повторный полный прогон прошли. Финальный прогон после footprint-исправлений — 332/332 без одновременной нагрузки replay. Cascade-код и тест не менялись; исходный лог сохранён в `planning/selector-confidence-20261019/full-tests-under-load.log`.

## Ограничения перед дефолтом

- **Открытый риск P2 из review:** противоположные контакты у конца бутылки могут быть имитированы рукой сзади у горлышка/основания. Эта геометрия не определяет порядок перекрытий; положительное terminal-свидетельство не является доказательством глубины.
- **Filled/amodal panel masks:** если детектор заливает фоновую бумагу поверх настоящей бутылки, её ID может быть ошибочно подавлен. Добавлены untapped visible/filled-контроли: оба сохраняют полное исходное RGB; для filled-сценария правильная физическая идентичность не заявляется. Требуются дополнительные независимые visual/pose/depth-признаки.
- Нужны независимая real-photo оценка и внешняя проверка целей пяти COCO-фото: в них нет label GT. Native/proxy-сцены коррелируют и использовались для настройки порогов.
- Прозрачные окна — открытая геометрия; отражение — виртуальный proxy; поза указания не проходила анатомическую валидацию.
- Заимствованные оси задних бутылок не отличают лежащую переднюю бутылку от magnum на нижней полке. Общий приоритет упаковки, чужие бирки и semantic-ошибки детектора остаются эвристиками.
- Production scene-v1 с 5 nouns отдельно не переизмерен: здесь оба варианта используют одни и те же 7 nouns. Ревизия SAM3 сервисом не раскрыта; сохранены точные байты ответов. Latency, лимит размера ответа и распознавание вина не проверялись. Default/cascade/Android не мигрированы.

## Артефакты и review

- HTML: `/Volumes/Storage/svoe-vino-final/datasets/main-selector-hardcases-v1/report.html`
- ZIP: `/Volumes/Storage/svoe-vino-final/datasets/main-selector-hardcases-v1.zip`; SHA-256 `026ab19e00d6cbe619935b3e66dd698c80531cee1b57875d630e4b0309101ba8`.
- `grip-span-verification.json`, `confidence-verification.json`, `grip-recall-verification.json`, `assignment-audit.json`, `confidence-contract-declaration.json`, `confidence-regression-declaration.json`, `comparison-inputs.json`, `prediction-inputs.json`, `comparison.json`, `perturbations.json`, `receipt.json`, `bundle-manifest.json`, `implementation.patch`.
- Снимок до этих исправлений: `main-selector-hardcases-v1-before-confidence-fixes` и ZIP; SHA-256 `e0545c2542528384c2945eded644b78948233d529bee4352c8630451e83914d3`. Старые отчёты и ревью сохранены; их показатели не приписываются текущей версии.
- Точная текущая ревизия: `2026-10-19-positive-grip-and-panel`.

Шестое read-only review Claude Opus 5.5 подтвердило исправление сохранённых ошибок и честность сравнения; отдельно указало потерю recall в body grips и terminal/panel неоднозначность. Recall восстановлен и проверен вне центра; terminal/panel риски открыто сохранены выше. Исходный review: `/Volumes/Storage/svoe-vino-final/planning/claude-opus-5-5-selector-review-20261018/round-6/review.md`. Проверенный им снимок сохранён в `main-selector-hardcases-v1-before-grip-recall-fixes` и ZIP (SHA-256 `80183ead338cd2013446a92a3c9b581fe097c241690165426c16de835f85345b`).

Седьмое review фактического Claude Opus 5.5 закрыло recall-дефект на сохранённых/off-center масках и указало на shortened-span риск. Этот риск независимо воспроизведён и исправлен через ограничение footprint; сохранены исходный review `round-7/review.md` и снимок `main-selector-hardcases-v1-before-span-control-fix` (ZIP SHA-256 `1fcb615a994c8d4b70fec6420ca22da1e6b32722bee5c1207a34831361bff395`).

Восьмое независимое read-only review **фактическим Claude Opus 5.5** (`claude-opus-5-5`) завершено. Контрпример с shortened span и обе detector-fragmentation версии исправлены; на сохранённых контролях **новых продемонстрированных P1/P2-дефектов не найдено**. Экспериментальный opt-in допустим; дефолт менять нельзя. Terminal mimicry, filled/amodal panel identity и unseen-real calibration остаются открытыми.

Review: `/Volumes/Storage/svoe-vino-final/planning/claude-opus-5-5-selector-review-20261018/round-8/review.md`; рядом `receipt.json`. Модель использовала 17 вызовов только Read/Grep/Glob и не запускала тесты/хеширование. После review Codex подтвердил неизменность 28 исходников и 3344 файлов пакета; ZIP и код соответствуют проверенной ревизии.

**Recall-стоимость footprint caps:** настоящий большой palm-front хват может перейти в fallback, особенно когда front/bottle >0,25 и нет wrap/terminal-свидетельств. Это открытый риск, а не обещание общего grip recognition. По просьбе reviewer ниже приведены все фактически выбранные bottle-кандидаты с положительной grip-геометрией в фото-replay. Это не внешняя GT-верификация физического хвата и не новая accuracy/recall-оценка. Два геометрически положительных, но не выбранных кандидата (`hc-038` controlled и `real-180751` live) отдельно сохранены в аудите: их переопределил контекстный конфликт.

Выборка: 59 положительных hand-detection строк в 50 photo-результатах. Несколько рук и controlled/live не являются независимыми фото. Максимальный front/bottle для broad-пути — 0.176471 при cap 0,25; если broad был единственным путём — 0.118509. Максимум для единственного localized-пути — 0.066237 при cap 0,10. Near-cap localized 0,099812 также имеет broad-поддержку, поэтому потеря только localized не меняет его решение.

<details>
<summary>Полный аудит выбранных bottle-кандидатов и путей подтверждения</summary>

| Случай / режим | Бутылка / рука | Front/hand | Front/bottle | Contact span | Пути геометрической поддержки |
|---|---|---:|---:|---:|---|
| hc-001 / controlled | d0 / d26 | 0.0992 | 0.0548 | 0.29153 | front_wrap |
| hc-001 / live | d6 / d23 | 0.1002 | 0.0568 | 0.288114 | front_wrap |
| hc-001 / live | d6 / d24 | 0.1369 | 0.0514 | 0.288114 | front_wrap, localized_front_contact |
| hc-002 / controlled | d0 / d26 | 0.2155 | 0.1126 | 0.384505 | front_wrap |
| hc-002 / live | d7 / d18 | 0.3489 | 0.0982 | 0.377982 | broad_front_contact, localized_front_contact |
| hc-003 / controlled | d0 / d25 | 0.1047 | 0.0651 | 0.3539 | front_wrap, terminal_opposition |
| hc-003 / live | d8 / d25 | 0.0902 | 0.0565 | 0.349473 | front_wrap, terminal_opposition |
| hc-003 / live | d8 / d26 | 0.1326 | 0.0567 | 0.349473 | front_wrap, localized_front_contact, terminal_opposition |
| hc-004 / controlled | d0 / d25 | 0.0511 | 0.0373 | 0.317589 | front_wrap, terminal_opposition |
| hc-004 / live | d6 / d25 | 0.1251 | 0.0447 | 0.310421 | front_wrap, localized_front_contact, terminal_opposition |
| hc-013 / controlled | d0 / d22 | 0.1287 | 0.0506 | 0.292112 | front_wrap, localized_front_contact |
| hc-013 / live | d0 / d21 | 0.1317 | 0.0528 | 0.288436 | front_wrap, localized_front_contact |
| hc-014 / controlled | d0 / d19 | 0.1995 | 0.1132 | 0.384506 | front_wrap |
| hc-014 / live | d0 / d13 | 0.3543 | 0.0988 | 0.381881 | broad_front_contact, localized_front_contact |
| hc-015 / controlled | d0 / d25 | 0.1047 | 0.0651 | 0.3539 | front_wrap, terminal_opposition |
| hc-015 / live | d6 / d23 | 0.0904 | 0.0565 | 0.349438 | front_wrap, terminal_opposition |
| hc-015 / live | d6 / d24 | 0.1337 | 0.0572 | 0.349438 | front_wrap, localized_front_contact, terminal_opposition |
| hc-017 / controlled | d0 / d23 | 0.2125 | 0.0869 | 0.284391 | front_wrap, localized_front_contact |
| hc-017 / live | d0 / d17 | 0.4344 | 0.0780 | 0.277849 | broad_front_contact, localized_front_contact |
| hc-017 / live | d0 / d18 | 0.1875 | 0.0774 | 0.277849 | front_wrap, localized_front_contact |
| hc-018 / controlled | d0 / d23 | 0.0783 | 0.0400 | 0.266457 | front_wrap, terminal_opposition |
| hc-018 / live | d6 / d22 | 0.0701 | 0.0203 | 0.266789 | front_wrap, terminal_opposition |
| hc-019 / controlled | d0 / d16 | 0.2494 | 0.0675 | 0.354319 | front_wrap, localized_front_contact, terminal_opposition |
| hc-019 / live | d1 / d14 | 0.2235 | 0.0609 | 0.355181 | front_wrap, localized_front_contact, terminal_opposition |
| hc-020 / controlled | d0 / d22 | 0.1615 | 0.0835 | 0.387249 | front_wrap, localized_front_contact |
| hc-020 / live | d4 / d22 | 0.2350 | 0.0662 | 0.381923 | localized_front_contact |
| hc-021 / controlled | d0 / d26 | 0.0992 | 0.0548 | 0.29153 | front_wrap |
| hc-021 / live | d6 / d24 | 0.0966 | 0.0545 | 0.288416 | front_wrap |
| hc-021 / live | d6 / d25 | 0.1339 | 0.0494 | 0.28784 | front_wrap, localized_front_contact |
| hc-022 / controlled | d0 / d26 | 0.2234 | 0.0863 | 0.284384 | front_wrap, localized_front_contact |
| hc-022 / live | d8 / d27 | 0.4334 | 0.0797 | 0.284802 | broad_front_contact, localized_front_contact |
| hc-022 / live | d8 / d28 | 0.2033 | 0.0795 | 0.27793 | front_wrap, localized_front_contact |
| hc-023 / controlled | d0 / d26 | 0.2155 | 0.1126 | 0.384505 | front_wrap |
| hc-023 / live | d7 / d18 | 0.3544 | 0.1000 | 0.378006 | broad_front_contact |
| hc-024 / controlled | d0 / d19 | 0.0912 | 0.0426 | 0.396043 | front_wrap |
| hc-024 / live | d5 / d16 | 0.1547 | 0.0412 | 0.386694 | localized_front_contact |
| hc-029 / controlled | d0 / d27 | 0.0992 | 0.0548 | 0.29153 | front_wrap |
| hc-029 / live | d6 / d24 | 0.1065 | 0.0610 | 0.287616 | front_wrap |
| hc-029 / live | d6 / d25 | 0.1468 | 0.0565 | 0.283565 | front_wrap, localized_front_contact |
| hc-030 / controlled | d0 / d25 | 0.2155 | 0.1126 | 0.384505 | front_wrap |
| hc-030 / live | d6 / d17 | 0.3544 | 0.0998 | 0.38188 | broad_front_contact, localized_front_contact |
| hc-033 / controlled | d0 / d4 | 0.0193 | 0.0328 | 0.366528 | front_wrap, terminal_opposition |
| hc-033 / live | d1 / d4 | 0.0891 | 0.0314 | 0.366126 | front_wrap, terminal_opposition |
| hc-034 / controlled | d0 / d4 | 0.1733 | 0.1089 | 0.498311 | front_wrap |
| hc-034 / live | d1 / d4 | 0.4258 | 0.1185 | 0.375082 | broad_front_contact |
| hc-036 / controlled | d0 / d2 | 0.1541 | 0.1111 | 0.459367 | front_wrap |
| hc-036 / controlled | d0 / d3 | 0.0860 | 0.0799 | 0.389849 | front_wrap |
| hc-036 / live | d0 / d2 | 0.2100 | 0.0660 | 0.375308 | localized_front_contact |
| hc-036 / live | d0 / d3 | 0.2971 | 0.1765 | 0.568772 | front_wrap, broad_front_contact |
| hc-037 / controlled | d0 / d4 | 0.0131 | 0.0356 | 0.369791 | front_wrap, terminal_opposition |
| hc-037 / live | d1 / d4 | 0.0855 | 0.0297 | 0.369612 | front_wrap, terminal_opposition |
| hc-040 / controlled | d0 / d4 | 0.1733 | 0.1089 | 0.498311 | front_wrap |
| hc-040 / live | d1 / d4 | 0.4203 | 0.1165 | 0.388997 | broad_front_contact |
| hc-042 / controlled | d0 / d4 | 0.0193 | 0.0328 | 0.366528 | front_wrap, terminal_opposition |
| hc-042 / live | d1 / d4 | 0.1136 | 0.0454 | 0.366328 | front_wrap, terminal_opposition |
| hc-047 / controlled | d0 / d4 | 0.0246 | 0.0396 | 0.363861 | front_wrap, terminal_opposition |
| hc-047 / live | d1 / d4 | 0.1176 | 0.0484 | 0.364723 | front_wrap, terminal_opposition |
| real-417632 / live | d1 / d11 | 0.1763 | 0.0548 | 0.421311 | front_wrap, localized_front_contact |
| real-541773 / live | d2 / d8 | 0.0000 | 0.0000 | 0.756563 | terminal_opposition |

</details>

Аудит: `/Volumes/Storage/svoe-vino-final/planning/selector-confidence-20261019/confirmed-grip-audit.json`, с SHA исходного `comparison.json`. Те же измерения присутствуют в раскрываемых деталях каждого случая HTML. Проверенный код, тестовые данные, GT, отчёт и ZIP после review не менялись; дополнено только описание issue этим аудитом.

Issue остаётся открытым для перечисленных рисков и независимой production-валидации. Код локальный, без commit/push/PR.
