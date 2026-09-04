/** `datetime-local` value (YYYY-MM-DDTHH:mm) in local wall time. */
export function localDatetimeInputValue(date = new Date()) {
  const offset = date.getTimezoneOffset() * 60000
  return new Date(date.getTime() - offset).toISOString().slice(0, 16)
}

export function noteDatetimeDiffersFromNow(value: string, date = new Date()) {
  return value.slice(0, 16) !== localDatetimeInputValue(date).slice(0, 16)
}

export function formatNoteDatetimePreview(value: string) {
  try {
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return value
    return date.toLocaleString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    })
  } catch {
    return value
  }
}
