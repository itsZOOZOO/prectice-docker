<script setup lang="ts">
import {
  buildMonthDates,
  currentMinutesInIst,
  currentMonthInIst,
  formatCurrentTimeIst,
  monthBounds,
  monthLabel,
  shiftMonth,
  timeToMinutes,
  todayInIst,
  type DateStripItem
} from '~/utils/agendaCalendar'
import { formatAmPm } from '~/utils/formatTime'

definePageMeta({ layout: 'mobile' })

type Appt = {
  appointment_id: number
  appointment_date: string
  appointment_time: string
  end_time?: string | null
  status: string
  name: string
  client_id: number | null
  doctor_id: number
  doctor_name: string | null
  doctor_color?: string | null
  service_name: string | null
  duration_minutes?: number | null
}

type Doctor = {
  doctor_id: number
  doctor_name: string
  color_code: string | null
}

type DaySection = {
  date: string
  meta: DateStripItem
  appointments: Appt[]
}

const DOCTOR_SEL_KEY = 'mobile-agenda-doctor-selection'

const { api } = useApi()
const toast = useToast()
const router = useRouter()

const viewingMonth = ref(currentMonthInIst())
const monthAppts = ref<Appt[]>([])
const doctors = ref<Doctor[]>([])
const selectedDoctorIds = ref<number[]>([])
const loading = ref(false)
const activeDate = ref(todayInIst())
const bookOpen = ref(false)
const bookDate = ref<string | null>(null)
const editAppointmentId = ref<number | null>(null)
const detailOpen = ref(false)
const detailAppointmentId = ref<number | null>(null)
const monthNow = currentMonthInIst()

const scrollEl = ref<HTMLElement | null>(null)
const stripEl = ref<HTMLElement | null>(null)
const sentinelMap = new Map<string, HTMLElement>()
const stripBtnMap = new Map<string, HTMLElement>()
let programmaticScroll = false
let pendingScrollDate: string | null = null

const headerMonth = computed(() => viewingMonth.value)
const headerMonthLabel = computed(() => monthLabel(headerMonth.value))
const isViewingToday = computed(() => activeDate.value === todayInIst())

const selectedSet = computed(() => new Set(selectedDoctorIds.value))
const allDoctorsSelected = computed(
  () => doctors.value.length > 0 && doctors.value.every(d => selectedSet.value.has(d.doctor_id))
)

const visibleAppts = computed(() =>
  monthAppts.value.filter(a => selectedSet.value.has(a.doctor_id))
)

const allDates = computed(() => {
  const apptDates = new Set(
    visibleAppts.value.map(a => String(a.appointment_date).slice(0, 10))
  )
  return buildMonthDates(viewingMonth.value, apptDates)
})

const daySections = computed((): DaySection[] => {
  const byDate = new Map<string, Appt[]>()
  for (const a of visibleAppts.value) {
    const d = String(a.appointment_date).slice(0, 10)
    const list = byDate.get(d) || []
    list.push(a)
    byDate.set(d, list)
  }
  return allDates.value.map((meta) => {
    const appointments = (byDate.get(meta.date) || []).slice().sort(
      (a, b) => timeToMinutes(a.appointment_time) - timeToMinutes(b.appointment_time)
    )
    return { date: meta.date, meta, appointments }
  })
})

const nowLabel = ref(formatCurrentTimeIst())
const nowMinutes = ref(currentMinutesInIst())
let nowTimer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  nowTimer = window.setInterval(() => {
    nowLabel.value = formatCurrentTimeIst()
    nowMinutes.value = currentMinutesInIst()
  }, 60_000)
  void bootstrap()
})

onUnmounted(() => {
  if (nowTimer) clearInterval(nowTimer)
})

async function fetchMonth(month: string): Promise<Appt[]> {
  const { from, to } = monthBounds(month)
  const data = await api<{ items: Appt[] }>('/appointments', {
    query: { from, to, limit: 2000 }
  })
  return data.items || []
}

async function loadDoctors() {
  const meta = await api<{ doctors: Doctor[] }>('/appointments/meta')
  doctors.value = meta.doctors || []
  initDoctorSelection()
}

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

function doctorChipLabel(name: string) {
  const cleaned = name.replace(/^dr\.?\s+/i, '').trim()
  const first = cleaned.split(/\s+/)[0] || cleaned
  return first.length > 10 ? `${first.slice(0, 9)}…` : first
}

function doctorDot(color: string | null | undefined) {
  return color || '#0097A7'
}

async function resetToMonth(month: string, focusDate: string) {
  loading.value = true
  programmaticScroll = true
  try {
    sentinelMap.clear()
    stripBtnMap.clear()
    if (!doctors.value.length) await loadDoctors()
    const items = await fetchMonth(month)
    viewingMonth.value = month
    monthAppts.value = items
    activeDate.value = focusDate
    pendingScrollDate = focusDate
    await nextTick()
    scrollToPending()
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to load', color: 'error' })
  } finally {
    loading.value = false
    window.setTimeout(() => { programmaticScroll = false }, 80)
  }
}

async function bootstrap() {
  try {
    await loadDoctors()
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to load doctors', color: 'error' })
  }
  await resetToMonth(currentMonthInIst(), todayInIst())
}

async function reloadLoaded() {
  try {
    monthAppts.value = await fetchMonth(viewingMonth.value)
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Refresh failed', color: 'error' })
  }
}

function setSentinel(date: string, el: Element | null) {
  if (el instanceof HTMLElement) sentinelMap.set(date, el)
  else sentinelMap.delete(date)
}

function setStripBtn(date: string, el: Element | null) {
  if (el instanceof HTMLElement) stripBtnMap.set(date, el)
  else stripBtnMap.delete(date)
}

function revealStripDate(date: string) {
  const btn = stripBtnMap.get(date)
  const container = stripEl.value
  if (!btn || !container) return
  const cRect = container.getBoundingClientRect()
  const bRect = btn.getBoundingClientRect()
  const pad = 8
  if (bRect.left >= cRect.left + pad && bRect.right <= cRect.right - pad) return
  const target = btn.offsetLeft - container.clientWidth / 2 + btn.offsetWidth / 2
  container.scrollTo({
    left: Math.max(0, Math.min(container.scrollWidth - container.clientWidth, target)),
    behavior: 'smooth'
  })
}

function syncActiveFromScroll() {
  if (programmaticScroll || !daySections.value.length) return
  const container = scrollEl.value
  if (!container) return
  const anchor = container.getBoundingClientRect().top + 8
  let next = daySections.value[0]?.date
  for (const section of daySections.value) {
    const el = sentinelMap.get(section.date)
    if (!el) continue
    if (el.getBoundingClientRect().top <= anchor) next = section.date
    else break
  }
  if (next && next !== activeDate.value) {
    activeDate.value = next
    revealStripDate(next)
  }
}

let scrollRaf = 0
function onAgendaScroll() {
  if (scrollRaf) cancelAnimationFrame(scrollRaf)
  scrollRaf = requestAnimationFrame(() => {
    syncActiveFromScroll()
  })
}

function scrollToDate(date: string, behavior: ScrollBehavior = 'smooth') {
  const sentinel = sentinelMap.get(date)
  const container = scrollEl.value
  if (!sentinel || !container) {
    pendingScrollDate = date
    return
  }
  const top =
    sentinel.getBoundingClientRect().top
    - container.getBoundingClientRect().top
    + container.scrollTop
  programmaticScroll = true
  activeDate.value = date
  container.scrollTo({ top: Math.max(0, top), behavior })
  revealStripDate(date)
  window.setTimeout(() => {
    programmaticScroll = false
  }, behavior === 'smooth' ? 450 : 50)
}

function scrollToPending() {
  if (!pendingScrollDate) return
  const date = pendingScrollDate
  pendingScrollDate = null
  scrollToDate(date, 'auto')
  if (date === todayInIst()) {
    window.setTimeout(() => {
      const marker = document.getElementById('agenda-now-marker')
      const container = scrollEl.value
      if (!marker || !container) return
      programmaticScroll = true
      const top =
        marker.getBoundingClientRect().top
        - container.getBoundingClientRect().top
        + container.scrollTop
        - 72
      container.scrollTo({ top: Math.max(0, top), behavior: 'auto' })
      window.setTimeout(() => { programmaticScroll = false }, 50)
    }, 40)
  }
}

watch(daySections, async () => {
  await nextTick()
  if (pendingScrollDate) scrollToPending()
})

function onSelectStripDate(date: string) {
  scrollToDate(date)
}

async function goMonth(delta: number) {
  const target = shiftMonth(viewingMonth.value, delta)
  const jump = target === currentMonthInIst() ? todayInIst() : `${target}-01`
  await resetToMonth(target, jump)
}

async function jumpToToday() {
  await resetToMonth(currentMonthInIst(), todayInIst())
}

function openBook(date?: string) {
  editAppointmentId.value = null
  bookDate.value = date || activeDate.value
  bookOpen.value = true
}

function onApptTap(a: Appt) {
  detailAppointmentId.value = a.appointment_id
  detailOpen.value = true
}

function onDetailEdit(id: number) {
  editAppointmentId.value = id
  bookDate.value = null
  bookOpen.value = true
}

function onDetailOpenPatient(clientId: number) {
  void router.push(`/clients/${clientId}`)
}

async function onDetailUpdated() {
  await reloadLoaded()
}

async function onBooked() {
  bookOpen.value = false
  editAppointmentId.value = null
  await reloadLoaded()
}

function statusTone(status: string) {
  const s = (status || '').toLowerCase()
  if (s.includes('cancel')) return 'bg-slate-100 text-slate-500'
  if (s.includes('no show')) return 'bg-orange-50 text-orange-700'
  if (s.includes('complete')) return 'bg-sky-50 text-sky-700'
  if (s.includes('pending')) return 'bg-amber-50 text-amber-700'
  return 'bg-emerald-50 text-emerald-700'
}

function clockParts(time: string) {
  const label = formatAmPm(time)
  const m = /^(.*)\s(AM|PM)$/.exec(label)
  return m ? { clock: m[1], period: m[2] } : { clock: label, period: '' }
}

function doctorColor(a: Appt) {
  return a.doctor_color || '#0097A7'
}

function doctorInitial(a: Appt) {
  const name = (a.doctor_name || '').replace(/^Dr\.?\s*/i, '').trim()
  return name.charAt(0).toUpperCase() || 'D'
}

function doctorLabel(a: Appt) {
  const name = (a.doctor_name || '').trim()
  if (!name) return '—'
  return /^dr\.?\s/i.test(name) ? name : `Dr. ${name}`
}

function apptMetaParts(a: Appt) {
  const mins = a.duration_minutes && a.duration_minutes > 0
    ? a.duration_minutes
    : Math.max(0, timeToMinutes(a.end_time || '') - timeToMinutes(a.appointment_time)) || 30
  return {
    duration: `${mins}m`,
    service: a.service_name || null,
    doctor: doctorLabel(a) !== '—' ? doctorLabel(a) : null
  }
}

function shouldShowNowBefore(section: DaySection, appt: Appt, idx: number): boolean {
  if (!section.meta.isToday) return false
  const start = timeToMinutes(appt.appointment_time)
  const prevEnd = idx > 0
    ? timeToMinutes(section.appointments[idx - 1].end_time || section.appointments[idx - 1].appointment_time)
    : -1
  return nowMinutes.value >= prevEnd && nowMinutes.value < start
}

function shouldShowNowAtEnd(section: DaySection): boolean {
  if (!section.meta.isToday) return false
  if (!section.appointments.length) return true
  const last = section.appointments[section.appointments.length - 1]
  const end = timeToMinutes(last.end_time || last.appointment_time)
  return nowMinutes.value >= end
}
</script>

<template>
  <div class="relative flex h-full min-h-0 flex-col bg-[#F0F4F8]">
    <div class="shrink-0 bg-[#0097A7] px-4 pb-3 pt-3">
      <div class="mb-2 flex items-center gap-1.5">
        <button
          type="button"
          class="shrink-0 px-1 text-[22px] leading-none text-white"
          aria-label="Previous month"
          @click="goMonth(-1)"
        >
          ‹
        </button>
        <span class="shrink-0 text-base font-semibold text-white">{{ headerMonthLabel }}</span>
        <button
          type="button"
          class="shrink-0 px-1 text-[22px] leading-none text-white"
          aria-label="Next month"
          @click="goMonth(1)"
        >
          ›
        </button>
        <button
          type="button"
          class="ml-auto rounded-full border border-white/40 bg-white/15 px-3 py-1 text-xs font-semibold text-white disabled:opacity-50"
          :disabled="isViewingToday && headerMonth === monthNow"
          @click="jumpToToday"
        >
          Today
        </button>
      </div>

      <div
        v-if="doctors.length"
        class="mb-2 flex gap-1.5 overflow-x-auto [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        <button
          type="button"
          class="inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold transition"
          :class="allDoctorsSelected
            ? 'bg-white text-[#0097A7]'
            : 'bg-white/15 text-white/90 ring-1 ring-white/30'"
          :aria-pressed="allDoctorsSelected"
          @click="toggleAllDoctors"
        >
          All docs
        </button>
        <button
          v-for="d in doctors"
          :key="d.doctor_id"
          type="button"
          class="inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold transition"
          :class="isDoctorSelected(d.doctor_id)
            ? 'bg-white text-[#0097A7]'
            : 'bg-white/15 text-white/90 ring-1 ring-white/30'"
          :aria-pressed="isDoctorSelected(d.doctor_id)"
          @click="toggleDoctor(d.doctor_id)"
        >
          <span
            class="h-2 w-2 shrink-0 rounded-full ring-1 ring-black/10"
            :style="{ background: doctorDot(d.color_code) }"
          />
          {{ doctorChipLabel(d.doctor_name) }}
        </button>
      </div>

      <div
        ref="stripEl"
        class="flex gap-1 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        <button
          v-for="d in allDates"
          :key="d.date"
          :ref="(el) => setStripBtn(d.date, el as Element | null)"
          type="button"
          class="relative w-11 shrink-0 rounded-[10px] py-1.5 text-center transition"
          :class="d.date === activeDate
            ? 'bg-white text-[#0097A7]'
            : d.isToday
              ? 'bg-white/35 text-white ring-2 ring-white/90'
              : 'bg-white/15 text-white/80'"
          :aria-pressed="d.date === activeDate"
          @click="onSelectStripDate(d.date)"
        >
          <div
            class="text-[10px] font-medium"
            :class="d.date === activeDate || d.isToday ? 'font-bold' : ''"
          >
            {{ d.isToday ? 'TODAY' : d.dayName }}
          </div>
          <div
            class="mx-auto mt-px flex h-7 w-7 items-center justify-center rounded-full text-base"
            :class="d.date === activeDate ? 'font-bold text-[#0097A7]' : 'font-medium text-white'"
          >
            {{ d.day }}
          </div>
          <span
            v-if="d.hasAppointments"
            class="absolute bottom-1 left-1/2 h-1 w-1 -translate-x-1/2 rounded-full"
            :class="d.date === activeDate ? 'bg-[#0097A7]' : 'bg-white'"
          />
        </button>
      </div>
    </div>

    <div
      ref="scrollEl"
      class="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-3 pb-24"
      @scroll.passive="onAgendaScroll"
    >
      <p v-if="loading" class="py-12 text-center text-sm text-slate-400">Loading appointments…</p>

      <template v-else>
        <section
          v-for="section in daySections"
          :key="section.date"
          :data-date="section.date"
        >
          <div
            :ref="(el) => setSentinel(section.date, el as Element | null)"
            class="pointer-events-none h-px w-full"
            aria-hidden="true"
          />
          <div
            class="sticky top-0 z-10 -mx-4 flex items-center justify-between gap-2 border-b px-4 py-2 backdrop-blur-sm"
            :class="section.meta.isToday
              ? 'border-[#0097A7]/30 bg-[#0097A7]/10'
              : 'border-slate-200/80 bg-[#F0F4F8]/95'"
          >
            <p class="m-0 flex min-w-0 items-center gap-2 truncate text-sm font-semibold text-[#1C2B35]">
              <span
                v-if="section.meta.isToday"
                class="shrink-0 rounded-md bg-[#0097A7] px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white"
              >
                Today
              </span>
              <span class="truncate">
                {{ section.meta.fullDateLabel }}
                ({{ section.appointments.length }} appt{{ section.appointments.length === 1 ? '' : 's' }})
              </span>
            </p>
            <button
              type="button"
              class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#0097A7] text-base leading-none text-white shadow-sm"
              :aria-label="`Book on ${section.meta.fullDateLabel}`"
              @click="openBook(section.date)"
            >
              +
            </button>
          </div>

          <div class="pb-2 pt-1">
            <template v-if="!section.appointments.length">
              <div
                v-if="section.meta.isToday"
                id="agenda-now-marker"
                class="my-2 flex items-center gap-2"
              >
                <span class="text-[10px] font-semibold text-red-500">{{ nowLabel }}</span>
                <span class="h-px flex-1 bg-red-400" />
              </div>
              <p class="py-2.5 text-center text-xs text-slate-400">No appointments</p>
            </template>

            <template v-else>
              <div
                v-for="(a, idx) in section.appointments"
                :key="a.appointment_id"
              >
                <div
                  v-if="shouldShowNowBefore(section, a, idx)"
                  id="agenda-now-marker"
                  class="my-2 flex items-center gap-2"
                >
                  <span class="text-[10px] font-semibold text-red-500">{{ nowLabel }}</span>
                  <span class="h-px flex-1 bg-red-400" />
                </div>
                <button
                  type="button"
                  class="mb-2 flex w-full gap-2.5 text-left"
                  @click="onApptTap(a)"
                >
                  <div class="w-12 shrink-0 pt-3.5 text-right text-[11px] font-medium text-slate-400">
                    {{ clockParts(a.appointment_time).clock }}
                    <span class="block text-[9px] text-slate-300">
                      {{ clockParts(a.appointment_time).period }}
                    </span>
                  </div>
                  <div class="relative min-w-0 flex-1 rounded-xl border border-slate-200 bg-white px-3 py-2.5 shadow-sm active:bg-slate-50">
                    <div
                      class="absolute bottom-2 left-0 top-2 w-1 rounded-sm"
                      :style="{ background: doctorColor(a) }"
                    />
                    <div class="flex items-start justify-between gap-2 pl-2">
                      <div class="min-w-0">
                        <p class="truncate text-sm font-semibold text-[#1C2B35]">{{ a.name }}</p>
                        <div class="mt-0.5 flex min-w-0 flex-wrap items-center gap-x-1 text-xs text-slate-500">
                          <span class="shrink-0">{{ apptMetaParts(a).duration }}</span>
                          <template v-if="apptMetaParts(a).service">
                            <span class="shrink-0 text-slate-300">·</span>
                            <span class="min-w-0 truncate">{{ apptMetaParts(a).service }}</span>
                          </template>
                          <template v-if="apptMetaParts(a).doctor">
                            <span class="shrink-0 text-slate-300">·</span>
                            <span
                              class="inline-flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full text-[7px] font-semibold text-white"
                              :style="{ background: doctorColor(a) }"
                            >
                              {{ doctorInitial(a) }}
                            </span>
                            <span class="min-w-0 truncate">{{ apptMetaParts(a).doctor }}</span>
                          </template>
                        </div>
                      </div>
                      <span
                        class="shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold"
                        :class="statusTone(a.status)"
                      >
                        {{ a.status }}
                      </span>
                    </div>
                  </div>
                </button>
              </div>
              <div
                v-if="shouldShowNowAtEnd(section)"
                id="agenda-now-marker"
                class="my-2 flex items-center gap-2"
              >
                <span class="text-[10px] font-semibold text-red-500">{{ nowLabel }}</span>
                <span class="h-px flex-1 bg-red-400" />
              </div>
            </template>
          </div>
        </section>
      </template>
    </div>

    <DeskAppointmentDetailModal
      v-model:open="detailOpen"
      :appointment-id="detailAppointmentId"
      @edit="onDetailEdit"
      @updated="onDetailUpdated"
      @open-patient="onDetailOpenPatient"
    />

    <DeskBookModal
      v-model:open="bookOpen"
      :date="bookDate"
      :edit-appointment-id="editAppointmentId"
      @booked="onBooked"
      @saved="onBooked"
    />
  </div>
</template>
