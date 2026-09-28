<script setup lang="ts">
defineEmits<{ chooseBottle: [] }>()
</script>

<template>
  <section class="shelf-unavailable" aria-labelledby="shelf-unavailable-heading">
    <div class="shelf-unavailable-symbol" aria-hidden="true"><AppIcon name="shelf" /></div>
    <p class="step-label">НЕСКОЛЬКО ВИН НА ОДНОМ ФОТО</p>
    <h2 id="shelf-unavailable-heading">«Вся полка» временно недоступна</h2>
    <p>Сейчас портал ищет вино по фотографии одной бутылки. Обработка полки вернётся позже.</p>
    <button class="button primary" @click="$emit('chooseBottle')"><AppIcon name="scan" />Перейти к одной бутылке</button>
    <p class="shelf-unavailable-note"><AppIcon name="info" />Фото не отправляется на обработку.</p>
  </section>
</template>
