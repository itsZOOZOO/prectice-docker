<script setup lang="ts">
import { formatAmPm } from '~/utils/formatTime'
import { formatInrAmount, formatLastPaymentRelative } from '~/utils/lastPayment'

type DeskSummary = {
  clinic: { clinic_name: string } | null
  checked_in: number
  appointments_today: number
  receipts_today_total: number
  open_tasks: number
  today: string
}
type ClientRow = {
  client_id: number
  name: string
  number: string | null
  status: string
  check_in_status?: boolean
  pending_bill_id?: number
  pending_amount?: number
  pending_bill_total?: number | null
  pending_total_paid?: number
  last_payment_amount?: number | null
  last_payment_mode?: string | null
  last_payment_at?: string | null
  last_payment_bill_total?: number | null
}
type Appt = { appointment_id: number, client_id: number | null, name: string, appointment_time: string, status: string, doctor_name: string | null }
type TodayReceipt = {
  receipt_id: number
  client_id: number
  client_name?: string
  amount: number
  payment_mode: string
  description?: string | null
  received_at: string
}

const REVEAL_MS = 4000

const { api } = useApi()
const toast = useToast()
const { openPatient, setView } = useDeskUrl()

const summary = ref<DeskSummary | null>(null)
const checkedIn = ref<ClientRow[]>([])
const todayAppts = ref<Appt[]>([])
const todayReceipts = ref<TodayReceipt[]>([])
const receiptsTodayTotal = ref(0)
const toggling = ref<number | null>(null)

const collectOpen = ref(false)
const collectBillId = ref<number | null>(null)
const collectAmountDue = ref(0)
const collectBillTotal = ref(0)
const collectTotalPaid = ref(0)
const collectClientName = ref('')

const collectedRevealed = ref(false)
const receiptsModalOpen = ref(false)
let revealTimer: ReturnType<typeof setTimeout> | null = null

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

function clearRevealTimer() {
  if (revealTimer) {
    clearTimeout(revealTimer)
    revealTimer = null
  }
}

async function revealCollectedToday() {
  collectedRevealed.value = true
  receiptsModalOpen.value = true
  clearRevealTimer()
  revealTimer = setTimeout(() => {
    collectedRevealed.value = false
    revealTimer = null
  }, REVEAL_MS)
  try {
    const receipts = await api<{ items: TodayReceipt[], total: number }>('/desk/receipts/today')
    todayReceipts.value = receipts.items
    receiptsTodayTotal.value = Number(receipts.total || 0)
    if (summary.value) {
      summary.value = { ...summary.value, receipts_today_total: receiptsTodayTotal.value }
    }
  } catch {
    // keep previously loaded rows
  }
}

async function load() {
  const [s, list, today, receipts] = await Promise.all([
    api<DeskSummary>('/desk/summary'),
    api<{ items: ClientRow[] }>('/clients', { query: { checked_in: true, limit: 50 } }),
    api<{ items: Appt[] }>('/desk/today'),
    api<{ items: TodayReceipt[], total: number }>('/desk/receipts/today')
  ])
  summary.value = s
  checkedIn.value = list.items
  todayAppts.value = today.items.filter(a => a.status !== 'Cancelled')
  todayReceipts.value = receipts.items
  receiptsTodayTotal.value = Number(receipts.total ?? s.receipts_today_total ?? 0)
}

onMounted(load)

onUnmounted(() => {
  clearRevealTimer()
})

async function checkout(c: ClientRow) {
  if (!window.confirm(`Check out ${c.name}?`)) return
  toggling.value = c.client_id
  try {
    await api(`/clients/${c.client_id}/check-out`, { method: 'POST' })
    toast.add({ title: 'Checked out', color: 'success' })
    await load()
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
  } finally {
    toggling.value = null
  }
}

function openCollect(c: ClientRow) {
  if (!hasPending(c)) return
  collectBillId.value = c.pending_bill_id || null
  collectAmountDue.value = Number(c.pending_amount || 0)
  collectBillTotal.value = Number(c.pending_bill_total || c.pending_amount || 0)
  collectTotalPaid.value = Number(c.pending_total_paid || 0)
  collectClientName.value = c.name
  collectOpen.value = true
}
</script>

<template>
  <div class="flex h-full min-h-0 flex-col overflow-y-auto overscroll-y-contain p-5 [-webkit-overflow-scrolling:touch]">
    <div class="mb-4 grid shrink-0 gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <div class="rounded-xl border border-slate-200 bg-white p-4">
        <p class="text-xs text-slate-500">Checked in</p>
        <p class="mt-1 text-3xl font-semibold text-[#0097A7]">{{ summary?.checked_in ?? '—' }}</p>
      </div>
      <div class="rounded-xl border border-slate-200 bg-white p-4">
        <p class="text-xs text-slate-500">Appointments today</p>
        <p class="mt-1 text-3xl font-semibold text-[#1C2B35]">{{ summary?.appointments_today ?? '—' }}</p>
      </div>
      <button
        type="button"
        class="rounded-xl border border-slate-200 bg-white p-4 text-left transition hover:border-[#0097A7]/40 hover:bg-slate-50/80 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#0097A7]"
        aria-label="Show today's collections"
        @click="revealCollectedToday"
      >
        <div class="flex items-center justify-between gap-2">
          <p class="text-xs text-slate-500">Collected today</p>
          <UIcon
            v-if="collectedRevealed"
            name="i-lucide-eye"
            class="h-4 w-4 shrink-0 text-slate-400"
          />
        </div>
        <p class="mt-1 flex min-h-[2.25rem] items-center text-3xl font-semibold text-[#1C2B35]">
          <template v-if="collectedRevealed">
            {{ formatInrAmount(receiptsTodayTotal || summary?.receipts_today_total || 0) }}
          </template>
          <UIcon
            v-else
            name="i-lucide-eye-off"
            class="h-8 w-8 text-slate-300"
            aria-hidden="true"
          />
        </p>
      </button>
      <div class="rounded-xl border border-slate-200 bg-white p-4">
        <p class="text-xs text-slate-500">Tasks due today</p>
        <p class="mt-1 text-3xl font-semibold text-[#1C2B35]">{{ summary?.open_tasks ?? '—' }}</p>
      </div>
    </div>

    <div class="grid min-h-0 flex-1 grid-rows-2 gap-4 xl:grid-cols-2 xl:grid-rows-1">
      <section class="flex min-h-0 flex-col overflow-hidden rounded-xl border border-slate-200 bg-white">
        <div class="flex shrink-0 items-center justify-between border-b border-slate-100 px-4 py-3">
          <h2 class="text-sm font-semibold">Today’s board</h2>
          <button type="button" class="text-xs font-medium text-[#0097A7]" @click="setView('calendar')">Calendar</button>
        </div>
        <ul class="min-h-0 flex-1 divide-y divide-slate-50 overflow-y-auto">
          <li v-if="!todayAppts.length" class="px-4 py-8 text-center text-sm text-slate-400">No appointments today.</li>
          <li v-for="a in todayAppts" :key="a.appointment_id">
            <button
              type="button"
              class="flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-slate-50"
              @click="a.client_id ? openPatient(a.client_id) : setView('calendar')"
            >
              <div>
                <p class="text-sm font-medium"><span class="mr-2 font-mono text-[#0097A7]">{{ formatAmPm(a.appointment_time) }}</span>{{ a.name }}</p>
                <p class="text-xs text-slate-500">{{ a.doctor_name }}</p>
              </div>
              <span class="rounded bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600">{{ a.status }}</span>
            </button>
          </li>
        </ul>
      </section>

      <section class="flex min-h-0 flex-col overflow-hidden rounded-xl border border-slate-200 bg-white">
        <div class="shrink-0 border-b border-slate-100 px-4 py-3">
          <h2 class="text-sm font-semibold">Checked in</h2>
        </div>
        <ul class="min-h-0 flex-1 divide-y divide-slate-50 overflow-y-auto">
          <li v-if="!checkedIn.length" class="px-4 py-8 text-center text-sm text-slate-400">Nobody checked in.</li>
          <li
            v-for="c in checkedIn"
            :key="c.client_id"
            class="px-4 py-3"
          >
            <div class="flex items-start justify-between gap-3">
              <button
                type="button"
                class="min-w-0 flex-1 text-left hover:opacity-80"
                @click="openPatient(c.client_id)"
              >
                <p class="text-sm font-medium text-[#1C2B35]">{{ c.name }}</p>
                <p class="text-xs text-slate-500">{{ c.number || 'No phone' }} · {{ c.status }}</p>
              </button>
              <span class="shrink-0 rounded bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-700">IN</span>
            </div>
            <div class="mt-2 flex flex-wrap items-center gap-2">
              <button
                type="button"
                class="rounded-lg px-3 py-1.5 text-xs font-semibold text-white disabled:cursor-not-allowed"
                :class="hasPending(c) ? 'bg-red-600 hover:bg-red-700' : 'bg-slate-300'"
                :disabled="!hasPending(c)"
                :title="hasPending(c) ? undefined : 'No pending bill'"
                @click="openCollect(c)"
              >
                <template v-if="hasPending(c)">
                  Collect {{ formatInrAmount(c.pending_amount || 0) }}
                </template>
                <template v-else>
                  Collect <span class="line-through">₹</span>
                </template>
              </button>
              <button
                type="button"
                class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-60"
                :disabled="toggling === c.client_id"
                @click="checkout(c)"
              >
                Check out
              </button>
              <button
                type="button"
                class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                @click="openPatient(c.client_id)"
              >
                Open
              </button>
            </div>
            <div
              v-if="hasLastPayment(c) && lastPaymentMeta(c)"
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
          </li>
        </ul>
      </section>
    </div>

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

    <DeskTodaysReceiptsModal
      v-model:open="receiptsModalOpen"
      :receipts="todayReceipts"
      :total="receiptsTodayTotal || Number(summary?.receipts_today_total || 0)"
      @open-patient="openPatient"
    />
  </div>
</template>
