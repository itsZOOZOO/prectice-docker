/** IST calendar helpers for mobile appointments agenda. */

export function todayInIst(): string {
  return new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' })
}

export function currentMonthInIst(): string {
  return todayInIst().slice(0, 7)
}

export function monthFromDate(date: string): string {
  return date.slice(0, 7)
}

export function shiftMonth(month: string, delta: number): string {
  const [y, mo] = month.split('-').map(Number)
  const d = new Date(Date.UTC(y, mo - 1 + delta, 1))
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}`
}

export function daysInMonth(month: string): number {
  const [y, m] = month.split('-').map(Number)
  return new Date(Date.UTC(y, m, 0)).getUTCDate()
}

export function monthBounds(month: string): { from: string, to: string } {
  const last = daysInMonth(month)
  return {
    from: `${month}-01`,
    to: `${month}-${String(last).padStart(2, '0')}`
  }
}

export function monthLabel(month: string): string {
  const [y, m] = month.split('-').map(Number)
  const d = new Date(Date.UTC(y, m - 1, 1))
  return d.toLocaleDateString('en-IN', { month: 'long', year: 'numeric', timeZone: 'UTC' })
}

export type DateStripItem = {
  date: string
  day: number
  dayName: string
  fullDateLabel: string
  isToday: boolean
  hasAppointments: boolean
}

export function buildMonthDates(month: string, apptDates: Set<string>): DateStripItem[] {
  const today = todayInIst()
  const last = daysInMonth(month)
  const items: DateStripItem[] = []
  for (let day = 1; day <= last; day++) {
    const date = `${month}-${String(day).padStart(2, '0')}`
    const noon = new Date(`${date}T12:00:00+05:30`)
    items.push({
      date,
      day,
      dayName: noon.toLocaleDateString('en-IN', { weekday: 'short', timeZone: 'Asia/Kolkata' }),
      fullDateLabel: noon.toLocaleDateString('en-IN', {
        weekday: 'long',
        day: 'numeric',
        month: 'long',
        timeZone: 'Asia/Kolkata'
      }),
      isToday: date === today,
      hasAppointments: apptDates.has(date)
    })
  }
  return items
}

export function formatCurrentTimeIst(now = new Date()): string {
  return now.toLocaleTimeString('en-IN', {
    timeZone: 'Asia/Kolkata',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true
  })
}

export function currentMinutesInIst(now = new Date()): number {
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Kolkata',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  }).formatToParts(now)
  const h = Number(parts.find(p => p.type === 'hour')?.value || 0)
  const m = Number(parts.find(p => p.type === 'minute')?.value || 0)
  return h * 60 + m
}

export function timeToMinutes(hhmm: string): number {
  const m = /^(\d{1,2}):(\d{2})/.exec(hhmm.trim())
  if (!m) return 0
  return Number(m[1]) * 60 + Number(m[2])
}
