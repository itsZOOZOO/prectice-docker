/** Format "HH:MM" or "HH:MM:SS" as "9:30 AM". Returns original string if unparseable. */
export function formatAmPm(time: string | null | undefined): string {
  if (!time) return ''
  const m = /^(\d{1,2}):(\d{2})/.exec(time.trim())
  if (!m) return time
  let hour = Number(m[1])
  const minute = m[2]
  if (!Number.isFinite(hour) || hour < 0 || hour > 23) return time
  const ampm = hour >= 12 ? 'PM' : 'AM'
  hour = hour % 12 || 12
  return `${hour}:${minute} ${ampm}`
}
