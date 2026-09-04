<script setup lang="ts">
type Doctor = { doctor_id: number, doctor_name: string, color_code: string | null }
type Service = { service_id: number, service_name: string, duration_minutes: number }
type Status = { status_id: number, status_name: string, color: string }
type Appt = {
  appointment_id: number
  client_id: number | null
  doctor_id: number
  name: string
  phone: string | null
  appointment_date: string
  appointment_time: string
  end_time: string | null
  status: string
  doctor_name: string | null
  service_name: string | null
  notes: string | null
}
type BoardSlot = {
  time: string
  available: boolean
  appointment: Appt | null
}
type DoctorBoard = {
  doctor_id: number
  doctor_name: string
  color_code: string | null
  duration_minutes: number
  board: BoardSlot[]
}

type MonthCell = {
  date: string
  inMonth: boolean
  isToday: boolean
  items: Appt[]
}

const { api } = useApi()
const toast = useToast()
const { patientId, openPatient, calMode, calDate, setCalendar, todayISO } = useDeskUrl()
const refreshBadges = inject<() => void>('deskRefreshBadges', () => {})

const doctors = ref<Doctor[]>([])
const services = ref<Service[]>([])
const statuses = ref<Status[]>([])
const boards = ref<DoctorBoard[]>([])
const monthItems = ref<Appt[]>([])
const loading = ref(false)
const error = ref('')
const doctorFilter = ref<number | 'all'>('all')
const openPatientCache = ref<{ id: number, name: string } | null>(null)

const bookOpen = ref(false)
const bookPrefill = reactive({
  date: null as string | null,
  time: null as string | null,
  doctorId: null as number | null
})

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

const doctorItems = computed(() => [
  { label: 'All doctors', value: 'all' as const },
  ...doctors.value.map(d => ({ label: d.doctor_name, value: d.doctor_id }))
])

const visibleBoards = computed(() => {
  if (doctorFilter.value === 'all') return boards.value
  return boards.value.filter(b => b.doctor_id === doctorFilter.value)
})

const monthLabel = computed(() => {
  const d = new Date(`${calDate.value.slice(0, 7)}-01T12:00:00`)
  return d.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })
})

const monthCells = computed<MonthCell[]>(() => {
  const today = todayISO()
  const [y, m] = calDate.value.split('-').map(Number)
  const first = new Date(y, m - 1, 1)
  // Monday-first: Mon=0 … Sun=6
  const startPad = (first.getDay() + 6) % 7
  const gridStart = new Date(y, m - 1, 1 - startPad)
  const byDate = new Map<string, Appt[]>()
  for (const a of monthItems.value) {
    const list = byDate.get(a.appointment_date) || []
    list.push(a)
    byDate.set(a.appointment_date, list)
  }
  const cells: MonthCell[] = []
  for (let i = 0; i < 42; i++) {
    const d = new Date(gridStart)
    d.setDate(gridStart.getDate() + i)
    const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    cells.push({
      date: iso,
      inMonth: d.getMonth() === m - 1,
      isToday: iso === today,
      items: byDate.get(iso) || []
    })
  }
  return cells
})

function statusTint(name: string) {
  const s = statuses.value.find(x => x.status_name === name)
  const map: Record<string, string> = {
    success: 'bg-emerald-100 text-emerald-800',
    warning: 'bg-amber-100 text-amber-800',
    danger: 'bg-red-100 text-red-800',
    error: 'bg-red-100 text-red-800',
    secondary: 'bg-slate-100 text-slate-700',
    neutral: 'bg-slate-100 text-slate-700',
    primary: 'bg-sky-100 text-sky-800'
  }
  return map[s?.color || ''] || 'bg-[#e0f7fa] text-[#006064]'
}

function statusColor(name: string) {
  const s = statuses.value.find(x => x.status_name === name)
  const map: Record<string, 'success' | 'warning' | 'error' | 'neutral' | 'primary'> = {
    success: 'success',
    warning: 'warning',
    danger: 'error',
    error: 'error',
    secondary: 'neutral',
    neutral: 'neutral'
  }
  return map[s?.color || ''] || 'neutral'
}

function shiftDay(delta: number) {
  const d = new Date(`${calDate.value}T12:00:00`)
  d.setDate(d.getDate() + delta)
  setCalendar({ date: d.toISOString().slice(0, 10) })
}

function shiftMonth(delta: number) {
  const [y, m] = calDate.value.split('-').map(Number)
  const d = new Date(y, m - 1 + delta, 1)
  const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`
  setCalendar({ date: iso, cal: 'month' })
}

async function loadMeta() {
  const meta = await api<{ doctors: Doctor[], services: Service[], statuses: Status[] }>('/appointments/meta')
  doctors.value = meta.doctors
  services.value = meta.services
  statuses.value = meta.statuses
}

async function loadBoard() {
  loading.value = true
  error.value = ''
  try {
    const data = await api<{ date: string, doctors: DoctorBoard[] }>('/appointments/day-board', {
      query: {
        on: calDate.value,
        doctor_id: doctorFilter.value === 'all' ? undefined : doctorFilter.value
      }
    })
    boards.value = data.doctors
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to load'
  } finally {
    loading.value = false
  }
}

async function loadMonth() {
  loading.value = true
  error.value = ''
  try {
    const [y, m] = calDate.value.split('-').map(Number)
    const first = new Date(y, m - 1, 1)
    const startPad = (first.getDay() + 6) % 7
    const gridStart = new Date(y, m - 1, 1 - startPad)
    const gridEnd = new Date(gridStart)
    gridEnd.setDate(gridStart.getDate() + 41)
    const from = `${gridStart.getFullYear()}-${String(gridStart.getMonth() + 1).padStart(2, '0')}-${String(gridStart.getDate()).padStart(2, '0')}`
    const to = `${gridEnd.getFullYear()}-${String(gridEnd.getMonth() + 1).padStart(2, '0')}-${String(gridEnd.getDate()).padStart(2, '0')}`
    const data = await api<{ items: Appt[] }>('/appointments', {
      query: {
        from,
        to,
        doctor_id: doctorFilter.value === 'all' ? undefined : doctorFilter.value,
        limit: 5000
      }
    })
    monthItems.value = data.items.filter(a => !['Cancelled', 'No Show'].includes(a.status))
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to load'
  } finally {
    loading.value = false
  }
}

async function loadView() {
  if (calMode.value === 'month') await loadMonth()
  else await loadBoard()
}

async function resolveOpenPatient() {
  if (!patientId.value) {
    openPatientCache.value = null
    return
  }
  try {
    const c = await api<{ client_id: number, name: string }>(`/clients/${patientId.value}`)
    openPatientCache.value = { id: c.client_id, name: c.name }
  } catch {
    openPatientCache.value = null
  }
}

function openBookEmpty(doctorId: number, time: string) {
  bookPrefill.date = calDate.value
  bookPrefill.time = time
  bookPrefill.doctorId = doctorId
  bookOpen.value = true
}

function openBookBlank() {
  bookPrefill.date = calDate.value
  bookPrefill.time = null
  bookPrefill.doctorId = doctorFilter.value === 'all' ? null : doctorFilter.value
  bookOpen.value = true
}

function goDay(date: string) {
  setCalendar({ cal: 'day', date })
}

async function setStatus(appt: Appt, status: string) {
  try {
    const updated = await api<Appt>(`/appointments/${appt.appointment_id}/status`, {
      method: 'PATCH',
      body: { status }
    })
    for (const board of boards.value) {
      for (const slot of board.board) {
        if (slot.appointment?.appointment_id === appt.appointment_id) {
          slot.appointment = updated
        }
      }
    }
    toast.add({ title: `Marked ${status}`, color: 'success' })
    refreshBadges()
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Update failed', color: 'error' })
  }
}

function onBooked() {
  bookOpen.value = false
  loadView()
  refreshBadges()
}

watch([calDate, calMode, doctorFilter], loadView)
watch(patientId, resolveOpenPatient, { immediate: true })

onMounted(async () => {
  try {
    await loadMeta()
    await loadView()
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to load calendar'
  }
})
</script>

<template>
  <div class="relative flex h-full min-h-0 flex-col overflow-hidden">
    <div class="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white px-5 py-3">
      <div class="flex flex-wrap items-center gap-3">
        <div class="flex rounded-lg border border-slate-200 p-0.5">
          <button
            type="button"
            class="rounded-md px-3 py-1.5 text-sm font-medium"
            :class="calMode === 'day' ? 'bg-[#0097A7] text-white' : 'text-slate-600 hover:bg-slate-50'"
            @click="setCalendar({ cal: 'day' })"
          >
            Day
          </button>
          <button
            type="button"
            class="rounded-md px-3 py-1.5 text-sm font-medium"
            :class="calMode === 'month' ? 'bg-[#0097A7] text-white' : 'text-slate-600 hover:bg-slate-50'"
            @click="setCalendar({ cal: 'month' })"
          >
            Month
          </button>
        </div>

        <div v-if="calMode === 'day'" class="flex items-center gap-1 rounded-xl border border-slate-200 bg-slate-50 p-1">
          <UButton icon="i-lucide-chevron-left" color="neutral" variant="ghost" size="sm" @click="shiftDay(-1)" />
          <UInput
            :model-value="calDate"
            type="date"
            class="w-40"
            size="sm"
            @update:model-value="(v: string) => setCalendar({ date: v })"
          />
          <UButton icon="i-lucide-chevron-right" color="neutral" variant="ghost" size="sm" @click="shiftDay(1)" />
          <UButton color="neutral" variant="ghost" size="sm" @click="setCalendar({ date: todayISO() })">Today</UButton>
        </div>

        <div v-else class="flex items-center gap-1 rounded-xl border border-slate-200 bg-slate-50 p-1">
          <UButton icon="i-lucide-chevron-left" color="neutral" variant="ghost" size="sm" @click="shiftMonth(-1)" />
          <span class="min-w-[9rem] px-2 text-center text-sm font-medium text-[#1C2B35]">{{ monthLabel }}</span>
          <UButton icon="i-lucide-chevron-right" color="neutral" variant="ghost" size="sm" @click="shiftMonth(1)" />
          <UButton color="neutral" variant="ghost" size="sm" @click="setCalendar({ date: todayISO(), cal: 'month' })">Today</UButton>
        </div>

        <USelect v-model="doctorFilter" :items="doctorItems" value-key="value" label-key="label" class="w-48" />
        <p v-if="openPatientCache && calMode === 'day'" class="text-xs text-slate-500">
          Booking will use <span class="font-medium text-[#0097A7]">{{ openPatientCache.name }}</span>
        </p>
      </div>
      <UButton icon="i-lucide-plus" class="bg-[#0097A7]" @click="openBookBlank">Book</UButton>
    </div>

    <div class="min-h-0 flex-1 overflow-y-auto px-5 py-4">
      <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
      <p v-if="loading" class="text-sm text-slate-400">Loading…</p>

      <!-- Month grid -->
      <div v-else-if="calMode === 'month'" class="overflow-hidden rounded-2xl border border-slate-200 bg-white">
        <div class="grid grid-cols-7 [grid-template-columns:repeat(7,minmax(0,1fr))] border-b border-slate-100 bg-slate-50">
          <div v-for="w in WEEKDAYS" :key="w" class="px-2 py-2 text-center text-xs font-semibold uppercase tracking-wide text-slate-500">
            {{ w }}
          </div>
        </div>
        <div class="grid [grid-template-columns:repeat(7,minmax(0,1fr))] auto-rows-[minmax(6.5rem,auto)]">
          <button
            v-for="cell in monthCells"
            :key="cell.date"
            type="button"
            class="flex min-h-[7.5rem] flex-col gap-1 border-b border-r border-slate-100 p-1.5 text-left transition hover:bg-[#0097A7]/5"
            :class="[
              cell.inMonth ? 'bg-white' : 'bg-slate-50/80',
              cell.isToday ? 'ring-2 ring-inset ring-[#0097A7]' : ''
            ]"
            @click="goDay(cell.date)"
          >
            <div class="flex items-center justify-between gap-1 px-0.5">
              <span
                class="text-xs font-semibold"
                :class="cell.inMonth ? 'text-[#1C2B35]' : 'text-slate-300'"
              >
                {{ Number(cell.date.slice(8)) }}
              </span>
              <span
                v-if="cell.items.length"
                class="rounded-full bg-[#0097A7] px-1.5 text-[10px] font-semibold text-white"
              >
                {{ cell.items.length }}
              </span>
            </div>
            <div class="flex min-h-0 flex-1 flex-col gap-0.5 overflow-hidden">
              <button
                v-for="a in cell.items.slice(0, 3)"
                :key="a.appointment_id"
                type="button"
                class="truncate rounded px-1 py-0.5 text-[10px] font-medium leading-tight"
                :class="statusTint(a.status)"
                :title="`${formatAmPm(a.appointment_time)} ${a.name}`"
                @click.stop="a.client_id ? openPatient(a.client_id!) : goDay(cell.date)"
              >
                {{ formatAmPm(a.appointment_time) }} {{ a.name }}
              </button>
              <span v-if="cell.items.length > 3" class="px-1 text-[10px] text-slate-400">
                +{{ cell.items.length - 3 }} more
              </span>
            </div>
          </button>
        </div>
      </div>

      <!-- Day board -->
      <div v-else class="space-y-6">
        <section
          v-for="board in visibleBoards"
          :key="board.doctor_id"
          class="overflow-hidden rounded-2xl border border-slate-200 bg-white"
        >
          <header
            class="flex items-center gap-2 border-b border-slate-100 px-4 py-2.5"
            :style="{ borderLeftWidth: '4px', borderLeftColor: board.color_code || '#0097A7' }"
          >
            <h3 class="text-sm font-semibold text-[#1C2B35]">{{ board.doctor_name }}</h3>
            <span class="text-xs text-slate-400">{{ board.duration_minutes }}m slots</span>
          </header>

          <ul v-if="board.board.length" class="divide-y divide-slate-100">
            <li
              v-for="slot in board.board"
              :key="`${board.doctor_id}-${slot.time}`"
              class="flex flex-col gap-2 px-4 py-2.5 sm:flex-row sm:items-center sm:justify-between"
              :class="slot.available ? 'hover:bg-[#0097A7]/5 cursor-pointer' : 'bg-slate-50/80'"
              @click="slot.available && openBookEmpty(board.doctor_id, slot.time)"
            >
              <div class="flex min-w-0 items-start gap-3">
                <span
                  class="w-12 shrink-0 pt-0.5 font-mono text-sm"
                  :class="slot.available ? 'text-slate-400' : 'text-[#0097A7]'"
                >
                  {{ formatAmPm(slot.time) }}
                </span>

                <template v-if="slot.appointment && slot.appointment.appointment_time === slot.time">
                  <div class="min-w-0">
                    <div class="flex flex-wrap items-center gap-2">
                      <button
                        v-if="slot.appointment.client_id"
                        type="button"
                        class="truncate text-sm font-medium text-[#1C2B35] hover:underline"
                        @click.stop="openPatient(slot.appointment.client_id!)"
                      >
                        {{ slot.appointment.name }}
                      </button>
                      <span v-else class="text-sm font-medium text-[#1C2B35]">{{ slot.appointment.name }}</span>
                      <UBadge :color="statusColor(slot.appointment.status)" variant="subtle" size="sm">
                        {{ slot.appointment.status }}
                      </UBadge>
                    </div>
                    <p class="truncate text-xs text-slate-500">
                      <span v-if="slot.appointment.service_name">{{ slot.appointment.service_name }}</span>
                      <span v-if="slot.appointment.phone"> · {{ slot.appointment.phone }}</span>
                      <span v-if="slot.appointment.end_time"> · until {{ formatAmPm(slot.appointment.end_time) }}</span>
                    </p>
                  </div>
                </template>
                <template v-else-if="slot.appointment">
                  <span class="pt-0.5 text-xs text-slate-400">In progress · {{ slot.appointment.name }}</span>
                </template>
                <template v-else>
                  <span class="pt-0.5 text-sm text-slate-400">Available — click to book</span>
                </template>
              </div>

              <div
                v-if="slot.appointment && slot.appointment.appointment_time === slot.time"
                class="flex flex-wrap gap-1 sm:justify-end"
                @click.stop
              >
                <UButton
                  v-for="s in statuses"
                  :key="s.status_id"
                  size="xs"
                  :variant="slot.appointment.status === s.status_name ? 'solid' : 'outline'"
                  :color="slot.appointment.status === s.status_name ? statusColor(s.status_name) : 'neutral'"
                  @click="setStatus(slot.appointment!, s.status_name)"
                >
                  {{ s.status_name }}
                </UButton>
              </div>
            </li>
          </ul>
          <p v-else class="px-4 py-8 text-center text-sm text-slate-400">
            No schedule for this day
          </p>
        </section>

        <p v-if="!visibleBoards.length" class="py-10 text-center text-sm text-slate-500">
          No doctors to show.
        </p>
      </div>
    </div>

    <DeskBookModal
      v-model:open="bookOpen"
      :client-id="openPatientCache?.id"
      :client-name="openPatientCache?.name"
      :date="bookPrefill.date"
      :time="bookPrefill.time"
      :doctor-id="bookPrefill.doctorId"
      @booked="onBooked"
    />
  </div>
</template>
