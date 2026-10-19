# fb-upper Equal distance and x: upper wins

[All cases](../README.md) · [Group](../groups/fallback.md) · [Exact case metadata](../evidence/fb-upper.json)

**scene-v1:** Contract N/A; fallback: target differs  
**semantic-v2:** Recorded checks pass

![fb-upper comparison](../previews/fb-upper.jpg)

## Expected result

- Group: `fallback`; provenance: `geometry_fixture`.
- Expected subject: `2`; acceptable IDs: `[2]`.
- Expected status: `selected`; expected selection mode: `fallback`.
- Interaction: `{}`.
- Annotation source: declared geometry fixture.
- Complete label GT: `False`.

Diagnostic geometry fixture, not a photograph or model output. The gold crosshair marks the photo center; no aim is supplied unless declared.

This is a diagnostic geometry fixture, not a photo. Annotated expected geometry and detector input masks are identified separately below. The new selector contract is not scored as legacy scene-v1 accuracy; target differences are shown only as observations.

## Original input and masks

![Original fb-upper](../assets/images/fb-upper.png)

![Masks fb-upper](../overlays/fb-upper.png)

| Mask ID | Category | Parent | Expected subject or label | Original binary PNG |
|---|---|---|---|---|
| `1` | bottle | `None` |  | [view raw mask](../assets/masks/fb-upper-i1.png) |
| `2` | bottle | `None` | yes | [view raw mask](../assets/masks/fb-upper-i2.png) |

## Declared detector input masks

These masks are the exact PNG bytes supplied as fixture detections. They may differ from the annotated expected geometry above. Source detector indices are not ground-truth instance IDs.

| Detector index | Class | Score | Input box | Original mask PNG |
|---|---|---:|---|---|
| `d0` | wine bottle | 0.9 | `[100, 150, 140, 230]` | [view input mask](../fixture-masks/fb-upper-d0.png) |
| `d1` | wine bottle | 0.9 | `[100, 10, 140, 90]` | [view input mask](../fixture-masks/fb-upper-d1.png) |

## Saved selector outputs

`live` replays saved detector responses; `controlled` uses declared GT-derived detections and faults. No new inference was run for this gallery. Expected-label retention below 98% is flagged separately from target matching. A full-frame crop can retain distractors.

### fallback

| Selector | Result | Assigned subject | Mode | Expected-label retention | Reason |
|---|---|---|---|---|---|
| `scene-v1` | LEGACY: TARGET DIFFERS (new contract not scored) | `1` | `legacy` | not scored | `existing_scene_v1_rank` |
| `semantic-v2` | Recorded checks pass | `2` | `fallback` | not scored | `fallback_uppermost` |

#### scene-v1 fallback crop

![scene-v1 fallback crop](../assets/crops/fb-upper-fallback-scene-v1.png)

[View original selector keep mask](../assets/crops/fb-upper-fallback-scene-v1-keep.png)

#### semantic-v2 fallback crop

![semantic-v2 fallback crop](../assets/crops/fb-upper-fallback-semantic-v2.png)

[View original selector keep mask](../assets/crops/fb-upper-fallback-semantic-v2-keep.png)
