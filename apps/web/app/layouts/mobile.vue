<script setup lang="ts">
import {
  fetchUnreadActivityCount,
  type ActivityFeedPayload
} from '~/utils/activity'

const route = useRoute()
const { clinicName, hydrate } = useAuth()
hydrate()

const { api } = useApi()
const { isDesktop } = useDeviceHome()
const mismatchAttention = useViewMismatchAttention(isDesktop)
const desktopSwitchClass = computed(() => viewSwitchClass(isDesktop.value, mismatchAttention.value))
const desktopSwitchTitle = computed(() =>
  isDesktop.value
    ? 'Large screen — use desktop'
    : 'Use desktop'
)

const badges = ref({ open_tasks: 0, lab_action_needed: 0, appointments_today: 0 })
const moreOpen = ref(false)
const moreMenuRef = ref<HTMLElement | null>(null)
const activityOpen = ref(false)
const activityCount = ref<number | null>(null)

const tabs = [
  { to: '/dashboard', label: 'Patients', icon: 'i-lucide-users', match: ['/dashboard', '/clients'] },
  { to: '/appointments', label: 'Appts', icon: 'i-lucide-calendar', match: ['/appointments'] },
  { to: '/tasks', label: 'Tasks', icon: 'i-lucide-check-square', match: ['/tasks'] },
  { to: '/treatments', label: 'Treats', icon: 'i-lucide-stethoscope', match: ['/treatments'] },
  { to: '/lab', label: 'Lab', icon: 'i-lucide-flask-conical', match: ['/lab'] }
]

function isActive(tab: (typeof tabs)[number]) {
  return tab.match.some(p => route.path === p || route.path.startsWith(`${p}/`))
}

async function refreshBadges() {
  try {
    const s = await api<{ open_tasks: number, lab_action_needed: number, appointments_today: number }>('/desk/summary')
    badges.value = {
      open_tasks: s.open_tasks || 0,
      lab_action_needed: s.lab_action_needed || 0,
      appointments_today: s.appointments_today || 0
    }
  } catch { /* ignore */ }
}

async function refreshActivityCount() {
  try {
    activityCount.value = await fetchUnreadActivityCount(params =>
      api<ActivityFeedPayload>('/activity', { query: params })
    )
  } catch {
    activityCount.value = null
  }
}

function badgeFor(to: string) {
  if (to === '/appointments') return badges.value.appointments_today
  if (to === '/tasks') return badges.value.open_tasks
  if (to === '/lab') return badges.value.lab_action_needed
  return 0
}

function onDocPointer(e: MouseEvent | TouchEvent) {
  const el = moreMenuRef.value
  if (!el) return
  if (e.target instanceof Node && !el.contains(e.target)) moreOpen.value = false
}

async function openActivityPatient(clientId: number) {
  await navigateTo(`/clients/${clientId}`)
}

onMounted(() => {
  refreshBadges()
  void refreshActivityCount()
  document.addEventListener('mousedown', onDocPointer)
  document.addEventListener('touchstart', onDocPointer)
})
onUnmounted(() => {
  document.removeEventListener('mousedown', onDocPointer)
  document.removeEventListener('touchstart', onDocPointer)
})
watch(() => route.path, () => {
  moreOpen.value = false
  void refreshActivityCount()
})
watch(activityOpen, () => {
  void refreshActivityCount()
})

const showBottomNav = computed(() => !route.path.startsWith('/clients/'))
/** Clinic branding + Use desktop + bell + ⋮ — Patients home only. */
const showShellHeader = computed(() => route.path === '/dashboard')
provide('mobileRefreshBadges', refreshBadges)
</script>

<template>
  <div class="mobile-shell mx-auto max-w-[480px]">
    <header
      v-if="showShellHeader"
      class="flex shrink-0 items-center justify-between gap-2 border-b border-slate-200 bg-white px-4 py-3"
    >
      <div class="min-w-0">
        <p class="truncate text-sm font-semibold text-[#1C2B35]">{{ clinicName || 'Nav Dental' }}</p>
        <p class="text-[11px] text-slate-400">Mobile</p>
      </div>
      <div class="flex items-center gap-1.5">
        <NuxtLink
          to="/desk?view=dashboard"
          :title="desktopSwitchTitle"
          :aria-label="desktopSwitchTitle"
          class="flex h-9 items-center justify-center gap-1.5 rounded-lg border px-2.5 text-xs font-medium transition"
          :class="desktopSwitchClass"
        >
          <span aria-hidden>🖥</span>
          <span class="hidden min-[380px]:inline">Use desktop</span>
        </NuxtLink>
        <div class="relative shrink-0">
          <span
            v-if="activityCount != null && activityCount > 0"
            class="absolute -right-1 -top-1 z-10 flex h-4 min-w-4 items-center justify-center rounded-full bg-[#0097A7] px-1 text-[10px] font-semibold text-white"
          >
            {{ activityCount > 99 ? '99+' : activityCount }}
          </span>
          <button
            type="button"
            class="flex h-9 w-9 items-center justify-center rounded-full bg-[#e0f7fa] text-[#0097A7] transition hover:bg-[#b2ebf2]"
            title="Activity log"
            aria-label="Activity log"
            @click="activityOpen = true"
          >
            <UIcon name="i-lucide-bell" class="h-5 w-5" />
          </button>
        </div>
        <div ref="moreMenuRef" class="relative">
          <button
            type="button"
            class="flex h-9 w-9 items-center justify-center rounded-full bg-slate-100 text-slate-600 transition hover:bg-slate-200"
            title="More"
            aria-label="More"
            :aria-expanded="moreOpen"
            aria-haspopup="menu"
            @click="moreOpen = !moreOpen"
          >
            <UIcon name="i-lucide-ellipsis-vertical" class="h-5 w-5" />
          </button>
          <div
            v-if="moreOpen"
            role="menu"
            class="absolute right-0 top-full z-30 mt-1 w-48 overflow-hidden rounded-xl border border-slate-200 bg-white py-1 shadow-lg"
          >
            <NuxtLink
              to="/settings"
              role="menuitem"
              class="flex w-full items-center gap-2 px-3 py-2.5 text-left text-sm text-slate-700 hover:bg-slate-50"
              @click="moreOpen = false"
            >
              <UIcon name="i-lucide-settings" class="h-4 w-4 text-slate-400" />
              Settings
            </NuxtLink>
          </div>
        </div>
      </div>
    </header>

    <main
      class="min-h-0 flex-1"
      :class="showBottomNav ? 'pb-20' : ''"
    >
      <slot />
    </main>

    <nav
      v-if="showBottomNav"
      class="fixed bottom-0 left-1/2 z-40 w-full max-w-[480px] -translate-x-1/2 border-t border-slate-200 bg-white/95 backdrop-blur"
      style="padding-bottom: max(0.5rem, env(safe-area-inset-bottom))"
    >
      <ul class="grid grid-cols-5 gap-0.5 px-1 pt-2">
        <li v-for="tab in tabs" :key="tab.to">
          <NuxtLink
            :to="tab.to"
            class="relative flex flex-col items-center gap-0.5 rounded-xl px-1 py-1.5 text-[10px] font-semibold"
            :class="isActive(tab) ? 'bg-[#e0f7fa] text-[#0097A7]' : 'text-slate-500'"
          >
            <UIcon :name="tab.icon" class="h-5 w-5" />
            <span>{{ tab.label }}</span>
            <span
              v-if="badgeFor(tab.to) > 0"
              class="absolute right-2 top-0.5 min-w-4 rounded-full bg-[#0097A7] px-1 text-center text-[9px] font-bold text-white"
            >
              {{ badgeFor(tab.to) > 99 ? '99+' : badgeFor(tab.to) }}
            </span>
          </NuxtLink>
        </li>
      </ul>
    </nav>

    <DeskActivityLogSheet
      v-model:open="activityOpen"
      @read-state-change="refreshActivityCount"
      @open-patient="openActivityPatient"
    />
  </div>
</template>
