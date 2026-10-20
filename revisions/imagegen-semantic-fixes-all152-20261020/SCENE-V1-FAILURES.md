# scene-v1: explicit automatic failure flags

**60 / 152 cases have a target, isolation or label-retention flag.** All mask/ownership proposals and crop-usability judgments require human review. No automatic flag does not mean approved image quality.

| Case | Frozen target | Selected | Flags |
|---|---|---|---|
| [pilot-v1--HA02](cases/pilot-v1--HA02.md) | d1 | d0 | **FAIL:** target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [pilot-v1--HA04](cases/pilot-v1--HA04.md) | d1 | d0 | **FAIL:** target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [pilot-v1--HA05](cases/pilot-v1--HA05.md) | d0 | d1 | **FAIL:** target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [pilot-v1--LA01](cases/pilot-v1--LA01.md) | d0 | d0 | **FAIL:** label retention proxy below 99.5% |
| [pilot-v1--OW01](cases/pilot-v1--OW01.md) | d4 | d8 | **FAIL:** target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [pilot-v1--OW02](cases/pilot-v1--OW02.md) | d0 | d6 | **FAIL:** target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [pilot-v1--OW03](cases/pilot-v1--OW03.md) | d3 | d3 | **FAIL:** label retention proxy below 99.5% |
| [pilot-v1--VI01](cases/pilot-v1--VI01.md) | d3 | d3 | **FAIL:** label retention proxy below 99.5% |
| [pilot-v1--AM01](cases/pilot-v1--AM01.md) | d1 | d0 | **FAIL:** target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [hardcases-v2--PT01](cases/hardcases-v2--PT01.md) | d0 | d2 | **FAIL:** target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [hardcases-v2--PT03](cases/hardcases-v2--PT03.md) | d2 | d1 | **FAIL:** target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [hardcases-v2--PT04](cases/hardcases-v2--PT04.md) | d0 | d1 | **FAIL:** target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [hardcases-v2--DP02](cases/hardcases-v2--DP02.md) | d1 | d4 | **FAIL:** target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [hardcases-v2--DP04](cases/hardcases-v2--DP04.md) | d21 | d66 | **FAIL:** target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [hardcases-v2--DK03](cases/hardcases-v2--DK03.md) | d5 | d5 | **FAIL:** label retention proxy below 99.5% |
| [hardcases-v2--BG01](cases/hardcases-v2--BG01.md) | d28 | d28 | **FAIL:** label retention proxy below 99.5% |
| [diverse-v3--PN01](cases/diverse-v3--PN01.md) | d48 | d13 | **FAIL:** target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [diverse-v3--PN02](cases/diverse-v3--PN02.md) | d15 | d40 | **FAIL:** target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [diverse-v3--PN03](cases/diverse-v3--PN03.md) | d32 | d19 | **FAIL:** target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [diverse-v3--PN04](cases/diverse-v3--PN04.md) | d37 | d7 | **FAIL:** target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [diverse-v3--PN05](cases/diverse-v3--PN05.md) | d44 | d44 | **FAIL:** label retention proxy below 99.5% |
| [diverse-v3--PN06](cases/diverse-v3--PN06.md) | d27 | d2 | **FAIL:** target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [diverse-v3--PN07](cases/diverse-v3--PN07.md) | d45 | d12 | **FAIL:** target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [diverse-v3--PN09](cases/diverse-v3--PN09.md) | d54 | d54 | **FAIL:** label retention proxy below 99.5% |
| [diverse-v3--PN10](cases/diverse-v3--PN10.md) | d33 | d3 | **FAIL:** target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [diverse-v3--HP01](cases/diverse-v3--HP01.md) | d14 | d14 | **FAIL:** label retention proxy below 99.5% |
| [diverse-v3--HP02](cases/diverse-v3--HP02.md) | d25 | d25 | **FAIL:** label retention proxy below 99.5% |
| [diverse-v3--HP05](cases/diverse-v3--HP05.md) | d0 | d0 | **FAIL:** label retention proxy below 99.5% |
| [diverse-v3--HP07](cases/diverse-v3--HP07.md) | d54 | d54 | **FAIL:** label retention proxy below 99.5% |
| [diverse-v3--HP09](cases/diverse-v3--HP09.md) | d34 | d34 | **FAIL:** label retention proxy below 99.5% |
| [diverse-v3--GP06](cases/diverse-v3--GP06.md) | d1 | d1 | **FAIL:** label retention proxy below 99.5% |
| [diverse-v3--PD01](cases/diverse-v3--PD01.md) | d48 | d48 | **FAIL:** label retention proxy below 99.5% |
| [diverse-v3--PD04](cases/diverse-v3--PD04.md) | d12 | d12 | **FAIL:** label retention proxy below 99.5% |
| [diverse-v3--PD06](cases/diverse-v3--PD06.md) | d10 | d58 | **FAIL:** target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [diverse-v3--PD07](cases/diverse-v3--PD07.md) | d47 | d47 | **FAIL:** label retention proxy below 99.5% |
| [diverse-v3--PD09](cases/diverse-v3--PD09.md) | d20 | d20 | **FAIL:** label retention proxy below 99.5% |
| [diverse-v3--WP05](cases/diverse-v3--WP05.md) | d0 | d8 | **FAIL:** target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [diverse-v3--WP06](cases/diverse-v3--WP06.md) | d1 | d8 | **FAIL:** target disagreement; isolation proxy failure |
| [diverse-v3--WP09](cases/diverse-v3--WP09.md) | d0 | d11 | **FAIL:** target disagreement |
| [diverse-v3--OC03](cases/diverse-v3--OC03.md) | d0 | d0 | **FAIL:** label retention proxy below 99.5% |
| [diverse-v3--OC05](cases/diverse-v3--OC05.md) | d0 | d1 | **FAIL:** target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [diverse-v3--OC06](cases/diverse-v3--OC06.md) | d1 | d1 | **FAIL:** label retention proxy below 99.5% |
| [diverse-v3--OC10](cases/diverse-v3--OC10.md) | d1 | d8 | **FAIL:** target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [diverse-v3--LT03](cases/diverse-v3--LT03.md) | d0 | d1 | **FAIL:** target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [diverse-v3--LT08](cases/diverse-v3--LT08.md) | d10 | d10 | **FAIL:** label retention proxy below 99.5% |
| [diverse-v3--LT09](cases/diverse-v3--LT09.md) | d0 | d0 | **FAIL:** label retention proxy below 99.5% |
| [diverse-v3--LT10](cases/diverse-v3--LT10.md) | d1 | d0 | **FAIL:** target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [diverse-v3--SZ01](cases/diverse-v3--SZ01.md) | d1 | d0 | **FAIL:** target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [diverse-v3--SZ02](cases/diverse-v3--SZ02.md) | d1 | d0 | **FAIL:** target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [diverse-v3--SZ04](cases/diverse-v3--SZ04.md) | d40 | d40 | **FAIL:** label retention proxy below 99.5% |
| [diverse-v3--SZ05](cases/diverse-v3--SZ05.md) | d12 | d12 | **FAIL:** label retention proxy below 99.5% |
| [diverse-v3--SZ08](cases/diverse-v3--SZ08.md) | d1 | d1 | **FAIL:** label retention proxy below 99.5% |
| [diverse-v3--SZ09](cases/diverse-v3--SZ09.md) | d21 | d21 | **FAIL:** label retention proxy below 99.5% |
| [diverse-v3--LB03](cases/diverse-v3--LB03.md) | d0 | d0 | **FAIL:** label retention proxy below 99.5% |
| [diverse-v3--LB04](cases/diverse-v3--LB04.md) | d1 | d0 | **FAIL:** target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [diverse-v3--LB06](cases/diverse-v3--LB06.md) | d1 | d0 | **FAIL:** target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [diverse-v3--CT01](cases/diverse-v3--CT01.md) | d1 | d0 | **FAIL:** target disagreement; isolation proxy failure; label retention proxy below 99.5% |
| [diverse-v3--CT07](cases/diverse-v3--CT07.md) | full_frame | d0 | **FAIL:** target disagreement; isolation proxy failure |
| [diverse-v3--CT09](cases/diverse-v3--CT09.md) | full_context | d0 | **FAIL:** target disagreement; isolation proxy failure |
| [diverse-v3--CT10](cases/diverse-v3--CT10.md) | full_context | d0 | **FAIL:** target disagreement; isolation proxy failure |
