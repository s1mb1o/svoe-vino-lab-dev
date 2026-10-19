# fb-multiple-grips-unheld-foreground Two confirmed grips block an unrelated unheld foreground bottle

[All cases](../README.md) · [Group](../groups/review.md) · [Exact case metadata](../evidence/fb-multiple-grips-unheld-foreground.json)

**scene-v1:** Contract N/A; fallback: target differs  
**semantic-v2:** Recorded checks pass

![fb-multiple-grips-unheld-foreground comparison](../previews/fb-multiple-grips-unheld-foreground.jpg)

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

![Original fb-multiple-grips-unheld-foreground](../assets/images/fb-multiple-grips-unheld-foreground.png)

![Masks fb-multiple-grips-unheld-foreground](../overlays/fb-multiple-grips-unheld-foreground.png)

| Mask ID | Category | Parent | Expected subject or label | Original binary PNG |
|---|---|---|---|---|
| `1` | bottle | `None` |  | [view raw mask](../assets/masks/fb-multiple-grips-unheld-foreground-i1.png) |
| `2` | bottle | `None` | yes | [view raw mask](../assets/masks/fb-multiple-grips-unheld-foreground-i2.png) |
| `3` | bottle | `None` |  | [view raw mask](../assets/masks/fb-multiple-grips-unheld-foreground-i3.png) |
| `4` | hand | `None` |  | [view raw mask](../assets/masks/fb-multiple-grips-unheld-foreground-i4.png) |
| `5` | hand | `None` |  | [view raw mask](../assets/masks/fb-multiple-grips-unheld-foreground-i5.png) |

## Declared detector input masks

These masks are the exact PNG bytes supplied as fixture detections. They may differ from the annotated expected geometry above. Source detector indices are not ground-truth instance IDs.

| Detector index | Class | Score | Input box | Original mask PNG |
|---|---|---:|---|---|
| `d0` | wine bottle | 0.9 | `[100, 100, 160, 300]` | [view input mask](../fixture-masks/fb-multiple-grips-unheld-foreground-d0.png) |
| `d1` | wine bottle | 0.9 | `[220, 100, 280, 300]` | [view input mask](../fixture-masks/fb-multiple-grips-unheld-foreground-d1.png) |
| `d2` | wine bottle | 0.9 | `[400, 150, 520, 470]` | [view input mask](../fixture-masks/fb-multiple-grips-unheld-foreground-d2.png) |
| `d3` | hand | 0.9 | `[160, 130, 180, 260]` | [view input mask](../fixture-masks/fb-multiple-grips-unheld-foreground-d3.png) |
| `d4` | hand | 0.9 | `[280, 130, 300, 260]` | [view input mask](../fixture-masks/fb-multiple-grips-unheld-foreground-d4.png) |

## Saved selector outputs

`live` replays saved detector responses; `controlled` uses declared GT-derived detections and faults. No new inference was run for this gallery. Expected-label retention below 98% is flagged separately from target matching. A full-frame crop can retain distractors.

### fallback

| Selector | Result | Assigned subject | Mode | Expected-label retention | Reason |
|---|---|---|---|---|---|
| `scene-v1` | LEGACY: TARGET DIFFERS (new contract not scored) | `3` | `legacy` | not scored | `existing_scene_v1_rank` |
| `semantic-v2` | Recorded checks pass | `2` | `fallback` | not scored | `fallback_nearest_center` |

#### scene-v1 fallback crop

![scene-v1 fallback crop](../assets/crops/fb-multiple-grips-unheld-foreground-fallback-scene-v1.png)

[View original selector keep mask](../assets/crops/fb-multiple-grips-unheld-foreground-fallback-scene-v1-keep.png)

#### semantic-v2 fallback crop

![semantic-v2 fallback crop](../assets/crops/fb-multiple-grips-unheld-foreground-fallback-semantic-v2.png)

[View original selector keep mask](../assets/crops/fb-multiple-grips-unheld-foreground-fallback-semantic-v2-keep.png)
