# fb-dominant-label-price-conflict A dominant real label also classified as price tag keeps full context

[All cases](../README.md) · [Group](../groups/review.md) · [Exact case metadata](../evidence/fb-dominant-label-price-conflict.json)

**scene-v1:** Contract N/A; fallback: target differs  
**semantic-v2:** Recorded checks pass

![fb-dominant-label-price-conflict comparison](../previews/fb-dominant-label-price-conflict.jpg)

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

![Original fb-dominant-label-price-conflict](../assets/images/fb-dominant-label-price-conflict.png)

![Masks fb-dominant-label-price-conflict](../overlays/fb-dominant-label-price-conflict.png)

| Mask ID | Category | Parent | Expected subject or label | Original binary PNG |
|---|---|---|---|---|
| `1` | label_front | `None` | yes | [view raw mask](../assets/masks/fb-dominant-label-price-conflict-i1.png) |
| `2` | packet | `None` |  | [view raw mask](../assets/masks/fb-dominant-label-price-conflict-i2.png) |
| `3` | price tag | `None` |  | [view raw mask](../assets/masks/fb-dominant-label-price-conflict-i3.png) |

## Declared detector input masks

These masks are the exact PNG bytes supplied as fixture detections. They may differ from the annotated expected geometry above. Source detector indices are not ground-truth instance IDs.

| Detector index | Class | Score | Input box | Original mask PNG |
|---|---|---:|---|---|
| `d0` | wine label | 0.9 | `[60, 40, 180, 200]` | [view input mask](../fixture-masks/fb-dominant-label-price-conflict-d0.png) |
| `d1` | packet | 0.9 | `[190, 100, 235, 160]` | [view input mask](../fixture-masks/fb-dominant-label-price-conflict-d1.png) |
| `d2` | price tag | 0.9 | `[60, 40, 180, 200]` | [view input mask](../fixture-masks/fb-dominant-label-price-conflict-d2.png) |

## Saved selector outputs

`live` replays saved detector responses; `controlled` uses declared GT-derived detections and faults. No new inference was run for this gallery. Expected-label retention below 98% is flagged separately from target matching. A full-frame crop can retain distractors.

### fallback

| Selector | Result | Assigned subject | Mode | Expected-label retention | Reason |
|---|---|---|---|---|---|
| `scene-v1` | LEGACY: TARGET DIFFERS (new contract not scored) | `2` | `legacy` | not scored | `existing_scene_v1_rank` |
| `semantic-v2` | Recorded checks pass | `1` | `fallback` | not scored | `fallback_center_contains` |

#### scene-v1 fallback crop

![scene-v1 fallback crop](../assets/crops/fb-dominant-label-price-conflict-fallback-scene-v1.png)

[View original selector keep mask](../assets/crops/fb-dominant-label-price-conflict-fallback-scene-v1-keep.png)

#### semantic-v2 fallback crop

![semantic-v2 fallback crop](../assets/crops/fb-dominant-label-price-conflict-fallback-semantic-v2.png)

[View original selector keep mask](../assets/crops/fb-dominant-label-price-conflict-fallback-semantic-v2-keep.png)

Label crop views: [view 1](../assets/crops/fb-dominant-label-price-conflict-fallback-semantic-v2-label-0.png).
