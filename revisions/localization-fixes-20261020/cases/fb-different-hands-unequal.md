# fb-different-hands-unequal Different hands holding two bottles cannot manufacture a unique grip

[All cases](../README.md) · [Group](../groups/review.md) · [Exact case metadata](../evidence/fb-different-hands-unequal.json)

**scene-v1:** Contract N/A; fallback: target match  
**semantic-v2:** Recorded checks pass

![fb-different-hands-unequal comparison](../previews/fb-different-hands-unequal.jpg)

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

![Original fb-different-hands-unequal](../assets/images/fb-different-hands-unequal.png)

![Masks fb-different-hands-unequal](../overlays/fb-different-hands-unequal.png)

| Mask ID | Category | Parent | Expected subject or label | Original binary PNG |
|---|---|---|---|---|
| `1` | bottle | `None` | yes | [view raw mask](../assets/masks/fb-different-hands-unequal-i1.png) |
| `2` | bottle | `None` |  | [view raw mask](../assets/masks/fb-different-hands-unequal-i2.png) |
| `3` | hand | `None` |  | [view raw mask](../assets/masks/fb-different-hands-unequal-i3.png) |
| `4` | hand | `None` |  | [view raw mask](../assets/masks/fb-different-hands-unequal-i4.png) |

## Declared detector input masks

These masks are the exact PNG bytes supplied as fixture detections. They may differ from the annotated expected geometry above. Source detector indices are not ground-truth instance IDs.

| Detector index | Class | Score | Input box | Original mask PNG |
|---|---|---:|---|---|
| `d0` | wine bottle | 0.9 | `[15, 20, 85, 230]` | [view input mask](../fixture-masks/fb-different-hands-unequal-d0.png) |
| `d1` | wine bottle | 0.9 | `[155, 20, 225, 230]` | [view input mask](../fixture-masks/fb-different-hands-unequal-d1.png) |
| `d2` | hand | 0.9 | `[85, 80, 115, 190]` | [view input mask](../fixture-masks/fb-different-hands-unequal-d2.png) |
| `d3` | hand | 0.9 | `[125, 130, 155, 160]` | [view input mask](../fixture-masks/fb-different-hands-unequal-d3.png) |

## Saved selector outputs

`live` replays saved detector responses; `controlled` uses declared GT-derived detections and faults. No new inference was run for this gallery. Expected-label retention below 98% is flagged separately from target matching. A full-frame crop can retain distractors.

### fallback

| Selector | Result | Assigned subject | Mode | Expected-label retention | Reason |
|---|---|---|---|---|---|
| `scene-v1` | LEGACY: TARGET MATCH (new contract not scored) | `1` | `legacy` | not scored | `existing_scene_v1_rank` |
| `semantic-v2` | Recorded checks pass | `1` | `fallback` | not scored | `fallback_leftmost` |

#### scene-v1 fallback crop

![scene-v1 fallback crop](../assets/crops/fb-different-hands-unequal-fallback-scene-v1.png)

[View original selector keep mask](../assets/crops/fb-different-hands-unequal-fallback-scene-v1-keep.png)

#### semantic-v2 fallback crop

![semantic-v2 fallback crop](../assets/crops/fb-different-hands-unequal-fallback-semantic-v2.png)

[View original selector keep mask](../assets/crops/fb-different-hands-unequal-fallback-semantic-v2-keep.png)
