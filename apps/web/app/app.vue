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
  <UApp class="!block h-svh max-h-svh w-full max-w-full overflow-hidden">
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </UApp>
</template>
