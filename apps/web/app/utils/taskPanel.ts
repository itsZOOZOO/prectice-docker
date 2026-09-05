/** IST helpers for mobile tasks panel (aligned with Next.js task-utils). */

import { todayInIst } from '~/utils/agendaCalendar'

export type TaskPanelFilter =
  | 'today'
  | 'overdue'
  | 'future'
  | 'pending'
  | 'completed_today'
  | 'all'

export type TaskPanelScope = 'all' | 'mine'

export function shiftDate(date: string, deltaDays: number): string {
  const [y, m, d] = date.split('-').map(Number)
  const dt = new Date(Date.UTC(y, m - 1, d + deltaDays))
  return dt.toISOString().slice(0, 10)
}

export function taskDateLabel(date: string): string {
  const today = todayInIst()
  const yesterday = shiftDate(today, -1)
  const tomorrow = shiftDate(today, 1)

  if (date === today) return "Today's Tasks"
  if (date === yesterday) return "Yesterday's Tasks"
  if (date === tomorrow) return "Tomorrow's Tasks"

  const selected = new Date(`${date}T12:00:00+05:30`)
  const todayDt = new Date(`${today}T12:00:00+05:30`)
  const diffDays = Math.round((selected.getTime() - todayDt.getTime()) / 86_400_000)

  if (Math.abs(diffDays) < 7) {
    return `${selected.toLocaleDateString('en-IN', { weekday: 'long', timeZone: 'Asia/Kolkata' })}'s Tasks`
  }

  return selected.toLocaleDateString('en-IN', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    timeZone: 'Asia/Kolkata'
  })
}

export function formatTaskDueRelative(date: string, today = todayInIst()): string {
  const selected = new Date(`${date}T12:00:00+05:30`)
  const todayDt = new Date(`${today}T12:00:00+05:30`)
  const diffDays = Math.round((selected.getTime() - todayDt.getTime()) / 86_400_000)

  if (diffDays === 0) return 'today'
  if (diffDays === 1) return 'tomorrow'
  if (diffDays === -1) return 'yesterday'
  if (diffDays > 1) return `in ${diffDays} days`
  return `${Math.abs(diffDays)} days ago`
}

export function formatTaskDueDate(date: string | null): string {
  if (!date) return 'No due date'
  const d = new Date(`${date}T12:00:00+05:30`)
  const absolute = d.toLocaleDateString('en-IN', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    timeZone: 'Asia/Kolkata'
  })
  return `${absolute} (${formatTaskDueRelative(date)})`
}

export function isTaskOpen(status: string) {
  const s = (status || '').trim().toLowerCase()
  return s === 'open' || s === 'pending'
}

export function isTaskOverdue(dueDate: string | null, status: string): boolean {
  if (!dueDate || !isTaskOpen(status)) return false
  return dueDate < todayInIst()
}

export function formatNoteTime(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString('en-IN', {
    day: 'numeric',
    month: 'short',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
    timeZone: 'Asia/Kolkata'
  })
}
