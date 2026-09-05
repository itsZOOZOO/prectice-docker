export default defineNuxtConfig({
  modules: [
    '@nuxt/eslint',
    '@nuxt/ui'
  ],

  devtools: {
    enabled: true
  },

  css: ['~/assets/css/main.css'],

  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://127.0.0.1:8000/api'
    }
  },

  // Vercel sets VERCEL=1 during builds; local/Docker keep default Nitro node preset.
  nitro: {
    ...(process.env.VERCEL ? { preset: 'vercel' as const } : {})
  },

  colorMode: {
    preference: 'light'
  },

  // Bundle Lucide locally so icons work on phone / offline (no Iconify CDN fetch).
  icon: {
    mode: 'svg',
    serverBundle: 'local',
    clientBundle: {
      scan: true,
      sizeLimitKb: 512,
      // Hard-include mobile + timeline icons (scan can miss some script usages).
      icons: [
        'lucide:users',
        'lucide:calendar',
        'lucide:check-square',
        'lucide:flask-conical',
        'lucide:ellipsis-vertical',
        'lucide:settings',
        'lucide:arrow-left',
        'lucide:home',
        'lucide:phone',
        'lucide:message-circle',
        'lucide:pill',
        'lucide:banknote',
        'lucide:stethoscope',
        'lucide:paperclip',
        'lucide:send',
        'lucide:clock',
        'lucide:pencil',
        'lucide:trash-2',
        'lucide:chevron-down',
        'lucide:x',
        'lucide:plus',
        'lucide:user-plus',
        'lucide:calendar-plus',
        'lucide:chevron-left',
        'lucide:chevron-right'
      ]
    }
  },

  fonts: {
    families: [
      { name: 'Source Sans 3', provider: 'google' }
    ]
  },

  compatibilityDate: '2026-06-30',

  eslint: {
    config: {
      stylistic: {
        commaDangle: 'never',
        braceStyle: '1tbs'
      }
    }
  }
})
