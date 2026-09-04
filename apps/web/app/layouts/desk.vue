<script setup lang="ts">
const { clinicName, user, hydrate, logout } = useAuth()
hydrate()

const { view, title, setView, openPatient, patientId } = useDeskUrl()
const { api } = useApi()

const collapsed = ref(false)
const search = ref('')
const searchOpen = ref(false)
const searching = ref(false)
const searchResults = ref<{ client_id: number, name: string, number: string | null, place: string | null }[]>([])
const addOpen = ref(false)
const bookOpen = ref(false)
const bookPatient = ref<{ id: number, name: string } | null>(null)
const badges = ref({ checked_in: 0, appointments_today: 0, open_tasks: 0 })
const searchTimer = ref<ReturnType<typeof setTimeout> | null>(null)
const searchInput = ref<HTMLInputElement | null>(null)
const clinicInitial = computed(() => String(clinicName.value || 'P').charAt(0))

const nav = [
  { key: 'dashboard' as const, label: 'Dashboard', icon: '▦' },
  { key: 'patients' as const, label: 'Patients', icon: '👥' },
  { key: 'calendar' as const, label: 'Calendar', icon: '📅' },
  { key: 'tasks' as const, label: 'Tasks', icon: '📋' },
  { key: 'settings' as const, label: 'Settings', icon: '⚙' }
]

onMounted(() => {
  try {
    collapsed.value = localStorage.getItem('desk-sidebar-collapsed') === 'true'
  } catch { /* ignore */ }
  refreshBadges()
})

function toggleSidebar() {
  collapsed.value = !collapsed.value
  try {
    localStorage.setItem('desk-sidebar-collapsed', String(collapsed.value))
  } catch { /* ignore */ }
}

async function refreshBadges() {
  try {
    const s = await api<{
      checked_in: number
      appointments_today: number
      open_tasks: number
    }>('/desk/summary')
    badges.value = {
      checked_in: s.checked_in,
      appointments_today: s.appointments_today,
      open_tasks: s.open_tasks
    }
  } catch { /* ignore */ }
}

function onSearchInput() {
  searchOpen.value = true
  if (searchTimer.value) clearTimeout(searchTimer.value)
  if (search.value.trim().length < 2) {
    searchResults.value = []
    return
  }
  searchTimer.value = setTimeout(async () => {
    searching.value = true
    try {
      const data = await api<{ items: typeof searchResults.value }>('/clients', {
        query: { q: search.value.trim(), limit: 12 }
      })
      searchResults.value = data.items
    } finally {
      searching.value = false
    }
  }, 220)
}

async function pickSearch(id: number) {
  search.value = ''
  searchOpen.value = false
  await openPatient(id)
}

async function openHeaderBook() {
  bookPatient.value = null
  if (patientId.value) {
    try {
      const c = await api<{ client_id: number, name: string }>(`/clients/${patientId.value}`)
      bookPatient.value = { id: c.client_id, name: c.name }
    } catch { /* ignore */ }
  }
  bookOpen.value = true
}

function badgeFor(key: string) {
  if (key === 'dashboard') return badges.value.checked_in
  if (key === 'calendar') return badges.value.appointments_today
  if (key === 'tasks') return badges.value.open_tasks
  return 0
}

function onKeydown(e: KeyboardEvent) {
  const mod = e.metaKey || e.ctrlKey
  if (mod && e.key.toLowerCase() === 'f') {
    e.preventDefault()
    searchInput.value?.focus()
  }
  if (mod && e.key.toLowerCase() === 'n') {
    e.preventDefault()
    addOpen.value = true
  }
  if (mod && e.key.toLowerCase() === 'b') {
    e.preventDefault()
    openHeaderBook()
  }
  if (mod && e.key.toLowerCase() === 'l') {
    e.preventDefault()
    setView('calendar')
  }
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))

provide('deskRefreshBadges', refreshBadges)
provide('deskOpenBook', openHeaderBook)
provide('deskOpenAddPatient', () => { addOpen.value = true })

useSeoMeta({ title: title })
</script>

<template>
  <div class="relative h-svh max-h-svh w-full max-w-full overflow-hidden">
    <div
      class="desk-shell"
      :style="{ '--desk-aside-w': collapsed ? '68px' : '240px' }"
    >
      <aside class="desk-shell__aside">
        <div class="border-b border-slate-100" :class="collapsed ? 'px-2 py-3' : 'px-4 py-4'">
          <div class="flex items-start gap-2" :class="collapsed ? 'flex-col items-center' : 'justify-between'">
            <div v-if="!collapsed" class="min-w-0 flex-1">
              <p class="truncate text-[11px] uppercase tracking-wider text-slate-400">{{ clinicName }}</p>
              <p class="text-base font-semibold text-[#1C2B35]">Desktop App</p>
            </div>
            <p v-else class="truncate text-center text-[11px] font-semibold uppercase tracking-wide text-slate-400">
              {{ clinicInitial }}
            </p>
            <button
              type="button"
              class="shrink-0 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50"
              :class="collapsed ? 'px-2 py-1.5 text-base' : 'px-2 py-1 text-sm'"
              @click="toggleSidebar"
            >
              {{ collapsed ? '»' : '«' }}
            </button>
          </div>
        </div>

        <nav class="min-h-0 flex-1 space-y-1 overflow-y-auto" :class="collapsed ? 'p-2' : 'p-3'">
          <button
            v-for="item in nav"
            :key="item.key"
            type="button"
            class="relative flex w-full items-center rounded-lg text-left text-sm font-medium transition"
            :class="[
              collapsed ? 'justify-center px-2 py-2.5' : 'gap-3 px-3 py-2.5',
              view === item.key ? 'bg-[#0097A7]/10 text-[#0097A7]' : 'text-slate-600 hover:bg-slate-50'
            ]"
            :title="item.label"
            @click="setView(item.key)"
          >
            <span class="text-base">{{ item.icon }}</span>
            <span v-if="!collapsed" class="flex-1">{{ item.label }}</span>
            <span
              v-if="badgeFor(item.key) > 0"
              class="flex h-5 min-w-5 items-center justify-center rounded-full bg-[#0097A7] px-1 text-[10px] font-semibold text-white"
              :class="collapsed ? 'absolute -right-0.5 -top-0.5' : ''"
            >
              {{ badgeFor(item.key) > 99 ? '99+' : badgeFor(item.key) }}
            </span>
          </button>
        </nav>

        <div class="border-t border-slate-100" :class="collapsed ? 'p-2' : 'p-4'">
          <button
            type="button"
            class="flex w-full items-center justify-center rounded-lg border border-slate-200 text-sm text-slate-600 hover:bg-slate-50"
            :class="collapsed ? 'px-2 py-2' : 'gap-2 px-3 py-2'"
            @click="logout()"
          >
            <span>{{ collapsed ? '⎋' : 'Sign out' }}</span>
          </button>
        </div>
      </aside>

      <div class="desk-shell__main">
        <header class="flex shrink-0 items-center gap-3 border-b border-slate-200 bg-white px-5 py-3">
          <h1 class="shrink-0 text-lg font-semibold text-[#1C2B35]">{{ title }}</h1>
          <div class="ml-auto flex min-w-0 items-center gap-2">
            <div class="relative w-full min-w-0 max-w-md sm:w-[320px]">
              <div class="flex h-9 items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3">
                <span class="text-slate-400">🔍</span>
                <input
                  ref="searchInput"
                  v-model="search"
                  type="search"
                  placeholder="Search name, phone, area…"
                  class="min-w-0 flex-1 border-none bg-transparent text-sm outline-none placeholder:text-slate-400"
                  @input="onSearchInput"
                  @focus="searchOpen = true"
                >
              </div>
              <div
                v-if="searchOpen && search.trim().length >= 2"
                class="absolute left-0 right-0 top-[calc(100%+6px)] z-30 max-h-72 overflow-y-auto rounded-lg border border-slate-200 bg-white shadow-lg"
              >
                <p v-if="searching" class="px-3 py-2.5 text-xs text-slate-400">Searching…</p>
                <p v-else-if="!searchResults.length" class="px-3 py-2.5 text-xs text-slate-400">No patients found</p>
                <button
                  v-for="row in searchResults"
                  :key="row.client_id"
                  type="button"
                  class="flex w-full items-center gap-2 border-b border-slate-50 px-3 py-2 text-left last:border-b-0 hover:bg-slate-50"
                  @click="pickSearch(row.client_id)"
                >
                  <div class="flex h-8 w-8 items-center justify-center rounded-full bg-[#e0f7fa] text-xs font-semibold text-[#0097A7]">
                    {{ row.name.charAt(0) }}
                  </div>
                  <div class="min-w-0">
                    <p class="truncate text-sm font-medium">{{ row.name }}</p>
                    <p class="truncate text-xs text-slate-500">{{ row.number || '—' }}<span v-if="row.place"> · {{ row.place }}</span></p>
                  </div>
                </button>
              </div>
            </div>
            <button
              type="button"
              class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-[#e0f7fa] text-[#0097A7] hover:bg-[#b2ebf2]"
              title="Add patient (Ctrl+N)"
              @click="addOpen = true"
            >
              <UIcon name="i-lucide-user-plus" class="h-[18px] w-[18px]" />
            </button>
            <button
              type="button"
              class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-[#e0f7fa] text-[#0097A7] hover:bg-[#b2ebf2]"
              title="Book appointment (Ctrl+B)"
              @click="openHeaderBook"
            >
              <UIcon name="i-lucide-calendar-plus" class="h-[18px] w-[18px]" />
            </button>
          </div>
        </header>

        <main class="desk-shell__content">
          <slot />
        </main>
      </div>
    </div>

    <DeskAddPatientModal v-model:open="addOpen" @created="(id) => { refreshBadges(); openPatient(id) }" />
    <DeskBookModal
      v-model:open="bookOpen"
      :client-id="bookPatient?.id"
      :client-name="bookPatient?.name"
      @booked="refreshBadges"
    />
  </div>
</template>
