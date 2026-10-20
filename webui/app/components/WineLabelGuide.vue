<script setup lang="ts">
import type { Wine } from '#shared/catalog'
import { deriveWineLabelExperience, type LabelSection } from '#shared/label'

const props = defineProps<{ wine: Wine }>()
const experience = computed(() => deriveWineLabelExperience(props.wine))
const selectedId = ref<LabelSection['id']>('grapes')
const selected = computed(() => experience.value.sections.find(section => section.id === selectedId.value) || experience.value.sections[0])
const detailId = useId()
</script>

<template>
  <section v-if="selected" class="label-guide" aria-label="Этикетка понятным языком">
    <div class="label-guide-heading"><h3>{{ wine.name }}</h3><p v-if="wine.producer">{{ wine.producer }}</p></div>
    <div class="label-guide-choices" role="group" aria-label="Характеристики вина">
      <button v-for="section in experience.sections" :key="section.id" type="button" :aria-pressed="selected.id === section.id" :aria-controls="detailId" :data-label-section="section.id" @click="selectedId = section.id">
        <span>{{ section.label }}</span><strong>{{ section.value }}</strong>
      </button>
    </div>
    <section :id="detailId" class="label-guide-detail" aria-live="polite">
      <p class="step-label">{{ selected.id === 'grapes' ? 'О СОРТАХ ВИНОГРАДА' : selected.label.toLocaleUpperCase('ru') }}</p>
      <h3>{{ selected.title }}</h3>
      <p v-if="selected.intro" class="label-guide-intro">{{ selected.intro }}</p>
      <div class="label-guide-notes" :class="{ 'label-guide-blend': selected.notes.length > 1 }">
        <article v-for="item in selected.notes" :key="item.value" class="label-guide-note">
          <h4>{{ item.value }}</h4><p>{{ item.text }}</p>
          <div class="label-guide-sources"><a v-for="reference in item.sources" :key="reference.url" :href="reference.url" target="_blank" rel="noopener noreferrer">{{ reference.name }}<span class="sr-only"> (откроется в новой вкладке)</span><AppIcon name="arrow-up-right" /></a></div>
        </article>
      </div>
    </section>
  </section>
</template>

<style scoped>
.label-guide { padding-top: 24px; }
.label-guide-heading h3 { margin: 0; font: 500 30px/1.25 'Playfair Display', Georgia, serif; overflow-wrap: anywhere; }
.label-guide-heading p { margin-top: 8px; color: var(--muted); font-size: 13px; }
.label-guide-choices { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin: 24px 0 18px; }
.label-guide-choices button { min-width: 0; min-height: 78px; padding: 15px 18px; border: 1px solid var(--line); border-radius: 12px; background: var(--paper); color: var(--ink); text-align: left; font: inherit; cursor: pointer; }
.label-guide-choices button > span { display: block; font-size: 12px; color: var(--muted); margin-bottom: 6px; }
.label-guide-choices button > strong { display: block; font-size: 14px; font-weight: 500; line-height: 1.5; overflow-wrap: anywhere; }
.label-guide-choices button[aria-pressed='true'] { background: var(--accent); color: var(--paper); border-color: var(--accent); }
.label-guide-choices button[aria-pressed='true'] > span { color: inherit; }
.label-guide-detail { padding: 24px; border-radius: 16px; background: var(--cream); }
.label-guide-detail > h3 { margin: 10px 0 16px; font: 500 27px/1.25 'Playfair Display', Georgia, serif; }
.label-guide-intro { line-height: 1.75; font-size: 14px; margin-bottom: 24px; }
.label-guide-notes { display: grid; gap: 22px; }
.label-guide-blend { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.label-guide-note { min-width: 0; }
.label-guide-note h4 { font-size: 17px; font-weight: 500; margin: 0 0 10px; overflow-wrap: anywhere; }
.label-guide-note > p { font-size: 14px; line-height: 1.8; }
.label-guide-sources { margin-top: 14px; }
.label-guide-sources a { display: inline-flex; align-items: center; gap: 6px; min-height: 30px; color: var(--accent); font-size: 12px; line-height: 1.6; text-decoration: underline; text-underline-offset: 3px; }
.label-guide-sources .icon { width: 13px; height: 13px; flex-shrink: 0; }
@media (max-width: 600px) {
  .label-guide-heading h3 { font-size: 26px; }
  .label-guide-choices button { padding: 13px; }
  .label-guide-detail { padding: 20px 16px; }
  .label-guide-blend { grid-template-columns: 1fr; }
  .label-guide-detail > h3 { font-size: 24px; }
  .label-guide-sources a { min-height: 44px; }
}
@media (max-width: 400px) {
  .label-guide-choices button[data-label-section='grapes'] { grid-column: 1 / -1; }
}
</style>
