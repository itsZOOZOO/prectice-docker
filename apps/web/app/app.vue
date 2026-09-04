<script setup lang="ts">
useHead({
  titleTemplate: (title) => (title ? `${title} · Prectice` : 'Prectice'),
  meta: [{ name: 'viewport', content: 'width=device-width, initial-scale=1' }],
  htmlAttrs: { lang: 'en' }
})

useSeoMeta({
  title: 'Prectice',
  description: 'Clinic desk — Go 1'
})
</script>

<template>
  <UApp>
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </UApp>
</template>
