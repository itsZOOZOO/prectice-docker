export type OverviewTab = 'yearly' | 'monthly'
export type IncomeYearMode = 'calendar' | 'financial'
export type IncomeMonthStatus = 'significant' | 'low' | 'none'

export type FlowChartPoint = {
  label: string
  count: number
}

export type YearlyStatusCount = {
  status: string
  count: number
}

export type YearlyLeadSource = {
  source: string
  total: number
  converted: number
  conversion_pct: number
}

export type ClientsOverviewConversion = {
  overall_pct: number
  converted: number
  not_converted: number
  total: number
}

export type YearlyOverviewClient = {
  client_id: number
  name: string
  number: string
  place: string
  age: number | null
  gender: string
  status: string
  created_at: string | null
}

export type YearlyMonthlyFlow = {
  month: number
  label: string
  count: number
}

export type MonthlyDailyFlow = {
  day: number
  label: string
  count: number
}

export type YearlyClientsOverview = {
  year: number
  start_month: number
  end_month: number
  total_clients: number
  average_per_month: number
  status_counts: YearlyStatusCount[]
  conversion: ClientsOverviewConversion
  lead_sources: YearlyLeadSource[]
  monthly_flow: YearlyMonthlyFlow[]
  clients: YearlyOverviewClient[]
}

export type MonthlyClientsOverview = {
  year: number
  month: number
  month_label: string
  days_in_month: number
  total_clients: number
  average_per_day: number
  status_counts: YearlyStatusCount[]
  conversion: ClientsOverviewConversion
  lead_sources: YearlyLeadSource[]
  daily_flow: MonthlyDailyFlow[]
  clients: YearlyOverviewClient[]
}

export type IncomePaymentModeBreakdown = {
  payment_mode: string
  total: number
  count: number
}

export type IncomeMonthlyFlowPoint = {
  month_key: string
  month: number
  year: number
  label: string
  income: number
  status: IncomeMonthStatus
}

export type YearlyIncomeOverview = {
  year: number
  mode: IncomeYearMode
  start_date: string
  end_date: string
  date_range_label: string
  total_income: number
  average_monthly_income: number
  significant_month_threshold: number
  significant_months: number
  months_in_range: number
  months_with_income: number
  monthly_flow: IncomeMonthlyFlowPoint[]
  payment_modes: IncomePaymentModeBreakdown[]
}

export type IncomeDailyFlowPoint = {
  day: number
  label: string
  income: number
  count: number
}

export type IncomeTransactionRow = {
  receipt_id: number
  client_id: number
  client_name: string
  client_visible: boolean
  amount: number
  payment_mode: string | null
  description: string | null
  receipt_date: string
}

export type MonthlyIncomeOverview = {
  year: number
  month: number
  month_label: string
  month_key: string
  days_in_month: number
  total_income: number
  transaction_count: number
  average_per_day: number
  payment_modes: IncomePaymentModeBreakdown[]
  daily_flow: IncomeDailyFlowPoint[]
  transactions: IncomeTransactionRow[]
}

export type AppointmentDoctorBreakdown = {
  doctor_id: number | null
  doctor_name: string
  total: number
  completed: number
  confirmed: number
  cancelled: number
  no_show: number
  pending: number
  attendance_rate: number
}

export type AppointmentNoShowRow = {
  appointment_id: number
  name: string
  phone: string
  client_id: number | null
  appointment_date: string
  appointment_time: string
  doctor_name: string
  service_name: string
  re_booked: boolean
}

export type AppointmentsOverviewBase = {
  total: number
  completed: number
  confirmed: number
  cancelled: number
  no_show: number
  pending: number
  attendance_rate: number
  shown_count: number
  doctors: AppointmentDoctorBreakdown[]
  no_shows: AppointmentNoShowRow[]
  rebooked_count: number
  rebook_rate: number
}

export type MonthlyAppointmentsOverview = AppointmentsOverviewBase & {
  year: number
  month: number
  month_label: string
  days_in_month: number
  average_per_day: number
  daily_flow: MonthlyDailyFlow[]
}

export type YearlyAppointmentsOverview = AppointmentsOverviewBase & {
  year: number
  start_month: number
  end_month: number
  average_per_month: number
  monthly_flow: YearlyMonthlyFlow[]
}

export type CheckinWeekdayFlow = {
  weekday: number
  label: string
  count: number
}

export type CheckinHourFlow = {
  hour: number
  label: string
  count: number
}

export type MonthlyCheckinsOverview = {
  year: number
  month: number
  month_label: string
  days_in_month: number
  month_total: number
  average_per_day: number
  year_total: number
  year_average_per_day: number
  days_in_year: number
  busiest_weekday: string | null
  busiest_hour: number | null
  busiest_hour_label: string | null
  daily_flow: MonthlyDailyFlow[]
  weekday_flow: CheckinWeekdayFlow[]
  hour_flow: CheckinHourFlow[]
}

export type YearlyCheckinsOverview = {
  year: number
  start_month: number
  end_month: number
  total: number
  average_per_month: number
  average_per_day: number
  days_in_range: number
  busiest_weekday: string | null
  busiest_hour: number | null
  busiest_hour_label: string | null
  monthly_flow: YearlyMonthlyFlow[]
  weekday_flow: CheckinWeekdayFlow[]
  hour_flow: CheckinHourFlow[]
}

export type InquiryConversionMonthRow = {
  month_key: string
  year: number
  month: number
  label: string
  inquiry_count: number
  conversion_count: number
  total_clients: number
  conversion_pct: number
}

export type InquiryConversionOverview = {
  from_date: string
  to_date: string
  date_range_label: string
  total_clients: number
  total_inquiry: number
  total_conversion: number
  avg_conversion_pct: number
  monthly_flow: InquiryConversionMonthRow[]
  conversion_statuses: string[]
  year?: number
  month?: number
  month_label?: string
  mode?: string
}

export const MONTH_OPTIONS = [
  { value: 1, label: 'Jan' },
  { value: 2, label: 'Feb' },
  { value: 3, label: 'Mar' },
  { value: 4, label: 'Apr' },
  { value: 5, label: 'May' },
  { value: 6, label: 'Jun' },
  { value: 7, label: 'Jul' },
  { value: 8, label: 'Aug' },
  { value: 9, label: 'Sep' },
  { value: 10, label: 'Oct' },
  { value: 11, label: 'Nov' },
  { value: 12, label: 'Dec' }
] as const

export const LEAD_SOURCE_COLORS: Record<string, string> = {
  Google: '#4285F4',
  Facebook: '#1877F2',
  Instagram: '#E1306C',
  Referral: '#22c55e',
  'Walk-in': '#f59e0b',
  'Direct Walk-in': '#f97316',
  Other: '#94a3b8',
  Unknown: '#cbd5e1'
}

export const STATISTICS_SECTIONS = [
  'total-patients',
  'appointments-overview',
  'total-income',
  'checkins-overview',
  'inquiry-conversion',
  'call-statistics',
  'lead-intelligence'
] as const

export type StatisticsSection = (typeof STATISTICS_SECTIONS)[number]

export const WAVE2_STATISTICS_SECTIONS = new Set<StatisticsSection>([])

export function formatInr(amount: number): string {
  try {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amount)
  } catch {
    return `₹${Math.round(amount).toLocaleString('en-IN')}`
  }
}

export function shiftMonth(year: number, month: number, delta: number) {
  const date = new Date(year, month - 1 + delta, 1)
  return { year: date.getFullYear(), month: date.getMonth() + 1 }
}

export function formatReceiptWhen(iso: string): string {
  try {
    const d = new Date(iso.includes('T') ? iso : iso.replace(' ', 'T'))
    if (Number.isNaN(d.getTime())) return iso
    return d.toLocaleString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
      timeZone: 'Asia/Kolkata'
    })
  } catch {
    return iso
  }
}

export function statusSummaryClass(status: string): string {
  const s = status.toLowerCase()
  if (s.includes('complet') || s === 'under rx' || s.includes('ortho')) {
    return 'border border-emerald-200 text-emerald-800'
  }
  if (s.includes('inquiry') || s === 'none' || s === 'dnd') {
    return 'border border-slate-200 text-slate-600'
  }
  return 'border border-sky-200 text-sky-800'
}
