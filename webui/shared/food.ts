export interface Location { latitude: number; longitude: number }
export interface FoodStore {
  id: number
  name: string
  address: string
  location: Location
  schedule: string
}
export interface FoodProduct {
  id: string
  name: string
  image: string | null
  url: string
  priceLabel: string
  conditions: string[]
  food: string
  reason: string
}
export type FoodSelection = { location: Location; storeId?: never } | { storeId: number; location?: never }
export interface FoodResult {
  provider: 'globus'
  store: FoodStore
  distanceKm: number | null
  checkedAt: string
  products: FoodProduct[]
  complete: boolean
}

export function validLocation(value: unknown): value is Location {
  if (!value || typeof value !== 'object') return false
  const p = value as Location
  return typeof p.latitude === 'number' && Number.isFinite(p.latitude) && Math.abs(p.latitude) <= 90
    && typeof p.longitude === 'number' && Number.isFinite(p.longitude) && Math.abs(p.longitude) <= 180
}

export function distanceKm(a: Location, b: Location): number {
  const rad = Math.PI / 180
  const value = Math.sin((b.latitude - a.latitude) * rad / 2) ** 2
    + Math.cos(a.latitude * rad) * Math.cos(b.latitude * rad) * Math.sin((b.longitude - a.longitude) * rad / 2) ** 2
  return 6371 * 2 * Math.asin(Math.sqrt(Math.min(1, Math.max(0, value))))
}
