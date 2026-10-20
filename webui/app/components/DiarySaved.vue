<script setup lang="ts">
// «Сохранённые» of «Винный дневник» (plan 07): wines that the person pinned, with one of four
// marks. The list does not depend on the history: a wine stays here after its history is removed.
import { accountErrorMessage } from '#shared/account'
import { sourceWineUrl, wineImageUrl } from '#shared/catalog'
import {
  COLOR_LABELS, SAVED_NOTE_MAX, SAVED_SOURCE_LABELS, SAVED_STATUSES, SAVED_STATUS_LABELS, SUGAR_LABELS, colorKey, isSavedSource,
  matchesFilter, normalizeNote, sugarKey, wineStyleLine,
  type ColorKey, type DiaryFilter, type SavedItem, type SavedStatus, type SugarKey,
} from '#shared/diary'
import { AccountRequestError, useAccountApi } from '~/composables/useAccountApi'
import { useDiary } from '~/composables/useDiary'
import { diaryDate } from '~/utils/diary-format'

const api = useAccountApi()
const diary = useDiary()
const items = ref<SavedItem[]>([])
const state = ref<'loading' | 'ready' | 'error'>('loading')
const error = ref('')
const notice = ref('')
const busy = ref('')
const status = ref<SavedStatus | ''>('')
const filter = ref<DiaryFilter>({ text: '', color: '', sugar: '' })
// Notes (owner request, 2026-10-20): the right half of a card. A note saves 1 s after the last key
// and when the field loses focus. Private text: the field is hidden from Metrika.
const notes = ref<Record<string, string>>({})
const noteState = ref<Record<string, 'saving' | 'saved' | 'error' | 'long' | ''>>({})
const noteTimers = new Map<string, ReturnType<typeof setTimeout>>()
const NOTE_STATE_TEXT = { saving: 'Сохраняем…', saved: 'Заметка сохранена', error: 'Не удалось сохранить заметку', long: `Не больше ${SAVED_NOTE_MAX} символов`, '': '' } as const

const counts = computed(() => Object.fromEntries(SAVED_STATUSES.map(key => [key, items.value.filter(item => item.status === key).length])) as Record<SavedStatus, number>)
const colors = computed(() => (Object.keys(COLOR_LABELS) as ColorKey[]).filter(key => items.value.some(item => colorKey(item.wine?.color) === key)))
const sugars = computed(() => (Object.keys(SUGAR_LABELS) as SugarKey[]).filter(key => items.value.some(item => sugarKey(item.wine?.sugar) === key)))
const shown = computed(() => items.value.filter(item => (!status.value || item.status === status.value) && matchesFilter(item.slug, item.wine, filter.value, notes.value[item.slug] ?? '')))
const sourceLabel = (key: string) => isSavedSource(key) ? SAVED_SOURCE_LABELS[key] : ''
const wineName = (item: SavedItem) => item.wine?.name || item.slug

function errorText(failure: unknown) {
  return accountErrorMessage(failure instanceof AccountRequestError ? failure.body : undefined)
}

async function load() {
  state.value = 'loading'
  error.value = ''
  try {
    items.value = (await api.saved()).items
    notes.value = Object.fromEntries(items.value.map(item => [item.slug, item.note ?? '']))
    for (const item of items.value) diary.setSaved(item.slug, item.status)
    state.value = 'ready'
  } catch (failure) {
    error.value = errorText(failure)
    state.value = 'error'
  }
}

async function change(item: SavedItem, next: SavedStatus) {
  if (next === item.status) return
  busy.value = item.slug
  notice.value = ''
  const previous = item.status
  item.status = next
  try {
    const saved = await diary.save(item.slug, isSavedSource(item.source) ? item.source : 'history', next)
    Object.assign(item, saved)
  } catch (failure) {
    item.status = previous
    notice.value = errorText(failure)
  } finally {
    busy.value = ''
  }
}

async function remove(item: SavedItem) {
  // A pending note save would add the wine again.
  clearTimeout(noteTimers.get(item.slug))
  noteTimers.delete(item.slug)
  busy.value = item.slug
  notice.value = ''
  try {
    await diary.unsave(item.slug)
    items.value = items.value.filter(entry => entry.slug !== item.slug)
    notice.value = `«${wineName(item)}» убрано из сохранённых.`
  } catch (failure) {
    notice.value = errorText(failure)
  } finally {
    busy.value = ''
  }
}

function editNote(item: SavedItem, value: string) {
  notes.value = { ...notes.value, [item.slug]: value }
  noteState.value = { ...noteState.value, [item.slug]: '' }
  clearTimeout(noteTimers.get(item.slug))
  noteTimers.set(item.slug, setTimeout(() => { void saveNote(item) }, 1000))
}

async function saveNote(item: SavedItem) {
  clearTimeout(noteTimers.get(item.slug))
  noteTimers.delete(item.slug)
  const text = normalizeNote(notes.value[item.slug] ?? '')
  if (text === (item.note ?? '')) return
  if (text.length > SAVED_NOTE_MAX) {
    noteState.value = { ...noteState.value, [item.slug]: 'long' }
    return
  }
  noteState.value = { ...noteState.value, [item.slug]: 'saving' }
  try {
    const saved = await api.putSaved(item.slug, item.status, isSavedSource(item.source) ? item.source : 'history', true, text)
    item.note = saved.note
    noteState.value = { ...noteState.value, [item.slug]: 'saved' }
  } catch {
    noteState.value = { ...noteState.value, [item.slug]: 'error' }
  }
}

onMounted(load)
// A note typed just before the tab changes is still saved.
onBeforeUnmount(() => {
  for (const slug of [...noteTimers.keys()]) {
    const item = items.value.find(entry => entry.slug === slug)
    if (item) void saveNote(item)
  }
})
defineExpose({ reload: load })
</script>

<template>
  <div class="diary-list-panel">
    <p v-if="state === 'loading'" class="account-lead account-loading"><span class="spinner" aria-hidden="true" />Загружаем сохранённые вина…</p>
    <div v-else-if="state === 'error'" class="account-panel" role="alert">
      <p>{{ error }}</p>
      <div class="account-actions"><button class="button secondary" type="button" @click="load">Повторить</button></div>
    </div>
    <div v-else-if="!items.length" class="diary-empty">
      <p>Здесь будут вина, которые вы сохраните. Нажмите на значок <AppIcon name="pin" class="diary-inline-icon" /> в карточке вина: после поиска по фото, на карте линейки, в «Вино к блюду» или в истории.</p>
      <NuxtLink class="button primary" to="/">Найти вино по фото</NuxtLink>
    </div>
    <template v-else>
      <div class="diary-status-filter" role="group" aria-label="Отметка">
        <button type="button" class="diary-chip" :aria-pressed="status === ''" @click="status = ''">Все <span>{{ items.length }}</span></button>
        <button v-for="key in SAVED_STATUSES" :key="key" type="button" class="diary-chip" :aria-pressed="status === key" @click="status = key">{{ SAVED_STATUS_LABELS[key] }} <span>{{ counts[key] }}</span></button>
      </div>
      <DiaryFilters v-model="filter" :colors="colors" :sugars="sugars" label="Фильтр сохранённых вин" />
      <p class="diary-count" role="status">{{ shown.length === items.length ? `Сохранено вин: ${items.length}` : `Показано ${shown.length} из ${items.length}` }}</p>
      <p v-if="notice" class="account-notice" role="status">{{ notice }}</p>
      <ul v-if="shown.length" class="diary-list">
        <li v-for="item in shown" :key="item.slug" class="diary-row diary-row-saved">
          <div class="diary-row-image"><WineImage :src="wineImageUrl(item.slug, 400)" alt="" width="64" height="128" loading="lazy" /></div>
          <div class="diary-row-body">
            <h3 class="diary-row-title">{{ wineName(item) }}</h3>
            <p v-if="item.wine?.producer" class="diary-row-producer">{{ item.wine.producer }}</p>
            <p v-if="wineStyleLine(item.wine)" class="diary-row-style">{{ wineStyleLine(item.wine) }}</p>
            <p class="diary-row-meta">Сохранено {{ diaryDate(item.addedAt) }}<template v-if="sourceLabel(item.source)"> · {{ sourceLabel(item.source) }}</template></p>
            <div class="diary-row-status">
              <label :for="`saved-status-${item.slug}`" class="sr-only">Отметка для «{{ wineName(item) }}»</label>
              <select :id="`saved-status-${item.slug}`" class="account-select" :value="item.status" :disabled="busy === item.slug" @change="change(item, ($event.target as HTMLSelectElement).value as SavedStatus)">
                <option v-for="key in SAVED_STATUSES" :key="key" :value="key">{{ SAVED_STATUS_LABELS[key] }}</option>
              </select>
            </div>
            <div class="diary-row-actions">
              <a class="account-link ym-disable-tracklink" :href="sourceWineUrl(item.slug)" target="_blank" rel="noopener noreferrer">На «Свое Вино»</a>
              <button type="button" class="account-link account-danger" :disabled="busy === item.slug" @click="remove(item)">Убрать из сохранённых</button>
            </div>
          </div>
          <div class="diary-row-note">
            <label :for="`saved-note-${item.slug}`">Заметка</label>
            <textarea
              :id="`saved-note-${item.slug}`"
              class="ym-disable-keys ym-hide-content"
              rows="5"
              :maxlength="SAVED_NOTE_MAX"
              :value="notes[item.slug]"
              placeholder="Вкус, повод, с чем пили, где купили…"
              :aria-describedby="`saved-note-state-${item.slug}`"
              @input="editNote(item, ($event.target as HTMLTextAreaElement).value)"
              @blur="saveNote(item)"
            />
            <p :id="`saved-note-state-${item.slug}`" class="diary-note-state" :class="{ 'is-error': noteState[item.slug] === 'error' || noteState[item.slug] === 'long' }" aria-live="polite">{{ NOTE_STATE_TEXT[noteState[item.slug] ?? ''] }}</p>
          </div>
        </li>
      </ul>
      <p v-else class="account-hint">Ничего не найдено. Измените фильтр.</p>
    </template>
  </div>
</template>
