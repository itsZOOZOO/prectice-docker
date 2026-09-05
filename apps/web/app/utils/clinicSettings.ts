export type ClinicAppointmentSettings = {
  slot_interval: number
  allow_overlapping_appointments: boolean
  booking_lead_time_hours: number
  max_advance_booking_days: number
  public_booking_min_days_ahead: number
  public_booking_max_days_ahead: number
}

export type ClinicDayHours = {
  day_name: string
  is_working: boolean
  start_time: string
  end_time: string
}

export type ClinicServiceItem = {
  service_id: number
  service_name: string
  duration_minutes: number
  description: string
  is_active: boolean
  allow_public_booking: boolean
}

export type UpsertClinicServiceInput = {
  service_name: string
  duration_minutes: number
  description?: string
}

export type ClinicSettingsTab = 'hours' | 'booking' | 'services'

export const CLINIC_WEEK_DAYS = [
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
  'Sunday'
] as const

export const CLINIC_SETTINGS_TABS: { key: ClinicSettingsTab, label: string }[] = [
  { key: 'hours', label: 'Clinic hours' },
  { key: 'booking', label: 'Booking rules' },
  { key: 'services', label: 'Services' }
]
