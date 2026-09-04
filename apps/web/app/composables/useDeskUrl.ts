export type DeskView = 'dashboard' | 'patients' | 'calendar' | 'tasks' | 'settings'
export type CalMode = 'day' | 'month'

const VIEW_TITLES: Record<DeskView, string> = {
  dashboard: 'Dashboard',
  patients: 'Patients',
  calendar: 'Calendar',
  tasks: 'Tasks',
  settings: 'Settings'
}

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
    if (v === 'patients' || v === 'calendar' || v === 'tasks' || v === 'dashboard' || v === 'settings') return v
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

  const title = computed(() => VIEW_TITLES[view.value])

  function buildHref(opts: {
    view: DeskView
    patientId?: number | null
    cal?: CalMode | null
    date?: string | null
  }) {
    const query: Record<string, string> = { view: opts.view }
    if (opts.view === 'patients' && opts.patientId) {
      query.patient = String(opts.patientId)
    }
    if (opts.view === 'calendar') {
      query.cal = opts.cal || 'month'
      query.date = opts.date || todayISO()
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
    title,
    buildHref,
    setView,
    setCalendar,
    openPatient,
    clearPatient,
    todayISO
  }
}
