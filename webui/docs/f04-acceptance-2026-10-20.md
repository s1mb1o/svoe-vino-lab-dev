# F04 acceptance report

Date: 2026-10-20, Europe/Moscow.
Issue: #73.
Branch: `codex/issue-73-f04`.
Initial main: `3095cc689208d78b5c576a798d43ad1a32f2a22a`.
Refreshed main: `a30827d6144f409420235f9c430645efb766caef`.
The implementation commit that contains this report identifies the reviewed source.
This report records branch acceptance. It does not accept a production release.
Issue #73 MUST remain open until the remaining human and release gates pass.

## Source and build identity

- The catalog contains 2093 Active exact IDs.
- Catalog version: `5bff04ed1d601eda697af5a8418ae8d26d30a91132617a4faae875a8ba9d0eb6`.
- Catalog JSON: 2,280,045 bytes. SHA-256: `fd730c20c630ace3a0960a0aaeea08bc95de4c2a5ff9a9864b7dfab3b4acbdab`.
- The existing MCP loader binds the manifest, rows, source export, provenance, and map index. The generated asset records the input hashes.
- The inherited matcher metadata snapshot is dated 2026-09-28T15:29:03+0300. That date is not a current deployed-catalog acceptance.
- The legacy donor was inspected in the protected checkout at `7dfc19e8e519bdaf1738c0a85bfe0f1dd2ce7368`. Its `webui/shared/recommendations.ts` Git blob is `72157f4e23a071374b36c4306937aa8ca45ef0e9`. The protected file was unchanged. Only the compatible bounded ranking behavior was ported.
- The Web runtime needs no MCP process, source export, or model weights.

The final local build contains 1764 files and 206,804,745 bytes.
The sorted file manifest has SHA-256 `bfbb2fa04c7c8d63a2856981e7720e7599a5bb64d1b8d9d69b6c76cadf567e49`.
The manifest records the relative path, byte length, and SHA-256 of every file in `.output`.
The manifest stays with the local test evidence. It is not a signed release artifact.

## Executed checks

All commands ran from `webui/` after the main refresh.

| Check | Result | Boundary |
| --- | --- | --- |
| `npm test` | PASS. 28 files. 573 passed. 26 existing skipped tests. | The skipped tests remain skipped. |
| `npm run typecheck` | PASS. | Static types only. |
| `npm run build` | PASS. | Production build. No deployment. |
| `npm run alternatives:check` | PASS. Exact generated asset. 81 Web comparison pairs match the MCP classifications. | Pinned source semantics. No preference or quality metric. |
| `npm run test:bundle` | PASS. `/`: 154.6 KB gzip. `/shelf`: 154.8 KB gzip. 25 map chunks remain lazy. | First-load JavaScript only. |
| `npm run test:pwa` through a disposable preview | PASS. Warmed page reopens offline with HTTP 200 from the service worker. APIs remain unavailable offline. Worker update waits. | First-ever offline navigation fails as documented. |
| `npm run test:f04` with the running matcher | PASS in Chromium and WebKit. | Actual account service. Isolated SQLite. Normal code challenge. Memory mail. |
| Same F04 build on physical Pixel 8, Chrome 155 | PASS at 10:29:55–10:30:06 Moscow. | Real phone renderer. See device limits below. |

The independent upload check uses an existing public catalog bottle image.
The running matcher returns `cantiani-cabernet-sauvignon`.
No Eval.zip, official evaluation photo, or derived accuracy metric was used.
The existing `test:contract` script was not run because that script reads official evaluation material.
The F04 checker independently verifies the multipart image/slug contract, empty-upload HTTP 400, bad-filter HTTP 400, and unsupported-card HTTP 404.
This integration smoke test does not establish recognition accuracy or an SLA.

## Integrated journey and failures

The automated journey verifies alternatives, exact comparison, save, reload, and offline reopening.
The comparison shows eight facts and explicit unknowns.
Both themes pass at 320, 390, and 1280 CSS pixels without horizontal overflow.
Back, Escape, close, and focus return preserve the source result.
The selected candidate saves once with the existing status model.
An edited status and private note survive online reload in the existing diary.
The original recognition history remains correct.
Comparison and save do not repeat recognition.

An actual eight-second alternatives timeout and HTTP 503 preserve the source result.
A held old filter response cannot replace the newer result.
These failures and filter changes do not repeat recognition.
HTTP 503 and a full-list HTTP 409 do not show save success.
An expired session exposes the login offer.
Denied IndexedDB preserves the successful server save and reports local unavailability.
Quota failure is atomic. The 51st local card evicts the oldest card.
Malformed local records stay hidden. An unsupported database version fails closed.
An account switch rejects old-owner writes.
A pending write cannot recreate cleared cards.
Logout clears local copies.
Account deletion clears local copies in another tab.
A held account-A request cannot restore account-A cards after the page switches to account B.
Private notes and authenticated API responses remain outside offline storage and Cache Storage.

Login continuation uses a real generated code challenge with `ACCOUNT_TEST_CODE` disabled.
The code is read from a disposable memory mail sink.
The public pair returns after login without a stored photo or an automatic save.
The user explicitly saves after return.
Memory mail does not establish SMTP delivery or ownership of a real email address.

## Twenty-anchor results

The manifest selected the first exact slug for twenty distinct known producers in the pinned sorted catalog.
The manifest fixed the source constraints before the first run.
No failed anchor was replaced.
Eighteen anchors return an eligible alternative. Two anchors have the reviewed reasons below.
Producer leaks: zero. Source/alias duplicates: zero. Hard-filter violations: zero.
All returned IDs are present in the pinned Active catalog.
The exhaustive catalog test also checks producer exclusion and exact accepted IDs.

| Exact source slug | Candidates | Reviewed outcome |
| --- | --- | --- |
| `abrau-dyurso-abrau-kupazh-svetlyy-suhoe-shardone-beloe-125` | 5 | Eligible strict alternatives. |
| `agora-rosa-viva-beloe-bryut` | 5 | Eligible strict alternatives. |
| `aratti-kaberne-sovinon-2020-krasnoe-suhoe` | 5 | Eligible strict alternatives. |
| `aristov-anima-millesimato-beloe-bryut` | 5 | Eligible strict alternatives. |
| `avtohtonnoe-vino-kryma-beloe-suhoe` | 4 | Eligible strict alternatives. |
| `avtorskij-gid-artura-sarkisyana` | 5 | Eligible strict alternatives. |
| `b-yu-rne-krasnostop-suhoe-krasnoe-classic` | 0 | No other confirmed producer shares the sourced grape under the color and sweetness constraints. |
| `balaklava-bryut-rezerv` | 5 | Eligible strict alternatives. |
| `belbek-beloe-suhoe-kaberne-sovinon-krasnoe-14` | 5 | Eligible strict alternatives. |
| `beloe-polusladkoe` | 0 | The source card has no sourced grape. Strict similarity cannot be established. |
| `beloe-suhoe` | 4 | Eligible strict alternatives. |
| `cantiani-cabernet-sauvignon` | 5 | Eligible strict alternatives. |
| `cloudy-winery-krash-super-bryut-shardone-beloe-ekstra-bryut-85` | 5 | Eligible strict alternatives. |
| `czimlyanskoe-beloe-bryut` | 5 | Eligible strict alternatives. |
| `denisov-winery-pino-nuar-shardone-ekstra-bryut-beloe-125` | 4 | Eligible strict alternatives. |
| `derbent-vino-desono-risling-ekstra-bryut-beloe-105-125` | 3 | Eligible strict alternatives. |
| `dubinin-winery-pino-nuar-bryut-roze-rozovoe-ekstra-bryut-125` | 5 | Eligible strict alternatives. |
| `dva-serdtsa-muskat-suhoy-muskat-belyy-beloe-suhoe-12` | 2 | Eligible strict alternatives. |
| `esse-prirodno-polusladkoe-beloe-risling-125` | 5 | Eligible strict alternatives. |
| `evolution-pinot-noir-bryut-beloe` | 4 | Eligible strict alternatives. |

## Physical-device evidence

The Pixel 8 runs the same final build against the running matcher and isolated actual account service.
The journey selects `aratti-kaberne-sovinon-2021-krasnoe-suhoe` as the exact candidate.
The phone opens alternatives, comparison, the existing diary save, and a local card after reload.
The test removes the test origin's ADB reverse mapping and uses browser network emulation.
The offline card opens while the test origin is unreachable.
The test uses Chrome's disposable localhost secure context. It does not change production cookies or TLS.
The helper restores its cookie and ADB state. The helper closes only its test tab.

File bytes enter the real phone file input through browser automation.
The native camera and gallery selectors are not accepted by this check.
The test does not toggle OS airplane mode.
The physical test is not TalkBack acceptance.

Physical iPhone tooling was unavailable because CoreDeviceService did not initialize.
No physical iPhone result is claimed.
WebKit automation is a separate browser-engine check.

## Remaining gates before release

1. Select the actual F01 release and metadata version. Regenerate the alternatives asset if the accepted catalog or map identities change. Repeat the source check, anchors, and affected checks.
2. Run the continuous journey on physical iPhone Safari.
3. Use native camera and gallery selection on both phones.
4. Test VoiceOver, TalkBack, 200% text, visible focus, and both themes on the phones.
5. Repeat warmed launch, close, and reopen with literal OS airplane mode.
6. Verify normal SMTP delivery with `ACCOUNT_TEST_CODE` disabled if email ownership is part of the release claim.
7. Integrate the branch. Verify the selected installation and existing account migrations 005/006. Record release and continuous-journey evidence separately.

The 13:00 integration and 16:00 release-acceptance checkpoints remain applicable.
No account migration or backend source was changed by F04.
No main merge or deployment was performed.
Do not close broader issues #20, #26, #60, #64, #71, #35, or #52 from this report.

## Reproduction and local evidence

Read `docs/f04-result-journey.md` for the disposable service setup.
Set `PLAYWRIGHT_MODULE` to the installed Playwright module.
Set `F04_PYTHON` to a Python environment with the local account package installed.
Set `F04_MATCHER_ENDPOINT` to the authorized running matcher.
Set `F04_REPORT_DIR` to a private temporary directory.
Set `F04_ANDROID=1` only for the authorized physical Android check.
Then run `npm run test:f04` against the completed build.

Local evidence root: `/private/tmp/f04-implementation-20261020`.
The root holds `build-final.log`, `unit-tests-final.log`, `typecheck-final.log`, `bundle-final.log`, `pwa-final.log`, and the build manifest.
`browser-final/` holds browser, anchor, and Pixel 8 JSON reports plus screenshots.
`browser-faults-final/` holds the passing additional failure and schema check report.
That check finished at 2026-10-20T07:33:35.527Z. It reported no page errors.
Private account databases, code outboxes, session fixtures, and local TLS keys MUST NOT be committed or published.
