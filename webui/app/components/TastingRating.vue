<script setup lang="ts">
import type { WineRating } from '#shared/account-taste'
import { accountErrorMessage } from '#shared/account'
import { AccountRequestError, useAccountApi } from '~/composables/useAccountApi'

const props = defineProps<{ slug: string; rating?: number | null; note?: string | null }>()
const emit = defineEmits<{ saved: [value: WineRating | null] }>()
const api = useAccountApi()
const open = ref(false)
const value = ref(props.rating ?? 0)
const note = ref(props.note ?? '')
const stored = ref(props.rating ?? null)
const busy = ref(false)
const message = ref('')
watch(() => [props.rating, props.note] as const, ([rating, text]) => {
  if (!open.value) { value.value = rating ?? 0; stored.value = rating ?? null; note.value = text ?? '' }
})
async function save(remove = false) {
  busy.value = true
  message.value = ''
  try {
    if (remove) {
      await api.deleteRating(props.slug)
      value.value = 0; note.value = ''; stored.value = null
      emit('saved', null)
    } else {
      const answer = await api.putRating(props.slug, value.value, note.value.trim() || null)
      stored.value = answer.rating; note.value = answer.note ?? ''
      emit('saved', answer)
    }
    open.value = false
    message.value = remove ? 'Оценка удалена.' : 'Оценка сохранена.'
  } catch (error) {
    message.value = accountErrorMessage(error instanceof AccountRequestError ? error.body : undefined)
  } finally { busy.value = false }
}
</script>

<template>
  <div class="tasting-rating ym-hide-content">
    <button class="account-link" type="button" :aria-expanded="open" @click="open = !open">{{ stored ? `Оценка: ${stored} из 5` : 'Оценить вино' }}</button>
    <form v-if="open" class="account-form" @submit.prevent="save()">
      <label :for="`rating-${slug}`">Ваша оценка</label>
      <select :id="`rating-${slug}`" v-model.number="value" class="account-select" :disabled="busy" required>
        <option :value="0" disabled>Выберите оценку</option>
        <option v-for="score in 5" :key="score" :value="score">{{ score }} из 5</option>
      </select>
      <label :for="`tasting-note-${slug}`">Заметка к оценке</label>
      <textarea :id="`tasting-note-${slug}`" v-model="note" class="ym-disable-keys ym-hide-content" rows="3" maxlength="1000" :aria-invalid="[...note.trim()].length > 500" :disabled="busy" />
      <p class="account-hint">До 500 символов. Оценка и эта заметка доступны вашим подключённым приложениям. Личные заметки в сохранённых винах остаются отдельно.</p>
      <div class="account-actions">
        <button class="button secondary" type="submit" :disabled="busy || value < 1 || [...note.trim()].length > 500">Сохранить оценку</button>
        <button v-if="stored" class="account-link account-danger" type="button" :disabled="busy" @click="save(true)">Удалить оценку</button>
      </div>
    </form>
    <p v-if="message" class="account-hint" role="status">{{ message }}</p>
  </div>
</template>

<style scoped>
.tasting-rating { margin-block: .75rem; }
.account-form { margin-top: .75rem; }
textarea { width: 100%; min-height: 6rem; resize: vertical; padding: .75rem; border: 1px solid var(--line); border-radius: 12px; background: var(--card); color: var(--ink); font: inherit; line-height: 1.5; }
textarea:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
</style>
