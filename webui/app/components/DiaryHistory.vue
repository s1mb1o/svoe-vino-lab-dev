<script setup lang="ts">
// «История» of «Винный дневник» (plan 07): every wine that the person found on the site and in the
// linked chats. The page loads the whole list once and filters it in the browser.
import { accountErrorMessage } from '#shared/account'
import { sourceWineUrl, wineImageUrl } from '#shared/catalog'
import {
  COLOR_LABELS, HISTORY_SOURCE_LABELS, SUGAR_LABELS, colorKey, isHistorySource, matchesFilter, sugarKey, wineStyleLine,
  type ColorKey, type DiaryFilter, type HistoryItem, type SugarKey,
} from '#shared/diary'
import { AccountRequestError, useAccountApi } from '~/composables/useAccountApi'
import { useDiary } from '~/composables/useDiary'
import { diaryDate, diaryDay } from '~/utils/diary-format'

const emit = defineEmits<{ settings: [] }>()
const api = useAccountApi()
const diary = useDiary()
const items = ref<HistoryItem[]>([])
const saveHistory = ref(true)
const state = ref<'loading' | 'ready' | 'error'>('loading')
const error = ref('')
const notice = ref('')
const busy = ref(false)
const confirmClear = ref(false)
const openDays = ref<Record<string, HistoryItem['days'] | 'loading' | 'error'>>({})
const filter = ref<DiaryFilter>({ text: '', color: '', sugar: '' })
const source = ref('')

const colors = computed(() => (Object.keys(COLOR_LABELS) as ColorKey[]).filter(key => items.value.some(item => colorKey(item.wine?.color) === key)))
const sugars = computed(() => (Object.keys(SUGAR_LABELS) as SugarKey[]).filter(key => items.value.some(item => sugarKey(item.wine?.sugar) === key)))
const sources = computed(() => Object.keys(HISTORY_SOURCE_LABELS).filter(key => items.value.some(item => item.sources.includes(key))))
const shown = computed(() => items.value.filter(item => matchesFilter(item.slug, item.wine, filter.value) && (!source.value || item.sources.includes(source.value))))
const filtered = computed(() => shown.value.length !== items.value.length)

const sourceLabel = (key: string) => isHistorySource(key) ? HISTORY_SOURCE_LABELS[key] : key
const wineName = (item: HistoryItem) => item.wine?.name || item.slug

async function load() {
  state.value = 'loading'
  error.value = ''
  try {
    const answer = await api.history()
    items.value = answer.items
    saveHistory.value = answer.saveHistory
    state.value = 'ready'
  } catch (failure) {
    error.value = accountErrorMessage(failure instanceof AccountRequestError ? failure.body : undefined)
    state.value = 'error'
  }
}

async function toggleDays(item: HistoryItem) {
  if (openDays.value[item.slug]) {
    const next = { ...openDays.value }
    delete next[item.slug]
    openDays.value = next
    return
  }
  openDays.value = { ...openDays.value, [item.slug]: 'loading' }
  try {
    const detail = await api.historyItem(item.slug)
    openDays.value = { ...openDays.value, [item.slug]: detail.days ?? [] }
  } catch {
    openDays.value = { ...openDays.value, [item.slug]: 'error' }
  }
}

async function remove(item: HistoryItem) {
  busy.value = true
  notice.value = ''
  try {
    await api.deleteHistoryWine(item.slug)
    items.value = items.value.filter(entry => entry.slug !== item.slug)
    notice.value = `«${wineName(item)}» удалено из истории.${item.savedStatus ? ' В сохранённых оно осталось.' : ''}`
  } catch (failure) {
    if (failure instanceof AccountRequestError && failure.status === 404) items.value = items.value.filter(entry => entry.slug !== item.slug)
    else notice.value = accountErrorMessage(failure instanceof AccountRequestError ? failure.body : undefined)
  } finally {
    busy.value = false
  }
}

async function clearAll() {
  busy.value = true
  notice.value = ''
  try {
    await api.clearHistory()
    items.value = []
    confirmClear.value = false
    notice.value = 'История очищена. Сохранённые вина остались.'
  } catch (failure) {
    notice.value = accountErrorMessage(failure instanceof AccountRequestError ? failure.body : undefined)
  } finally {
    busy.value = false
  }
}

// The pins of the rows share the state of the site pins; keep the saved marks of the rows equal.
watch(diary.saved, saved => {
  for (const item of items.value) item.savedStatus = saved[item.slug] ?? null
}, { deep: true })

onMounted(load)
defineExpose({ reload: load })
</script>

<template>
  <div class="diary-list-panel">
    <p v-if="state === 'loading'" class="account-lead account-loading"><span class="spinner" aria-hidden="true" />Загружаем историю…</p>
    <div v-else-if="state === 'error'" class="account-panel" role="alert">
      <p>{{ error }}</p>
      <div class="account-actions"><button class="button secondary" type="button" @click="load">Повторить</button></div>
    </div>
    <template v-else>
      <p v-if="!saveHistory" class="account-notice">Запись находок выключена. <button type="button" class="account-link" @click="emit('settings')">Включить в настройках</button></p>
      <div v-if="!items.length" class="diary-empty">
        <p>История пуста. Найдите вино по фото на сайте, в Telegram или MAX — оно появится здесь.</p>
        <NuxtLink class="button primary" to="/">Найти вино по фото</NuxtLink>
      </div>
      <template v-else>
        <DiaryFilters v-model="filter" :colors="colors" :sugars="sugars" label="Фильтр истории">
          <div v-if="sources.length > 1" class="diary-filter">
            <label for="diary-history-source">Где нашли</label>
            <select id="diary-history-source" v-model="source" class="account-select">
              <option value="">Везде</option>
              <option v-for="key in sources" :key="key" :value="key">{{ sourceLabel(key) }}</option>
            </select>
          </div>
        </DiaryFilters>
        <p class="diary-count" role="status">{{ filtered ? `Показано ${shown.length} из ${items.length}` : `Вин в истории: ${items.length}` }}</p>
        <p v-if="notice" class="account-notice" role="status">{{ notice }}</p>
        <ul v-if="shown.length" class="diary-list">
          <li v-for="item in shown" :key="item.slug" class="diary-row">
            <div class="diary-row-image"><WineImage :src="wineImageUrl(item.slug, 400)" alt="" width="72" height="96" loading="lazy" /></div>
            <div class="diary-row-body">
              <h3 class="diary-row-title">{{ wineName(item) }}</h3>
              <p v-if="item.wine?.producer" class="diary-row-producer">{{ item.wine.producer }}</p>
              <p v-if="wineStyleLine(item.wine)" class="diary-row-style">{{ wineStyleLine(item.wine) }}</p>
              <p class="diary-row-meta">Встреч: {{ item.daysCount }} · последний раз {{ diaryDate(item.lastMetAt) }}<template v-if="item.daysCount > 1"> · впервые {{ diaryDate(item.firstMetAt) }}</template></p>
              <p class="diary-row-tags"><span v-for="key in item.sources" :key="key" class="diary-tag">{{ sourceLabel(key) }}</span><span v-if="item.savedStatus" class="diary-tag diary-tag-saved">Сохранено</span></p>
              <div class="diary-row-actions">
                <button type="button" class="account-link" :aria-expanded="Boolean(openDays[item.slug])" @click="toggleDays(item)">{{ openDays[item.slug] ? 'Скрыть даты' : 'Даты' }}</button>
                <a class="account-link ym-disable-tracklink" :href="sourceWineUrl(item.slug)" target="_blank" rel="noopener noreferrer">На «Свое Вино»</a>
                <button type="button" class="account-link account-danger" :disabled="busy" @click="remove(item)">Удалить из истории</button>
              </div>
              <template v-if="openDays[item.slug]">
                <p v-if="openDays[item.slug] === 'loading'" class="account-hint">Загружаем даты…</p>
                <p v-else-if="openDays[item.slug] === 'error'" class="account-hint">Даты не загрузились. Попробуйте ещё раз.</p>
                <ul v-else class="diary-days">
                  <li v-for="day in (openDays[item.slug] as NonNullable<HistoryItem['days']>)" :key="day.metOn">{{ diaryDay(day.metOn) }} · {{ sourceLabel(day.source) }}</li>
                </ul>
              </template>
            </div>
            <div class="diary-row-pin"><PinButton :slug="item.slug" source="history" :wine-name="wineName(item)" /></div>
          </li>
        </ul>
        <p v-else class="account-hint">Ничего не найдено. Измените фильтр.</p>
        <div v-if="!confirmClear" class="account-actions">
          <button class="button secondary account-danger" type="button" :disabled="busy" @click="confirmClear = true">Очистить историю</button>
        </div>
        <div v-else class="account-confirm" role="group" aria-labelledby="diary-clear-heading">
          <h3 id="diary-clear-heading" class="account-subheading">Очистить всю историю?</h3>
          <p>Удалятся все найденные вина и даты: {{ items.length }}. Сохранённые вина останутся. Это действие нельзя отменить.</p>
          <div class="account-actions">
            <button class="button primary account-danger-fill" type="button" :disabled="busy" @click="clearAll">Очистить</button>
            <button class="button secondary" type="button" :disabled="busy" @click="confirmClear = false">Отмена</button>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>
