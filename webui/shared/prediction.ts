// The interactive request includes uploading the original image (up to 10 MiB).
// Allow about 84 seconds at 1 Mbit/s, then the upstream budget and a small margin.
export const PORTAL_PREDICTION_TIMEOUT_MS = 120_000
export const PORTAL_UPSTREAM_TIMEOUT_MS = 30_000

// Preserve the existing official evaluator proxy budget independently of the UI.
export const EVALUATOR_UPSTREAM_TIMEOUT_MS = 8_000
