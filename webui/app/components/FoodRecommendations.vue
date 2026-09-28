<script setup lang="ts">
import type { Wine } from '#shared/catalog'
const props = defineProps<{ wine: Wine; mock: boolean }>()
const food = useFoodRecommendations(props.wine.slug)
const { phase, error, result, stores, loadingStores, busy } = food
const manual = ref(false)
const selectedStore = ref<number | ''>('')
const heading = ref<HTMLElement>()
const panel = ref<HTMLElement>()
const brokenImages = reactive(new Set<string>())
const distance = computed(() => {
  const km = result.value?.distanceKm
  if (km == null) return ''
  return km < 1 ? `${Math.round(km * 1000)} м по прямой` : `${new Intl.NumberFormat('ru', { maximumFractionDigits: 1 }).format(km)} км по прямой`
})
const checkedTime = computed(() => result.value ? new Intl.DateTimeFormat('ru', { hour: '2-digit', minute: '2-digit' }).format(new Date(result.value.checkedAt)) : '')
async function showStores() { manual.value = true; await food.loadStores() }
function nearby() { manual.value = false; void food.nearby() }
watch(phase, async value => {
  if (value !== 'ready') return
  await nextTick()
  heading.value?.focus({ preventScroll: true })
  panel.value?.scrollIntoView({ block: 'start', behavior: 'auto' })
})
useFoodTools(food)
</script>

<template>
  <section ref="panel" class="food-panel" aria-labelledby="food-heading" :aria-busy="busy">
    <div class="food-intro">
      <div class="food-emblem" aria-hidden="true"><AppIcon name="food" /></div>
      <div class="food-title"><p class="step-label">03 / ВКУСНОЕ СОЧЕТАНИЕ</p><h2 id="food-heading" ref="heading" tabindex="-1">{{ result ? 'К вашему вину' : 'А что подать к вину?' }}</h2><p>{{ mock ? 'Подберём продукты к демонстрационному вину.' : 'Три идеи для вашего стола — из ассортимента «Глобуса».' }}</p></div>
      <div v-if="!result && !busy" class="food-start">
        <button class="button primary" @click="nearby"><AppIcon name="location" />Подобрать 3 продукта к вину</button>
        <p>Разрешите геолокацию для поиска ближайшего «Глобуса».</p>
        <button class="text-button" @click="showStores">Выбрать магазин вручную<AppIcon name="arrow" /></button>
      </div>
      <button v-if="result && !busy" class="button secondary food-change" @click="showStores"><AppIcon name="location" />Сменить магазин</button>
    </div>

    <div v-if="busy" class="food-progress" role="status"><span class="spinner" /><div><strong>{{ phase === 'locating' ? 'Определяем местоположение…' : loadingStores ? 'Получаем магазины…' : 'Ищем вкусные сочетания…' }}</strong><p>{{ phase === 'locating' ? 'Подтвердите доступ в окне браузера.' : 'Проверяем ассортимент «Глобуса».' }}</p></div><button class="text-button" @click="food.cancel()">Отменить</button></div>
    <div v-if="error" class="inline-error" role="alert"><AppIcon name="info" /><span>{{ error }}</span></div>

    <form v-if="manual && !loadingStores && stores.length" class="store-form" @submit.prevent="selectedStore && food.recommend({ storeId: selectedStore })">
      <label for="food-store">Магазин «Глобус»<select id="food-store" v-model="selectedStore" :disabled="busy" required><option disabled value="">Выберите магазин и адрес</option><option v-for="store in stores" :key="store.id" :value="store.id">{{ store.name }} — {{ store.address }}</option></select></label>
      <button class="button primary" :disabled="!selectedStore || busy" type="submit">Подобрать продукты<AppIcon name="arrow" /></button>
    </form>

    <template v-if="result && !busy">
      <div class="food-store"><div class="store-symbol"><AppIcon name="store" /></div><div><p class="store-kicker">{{ result.distanceKm == null ? 'ВЫБРАННЫЙ МАГАЗИН' : 'БЛИЖАЙШИЙ МАГАЗИН СЕТИ «ГЛОБУС»' }}</p><h3>{{ result.store.name }}</h3><p>{{ result.store.address }}</p><p>{{ distance }}<span v-if="distance && result.store.schedule"> · </span>{{ result.store.schedule }}</p></div><span class="food-source"><span />Ассортимент магазина</span></div>
      <p v-if="result.distanceKm != null && result.distanceKm > 50" class="food-notice">Рядом с вами нет «Глобуса»: ближайший магазин находится далеко. Можно выбрать другой магазин вручную.</p>
      <p v-if="!result.complete" class="food-notice" role="status">{{ result.products.length ? `Нашли ${result.products.length} из 3 сочетаний. Для остальных идей доступных товаров пока нет.` : 'Сейчас не нашли подходящих товаров в этом магазине. Попробуйте выбрать другой.' }}</p>
      <div class="food-grid">
        <article v-for="(product, index) in result.products" :key="product.id" class="food-card">
          <div class="food-image"><span class="food-number">0{{ index + 1 }}</span><img v-if="product.image && !brokenImages.has(product.id)" :src="product.image" :alt="product.name" loading="lazy" referrerpolicy="no-referrer" @error="brokenImages.add(product.id)"><AppIcon v-else name="food" /></div>
          <div class="food-card-copy"><p class="food-idea">{{ product.food }}</p><h3>{{ product.name }}</h3><p class="food-reason">{{ product.reason }}</p><div class="food-price"><strong>{{ product.priceLabel }}</strong><span>Доступен по данным магазина</span></div><p v-if="product.conditions.length" class="food-conditions">{{ product.conditions.join(' · ') }}</p><a :href="product.url" class="button secondary" target="_blank" rel="noopener noreferrer">Посмотреть в «Глобусе»<AppIcon name="arrow-up-right" /></a></div>
        </article>
      </div>
      <p class="food-fineprint">Данные «Глобуса» на {{ checkedTime }}. Цена и наличие могут измениться. Проверьте выбранный магазин на сайте сети.</p>
    </template>
    <p class="food-privacy"><AppIcon name="location" />Геолокация нужна только для поиска магазина и не сохраняется.</p>
  </section>
</template>
