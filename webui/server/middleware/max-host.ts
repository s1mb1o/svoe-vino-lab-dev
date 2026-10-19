// The MAX mini-app host serves only the diary pages and routes (plan 05, "Deployment").
// Nitro serves public/ files before this middleware, so Caddy filters the mini-app host too.
import { maxHostGuard } from '../utils/account'

export default defineEventHandler(event => maxHostGuard(event, String(useRuntimeConfig(event).accountMaxHost || '')))
