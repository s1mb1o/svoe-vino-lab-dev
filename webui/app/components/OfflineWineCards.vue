<script setup lang="ts">
import { alternativeStyleLine } from '#shared/alternatives'
import type { OfflineCard } from '#shared/offline-cards'
const offline = useOfflineCards()
const diary = useDiary()
const selected = ref<OfflineCard | null>(null)
const offlineMode = ref(false)
async function load() {
  offlineMode.value = !navigator.onLine
  try {
    if (offlineMode.value) await offline.refresh(true)
    else if (await offline.hasStoredCards()) {
      await diary.load(true)
      if (diary.state.value === 'in') await offline.refresh()
    }
  } catch { offline.error.value = 'Копии на устройстве временно недоступны.' }
}
async function remove(slug: string) {
  try { await offline.remove(slug); selected.value = null } catch { offline.error.value = 'Не удалось удалить копию. Повторите попытку.' }
}
watch(offline.cards, cards => { if (selected.value && !cards.some(card => card.slug === selected.value?.slug)) selected.value = null })
onMounted(() => { void load(); window.addEventListener('online', load); window.addEventListener('offline', load) })
onBeforeUnmount(() => { window.removeEventListener('online', load); window.removeEventListener('offline', load) })
</script>

<template>
  <section v-if="offline.cards.value.length || offline.error.value" class="f04-device-cards ym-hide-content" aria-label="Карточки на этом устройстве">
    <h2>Карточки на этом устройстве</h2><p>Последние 50 локальных копий публичных карточек. Удаление копии не меняет дневник. Дневник, заметки и новые изменения требуют сети.</p>
    <p v-if="offline.error.value" role="alert">{{ offline.error.value }}</p>
    <ul class="f04-local-list"><li v-for="card in offline.cards.value" :key="card.slug"><button class="button secondary" @click="selected = card">{{ card.wine.name }}</button><button class="text-button" :aria-label="`Удалить копию: ${card.wine.name}`" @click="remove(card.slug)">Удалить копию</button></li></ul>
    <article v-if="selected" class="f04-stored-card"><div class="f04-offline-image"><WineImage :alt="selected.wine.name" width="60" height="100" /></div><h3>{{ selected.wine.name }}</h3><p>{{ selected.wine.producer || 'Производитель: нет данных' }}</p><p>{{ alternativeStyleLine(selected.wine) || 'Характеристики: нет данных' }}</p><p>Сорта: {{ selected.wine.grapes.join(', ') || 'Нет данных' }}</p><p>Алкоголь: {{ selected.wine.alcohol || 'Нет данных' }}</p><p>Температура подачи: {{ selected.wine.servingTemperature || 'Нет данных' }}</p><p>Копия от {{ new Date(selected.savedAt).toLocaleString('ru', { timeZone: 'Europe/Moscow' }) }} (Москва).</p><details class="f04-version"><summary>Снимок данных</summary><code>{{ selected.version }}</code></details><a :href="selected.wine.source" target="_blank" rel="noopener noreferrer">Карточка источника · нужна сеть</a><p v-if="offlineMode" role="status">Нет сети. Изменения дневника недоступны.</p><button class="text-button" @click="selected = null">Закрыть карточку</button></article>
  </section>
</template>
