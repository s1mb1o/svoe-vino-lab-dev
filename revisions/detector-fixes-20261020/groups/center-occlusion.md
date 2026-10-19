# Photo center through an occluder

[All groups](../README.md)

Balanced bottles with the center covered by a foreground glass or by the bottle itself. Targets follow visible GT mask geometry, separately from intent.

5 cases. Failures below use frozen result fields; photos and fixtures retain separate interpretation.

| Case | scene-v1 | semantic-v2 |
|---|---|---|
| [hc-057 center_glass_occlusion](../cases/hc-057.md) | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS, live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-058 center_visible_bottle](../cases/hc-058.md) | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS, live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-126 center_glass_occlusion__new_view_and_light](../cases/hc-126.md) | **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS, live: WRONG TARGET; EXPECTED LABEL LOSS | Recorded checks pass |
| [hc-127 center_visible_bottle__new_view_and_light](../cases/hc-127.md) | Recorded checks pass | Recorded checks pass |
| [real-397354 people_occlude_party_table_bottles](../cases/real-397354.md) | Recorded checks pass | **FAIL** live: WRONG TARGET |

## Visual examples

### hc-057 center_glass_occlusion

**scene-v1:** **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS, live: WRONG TARGET; EXPECTED LABEL LOSS

[Open original photo, all masks and every selector crop](../cases/hc-057.md)

[![hc-057](../previews/hc-057.jpg)](../cases/hc-057.md)

### hc-058 center_visible_bottle

**scene-v1:** **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS, live: WRONG TARGET; EXPECTED LABEL LOSS

[Open original photo, all masks and every selector crop](../cases/hc-058.md)

[![hc-058](../previews/hc-058.jpg)](../cases/hc-058.md)

### hc-126 center_glass_occlusion__new_view_and_light

**scene-v1:** **FAIL** controlled: WRONG TARGET; EXPECTED LABEL LOSS, live: WRONG TARGET; EXPECTED LABEL LOSS

[Open original photo, all masks and every selector crop](../cases/hc-126.md)

[![hc-126](../previews/hc-126.jpg)](../cases/hc-126.md)

### hc-127 center_visible_bottle__new_view_and_light

**scene-v1:** Recorded checks pass

[Open original photo, all masks and every selector crop](../cases/hc-127.md)

[![hc-127](../previews/hc-127.jpg)](../cases/hc-127.md)

### real-397354 people_occlude_party_table_bottles

**scene-v1:** Recorded checks pass

[Open original photo, all masks and every selector crop](../cases/real-397354.md)

[![real-397354](../previews/real-397354.jpg)](../cases/real-397354.md)

