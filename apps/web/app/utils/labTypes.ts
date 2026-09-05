export type LabCaseFilter =
  | 'action_needed'
  | 'blocked_on_clinic'
  | 'at_lab'
  | 'at_lab_overdue'
  | 'received_no_future_appointment'
  | 'open'
  | 'closed'
  | 'cancelled'

export type LabCaseSummaryCounts = {
  action_needed: number
  blocked_on_clinic: number
  at_lab: number
  at_lab_overdue: number
  received_no_future_appointment: number
  open: number
}

export type LabCaseListItem = {
  case_id: number
  case_ref: string
  client_id: number
  client_name: string
  profile_photo_url: string | null
  lab_id: number
  lab_name: string
  case_type: string | null
  tooth_numbers: string | null
  description: string | null
  status: 'open' | 'closed' | 'cancelled'
  current_cycle_number: number
  stage: 'send_pending' | 'at_lab' | 'received'
  action_category: string | null
  expected_return_date: string | null
  days_overdue: number | null
  send_pending_at: string | null
  sent_at: string | null
  received_at: string | null
  has_future_appointment: boolean
  created_at: string
  cycles?: {
    cycle_id: number
    cycle_number: number
    stage: string
    send_pending_at: string | null
    sent_at: string | null
    received_at: string | null
    expected_return_date: string | null
    notes: string | null
    created_at: string
  }[]
}

export type DentalLab = {
  lab_id: number
  name: string
  contact_person: string | null
  phone: string | null
  notes: string | null
}

export const LAB_CASE_TYPE_CHIPS = ['Crown & Bridge', 'Denture', 'Implant prosthesis'] as const

export const LAB_FILTER_OPTIONS: {
  value: LabCaseFilter
  label: string
  summaryKey?: keyof LabCaseSummaryCounts
}[] = [
  { value: 'action_needed', label: 'Action needed', summaryKey: 'action_needed' },
  { value: 'blocked_on_clinic', label: 'Send pending', summaryKey: 'blocked_on_clinic' },
  { value: 'at_lab_overdue', label: 'Overdue at lab', summaryKey: 'at_lab_overdue' },
  {
    value: 'received_no_future_appointment',
    label: 'Book appointment',
    summaryKey: 'received_no_future_appointment'
  },
  { value: 'at_lab', label: 'At lab', summaryKey: 'at_lab' },
  { value: 'open', label: 'All open', summaryKey: 'open' }
]

export function labCaseStatusLabel(item: LabCaseListItem): string {
  if (item.action_category === 'blocked_on_clinic') return 'Send pending'
  if (item.action_category === 'at_lab_missing_due') return 'Set due date'
  if (item.action_category === 'at_lab_overdue') {
    const days = item.days_overdue ?? 0
    return days > 0 ? `Overdue ${days}d` : 'Overdue at lab'
  }
  if (item.action_category === 'received_no_future_appointment') return 'Book appointment'
  if (item.action_category === 'at_lab') return 'At lab'
  if (item.stage === 'received') return 'Received'
  if (item.stage === 'at_lab') return 'At lab'
  if (item.status === 'closed') return 'Closed'
  if (item.status === 'cancelled') return 'Cancelled'
  return 'Send pending'
}

export function labCaseStatusColor(item: LabCaseListItem): string {
  if (item.action_category === 'at_lab_overdue') return '#ef4444'
  if (item.action_category === 'at_lab_missing_due') return '#ef4444'
  if (item.action_category === 'blocked_on_clinic') return '#f59e0b'
  if (item.action_category === 'received_no_future_appointment') return '#7c3aed'
  if (item.action_category === 'at_lab') return '#0284c7'
  if (item.status === 'closed') return '#22c55e'
  if (item.status === 'cancelled') return '#94a3b8'
  return '#64748b'
}

/** Mon–Sat open, Sunday closed — matches legacy default clinic hours. */
export function addClinicWorkingDays(startYmd: string, workingDays: number): string {
  if (workingDays <= 0) return startYmd
  const [y, m, d] = startYmd.split('-').map(Number)
  const cursor = new Date(y, m - 1, d)
  let counted = 0
  while (counted < workingDays) {
    cursor.setDate(cursor.getDate() + 1)
    if (cursor.getDay() !== 0) counted += 1
  }
  const yy = cursor.getFullYear()
  const mm = String(cursor.getMonth() + 1).padStart(2, '0')
  const dd = String(cursor.getDate()).padStart(2, '0')
  return `${yy}-${mm}-${dd}`
}

export function todayYmdLocal(): string {
  const d = new Date()
  const offset = d.getTimezoneOffset()
  const local = new Date(d.getTime() - offset * 60000)
  return local.toISOString().slice(0, 10)
}
