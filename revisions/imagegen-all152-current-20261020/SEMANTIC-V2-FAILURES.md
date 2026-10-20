# semantic-v2 failure flags

These are provisional development checks against unreviewed target/mask proposals. Scene-confirmed and pending-scene cohorts remain separate; no mask ground-truth accuracy is claimed. A matching target ID can still have a retention or isolation failure. No flag is a claim of crop usefulness.

50 cases flagged. [All 152 cases](README.md).

| Case | Cohort | Selected / target | Failure flags |
|---|---|---|---|
| [pilot-v1:OW02](cases/pilot-v1--OW02.md) | scene_confirmed_masks_pending | d0 / d0 | isolation proxy failure |
| [pilot-v1:VI01](cases/pilot-v1--VI01.md) | scene_confirmed_masks_pending | d3 / d3 | selected-label proposal not fully retained; mask review pending |
| [pilot-v1:AM02](cases/pilot-v1--AM02.md) | scene_confirmed_masks_pending | d18 / d18 | isolation proxy failure |
| [hardcases-v2:PT01](cases/hardcases-v2--PT01.md) | scene_confirmed_masks_pending | d2 / d0 | target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [hardcases-v2:PT04](cases/hardcases-v2--PT04.md) | scene_confirmed_masks_pending | d1 / d0 | target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [hardcases-v2:DP01](cases/hardcases-v2--DP01.md) | scene_confirmed_masks_pending | d47 / d1 | target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [hardcases-v2:DP02](cases/hardcases-v2--DP02.md) | scene_confirmed_masks_pending | d4 / d1 | target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [hardcases-v2:DP03](cases/hardcases-v2--DP03.md) | scene_confirmed_masks_pending | d2 / d1 | target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [hardcases-v2:DP04](cases/hardcases-v2--DP04.md) | scene_confirmed_masks_pending | d16 / d21 | target disagreement; isolation proxy failure; tiny crop; label retention proxy below 99.5% |
| [hardcases-v2:GL02](cases/hardcases-v2--GL02.md) | scene_confirmed_masks_pending | d4 / d4 | isolation proxy failure |
| [hardcases-v2:GL04](cases/hardcases-v2--GL04.md) | scene_confirmed_masks_pending | d1 / d0 | target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [hardcases-v2:BG01](cases/hardcases-v2--BG01.md) | scene_confirmed_masks_pending | d28 / d28 | isolation proxy failure |
| [hardcases-v2:BG03](cases/hardcases-v2--BG03.md) | scene_confirmed_masks_pending | d37 / d6 | target disagreement; isolation proxy failure; tiny crop; label retention proxy below 99.5% |
| [hardcases-v2:BG04](cases/hardcases-v2--BG04.md) | scene_confirmed_masks_pending | d7 / d1 | target disagreement |
| [diverse-v3:PN01](cases/diverse-v3--PN01.md) | scene_pending_masks_pending | d13 / d48 | target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [diverse-v3:PN03](cases/diverse-v3--PN03.md) | scene_pending_masks_pending | d51 / d32 | target disagreement; isolation proxy failure; tiny crop; label retention proxy below 99.5% |
| [diverse-v3:PN04](cases/diverse-v3--PN04.md) | scene_pending_masks_pending | d37 / d37 | isolation proxy failure |
| [diverse-v3:PN07](cases/diverse-v3--PN07.md) | scene_pending_masks_pending | d41 / d45 | target disagreement; isolation proxy failure; tiny crop; label retention proxy below 99.5% |
| [diverse-v3:PN09](cases/diverse-v3--PN09.md) | scene_pending_masks_pending | d54 / d54 | isolation proxy failure |
| [diverse-v3:PN10](cases/diverse-v3--PN10.md) | scene_pending_masks_pending | d33 / d33 | isolation proxy failure |
| [diverse-v3:HP01](cases/diverse-v3--HP01.md) | scene_pending_masks_pending | d14 / d14 | isolation proxy failure |
| [diverse-v3:HP03](cases/diverse-v3--HP03.md) | scene_pending_masks_pending | d48 / d48 | isolation proxy failure; selected-label proposal not fully retained; mask review pending |
| [diverse-v3:HP06](cases/diverse-v3--HP06.md) | scene_pending_masks_pending | d14 / d14 | isolation proxy failure |
| [diverse-v3:HP07](cases/diverse-v3--HP07.md) | scene_pending_masks_pending | d54 / d54 | isolation proxy failure |
| [diverse-v3:HP08](cases/diverse-v3--HP08.md) | scene_pending_masks_pending | d6 / d6 | isolation proxy failure; selected-label proposal not fully retained; mask review pending |
| [diverse-v3:HP09](cases/diverse-v3--HP09.md) | scene_pending_masks_pending | d0 / d34 | target disagreement; isolation proxy failure; tiny crop; label retention proxy below 99.5% |
| [diverse-v3:HP10](cases/diverse-v3--HP10.md) | scene_pending_masks_pending | d14 / d14 | isolation proxy failure |
| [diverse-v3:PD01](cases/diverse-v3--PD01.md) | scene_pending_masks_pending | d48 / d48 | isolation proxy failure |
| [diverse-v3:PD02](cases/diverse-v3--PD02.md) | scene_pending_masks_pending | d39 / d10 | target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [diverse-v3:PD03](cases/diverse-v3--PD03.md) | scene_pending_masks_pending | d39 / d39 | isolation proxy failure; selected-label proposal not fully retained; mask review pending |
| [diverse-v3:PD04](cases/diverse-v3--PD04.md) | scene_pending_masks_pending | d43 / d12 | target disagreement; isolation proxy failure; tiny crop; label retention proxy below 99.5% |
| [diverse-v3:PD05](cases/diverse-v3--PD05.md) | scene_pending_masks_pending | d27 / d27 | isolation proxy failure; selected-label proposal not fully retained; mask review pending |
| [diverse-v3:PD06](cases/diverse-v3--PD06.md) | scene_pending_masks_pending | d58 / d10 | target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [diverse-v3:PD07](cases/diverse-v3--PD07.md) | scene_pending_masks_pending | d47 / d47 | isolation proxy failure |
| [diverse-v3:PD08](cases/diverse-v3--PD08.md) | scene_pending_masks_pending | d10 / d1 | target disagreement; isolation proxy failure; tiny crop; label retention proxy below 99.5% |
| [diverse-v3:PD09](cases/diverse-v3--PD09.md) | scene_pending_masks_pending | d20 / d20 | isolation proxy failure |
| [diverse-v3:PD10](cases/diverse-v3--PD10.md) | scene_pending_masks_pending | d11 / d7 | target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [diverse-v3:WP05](cases/diverse-v3--WP05.md) | scene_pending_masks_pending | d1 / d0 | target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [diverse-v3:WP09](cases/diverse-v3--WP09.md) | scene_pending_masks_pending | d11 / d0 | target disagreement |
| [diverse-v3:OC03](cases/diverse-v3--OC03.md) | scene_pending_masks_pending | d1 / d0 | target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [diverse-v3:OC04](cases/diverse-v3--OC04.md) | scene_pending_masks_pending | d25 / d25 | isolation proxy failure |
| [diverse-v3:OC07](cases/diverse-v3--OC07.md) | scene_pending_masks_pending | d1 / d0 | target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [diverse-v3:SZ01](cases/diverse-v3--SZ01.md) | scene_pending_masks_pending | d0 / d1 | target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [diverse-v3:SZ04](cases/diverse-v3--SZ04.md) | scene_pending_masks_pending | d6 / d40 | target disagreement; isolation proxy failure; tiny crop; label retention proxy below 99.5% |
| [diverse-v3:LB01](cases/diverse-v3--LB01.md) | scene_pending_masks_pending | d1 / d0 | target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [diverse-v3:LB04](cases/diverse-v3--LB04.md) | scene_pending_masks_pending | d0 / d1 | target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [diverse-v3:LB05](cases/diverse-v3--LB05.md) | scene_pending_masks_pending | d3 / d2 | target disagreement; isolation proxy failure; tiny crop; label retention proxy below 99.5% |
| [diverse-v3:CT07](cases/diverse-v3--CT07.md) | scene_pending_masks_pending | d0 / full_frame | target disagreement; isolation proxy failure |
| [diverse-v3:CT09](cases/diverse-v3--CT09.md) | scene_pending_masks_pending | d0 / full_context | target disagreement; isolation proxy failure |
| [diverse-v3:CT10](cases/diverse-v3--CT10.md) | scene_pending_masks_pending | d0 / full_context | target disagreement; isolation proxy failure |
