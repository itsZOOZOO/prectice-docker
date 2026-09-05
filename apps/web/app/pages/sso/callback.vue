<script setup lang="ts">
import {
  safePostLoginPath,
  takeSsoRememberPref
} from '~/utils/sso'
import { homePathForViewport } from '~/utils/deviceHome'

definePageMeta({
  layout: 'auth',
  // Auth portal often registers the legacy .php path
  alias: ['/sso/callback.php']
})

const auth = useAuth()
const { api } = useApi()
const route = useRoute()

const status = ref('Completing Google sign-in…')
const error = ref('')

onMounted(async () => {
  auth.hydrate()
  if (auth.isLoggedIn.value) {
    await navigateTo(homePathForViewport())
    return
  }

  const code = typeof route.query.code === 'string' ? route.query.code.trim() : ''
  if (!code) {
    await navigateTo({ path: '/login', query: { error: 'SSO sign-in was cancelled or missing a code.' } })
    return
  }

  const remember = takeSsoRememberPref()
  const fallback = homePathForViewport()

  try {
    const data = await api<{
      access_token: string
      user: {
        user_id: number
        clinic_id: number
        username: string
        full_name: string
        role: string
        email?: string | null
      }
      clinic_name: string
      final_redirect?: string
    }>('/auth/sso/exchange', {
      method: 'POST',
      body: { code, remember },
      authRedirect: false
    })
    auth.setSession(data)
    const target = safePostLoginPath(data.final_redirect, fallback)
    status.value = 'Signed in — redirecting…'
    await navigateTo(target)
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : 'SSO sign-in failed'
    error.value = message
    await navigateTo({ path: '/login', query: { error: message } })
  }
})
</script>

<template>
  <div class="mx-auto flex min-h-screen max-w-md flex-col justify-center px-4 py-10">
    <p class="text-4xl font-semibold text-[#0097A7]">
      Prectice
    </p>
    <p class="mt-6 text-slate-600">
      {{ error || status }}
    </p>
  </div>
</template>
