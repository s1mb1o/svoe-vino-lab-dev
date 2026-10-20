# Alternatives, comparison, and offline cards

Date: 2026-10-20.
Issue: #73.
Read [the implementation plan](plans/06_f04-result-journey.md).
Read [the dated acceptance report](f04-acceptance-2026-10-20.md).

## User journey

A real photo result exposes «Найти альтернативы».
Mock results do not expose this action.
The action uses the exact recognized slug.
It excludes that wine, its verified aliases, and its producer before ranking.
It requires a known producer, color, and sweetness.
It uses common sourced grapes for the bounded similar-style ranking.
Color, sweetness, and an explicit still/sparkling choice are hard filters.
A missing still/sparkling field remains unknown.
An empty result does not relax the producer rule.
An unsupported exact slug has an explicit outside-snapshot message.

«Сравнить» opens two exact cards and eight factual fields.
Shared facts, differences, and unknown fields remain separate.
The comparison follows `CatalogService.compareWines` semantics.
The source check compares the Web classifications with the MCP classifications.
The runtime Web server does not call MCP.
The comparison does not select a quality winner.

The cards reuse `PinButton`, `useDiary`, and the existing account service.
The selected candidate supplies the saved slug.
The initiating photo flow supplies the existing `photo` saved source.
The candidate is not recorded as another recognized photo result.
The existing four saved statuses and private notes remain in the diary.
The server resolves accepted candidate metadata from the pinned catalog.

## Source identity

`server/data/alternative-catalog.json` contains 2093 Active IDs.
The generator uses the existing MCP catalog loader.
The loader validates the matcher manifest, wine rows, source export, provenance, and map index.
The asset records the exact source hashes and catalog version.
Verified map producer and wine aliases provide canonical identities.
A slug prefix alone does not establish a producer identity.
The asset is server-only. Do not import it in an application component.

Run from `webui/` in a full repository checkout:

```bash
npm run alternatives:check
```

After an accepted catalog change, run:

```bash
npm run alternatives:catalog
```

Review the anchor manifest against the new catalog version before release.
Do not replace an anchor after it fails.
Then run the source check, affected tests, and the build.
The generated asset permits a standalone Web runtime without model weights or repository input files.
The generation and source-check commands need the checked-in catalog sources and `mcp/`.

## Offline copy

An explicit successful save can create a separate public-card copy on the device.
IndexedDB stores at most 50 copies.
The oldest copy is removed first. The server diary is unchanged.
The copy contains the exact slug, public card fields, catalog version, and snapshot time.
The copy uses the public image placeholder.
It contains no private note, personal rating, account response, token, email, or uploaded photo.
The online diary remains the source of truth for statuses and notes.

The home page exposes «Карточки на этом устройстве».
A stored card can open after an online warm-up and a later offline start.
The first-ever offline launch is not supported.
Portal links and new recognition require the network.
Offline status and note mutations are not queued.
A local write failure keeps the successful server save and reports the missing offline copy.

The store checks owner and epoch inside each write transaction.
Logout, deletion, and account reset invalidate pending writes and clear device copies.
A local tombstone blocks reads after a failed deletion.
Other tabs receive cache-clear notifications.
An online page verifies the current account before it renders device copies.
An offline page labels the records as public device copies.
Private account pages and APIs remain outside the service-worker caches.

## Login continuation

The login link keeps a bounded pair of public cards in session storage.
The pair contains no photo, private note, or authentication data.
After the existing login return, «Продолжить сравнение» reopens the pair.
The restored pair does not claim another recognition.
Saving still requires an explicit click.
Expired-session save errors expose the existing login offer.

## Browser acceptance

Install the normal locked Web dependencies.
Prepare a disposable Python environment with the local `account/` package.
Point `PLAYWRIGHT_MODULE` to a local Playwright `index.mjs`.
Point `F04_PYTHON` to that Python executable.
Run from `webui/`:

```bash
npm run build
npm run test:f04
```

The browser check starts temporary loopback services on OS-assigned ports.
The check uses the actual account service and an isolated SQLite database.
The check uses a memory mail sink and leaves `ACCOUNT_TEST_CODE` disabled.
Memory mail does not prove SMTP delivery or ownership of a real address.
The default matcher is a deterministic test upstream.
Set `F04_MATCHER_ENDPOINT` to an authorized running matcher for a real integration smoke test.
The image is an existing public catalog bottle image. It is not an independent accuracy sample.
No Eval.zip or derived evaluation file is used.

Set `F04_ANDROID=1` only with an authorized, unlocked Android test phone and Chrome debugging available.
The helper opens one test tab and restores its cookie and ADB state.
The phone uses a disposable localhost secure context.
The helper removes only that test origin's reverse mapping for the offline check.
The helper does not disable the phone network or change production TLS.
Native camera/gallery input, OS airplane mode, TalkBack, VoiceOver, and physical iPhone Safari need separate human acceptance.

The existing `test:contract` command reads official evaluation material.
This F04 check uses an independent public-image upload contract check instead.
Run the existing PWA and bundle checks on the same final build.
