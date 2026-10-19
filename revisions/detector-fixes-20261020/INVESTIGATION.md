# Investigation of the eleven residual cases

**Three fixed; eight still fail.** Targets, GT masks, exact fallback rules and the assignment scorer are unchanged.

[Full current comparison](README.md) · [Before/after audit](evidence/revision-diff.json) · [Raw model probe responses](investigation/README.md).

| Case | Current result | Diagnosis |
|---|---|---|
| [hc-025](cases/hc-025.md) | **FAIL** | UNRESOLVED: independent detector localization error reverses the exact GT tie. Lossless and local-crop proposals do not consistently recover the frozen geometry. No near-tie epsilon was added. |
| [hc-035](cases/hc-035.md) | **FAIL** | UNRESOLVED: independent detector localization error reverses the exact GT tie. Lossless and local-crop proposals do not consistently recover the frozen geometry. No near-tie epsilon was added. |
| [hc-039](cases/hc-039.md) | **FAIL** | UNRESOLVED: independent detector localization error reverses the exact GT tie. Lossless and local-crop proposals do not consistently recover the frozen geometry. No near-tie epsilon was added. |
| [hc-041](cases/hc-041.md) | **FAIL** | UNRESOLVED: independent detector localization error reverses the exact GT tie. Lossless and local-crop proposals do not consistently recover the frozen geometry. No near-tie epsilon was added. |
| [hc-056](cases/hc-056.md) | **FAIL** | UNRESOLVED: independent detector localization error reverses the exact GT tie. Lossless and local-crop proposals do not consistently recover the frozen geometry. No near-tie epsilon was added. |
| [hc-145](cases/hc-145.md) | PASS | FIXED: small box/mask disagreement was clipping valid detector pixels; bounded visible-mask geometry restores the declared winner with honest fallback. |
| [hc-146](cases/hc-146.md) | PASS | FIXED: small box/mask disagreement was clipping valid detector pixels; bounded visible-mask geometry restores the declared winner with honest fallback. |
| [real-520871](cases/real-520871.md) | PASS | FIXED: the wine-specific prompt returned zero detections; a generic bottle recovery pass finds the carafe. Beverage identity is unverified; original wine wording remains quoted source data. |
| [real-166918](cases/real-166918.md) | **FAIL** | UNRESOLVED: no raw/full-frame or tiled proposal covers the tiny GT target (best target mask IoU 0). No target-shaped candidate was manufactured. |
| [real-117719](cases/real-117719.md) | **FAIL** | UNRESOLVED: nearer detected bottles are visible in the source photograph but absent from the incomplete COCO annotation subset. The selector cannot drop them based on GT membership. |
| [real-397354](cases/real-397354.md) | **FAIL** | UNRESOLVED: small localization differences reverse two near-equal distances. The tested generic/lossless profiles do not safely repair the ordering. |

All trial responses are retained, including unsuccessful lossless/generic full-frame, RGB crop and fixed-tile outputs. They are diagnostic development attempts, not independent evaluation data. New recovery logic is limited to the byte adapter; exact supplied-instance replay and cascade reuse do not start another detector request.
