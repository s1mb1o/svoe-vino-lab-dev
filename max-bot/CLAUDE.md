# Context chto-za-vino-max-bot

This project contains the MAX messenger bot «Что за вино?» at `@se14697933_bot`.
It is the port of `../telegram-bot` with the same functionality.
Read `README.md`, `docs/specification.md`, and `docs/plans/01_max-port.md` before a change.
The workspace rules are in `../../CLAUDE.md`.

## Safety rules

1. The bot MUST moderate each image before it writes the image to disk when moderation is enabled.
2. A moderation failure MUST fail closed when moderation is enabled.
3. Production MUST keep `moderation.enabled` set to `true`.
4. The bot MUST NOT send an unsafe image to the recognition service.
5. The bot MUST store an unsafe image only under `quarantine`.
6. The `quarantine` directory MUST use owner-only permissions.
7. The bot MUST NOT write `MAX_BOT_TOKEN` or `MAX_WEBHOOK_SECRET` to a file in this repository.
8. Logs MUST NOT contain image bytes, tokens, secrets, attachment URLs, first names, last names,
   or usernames.
9. The database MAY contain the MAX identity snapshot that the user authorized.

## Service rules

1. Use long polling in production during the hackathon (owner decision, issue #10).
   `updates.mode` in `config.yaml` selects `polling` or `webhook`. The webhook switch is issue #23.
2. Read the model service endpoints only from configuration (`MODERATION_ENDPOINT`,
   `SAM3_ENDPOINT`). In a container, `127.0.0.1` is the container itself.
3. Read the matcher endpoint only from `MATCHER_ENDPOINT`.
4. Keep the request limit in environment configuration.
5. Keep the default limit at 50 image requests in 3600 seconds per MAX user ID.
6. Keep user-visible bot text in Russian.
7. Keep technical documentation in English and use STE-style text. Exceptions: `README.md`
   (owner decision of 2026-10-16) and the deployment guide `deploy/README.md` (owner decision of
   2026-10-18) are in Russian. Write them in short active Russian sentences.
8. Send all photo processing through the shared work queue.
9. Keep the default queue worker count at one until a GPU load test approves a higher value.
10. Fetch catalogue result images only from `https://chtozavino.ru` (the static wine images of
    plan `docs/plans/06_wine-images.md`) and, until each matcher gives those addresses, from
    `https://api.vino-svoe.ru`. The owner moved the images to chtozavino.ru on 2026-10-19.
11. Use the submitted accepted photo when a catalogue result image is unavailable.
12. Authorize administrator commands only by `BOT_ADMIN_USER_ID` and the dialog chat type.
    In MAX, the dialog chat ID is not the user ID.
13. Require an explicit `BOT_ADMIN_USER_ID`. Do not keep a real account as a default.
14. Show result feedback only for a successful non-album request.
15. Accept result feedback only from the source MAX user ID.
16. Use `shieldgemma-2-4b-it` for image moderation when moderation is enabled.
17. Use only the `dangerous`, `sexual`, and `violence` moderation policies when moderation is enabled.
18. Use the ShieldGemma service `flagged` list at threshold `0.5` when moderation is enabled.
19. Send the configured rejection illustration for an unsafe image.
20. Reply with a rejection illustration to the source photo.
21. Read the SAM3 base URL only from `SAM3_ENDPOINT`.
22. Use SAM3 to check for a wine bottle and a usable label before recognition.
23. Treat image quality as advisory.
24. Continue recognition when the quality service fails or reports an issue.
25. Request four ranked matcher candidates.
26. Keep matcher score and margin thresholds in environment configuration.
26.1. Use these thresholds to choose the result wording when a candidate exists.
26.2. Show the Top-1 wine card for a low score or a low margin.
26.3. Give low-score wording precedence when both confidence conditions fail.
26.4. Keep the confidence status and HTTP confidence flag accurate for a tentative card.
26.5. Accept a `file` attachment as a photo only when its file name ends with `.jpg`, `.jpeg`,
     `.png`, `.webp`, `.heic`, or `.heif`. The worker checks the image bytes as for an `image`
     attachment.
27. Keep the queue wait estimate in environment configuration.
28. A negative Top-1 feedback action MUST show ranks 2 through 4 and `Ничего из этого`.
29. Run the administration web interface as a separate service.
30. Do not serve accepted source files or quarantine images from the administration web interface.
31. Send an administration retry through the shared bot work queue.
31.1. Delete a request from the administration web interface only when it is not active.
     The deletion removes the row, the source image of each attempt, and the artifacts.
32. Run moderation again for an administration retry when moderation is enabled.
33. Restrict the administration web interface to configured networks.
34. Persist full-fidelity pipeline artifacts only after safe moderation or an explicit
    non-production moderation bypass.
35. Treat pipeline artifact generation as advisory.
36. Serve a full-fidelity pipeline artifact only when the current request remains safe or
    has the explicit non-production bypass state.
37. Create only an irreversible censored preview for an unsafe request.
38. Do not use CSS blur as the only censorship control.
39. Serve a censored preview only when the current request remains unsafe.
40. Never serve a quarantine source file through the administration web interface.
41. Send `k=4` and no pipeline name with every matcher request.
42. Take the wine card of each candidate from the matcher answer. Do not read a local
    catalogue or a local wine code map.
43. Run the internal recognition API in the bot process.
44. Send HTTP API images through the shared work queue.
45. Keep an unmoderated HTTP upload in memory.
46. Do not use a temporary upload file before moderation or its explicit non-production bypass.
47. Restrict the HTTP recognition API to configured LAN networks.
48. Keep `28004` as the default recognition API port and `28005` as the default administration
    port. A deployment selects the published ports.
49. Do not restore an interrupted API request as a MAX request.
50. Require a bearer token for every recognition API request.
51. Apply the API rate and in-flight limits before the service reads an upload body.
52. Keep the administration listener on loopback unless a TLS proxy is the only published route.
53. Production MUST refuse to start when moderation is disabled.
54. Production MUST delete terminal request data after 30 days.
55. Allow only `vino-svoe.ru` and `www.vino-svoe.ru` as result page hosts.
56. Preserve JPEG, PNG, and WebP source types in storage and matcher requests.
56.1. Convert a HEIC or HEIF image to JPEG without EXIF data before moderation.
57. Keep `/healthz` as liveness. Use `/readyz` for database, queue, and upstream reachability.
58. Require at least 32 characters in `BOT_ADMIN_WEB_PASSWORD`.
59. Limit failed administration authentication attempts by socket client address.
60. Deploy production with Docker Compose. `deploy/README.md` is the generic deployment guide.
    `deploy/compose.example.yaml` and `deploy/max-bot.env.example` are its examples. Keep the
    files of a real installation (its Compose file, its environment file, its deployment
    record) outside this repository. Keep the secrets in the environment file of the server
    (mode `0600`). Never put a secret in this repository, the Compose file, its `.env` file,
    or the image. Do not name a specific host, address, or path in this project.

## MAX platform rules

1. Call the Bot API only at `MAX_API_BASE_URL` (default `https://platform-api2.max.ru`).
2. Send the token only in the `Authorization` header, without `Bearer` and never in a query.
3. Trust the bundled Russian Trusted Root CA in addition to the public store.
   Never disable TLS verification.
4. Keep 30 requests per second in total and 2 message operations per second in one chat.
5. Repeat a send only after HTTP 429. A 5xx answer or a timeout can hide a sent message.
6. Treat HTTP 200 with `success: false` as an error.
7. Compare `X-Max-Bot-Api-Secret` in constant time. Answer HTTP 200 only after the update is in
   the `update_inbox` table.
8. Write each update to `update_inbox` before the bot handles it, in both delivery modes.
9. Store the body of each bot message with a callback keyboard in `sent_messages`. A keyboard
   change sends the complete attachment list; an empty list removes all attachments.
10. Do not send the bot token to upload or download hosts.

## Common mistakes

- Do not make a feedback UI update depend on a new database write.
- A repeated callback MUST restore the correct keyboard after a MAX edit failure.
- A callback edit MUST target the clicked message (`callback.message.mid`), not a stored ID.
- Do not add a bot log handler without `SecretRedactingFormatter`. Keep the `httpx` and
  `httpcore` loggers at `WARNING`: `httpx` logs each request URL, and an attachment URL gives
  access to a user photo.
- Change the processing core in `../im-core` (package `chto_za_vino_core`), not here. Then run
  the checks of `../im-core`, `../telegram-bot`, and this project.
- Do not change a copied module (`admin_web.py`, `artifact_backfill.py`, `data_lifecycle.py`)
  only here. Change `../telegram-bot` first, then run `python scripts/sync_shared.py`.
  `tests/test_shared_modules.py` detects a drift.

## Verification

Run this command before deployment:

```bash
./scripts/verify.sh
```
