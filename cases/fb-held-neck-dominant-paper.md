# fb-held-neck-dominant-paper A held neck cannot discard an unowned complete label (contact alone is unconfirmed; use geometric fallback)

[All cases](../README.md) · [Group](../groups/review.md) · [Exact case metadata](../evidence/fb-held-neck-dominant-paper.json)

**scene-v1:** Contract N/A; fallback: target differs  
**semantic-v2:** Recorded checks pass

![fb-held-neck-dominant-paper comparison](../previews/fb-held-neck-dominant-paper.jpg)

## Expected result

- Group: `review`; provenance: `geometry_fixture`.
- Expected subject: `2`; acceptable IDs: `[2]`.
- Expected status: `selected`; expected selection mode: `fallback`.
- Interaction: `{}`.
- Annotation source: declared geometry fixture.
- Complete label GT: `False`.

Diagnostic geometry fixture, not a photograph or model output. The gold crosshair marks the photo center; no aim is supplied unless declared.

This is a diagnostic geometry fixture, not a photo. Annotated expected geometry and detector input masks are identified separately below. The new selector contract is not scored as legacy scene-v1 accuracy; target differences are shown only as observations.

## Original input and masks

![Original fb-held-neck-dominant-paper](../assets/images/fb-held-neck-dominant-paper.png)

![Masks fb-held-neck-dominant-paper](../overlays/fb-held-neck-dominant-paper.png)

| Mask ID | Category | Parent | Expected subject or label | Original binary PNG |
|---|---|---|---|---|
| `1` | bottle | `None` |  | [view raw mask](../assets/masks/fb-held-neck-dominant-paper-i1.png) |
| `2` | label_front | `None` | yes | [view raw mask](../assets/masks/fb-held-neck-dominant-paper-i2.png) |
| `3` | hand | `None` |  | [view raw mask](../assets/masks/fb-held-neck-dominant-paper-i3.png) |

## Declared detector input masks

These masks are the exact PNG bytes supplied as fixture detections. They may differ from the annotated expected geometry above. Source detector indices are not ground-truth instance IDs.

| Detector index | Class | Score | Input box | Original mask PNG |
|---|---|---:|---|---|
| `d0` | wine bottle | 0.9 | `[60, 10, 100, 100]` | [view input mask](../fixture-masks/fb-held-neck-dominant-paper-d0.png) |
| `d1` | wine label | 0.9 | `[10, 100, 160, 230]` | [view input mask](../fixture-masks/fb-held-neck-dominant-paper-d1.png) |
| `d2` | hand | 0.9 | `[100, 20, 125, 90]` | [view input mask](../fixture-masks/fb-held-neck-dominant-paper-d2.png) |

## Saved selector outputs

`live` replays saved detector responses; `controlled` uses declared GT-derived detections and faults. No new inference was run for this gallery. Expected-label retention below 98% is flagged separately from target matching. A full-frame crop can retain distractors.

### fallback

| Selector | Result | Assigned subject | Mode | Expected-label retention | Reason |
|---|---|---|---|---|---|
| `scene-v1` | LEGACY: TARGET DIFFERS (new contract not scored) | `1` | `legacy` | not scored | `existing_scene_v1_rank` |
| `semantic-v2` | Recorded checks pass | `2` | `fallback` | not scored | `fallback_center_contains` |

#### scene-v1 fallback crop

![scene-v1 fallback crop](../assets/crops/fb-held-neck-dominant-paper-fallback-scene-v1.png)

[View original selector keep mask](../assets/crops/fb-held-neck-dominant-paper-fallback-scene-v1-keep.png)

#### semantic-v2 fallback crop

![semantic-v2 fallback crop](../assets/crops/fb-held-neck-dominant-paper-fallback-semantic-v2.png)

[View original selector keep mask](../assets/crops/fb-held-neck-dominant-paper-fallback-semantic-v2-keep.png)

Label crop views: [view 1](../assets/crops/fb-held-neck-dominant-paper-fallback-semantic-v2-label-0.png).
