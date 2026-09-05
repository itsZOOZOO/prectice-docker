export type CallStatisticsView =
  | 'all_first'
  | 'answered_first'
  | 'missed_first'
  | 'answered_later'
  | 'we_called_back'
  | 'abandoned'

export type CallPriorityDevice = {
  device_id: string
  device_name: string
  device_model: string
  last_seen_at: string | null
}

export type CallTag = {
  id: number
  name: string
  color: string
}

export type CallStatisticsStats = {
  first_time: number
  answered_first: number
  missed_first: number
  answered_later: number
  we_called_back: number
  called_other_dev: number
  abandoned: number
}

export type CallFollowUp = {
  id: number
  call_date: string
  duration: number
  elapsed_seconds: number
  s3_key: string | null
  device_id?: string
  device_name?: string
  other_device?: boolean
}

export type CallStatisticsRow = {
  id: number
  contact_name: string
  caller_number: string
  caller_number_normalized: string
  call_date: string
  call_type: 'INCOMING' | 'OUTGOING' | 'MISSED' | string
  duration: number
  outcome:
    | 'answered_first'
    | 'answered_later'
    | 'we_called_back'
    | 'called_other_device'
    | 'abandoned'
  s3_key: string | null
  tags: CallTag[]
  note: string | null
  retry_in: CallFollowUp | null
  callback_out: CallFollowUp | null
}

export type CallStatisticsReport = {
  stats: CallStatisticsStats
  calls: CallStatisticsRow[]
  pagination: {
    page: number
    per_page: number
    total_rows: number
    total_pages: number
  }
  meta: {
    device_id: string
    device_name: string
    date_from: string
    date_to: string
    view: CallStatisticsView
  }
}

export type CallIntelligenceClinicStatus = {
  enabled: boolean
  has_token: boolean
  can_use: boolean
}

export type CallIntelligenceAdminStatus = {
  enabled: boolean
  has_token: boolean
  token_hint: string | null
  api_base_url: string
  default_api_base_url: string
  can_use: boolean
  smoke_test?: { ok: boolean, devices_count: number }
}

export const CALL_STATISTICS_VIEW_LABELS: Record<CallStatisticsView, string> = {
  all_first: 'All First-Time',
  answered_first: 'Answered 1st Ring',
  missed_first: 'Missed 1st Ring',
  answered_later: 'Answered 2nd+ Ring',
  we_called_back: 'We Called Back',
  abandoned: 'Abandoned'
}

export function callStatisticsViewCount(view: CallStatisticsView, stats: CallStatisticsStats): number {
  switch (view) {
    case 'answered_first': return stats.answered_first
    case 'missed_first': return stats.missed_first
    case 'answered_later': return stats.answered_later
    case 'we_called_back': return stats.we_called_back
    case 'abandoned': return stats.abandoned
    default: return stats.first_time
  }
}

export function formatCallPct(part: number, whole: number): string {
  if (whole <= 0) return '0%'
  return `${Math.round((part / whole) * 100)}%`
}

export function formatCallDuration(seconds: number): string {
  if (seconds <= 0) return '—'
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return m > 0 ? `${m}m ${s}s` : `${s}s`
}

export function formatCallElapsed(seconds: number): string {
  const secs = Math.max(0, seconds)
  if (secs < 60) return `${secs}s`
  if (secs < 3600) {
    const m = Math.floor(secs / 60)
    return `${m}m ${secs % 60}s`
  }
  if (secs < 86400) {
    const h = Math.floor(secs / 3600)
    const m = Math.floor((secs % 3600) / 60)
    return m > 0 ? `${h}h ${m}m` : `${h}h`
  }
  const d = Math.floor(secs / 86400)
  const h = Math.floor((secs % 86400) / 3600)
  return h > 0 ? `${d}d ${h}h` : `${d}d`
}

export function formatCallDateTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString('en-IN', {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
      timeZone: 'Asia/Kolkata'
    })
  } catch {
    return iso
  }
}

export function defaultCallDateRange() {
  const to = new Date()
  const from = new Date()
  from.setDate(from.getDate() - 29)
  return {
    dateFrom: from.toISOString().slice(0, 10),
    dateTo: to.toISOString().slice(0, 10)
  }
}
