<script setup lang="ts">
const title = 'Найти вино на полке по фото — Что за вино?'
const description = 'Снимите полку целиком. Мы найдём бутылки и покажем совпадения с каталогом российского вина.'
useSeoMeta({ title, description, ogType: 'website', ogTitle: title, ogDescription: description, ogUrl: 'https://chtozavino.ru/shelf', twitterTitle: title, twitterDescription: description })
useHead({ link: [{ rel: 'canonical', href: 'https://chtozavino.ru/shelf' }] })
</script>

<template>
  <ScannerPage mode="shelf" />
</template>
