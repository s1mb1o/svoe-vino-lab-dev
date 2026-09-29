# Context chto-za-vino-bot

This project contains the Telegram bot at `@ChtoZaVinoBot`.
Read `README.md` and `docs/specification.md` before a change.
The workspace rules are in `../../CLAUDE.md`.

## Safety rules

1. The bot MUST moderate each image before it writes the image to disk when moderation is enabled.
2. A moderation failure MUST fail closed when moderation is enabled.
3. Production MUST keep `moderation.enabled` set to `true`.
4. The bot MUST NOT send an unsafe image to the recognition service.
5. The bot MUST store an unsafe image only under `quarantine`.
6. The `quarantine` directory MUST use owner-only permissions.
7. The bot MUST NOT write `TELEGRAM_BOT_TOKEN` to a file in this repository.
8. Logs MUST NOT contain image bytes, tokens, first names, last names, or usernames.
9. The database MAY contain the Telegram identity snapshot that the user authorized.

## Service rules

1. Use Telegram long polling.
2. Use `192.168.86.14:18081` for the `llama-swap` service on `gx10`. In a container,
   `127.0.0.1` is the container itself.
3. Use the prod matcher endpoint `http://192.168.86.14:28000/v1/match` on `gx10`.
4. Keep the request limit in environment configuration.
5. Keep the default limit at 50 image requests in 3600 seconds per Telegram user ID.
6. Keep user-visible bot text in Russian.
7. Keep technical documentation in English and use STE-style text.
8. Send all photo processing through the shared work queue.
9. Keep the default queue worker count at one until a GPU load test approves a higher value.
10. Fetch catalogue result images only from `https://api.vino-svoe.ru`.
11. Use the submitted accepted photo when a catalogue result image is unavailable.
12. Authorize administrator commands only by `BOT_ADMIN_USER_ID` and the private chat ID.
13. Require an explicit `BOT_ADMIN_USER_ID`. Do not keep a real account as a default.
14. Show result feedback only for a successful non-album request.
15. Accept result feedback only from the source Telegram user ID.
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
27. Keep the queue wait estimate in environment configuration.
28. A negative Top-1 feedback action MUST show ranks 2 through 4 and `Ничего из этого`.
29. Run the administration web interface as a separate service.
30. Do not serve accepted source files or quarantine images from the administration web interface.
31. Send an administration retry through the shared bot work queue.
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
48. Keep TCP port `28002` as the production recognition API port on `gx10`.
49. Do not restore an interrupted API request as a Telegram request.
50. Require a bearer token for every recognition API request.
51. Apply the API rate and in-flight limits before the service reads an upload body.
52. Keep the administration listener on loopback unless a TLS proxy is the only published route.
53. Production MUST refuse to start when moderation is disabled.
54. Production MUST delete terminal request data after 30 days.
55. Allow only `vino-svoe.ru` and `www.vino-svoe.ru` as result page hosts.
56. Preserve JPEG, PNG, and WebP source types in storage and matcher requests.
57. Keep `/healthz` as liveness. Use `/readyz` for database, queue, and upstream reachability.
58. Require at least 32 characters in `BOT_ADMIN_WEB_PASSWORD`.
59. Limit failed administration authentication attempts by socket client address.

## Common mistakes

- Do not make a feedback UI update depend on a new database write.
- A repeated callback MUST restore the correct keyboard after a Telegram edit failure.
- Do not add a bot log handler without `SecretRedactingFormatter`. An aiogram download error
  contains the file URL, and that URL contains the bot token.

## Verification

Run these commands before deployment:

```bash
uv sync --extra dev
uv run ruff check .
uv run pytest -q
```
