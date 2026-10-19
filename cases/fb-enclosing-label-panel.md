# fb-enclosing-label-panel A complete panel encloses bottle artwork; preserve the panel context

[All cases](../README.md) · [Group](../groups/review.md) · [Exact case metadata](../evidence/fb-enclosing-label-panel.json)

**scene-v1:** Contract N/A; fallback: target differs  
**semantic-v2:** Recorded checks pass

![fb-enclosing-label-panel comparison](../previews/fb-enclosing-label-panel.jpg)

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

![Original fb-enclosing-label-panel](../assets/images/fb-enclosing-label-panel.png)

![Masks fb-enclosing-label-panel](../overlays/fb-enclosing-label-panel.png)

| Mask ID | Category | Parent | Expected subject or label | Original binary PNG |
|---|---|---|---|---|
| `1` | label_front | `None` | yes | [view raw mask](../assets/masks/fb-enclosing-label-panel-i1.png) |
| `2` | bottle | `None` |  | [view raw mask](../assets/masks/fb-enclosing-label-panel-i2.png) |
| `3` | label_front | `None` |  | [view raw mask](../assets/masks/fb-enclosing-label-panel-i3.png) |

## Declared detector input masks

These masks are the exact PNG bytes supplied as fixture detections. They may differ from the annotated expected geometry above. Source detector indices are not ground-truth instance IDs.

| Detector index | Class | Score | Input box | Original mask PNG |
|---|---|---:|---|---|
| `d0` | wine label | 0.9 | `[40, 10, 200, 230]` | [view input mask](../fixture-masks/fb-enclosing-label-panel-d0.png) |
| `d1` | wine bottle | 0.9 | `[90, 45, 150, 190]` | [view input mask](../fixture-masks/fb-enclosing-label-panel-d1.png) |
| `d2` | wine label | 0.9 | `[100, 120, 140, 160]` | [view input mask](../fixture-masks/fb-enclosing-label-panel-d2.png) |

## Saved selector outputs

`live` replays saved detector responses; `controlled` uses declared GT-derived detections and faults. No new inference was run for this gallery. Expected-label retention below 98% is flagged separately from target matching. A full-frame crop can retain distractors.

### fallback

| Selector | Result | Assigned subject | Mode | Expected-label retention | Reason |
|---|---|---|---|---|---|
| `scene-v1` | LEGACY: TARGET DIFFERS (new contract not scored) | `2` | `legacy` | not scored | `existing_scene_v1_rank` |
| `semantic-v2` | Recorded checks pass | `1` | `fallback` | not scored | `fallback_center_contains` |

#### scene-v1 fallback crop

![scene-v1 fallback crop](../assets/crops/fb-enclosing-label-panel-fallback-scene-v1.png)

[View original selector keep mask](../assets/crops/fb-enclosing-label-panel-fallback-scene-v1-keep.png)

#### semantic-v2 fallback crop

![semantic-v2 fallback crop](../assets/crops/fb-enclosing-label-panel-fallback-semantic-v2.png)

[View original selector keep mask](../assets/crops/fb-enclosing-label-panel-fallback-semantic-v2-keep.png)

Label crop views: [view 1](../assets/crops/fb-enclosing-label-panel-fallback-semantic-v2-label-0.png).
