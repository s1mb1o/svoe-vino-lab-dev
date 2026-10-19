// Server side of the «Винный дневник» lists: the history of found wines and the saved wines.
// Plan: docs/plans/07_diary-history-and-saved.md. The rules of /api/account/* apply
// (docs/account.md): Origin on writes, no-store, a 2 s timeout, no retry.
import type { H3Event } from 'h3'
import type { Wine } from '#shared/catalog'
import {
  DIARY_DAY_PATTERN, DIARY_SLUG_PATTERN, SITE_HISTORY_SOURCES, diarySnapshot, isSavedSource, isSavedStatus,
  type DiaryWine, type HistoryDay, type HistoryItem, type SavedItem,
} from '#shared/diary'
import wines from '../data/wines.json'
import {
  AccountHttpError, accountJson, callAccount, checkOrigin, readJson, sessionOf,
  type AccountConfig, type AccountConfigSource,
} from './account'
import { fetchSourceWine } from './wine-metadata'

// A history of 2,000 wines is about 600 KB of JSON.
const LIST_RESPONSE_BYTES = 2 * 1024 * 1024

/** Finds the wine of a slug: the local catalogue, then the vino-svoe.ru API. */
export type WineLookup = (slug: string) => Promise<Wine | null>

export const defaultWineLookup: WineLookup = async slug => {
  const local = (wines as Wine[]).find(wine => wine.slug === slug)
  return local ?? fetchSourceWine(slug)
}

/**
 * The snapshot of a wine for a diary write. A wine that the catalogue does not know is refused
 * (404 `unknown_wine`). When the catalogue does not answer, the write goes on without a snapshot.
 */
export async function snapshotFor(slug: string, lookup: WineLookup): Promise<DiaryWine | null> {
  let wine: Wine | null
  try {
    wine = await lookup(slug)
  } catch {
    return null
  }
  if (!wine) throw new AccountHttpError(404, 'unknown_wine')
  return diarySnapshot(wine)
}

function slugParam(value: unknown): string {
  if (typeof value !== 'string' || !DIARY_SLUG_PATTERN.test(value)) throw new AccountHttpError(404, 'not_found')
  return value
}

const text = (value: unknown) => typeof value === 'string' ? value : ''

function wineView(value: unknown): DiaryWine | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  return diarySnapshot(value as Record<string, unknown>)
}

type ServiceHistoryItem = {
  slug?: string; wine?: unknown; first_met_at?: string; last_met_at?: string; days_count?: number
  sources?: unknown; saved_status?: string | null; days?: Array<{ met_on?: string; source?: string; first_at?: string }>
}
type ServiceSavedItem = {
  slug?: string; wine?: unknown; status?: string; source?: string; added_at?: string; updated_at?: string; in_history?: boolean
}

function historyView(item: ServiceHistoryItem): HistoryItem {
  const view: HistoryItem = {
    slug: text(item.slug),
    wine: wineView(item.wine),
    firstMetAt: text(item.first_met_at),
    lastMetAt: text(item.last_met_at),
    daysCount: typeof item.days_count === 'number' ? item.days_count : 0,
    sources: Array.isArray(item.sources) ? item.sources.filter((source): source is string => typeof source === 'string') : [],
    savedStatus: isSavedStatus(item.saved_status) ? item.saved_status : null,
  }
  if (Array.isArray(item.days)) {
    view.days = item.days.map((day): HistoryDay => ({ metOn: text(day.met_on), source: text(day.source), firstAt: text(day.first_at) }))
  }
  return view
}

function savedView(item: ServiceSavedItem): SavedItem {
  return {
    slug: text(item.slug),
    wine: wineView(item.wine),
    status: isSavedStatus(item.status) ? item.status : 'not_tasted',
    source: text(item.source),
    addedAt: text(item.added_at),
    updatedAt: text(item.updated_at),
    inHistory: item.in_history === true,
  }
}

// --------------------------------------------------------------------------- history

export function historyListRoute(event: H3Event, source: AccountConfigSource) {
  return accountJson(event, source, async config => {
    const { data } = await callAccount<{ items?: ServiceHistoryItem[]; save_history?: boolean }>(config, 'GET', '/v1/me/history', {
      session: sessionOf(event), maxBytes: LIST_RESPONSE_BYTES,
    })
    return { items: (data.items ?? []).map(historyView), saveHistory: data.save_history !== false }
  })
}

export function historyItemRoute(event: H3Event, source: AccountConfigSource, slug: unknown) {
  return accountJson(event, source, async config => {
    const session = sessionOf(event)
    const { data } = await callAccount<ServiceHistoryItem>(config, 'GET', `/v1/me/history/${slugParam(slug)}`, { session, maxBytes: LIST_RESPONSE_BYTES })
    return historyView(data)
  })
}

/**
 * Records a found wine for today. The browser sends it after a match, in the background.
 * A mock prediction is not the person's wine, so mock mode refuses the write.
 */
export function historyRecordRoute(event: H3Event, source: AccountConfigSource, options: { mock: boolean; lookup?: WineLookup }) {
  return accountJson(event, source, async config => {
    checkOrigin(event, config)
    const session = sessionOf(event)
    if (options.mock) throw new AccountHttpError(409, 'mock_mode')
    const body = await readJson(event)
    const slug = typeof body.slug === 'string' && DIARY_SLUG_PATTERN.test(body.slug) ? body.slug : ''
    if (!slug) throw new AccountHttpError(400, 'invalid_request')
    const recordSource = typeof body.source === 'string' && SITE_HISTORY_SOURCES.includes(body.source as never) ? body.source : ''
    if (!recordSource) throw new AccountHttpError(400, 'invalid_request')
    const snapshot = await snapshotFor(slug, options.lookup ?? defaultWineLookup)
    const { data } = await callAccount<{ status?: string; met_on?: string }>(config, 'POST', '/v1/me/history', {
      session, body: { slug, source: recordSource, ...(snapshot ? { wine_snapshot: snapshot } : {}) },
    })
    const status = data.status === 'recorded' || data.status === 'already' || data.status === 'off' ? data.status : 'off'
    return { status, ...(typeof data.met_on === 'string' && DIARY_DAY_PATTERN.test(data.met_on) ? { metOn: data.met_on } : {}) }
  })
}

export function historyDeleteDayRoute(event: H3Event, source: AccountConfigSource, slug: unknown, day: unknown) {
  return accountJson(event, source, async config => {
    checkOrigin(event, config)
    const session = sessionOf(event)
    if (typeof day !== 'string' || !DIARY_DAY_PATTERN.test(day)) throw new AccountHttpError(404, 'not_found')
    await callAccount(config, 'DELETE', `/v1/me/history/${slugParam(slug)}/days/${day}`, { session })
    return { status: 'removed' }
  })
}

export function historyDeleteWineRoute(event: H3Event, source: AccountConfigSource, slug: unknown) {
  return accountJson(event, source, async config => {
    checkOrigin(event, config)
    const session = sessionOf(event)
    await callAccount(config, 'DELETE', `/v1/me/history/${slugParam(slug)}`, { session })
    return { status: 'removed' }
  })
}

export function historyClearRoute(event: H3Event, source: AccountConfigSource) {
  return accountJson(event, source, async config => {
    checkOrigin(event, config)
    await callAccount(config, 'DELETE', '/v1/me/history', { session: sessionOf(event) })
    return { status: 'cleared' }
  })
}

/** Account settings: today only the switch «Записывать найденные вина». */
export function settingsRoute(event: H3Event, source: AccountConfigSource) {
  return accountJson(event, source, async config => {
    checkOrigin(event, config)
    const session = sessionOf(event)
    const body = await readJson(event)
    if (typeof body.saveHistory !== 'boolean') throw new AccountHttpError(400, 'invalid_request')
    const { data } = await callAccount<{ user?: unknown }>(config, 'PATCH', '/v1/me', { session, body: { save_history: body.saveHistory } })
    return { user: data.user }
  })
}

// --------------------------------------------------------------------------- saved wines

export function savedListRoute(event: H3Event, source: AccountConfigSource) {
  return accountJson(event, source, async config => {
    const { data } = await callAccount<{ items?: ServiceSavedItem[] }>(config, 'GET', '/v1/me/saved', {
      session: sessionOf(event), maxBytes: LIST_RESPONSE_BYTES,
    })
    return { items: (data.items ?? []).map(savedView) }
  })
}

/** The saved slugs and statuses: the state of the pins on a page. */
export function savedSlugsRoute(event: H3Event, source: AccountConfigSource) {
  return accountJson(event, source, async config => {
    const { data } = await callAccount<{ items?: Array<{ slug?: string; status?: string }> }>(config, 'GET', '/v1/me/saved/slugs', {
      session: sessionOf(event), maxBytes: LIST_RESPONSE_BYTES,
    })
    return {
      items: (data.items ?? [])
        .filter(item => typeof item.slug === 'string' && isSavedStatus(item.status))
        .map(item => ({ slug: item.slug as string, status: item.status })),
    }
  })
}

/** Saves a wine, or changes its status. The server builds the snapshot from the slug. */
export function savedPutRoute(event: H3Event, source: AccountConfigSource, slug: unknown, options: { lookup?: WineLookup } = {}) {
  return accountJson(event, source, async (config: AccountConfig) => {
    checkOrigin(event, config)
    const session = sessionOf(event)
    const wineSlug = slugParam(slug)
    const body = await readJson(event)
    if (!isSavedStatus(body.status) || !isSavedSource(body.source)) throw new AccountHttpError(400, 'invalid_request')
    // A status change of a saved wine keeps the stored snapshot: no catalogue request.
    const snapshot = body.change === true ? null : await snapshotFor(wineSlug, options.lookup ?? defaultWineLookup)
    const { data } = await callAccount<ServiceSavedItem>(config, 'PUT', `/v1/me/saved/${wineSlug}`, {
      session, body: { status: body.status, source: body.source, ...(snapshot ? { wine_snapshot: snapshot } : {}) },
    })
    return savedView(data)
  })
}

export function savedDeleteRoute(event: H3Event, source: AccountConfigSource, slug: unknown) {
  return accountJson(event, source, async config => {
    checkOrigin(event, config)
    const session = sessionOf(event)
    await callAccount(config, 'DELETE', `/v1/me/saved/${slugParam(slug)}`, { session })
    return { status: 'removed' }
  })
}
