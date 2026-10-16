# Smoke tests

## Profile

- Open `@se14697933_bot` in MAX.
- Confirm that the bot card shows the logo without a clipped part.
- Confirm that the card description is the text of `SHORT_DESCRIPTION` in `profile.py`.
  MAX has no API for the description. Set it on business.max.ru; the change passes moderation.
- Run `uv run chto-za-vino-max-profile`.
- Confirm that `/start`, `/help`, `/stats`, and `/privacy` appear in the command menu.
- Confirm that `/users` and `/reset_limit` do not appear in the menu. MAX has no command scope.
- Confirm that `/users` and `/reset_limit` work in the administrator's dialog.
- Open `https://max.ru/se14697933_bot?start=privacy`.
- Confirm that the bot shows the privacy notice with the user's own MAX user ID.

## Start

- Press «Начать» for a new dialog, then send `/start`.
- Confirm that both actions show the same message.
- Confirm that the bot shows `Мне есть 18 лет` and `Мне нет 18 лет` buttons.
- Confirm that the bot shows the alcohol notice.
- Confirm that the message names `vino-svoe.ru`.
- Confirm that the message names `ALOLA 1`.
- Confirm that the message contains `@s1mb1o`.
- Confirm that the message states that the photo is saved.
- Send a photo before the adult confirmation.
- Confirm that the photo does not enter the queue.
- Confirm that the photo does not use the hourly rate limit.
- Select `Мне нет 18 лет`.
- Confirm that the bot rejects a subsequent photo.
- Select `Мне есть 18 лет` from a new `/start` message.
- Confirm that the bot accepts a subsequent photo.

## Recognition

- Confirm that each matcher request uses `k=4` and does not select a pipeline.
- Send a clear catalogue wine photo.
- Confirm that the bot first shows the processing status.
- Confirm that the status shows the queue position and approximate wait.
- Confirm that the same status message changes when processing starts.
- Confirm that the final message contains a wine name.
- Confirm that the final message is a photo message.
- Confirm that the result photo shows the official catalogue image.
- Confirm that the complete bottle is visible in the MAX preview.
- Confirm that the bottle has a small white margin above and below it.
- Confirm that a very tall source image appears on a 4:5 white canvas.
- Confirm that the caption contains the producer, color, sugar class, and grape varieties.
- Confirm that a missing parameter appears as `нет данных`.
- Confirm that the final message contains a `vino-svoe.ru/wines/` link.
- Confirm that the final message shows an `Открыть страницу вина` inline button.
- Confirm that the final message contains the alcohol notice.
- Block the official image host in a test environment.
- Confirm that the bot sends the submitted safe photo with the result caption.
- Confirm that the database row has status `recognized`.
- Confirm that the image exists under `accepted`.
- Confirm that a successful single-photo result shows `✅ Совпало` and `❌ Не совпало` buttons.
- Select `✅ Совпало` as the source user.
- Confirm that the bot thanks the user and removes both buttons.
- Confirm that the database stores the positive value and submission time.
- Try to submit another value for the same request.
- Confirm that the stored value does not change.
- Try to select a feedback button from a different MAX user.
- Confirm that the bot rejects the feedback.
- Send another clear photo and select `❌ Не совпало`.
- Confirm that the bot shows candidates 2, 3, and 4.
- Confirm that the bot shows `Ничего из этого`.
- Simulate one failed MAX keyboard edit (`PUT /messages`).
- Confirm that the bot sends the alternatives in a new message.
- Repeat the negative feedback callback after the value is stored.
- Confirm that the bot restores the three alternatives.
- Select one alternative.
- Confirm that the database stores its rank, slug, and selection time.
- Repeat the flow and select `Ничего из этого`.
- Confirm that the database stores rank zero and no selected slug.
- Send a result with a Top-1 score below `BOT_MATCH_MIN_SCORE`.
- Confirm that the bot answers `Не уверен` and does not show a confident wine card.
- Send a result with a score margin below `BOT_MATCH_MIN_MARGIN`.
- Confirm that the bot answers `Не уверен` and stores the candidates.

## Photo quality

- Send a strongly blurred bottle photo.
- Confirm that the bot stores the blur issue and continues to recognition.
- Send a bottle photo with a strong clipped glare over the label.
- Confirm that the bot stores the glare issue and continues to recognition.
- Send a scene without a wine bottle.
- Confirm that the bot stores the missing-bottle issue and continues to recognition.
- Send a scene where the bottle label occupies less than the configured area.
- Confirm that the bot stores the small-label issue and continues to recognition.
- Stop the SAM3 endpoint.
- Confirm that the bot records the quality-check failure and continues to recognition.
- Send a photo that triggers one or more quality issues.
- Confirm that the bot stores the issues and continues to recognition.
- Confirm that a moderated database row contains `image_phash` and `image_dhash`.

## Queue

- Send one MAX message with three wine photos (a MAX album).
- Confirm that the bot creates one queue acknowledgement for the complete album.
- Confirm that the bot does not create another queue acknowledgement for each photo.
- Send one MAX message with one photo and one video.
- Confirm that the bot treats it as an album: one acknowledgement and no feedback buttons.
- Confirm that the bot processes the photos in the album order.
- Confirm that the bot returns one result for each photo.
- Confirm that each result replies to the source message.
- Confirm that no album result shows feedback buttons.
- Confirm that the three photos use three requests from the hourly rate limit.
- Send three photos from two MAX accounts without waiting for a result.
- Confirm that each photo gets an immediate queue acknowledgement.
- Confirm that `/stats` responds while one photo is processed.
- Confirm that `/stats` shows the waiting and active queue counts.
- Confirm that the default configuration processes one photo at a time.
- Restart the bot while one photo waits in the queue.
- Confirm that the bot restores and processes the interrupted requests.
- Confirm that `request_step_timings` contains `queue_wait` and each applicable main step.
- Confirm that each timing row contains a start time, duration, and outcome.
- Confirm that the service journal contains the same request ID and step names.
- Set `BOT_QUEUE_CAPACITY=1` in a test environment.
- Send a second photo while the first photo is processed.
- Confirm that the bot rejects the second photo as a capacity rejection.
- Confirm that the rejected photo does not use the hourly rate limit.

## Safety

- Set `BOT_ENVIRONMENT=test`, set `moderation.enabled` to `false`, and remove
  `MODERATION_ENDPOINT` from a test environment.
- Start the bot and confirm that the log states that image moderation is disabled.
- Send a valid test photo and confirm that ShieldGemma receives no request.
- Confirm that recognition continues and that the moderation category is `disabled`.
- Confirm that `moderation_safe` is `NULL`.
- Confirm that the administration page shows `Проверка выполнена: нет`,
  `Проверка пропущена: да`, and `Безопасно: не проверено`.
- Submit an HTTP API image and confirm that moderation contains `performed=false`,
  `bypassed=true`, and `safe=null`.
- Restore `moderation.enabled` to `true` for the remaining safety checks.
- Set `BOT_ENVIRONMENT=production` with `moderation.enabled=false`.
- Confirm that the bot refuses to start.
- Use an internal synthetic unsafe fixture.
- Do not use real abusive material for the smoke test.
- Confirm that the bot sends a multipart `image` field to `shieldgemma-2-4b-it`.
- Confirm that the moderation result contains `dangerous`, `sexual`, and `violence` scores.
- Confirm that one score at or above `0.5` appears in `flagged`.
- Confirm that the bot does not return a wine result.
- Confirm that the bot replies to the source photo with the supplied monkey illustration.
- Confirm that the caption states that the content is inappropriate and was not sent to recognition.
- Confirm that the result shows `Сообщить об ошибке фильтра`.
- Select the filter error button as the source user.
- Confirm that the database stores the appeal time and removes the button.
- Try the callback as another MAX user.
- Confirm that the bot rejects the callback.
- Confirm that the temporary processing status is removed.
- Confirm that the database row has status `quarantined`.
- Confirm that the image exists only under `quarantine`.
- Stop the moderation endpoint.
- Send a safe test photo.
- Confirm that the bot reports a temporary safety-check failure.
- Confirm that the image does not exist under `accepted` or `quarantine`.
- Return an unknown policy or an inconsistent `flagged` list in a test environment.
- Confirm that the bot fails closed and does not store or recognize the image.
- Remove the rejection illustration in a test environment.
- Confirm that startup fails instead of running with a missing response asset.
- Simulate a MAX photo-send failure (upload or `POST /messages`).
- Confirm that the bot shows the text rejection status.

## Rate limit

- Send 50 images from one test account inside one hour.
- Confirm that each request enters processing.
- Send the 51st image.
- Confirm that the bot returns the remaining wait time.
- Restart the bot.
- Send one more image inside the same hour.
- Confirm that the request is still limited.

## Statistics

- Send `/stats` as a regular user.
- Confirm that the response contains only that user's total, daily, recognized, failed, quarantined, and hourly counts.
- Confirm that the response does not contain participant or queue counts.
- Send `/stats` as the configured `BOT_ADMIN_USER_ID` in its dialog.
- Confirm that the response contains aggregate, participant, queue, and personal hourly counts.

## Administrator commands

- Send `/users` as a regular user.
- Confirm that the bot denies access.
- Send `/users` as the configured `BOT_ADMIN_USER_ID` in its dialog.
- Confirm that the response shows no more than 20 users on one page.
- Confirm that each entry shows username, name, user ID, request count, hourly use, and last request time in Moscow time.
- Send `/users 2` when at least 21 users exist.
- Confirm that the second page starts with user 21.
- Send `/reset_limit` as the administrator.
- Confirm that the administrator's current hourly use becomes zero.
- Send `/reset_limit @username` for a limited test user.
- Confirm that the user can send a new photo.
- Confirm that the user's request history and total statistics do not change.
- Restart the bot.
- Confirm that the reset still applies.
- Send `/reset_limit USER_ID` for another limited test user.
- Confirm that the user can send a new photo.
- Send `/users` from a group as the administrator.
- Confirm that the bot denies access.
- Send a wine photo as the administrator in its dialog.
- Confirm that the result or the `Не уверен` answer ends with
  `Оценка: … (порог …) · отрыв: … (порог …)`.
- Send the same photo as a regular user.
- Confirm that the answer has no `Оценка` line.

## Administration web interface

- Open the administration interface through its configured HTTPS proxy or secure tunnel.
- Confirm that the browser requires a username and password.
- Set the failed-authentication limit to `2` in a test environment.
- Submit an incorrect password two times from one client address.
- Confirm that both attempts return HTTP 401.
- Submit the incorrect password again.
- Confirm that the attempt returns HTTP 429 with a `Retry-After` header.
- Submit the correct password.
- Confirm that the correct password also returns HTTP 429 during the `Retry-After` period.
- Wait for the `Retry-After` period and submit the correct password.
- Confirm that access succeeds.
- Open the interface from an address outside the configured CIDR networks.
- Confirm that access is denied.
- Confirm that the overview shows aggregate statistics and recent requests.
- Confirm that the user page shows total requests and current hourly use.
- Open `/users`, `/requests`, and `/appeals` with `page=999999999999999999`.
- Confirm that each page returns HTTP 400 and that the administration service stays healthy.
- Reset one test user's rate limit.
- Confirm that the user can send another photo.
- Confirm that the reset preserves the request history.
- Open one request.
- Confirm that the page shows moderation, quality, candidates, feedback, and step timings.
- Confirm that the page shows the exact matcher input and the moderation image.
- Confirm that the page shows the combined SAM3 overlay with boxes, prompts, and scores.
- Confirm that the page shows each SAM3 mask.
- Confirm that the page shows the selected bottle and label box crops.
- Confirm that the page shows the selected bottle and label masked cutouts.
- Confirm that a successful request shows the final MAX result image.
- Open one artifact and confirm that the full image loads.
- Confirm that desktop request cards use at most two columns.
- Confirm that names, statuses, dates, and decimal values do not render one character per line.
- Confirm that each request card becomes full-width on a narrow mobile viewport.
- Confirm that the page does not show an accepted or quarantine storage path.
- Change a test request to an unsafe moderation result.
- Confirm that the request page and artifact route no longer expose its safe artifacts.
- Confirm that a quarantined request shows one strongly blurred censored preview.
- Confirm that the preview contains no recoverable fine detail.
- Confirm that the preview file has a maximum longest side of 768 pixels.
- Confirm that the browser receives the blurred JPEG and not a CSS-blurred source.
- Confirm that the quarantine storage path does not work through the artifact route.
- Open the filter error page.
- Confirm that a stored moderation appeal appears.
- Open a request with a safe moderation result.
- Request repeat processing.
- Confirm that the bot adds the request to its FIFO queue.
- Confirm that the bot runs moderation again.
- Open a quarantined request.
- Confirm that the interface does not offer repeat processing.
- Restart the administration service after a repeat request and before bot pickup.
- Confirm that the repeat request remains pending.
- Confirm that every state-changing form rejects a missing or invalid CSRF token.
- Run `chto-za-vino-max-artifacts REQUEST_ID` for a previously safe request.
- Confirm that the command creates artifacts and does not send a MAX message.
- Run the same command for a previously quarantined request.
- Confirm that the command creates only one censored preview and sends no MAX message.

## HTTP recognition API

- Open `http://192.168.86.14:28004/docs` from the home LAN.
- Confirm that Swagger UI shows `POST /api/v1/recognize`.
- Open the API from an address outside `BOT_HTTP_API_ALLOWED_NETWORKS`.
- Confirm that access is denied.
- Submit one clear wine image in the multipart `image` field with
  `Authorization: Bearer <BOT_HTTP_API_TOKEN>`.
- Confirm that the response has HTTP 200 and status `recognized` or `abstained`.
- Confirm that `matcher_pipeline` identifies the pipeline selected by the matcher.
- Confirm that the response contains up to four ranked candidates.
- Confirm that each candidate contains the wine name, color, sugar class, grape varieties,
  and catalogue URL when the catalogue has these values.
- Use a matcher candidate whose wine card contains a QR URL.
- Confirm that its selected wine object and candidate object contain `qr_urls`.
- Use a wine without a QR URL.
- Confirm that its wine object does not contain `qr_urls`.
- Confirm that the response contains moderation, quality, and step timing objects.
- Confirm that production moderation contains `performed=true`, `bypassed=false`, and a
  Boolean `safe` value.
- Confirm that the request appears in the administration interface with source `HTTP API`.
- Submit a synthetic unsafe fixture.
- Confirm that the response has status `quarantined`.
- Confirm that the response does not contain image bytes or a storage path.
- Stop the moderation endpoint and submit a safe fixture.
- Confirm that the response has HTTP 503 and status `moderation_failed`.
- Fill the shared queue and submit another API request.
- Confirm that the endpoint returns HTTP 503 with error `queue_full`.
- Confirm that an API request and a MAX photo are processed sequentially by one queue worker.
- Submit a request without the bearer token and with an incorrect bearer token.
- Confirm that both requests return HTTP 401 before image processing starts.
- Exceed `BOT_HTTP_API_RATE_LIMIT` from one client address.
- Confirm that the next request returns HTTP 429.
- Fill `BOT_HTTP_API_MAX_IN_FLIGHT` with incomplete requests.
- Confirm that another request is rejected before its upload body is read.
- Submit JPEG, PNG, and WebP fixtures.
- Confirm that storage and matcher multipart requests preserve each source type.
- Restart the bot while an API request waits in memory.
- Confirm that the interrupted API request becomes `internal_failed` after restart.
- Confirm that the service does not attempt to send the interrupted API request to MAX.

## Matcher endpoint `/v1/match`

- Start the bot with `MATCHER_ENDPOINT=http://127.0.0.1:28000/v1/not-match`.
- Confirm that the bot stops at start with an error that names `endpoints.matcher`.
- Remove one endpoint variable that `config.yaml` references.
- Confirm that the bot stops at start and names the missing variable without printing its value.
- Send a clear wine photo through MAX.
- Confirm that the bot answers with a result card or with `Не уверен`.
- Confirm in the service log that the matcher request went to `/v1/match?k=4` and did not
  include a pipeline selector.
- Press `❌ Не совпало` on a result.
- Confirm that the alternatives show wine names, not slugs.
- Submit a photo to `POST /api/v1/recognize`.
- Confirm that `matcher_pipeline` is the pipeline name returned by the matcher.
- Confirm that each candidate has a `wine` object with `name` and `page_url`.
- Stop the matcher and submit a safe photo.
- Confirm that the response has HTTP 502 and status `recognition_failed`.
- Open an old request of the version before 2026-09-28 in the administration interface.
- Confirm that the page opens and that its candidates show the slug.

## Docker deployment

- Run `docker compose ps` in `/srv/svoe-vino-lab/prod/max-bot`.
- Confirm that both containers are `healthy`.
- Confirm that `config/max-bot.env` has mode `600` and that `.env` names the deployed revision.
- Confirm that the production `config.yaml` sets `moderation.enabled` to `true`.
- Confirm that `docker compose logs max-bot` contains `MAX bot connected` and no token.
- Confirm that the administration interface answers only on `127.0.0.1:28005` of gx10.
- Open it through `ssh -N -L 28005:127.0.0.1:28005 gx10` and confirm that it asks for the
  administration password.
- Confirm that another LAN host cannot connect to port `28005`.
- Confirm that `http://192.168.86.14:28004/healthz` answers `ok`.
- Confirm that `http://192.168.86.14:28004/readyz` reports every dependency as ready.
- Confirm that `docker compose exec max-bot touch /app/x` fails (read-only root file system).
- Restart the bot container while no photo job runs.
- Confirm that the bot answers a new photo after the restart.
- Run `docker compose stop` and confirm that it ends in a few seconds: the bot exits with code 0;
  the administration interface exits with 0 or 143, because uvicorn raises SIGTERM again after
  its graceful shutdown.

## Host verification and data lifecycle

- Run `uv run chto-za-vino-max-host-demo` without private model services.
- Confirm that it returns a safe, acceptable, confident `host-demo` result.
- Create a terminal request older than 30 days with a source image and artifacts.
- Restart the bot.
- Confirm that the request, files, artifacts, and inactive user profile are deleted.
- Create an active request older than 30 days.
- Confirm that retention does not delete it.
- Stop the bot and run `uv run chto-za-vino-max-delete-user USER_ID --confirm`.
- Confirm that all request rows, source images, artifacts, and the user profile are deleted.

## MAX platform

- Run `curl https://platform-api2.max.ru/me` on the host without the bundled CA.
- Confirm that TLS verification fails (curl exit code 60). The host needs the Минцифры root.
- Start the bot and confirm that the log shows `MAX bot connected bot_user_id=...`.
- Confirm that the log contains no bot token, webhook secret, image URL, or user name.
- Set `MAX_UPDATE_MODE=polling` while a webhook subscription is active.
- Confirm that the bot refuses to start and names the active subscription.
- Set `BOT_ENVIRONMENT=production` and `MAX_UPDATE_MODE=polling` without
  `MAX_ALLOW_PRODUCTION_POLLING=true`.
- Confirm that the bot refuses to start.
- In webhook mode, confirm that `GET /subscriptions` shows the configured HTTPS URL.
- Send a webhook request with a wrong `X-Max-Bot-Api-Secret` header.
- Confirm that the receiver answers HTTP 401 and stores nothing.
- Stop the bot after a photo update is stored in `update_inbox` and before it is processed.
- Start the bot again.
- Confirm that the update is processed once and that the photo gets one request row.
- Send a photo, delete the source message, and wait until the request is processed.
- Confirm that the result is sent without the reply link.
- Send five photos as five separate messages without waiting.
- Confirm that the bot keeps two or fewer message operations per second in the dialog.
