// Test-only access to every producer map. Pages load maps on demand through loadProductLine.
import { readFileSync, readdirSync } from 'node:fs'
import { findProducerLineIn, resolveProductLineIn } from '../../shared/product-line-core'
import type { ProductLineMapData, ProductLineWineRef } from '../../shared/product-line-core'

export const PRODUCT_LINE_DIRECTORY = new URL('../../shared/data/product-line-maps/', import.meta.url)
export const PRODUCT_LINE_FILES = readdirSync(PRODUCT_LINE_DIRECTORY).filter(name => name.endsWith('.json')).sort()

export const PRODUCT_LINE_MAPS: ProductLineMapData[] = PRODUCT_LINE_FILES
  .map(name => JSON.parse(readFileSync(new URL(name, PRODUCT_LINE_DIRECTORY), 'utf8')) as ProductLineMapData)
  .sort((a, b) => a.producer.name.localeCompare(b.producer.name, 'ru'))
export const ABRAU_PRODUCT_LINE = PRODUCT_LINE_MAPS.find(line => line.producer.id === 'abrau-durso')!

export const resolveProductLine = (wine?: ProductLineWineRef) => resolveProductLineIn(PRODUCT_LINE_MAPS, wine)
export const findProducerLine = (wine: ProductLineWineRef) => findProducerLineIn(PRODUCT_LINE_MAPS, wine)
