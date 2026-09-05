export default defineNuxtConfig({
  compatibilityDate: '2025-01-01',
  devtools: { enabled: false },
  css: ['~/assets/css/plan.css'],
  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://127.0.0.1:8000/api'
    }
  },
  app: {
    head: {
      title: 'Your treatment plan',
      meta: [
        { name: 'robots', content: 'noindex, nofollow' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1, viewport-fit=cover' }
      ]
    }
  }
})
