# Context chto-za-vino-bot

This project contains the Telegram bot at `@ChtoZaVinoBot`.
Read `README.md` and `docs/specification.md` before a change.
The workspace rules are in `../../CLAUDE.md`.

## Safety rules

1. The bot MUST moderate each image before it writes the image to disk.
2. A moderation failure MUST fail closed.
3. The bot MUST NOT send an unsafe image to the recognition service.
4. The bot MUST store an unsafe image only under `quarantine`.
5. The `quarantine` directory MUST use owner-only permissions.
6. The bot MUST NOT write `TELEGRAM_BOT_TOKEN` to a file in this repository.
7. Logs MUST NOT contain image bytes, tokens, first names, last names, or usernames.
8. The database MAY contain the Telegram identity snapshot that the user authorized.

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
11. Use the submitted safe photo when a catalogue result image is unavailable.
12. Authorize administrator commands only by `BOT_ADMIN_USER_ID` and the private chat ID.
13. Keep `207286210` as the default administrator user ID.
14. Show result feedback only for a successful non-album request.
15. Accept result feedback only from the source Telegram user ID.
16. Use `shieldgemma-2-4b-it` for image moderation.
17. Use only the `dangerous`, `sexual`, and `violence` moderation policies.
18. Use the ShieldGemma service `flagged` list at threshold `0.5`.
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
32. Run moderation again for an administration retry.
33. Restrict the administration web interface to configured LAN networks.
34. Persist full-fidelity pipeline artifacts only after safe moderation.
35. Treat pipeline artifact generation as advisory.
36. Serve a full-fidelity pipeline artifact only when the current request remains safe.
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
46. Do not use a temporary upload file before moderation.
47. Restrict the HTTP recognition API to configured LAN networks.
48. Keep TCP port `28002` as the production recognition API port on `gx10`.
49. Do not restore an interrupted API request as a Telegram request.

## Common mistakes

- Do not make a feedback UI update depend on a new database write.
- A repeated callback MUST restore the correct keyboard after a Telegram edit failure.

## Verification

Run these commands before deployment:

```bash
uv sync --extra dev
uv run ruff check .
uv run pytest -q
```
