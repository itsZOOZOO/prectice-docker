import { todayInIst } from '~/utils/agendaCalendar'

const IST = 'Asia/Kolkata'

function istDateKey(value: string): string {
  const normalized = value.includes('T') ? value : value.replace(' ', 'T')
  const d = new Date(normalized)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleDateString('en-CA', { timeZone: IST })
}

function shortDateInIst(value: string): string {
  const normalized = value.includes('T') ? value : value.replace(' ', 'T')
  const d = new Date(normalized)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', timeZone: IST })
}

export type LastPaymentRelative = {
  relative: string
  shortDate: string
  isToday: boolean
}

/** Relative label for a past payment date (IST calendar days). */
export function formatLastPaymentRelative(receiptAt: string): LastPaymentRelative {
  const receiptDay = istDateKey(receiptAt)
  const today = todayInIst()
  const shortDate = shortDateInIst(receiptAt)

  if (!receiptDay) {
    return { relative: '', shortDate, isToday: false }
  }

  if (receiptDay === today) {
    return { relative: 'Today', shortDate, isToday: true }
  }

  const receiptMs = new Date(`${receiptDay}T12:00:00`).getTime()
  const todayMs = new Date(`${today}T12:00:00`).getTime()
  const daysAgo = Math.round((todayMs - receiptMs) / 86400000)

  if (daysAgo === 1) {
    return { relative: 'Yesterday', shortDate, isToday: false }
  }
  if (daysAgo > 1 && daysAgo < 7) {
    return { relative: `${daysAgo} days ago`, shortDate, isToday: false }
  }
  if (daysAgo >= 7 && daysAgo < 30) {
    const weeks = Math.floor(daysAgo / 7)
    return {
      relative: weeks === 1 ? '1 week ago' : `${weeks} weeks ago`,
      shortDate,
      isToday: false
    }
  }
  if (daysAgo >= 30) {
    const months = Math.floor(daysAgo / 30)
    return {
      relative: months === 1 ? '1 month ago' : `${months} months ago`,
      shortDate,
      isToday: false
    }
  }

  return { relative: shortDate || 'Earlier', shortDate, isToday: false }
}

export function formatInrAmount(n: number) {
  return `₹${Number(n).toLocaleString('en-IN')}`
}
