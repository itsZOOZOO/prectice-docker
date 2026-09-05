<script setup lang="ts">
import { formatInrAmount, formatLastPaymentRelative } from '~/utils/lastPayment'

definePageMeta({ layout: 'mobile' })

type ClientRow = {
  client_id: number
  name: string
  number: string | null
  place: string | null
  status: string
  check_in_status: boolean
  profile_photo_url?: string | null
  pending_bill_id?: number
  pending_amount?: number
  pending_bill_total?: number | null
  pending_total_paid?: number
  last_payment_amount?: number | null
  last_payment_mode?: string | null
  last_payment_at?: string | null
  last_payment_bill_total?: number | null
}

type DashboardFilter = {
  filter_id: number
  name: string
  show_on_dashboard: boolean
  sort_order: number
}

type DashTab = 'checked_in' | 'all' | `filter:${number}`

const { api } = useApi()
const toast = useToast()
const addOpen = ref(false)

const tab = ref<DashTab>('checked_in')
const dashboardFilters = ref<DashboardFilter[]>([])
const q = ref('')
const list = ref<ClientRow[]>([])
const loading = ref(false)
const toggling = ref<number | null>(null)

const collectOpen = ref(false)
const collectBillId = ref<number | null>(null)
const collectAmountDue = ref(0)
const collectBillTotal = ref(0)
const collectTotalPaid = ref(0)
const collectClientName = ref('')

const searching = computed(() => q.value.trim().length > 0)

const activeFilterId = computed(() => {
  if (typeof tab.value !== 'string' || !tab.value.startsWith('filter:')) return null
  const n = Number(tab.value.slice('filter:'.length))
  return Number.isFinite(n) && n > 0 ? n : null
})

function hasPending(c: ClientRow) {
  return (c.pending_bill_id || 0) > 0 && (c.pending_amount || 0) > 0
}

function hasLastPayment(c: ClientRow) {
  return (c.last_payment_amount || 0) > 0 && !!c.last_payment_at
}

function lastPaymentMeta(c: ClientRow) {
  if (!c.last_payment_at) return null
  return formatLastPaymentRelative(c.last_payment_at)
}

async function loadDashboardFilters() {
  try {
    const data = await api<{ filters: DashboardFilter[] }>('/client-filters/dashboard')
    dashboardFilters.value = data.filters ?? []
  } catch {
    dashboardFilters.value = []
  }
}

async function load() {
  loading.value = true
  try {
    // Search is always global — ignore Checked in / All / filter tabs
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
    } else if (activeFilterId.value != null) {
      const data = await api<{ items: ClientRow[] }>('/clients', {
        query: { filter_id: activeFilterId.value, limit: 80 }
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

onMounted(async () => {
  await loadDashboardFilters()
  await load()
})

function clearSearch() {
  q.value = ''
}

function setTab(next: DashTab) {
  tab.value = next
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

function openCollect(c: ClientRow, ev: Event) {
  ev.preventDefault()
  ev.stopPropagation()
  if (!hasPending(c)) return
  collectBillId.value = c.pending_bill_id || null
  collectAmountDue.value = Number(c.pending_amount || 0)
  collectBillTotal.value = Number(c.pending_bill_total || c.pending_amount || 0)
  collectTotalPaid.value = Number(c.pending_total_paid || 0)
  collectClientName.value = c.name
  collectOpen.value = true
}

const emptyMessage = computed(() => {
  if (searching.value) return 'No patients match your search.'
  if (tab.value === 'checked_in') return 'Nobody checked in.'
  if (activeFilterId.value != null) return 'No patients in this list.'
  return 'No patients found.'
})

const showCollectColumn = computed(
  () => searching.value || tab.value === 'checked_in'
)

const tabCount = computed(() => 2 + dashboardFilters.value.length)
</script>

<template>
  <div class="relative flex h-full min-h-0 flex-col">
    <div class="shrink-0 space-y-3 border-b border-slate-200 bg-white px-4 py-3">
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
        class="gap-1 rounded-xl bg-slate-100 p-1"
        :class="tabCount <= 2 ? 'grid grid-cols-2' : 'flex overflow-x-auto'"
      >
        <button
          type="button"
          class="shrink-0 rounded-lg px-3 py-2 text-xs font-semibold whitespace-nowrap"
          :class="tab === 'checked_in' ? 'bg-white text-[#0097A7] shadow-sm' : 'text-slate-500'"
          @click="setTab('checked_in')"
        >
          Checked in
        </button>
        <button
          type="button"
          class="shrink-0 rounded-lg px-3 py-2 text-xs font-semibold whitespace-nowrap"
          :class="tab === 'all' ? 'bg-white text-[#0097A7] shadow-sm' : 'text-slate-500'"
          @click="setTab('all')"
        >
          All
        </button>
        <button
          v-for="f in dashboardFilters"
          :key="f.filter_id"
          type="button"
          class="shrink-0 rounded-lg px-3 py-2 text-xs font-semibold whitespace-nowrap"
          :class="tab === `filter:${f.filter_id}`
            ? 'bg-white text-[#0097A7] shadow-sm'
            : 'text-slate-500'"
          @click="setTab(`filter:${f.filter_id}`)"
        >
          {{ f.name }}
        </button>
      </div>
    </div>

    <div class="min-h-0 flex-1 overflow-y-auto px-3 py-3 pb-24">
      <p v-if="loading" class="py-10 text-center text-sm text-slate-400">Loading…</p>
      <ul v-else class="space-y-2">
        <li v-for="c in list" :key="c.client_id">
          <div class="rounded-2xl border border-slate-200 bg-white p-2 shadow-sm">
            <div class="flex items-stretch gap-2">
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

              <div class="flex shrink-0 items-stretch gap-1.5">
                <button
                  v-if="showCollectColumn && c.check_in_status"
                  type="button"
                  class="flex min-h-[3.25rem] min-w-[4.25rem] flex-col items-center justify-center rounded-xl px-1.5 text-white disabled:cursor-not-allowed"
                  :class="hasPending(c) ? 'bg-red-600 active:bg-red-700' : 'bg-slate-300'"
                  :disabled="!hasPending(c)"
                  :title="hasPending(c) ? 'Collect payment' : 'No pending bill'"
                  @click="openCollect(c, $event)"
                >
                  <span class="text-[10px] font-semibold uppercase tracking-wide opacity-90">Collect</span>
                  <span
                    v-if="hasPending(c)"
                    class="text-sm font-bold leading-none"
                  >
                    {{ formatInrAmount(c.pending_amount || 0) }}
                  </span>
                  <span
                    v-else
                    class="text-sm font-bold leading-none line-through opacity-80"
                  >₹</span>
                </button>

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
            </div>

            <div
              v-if="showCollectColumn && c.check_in_status && hasLastPayment(c) && lastPaymentMeta(c)"
              class="mt-2 rounded-lg px-2.5 py-1.5 text-xs leading-snug"
              :class="lastPaymentMeta(c)!.isToday
                ? 'border border-green-200 bg-green-50 text-green-900'
                : 'border border-slate-100 bg-slate-50 text-slate-600'"
            >
              <p
                v-if="lastPaymentMeta(c)!.isToday"
                class="m-0 font-semibold text-green-800"
              >
                Paid today · {{ formatInrAmount(c.last_payment_amount || 0) }}
                <span
                  v-if="(c.last_payment_bill_total || 0) > 0"
                  class="font-normal text-green-700/75"
                > · Bill {{ formatInrAmount(c.last_payment_bill_total || 0) }}</span>
                <template v-if="c.last_payment_mode"> · {{ c.last_payment_mode }}</template>
              </p>
              <p
                v-else
                class="m-0"
              >
                <span class="font-medium text-slate-700">Last payment </span>
                {{ formatInrAmount(c.last_payment_amount || 0) }}
                <span
                  v-if="(c.last_payment_bill_total || 0) > 0"
                  class="text-slate-400"
                > · Bill {{ formatInrAmount(c.last_payment_bill_total || 0) }}</span>
                <template v-if="c.last_payment_mode"> · {{ c.last_payment_mode }}</template>
                <span class="text-slate-500">
                  · {{ lastPaymentMeta(c)!.relative }}
                  <template v-if="lastPaymentMeta(c)!.shortDate">
                    ({{ lastPaymentMeta(c)!.shortDate }})
                  </template>
                </span>
              </p>
            </div>
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
    <DeskCollectBillModal
      v-model:open="collectOpen"
      :bill-id="collectBillId"
      :amount-due="collectAmountDue"
      :bill-total="collectBillTotal"
      :total-paid="collectTotalPaid"
      :client-name="collectClientName"
      @saved="load"
      @update:open="(v) => { if (!v) collectBillId = null }"
    />
  </div>
</template>
