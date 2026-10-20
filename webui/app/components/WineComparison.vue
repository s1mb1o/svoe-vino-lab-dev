<script setup lang="ts">
import { compareWineFacts, type ComparisonPair } from '#shared/alternatives'
const comparison = useWineComparison()
const { pair, savedBase, active } = comparison
const dialog = ref<HTMLDialogElement>()
const heading = ref<HTMLElement>()
const resumed = ref<ComparisonPair | null>(null)
const resumedSaved = ref<string | null>(null)
const titleId = useId()
const rows = computed(() => pair.value ? compareWineFacts(pair.value.base, pair.value.candidate) : [])
watch(active, async value => {
  await nextTick()
  if (value && dialog.value && !dialog.value.open) dialog.value.showModal()
  else if (!value) dialog.value?.close()
})
watch(savedBase, async (value, previous) => {
  if (!value && previous && pair.value) {
    await nextTick()
    if (dialog.value) dialog.value.scrollTop = 0
    heading.value?.focus({ preventScroll: true })
  }
})
onMounted(() => { resumed.value = comparison.takeReturn(); resumedSaved.value = comparison.takeSavedReturn(); window.addEventListener('popstate', comparison.close) })
onBeforeUnmount(() => { window.removeEventListener('popstate', comparison.close); dialog.value?.close(); comparison.close() })
function resume(event: Event) {
  if (resumed.value) comparison.open(resumed.value, event.currentTarget as HTMLElement)
  else if (resumedSaved.value) comparison.openSaved(resumedSaved.value, event.currentTarget as HTMLElement)
}
</script>

<template>
  <div v-if="resumed || resumedSaved" class="f04-resume"><p>Сравнение сохранено на время входа. Фото не сохранялось.</p><button class="button secondary" @click="resume">Продолжить сравнение</button></div>
  <dialog ref="dialog" class="f04-dialog" :aria-labelledby="titleId" @cancel.prevent="comparison.close()" @close="comparison.close()" @click="event => { if (event.target === dialog) comparison.close() }">
    <header v-if="active" class="f04-dialog-head"><h2 :id="titleId" ref="heading" tabindex="-1">{{ savedBase ? 'Второе вино из сохранённых' : 'Сравнение двух вин' }}</h2><button class="icon-button" aria-label="Закрыть сравнение" @click="comparison.close()"><AppIcon name="close" /></button></header>
    <SavedWinePicker v-if="savedBase" :key="savedBase" :slug="savedBase" />
    <template v-else-if="pair">
      <p>Факты снимка каталога. Сходство характеристик не означает одинаковый вкус или качество.</p>
      <div class="f04-compare-cards"><article v-for="(item, index) in [pair.base, pair.candidate]" :key="item.slug"><h3>{{ item.name }}</h3><PinButton :slug="item.slug" source="photo" :wine-name="item.name" :offline-card="{ wine: item, version: pair.version }" :return-pair="pair" /><a :href="item.source" target="_blank" rel="noopener noreferrer">Карточка источника · нужна сеть</a><button v-if="index === 1" class="button secondary f04-change-saved" @click="comparison.openSaved(pair.base.slug)">Выбрать из сохранённых</button></article></div>
      <dl class="f04-facts"><div v-for="row in rows" :key="row.key" :class="row.kind"><dt>{{ row.label }} <small>{{ row.kind === 'shared' ? 'Общее' : row.kind === 'different' ? 'Различие' : 'Неизвестно' }}</small></dt><dd>{{ row.left }}</dd><dd>{{ row.right }}</dd></div></dl>
      <p>Год, дуб, цена и наличие: нет подтверждённых данных для этого сравнения. Названия и точные варианты сохранены.</p>
      <details class="f04-version"><summary>Снимок данных</summary><p v-for="item in [pair.base, pair.candidate]" :key="item.slug">{{ item.name }}: <code>{{ item.slug }}</code></p><code>{{ pair.version }}</code></details>
    </template>
  </dialog>
</template>
