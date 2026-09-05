const IST = 'Asia/Kolkata'

function pickDatePart(parts: Intl.DateTimeFormatPart[], type: Intl.DateTimeFormatPartTypes) {
  return parts.find(p => p.type === type)?.value ?? ''
}

function formatWeekdayDateInZone(
  date: Date,
  options: { day?: 'numeric' | '2-digit', month?: 'short' | 'long', uppercase?: boolean } = {}
) {
  const parts = new Intl.DateTimeFormat('en-US', {
    weekday: 'short',
    day: options.day ?? 'numeric',
    month: options.month ?? 'short',
    year: 'numeric',
    timeZone: IST
  }).formatToParts(date)
  const formatted = `${pickDatePart(parts, 'weekday')}, ${pickDatePart(parts, 'day')} ${pickDatePart(parts, 'month')} ${pickDatePart(parts, 'year')}`
  return options.uppercase ? formatted.toUpperCase() : formatted
}

/** YYYY-MM-DD calendar key in IST. */
export function dateKey(iso: string) {
  try {
    return new Date(iso).toLocaleDateString('en-CA', { timeZone: IST })
  } catch {
    return iso.slice(0, 10)
  }
}

function formatCalendarDayRelative(isoOrKey: string): string {
  const key = /^\d{4}-\d{2}-\d{2}$/.test(isoOrKey.trim()) ? isoOrKey.trim() : dateKey(isoOrKey)
  const today = new Date().toLocaleDateString('en-CA', { timeZone: IST })
  const selected = new Date(`${key}T12:00:00`)
  const todayDt = new Date(`${today}T12:00:00`)
  const diffDays = Math.round((selected.getTime() - todayDt.getTime()) / 86_400_000)

  if (diffDays === 0) return 'today'
  if (diffDays === 1) return 'tomorrow'
  if (diffDays === -1) return 'yesterday'
  if (diffDays > 1) return `in ${diffDays} days`
  return `${Math.abs(diffDays)} days ago`
}

/** Appointment bubble relative day: Today / Tomorrow / After 30 days / 45 days ago. */
export function apptRelativeLabel(dateStr: string): string {
  const key = /^\d{4}-\d{2}-\d{2}$/.test(dateStr.trim()) ? dateStr.trim() : dateKey(dateStr)
  const today = new Date().toLocaleDateString('en-CA', { timeZone: IST })
  const selected = new Date(`${key}T12:00:00`)
  const todayDt = new Date(`${today}T12:00:00`)
  const diff = Math.round((selected.getTime() - todayDt.getTime()) / 86_400_000)

  if (diff < 0) return diff === -1 ? 'Yesterday' : `${Math.abs(diff)} days ago`
  if (diff === 0) return 'Today'
  if (diff === 1) return 'Tomorrow'
  return `After ${diff} days`
}

/** Inline separator: TODAY / YESTERDAY / FRI, 12 SEPTEMBER 2026 (3 days ago) */
export function formatDateSeparator(iso: string) {
  const key = dateKey(iso)
  const today = new Date().toLocaleDateString('en-CA', { timeZone: IST })
  const yesterday = new Date(Date.now() - 86400000).toLocaleDateString('en-CA', {
    timeZone: IST
  })

  if (key === today) return 'TODAY'
  if (key === yesterday) return 'YESTERDAY'

  const absolute = formatWeekdayDateInZone(new Date(iso), {
    day: '2-digit',
    month: 'long',
    uppercase: true
  })
  return `${absolute} (${formatCalendarDayRelative(key)})`
}

/** Book/edit confirm: Mon 05 Sep 2026 (Today) */
export function formatBookConfirmDate(dateStr: string) {
  const key = /^\d{4}-\d{2}-\d{2}$/.test(dateStr.trim()) ? dateStr.trim() : dateKey(dateStr)
  const parts = new Intl.DateTimeFormat('en-GB', {
    weekday: 'short',
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    timeZone: IST
  }).formatToParts(new Date(`${key}T12:00:00+05:30`))
  const absolute = `${pickDatePart(parts, 'weekday')} ${pickDatePart(parts, 'day')} ${pickDatePart(parts, 'month')} ${pickDatePart(parts, 'year')}`
  return `${absolute} (${apptRelativeLabel(key)})`
}

/** Floating pill: Today / Yesterday / Fri, 12 Sep 2026 (3 days ago) */
export function formatFloatingDate(isoOrKey: string) {
  const key = /^\d{4}-\d{2}-\d{2}$/.test(isoOrKey.trim()) ? isoOrKey.trim() : dateKey(isoOrKey)
  const today = new Date().toLocaleDateString('en-CA', { timeZone: IST })
  const yesterday = new Date(Date.now() - 86400000).toLocaleDateString('en-CA', {
    timeZone: IST
  })
  if (key === today) return 'Today'
  if (key === yesterday) return 'Yesterday'
  const absolute = formatWeekdayDateInZone(new Date(`${key}T12:00:00+05:30`))
  return `${absolute} (${formatCalendarDayRelative(key)})`
}
