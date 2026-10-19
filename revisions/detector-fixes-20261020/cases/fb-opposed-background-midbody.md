# fb-opposed-background-midbody Opposed background skin without front or terminal evidence is not a grip

[All cases](../README.md) · [Group](../groups/review.md) · [Exact case metadata](../evidence/fb-opposed-background-midbody.json)

**scene-v1:** Contract N/A; fallback: target match  
**semantic-v2:** Recorded checks pass

![fb-opposed-background-midbody comparison](../previews/fb-opposed-background-midbody.jpg)

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

![Original fb-opposed-background-midbody](../assets/images/fb-opposed-background-midbody.png)

![Masks fb-opposed-background-midbody](../overlays/fb-opposed-background-midbody.png)

| Mask ID | Category | Parent | Expected subject or label | Original binary PNG |
|---|---|---|---|---|
| `1` | bottle | `None` | yes | [view raw mask](../assets/masks/fb-opposed-background-midbody-i1.png) |
| `2` | bottle | `None` |  | [view raw mask](../assets/masks/fb-opposed-background-midbody-i2.png) |
| `3` | hand | `None` |  | [view raw mask](../assets/masks/fb-opposed-background-midbody-i3.png) |

## Declared detector input masks

These masks are the exact PNG bytes supplied as fixture detections. They may differ from the annotated expected geometry above. Source detector indices are not ground-truth instance IDs.

| Detector index | Class | Score | Input box | Original mask PNG |
|---|---|---:|---|---|
| `d0` | wine bottle | 0.9 | `[70, 20, 140, 230]` | [view input mask](../fixture-masks/fb-opposed-background-midbody-d0.png) |
| `d1` | wine bottle | 0.9 | `[180, 20, 230, 230]` | [view input mask](../fixture-masks/fb-opposed-background-midbody-d1.png) |
| `d2` | hand | 0.9 | `[50, 80, 160, 140]` | [view input mask](../fixture-masks/fb-opposed-background-midbody-d2.png) |

## Saved selector outputs

`live` replays saved detector responses; `controlled` uses declared GT-derived detections and faults. No new inference was run for this gallery. Expected-label retention below 98% is flagged separately from target matching. A full-frame crop can retain distractors.

### fallback

| Selector | Result | Assigned subject | Mode | Expected-label retention | Reason |
|---|---|---|---|---|---|
| `scene-v1` | LEGACY: TARGET MATCH (new contract not scored) | `1` | `legacy` | not scored | `existing_scene_v1_rank` |
| `semantic-v2` | Recorded checks pass | `1` | `fallback` | not scored | `fallback_center_contains` |

#### scene-v1 fallback crop

![scene-v1 fallback crop](../assets/crops/fb-opposed-background-midbody-fallback-scene-v1.png)

[View original selector keep mask](../assets/crops/fb-opposed-background-midbody-fallback-scene-v1-keep.png)

#### semantic-v2 fallback crop

![semantic-v2 fallback crop](../assets/crops/fb-opposed-background-midbody-fallback-semantic-v2.png)

[View original selector keep mask](../assets/crops/fb-opposed-background-midbody-fallback-semantic-v2-keep.png)
