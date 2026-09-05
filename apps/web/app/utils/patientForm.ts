export const CLIENT_STATUSES = [
  'Inquiry',
  'Under Rx',
  'Completed',
  '6m followup',
  'Yearly followup',
  'DND',
  'Ortho'
] as const

export const LEAD_SOURCES = [
  'Google',
  'Facebook',
  'Instagram',
  'Referral',
  'Walk-in',
  'Direct Walk-in',
  'Other'
] as const

export const PHONE_TYPES = [
  'Primary',
  'Calling',
  'Father',
  'Mother',
  'Son',
  'Daughter',
  'Spouse',
  'Guardian',
  'Emergency',
  'Alternate'
] as const

export const COUNTRY_CODES = ['+91', '+1', '+256', '+44'] as const

export type PatientPhoneDraft = {
  key: string
  phone_id?: number
  country_code: string
  phone_number: string
  phone_type: string
  notes: string
  is_primary: boolean
}

export function ageFromDob(isoDate: string): number | null {
  if (!isoDate || !/^\d{4}-\d{2}-\d{2}$/.test(isoDate)) return null
  const [y, m, d] = isoDate.split('-').map(Number)
  const born = new Date(y, m - 1, d)
  if (Number.isNaN(born.getTime())) return null
  const today = new Date()
  let age = today.getFullYear() - born.getFullYear()
  const md = today.getMonth() - born.getMonth()
  if (md < 0 || (md === 0 && today.getDate() < born.getDate())) age -= 1
  return age >= 0 && age < 130 ? age : null
}

export function newPhoneDraft(primary = false): PatientPhoneDraft {
  return {
    key: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    country_code: '+91',
    phone_number: '',
    phone_type: primary ? 'Primary' : 'Calling',
    notes: '',
    is_primary: primary
  }
}

export type PatientFormInitial = {
  name?: string
  photoUrl?: string | null
  phones?: Array<{
    phone_id?: number
    country_code?: string
    phone_number: string
    phone_type?: string | null
    notes?: string | null
    is_primary?: boolean
  }>
  date_of_birth?: string | null
  age?: number | null
  gender?: string | null
  place?: string | null
  lead_source?: string | null
  reference?: string | null
  status?: string | null
  client_personal_note?: string | null
}
