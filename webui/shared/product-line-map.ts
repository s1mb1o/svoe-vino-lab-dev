import productLineIndex from './data/product-line-index.json'
import { PRODUCT_LINE_LOADERS } from './data/product-line-maps'
import { sourceWineUrl } from './catalog'
import { resolveProductLineIndex } from './product-line-core'
import type { LineProduct, ProductLineIndex, ProductLineIndexResolution, ProductLineMapData, ProductLineWineRef } from './product-line-core'

export * from './product-line-core'

// Pages import only this index. A full map loads on demand through loadProductLine.
// The tests and the build validate the maps and check that this index matches them.
// The JSON type that TypeScript infers lists each slug key. The index test checks the real shape.
export const PRODUCT_LINE_INDEX = productLineIndex as unknown as ProductLineIndex

export function resolveProductLine(wine?: ProductLineWineRef): ProductLineIndexResolution {
  return resolveProductLineIndex(PRODUCT_LINE_INDEX, wine)
}

const loading = new Map<string, Promise<ProductLineMapData | undefined>>()

export function loadProductLine(producerId: string): Promise<ProductLineMapData | undefined> {
  const load = Object.hasOwn(PRODUCT_LINE_LOADERS, producerId) ? PRODUCT_LINE_LOADERS[producerId] : undefined
  if (!load) return Promise.resolve(undefined)
  let pending = loading.get(producerId)
  if (!pending) {
    pending = load().then(module => module.default as ProductLineMapData)
    // A failed chunk request must not stay cached. The next attempt loads it again.
    pending.catch(() => loading.delete(producerId))
    loading.set(producerId, pending)
  }
  return pending
}

export function productPortalUrl(product: LineProduct): string | null {
  return product.wine_slug ? sourceWineUrl(product.wine_slug) : null
}
