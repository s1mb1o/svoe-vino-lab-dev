import type { H3Event } from 'h3'
import { DIARY_SLUG_PATTERN } from '#shared/diary'
import { parsePreferences } from '#shared/account-taste'
import { AccountHttpError, accountJson, callAccount, checkOrigin, readJson, sessionOf, type AccountConfigSource } from './account'
import { defaultWineLookup, snapshotFor, type WineLookup } from './diary'

export function preferencesRoute(event: H3Event, source: AccountConfigSource) {
  return accountJson(event, source, async config => {
    const session = sessionOf(event)
    if (event.method !== 'GET') checkOrigin(event, config)
    if (event.method === 'DELETE') {
      await callAccount(config, 'DELETE', '/v1/me/preferences', { session })
      return { preferences: null }
    }
    if (event.method === 'PUT') {
      let body
      try { body = parsePreferences(await readJson(event, 12 * 1024)) } catch { throw new AccountHttpError(400, 'invalid_request') }
      return (await callAccount(config, 'PUT', '/v1/me/preferences', { session, body })).data
    }
    return (await callAccount(config, 'GET', '/v1/me/preferences', { session })).data
  })
}

export function ratingsRoute(event: H3Event, source: AccountConfigSource, slug?: unknown, lookup: WineLookup = defaultWineLookup) {
  return accountJson(event, source, async config => {
    const session = sessionOf(event)
    if (slug === undefined && event.method === 'GET') return (await callAccount(config, 'GET', '/v1/me/ratings', { session, maxBytes: 16 * 1024 * 1024 })).data
    checkOrigin(event, config)
    if (typeof slug !== 'string' || !DIARY_SLUG_PATTERN.test(slug)) throw new AccountHttpError(404, 'not_found')
    const path = `/v1/me/ratings/${slug}`
    if (event.method === 'DELETE') {
      await callAccount(config, 'DELETE', path, { session })
      return { status: 'removed' }
    }
    const body = await readJson(event, 4 * 1024)
    if (!Number.isInteger(body.rating) || Number(body.rating) < 1 || Number(body.rating) > 5) throw new AccountHttpError(400, 'invalid_request')
    if (body.note !== null && body.note !== undefined && (typeof body.note !== 'string' || [...body.note].length > 500 || /[\u0000-\u0008\u000b-\u001f\u007f-\u009f]/u.test(body.note))) throw new AccountHttpError(400, 'invalid_request')
    const snapshot = await snapshotFor(slug, lookup)
    return (await callAccount(config, 'PUT', path, { session, body: { rating: body.rating, note: body.note ?? null, wine_snapshot: snapshot } })).data
  })
}
