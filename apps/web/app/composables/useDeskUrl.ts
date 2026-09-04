export type DeskView = 'dashboard' | 'patients' | 'calendar' | 'tasks'

const VIEW_TITLES: Record<DeskView, string> = {
  dashboard: 'Dashboard',
  patients: 'Patients',
  calendar: 'Calendar',
  tasks: 'Tasks'
}

export function useDeskUrl() {
  const route = useRoute()
  const router = useRouter()

  const view = computed<DeskView>(() => {
    const v = route.query.view
    if (v === 'patients' || v === 'calendar' || v === 'tasks' || v === 'dashboard') return v
    return 'dashboard'
  })

  const patientId = computed<number | null>(() => {
    const raw = route.query.patient
    if (typeof raw !== 'string' || !raw) return null
    const n = Number(raw)
    return Number.isFinite(n) && n > 0 ? n : null
  })

  const title = computed(() => VIEW_TITLES[view.value])

  function buildHref(nextView: DeskView, nextPatientId?: number | null) {
    const query: Record<string, string> = { view: nextView }
    if (nextPatientId) query.patient = String(nextPatientId)
    return { path: '/desk', query }
  }

  async function setView(nextView: DeskView, nextPatientId?: number | null) {
    const patient = nextView === 'patients' ? (nextPatientId ?? patientId.value) : null
    await router.push(buildHref(nextView, patient))
  }

  async function openPatient(id: number) {
    await router.push(buildHref('patients', id))
  }

  async function clearPatient() {
    await router.push(buildHref('patients', null))
  }

  return { view, patientId, title, buildHref, setView, openPatient, clearPatient }
}
