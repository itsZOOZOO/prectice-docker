<script setup lang="ts">
useHead({
  titleTemplate: (title) => (title ? `${title} · Nav Dental` : 'Nav Dental'),
  meta: [
    { name: 'viewport', content: 'width=device-width, initial-scale=1, viewport-fit=cover' },
    { name: 'theme-color', content: '#0097A7' },
    { name: 'mobile-web-app-capable', content: 'yes' },
    { name: 'apple-mobile-web-app-capable', content: 'yes' },
    { name: 'apple-mobile-web-app-status-bar-style', content: 'default' },
    { name: 'apple-mobile-web-app-title', content: 'Nav Dental' }
  ],
  link: [
    { rel: 'manifest', href: '/manifest.webmanifest' },
    { rel: 'icon', type: 'image/png', sizes: '32x32', href: '/icons/favicon-32.png' },
    { rel: 'icon', type: 'image/png', sizes: '16x16', href: '/icons/favicon-16.png' },
    { rel: 'apple-touch-icon', href: '/icons/apple-touch-icon.png' }
  ],
  htmlAttrs: { lang: 'en' }
})

useSeoMeta({
  title: 'Nav Dental',
  description: 'Clinic desk & mobile'
})
</script>

<template>
  <UApp class="!block h-full max-h-full w-full max-w-full overflow-hidden">
    <!-- Constrained flex column so layouts get a real height for overflow-y-auto children. -->
    <div class="flex h-full min-h-0 w-full max-w-full flex-col overflow-hidden">
      <div class="app-layout-host relative min-h-0 w-full flex-1 overflow-hidden">
        <NuxtLayout>
          <NuxtPage />
        </NuxtLayout>
      </div>
      <ClientOnly>
        <PwaInstallPrompt />
      </ClientOnly>
    </div>
  </UApp>
</template>
