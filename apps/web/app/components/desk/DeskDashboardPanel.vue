<script setup lang="ts">
type DeskSummary = {
  clinic: { clinic_name: string } | null
  checked_in: number
  appointments_today: number
  receipts_today_total: number
  open_tasks: number
  today: string
}
type ClientRow = { client_id: number, name: string, number: string | null, status: string }
type Appt = { appointment_id: number, client_id: number | null, name: string, appointment_time: string, status: string, doctor_name: string | null }
type Receipt = { receipt_id: number, client_id: number, amount: number, payment_mode: string, received_at: string }

const { api } = useApi()
const { openPatient, setView } = useDeskUrl()

const summary = ref<DeskSummary | null>(null)
const checkedIn = ref<ClientRow[]>([])
const todayAppts = ref<Appt[]>([])
const todayReceipts = ref<Receipt[]>([])

async function load() {
  const [s, list, today, receipts] = await Promise.all([
    api<DeskSummary>('/desk/summary'),
    api<{ items: ClientRow[] }>('/clients', { query: { checked_in: true, limit: 50 } }),
    api<{ items: Appt[] }>('/desk/today'),
    api<{ items: Receipt[] }>('/desk/receipts/today')
  ])
  summary.value = s
  checkedIn.value = list.items
  todayAppts.value = today.items.filter(a => a.status !== 'Cancelled')
  todayReceipts.value = receipts.items
}

onMounted(load)
</script>

<template>
  <div class="h-full overflow-y-auto p-5">
    <div class="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <div class="rounded-xl border border-slate-200 bg-white p-4">
        <p class="text-xs text-slate-500">Checked in</p>
        <p class="mt-1 text-3xl font-semibold text-[#0097A7]">{{ summary?.checked_in ?? '—' }}</p>
      </div>
      <div class="rounded-xl border border-slate-200 bg-white p-4">
        <p class="text-xs text-slate-500">Appointments today</p>
        <p class="mt-1 text-3xl font-semibold text-[#1C2B35]">{{ summary?.appointments_today ?? '—' }}</p>
      </div>
      <div class="rounded-xl border border-slate-200 bg-white p-4">
        <p class="text-xs text-slate-500">Collected today</p>
        <p class="mt-1 text-3xl font-semibold text-[#1C2B35]">₹{{ Number(summary?.receipts_today_total || 0).toLocaleString('en-IN') }}</p>
      </div>
      <div class="rounded-xl border border-slate-200 bg-white p-4">
        <p class="text-xs text-slate-500">Open tasks</p>
        <p class="mt-1 text-3xl font-semibold text-[#1C2B35]">{{ summary?.open_tasks ?? '—' }}</p>
      </div>
    </div>

    <div class="grid gap-4 xl:grid-cols-2">
      <section class="rounded-xl border border-slate-200 bg-white">
        <div class="flex items-center justify-between border-b border-slate-100 px-4 py-3">
          <h2 class="text-sm font-semibold">Today’s board</h2>
          <button type="button" class="text-xs font-medium text-[#0097A7]" @click="setView('calendar')">Calendar</button>
        </div>
        <ul class="divide-y divide-slate-50">
          <li v-if="!todayAppts.length" class="px-4 py-8 text-center text-sm text-slate-400">No appointments today.</li>
          <li v-for="a in todayAppts" :key="a.appointment_id">
            <button
              type="button"
              class="flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-slate-50"
              @click="a.client_id ? openPatient(a.client_id) : setView('calendar')"
            >
              <div>
                <p class="text-sm font-medium"><span class="mr-2 font-mono text-[#0097A7]">{{ a.appointment_time }}</span>{{ a.name }}</p>
                <p class="text-xs text-slate-500">{{ a.doctor_name }}</p>
              </div>
              <span class="rounded bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600">{{ a.status }}</span>
            </button>
          </li>
        </ul>
      </section>

      <section class="rounded-xl border border-slate-200 bg-white">
        <div class="border-b border-slate-100 px-4 py-3">
          <h2 class="text-sm font-semibold">Checked in</h2>
        </div>
        <ul class="divide-y divide-slate-50">
          <li v-if="!checkedIn.length" class="px-4 py-8 text-center text-sm text-slate-400">Nobody checked in.</li>
          <li v-for="c in checkedIn" :key="c.client_id">
            <button type="button" class="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-slate-50" @click="openPatient(c.client_id)">
              <div>
                <p class="text-sm font-medium">{{ c.name }}</p>
                <p class="text-xs text-slate-500">{{ c.number || 'No phone' }} · {{ c.status }}</p>
              </div>
              <span class="rounded bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-700">IN</span>
            </button>
          </li>
        </ul>
      </section>

      <section class="rounded-xl border border-slate-200 bg-white xl:col-span-2">
        <div class="border-b border-slate-100 px-4 py-3">
          <h2 class="text-sm font-semibold">Receipts today</h2>
        </div>
        <ul class="divide-y divide-slate-50">
          <li v-if="!todayReceipts.length" class="px-4 py-8 text-center text-sm text-slate-400">No receipts yet.</li>
          <li v-for="r in todayReceipts" :key="r.receipt_id">
            <button type="button" class="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-slate-50" @click="openPatient(r.client_id)">
              <p class="text-sm font-medium">₹{{ Number(r.amount).toLocaleString('en-IN') }} · {{ r.payment_mode }}</p>
              <p class="text-xs text-slate-500">{{ new Date(r.received_at).toLocaleTimeString() }}</p>
            </button>
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>
