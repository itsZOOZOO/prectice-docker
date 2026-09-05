export type ActivityEventType =
  | 'client.created'
  | 'appointment.booked'
  | 'appointment.status_changed'
  | (string & {})

export type ActivityEventFilter = '' | ActivityEventType

export type ActivityEventPayload = {
  name?: string
  appointment_date?: string
  appointment_time?: string
  old_status?: string
  new_status?: string
  [key: string]: unknown
}

export type ActivityEvent = {
  id: number
  event_type: ActivityEventType
  entity_type: string
  entity_id: number
  client_id: number | null
  payload: ActivityEventPayload | null
  created_at: string
  actor_name: string | null
  client_name: string | null
}

export type ActivityFeedPayload = {
  events: ActivityEvent[]
  has_more: boolean
  next_before_id: number | null
}

export const ACTIVITY_FEED_PAGE_SIZE = 30

export const ACTIVITY_TYPE_FILTERS: { key: ActivityEventFilter, label: string }[] = [
  { key: '', label: 'All events' },
  { key: 'client.created', label: 'Client created' },
  { key: 'appointment.booked', label: 'Appointment booked' },
  { key: 'appointment.status_changed', label: 'Status changed' }
]

export function activityEventLabel(type: ActivityEventType) {
  switch (type) {
    case 'client.created':
      return 'Client created'
    case 'appointment.booked':
      return 'Appointment booked'
    case 'appointment.status_changed':
      return 'Status changed'
    default:
      return type
  }
}

export function activityEventBadgeClass(type: ActivityEventType) {
  switch (type) {
    case 'client.created':
      return 'bg-[#0097A7] text-white'
    case 'appointment.booked':
      return 'bg-emerald-600 text-white'
    case 'appointment.status_changed':
      return 'bg-amber-500 text-white'
    default:
      return 'bg-slate-500 text-white'
  }
}

const IST = 'Asia/Kolkata'

function parseIsoDate(value: string): Date | null {
  const d = new Date(value.includes('T') ? value : value.replace(' ', 'T'))
  return Number.isNaN(d.getTime()) ? null : d
}

function formatShortDate(iso: string) {
  const d = parseIsoDate(iso)
  if (!d) return ''
  return d.toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: IST
  })
}

function formatShortTime(iso: string) {
  const d = parseIsoDate(iso)
  if (!d) return ''
  return d.toLocaleTimeString('en-IN', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
    timeZone: IST
  })
}

function formatClockTime(time: string) {
  const parts = time.trim().split(':')
  if (parts.length < 2) return ''
  const hours = Number(parts[0])
  const minutes = Number(parts[1])
  if (!Number.isFinite(hours) || !Number.isFinite(minutes)) return ''
  const period = hours >= 12 ? 'PM' : 'AM'
  const h12 = hours % 12 || 12
  return `${h12}:${String(minutes).padStart(2, '0')} ${period}`
}

function formatAppointmentSlotTime(dateRaw: string, timeRaw: string) {
  const time = timeRaw.trim()
  if (!time) return ''
  const date = dateRaw.trim().slice(0, 10)
  if (date) {
    const formatted = formatShortTime(`${date}T${time}`)
    if (formatted) return formatted
  }
  return formatClockTime(time)
}

export function formatActivityDateTime(iso: string) {
  const d = parseIsoDate(iso)
  if (!d) return iso
  return d.toLocaleString('en-IN', {
    day: 'numeric',
    month: 'short',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
    timeZone: IST
  })
}

export function activityEventDisplay(event: ActivityEvent): { patientName: string, detail: string | null } {
  const payload = event.payload ?? {}
  const patientName = (payload.name ?? event.client_name ?? '').toString().trim() || 'Unknown'

  switch (event.event_type) {
    case 'client.created':
      return { patientName, detail: null }
    case 'appointment.booked': {
      const dateRaw = payload.appointment_date ? String(payload.appointment_date) : ''
      const timeRaw = payload.appointment_time ? String(payload.appointment_time) : ''
      const date = dateRaw ? formatShortDate(dateRaw) : ''
      const time = timeRaw ? formatAppointmentSlotTime(dateRaw, timeRaw) : ''
      const detail = [date, time].filter(Boolean).join(' — ')
      return { patientName, detail: detail || null }
    }
    case 'appointment.status_changed':
      return {
        patientName,
        detail: `${payload.old_status ?? '?'} → ${payload.new_status ?? '?'}`
      }
    default:
      return { patientName, detail: null }
  }
}

const STORAGE_KEY = 'activity-last-seen-id'

export function hasActivityReadBaseline() {
  try {
    return localStorage.getItem(STORAGE_KEY) != null
  } catch {
    return false
  }
}

export function readLastSeenActivityId() {
  try {
    const id = Number(localStorage.getItem(STORAGE_KEY))
    return Number.isFinite(id) && id > 0 ? id : 0
  } catch {
    return 0
  }
}

export function markActivitySeenUpTo(eventId: number) {
  if (!Number.isFinite(eventId) || eventId <= 0) return false
  try {
    const current = readLastSeenActivityId()
    if (eventId <= current) return false
    localStorage.setItem(STORAGE_KEY, String(eventId))
    return true
  } catch {
    return false
  }
}

/** Count events newer than localStorage last-seen id (Next parity). */
export async function fetchUnreadActivityCount(
  fetchPage: (params: { limit: number, before_id?: number }) => Promise<ActivityFeedPayload>
): Promise<number> {
  if (!hasActivityReadBaseline()) {
    const data = await fetchPage({ limit: 1 })
    const newestId = data.events[0]?.id
    if (newestId) markActivitySeenUpTo(newestId)
    return 0
  }

  const lastSeenId = readLastSeenActivityId()
  let unread = 0
  let beforeId: number | undefined
  const scanSize = 100
  const maxPages = 20

  for (let page = 0; page < maxPages; page++) {
    const data = await fetchPage({
      limit: scanSize,
      before_id: beforeId
    })
    for (const event of data.events) {
      if (event.id > lastSeenId) unread++
      else return unread
    }
    if (!data.has_more || !data.next_before_id) return unread
    beforeId = data.next_before_id
  }
  return unread
}
