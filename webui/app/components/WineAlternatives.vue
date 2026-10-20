<script setup lang="ts">
import { ALTERNATIVE_COLORS, ALTERNATIVE_SUGAR, type AlternativeAnswer } from '#shared/alternatives'
const props = defineProps<{ slug: string }>()
const answer = shallowRef<AlternativeAnswer | null>(null)
const opened = ref(false)
const busy = ref(false)
const error = ref('')
const color = ref(''), sweetness = ref(''), sparkle = ref('')
const comparison = useWineComparison()
const offline = useOfflineCards()
let controller: AbortController | undefined
let generation = 0
async function load() {
  const gen = ++generation
  controller?.abort()
  controller = new AbortController()
  const abort = controller
  const timer = setTimeout(() => abort.abort(), 8000)
  opened.value = true; busy.value = true; error.value = ''; answer.value = null
  const query = new URLSearchParams({ slug: props.slug })
  if (color.value) query.set('color', color.value)
  if (sweetness.value) query.set('sweetness', sweetness.value)
  if (sparkle.value) query.set('sparkle', sparkle.value)
  try {
    const response = await fetch(`/api/recommendations/alternatives?${query}`, { signal: abort.signal, cache: 'no-store' })
    if (!response.ok) throw new Error(response.status === 404 ? 'outside_snapshot' : 'unavailable')
    const data = await response.json() as AlternativeAnswer
    if (gen === generation) answer.value = data
  } catch (reason) {
    if (gen === generation) error.value = reason instanceof Error && reason.message === 'outside_snapshot'
      ? 'Этого точного вина нет в проверенном снимке каталога. Подбор альтернатив для него пока недоступен.'
      : 'Подбор временно недоступен. Исходное вино сохранено на экране. Попробуйте ещё раз.'
  } finally { clearTimeout(timer); if (gen === generation) busy.value = false }
}
watch(() => props.slug, () => { generation++; controller?.abort(); answer.value = null; opened.value = false; busy.value = false })
onBeforeUnmount(() => { generation++; controller?.abort() })
</script>

<template>
  <section class="f04-alternatives" aria-label="Вина другого производителя" :aria-busy="busy">
    <div class="f04-section-head"><div><h2>Вина другого производителя</h2><p>Общие сорта и известные характеристики. Без обещания одинакового вкуса.</p></div><button class="button secondary" :disabled="busy" @click="load">{{ busy ? 'Подбираем…' : opened ? 'Повторить подбор' : 'Найти альтернативы' }}</button></div>
    <template v-if="opened">
      <div class="f04-filters"><label>Цвет<select v-model="color" @change="load"><option value="">Как у исходного вина</option><option v-for="item in ALTERNATIVE_COLORS" :key="item" :value="item">{{ item }}</option></select></label><label>Сладость<select v-model="sweetness" @change="load"><option value="">Как у исходного вина</option><option v-for="(label, key) in ALTERNATIVE_SUGAR" :key="key" :value="key">{{ label }}</option></select></label><label>Тип<select v-model="sparkle" @change="load"><option value="">Любой известный или неуказанный</option><option value="still">Только подтверждённое тихое</option><option value="sparkling">Только подтверждённое игристое</option></select></label></div>
      <p v-if="error" role="alert">{{ error }}</p>
      <p v-if="answer?.explanation" role="status">{{ answer.explanation }}</p>
      <ol v-if="answer?.results.length" class="f04-results"><li v-for="result in answer.results" :key="result.wine.slug"><WineImage :src="result.wine.image" :alt="result.wine.name" width="80" height="130" loading="lazy" /><div><h3>{{ result.wine.name }}</h3><ul><li v-for="reason in result.reasons" :key="reason">{{ reason }}</li></ul><p v-for="missing in result.missing" :key="missing">{{ missing }}</p><div class="f04-actions"><button class="button secondary" @click="comparison.open({ base: answer!.base, candidate: result.wine, version: answer!.version }, $event.currentTarget as HTMLElement)">Сравнить</button><PinButton :slug="result.wine.slug" source="photo" :wine-name="result.wine.name" :offline-card="{ wine: result.wine, version: answer.version }" :return-pair="{ base: answer.base, candidate: result.wine, version: answer.version }" /><a :href="result.wine.source" target="_blank" rel="noopener noreferrer">Карточка источника</a></div><p v-if="offline.cards.value.some(card => card.slug === result.wine.slug)" class="f04-offline-ready" role="status">Доступно офлайн на этом устройстве</p></div></li></ol>
      <details v-if="answer" class="f04-version"><summary>Источник данных</summary><p>Снимок каталога. Цены и наличие не проверяются.</p><code>{{ answer.version }}</code></details>
    </template>
  </section>
</template>
