# Eight producer maps: review resolution

Date: 2026-10-17.
Status: Confirmed defects corrected. Local verification passed.
Reviewer: Claude Opus 5.5. Effort: max.
Canonical model: `claude-opus-5-5`.

## Review scope

The owner approved `/tmp/lineup-eight/review-packet.txt` in the current request.
The packet contains 501240 bytes.
Its SHA-256 is `f6aa251ff22684e360e4f9867fcbb3f71f2a4850894a374e08cb0362b46a0051`.
The packet describes commit `49349ccf`.
The reviewer had no tools or bottle image pixels.
The packet summarized `ProductLineMap.vue` and omitted image fields from product excerpts.
The real producer JSON files retain their image fields.
The reviewer did not execute tests or inspect the application.
The agent checked the advice against source records, original photographs, code, and browser results.
There was one external review request. No second external approval is claimed.
Read the adjacent JSON for response hashes and verification metadata.
The local raw result is `reports/eight-producer-maps/2026-10-17-opus-review.txt`.

## Blocking findings

### 1. Novy Svet positioning

Special historical cuvees now use rank 0.
They do not share a confirmed premium rank or one limited-release status.
Two exact names state `выдержанное`. These cards now use the aged group.
The two shorter Aligote and Kokur cards do not establish that collection.
These two cards use a separate unconfirmed group at rank 0.
All 44 catalog identities remain separate.
The official Коронационное addition remains unlinked and has a limited-release label.
The map now has six groups.

### 2. Group descriptions

BLUSH MIRAGE now states slight effervescence.
The producer also classifies the range as still wine.
Historical Yachting cards now state oak ageing from 12 months.
The current official range index does support 12–18 months.
That current upper limit does not override historical card evidence.
VINTAGE no longer makes an unsupported comparison with other sparkling methods.
AGORA CUVEE retains premium wording because the [official page](https://www.agora-group.ru/catalog/range/agora/agora-cuvee/) supports that wording.
AGORA Terroir now describes the oak ageing in its snapshot cards.
Belbek rose text now allows different blends.
Sober Bash Грани now names all six retained products.

### 3. Source confidence

Each reviewed producer now has `source-evidence.json`.
The file records exact URLs, document sections, retrieval dates, and HTML SHA-256 values.
ESSE uses the actual catalog section anchors.
AGORA uses exact range pages.
A source label identifies the real document. It does not imply a dedicated group page.
Snapshot-only groups cite only `svoe-vino-2026-09-17` and use rank 0.
Historical Soyuz-Vino brands no longer receive unsupported price ranks.
Current Lavetti ciders do not identify historical wine cards.
The alcoholic Perle source uses the saved official page from 2026-10-16.
Current retrieval of that page returned HTTP 403.
Unused sources were removed from the eight maps.
Repeated `official-official-` prefixes were replaced with `official-product-`.
The Sober Bash amphora URL had already been corrected in `5605f840` during the independent local check.
The Novy Svet exact absence scope had already been corrected in `710075de`.

### 4. Snapshot test evidence

The final full test run used `PRODUCT_LINE_CATALOG_SNAPSHOT` with the exact saved catalog file.
The run reported:

```text
Test Files  16 passed (16)
Tests  276 passed (276)
```

No test was skipped in that run.
The source SHA-256 remains `e915493a0a960df040b4055d33c815940e48fb1a2994a7979a819786b2c41961`.
The default CI path now checks all 2103 slug-to-producer records through a pinned public projection.
Attribution no longer depends on the optional full snapshot path.
The full snapshot also verifies the projection against the original rows.
The registry-only run without the full snapshot passed 76 tests and skipped 19 full-snapshot checks.
Do not report that default run as zero-skipped verification.

### 5. Image acceptance

The pixel checker now verifies actual dimensions, alpha presence, transparent pixels, and containment of the measured alpha outline.
All 1046 image references passed.
The input hashes of all 370 linked source photos were checked against original files.
All 67 imagegen records matched their input hashes, generated hashes, and recorded prompts.
Output checksums remain covered by the registry suite.
Original-label contact sheets were inspected for disputed collection assignments.
The image sizing document now defines the display-derivative acceptance rule.
Imagegen display derivatives can change fine print.
They are not evidence for product identity and are not described as pixel-identical originals.
This review found no specific damaged image that required replacement.
An alpha-matte reconstruction or a quantitative fidelity gate would require a separate asset pipeline.
The owner-selected imagegen display workflow remains in use with the documented limit.

## Membership and identity findings

- Every reviewed crosswalk entry now records `group_basis`.
- Original ESSE labels identify Pinot Noir, Chenin Blanc, Odessa Black, and Saperavi Heaven as Unplugged. Four incorrect KACHA VALLEY placements were corrected.
- The claim that these original Unplugged photos show KACHA VALLEY was not confirmed. The source photographs read ESSE UNPLUGGED.
- Chateau Pinot retains confirmed Gravity labels. Seven historical blends without a verified collection use a neutral group. A current matching blend does not prove the historical series. The map now has 13 groups.
- Valery Zakharyin reserve membership uses original Reserve labels. The group explicitly combines different collections. Rubedo alone is not evidence for the autochthon reserve identities.
- Belbek Reserve and ESSE YELLOW GLOVES record possible historical catalog counterparts. No exact equivalence is asserted. Both additions remain unlinked.
- Repeated names receive `catalog_card_label` values. The labels identify separate catalog records. They do not infer a vintage, size, or quality difference from a slug.
- The Novy Svet white-name/rose-category conflict and the Soyuz red-wine/white-grape conflict have visible badges. Source fields remain unchanged.
- Sparkling styles now identify sparkling wine in the reviewed maps.
- Grape facts identify their catalog or official source. Catalog grape lists can be incomplete.
- The UI states that price steps compare groups within one producer.
- Limited-release labels are used for the verified Poezdnik and Коронационное releases. The `catalog` release value remains an evidence state. It does not assert current retail availability.
- Soyuz editorial `Secco` spelling was corrected. Exact catalog fields remain unchanged.

## Code findings

`ProductLineImage.vue` now applies consumer class and style once to the frame.
Native image attributes remain on the inner image.
Default image limits prevent an empty frame when custom properties are absent.
Gray filters now apply once in both themes.
The browser suite checks the inner image filter and class attributes.
A missing image key now produces a validation error instead of a TypeError.
A regression test covers that partial JSON record.

## Performance and scope limits

The static registry remains in the shared module.
The production client chunk is 1295.93 kB before compression and 186.49 kB with gzip.
This is a size measurement. No mobile latency budget was measured.
Per-producer asynchronous loading remains an optional performance change.
All current browser checks passed with the static registry.
The final combined tree was tested. Historical commit revisions were not rebuilt independently.
Each producer has a separate implementation commit and a separate review-correction commit.
The branch remains local. No push or merge into main was performed.
Mobile checks use browser emulation. No physical phone was tested.

## Final verification

- 276 unit tests passed with the full snapshot. No tests were skipped.
- Type checks and the production build passed.
- 81 producer cases passed in Chromium. The same 81 cases passed in WebKit.
- The producer suite checks the longest Novy Svet title and Soyuz-Vino at 767 and 768 px.
- The complete Abrau regression suite passed in both engines.
- All 1046 image references passed actual pixel and frame checks.
- All 370 linked photo inputs and 67 imagegen records passed hash checks.
- Fresh desktop and mobile screenshots were inspected in both themes.
- Product counts and catalog coverage remain unchanged. The eight maps now have 81 groups.
- The local server runs at `http://127.0.0.1:18553`.

## Producer correction commits

| Producer ID | Commit |
| --- | --- |
| `novy-svet` | `3c145580` |
| `agora` | `7f6a9e75` |
| `belbek` | `58d01f04` |
| `sober-bash` | `b61ad647` |
| `esse` | `039333de` |
| `chateau-pinot` | `86fc87e5` |
| `valery-zakharyin` | `84fce9d7` |
| `soyuz-vino` | `4fc73700` |
