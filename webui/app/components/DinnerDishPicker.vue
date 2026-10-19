<script setup lang="ts">
import { DINNER_PICKER_ENTRIES, dinnerPickerRows, type DinnerPickerEntry } from '#shared/dinner-picker'

const props = defineProps<{ modelValue: string; disabled?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: string]; select: [id: string] }>()
const input = ref<HTMLInputElement>()
const root = ref<HTMLElement>()
const open = ref(false)
const browse = ref(false)
const expanded = ref(new Set<string>())
const active = ref<string | null>(null)
const selected = ref<string | null>(null)
const query = computed(() => browse.value ? '' : props.modelValue.trim())
const searching = computed(() => !!query.value)
const rows = computed(() => dinnerPickerRows(expanded.value, query.value))
const branches = new Set(DINNER_PICKER_ENTRIES.filter(node => node.parentId).map(node => node.parentId))
const idFor = (id: string) => `dinner-option-${id}`
function focus() { input.value?.focus() }
function close() { open.value = false; active.value = null }
function showCategories() { browse.value = true; expanded.value = new Set(); active.value = null; open.value = true; focus() }
function edit(event: Event) {
  browse.value = false; selected.value = null; active.value = null; open.value = true
  emit('update:modelValue', (event.target as HTMLInputElement).value)
}
function choose(node: DinnerPickerEntry) {
  emit('update:modelValue', node.label); emit('select', node.id)
  selected.value = node.id; close(); focus()
}
function toggle(node: DinnerPickerEntry) {
  active.value = node.id
  const next = new Set(expanded.value)
  if (next.has(node.id)) next.delete(node.id); else next.add(node.id)
  expanded.value = next
}
async function reveal() { await nextTick(); document.getElementById(idFor(active.value || ''))?.scrollIntoView({ block: 'nearest' }) }
function keydown(event: KeyboardEvent) {
  if (event.isComposing) return
  if (event.key === 'Escape') { if (open.value) event.preventDefault(); close(); return }
  if (event.key === 'Tab') { close(); return }
  if (event.key === 'Enter') {
    const node = open.value && rows.value.find(value => value.id === active.value)
    if (node) { event.preventDefault(); choose(node) } else close()
    return
  }
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault(); open.value = true
    const index = rows.value.findIndex(node => node.id === active.value)
    const next = index < 0 ? (event.key === 'ArrowDown' ? 0 : rows.value.length - 1) : Math.max(0, Math.min(rows.value.length - 1, index + (event.key === 'ArrowDown' ? 1 : -1)))
    active.value = rows.value[next]?.id ?? null; void reveal(); return
  }
  if (!open.value || searching.value) return
  const node = rows.value.find(value => value.id === active.value)
  if (!node) return
  if (event.key === 'ArrowRight' && branches.has(node.id)) {
    event.preventDefault()
    if (!expanded.value.has(node.id)) toggle(node)
    else active.value = rows.value.find(value => value.parentId === node.id)?.id ?? node.id
    void reveal()
  } else if (event.key === 'ArrowLeft') {
    event.preventDefault()
    if (expanded.value.has(node.id)) toggle(node)
    else active.value = node.parentId
    void reveal()
  }
}
function position(node: DinnerPickerEntry) {
  const siblings = searching.value ? rows.value : DINNER_PICKER_ENTRIES.filter(value => value.parentId === node.parentId)
  return { 'aria-posinset': siblings.findIndex(value => value.id === node.id) + 1, 'aria-setsize': siblings.length }
}
function outside(event: PointerEvent) { if (!root.value?.contains(event.target as Node)) close() }
onMounted(() => document.addEventListener('pointerdown', outside))
onBeforeUnmount(() => document.removeEventListener('pointerdown', outside))
watch(() => props.disabled, value => { if (value) close() })
watch(() => props.modelValue, value => { if (DINNER_PICKER_ENTRIES.find(node => node.id === selected.value)?.label !== value) selected.value = null })
defineExpose({ focus, close, showCategories })
</script>

<template>
  <div ref="root" class="dish-picker" @focusout="event => { if (!(event.currentTarget as HTMLElement).contains(event.relatedTarget as Node)) close() }">
    <div class="dish-picker-field">
      <input id="dinner-dish" ref="input" :value="modelValue" type="search" role="combobox" aria-autocomplete="list" aria-haspopup="tree" aria-controls="dinner-dish-options" :aria-expanded="open" :aria-activedescendant="open && active ? idFor(active) : undefined" aria-describedby="dinner-dish-hint" maxlength="500" placeholder="Блюдо или категория" :disabled="disabled" required autocomplete="off" @input="edit" @focus="open = true" @keydown="keydown">
      <button type="button" class="dish-picker-toggle" :disabled="disabled" aria-label="Показать категории блюд" :aria-expanded="open && browse" aria-controls="dinner-dish-options" @click="open && browse ? close() : showCategories()"><span aria-hidden="true">⌄</span></button>
    </div>
    <div v-if="open && !disabled" class="dish-picker-popup">
      <p class="dish-picker-help">{{ searching ? 'Совпадения по названию и категории' : 'Выберите категорию или раскройте её стрелкой' }}</p>
      <div id="dinner-dish-options" role="tree" aria-label="Блюда по категориям" class="dish-picker-options">
        <div v-for="node in rows" :id="idFor(node.id)" :key="node.id" role="treeitem" :aria-label="searching ? [node.context, node.label].filter(Boolean).join(' › ') : node.displayLabel" :aria-level="searching ? 1 : node.level" v-bind="position(node)" :aria-expanded="!searching && branches.has(node.id) ? expanded.has(node.id) : undefined" :aria-selected="selected === node.id" class="dish-picker-option" :class="{ active: active === node.id }" :style="{ '--level': searching ? 1 : node.level }" @mousedown.prevent @click="choose(node)">
          <span class="dish-picker-copy"><span>{{ searching ? node.label : node.displayLabel }}</span><small v-if="searching && node.context">{{ node.context }}</small></span>
          <span v-if="!searching && branches.has(node.id)" class="dish-picker-expand" aria-hidden="true" @click.stop="toggle(node)">{{ expanded.has(node.id) ? '⌄' : '›' }}</span>
        </div>
      </div>
      <p v-if="!rows.length" class="dish-picker-help" role="status">Совпадений нет. Оставьте своё название или выберите категорию стрелкой справа от поля.</p>
    </div>
    <p id="dinner-dish-hint" class="dish-picker-hint">Можно выбрать категорию, уточнить блюдо или ввести своё название.<span class="sr-only"> Стрелки вверх и вниз — переход по списку, вправо и влево — раскрытие и сворачивание категории, Enter — выбор, Escape — закрытие списка.</span></p>
  </div>
</template>

<style scoped>
.dish-picker { position: relative; min-width: 0; }
.dish-picker-field { position: relative; }
.dish-picker-field input { display: block; width: 100%; min-width: 0; min-height: 48px; padding: 12px 52px 12px 12px; border: 1px solid var(--line); border-radius: 9px; background: var(--paper); color: var(--ink); font: inherit; font-size: 14px; }
.dish-picker-field input::-webkit-search-cancel-button { display: none; }
.dish-picker-toggle { position: absolute; inset: 1px 1px 1px auto; width: 46px; border: 0; border-inline-start: 1px solid var(--line); border-radius: 0 8px 8px 0; background: transparent; color: var(--accent); font-size: 25px; }
.dish-picker-popup { position: absolute; z-index: 5; top: 56px; inset-inline: 0; border: 1px solid var(--line); border-radius: 9px; background: var(--paper); box-shadow: 0 12px 28px #0002; overflow: hidden; }
.dish-picker-help, .dish-picker-hint { margin: 0; padding: 10px 12px; color: var(--muted); font-size: 12px; line-height: 1.6; }
.dish-picker-hint { padding: 10px 0 0; }
.dish-picker-options { max-height: 300px; overflow: auto; overscroll-behavior: contain; }
.dish-picker-option { display: flex; align-items: stretch; min-height: 48px; padding-inline-start: calc(12px + (var(--level) - 1) * 16px); border-top: 1px solid var(--line); cursor: pointer; font-size: 14px; line-height: 1.5; }
.dish-picker-copy { flex: 1; min-width: 0; padding: 12px 8px 12px 0; overflow-wrap: anywhere; }
.dish-picker-copy small { display: block; color: var(--muted); font-size: 11px; margin-top: 3px; }
.dish-picker-expand { display: grid; place-items: center; min-width: 48px; color: var(--accent); font-size: 22px; border-inline-start: 1px solid var(--line); }
.dish-picker-option.active, .dish-picker-option:hover { background: var(--cream); box-shadow: inset 3px 0 var(--accent); }
.dish-picker-option[aria-selected="true"] { color: var(--accent); }
@media (forced-colors: active) { .dish-picker-option.active { outline: 2px solid Highlight; outline-offset: -2px; } }
@media (max-width: 767px) { .dish-picker-field input { font-size: 16px; } }
</style>
