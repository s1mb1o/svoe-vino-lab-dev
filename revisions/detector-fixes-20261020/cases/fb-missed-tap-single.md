# fb-missed-tap-single Missed tap continues to the single candidate

[All cases](../README.md) · [Group](../groups/review.md) · [Exact case metadata](../evidence/fb-missed-tap-single.json)

**scene-v1:** Contract N/A; fallback: target match  
**semantic-v2:** Recorded checks pass

![fb-missed-tap-single comparison](../previews/fb-missed-tap-single.jpg)

## Expected result

- Group: `review`; provenance: `geometry_fixture`.
- Expected subject: `1`; acceptable IDs: `[1]`.
- Expected status: `selected`; expected selection mode: `confident`.
- Interaction: `{"tap": [0, 0]}`.
- Annotation source: declared geometry fixture.
- Complete label GT: `False`.

Diagnostic geometry fixture, not a photograph or model output. The gold crosshair marks the photo center; no aim is supplied unless declared.

This is a diagnostic geometry fixture, not a photo. Annotated expected geometry and detector input masks are identified separately below. The new selector contract is not scored as legacy scene-v1 accuracy; target differences are shown only as observations.

## Original input and masks

![Original fb-missed-tap-single](../assets/images/fb-missed-tap-single.png)

![Masks fb-missed-tap-single](../overlays/fb-missed-tap-single.png)

| Mask ID | Category | Parent | Expected subject or label | Original binary PNG |
|---|---|---|---|---|
| `1` | bottle | `None` | yes | [view raw mask](../assets/masks/fb-missed-tap-single-i1.png) |

## Declared detector input masks

These masks are the exact PNG bytes supplied as fixture detections. They may differ from the annotated expected geometry above. Source detector indices are not ground-truth instance IDs.

| Detector index | Class | Score | Input box | Original mask PNG |
|---|---|---:|---|---|
| `d0` | wine bottle | 0.9 | `[70, 10, 170, 235]` | [view input mask](../fixture-masks/fb-missed-tap-single-d0.png) |

## Saved selector outputs

`live` replays saved detector responses; `controlled` uses declared GT-derived detections and faults. No new inference was run for this gallery. Expected-label retention below 98% is flagged separately from target matching. A full-frame crop can retain distractors.

### fallback

| Selector | Result | Assigned subject | Mode | Expected-label retention | Reason |
|---|---|---|---|---|---|
| `scene-v1` | LEGACY: TARGET MATCH (new contract not scored) | `1` | `legacy` | not scored | `existing_scene_v1_rank` |
| `semantic-v2` | Recorded checks pass | `1` | `confident` | not scored | `only_credible_subject` |

#### scene-v1 fallback crop

![scene-v1 fallback crop](../assets/crops/fb-missed-tap-single-fallback-scene-v1.png)

[View original selector keep mask](../assets/crops/fb-missed-tap-single-fallback-scene-v1-keep.png)

#### semantic-v2 fallback crop

![semantic-v2 fallback crop](../assets/crops/fb-missed-tap-single-fallback-semantic-v2.png)

[View original selector keep mask](../assets/crops/fb-missed-tap-single-fallback-semantic-v2-keep.png)
