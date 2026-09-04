<script setup lang="ts">
type Doctor = {
  doctor_id: number
  doctor_name: string
  color_code: string | null
  profile_photo_url?: string | null
}
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
const selectedDoctorIds = ref<number[]>([])
const openPatientCache = ref<{ id: number, name: string } | null>(null)

const DOCTOR_SEL_KEY = 'desk-cal-doctor-selection'

const bookOpen = ref(false)
const bookPrefill = reactive({
  date: null as string | null,
  time: null as string | null,
  doctorId: null as number | null
})

const detailOpen = ref(false)
const detailAppt = ref<Appt | null>(null)
const dayListOpen = ref(false)
const dayListDate = ref<string | null>(null)
const dayListItems = ref<Appt[]>([])

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

const viewItems = [
  { label: 'Month', value: 'month' as const },
  { label: 'Day', value: 'day' as const }
  // Week later
]

const selectedSet = computed(() => new Set(selectedDoctorIds.value))

const allDoctorsSelected = computed(
  () => doctors.value.length > 0 && doctors.value.every(d => selectedSet.value.has(d.doctor_id))
)

const someDoctorsSelected = computed(
  () => selectedDoctorIds.value.length > 0 && !allDoctorsSelected.value
)

const bookDoctorPrefill = computed(() =>
  selectedDoctorIds.value.length === 1 ? selectedDoctorIds.value[0]! : null
)

const dayListLabel = computed(() => {
  if (!dayListDate.value) return 'Appointments'
  const d = new Date(`${dayListDate.value}T12:00:00`)
  return d.toLocaleDateString('en-IN', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  })
})

const visibleBoards = computed(() =>
  boards.value.filter(b => selectedSet.value.has(b.doctor_id))
)

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
    if (!selectedSet.value.has(a.doctor_id)) continue
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

function persistDoctorSelection() {
  try {
    localStorage.setItem(
      DOCTOR_SEL_KEY,
      JSON.stringify({
        selected: selectedDoctorIds.value,
        known: doctors.value.map(d => d.doctor_id)
      })
    )
  } catch { /* ignore */ }
}

function initDoctorSelection() {
  const allIds = doctors.value.map(d => d.doctor_id)
  try {
    const raw = localStorage.getItem(DOCTOR_SEL_KEY)
    if (raw) {
      const parsed = JSON.parse(raw) as { selected?: number[], known?: number[] }
      const saved = Array.isArray(parsed.selected) ? parsed.selected : []
      const known = new Set(Array.isArray(parsed.known) ? parsed.known : [])
      const kept = saved.filter(id => allIds.includes(id))
      const newcomers = allIds.filter(id => !known.has(id))
      selectedDoctorIds.value = [...new Set([...kept, ...newcomers])]
      persistDoctorSelection()
      return
    }
  } catch { /* ignore */ }
  selectedDoctorIds.value = allIds
  persistDoctorSelection()
}

function isDoctorSelected(id: number) {
  return selectedSet.value.has(id)
}

function toggleDoctor(id: number) {
  if (selectedSet.value.has(id)) {
    selectedDoctorIds.value = selectedDoctorIds.value.filter(x => x !== id)
  } else {
    selectedDoctorIds.value = [...selectedDoctorIds.value, id]
  }
  persistDoctorSelection()
}

function toggleAllDoctors() {
  if (allDoctorsSelected.value) {
    selectedDoctorIds.value = []
  } else {
    selectedDoctorIds.value = doctors.value.map(d => d.doctor_id)
  }
  persistDoctorSelection()
}

function doctorInitials(name: string) {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (!parts.length) return '?'
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase()
  return `${parts[0]!.charAt(0)}${parts[parts.length - 1]!.charAt(0)}`.toUpperCase()
}

function doctorColor(doctorId: number) {
  return doctors.value.find(d => d.doctor_id === doctorId)?.color_code || '#0097A7'
}

function doctorName(doctorId: number) {
  return doctors.value.find(d => d.doctor_id === doctorId)?.doctor_name || null
}

function apptChipTitle(a: Appt) {
  const parts = [formatAmPm(a.appointment_time), a.name]
  const doc = a.doctor_name || doctorName(a.doctor_id)
  if (doc) parts.push(doc)
  return parts.join(' · ')
}

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
  initDoctorSelection()
}

async function loadBoard() {
  loading.value = true
  error.value = ''
  try {
    const data = await api<{ date: string, doctors: DoctorBoard[] }>('/appointments/day-board', {
      query: { on: calDate.value }
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
      query: { from, to, limit: 5000 }
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
  bookPrefill.doctorId = bookDoctorPrefill.value
  bookOpen.value = true
}

function openBookForDate(date: string) {
  bookPrefill.date = date
  bookPrefill.time = null
  bookPrefill.doctorId = bookDoctorPrefill.value
  bookOpen.value = true
}

function openApptDetail(appt: Appt) {
  detailAppt.value = appt
  detailOpen.value = true
}

function openDayList(date: string, items: Appt[]) {
  dayListDate.value = date
  dayListItems.value = items
  dayListOpen.value = true
}

function pickFromDayList(appt: Appt) {
  dayListOpen.value = false
  openApptDetail(appt)
}

function onChangeView(next: 'day' | 'month') {
  if (next === calMode.value) return
  setCalendar({ cal: next, date: calDate.value })
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
    const mi = monthItems.value.findIndex(a => a.appointment_id === appt.appointment_id)
    if (mi >= 0) {
      if (['Cancelled', 'No Show'].includes(updated.status)) {
        monthItems.value.splice(mi, 1)
      } else {
        monthItems.value[mi] = updated
      }
    }
    const di = dayListItems.value.findIndex(a => a.appointment_id === appt.appointment_id)
    if (di >= 0) dayListItems.value[di] = updated
    if (detailAppt.value?.appointment_id === appt.appointment_id) {
      detailAppt.value = updated
    }
    toast.add({ title: `Marked ${status}`, color: 'success' })
    refreshBadges()
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Update failed', color: 'error' })
  }
}

function formatDateLabel(iso: string) {
  const d = new Date(`${iso}T12:00:00`)
  return d.toLocaleDateString('en-IN', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric'
  })
}

function onBooked() {
  bookOpen.value = false
  loadView()
  refreshBadges()
}

watch([calDate, calMode], loadView)
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
  <div class="relative flex h-full min-h-0 overflow-hidden">
    <aside class="flex w-[220px] shrink-0 flex-col border-r border-slate-200 bg-white">
      <div class="border-b border-slate-100 px-3 py-3">
        <p class="text-[11px] font-semibold uppercase tracking-wide text-slate-400">Doctors</p>
      </div>
      <div class="min-h-0 flex-1 space-y-0.5 overflow-y-auto p-2">
        <label class="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-2 text-sm font-medium text-[#1C2B35] hover:bg-slate-50">
          <input
            type="checkbox"
            class="h-3.5 w-3.5 accent-[#0097A7]"
            :checked="allDoctorsSelected"
            :indeterminate.prop="someDoctorsSelected"
            @change="toggleAllDoctors"
          >
          <span>All doctors</span>
        </label>
        <label
          v-for="d in doctors"
          :key="d.doctor_id"
          class="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-2 text-sm text-slate-700 hover:bg-slate-50"
          :class="isDoctorSelected(d.doctor_id) ? 'bg-[#0097A7]/5' : ''"
        >
          <input
            type="checkbox"
            class="h-3.5 w-3.5 accent-[#0097A7]"
            :checked="isDoctorSelected(d.doctor_id)"
            @change="toggleDoctor(d.doctor_id)"
          >
          <span class="relative flex h-7 w-7 shrink-0 items-center justify-center overflow-hidden rounded-full text-[10px] font-semibold text-white"
            :style="{ background: d.color_code || '#0097A7' }"
          >
            <img
              v-if="d.profile_photo_url"
              :src="d.profile_photo_url"
              :alt="d.doctor_name"
              class="h-full w-full object-cover"
            >
            <span v-else>{{ doctorInitials(d.doctor_name) }}</span>
          </span>
          <span class="min-w-0 flex-1 truncate">{{ d.doctor_name }}</span>
          <span
            class="h-2.5 w-2.5 shrink-0 rounded-full"
            :style="{ background: d.color_code || '#0097A7' }"
          />
        </label>
        <p v-if="!doctors.length" class="px-2 py-6 text-center text-xs text-slate-400">No doctors</p>
      </div>
    </aside>

    <div class="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
      <div class="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white px-5 py-3">
        <div class="flex flex-wrap items-center gap-3">
          <div class="flex items-center gap-2">
            <span class="text-xs font-medium uppercase tracking-wide text-slate-400">Change view</span>
            <USelect
              :model-value="calMode"
              :items="viewItems"
              value-key="value"
              label-key="label"
              class="w-32"
              @update:model-value="(v: 'day' | 'month') => onChangeView(v)"
            />
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

          <p v-if="openPatientCache && calMode === 'day'" class="text-xs text-slate-500">
            Booking will use <span class="font-medium text-[#0097A7]">{{ openPatientCache.name }}</span>
          </p>
        </div>
        <UButton icon="i-lucide-plus" class="bg-[#0097A7]" @click="openBookBlank">Book</UButton>
      </div>

      <div
        class="min-h-0 flex-1 px-5 py-4"
        :class="calMode === 'month' && selectedDoctorIds.length && !loading && !error
          ? 'flex flex-col overflow-hidden'
          : 'overflow-y-auto'"
      >
        <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
        <p v-else-if="loading" class="text-sm text-slate-400">Loading…</p>
        <div
          v-else-if="!selectedDoctorIds.length"
          class="flex h-full min-h-[12rem] items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-white px-4 text-center text-sm text-slate-500"
        >
          Select at least one doctor to see appointments.
        </div>

        <!-- Month grid: fills viewport, no vertical scroll -->
        <div
          v-else-if="calMode === 'month'"
          class="flex h-full min-h-0 flex-1 flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white"
        >
          <div class="grid shrink-0 grid-cols-7 border-b border-slate-100 bg-slate-50 [grid-template-columns:repeat(7,minmax(0,1fr))]">
            <div
              v-for="w in WEEKDAYS"
              :key="w"
              class="px-2 py-2 text-center text-sm font-semibold uppercase tracking-wide text-slate-500"
            >
              {{ w }}
            </div>
          </div>
          <div class="grid min-h-0 flex-1 grid-cols-7 grid-rows-6 [grid-template-columns:repeat(7,minmax(0,1fr))] [grid-template-rows:repeat(6,minmax(0,1fr))]">
            <div
              v-for="cell in monthCells"
              :key="cell.date"
              role="button"
              tabindex="0"
              class="flex min-h-0 cursor-pointer flex-col gap-0.5 overflow-hidden border-b border-r border-slate-100 p-1.5 text-left transition hover:bg-[#0097A7]/5"
              :class="[
                cell.inMonth ? 'bg-white' : 'bg-slate-50/80',
                cell.isToday ? 'ring-2 ring-inset ring-[#0097A7]' : ''
              ]"
              @click="openBookForDate(cell.date)"
              @keydown.enter.prevent="openBookForDate(cell.date)"
            >
              <div class="flex shrink-0 items-center justify-between gap-1 px-0.5">
                <span
                  class="text-sm font-semibold"
                  :class="cell.inMonth ? 'text-[#1C2B35]' : 'text-slate-300'"
                >
                  {{ Number(cell.date.slice(8)) }}
                </span>
              </div>
              <div class="flex min-h-0 flex-1 flex-col gap-0.5 overflow-hidden">
                <button
                  v-for="a in cell.items.slice(0, 3)"
                  :key="a.appointment_id"
                  type="button"
                  class="flex min-w-0 shrink-0 items-center gap-1.5 truncate rounded px-1.5 py-0.5 text-left text-xs font-medium leading-snug"
                  :class="statusTint(a.status)"
                  :title="apptChipTitle(a)"
                  @click.stop="openApptDetail(a)"
                >
                  <span
                    class="h-2 w-2 shrink-0 rounded-full"
                    :style="{ background: doctorColor(a.doctor_id) }"
                  />
                  <span class="min-w-0 truncate">{{ formatAmPm(a.appointment_time) }} {{ a.name }}</span>
                </button>
                <button
                  v-if="cell.items.length > 3"
                  type="button"
                  class="shrink-0 px-1.5 text-left text-xs text-slate-500 hover:text-[#0097A7] hover:underline"
                  @click.stop="openDayList(cell.date, cell.items)"
                >
                  +{{ cell.items.length - 3 }} more
                </button>
              </div>
            </div>
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

    <UModal v-model:open="detailOpen" title="Appointment">
      <template #body>
        <div v-if="detailAppt" class="space-y-4">
          <div>
            <p class="text-lg font-semibold text-[#1C2B35]">{{ detailAppt.name }}</p>
            <p class="mt-1 text-sm text-slate-500">{{ formatDateLabel(detailAppt.appointment_date) }}</p>
            <p class="text-sm text-slate-600">
              {{ formatAmPm(detailAppt.appointment_time) }}
              <span v-if="detailAppt.end_time"> – {{ formatAmPm(detailAppt.end_time) }}</span>
            </p>
          </div>
          <div class="space-y-1 text-sm text-slate-600">
            <p v-if="detailAppt.doctor_name"><span class="text-slate-400">Doctor:</span> {{ detailAppt.doctor_name }}</p>
            <p v-if="detailAppt.service_name"><span class="text-slate-400">Service:</span> {{ detailAppt.service_name }}</p>
            <p v-if="detailAppt.phone"><span class="text-slate-400">Phone:</span> {{ detailAppt.phone }}</p>
            <p v-if="detailAppt.notes"><span class="text-slate-400">Notes:</span> {{ detailAppt.notes }}</p>
            <p>
              <span class="text-slate-400">Status:</span>
              <UBadge class="ml-1" :color="statusColor(detailAppt.status)" variant="subtle" size="sm">
                {{ detailAppt.status }}
              </UBadge>
            </p>
          </div>
          <div class="flex flex-wrap gap-1">
            <UButton
              v-for="s in statuses"
              :key="s.status_id"
              size="xs"
              :variant="detailAppt.status === s.status_name ? 'solid' : 'outline'"
              :color="detailAppt.status === s.status_name ? statusColor(s.status_name) : 'neutral'"
              @click="setStatus(detailAppt!, s.status_name)"
            >
              {{ s.status_name }}
            </UButton>
          </div>
          <div class="flex justify-end gap-2 pt-1">
            <UButton color="neutral" variant="ghost" @click="detailOpen = false">Close</UButton>
            <UButton
              v-if="detailAppt.client_id"
              class="bg-[#0097A7]"
              @click="openPatient(detailAppt.client_id!); detailOpen = false"
            >
              Open patient
            </UButton>
          </div>
        </div>
      </template>
    </UModal>

    <UModal v-model:open="dayListOpen" :title="dayListLabel">
      <template #body>
        <ul class="divide-y divide-slate-100">
          <li v-if="!dayListItems.length" class="py-8 text-center text-sm text-slate-500">No appointments</li>
          <li
            v-for="a in dayListItems"
            :key="a.appointment_id"
          >
            <button
              type="button"
              class="flex w-full items-center justify-between gap-3 px-1 py-2.5 text-left hover:bg-slate-50"
              @click="pickFromDayList(a)"
            >
              <div class="min-w-0">
                <p class="truncate text-sm font-medium text-[#1C2B35]">
                  {{ formatAmPm(a.appointment_time) }} · {{ a.name }}
                </p>
                <p class="truncate text-xs text-slate-500">
                  {{ [a.doctor_name, a.service_name].filter(Boolean).join(' · ') || '—' }}
                </p>
              </div>
              <UBadge :color="statusColor(a.status)" variant="subtle" size="sm">{{ a.status }}</UBadge>
            </button>
          </li>
        </ul>
        <div class="mt-3 flex justify-end gap-2">
          <UButton color="neutral" variant="ghost" @click="dayListOpen = false">Close</UButton>
          <UButton
            class="bg-[#0097A7]"
            @click="dayListOpen = false; dayListDate && openBookForDate(dayListDate)"
          >
            Book this day
          </UButton>
        </div>
      </template>
    </UModal>
  </div>
</template>
