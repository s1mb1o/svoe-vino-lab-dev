import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const origin = process.env.PORTAL_ORIGIN || 'http://127.0.0.1:8153'
const snapshot = JSON.parse(await readFile(new URL('../server/data/alternative-catalog.json', import.meta.url)))
const anchors = JSON.parse(await readFile(new URL('../tests/data/f04-anchors-v2.json', import.meta.url)))
const accepted = new Set(snapshot.wines.map(wine => wine.slug))
const cases = [
  ['kuban-vino-kaberne-de-tamane-kaberne-sovinon-krasnoe-suhoe-125', 'dry'],
  ['shato-pino-grand-reserve-cabernet-sauvignon-kaberne-sovinon-krasnoe-suhoe-135', 'dry'],
  ['shato-pino-pino-gridzhio-beloe-suhoe-12', 'dry'],
  ['appassimento', 'sweet'],
  ['abrau-dyurso-imperatorskoe-bryut-shardone-beloe-12', 'brut'],
]
const outcomes = []
async function alternatives(slug, filters = {}) {
  const response = await fetch(`${origin}/api/recommendations/alternatives?${new URLSearchParams({ slug, ...filters })}`)
  assert.equal(response.status, 200, slug)
  assert.equal(response.headers.get('cache-control'), 'no-store')
  const answer = await response.json()
  assert.equal(answer.version, snapshot.version)
  assert.equal(answer.base.slug, slug)
  assert(answer.results.length <= 5)
  const identities = new Set([answer.base.canonicalId])
  for (const { wine } of answer.results) {
    assert(accepted.has(wine.slug))
    assert(wine.producerId && wine.producerId !== answer.base.producerId)
    assert(!identities.has(wine.canonicalId)); identities.add(wine.canonicalId)
    assert.equal(wine.sweetness, filters.sweetness || answer.base.sweetness)
    assert.equal(wine.color, filters.color || answer.base.color)
    if (filters.sparkle) assert.equal(wine.sparkle, filters.sparkle)
    assert(wine.grapes.some(grape => answer.base.grapes.includes(grape)))
  }
  return answer
}
for (const [slug, sweetness] of cases) {
  const answer = await alternatives(slug)
  assert.equal(answer.base.sweetness, sweetness)
  assert(answer.results.length > 0, slug)
  outcomes.push({ slug, sweetness, results: answer.results.length })
}
let retired = 0, activeAnchors = 0
for (const anchor of anchors.anchors) {
  if (anchor.expectedStatus === 404) {
    assert.equal((await fetch(`${origin}/api/recommendations/alternatives?slug=${anchor.slug}`)).status, 404)
    retired++
  } else {
    const answer = await alternatives(anchor.slug)
    assert(answer.results.length > 0, anchor.slug)
    assert.equal(answer.base.sweetness, anchor.sweetness)
    activeAnchors++
  }
}
await alternatives(cases[0][0], { sweetness: 'semi_sweet' })
await alternatives(cases[0][0], { sparkle: 'still' })
for (const query of ['slug=../account', `slug=${cases[0][0]}&sweetness=unknown`, `slug=${cases[0][0]}&extra=1`, `slug=${cases[0][0]}&sweetness=dry&sweetness=sweet`]) {
  assert.equal((await fetch(`${origin}/api/recommendations/alternatives?${query}`)).status, 400)
}
assert.equal((await fetch(`${origin}/api/recommendations/alternatives?slug=missing-public-wine`)).status, 404)
console.log(JSON.stringify({ version: snapshot.version, outcomes, activeAnchors, retiredAnchors: retired, producerLeaks: 0, filterViolations: 0 }, null, 2))
