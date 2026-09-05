<script setup lang="ts">
import {
  buildSsoLoginUrl,
  safePostLoginPath,
  storeSsoRememberPref
} from '~/utils/sso'
import { homePathForViewport } from '~/utils/deviceHome'

definePageMeta({ layout: 'auth' })

const auth = useAuth()
const { api } = useApi()
const route = useRoute()

const username = ref('')
const password = ref('')
const remember = ref(false)
const showPassword = ref(false)
const loading = ref(false)
const ssoLoading = ref(false)
const error = ref('')

onMounted(() => {
  auth.hydrate()
  if (auth.isLoggedIn.value) {
    void navigateTo(homePathForViewport())
    return
  }
  const q = route.query.error
  if (typeof q === 'string' && q.trim()) {
    error.value = q.trim()
  }
})

async function submitPassword() {
  loading.value = true
  error.value = ''
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
    }>('/auth/login', {
      method: 'POST',
      body: {
        username: username.value,
        password: password.value,
        remember: remember.value
      }
    })
    auth.setSession(data)
    await navigateTo(homePathForViewport())
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Login failed'
  } finally {
    loading.value = false
  }
}

function startSso() {
  error.value = ''
  ssoLoading.value = true
  storeSsoRememberPref(remember.value)
  const redirect = safePostLoginPath(
    typeof route.query.redirect === 'string' ? route.query.redirect : homePathForViewport()
  )
  window.location.href = buildSsoLoginUrl(redirect)
}
</script>

<template>
  <div class="mx-auto flex min-h-screen max-w-md flex-col justify-center px-4 py-10">
    <div class="mb-8">
      <p class="text-4xl font-semibold text-[#0097A7]">
        Prectice
      </p>
      <p class="mt-2 text-slate-600">
        Clinic desk & mobile
      </p>
    </div>

    <div class="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <p
        v-if="error"
        class="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700"
      >
        {{ error }}
      </p>

      <UButton
        block
        size="lg"
        color="neutral"
        variant="outline"
        :loading="ssoLoading"
        class="justify-center gap-2"
        @click="startSso"
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 48 48"
          aria-hidden="true"
        >
          <path
            fill="#FFC107"
            d="M43.611 20.083H42V20H24v8h11.303C33.654 32.657 29.083 36 24 36c-5.522 0-10-4.478-10-10s4.478-10 10-10c2.837 0 5.352 1.174 7.196 3.064l5.657-5.657C34.046 10.846 29.268 9 24 9 14.059 9 6 17.059 6 27s8.059 18 18 18 18-8.059 18-18c0-1.341-.138-2.65-.389-3.917z"
          />
          <path
            fill="#FF3D00"
            d="M6 27c0-1.657.276-3.25.783-4.741l8.564 6.548C14.655 30.657 19.026 33 24 33c2.837 0 5.352 1.174 7.196 3.064l5.657 5.657C34.046 41.154 29.268 43 24 43 14.059 43 6 34.941 6 27z"
          />
          <path
            fill="#4CAF50"
            d="M42.459 15.917l-8.564 6.548C32.345 19.343 28.374 17 24 17c-2.837 0-5.352 1.174-7.196 3.064l-5.657-5.657C13.954 10.846 18.732 9 24 9c5.268 0 10.046 1.846 13.459 4.917z"
          />
          <path
            fill="#1976D2"
            d="M43.611 20.083H42V20H24v8h11.303a12.04 12.04 0 0 1-4.087 5.571l.003-.002 8.564-6.548C42.654 25.657 43 26.309 43 27c0 .691-.346 1.343-.389 1.917z"
          />
        </svg>
        Sign in with Google
      </UButton>

      <label class="flex cursor-pointer items-center gap-2 text-sm text-slate-600">
        <input
          v-model="remember"
          type="checkbox"
          class="size-4 rounded border-slate-300 text-[#0097A7] focus:ring-[#0097A7]"
        >
        Remember me for 30 days
      </label>

      <div class="flex items-center gap-3 py-1">
        <div class="h-px flex-1 bg-slate-200" />
        <span class="text-xs text-slate-400">or</span>
        <div class="h-px flex-1 bg-slate-200" />
      </div>

      <button
        type="button"
        class="w-full text-center text-sm font-medium text-slate-600 hover:text-[#0097A7]"
        @click="showPassword = !showPassword"
      >
        {{ showPassword ? 'Hide password login' : 'Sign in with password' }}
      </button>

      <form
        v-if="showPassword"
        class="space-y-4"
        @submit.prevent="submitPassword"
      >
        <UFormField label="Username">
          <UInput
            v-model="username"
            autocomplete="username"
            class="w-full"
            size="lg"
          />
        </UFormField>
        <UFormField label="Password">
          <UInput
            v-model="password"
            type="password"
            autocomplete="current-password"
            class="w-full"
            size="lg"
          />
        </UFormField>

        <UButton
          type="submit"
          block
          size="lg"
          class="bg-[#0097A7]"
          :loading="loading"
        >
          Sign in
        </UButton>
      </form>
    </div>
  </div>
</template>
