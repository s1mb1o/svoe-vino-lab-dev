import abrauData from './data/product-line-maps/abrau-durso.json'
import registeredProducerMaps from './data/product-line-maps'
import type { Wine } from './catalog'
import { sourceWineUrl } from './catalog'
import { findProducerLineIn, resolveProductLineIn, validateProductLineMaps } from './product-line-core'
import type { LineProduct, ProductLineMapData, ProductLineResolution } from './product-line-core'

export * from './product-line-core'

export const ABRAU_PRODUCT_LINE = abrauData as ProductLineMapData
export const PRODUCT_LINE_MAPS: ProductLineMapData[] = ([...registeredProducerMaps] as ProductLineMapData[])
  .sort((a, b) => a.producer.name.localeCompare(b.producer.name, 'ru'))

export function findProducerLine(wine: Pick<Wine, 'producer' | 'slug'>): ProductLineMapData | undefined {
  return findProducerLineIn(PRODUCT_LINE_MAPS, wine)
}

export function resolveProductLine(wine?: Pick<Wine, 'producer' | 'slug'>): ProductLineResolution {
  return resolveProductLineIn(PRODUCT_LINE_MAPS, wine)
}

export function productPortalUrl(product: LineProduct): string | null {
  return product.wine_slug ? sourceWineUrl(product.wine_slug) : null
}

const mapErrors = validateProductLineMaps(PRODUCT_LINE_MAPS)
if (mapErrors.length) throw new Error(`Invalid product-line maps: ${mapErrors.join('; ')}`)
