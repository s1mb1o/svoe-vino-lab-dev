# Decision 011: quality checks and ranked results

Date: 2026-09-26

## Context

The bot can return a confident wrong Top-1 result.
The bot also sends weak photos to the recognizer.
The matcher already supports a ranked response with scores.
The shared SAM3 service can locate bottles and labels.

## Options

### Local metrics only

This option has no additional service dependency.
It cannot reliably determine whether an image contains a bottle or a label.

### One multimodal model

This option can describe all quality defects.
Its output is less deterministic.
It also adds variable latency.

### Local metrics plus SAM3

Pillow supplies deterministic blur and glare metrics.
SAM3 supplies bottle and label geometry.
The matcher supplies ranked candidates and scores.

## Decision

Use local image metrics plus SAM3.
Use the matcher Top-1 score and score margin for abstention.
Store all four matcher candidates.

## Consequences

Recognition uses the SAM3 service when it is available.
An unavailable or invalid SAM3 response records an advisory failure and does not stop recognition.
The quality thresholds are initial operating values.
Production feedback MUST be used to calibrate the thresholds.
