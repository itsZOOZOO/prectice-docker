import type { ClinicDayHours } from '~/utils/clinicSettings'

export type DoctorDetailTab = 'schedule' | 'breaks' | 'time-off' | 'services'

export type DoctorListItem = {
  doctor_id: number
  user_id: number | null
  full_name: string
  doctor_name?: string | null
  username: string
  role: string
  specialization: string
  color_code: string
  is_active: boolean
  user_active: boolean
}

export type EligibleDoctorUser = {
  user_id: number
  full_name: string
  username: string
  role: string
}

export type DoctorBreak = {
  break_id: number
  day_name: string
  break_name: string
  start_time: string
  end_time: string
  allow_booking: boolean
}

export type DoctorTimeOff = {
  time_off_id: number
  start_date: string
  end_date: string
  start_time: string | null
  end_time: string | null
  reason: string
  google_sourced: boolean
  is_approved?: boolean
  is_past: boolean
}

export type DoctorServiceAssignment = {
  service_id: number
  service_name: string
  duration_minutes: number
  assigned: boolean
}

export type DoctorDetail = {
  doctor_id: number
  user_id: number | null
  full_name: string
  doctor_name?: string | null
  username: string
  role: string
  specialization: string
  color_code: string
  is_active: boolean
  schedule: ClinicDayHours[]
  breaks: DoctorBreak[]
  time_off: DoctorTimeOff[]
  services: DoctorServiceAssignment[]
}

export type ClinicTimeOffItem = {
  time_off_id: number
  doctor_id: number
  doctor_name: string
  color_code: string
  start_date: string
  end_date: string
  start_time: string | null
  end_time: string | null
  reason: string
  google_sourced: boolean
  is_approved?: boolean
  is_past?: boolean
}

export type DoctorsListPayload = {
  doctors: DoctorListItem[]
  eligible_users: EligibleDoctorUser[]
  upcoming_time_off?: ClinicTimeOffItem[]
}

export type UpsertDoctorBreakInput = {
  day_name: string
  start_time: string
  end_time: string
  break_name?: string
  allow_booking?: boolean
}

export type AddDoctorTimeOffInput = {
  start_date: string
  end_date: string
  start_time?: string
  end_time?: string
  reason?: string
}

export type TimeOffFormState = {
  doctorId: string
  startDate: string
  endDate: string
  startTime: string
  endTime: string
  fullDay: boolean
  reason: string
}

export const DOCTOR_DETAIL_TABS: { key: DoctorDetailTab, label: string }[] = [
  { key: 'schedule', label: 'Schedule' },
  { key: 'breaks', label: 'Breaks' },
  { key: 'time-off', label: 'Time off' },
  { key: 'services', label: 'Services' }
]

export function formatTimeOffRange(
  item: Pick<DoctorTimeOff, 'start_date' | 'end_date' | 'start_time' | 'end_time'>
): string {
  const isFullDay = !item.start_time && !item.end_time
  if (item.start_date === item.end_date) {
    if (isFullDay) return item.start_date
    return `${item.start_date} · ${item.start_time} – ${item.end_time}`
  }
  if (isFullDay) return `${item.start_date} → ${item.end_date}`
  const start = `${item.start_date} ${item.start_time ?? ''}`.trim()
  const end = `${item.end_date} ${item.end_time ?? ''}`.trim()
  return `${start} → ${end}`
}

function todayYmdLocal(): string {
  const d = new Date()
  const offset = d.getTimezoneOffset()
  const local = new Date(d.getTime() - offset * 60000)
  return local.toISOString().slice(0, 10)
}

export function createDefaultTimeOffForm(doctorId = ''): TimeOffFormState {
  const today = todayYmdLocal()
  return {
    doctorId,
    startDate: today,
    endDate: today,
    startTime: '09:00',
    endTime: '18:00',
    fullDay: true,
    reason: ''
  }
}

export function timeOffFormFromItem(
  item: Pick<DoctorTimeOff | ClinicTimeOffItem, 'start_date' | 'end_date' | 'start_time' | 'end_time' | 'reason'> & {
    doctor_id?: number
  },
  doctorId = ''
): TimeOffFormState {
  const isFullDay = !item.start_time && !item.end_time
  return {
    doctorId: item.doctor_id != null ? String(item.doctor_id) : doctorId,
    startDate: item.start_date,
    endDate: item.end_date,
    startTime: item.start_time ?? '09:00',
    endTime: item.end_time ?? '18:00',
    fullDay: isFullDay,
    reason: item.reason ?? ''
  }
}

export function timeOffPayloadFromForm(form: TimeOffFormState): AddDoctorTimeOffInput {
  return {
    start_date: form.startDate,
    end_date: form.endDate,
    ...(form.fullDay
      ? {}
      : {
          start_time: form.startTime,
          end_time: form.endTime
        }),
    reason: form.reason || undefined
  }
}
