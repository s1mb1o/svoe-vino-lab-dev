import data from '../data/alternative-catalog.json'
import type { AlternativeWine } from '#shared/alternatives'

export const alternativeCatalog = data.wines as AlternativeWine[]
export const alternativeVersion = data.version
const bySlug = new Map(alternativeCatalog.map(wine => [wine.slug, wine]))
export const alternativeWine = (slug: string) => bySlug.get(slug) ?? null
