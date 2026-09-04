<script setup lang="ts">
definePageMeta({ layout: 'mobile' })

type ClientRow = {
  client_id: number
  name: string
  number: string | null
  place: string | null
  status: string
  check_in_status: boolean
  profile_photo_url?: string | null
}

const { api } = useApi()
const toast = useToast()
const addOpen = ref(false)

const tab = ref<'checked_in' | 'all'>('checked_in')
const q = ref('')
const list = ref<ClientRow[]>([])
const loading = ref(false)
const toggling = ref<number | null>(null)

const searching = computed(() => q.value.trim().length > 0)

async function load() {
  loading.value = true
  try {
    // Search is always global — ignore Checked in / All tabs
    if (searching.value) {
      const data = await api<{ items: ClientRow[] }>('/clients', {
        query: { q: q.value.trim(), limit: 80 }
      })
      list.value = data.items
    } else if (tab.value === 'checked_in') {
      const data = await api<{ items: ClientRow[] }>('/clients', {
        query: { checked_in: true, limit: 80 }
      })
      list.value = data.items
    } else {
      const data = await api<{ items: ClientRow[] }>('/clients', {
        query: { limit: 80 }
      })
      list.value = data.items
    }
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to load', color: 'error' })
  } finally {
    loading.value = false
  }
}

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(q, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { void load() }, q.value.trim() ? 220 : 0)
})
watch(tab, () => {
  if (!searching.value) void load()
})

onMounted(load)

function clearSearch() {
  q.value = ''
}

async function toggleCheckin(c: ClientRow, ev: Event) {
  ev.preventDefault()
  ev.stopPropagation()
  toggling.value = c.client_id
  try {
    const path = c.check_in_status ? 'check-out' : 'check-in'
    await api(`/clients/${c.client_id}/${path}`, { method: 'POST' })
    await load()
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
  } finally {
    toggling.value = null
  }
}

const emptyMessage = computed(() => {
  if (searching.value) return 'No patients match your search.'
  if (tab.value === 'checked_in') return 'Nobody checked in.'
  return 'No patients found.'
})
</script>

<template>
  <div class="relative flex h-full min-h-0 flex-col">
    <div class="shrink-0 space-y-3 border-b border-slate-200 bg-white px-4 py-3">
      <div class="flex items-center justify-between gap-2">
        <h1 class="text-lg font-semibold text-[#1C2B35]">Patients</h1>
        <span class="text-xs text-slate-400">{{ list.length }}</span>
      </div>
      <div class="relative">
        <input
          v-model="q"
          type="search"
          placeholder="Search all patients…"
          class="h-10 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 pr-10 text-sm outline-none focus:border-[#0097A7] focus:bg-white"
        >
        <button
          v-if="searching"
          type="button"
          class="absolute right-2 top-1/2 -translate-y-1/2 rounded-md px-1.5 py-0.5 text-xs text-slate-500 hover:bg-slate-200"
          aria-label="Clear search"
          @click="clearSearch"
        >
          ✕
        </button>
      </div>

      <p v-if="searching" class="text-[11px] font-medium text-[#0097A7]">
        Searching all patients
      </p>
      <div
        v-else
        class="grid grid-cols-2 gap-2 rounded-xl bg-slate-100 p-1"
      >
        <button
          type="button"
          class="rounded-lg py-2 text-xs font-semibold"
          :class="tab === 'checked_in' ? 'bg-white text-[#0097A7] shadow-sm' : 'text-slate-500'"
          @click="tab = 'checked_in'"
        >
          Checked in
        </button>
        <button
          type="button"
          class="rounded-lg py-2 text-xs font-semibold"
          :class="tab === 'all' ? 'bg-white text-[#0097A7] shadow-sm' : 'text-slate-500'"
          @click="tab = 'all'"
        >
          All patients
        </button>
      </div>
    </div>

    <div class="min-h-0 flex-1 overflow-y-auto px-3 py-3 pb-24">
      <p v-if="loading" class="py-10 text-center text-sm text-slate-400">Loading…</p>
      <ul v-else class="space-y-2">
        <li v-for="c in list" :key="c.client_id">
          <div class="flex items-stretch gap-2 rounded-2xl border border-slate-200 bg-white p-2 shadow-sm">
            <NuxtLink
              :to="`/clients/${c.client_id}`"
              class="flex min-w-0 flex-1 items-center gap-3 rounded-xl px-1 py-1 active:bg-slate-50"
            >
              <div class="flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-full bg-[#e0f7fa] text-sm font-semibold text-[#0097A7]">
                <img
                  v-if="c.profile_photo_url"
                  :src="c.profile_photo_url"
                  :alt="c.name"
                  class="h-full w-full object-cover"
                >
                <span v-else>{{ c.name.charAt(0) }}</span>
              </div>
              <div class="min-w-0 flex-1">
                <p class="truncate text-sm font-semibold text-[#1C2B35]">{{ c.name }}</p>
                <p class="truncate text-xs text-slate-500">
                  {{ c.number || 'No phone' }}
                  <span v-if="c.place"> · {{ c.place }}</span>
                </p>
              </div>
            </NuxtLink>
            <button
              type="button"
              class="flex min-h-[3.25rem] w-[4.5rem] shrink-0 flex-col items-center justify-center rounded-xl px-1 text-white disabled:opacity-60"
              :class="c.check_in_status ? 'bg-red-500 active:bg-red-600' : 'bg-emerald-600 active:bg-emerald-700'"
              :disabled="toggling === c.client_id"
              @click="toggleCheckin(c, $event)"
            >
              <span class="text-[10px] font-semibold uppercase tracking-wide opacity-90">Check</span>
              <span class="text-base font-bold leading-none">
                {{ c.check_in_status ? 'out' : 'in' }}
              </span>
            </button>
          </div>
        </li>
        <li v-if="!list.length" class="rounded-2xl border border-dashed border-slate-300 px-4 py-12 text-center text-sm text-slate-400">
          {{ emptyMessage }}
        </li>
      </ul>
    </div>

    <button
      type="button"
      class="absolute bottom-6 right-4 z-30 flex h-14 w-14 items-center justify-center rounded-full bg-[#0097A7] text-2xl text-white shadow-lg"
      title="Add patient"
      @click="addOpen = true"
    >
      +
    </button>

    <DeskAddPatientModal v-model:open="addOpen" @created="load" />
  </div>
</template>
