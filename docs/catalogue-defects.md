# Catalogue and photo defects found by the agent hunt

Status 2026-09-16. Found by agents in batches 1 and 2, which covered 96 of the 570
wines of the `needs_positive` queue. Each line names the agent that found it.
No agent changed any of this. Every item needs a decision by the project owner.

## A. Two catalogue rows, one wine

| slugs | evidence | found by |
|---|---|---|
| `aligote-avtorskoe`, `aligote-avtorskoe-vino` | one `bottle_path` for both | hunter-03 |
| `balaklava-muskat`, `balaklava-muskat-beloe-polusladkoe` | identical front label. The renders differ only in the neck mark: `1889 / ЗОЛОТАЯ БАЛКА` on the foil against `ЗОЛОТАЯ БАЛКА / КРЫМ / с 1889 г.` on the glass | hunter-07 |
| `belmas-winery-syrah-katya-sira-...-125`, `belmas-winery-syrah-katya-belmas-...-125` | near duplicates of one wine | hunter-07 |

## B. The catalogue bottle is wrong or absent

| slug | defect | found by |
|---|---|---|
| `belmas-winery-syrah-katya-sira-krasnoe-suhoe-125` | the render is the Belmas Katya **Riesling**: tall flute bottle, white wine, `RIESLING` on the label. Every record field says a red Syrah (name Syrah Katya, grapes Сира, Красное, 12.5, blackberry and pepper). The sibling slug carries the correct Syrah render | hunter-07 |
| `balaklava-pino-nuar` | `bottle_path` is a photo of a vineyard and grapes, not a bottle | hunter-07 |
| `czitronnyj-magaracha` | `bottle_path` is `Screenshot_20_47de2b4b32.webp`, a landscape photo of a winery lawn. vino-svoe.ru shows the same wrong picture, so the defect is upstream of the import | hunter-12 |
| `cary-pandas-avtorskoe-vino` | the render shows a dark bottle with red content for a dry **white** wine. It looks like the Сары Пандас label put onto the red Саперави bottle. Every real photo shows light olive glass. Do not judge a candidate here by bottle colour | hunter-08 |
| `chateau-tamagne-select-blanc-brut-svo-yo-vino` | no catalogue bottle, no name, no producer. Its one photo is the same file as `01_conf100.jpg` of `chateau-tamagne-select-blanc-brut` | hunter-09 |
| `alma-valley-shardone-rezerv-beloe-suhoe-14` | the render is a **2020** bottle whose own label reads **13,0 %**, not 14 | hunter-04 |
| `abrau-dyurso-abrau-estates-beloe-shardone-suhoe-12` | the label reads `CHARDONNAY / SAUVIGNON BLANC`; the slug names only `shardone` | hunter-01 |

## C. Existing photos show a different wine

These photos are already in `my/`. Most are unlabelled pipeline candidates with a
high confidence in the file name. They SHOULD be labelled `negative`.

| slug | photos | what they really show | found by |
|---|---|---|---|
| `alma-valley-pino-nuar-beloe-ekstra-bryut-115` | `01_conf095.jpg`, `02_conf095.jpg` | the still red Pinot Noir 2020 | hunter-04 |
| `chateau-tamagne-select-blanc-brut` | all 4 | the still Select Blanc 2021 Chardonnay-Sauvignon Blanc, screwcap | hunter-09 |
| `chateau-de-talu-uroki-frantsuzskogo-sovinon-blan-...-115` | all 3 | Blanc de Talu 2019 | hunter-09 |
| `chateau-tamagne-signature-kaberne` | `01`-`04` | the regular Chateau Tamagne Cabernet line: cream label, round blue seal | hunter-10 |
| `chteau-le-grand-vostock-aligote-reserve-...` | pipeline photos | the plain wine of the same grape: turquoise or green capsule, shoulder label | hunter-10 |
| `chteau-le-grand-vostock-chardonnay-reserve-...` | pipeline photos | same defect | hunter-10 |
| `chteau-le-grand-vostock-cabernet-sauvignon-reserve-...` | pipeline photos | same defect | hunter-10 |

## D. Pairs that a photo cannot separate

| slugs | the only difference | found by |
|---|---|---|
| `alma-valley-merlo-rezerv-...-14`, `...-15` | both renders are 2021 with the same gold Scythian medallion. The two RENDERS are separable: `-15` ends `КРЫМ` plus `СПИРТ: 15,0 % об.`, `-14` ends `КРЫМ \| РОССИЯ` with no alcohol line. The problem is the CANDIDATE: a web photo can be assigned only when that bottom line is readable in the photo itself, and most are not. Do not read this row as "the renders look the same" | hunter-03 and hunter-04 independently; wording sharpened after irec-03 misread it |
| Chateau de Talu Каберне Фран base, Резерв, Премиум | base = man climbing a ladder; Резерв = man sitting on a cloud plus the line `Резерв`; Премиум = ladder plus `Премиум`. One small line separates base from Премиум | hunter-09 |

## E. One proposal is known to be wrong

`aratti-muskat-belyj-polusuhoe` `02_agent.jpg`, proposed at 0.85 by hunter-05. The
agent then enlarged the label and found the dry version, not the semi-dry of the slug.
An agent has no delete route, so it could only add a photo comment. Reject it.

## F. Open questions for the owner

1. `chateau-de-talu-...-kaberne-fran-rezerv-...-146`: the producer also sells a
   "Каберне Фран Резерв" with a completely different white chateau-and-sea-waves
   label. It may be the generation before "Южная Вертикаль", or a separate line.
   hunter-09 proposed nothing from it.
2. `chteau-le-grand-vostock` Aligote Reserve and Chardonnay Reserve moved in 2026
   from the straight clear bottle of the render to a burgundy-shaped green bottle;
   Aligote also gained an acute accent. hunter-10 proposed those as `variant`.
   Decide which generation the catalogue keeps.
3. `ballet-blanc`: all four proposals are older vintages (2024, 2021, 2019) of the
   catalogue's ВОСЬМОЙ УРОЖАЙ 2025. The label design is identical; only the harvest
   line and the year change. hunter-07 used `positive`. Downgrade to `variant` if the
   harvest line must match.
