export type DeskView = 'dashboard' | 'patients' | 'calendar' | 'tasks' | 'lab' | 'settings'
export type CalMode = 'day' | 'month'
export type LabFilter =
  | 'action_needed'
  | 'blocked_on_clinic'
  | 'at_lab'
  | 'at_lab_overdue'
  | 'received_no_future_appointment'
  | 'open'
  | 'closed'
  | 'cancelled'

const VIEW_TITLES: Record<DeskView, string> = {
  dashboard: 'Dashboard',
  patients: 'Patients',
  calendar: 'Calendar',
  tasks: 'Tasks',
  lab: 'Lab',
  settings: 'Settings'
}

const LAB_FILTERS = new Set<LabFilter>([
  'action_needed',
  'blocked_on_clinic',
  'at_lab',
  'at_lab_overdue',
  'received_no_future_appointment',
  'open',
  'closed',
  'cancelled'
])

function todayISO() {
  const d = new Date()
  const offset = d.getTimezoneOffset()
  const local = new Date(d.getTime() - offset * 60000)
  return local.toISOString().slice(0, 10)
}

export function useDeskUrl() {
  const route = useRoute()
  const router = useRouter()

  const view = computed<DeskView>(() => {
    const v = route.query.view
    if (
      v === 'patients'
      || v === 'calendar'
      || v === 'tasks'
      || v === 'lab'
      || v === 'dashboard'
      || v === 'settings'
    ) {
      return v
    }
    return 'dashboard'
  })

  const patientId = computed<number | null>(() => {
    const raw = route.query.patient
    if (typeof raw !== 'string' || !raw) return null
    const n = Number(raw)
    return Number.isFinite(n) && n > 0 ? n : null
  })

  const calMode = computed<CalMode>(() => {
    if (route.query.cal === 'day') return 'day'
    return 'month'
  })

  const calDate = computed(() => {
    const raw = route.query.date
    if (typeof raw === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw
    return todayISO()
  })

  const labFilter = computed<LabFilter>(() => {
    const raw = route.query.labFilter
    if (typeof raw === 'string' && LAB_FILTERS.has(raw as LabFilter)) return raw as LabFilter
    return 'action_needed'
  })

  const title = computed(() => VIEW_TITLES[view.value])

  function buildHref(opts: {
    view: DeskView
    patientId?: number | null
    cal?: CalMode | null
    date?: string | null
    labFilter?: LabFilter | null
  }) {
    const query: Record<string, string> = { view: opts.view }
    if (opts.view === 'patients' && opts.patientId) {
      query.patient = String(opts.patientId)
    }
    if (opts.view === 'calendar') {
      query.cal = opts.cal || 'month'
      query.date = opts.date || todayISO()
    }
    if (opts.view === 'lab') {
      query.labFilter = opts.labFilter || 'action_needed'
    }
    return { path: '/desk', query }
  }

  async function setView(nextView: DeskView, nextPatientId?: number | null) {
    if (nextView === 'calendar') {
      await router.push(buildHref({
        view: 'calendar',
        cal: 'month',
        date: todayISO()
      }))
      return
    }
    if (nextView === 'lab') {
      await router.push(buildHref({
        view: 'lab',
        labFilter: labFilter.value
      }))
      return
    }
    await router.push(buildHref({
      view: nextView,
      patientId: nextView === 'patients' ? (nextPatientId ?? patientId.value) : null
    }))
  }

  async function setCalendar(opts: { cal?: CalMode, date?: string }) {
    await router.push(buildHref({
      view: 'calendar',
      cal: opts.cal ?? calMode.value,
      date: opts.date ?? calDate.value
    }))
  }

  async function setLabFilter(next: LabFilter) {
    await router.push(buildHref({ view: 'lab', labFilter: next }))
  }

  async function openPatient(id: number) {
    await router.push(buildHref({ view: 'patients', patientId: id }))
  }

  async function clearPatient() {
    await router.push(buildHref({ view: 'patients', patientId: null }))
  }

  return {
    view,
    patientId,
    calMode,
    calDate,
    labFilter,
    title,
    buildHref,
    setView,
    setCalendar,
    setLabFilter,
    openPatient,
    clearPatient,
    todayISO
  }
}
