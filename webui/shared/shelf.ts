export const MAX_SHELF_BOTTLES = 100
export const SHELF_TIMEOUT_MS = 300000
export type BottleBox = [number, number, number, number]
export interface ShelfBottle { id: string; box: BottleBox; mask: string; crop: string }
export interface ShelfResult {
  image: { width: number; height: number; preview: string }
  bottles: ShelfBottle[]
  detectedCount: number
  truncated: boolean
}
export function imageDataUrl(value: unknown, mime: 'jpeg' | 'png', maxLength: number): value is string {
  const prefix = `data:image/${mime};base64,`
  if (typeof value !== 'string' || !value.startsWith(prefix) || value.length >= maxLength) return false
  const data = value.slice(prefix.length)
  return data.length > 0 && /^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(data)
}
export function validBox(value: unknown): value is BottleBox {
  return Array.isArray(value) && value.length === 4 && value.every(n => typeof n === 'number' && Number.isFinite(n) && n >= 0 && n <= 1) && value[2] > value[0] && value[3] > value[1]
}
export function validShelfResult(value: unknown): value is ShelfResult {
  const r = value as ShelfResult | null
  return Boolean(r && r.image && Number.isInteger(r.image.width) && r.image.width > 0 && r.image.width <= 1600 && Number.isInteger(r.image.height) && r.image.height > 0 && r.image.height <= 1600
    && imageDataUrl(r.image.preview, 'jpeg', 4 * 1024 * 1024)
    && Array.isArray(r.bottles) && r.bottles.length <= MAX_SHELF_BOTTLES && r.bottles.every(b => b && typeof b === 'object') && new Set(r.bottles.map(b => b.id)).size === r.bottles.length
    && Number.isInteger(r.detectedCount) && r.detectedCount >= r.bottles.length && typeof r.truncated === 'boolean'
    && r.bottles.every(b => b && typeof b.id === 'string' && /^b[1-9]\d{0,2}$/.test(b.id) && validBox(b.box)
      && imageDataUrl(b.mask, 'png', 1024 * 1024)
      && imageDataUrl(b.crop, 'jpeg', 1024 * 1024)))
}
