export const CLIENT_FILTER_STATUSES = [
  'Inquiry',
  'Under Rx',
  'Ortho',
  'Completed',
  '6m followup',
  'Yearly followup',
  'DND',
  'None'
] as const

export type ClientFilterStatus = (typeof CLIENT_FILTER_STATUSES)[number]

export const CLIENT_FILTER_RELATIVE_DAYS = [7, 15, 30, 60, 90] as const

export type ClientFilterDateMode = 'any' | 'relative' | 'absolute'
export type ClientFilterPresence = 'any' | 'has' | 'none'

export type ClientFilterDateCriteria = {
  mode: ClientFilterDateMode
  relative_days?: number
  from?: string
  to?: string
}

export type ClientFilterCriteria = {
  status_include: string[]
  status_exclude: string[]
  tag_include: string[]
  tag_exclude: string[]
  date: ClientFilterDateCriteria
  future_appointment: ClientFilterPresence
  future_task: ClientFilterPresence
  total_billed_min: number | null
  pending_payment_min: number | null
}

export type ClientFilterRow = {
  filter_id: number
  clinic_id: number
  name: string
  sort_order: number
  show_on_dashboard: boolean
  criteria: ClientFilterCriteria
  manual_member_count: number
  created_at: string
  updated_at: string
}

export type ClientFilterMember = {
  client_id: number
  name: string
  number: string | null
  place: string | null
}

export function emptyClientFilterCriteria(): ClientFilterCriteria {
  return {
    status_include: [],
    status_exclude: [],
    tag_include: [],
    tag_exclude: [],
    date: { mode: 'any' },
    future_appointment: 'any',
    future_task: 'any',
    total_billed_min: null,
    pending_payment_min: null
  }
}

export function normalizeCriteria(raw: Partial<ClientFilterCriteria> | null | undefined): ClientFilterCriteria {
  const base = emptyClientFilterCriteria()
  if (!raw || typeof raw !== 'object') return base
  const dateRaw = raw.date && typeof raw.date === 'object' ? raw.date : { mode: 'any' as const }
  const mode = dateRaw.mode === 'relative' || dateRaw.mode === 'absolute' ? dateRaw.mode : 'any'
  return {
    status_include: Array.isArray(raw.status_include) ? [...raw.status_include] : [],
    status_exclude: Array.isArray(raw.status_exclude) ? [...raw.status_exclude] : [],
    tag_include: Array.isArray(raw.tag_include) ? [...raw.tag_include] : [],
    tag_exclude: Array.isArray(raw.tag_exclude) ? [...raw.tag_exclude] : [],
    date: {
      mode,
      ...(mode === 'relative' && dateRaw.relative_days
        ? { relative_days: Number(dateRaw.relative_days) }
        : {}),
      ...(mode === 'absolute'
        ? { from: String(dateRaw.from || ''), to: String(dateRaw.to || '') }
        : {})
    },
    future_appointment: raw.future_appointment === 'has' || raw.future_appointment === 'none'
      ? raw.future_appointment
      : 'any',
    future_task: raw.future_task === 'has' || raw.future_task === 'none'
      ? raw.future_task
      : 'any',
    total_billed_min: raw.total_billed_min != null && raw.total_billed_min !== ('' as unknown)
      ? Number(raw.total_billed_min) || null
      : null,
    pending_payment_min: raw.pending_payment_min != null && raw.pending_payment_min !== ('' as unknown)
      ? Number(raw.pending_payment_min) || null
      : null
  }
}
