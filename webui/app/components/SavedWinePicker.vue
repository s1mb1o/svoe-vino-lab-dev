<script setup lang="ts">
import { normalizedFact, type SavedComparisonAnswer } from '#shared/alternatives'
import { accountErrorMessage } from '#shared/account'
import { AccountRequestError } from '~/composables/useAccountApi'

const props = defineProps<{ slug: string }>()
const api = useAccountApi()
const diary = useDiary()
const comparison = useWineComparison()
const route = useRoute()
const answer = shallowRef<SavedComparisonAnswer | null>(null)
const state = ref<'loading' | 'ready' | 'login' | 'error'>('loading')
const error = ref('')
const query = ref('')
const search = ref<HTMLInputElement>()
const searchId = useId()
let generation = 0
const shown = computed(() => {
  const words = normalizedFact(query.value).split(' ').filter(Boolean)
  return (answer.value?.items ?? []).filter(item => {
    const text = normalizedFact([item.wine?.name, item.wine?.producer, item.wine?.region, item.slug.replace(/-/g, ' ')].filter(Boolean).join(' '))
    return words.every(word => text.includes(word))
  })
})
async function load() {
  const gen = ++generation
  answer.value = null
  state.value = 'loading'
  error.value = ''
  try {
    const data = await api.savedComparison(props.slug)
    if (gen !== generation) return
    answer.value = data
    state.value = 'ready'
    await nextTick()
    search.value?.focus()
  } catch (reason) {
    if (gen !== generation) return
    state.value = reason instanceof AccountRequestError && reason.status === 401 ? 'login' : 'error'
    error.value = reason instanceof AccountRequestError && reason.body.error === 'unknown_wine'
      ? 'Исходного вина нет в проверенном снимке каталога. Сравнение пока недоступно.'
      : accountErrorMessage(reason instanceof AccountRequestError ? reason.body : undefined)
  }
}
// Keep the private list in this mounted picker only. Discard delayed responses after account reset.
watch([diary.owner, diary.state], ([owner, state], [oldOwner]) => {
  if (oldOwner && (owner !== oldOwner || state === 'out' || state === 'off' || state === 'unknown')) {
    generation++
    answer.value = null
    query.value = ''
    comparison.cancelSaved()
  }
})
watch(() => props.slug, load)
onMounted(load)
onBeforeUnmount(() => { generation++; answer.value = null })
</script>

<template>
  <section class="f04-saved-picker ym-hide-content" aria-label="Выбор второго вина из сохранённых" :aria-busy="state === 'loading'">
    <p v-if="state === 'loading'" role="status">Загружаем сохранённые вина…</p>
    <template v-else-if="state === 'login'">
      <p>Войдите в «Винный дневник», чтобы выбрать второе вино из сохранённых.</p>
      <NuxtLink class="button primary" :to="`/account?next=${encodeURIComponent(route.fullPath)}`" @click="comparison.rememberSaved()">Войти</NuxtLink>
    </template>
    <template v-else-if="state === 'error'">
      <p role="alert">{{ error }}</p>
      <button class="button secondary" @click="load">Повторить</button>
    </template>
    <template v-else-if="answer">
      <p>Первое вино: <strong>{{ answer.base.name }}</strong>. Выберите второе вино ниже.</p>
      <p v-if="!answer.items.length" role="status">В сохранённых пока нет другого вина. Сохраните вино значком булавки в его карточке.</p>
      <template v-else>
        <label class="f04-saved-search" :for="searchId">Поиск в сохранённых<input :id="searchId" ref="search" v-model="query" class="ym-disable-keys" type="search" placeholder="Название, производитель или регион"></label>
        <ul v-if="shown.length" class="f04-saved-options">
          <li v-for="item in shown" :key="item.slug">
            <div><h3>{{ item.wine?.name || item.slug }}</h3><p v-if="item.wine?.producer">{{ item.wine.producer }}<template v-if="item.wine.region"> · {{ item.wine.region }}</template></p></div>
            <button v-if="item.wine" class="button secondary" :aria-label="`Сравнить с «${item.wine.name}»`" @click="comparison.open({ base: answer.base, candidate: item.wine, version: answer.version })">Сравнить</button>
            <p v-else>Этого вина нет в снимке каталога. Сравнение пока недоступно.</p>
          </li>
        </ul>
        <p v-else role="status">Ничего не найдено. Измените поиск.</p>
      </template>
    </template>
    <button class="text-button f04-saved-cancel" @click="comparison.cancelSaved()">{{ comparison.pair.value ? 'Вернуться к сравнению' : 'Отмена' }}</button>
  </section>
</template>
