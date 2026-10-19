// The MAX mini-app host serves only the diary pages and routes (plan 05, "Deployment").
import { getHeader, getRequestURL, sendRedirect, setResponseStatus } from 'h3'
import { maxHostDecision } from '../utils/account'

export default defineEventHandler((event) => {
  const host = String(useRuntimeConfig(event).accountMaxHost || '').trim().toLowerCase()
  if (!host) return
  // Caddy keeps the original Host header. Nuxt listens on loopback only.
  const requestHost = (getHeader(event, 'host') ?? '').toLowerCase().replace(/:\d+$/, '')
  if (requestHost !== host) return
  const decision = maxHostDecision(event.method, getRequestURL(event).pathname)
  if (decision === 'redirect') return sendRedirect(event, '/max', 302)
  if (decision === 'reject') {
    setResponseStatus(event, 404)
    return 'Not found'
  }
})
