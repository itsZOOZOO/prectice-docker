export type DeskView =
  | 'dashboard'
  | 'patients'
  | 'calendar'
  | 'tasks'
  | 'lab'
  | 'wa-inbox'
  | 'statistics'
  | 'settings'

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

export type SettingsSection =
  | 'clinic-settings'
  | 'doctors-schedules'
  | 'dental-labs'
  | 'whatsapp'
  | 'medicine-templates'
  | 'treatment-templates'
  | 'warranty-templates'
  | 'patient-lists'
  | 'client-tags'
  | 'setup-pin'
  | 'lead-intelligence'

export type StatisticsSection =
  | 'total-patients'
  | 'appointments-overview'
  | 'total-income'
  | 'checkins-overview'
  | 'inquiry-conversion'
  | 'call-statistics'
  | 'lead-intelligence'

const VIEW_TITLES: Record<DeskView, string> = {
  dashboard: 'Dashboard',
  patients: 'Patients',
  calendar: 'Calendar',
  tasks: 'Tasks',
  lab: 'Lab',
  'wa-inbox': 'WhatsApp Inbox',
  statistics: 'Reports',
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

const SETTINGS_SECTIONS = new Set<SettingsSection>([
  'clinic-settings',
  'doctors-schedules',
  'dental-labs',
  'whatsapp',
  'medicine-templates',
  'treatment-templates',
  'warranty-templates',
  'patient-lists',
  'client-tags',
  'setup-pin',
  'lead-intelligence'
])

const STATISTICS_SECTIONS = new Set<StatisticsSection>([
  'total-patients',
  'appointments-overview',
  'total-income',
  'checkins-overview',
  'inquiry-conversion',
  'call-statistics',
  'lead-intelligence'
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
      || v === 'statistics'
      || v === 'wa-inbox'
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

  const settingsSection = computed<SettingsSection | null>(() => {
    const raw = route.query.section
    if (typeof raw === 'string' && SETTINGS_SECTIONS.has(raw as SettingsSection)) {
      return raw as SettingsSection
    }
    return null
  })

  const statisticsSection = computed<StatisticsSection | null>(() => {
    if (view.value !== 'statistics') return null
    const raw = route.query.section
    if (typeof raw === 'string' && STATISTICS_SECTIONS.has(raw as StatisticsSection)) {
      return raw as StatisticsSection
    }
    return null
  })

  const title = computed(() => VIEW_TITLES[view.value])

  function buildHref(opts: {
    view: DeskView
    patientId?: number | null
    cal?: CalMode | null
    date?: string | null
    labFilter?: LabFilter | null
    section?: SettingsSection | StatisticsSection | string | null
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
    if (opts.view === 'settings') {
      const section = opts.section === undefined ? settingsSection.value : opts.section
      if (typeof section === 'string' && SETTINGS_SECTIONS.has(section as SettingsSection)) {
        query.section = section
      }
    }
    if (opts.view === 'statistics') {
      const section = opts.section === undefined ? statisticsSection.value : opts.section
      if (typeof section === 'string' && STATISTICS_SECTIONS.has(section as StatisticsSection)) {
        query.section = section
      }
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
    if (nextView === 'settings') {
      await router.push(buildHref({
        view: 'settings',
        section: settingsSection.value || 'clinic-settings'
      }))
      return
    }
    if (nextView === 'statistics') {
      await router.push(buildHref({
        view: 'statistics',
        section: statisticsSection.value || 'total-patients'
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

  async function setSettingsSection(id: string | null) {
    await router.push(buildHref({
      view: 'settings',
      section: id
    }))
  }

  async function setStatisticsSection(id: string | null) {
    await router.push(buildHref({
      view: 'statistics',
      section: id
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
    labFilter,
    settingsSection,
    statisticsSection,
    title,
    buildHref,
    setView,
    setCalendar,
    setLabFilter,
    setSettingsSection,
    setStatisticsSection,
    openPatient,
    clearPatient,
    todayISO
  }
}
