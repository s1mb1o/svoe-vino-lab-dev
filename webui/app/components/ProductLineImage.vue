<script setup lang="ts">
import type { StyleValue } from 'vue'
import type { LineImageFrame } from '#shared/product-line-map'

defineOptions({ inheritAttrs: false })
const props = defineProps<{ src: string; alt: string; frame?: LineImageFrame }>()
const emit = defineEmits<{ error: [event: Event] }>()
const attrs = useAttrs()
function imageAttrs() {
  // Apply visual attributes once, on the clipped frame. Keep native attributes on the image.
  const { class: _class, style: _style, ...nativeAttrs } = attrs
  return nativeAttrs
}
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
  <span v-if="frame" class="plm-image-frame" :class="$attrs.class" :style="[$attrs.style as StyleValue, frameStyle]" data-image-frame>
    <img v-bind="imageAttrs()" :src="src" :alt="alt" :style="imageStyle" @error="emit('error', $event)">
  </span>
  <img v-else v-bind="$attrs" :src="src" :alt="alt" @error="emit('error', $event)">
</template>

<style scoped>
.plm-image-frame {
  position: relative;
  display: inline-block;
  flex: 0 0 auto;
  width: min(calc(var(--plm-image-height, 112px) * var(--plm-frame-ratio)), var(--plm-image-width, 70px));
  height: min(var(--plm-image-height, 112px), calc(var(--plm-image-width, 70px) / var(--plm-frame-ratio)));
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
