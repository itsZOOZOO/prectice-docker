export type LeadIntelligenceLinkedUser = {
  id: number
  name: string | null
  email: string | null
}

export type LeadIntelligenceClinicStatus = {
  enabled: boolean
  has_api_key: boolean
  can_use: boolean
  can_manage_link: boolean
  linked_user: LeadIntelligenceLinkedUser | null
}

export type LeadIntelligenceAdminStatus = {
  enabled: boolean
  has_api_key: boolean
  token_hint: string | null
  api_base_url: string
  default_api_base_url: string
  can_use: boolean
  linked_user: LeadIntelligenceLinkedUser | null
  smoke_test?: { ok: boolean, linked_user: LeadIntelligenceLinkedUser }
}

export type LeadIntelligenceGroup = {
  id: number
  name: string
  color: string | null
  is_priority: boolean
}

export type LeadIntelligenceRow = {
  id: number
  display_name: string
  phone: string
  created_at: string | null
  first_contact_date: string | null
  response_minutes: number | null
  response_time_label: string
  inquiry_on_duty?: boolean
  groups: LeadIntelligenceGroup[]
}

export type LeadIntelligenceDutyBucket = {
  count: number
  avg_response_minutes: number | null
  avg_response_label: string
  label?: string
  motivation?: string
  tone?: string
}

export type LeadIntelligenceSummary = {
  leads_received: number
  leads_contacted: number
  contact_rate: number
  avg_response_minutes: number | null
  avg_response_label: string
  response_categories: {
    under_5min: number
    between_5_15min: number
    between_15_30min: number
    over_30min: number
  }
  on_duty?: LeadIntelligenceDutyBucket
  off_duty?: LeadIntelligenceDutyBucket
}

export type LeadIntelligenceInquiryTimingCounts = {
  on: number
  off: number
  total: number
}

export type LeadIntelligenceResponseLog = {
  period: string
  period_label: string
  date_from: string
  date_to: string
  ym?: string | null
  limit: number
  duty?: string
  duty_label?: string
  duty_today_banner?: string
  duty_week_summary?: string
  groups_auto_applied?: boolean
  all_groups?: boolean
  group_or?: number[]
  group_and?: number[]
  available_groups?: LeadIntelligenceGroup[]
  priority_group_ids?: number[]
  inquiry_timing_counts?: LeadIntelligenceInquiryTimingCounts
  summary: LeadIntelligenceSummary
  rows: LeadIntelligenceRow[]
}

export type LeadIntelligencePeriod = '7d' | '15d' | '30d' | 'month' | 'custom'
export type LeadIntelligenceDuty = 'on' | 'off' | 'all'

export function leadIntelligenceDutyLabel(duty: LeadIntelligenceDuty): string {
  if (duty === 'on') return 'Duty hours only'
  if (duty === 'off') return 'Off-duty only'
  return 'Both (on + off duty)'
}

export function isInquiryOnDuty(value: LeadIntelligenceRow['inquiry_on_duty']): boolean {
  return value === true
}

export function formatLeadDateTime(value: string | null): string {
  if (!value) return '—'
  const d = new Date(value.includes('T') ? value : value.replace(' ', 'T'))
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString('en-IN', {
    timeZone: 'Asia/Kolkata',
    weekday: 'short',
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit'
  })
}

export function responseMinutesTone(
  minutes: number | null,
  inquiryOnDuty = true
): 'ok' | 'info' | 'warn' | 'bad' | 'muted' {
  if (minutes === null) return 'muted'
  if (!inquiryOnDuty) return 'muted'
  if (minutes <= 5) return 'ok'
  if (minutes <= 15) return 'info'
  if (minutes <= 30) return 'warn'
  return 'bad'
}

export function contactRateTone(rate: number): 'ok' | 'warn' | 'bad' {
  if (rate >= 80) return 'ok'
  if (rate >= 50) return 'warn'
  return 'bad'
}

export function avgResponseTone(minutes: number | null): 'ok' | 'info' | 'warn' | 'bad' | 'muted' {
  if (minutes === null) return 'muted'
  if (minutes <= 5) return 'ok'
  if (minutes <= 15) return 'info'
  if (minutes <= 30) return 'warn'
  return 'bad'
}

export function currentYmInIst(): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Kolkata',
    year: 'numeric',
    month: '2-digit'
  })
    .format(new Date())
    .slice(0, 7)
}

export function shiftYm(ym: string, delta: number): string {
  const [y, m] = ym.split('-').map(Number)
  const d = new Date(Date.UTC(y!, (m! - 1) + delta, 1))
  const yy = d.getUTCFullYear()
  const mm = String(d.getUTCMonth() + 1).padStart(2, '0')
  return `${yy}-${mm}`
}

export function toneText(tone: string): string {
  if (tone === 'ok' || tone === 'excellent') return 'text-emerald-700'
  if (tone === 'info' || tone === 'good') return 'text-cyan-700'
  if (tone === 'warn' || tone === 'poor') return 'text-amber-700'
  if (tone === 'bad' || tone === 'critical') return 'text-red-700'
  return 'text-slate-600'
}

export function toneBadge(tone: string): string {
  if (tone === 'ok' || tone === 'excellent') return 'bg-emerald-100 text-emerald-900'
  if (tone === 'info' || tone === 'good') return 'bg-cyan-100 text-cyan-900'
  if (tone === 'warn' || tone === 'poor') return 'bg-amber-100 text-amber-900'
  if (tone === 'bad' || tone === 'critical') return 'bg-red-100 text-red-800'
  return 'bg-slate-100 text-slate-600'
}
