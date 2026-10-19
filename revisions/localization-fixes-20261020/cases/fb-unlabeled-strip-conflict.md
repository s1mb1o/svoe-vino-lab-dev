# fb-unlabeled-strip-conflict An unlabeled held strip cannot confidently override a much larger centered labeled bottle

[All cases](../README.md) · [Group](../groups/review.md) · [Exact case metadata](../evidence/fb-unlabeled-strip-conflict.json)

**scene-v1:** Contract N/A; fallback: target match  
**semantic-v2:** Recorded checks pass

![fb-unlabeled-strip-conflict comparison](../previews/fb-unlabeled-strip-conflict.jpg)

## Expected result

- Group: `review`; provenance: `geometry_fixture`.
- Expected subject: `1`; acceptable IDs: `[1]`.
- Expected status: `selected`; expected selection mode: `fallback`.
- Interaction: `{}`.
- Annotation source: declared geometry fixture.
- Complete label GT: `False`.

Diagnostic geometry fixture, not a photograph or model output. The gold crosshair marks the photo center; no aim is supplied unless declared.

This is a diagnostic geometry fixture, not a photo. Annotated expected geometry and detector input masks are identified separately below. The new selector contract is not scored as legacy scene-v1 accuracy; target differences are shown only as observations.

## Original input and masks

![Original fb-unlabeled-strip-conflict](../assets/images/fb-unlabeled-strip-conflict.png)

![Masks fb-unlabeled-strip-conflict](../overlays/fb-unlabeled-strip-conflict.png)

| Mask ID | Category | Parent | Expected subject or label | Original binary PNG |
|---|---|---|---|---|
| `1` | bottle | `None` | yes | [view raw mask](../assets/masks/fb-unlabeled-strip-conflict-i1.png) |
| `2` | label_front | `None` |  | [view raw mask](../assets/masks/fb-unlabeled-strip-conflict-i2.png) |
| `3` | bottle | `None` |  | [view raw mask](../assets/masks/fb-unlabeled-strip-conflict-i3.png) |
| `4` | hand | `None` |  | [view raw mask](../assets/masks/fb-unlabeled-strip-conflict-i4.png) |

## Declared detector input masks

These masks are the exact PNG bytes supplied as fixture detections. They may differ from the annotated expected geometry above. Source detector indices are not ground-truth instance IDs.

| Detector index | Class | Score | Input box | Original mask PNG |
|---|---|---:|---|---|
| `d0` | wine bottle | 0.9 | `[80, 10, 160, 230]` | [view input mask](../fixture-masks/fb-unlabeled-strip-conflict-d0.png) |
| `d1` | wine label | 0.9 | `[90, 100, 150, 190]` | [view input mask](../fixture-masks/fb-unlabeled-strip-conflict-d1.png) |
| `d2` | wine bottle | 0.9 | `[5, 30, 75, 42]` | [view input mask](../fixture-masks/fb-unlabeled-strip-conflict-d2.png) |
| `d3` | hand | 0.9 | `[5, 42, 75, 65]` | [view input mask](../fixture-masks/fb-unlabeled-strip-conflict-d3.png) |

## Saved selector outputs

`live` replays saved detector responses; `controlled` uses declared GT-derived detections and faults. No new inference was run for this gallery. Expected-label retention below 98% is flagged separately from target matching. A full-frame crop can retain distractors.

### fallback

| Selector | Result | Assigned subject | Mode | Expected-label retention | Reason |
|---|---|---|---|---|---|
| `scene-v1` | LEGACY: TARGET MATCH (new contract not scored) | `1` | `legacy` | not scored | `existing_scene_v1_rank` |
| `semantic-v2` | Recorded checks pass | `1` | `fallback` | not scored | `fallback_center_contains` |

#### scene-v1 fallback crop

![scene-v1 fallback crop](../assets/crops/fb-unlabeled-strip-conflict-fallback-scene-v1.png)

[View original selector keep mask](../assets/crops/fb-unlabeled-strip-conflict-fallback-scene-v1-keep.png)

#### semantic-v2 fallback crop

![semantic-v2 fallback crop](../assets/crops/fb-unlabeled-strip-conflict-fallback-semantic-v2.png)

[View original selector keep mask](../assets/crops/fb-unlabeled-strip-conflict-fallback-semantic-v2-keep.png)

Label crop views: [view 1](../assets/crops/fb-unlabeled-strip-conflict-fallback-semantic-v2-label-0.png).
