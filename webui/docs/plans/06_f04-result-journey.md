# F04 result journey

Date: 2026-10-20.
Status: Implemented on `codex/issue-73-f04`. Automated acceptance passed.
Physical iPhone and the remaining human checks are release gates.
Authority: Issue #73 and the owner's implementation request.
Initial base: main `3095cc689208d78b5c576a798d43ad1a32f2a22a`.
Refreshed base: main `a30827d6144f409420235f9c430645efb766caef`.
Read [the acceptance report](../f04-acceptance-2026-10-20.md).

## Contracts

Use the existing photo prediction and exact `slug` contract.
Generate a server-only alternatives snapshot from the pinned MCP catalog loader.
Preserve its source hashes and Active IDs.
Use verified map identities for producer and wine aliases.
Do not infer a producer identity from a slug prefix.
Require a known source producer and a different known candidate producer.
Apply known color and sweetness constraints before ranking.
Apply an explicit still/sparkling filter only when that field is known.
Rank by shared grapes and supported public facts.
Keep unknown fields explicit.

`GET /api/recommendations/alternatives` accepts one exact slug and bounded enumerated filters.
It returns the pinned source card, at most five candidates, reasons, and snapshot version.
The client uses the same cards for factual comparison.
Comparison uses the eight known-field semantics of `CatalogService.compareWines`.
A running MCP server is not required.

Use the existing `PinButton`, `useDiary`, and account service.
Pass `source=photo` for this photo-result journey.
Saving a candidate does not record another recognition event.
Resolve known candidate slugs from the same snapshot for diary writes.
Do not add another account table or change authentication.

## Offline storage

Store only explicit successful saves in a separate versioned IndexedDB cache.
Store public card facts, exact slug, snapshot version, and snapshot date.
Store at most 50 cards. Evict the oldest card deterministically.
Use the existing public image placeholder. Do not store uploaded photos.
Do not store notes, ratings, account responses, emails, session tokens, or credentials.
The owner marker is an opaque existing account ID.
Each write checks its owner and generation inside the same transaction.
An owner change clears prior records.
Logout, deletion, and account reset invalidate pending writes and clear local records.
Notify other tabs after a cache change.
Show offline readiness only after a transaction commits.
Keep server save success separate from local copy failure.
The main public page exposes local cards after online warm-up.
An offline start reads public device copies without an account request.
An online start verifies the current account before it reads device copies.
Preserve the service worker exclusions for private pages and APIs.
Offline mutations remain unavailable. Do not add a synchronization queue.

## Login continuation

Preserve only the two public comparison cards and version in session storage.
Restore the comparison after the existing login return.
Do not preserve an uploaded photo or claim a new recognition.
Require another explicit save click after login.

## Acceptance

Run the issue's twenty-anchor and zero-leak checks against the generated snapshot.
Run focused logic and browser failure checks.
Run type, build, contract, PWA, and applicable theme checks.
Exercise real account persistence with an isolated local SQLite service.
Keep browser fixtures separate from actual recognition and physical-device acceptance.
Record the exact source and commands in the test report.
Do not use Eval.zip or its derivatives.
Keep the 13:00 integration, 16:00 acceptance, and 18:00 internal freeze checkpoints.

## Decisions

Reuse the existing catalog loader to avoid a second interpretation of accepted source IDs.
Generate a server-only asset to avoid runtime access to repository files and model assets.
Reuse the existing diary to preserve its storage, limits, and private notes.
Use a separate public-card cache because account HTML and API responses must stay uncached.
Keep placeholders offline to avoid another image download or storage pipeline.
