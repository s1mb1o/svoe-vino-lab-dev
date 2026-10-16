<script setup lang="ts">
import type { LineImageFrame } from '#shared/product-line-map'

defineOptions({ inheritAttrs: false })
const props = defineProps<{ src: string; alt: string; frame?: LineImageFrame }>()
const emit = defineEmits<{ error: [event: Event] }>()
const frameStyle = computed(() => props.frame ? { '--plm-frame-ratio': props.frame.width / props.frame.height } : undefined)
const imageStyle = computed(() => {
  const frame = props.frame
  if (!frame) return undefined
  return {
    width: `${frame.source_width / frame.width * 100}%`,
    height: `${frame.source_height / frame.height * 100}%`,
    left: `${-frame.x / frame.width * 100}%`,
    top: `${-frame.y / frame.height * 100}%`,
  }
})
</script>

<template>
  <span v-if="frame" class="plm-image-frame" :class="$attrs.class" :style="frameStyle" data-image-frame>
    <img v-bind="$attrs" :src="src" :alt="alt" :style="imageStyle" @error="emit('error', $event)">
  </span>
  <img v-else v-bind="$attrs" :src="src" :alt="alt" @error="emit('error', $event)">
</template>

<style scoped>
.plm-image-frame {
  position: relative;
  display: inline-block;
  flex: 0 0 auto;
  width: min(calc(var(--plm-image-height) * var(--plm-frame-ratio)), var(--plm-image-width));
  height: min(var(--plm-image-height), calc(var(--plm-image-width) / var(--plm-frame-ratio)));
  overflow: hidden;
}
.plm-image-frame img {
  position: absolute;
  display: block;
  max-width: none;
  max-height: none;
  object-fit: fill;
  pointer-events: none;
}
</style>
