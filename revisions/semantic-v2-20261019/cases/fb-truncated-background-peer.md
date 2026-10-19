# fb-truncated-background-peer A truncated background silhouette cannot establish a foreground size ratio

[All cases](../README.md) · [Group](../groups/review.md) · [Exact case metadata](../evidence/fb-truncated-background-peer.json)

**scene-v1:** Contract N/A; fallback: target match  
**semantic-v2:** Recorded checks pass

![fb-truncated-background-peer comparison](../previews/fb-truncated-background-peer.jpg)

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

![Original fb-truncated-background-peer](../assets/images/fb-truncated-background-peer.png)

![Masks fb-truncated-background-peer](../overlays/fb-truncated-background-peer.png)

| Mask ID | Category | Parent | Expected subject or label | Original binary PNG |
|---|---|---|---|---|
| `1` | bottle | `None` |  | [view raw mask](../assets/masks/fb-truncated-background-peer-i1.png) |
| `2` | bottle | `None` | yes | [view raw mask](../assets/masks/fb-truncated-background-peer-i2.png) |
| `3` | bottle | `None` |  | [view raw mask](../assets/masks/fb-truncated-background-peer-i3.png) |

## Declared detector input masks

These masks are the exact PNG bytes supplied as fixture detections. They may differ from the annotated expected geometry above. Source detector indices are not ground-truth instance IDs.

| Detector index | Class | Score | Input box | Original mask PNG |
|---|---|---:|---|---|
| `d0` | wine bottle | 0.9 | `[0, 0, 70, 240]` | [view input mask](../fixture-masks/fb-truncated-background-peer-d0.png) |
| `d1` | wine bottle | 0.9 | `[100, 0, 145, 150]` | [view input mask](../fixture-masks/fb-truncated-background-peer-d1.png) |
| `d2` | wine bottle | 0.9 | `[165, 65, 220, 215]` | [view input mask](../fixture-masks/fb-truncated-background-peer-d2.png) |

## Saved selector outputs

`live` replays saved detector responses; `controlled` uses declared GT-derived detections and faults. No new inference was run for this gallery. Expected-label retention below 98% is flagged separately from target matching. A full-frame crop can retain distractors.

### fallback

| Selector | Result | Assigned subject | Mode | Expected-label retention | Reason |
|---|---|---|---|---|---|
| `scene-v1` | LEGACY: TARGET MATCH (new contract not scored) | `2` | `legacy` | not scored | `existing_scene_v1_rank` |
| `semantic-v2` | Recorded checks pass | `2` | `fallback` | not scored | `fallback_center_contains` |

#### scene-v1 fallback crop

![scene-v1 fallback crop](../assets/crops/fb-truncated-background-peer-fallback-scene-v1.png)

[View original selector keep mask](../assets/crops/fb-truncated-background-peer-fallback-scene-v1-keep.png)

#### semantic-v2 fallback crop

![semantic-v2 fallback crop](../assets/crops/fb-truncated-background-peer-fallback-semantic-v2.png)

[View original selector keep mask](../assets/crops/fb-truncated-background-peer-fallback-semantic-v2-keep.png)
