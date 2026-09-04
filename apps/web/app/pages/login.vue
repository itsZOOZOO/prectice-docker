<script setup lang="ts">
definePageMeta({ layout: 'auth' })

const auth = useAuth()
const { api } = useApi()

const username = ref('admin')
const password = ref('admin123')
const loading = ref(false)
const error = ref('')

async function submit() {
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
      body: { username: username.value, password: password.value }
    })
    auth.setSession(data)
    await navigateTo(homePathForViewport())
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Login failed'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="mx-auto flex min-h-screen max-w-md flex-col justify-center px-4 py-10">
    <div class="mb-8">
      <p class="text-4xl font-semibold text-[#0097A7]">Prectice</p>
      <p class="mt-2 text-slate-600">Clinic desk & mobile</p>
    </div>

    <form class="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm" @submit.prevent="submit">
      <UFormField label="Username">
        <UInput v-model="username" autocomplete="username" class="w-full" size="lg" />
      </UFormField>
      <UFormField label="Password">
        <UInput v-model="password" type="password" autocomplete="current-password" class="w-full" size="lg" />
      </UFormField>

      <p v-if="error" class="text-sm text-red-600">{{ error }}</p>

      <UButton type="submit" block size="lg" class="bg-[#0097A7]" :loading="loading">
        Sign in
      </UButton>
    </form>

    <p class="mt-4 text-xs text-slate-500">
      Break-glass: <code>admin / admin123</code> · or your clinic staff login
    </p>
  </div>
</template>
