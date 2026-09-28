# Quality, alternatives, and queue plan

Date: 2026-09-26

## Goal

Improve the bot response when the source photo is weak or the first result is wrong.
Keep one Telegram progress message for each accepted photo or album receipt.

## Requirements

1. The matcher MUST request four ranked candidates.
2. A result MUST use a configurable minimum score and minimum first-to-second score margin.
3. The bot MUST answer `Не уверен` when the ranked result does not meet both thresholds.
4. A negative Top-1 feedback action MUST show candidates at ranks 2 through 4.
5. The alternative list MUST include `Ничего из этого`.
6. The bot MUST store the selected alternative or the empty alternative result.
7. The bot MUST check blur and glare with deterministic image metrics.
8. The bot MUST use SAM3 to check for a wine bottle and a usable label.
9. The quality check MUST run after moderation or its explicit non-production bypass and
before recognition.
10. A quality check result MUST be advisory.
11. A quality check failure or issue MUST NOT stop recognition.
12. The bot MUST store a perceptual hash and a difference hash for each accepted image.
13. A moderation rejection MUST show `Сообщить об ошибке фильтра`.
14. The filter error action MUST be available only to the source user.
15. The filter error action MUST be stored once.
16. A queue receipt MUST show the queue position and an approximate wait.
17. The bot MUST edit the queue receipt when processing starts.
18. The bot MUST keep one queue receipt for a Telegram album.
19. A successful result MUST contain an `Открыть страницу вина` URL button.
20. The bot MUST store the queue wait and each main processing step duration.
21. Each timing row MUST contain the request ID, step, start time, duration, and outcome.
22. The service journal MUST contain one timing record for each stored step.
23. A repeated negative feedback action MUST restore the alternative keyboard.
24. A Telegram keyboard edit failure MUST send the alternatives in a new message.

## Service contracts

### SAM3

Read the base URL from `SAM3_ENDPOINT`.
Use `POST {SAM3_ENDPOINT}/segment_multi`.
Send one multipart `image` field.
Send `wine bottle, label, wine bottle label` in `texts`.
Use the returned boxes and scores.
Do not request masks.

### Matcher

Use `POST {MATCHER_ENDPOINT}?limit=4`.
Accept only `{"candidates":[{"slug","score","rank"}, ...]}`.
Reject an invalid, empty, duplicate, or unordered candidate list.

## Default thresholds

Use `0.70` as the minimum Top-1 score.
Use `0.015` as the minimum score margin.
The measured matcher median margin is approximately `0.040` for correct Top-1 results.
The measured matcher median margin is approximately `0.007` for wrong Top-1 results.
Keep both thresholds in environment configuration.

Use a normalized long edge of 1024 pixels for local quality metrics.
Use a Laplacian variance below `80` as the blur condition.
Use an overexposed low-chroma share above `0.20` inside the label box as the glare condition.
Use a bottle box area below `0.10` of the image as a missing or unusable bottle condition.
Use a label box area below `0.015` of the image as a tiny or unusable label condition.
Keep each quality threshold in environment configuration.

## Data model

Add image hash, quality, confidence, and moderation appeal fields to `requests`.
Add one `request_candidates` row for each ranked matcher candidate.
Keep the existing Top-1 feedback fields.
Add the selected alternative rank, slug, and selection time.
Add one append-only `request_step_timings` row for each measured step attempt.

## Queue estimate

Start with a configurable estimate of 20 seconds for one photo.
Update the estimate with an exponential moving average after each completed job.
Calculate the wait from the number of jobs ahead and the worker count.

## Verification

Add unit tests for all parsers and metrics.
Add repository migration and callback tests.
Add queue estimate tests.
Update the manual smoke tests.
Run `uv run ruff check .`.
Run `uv run pytest -q`.
