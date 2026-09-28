<script setup lang="ts">
import { saveAgeConfirmation } from '~/utils/age'

const emit = defineEmits<{ confirmed: [] }>()
const declined = ref(false)
const storageError = ref(false)

function confirm() {
  storageError.value = !saveAgeConfirmation(localStorage)
  if (storageError.value) return
  emit('confirmed')
}
</script>

<template>
  <div class="age-gate" aria-labelledby="age-heading">
    <section class="age-card" role="dialog" aria-modal="true" aria-describedby="age-copy">
      <img src="/reference/logo.svg" alt="Свое Вино" width="160" height="40">
      <div class="age-mark" aria-hidden="true">18+</div>
      <template v-if="!declined">
        <p class="step-label">ПОДТВЕРЖДЕНИЕ ВОЗРАСТА</p>
        <h2 id="age-heading">Вам уже исполнилось 18 лет?</h2>
        <p id="age-copy">Портал посвящён культуре российского вина. Подтвердите возраст, чтобы продолжить.</p>
        <div class="age-actions">
          <button class="button primary" autofocus @click="confirm">Да, мне есть 18 лет</button>
          <button class="button secondary" @click="declined = true">Нет, мне нет 18 лет</button>
        </div>
        <p v-if="storageError" class="age-storage-note error" role="alert"><AppIcon name="info" />Не удалось сохранить подтверждение. Разрешите локальное хранение и повторите.</p>
        <p v-else class="age-storage-note"><AppIcon name="info" />Подтверждение сохраняется только в этом браузере.</p>
      </template>
      <template v-else>
        <p class="step-label">ДОСТУП ОГРАНИЧЕН</p>
        <h2 id="age-heading">Этот портал доступен только совершеннолетним</h2>
        <p id="age-copy">Мы не сохранили ваш ответ. Закройте страницу или вернитесь к подтверждению.</p>
        <button class="button secondary" @click="declined = false">Вернуться</button>
      </template>
      <p class="age-warning">Чрезмерное употребление алкоголя вредит вашему здоровью</p>
    </section>
  </div>
</template>
