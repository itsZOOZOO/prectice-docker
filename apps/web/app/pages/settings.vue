<script setup lang="ts">
definePageMeta({ layout: 'mobile' })

const { user, clinicName, logout, hydrate } = useAuth()
hydrate()

const accountOpen = ref(false)
const loggingOut = ref(false)
const accountRef = ref<HTMLElement | null>(null)

const initials = computed(() => {
  const name = user.value?.full_name || user.value?.username || '?'
  return name
    .split(/\s+/)
    .filter(Boolean)
    .map(w => w.charAt(0))
    .slice(0, 2)
    .join('')
    .toUpperCase()
})

function roleLabel(role: string | undefined) {
  if (!role) return ''
  if (role === 'admin') return 'Administrator'
  if (role === 'doctor') return 'Doctor'
  if (role === 'staff') return 'Staff'
  return role.charAt(0).toUpperCase() + role.slice(1)
}

function onDocPointer(e: MouseEvent | TouchEvent) {
  const el = accountRef.value
  if (!el) return
  if (e.target instanceof Node && !el.contains(e.target)) accountOpen.value = false
}

async function handleLogout() {
  loggingOut.value = true
  try {
    await logout()
  } finally {
    loggingOut.value = false
  }
}

onMounted(() => {
  document.addEventListener('mousedown', onDocPointer)
  document.addEventListener('touchstart', onDocPointer)
})
onUnmounted(() => {
  document.removeEventListener('mousedown', onDocPointer)
  document.removeEventListener('touchstart', onDocPointer)
})
</script>

<template>
  <div class="h-full min-h-0 overflow-y-auto overscroll-y-contain px-4 py-4 [-webkit-overflow-scrolling:touch]">
    <div class="mb-4">
      <h1 class="text-lg font-semibold text-[#1C2B35]">Settings</h1>
      <p class="text-xs text-slate-500">Account & preferences</p>
    </div>

    <div class="space-y-3">
      <div class="rounded-xl border border-slate-200 bg-white p-4">
        <div class="flex items-center gap-3">
          <div class="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-[#e0f7fa] text-base font-semibold text-[#0097A7]">
            {{ initials || '?' }}
          </div>
          <div class="min-w-0">
            <p class="truncate text-base font-semibold text-[#1C2B35]">{{ user?.full_name || '—' }}</p>
            <p class="truncate text-sm text-slate-500">@{{ user?.username }}</p>
            <p class="mt-0.5 text-xs text-[#0097A7]">{{ roleLabel(user?.role) }}</p>
          </div>
        </div>
      </div>

      <div ref="accountRef" class="relative">
        <button
          type="button"
          class="flex w-full items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3.5 text-left transition hover:bg-slate-50"
          :aria-expanded="accountOpen"
          aria-haspopup="menu"
          @click="accountOpen = !accountOpen"
        >
          <div class="flex items-center gap-3">
            <span class="flex h-9 w-9 items-center justify-center rounded-full bg-slate-100 text-lg">👤</span>
            <div>
              <p class="text-sm font-semibold text-[#1C2B35]">Account</p>
              <p class="text-xs text-slate-500">Session & sign out</p>
            </div>
          </div>
          <span
            class="text-slate-400 transition"
            :style="{ transform: accountOpen ? 'rotate(180deg)' : 'rotate(0deg)' }"
          >
            ▾
          </span>
        </button>

        <div
          v-if="accountOpen"
          role="menu"
          class="absolute left-0 right-0 z-20 mt-1 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-lg"
        >
          <div class="border-b border-slate-100 px-4 py-3">
            <p class="text-xs text-slate-400">Signed in as</p>
            <p class="text-sm font-medium text-[#1C2B35]">{{ user?.full_name }}</p>
            <p class="text-xs text-slate-500">{{ clinicName }}</p>
          </div>
          <button
            type="button"
            role="menuitem"
            class="flex w-full items-center gap-2 px-4 py-3.5 text-left text-sm font-medium text-red-600 transition hover:bg-red-50 disabled:opacity-60"
            :disabled="loggingOut"
            @click="handleLogout"
          >
            <span class="text-base">⎋</span>
            {{ loggingOut ? 'Signing out…' : 'Sign out' }}
          </button>
        </div>
      </div>

      <p class="pt-2 text-center text-[11px] text-slate-400">
        Clinic settings (WhatsApp, labs) ·
        <NuxtLink to="/desk?view=settings" class="text-[#0097A7]">Open desk settings</NuxtLink>
      </p>
    </div>
  </div>
</template>
