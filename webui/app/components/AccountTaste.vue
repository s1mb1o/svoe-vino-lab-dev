<script setup lang="ts">
import { PREFERENCE_BODY, PREFERENCE_COLORS, PREFERENCE_FRESHNESS, PREFERENCE_SWEETNESS, emptyPreferences, parsePreferences, type WineRating } from '#shared/account-taste'
import { accountErrorMessage } from '#shared/account'
import { AccountRequestError, useAccountApi } from '~/composables/useAccountApi'

const api = useAccountApi()
const preferences = ref(emptyPreferences())
const grapes = ref('')
const sparkling = ref('any')
const ratings = ref<WineRating[]>([])
const ready = ref(false)
const busy = ref(false)
const message = ref('')
function fail(error: unknown) { message.value = accountErrorMessage(error instanceof AccountRequestError ? error.body : undefined) }
async function load() {
  ready.value = false
  try {
    const [profile, list] = await Promise.all([api.preferences(), api.ratings()])
    preferences.value = profile.preferences ?? emptyPreferences()
    grapes.value = preferences.value.grapes.join(', ')
    sparkling.value = preferences.value.sparkling === null ? 'any' : preferences.value.sparkling ? 'yes' : 'no'
    ratings.value = list.items
    ready.value = true
  } catch (error) { fail(error) }
}
async function save(reset = false) {
  busy.value = true
  message.value = ''
  try {
    if (reset) {
      await api.clearPreferences()
      preferences.value = emptyPreferences(); grapes.value = ''; sparkling.value = 'any'
    } else {
      const names = grapes.value.split(',').map(name => name.trim()).filter(Boolean)
      const value = { ...preferences.value, sparkling: sparkling.value === 'any' ? null : sparkling.value === 'yes', grapes: names }
      try { parsePreferences(value) } catch {
        message.value = 'Укажите до 16 разных сортов, каждый — от 1 до 80 символов.'
        return
      }
      preferences.value = (await api.putPreferences(value)).preferences
    }
    message.value = reset ? 'Предпочтения сброшены.' : 'Предпочтения сохранены.'
  } catch (error) { fail(error) } finally { busy.value = false }
}
function rated(slug: string, value: WineRating | null) {
  ratings.value = value ? ratings.value.map(item => item.slug === slug ? value : item).sort((a, b) => b.updated_at.localeCompare(a.updated_at) || a.slug.localeCompare(b.slug)) : ratings.value.filter(item => item.slug !== slug)
}
onMounted(load)
</script>

<template>
  <section class="account-taste ym-hide-content" aria-labelledby="taste-heading">
    <h2 id="taste-heading" class="account-subheading">Вкусовые предпочтения</h2>
    <p class="account-hint">Ваш выбор, который можно изменить или сбросить. Эти предпочтения доступны вашим подключённым приложениям.</p>
    <p v-if="message" class="account-notice" role="status">{{ message }}</p>
    <button v-if="!ready" class="account-link" type="button" @click="load">Загрузить предпочтения</button>
    <template v-else>
      <form class="account-form" @submit.prevent="save()">
        <fieldset :disabled="busy"><legend>Какие вина вы выбираете?</legend>
          <label v-for="(label, key) in PREFERENCE_COLORS" :key="key" class="account-check"><input v-model="preferences.colors" type="checkbox" :value="key"> {{ label }}</label>
        </fieldset>
        <label for="taste-sparkling">Игристое</label>
        <select id="taste-sparkling" v-model="sparkling" class="account-select" :disabled="busy"><option value="any">Не важно</option><option value="yes">Предпочитаю игристое</option><option value="no">Предпочитаю тихое</option></select>
        <fieldset :disabled="busy"><legend>Насколько сладкое?</legend>
          <label v-for="(label, key) in PREFERENCE_SWEETNESS" :key="key" class="account-check"><input v-model="preferences.sweetness" type="checkbox" :value="key"> {{ label }}</label>
        </fieldset>
        <label for="taste-body">Насыщенность</label>
        <select id="taste-body" v-model="preferences.body" class="account-select" :disabled="busy"><option v-for="(label, key) in PREFERENCE_BODY" :key="key" :value="key">{{ label }}</option></select>
        <label for="taste-freshness">Свежесть</label>
        <select id="taste-freshness" v-model="preferences.freshness" class="account-select" :disabled="busy"><option v-for="(label, key) in PREFERENCE_FRESHNESS" :key="key" :value="key">{{ label }}</option></select>
        <label for="taste-grapes">Любимые сорта — до 16, через запятую</label>
        <input id="taste-grapes" v-model="grapes" type="text" class="ym-disable-keys" maxlength="2600" :disabled="busy">
        <div class="account-actions"><button class="button secondary" type="submit" :disabled="busy">Сохранить предпочтения</button><button class="account-link" type="button" :disabled="busy" @click="save(true)">Сбросить</button></div>
      </form>
      <h2 class="account-subheading">Мои оценки</h2>
      <p class="account-hint">От 1 до 5. Добавить оценку можно в истории или сохранённых винах. Оценки остаются после очистки этих списков.</p>
      <p v-if="!ratings.length" class="account-hint">Оценок пока нет.</p>
      <ul v-else class="account-identities"><li v-for="item in ratings" :key="item.slug"><div><p>{{ item.wine?.name || item.slug }}</p><TastingRating :slug="item.slug" :rating="item.rating" :note="item.note" @saved="rated(item.slug, $event)" /></div></li></ul>
    </template>
  </section>
</template>

<style scoped>
.account-taste { margin-block: 1.5rem; }
fieldset { border: 1px solid var(--line); border-radius: .5rem; padding: .75rem; }
</style>
