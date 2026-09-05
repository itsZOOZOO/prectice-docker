<script setup lang="ts">
useHead({
  titleTemplate: (title) => (title ? `${title} · Nav Dental` : 'Nav Dental'),
  meta: [{ name: 'viewport', content: 'width=device-width, initial-scale=1' }],
  htmlAttrs: { lang: 'en' }
})

useSeoMeta({
  title: 'Nav Dental',
  description: 'Clinic desk & mobile'
})
</script>

<template>
  <UApp class="!block h-svh max-h-svh w-full max-w-full overflow-hidden">
    <!-- Fill UApp so layouts/pages get a definite height (needed for overflow-y-auto). -->
    <div class="flex h-full min-h-0 w-full max-w-full flex-col overflow-hidden">
      <NuxtLayout>
        <NuxtPage />
      </NuxtLayout>
    </div>
  </UApp>
</template>
