# fb-no-candidates No candidate: unchanged full image

[All cases](../README.md) · [Group](../groups/fallback.md) · [Exact case metadata](../evidence/fb-no-candidates.json)

**scene-v1:** Contract N/A; fallback: target match  
**semantic-v2:** Recorded checks pass

![fb-no-candidates comparison](../previews/fb-no-candidates.jpg)

## Expected result

- Group: `fallback`; provenance: `geometry_fixture`.
- Expected subject: `None`; acceptable IDs: `[]`.
- Expected status: `no_target`; expected selection mode: `fallback`.
- Interaction: `{}`.
- Annotation source: declared geometry fixture.
- Complete label GT: `False`.

Diagnostic geometry fixture, not a photograph or model output. The gold crosshair marks the photo center; no aim is supplied unless declared.

This is a diagnostic geometry fixture, not a photo. Annotated expected geometry and detector input masks are identified separately below. The new selector contract is not scored as legacy scene-v1 accuracy; target differences are shown only as observations.

## Original input and masks

![Original fb-no-candidates](../assets/images/fb-no-candidates.png)

![Masks fb-no-candidates](../overlays/fb-no-candidates.png)

| Mask ID | Category | Parent | Expected subject or label | Original binary PNG |
|---|---|---|---|---|
| none | no eligible masks | | full frame | |

## Declared detector input masks

These masks are the exact PNG bytes supplied as fixture detections. They may differ from the annotated expected geometry above. Source detector indices are not ground-truth instance IDs.

| Detector index | Class | Score | Input box | Original mask PNG |
|---|---|---:|---|---|

## Saved selector outputs

`live` replays saved detector responses; `controlled` uses declared GT-derived detections and faults. No new inference was run for this gallery. Expected-label retention below 98% is flagged separately from target matching. A full-frame crop can retain distractors.

### fallback

| Selector | Result | Assigned subject | Mode | Expected-label retention | Reason |
|---|---|---|---|---|---|
| `scene-v1` | LEGACY: TARGET MATCH (new contract not scored) | `None` | `legacy` | not scored | `existing_original_frame_fallback` |
| `semantic-v2` | Recorded checks pass | `None` | `fallback` | not scored | `fallback_original_frame` |

#### scene-v1 fallback crop

![scene-v1 fallback crop](../assets/crops/fb-no-candidates-fallback-scene-v1.png)

[View original selector keep mask](../assets/crops/fb-no-candidates-fallback-scene-v1-keep.png)

#### semantic-v2 fallback crop

![semantic-v2 fallback crop](../assets/crops/fb-no-candidates-fallback-semantic-v2.png)

[View original selector keep mask](../assets/crops/fb-no-candidates-fallback-semantic-v2-keep.png)
