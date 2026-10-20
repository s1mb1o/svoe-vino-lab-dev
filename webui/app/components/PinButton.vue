<script setup lang="ts">
// The pin of a wine card: saves the wine in «Сохранённые» of «Винный дневник» (plan 07).
// A click on an unsaved wine saves it with «Не пробовано» and opens the status panel. A click on a
// saved wine opens the panel; it never removes the wine. A logged-out person gets a login offer.
import { SAVED_STATUSES, SAVED_STATUS_LABELS, type SavedSource, type SavedStatus } from '#shared/diary'
import { accountErrorMessage } from '#shared/account'
import { AccountRequestError } from '~/composables/useAccountApi'
import { useDiary } from '~/composables/useDiary'

const props = defineProps<{ slug: string; source: SavedSource; wineName?: string }>()
const diary = useDiary()
const route = useRoute()
const open = ref(false)
const busy = ref(false)
const error = ref('')
const root = ref<HTMLElement>()
const button = ref<HTMLButtonElement>()
const panel = ref<HTMLElement>()
const panelId = useId()
// A failed status change re-renders the radio buttons, so the checked one shows the saved status.
const radioKey = ref(0)
const status = computed<SavedStatus | null>(() => diary.saved.value[props.slug] ?? null)
const visible = computed(() => diary.state.value === 'in' || diary.state.value === 'out')
const name = computed(() => props.wineName ? `«${props.wineName}»` : 'вино')
const label = computed(() => status.value ? `Сохранено: ${SAVED_STATUS_LABELS[status.value]}. Изменить` : `Сохранить ${name.value}`)
const loginHref = computed(() => `/account?next=${encodeURIComponent(route.fullPath)}`)

onMounted(() => { diary.load() })
onBeforeUnmount(() => document.removeEventListener('pointerdown', outside, true))

function failure(reason: unknown) {
  const body = reason instanceof AccountRequestError ? reason.body : { error: 'account_unavailable' }
  if (body.error === 'saved_full') return 'В сохранённых уже 500 вин. Уберите лишние на странице дневника.'
  if (body.error === 'session_required' || body.error === 'session_invalid') return accountErrorMessage(body)
  return 'Не удалось сохранить. Попробуйте ещё раз.'
}

async function show() {
  open.value = true
  document.addEventListener('pointerdown', outside, true)
  await nextTick()
  const target = panel.value?.querySelector<HTMLElement>('input:checked, a, button') ?? panel.value
  target?.focus()
}

function close(returnFocus = true) {
  open.value = false
  error.value = ''
  document.removeEventListener('pointerdown', outside, true)
  if (returnFocus) button.value?.focus()
}

function outside(event: Event) {
  if (root.value && !root.value.contains(event.target as Node)) close(false)
}

async function toggle() {
  if (busy.value) return
  if (open.value) return close()
  if (diary.state.value === 'in' && !status.value && !busy.value) {
    busy.value = true
    error.value = ''
    try {
      await diary.save(props.slug, props.source)
    } catch (reason) {
      error.value = failure(reason)
    } finally {
      busy.value = false
    }
  }
  await show()
}

async function choose(next: SavedStatus) {
  if (next === status.value) return
  if (busy.value) {
    radioKey.value++
    return
  }
  busy.value = true
  error.value = ''
  try {
    await diary.save(props.slug, props.source, next)
  } catch (reason) {
    error.value = failure(reason)
    radioKey.value++
  } finally {
    busy.value = false
  }
}

async function remove() {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    await diary.unsave(props.slug)
    close()
  } catch (reason) {
    error.value = failure(reason)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div v-if="visible" ref="root" class="pin" @keydown.esc.stop.prevent="close()">
    <button
      ref="button"
      type="button"
      class="pin-button"
      :class="{ 'is-saved': status }"
      :aria-label="label"
      :title="status ? `Сохранено: ${SAVED_STATUS_LABELS[status]}` : 'Сохранить в дневник'"
      aria-haspopup="dialog"
      :aria-expanded="open"
      :aria-controls="open ? panelId : undefined"
      :aria-busy="busy"
      @click="toggle"
    >
      <AppIcon name="pin" :filled="Boolean(status)" />
    </button>
    <div v-if="open" :id="panelId" ref="panel" class="pin-panel" role="dialog" tabindex="-1" :aria-label="status ? 'Сохранённое вино' : 'Сохранить вино'">
      <template v-if="diary.state.value === 'out'">
        <p>Сохранять вина можно в «Винном дневнике».</p>
        <NuxtLink class="button primary pin-login" :to="loginHref">Войти</NuxtLink>
      </template>
      <template v-else>
        <p class="pin-panel-title">{{ status ? 'Сохранено в дневнике' : 'Не сохранено' }}</p>
        <fieldset v-if="status" :key="radioKey" class="pin-statuses" :aria-busy="busy">
          <legend class="sr-only">Отметка</legend>
          <label v-for="item in SAVED_STATUSES" :key="item" class="pin-status">
            <input type="radio" :name="`${panelId}-status`" :value="item" :checked="status === item" @change="choose(item)">
            <span>{{ SAVED_STATUS_LABELS[item] }}</span>
          </label>
        </fieldset>
        <div v-if="status" class="pin-actions">
          <button type="button" class="account-link" @click="remove">Убрать из сохранённых</button>
          <NuxtLink class="account-link" to="/account?tab=saved">Все сохранённые</NuxtLink>
        </div>
      </template>
      <p v-if="error" class="pin-error" role="alert">{{ error }}</p>
    </div>
  </div>
</template>
