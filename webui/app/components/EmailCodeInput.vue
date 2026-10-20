<script setup lang="ts">
const props = defineProps<{ id: string; disabled?: boolean }>()
const code = defineModel<string>({ required: true })
const input = ref<HTMLInputElement>()
const focused = ref(false)
const start = ref(0)
const end = ref(0)
const active = computed(() => Math.min(start.value, 5))

function readSelection() {
  start.value = input.value?.selectionStart ?? 0
  end.value = input.value?.selectionEnd ?? start.value
}

function update(event: Event) {
  const field = event.target as HTMLInputElement
  const caret = field.value.slice(0, field.selectionStart ?? field.value.length).replace(/\D/g, '').length
  const digits = field.value.replace(/\D/g, '').slice(0, 6)
  code.value = digits
  field.value = digits
  nextTick(() => {
    field.setSelectionRange(caret, caret)
    readSelection()
  })
}

function focusDigit(index: number) {
  if (props.disabled || !input.value) return
  input.value.focus()
  const position = Math.min(index, code.value.length)
  input.value.setSelectionRange(position, Math.min(position + 1, code.value.length))
  readSelection()
}

function paste(event: ClipboardEvent) {
  const digits = event.clipboardData?.getData('text').replace(/\D/g, '')
  if (!digits || !input.value) return
  event.preventDefault()
  const field = input.value
  const from = field.selectionStart ?? 0
  const to = field.selectionEnd ?? from
  code.value = digits.length >= 6 ? digits.slice(0, 6) : (code.value.slice(0, from) + digits + code.value.slice(to)).slice(0, 6)
  nextTick(() => {
    const position = digits.length >= 6 ? 6 : Math.min(from + digits.length, 6)
    field.setSelectionRange(position, position)
    readSelection()
  })
}
</script>

<template>
  <div class="email-code" :class="{ 'is-disabled': disabled }">
    <!-- One native field preserves autofill, paste, selection, and keyboard editing. -->
    <input
      :id="id"
      ref="input"
      :value="code"
      class="email-code-input ym-disable-keys ym-hide-content"
      type="text"
      name="one-time-code"
      autocomplete="one-time-code"
      inputmode="numeric"
      pattern="[0-9]{6}"
      maxlength="6"
      required
      :disabled="disabled"
      @input="update"
      @paste="paste"
      @focus="focused = true; readSelection()"
      @blur="focused = false"
      @select="readSelection"
      @keyup="readSelection"
    >
    <span
      v-for="(_, index) in 6"
      :key="index"
      class="email-code-digit ym-hide-content"
      :class="{
        'is-active': focused && active === index,
        'is-selected': focused && index >= start && index < end,
        'has-caret': focused && start === end && active === index,
        'caret-after': start === 6,
      }"
      aria-hidden="true"
      @pointerdown.prevent="focusDigit(index)"
    >{{ code[index] }}</span>
  </div>
</template>

<style scoped>
.email-code { position: relative; display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: clamp(6px, 2vw, 12px); width: 100%; max-width: 384px; margin-inline: auto; }
.email-code-input { position: absolute; inset: 0; width: 100%; opacity: 0; }
.email-code-digit { position: relative; display: grid; place-items: center; min-width: 0; height: 64px; border: 1px solid var(--line); border-radius: 12px; background: var(--paper); color: var(--ink); font-size: 28px; font-variant-numeric: tabular-nums; line-height: 1; cursor: text; }
.email-code-digit.is-active { border-color: var(--accent); outline: 2px solid var(--accent); outline-offset: 2px; }
.email-code-digit.is-selected { background: var(--cream); }
.email-code-digit.has-caret::after { content: ''; position: absolute; top: 18px; bottom: 18px; left: calc(50% - .35em); width: 2px; background: var(--accent); animation: email-code-caret 1s step-end infinite; }
.email-code-digit.has-caret:empty::after { left: calc(50% - 1px); }
.email-code-digit.caret-after::after { left: calc(50% + .35em); }
.email-code.is-disabled { opacity: .55; }
.email-code.is-disabled .email-code-digit { cursor: default; }
@keyframes email-code-caret { 50% { opacity: 0; } }
@media (prefers-reduced-motion: reduce) { .email-code-digit.has-caret::after { animation: none; } }
@media (forced-colors: active) { .email-code-digit.is-active { border-color: Highlight; outline-color: Highlight; } .email-code-digit.has-caret::after { background: CanvasText; } }
</style>
