<script setup lang="ts">
// Filters of a «Винный дневник» list: text, color, and sugar. A list adds its own field in the slot.
import { COLOR_LABELS, SUGAR_LABELS, type ColorKey, type DiaryFilter, type SugarKey } from '#shared/diary'

const props = defineProps<{ colors: ColorKey[]; sugars: SugarKey[]; label: string }>()
const filter = defineModel<DiaryFilter>({ required: true })
const id = useId()
const active = computed(() => Boolean(filter.value.text.trim() || filter.value.color || filter.value.sugar))
const update = (patch: Partial<DiaryFilter>) => { filter.value = { ...filter.value, ...patch } }
defineExpose({ active })
</script>

<template>
  <div class="diary-filters" role="search" :aria-label="props.label">
    <div class="diary-filter diary-filter-text">
      <label :for="`${id}-text`">Название или винодельня</label>
      <input :id="`${id}-text`" type="search" class="ym-disable-keys" autocomplete="off" maxlength="80" :value="filter.text" @input="update({ text: ($event.target as HTMLInputElement).value })">
    </div>
    <div class="diary-filter">
      <label :for="`${id}-color`">Цвет</label>
      <select :id="`${id}-color`" class="account-select" :value="filter.color" @change="update({ color: ($event.target as HTMLSelectElement).value as DiaryFilter['color'] })">
        <option value="">Любой</option>
        <option v-for="key in colors" :key="key" :value="key">{{ COLOR_LABELS[key] }}</option>
      </select>
    </div>
    <div class="diary-filter">
      <label :for="`${id}-sugar`">Сахар</label>
      <select :id="`${id}-sugar`" class="account-select" :value="filter.sugar" @change="update({ sugar: ($event.target as HTMLSelectElement).value as DiaryFilter['sugar'] })">
        <option value="">Любой</option>
        <option v-for="key in sugars" :key="key" :value="key">{{ SUGAR_LABELS[key] }}</option>
      </select>
    </div>
    <slot />
  </div>
</template>
