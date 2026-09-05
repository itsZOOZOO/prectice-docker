export const SETUP_UNLOCK_STORAGE_KEY = 'desk-setup-unlock'

export const SETUP_LOCKED_SETTING_IDS = [
  'setup-pin',
  'doctors-schedules',
  'treatment-templates',
  'clinic-settings',
  'warranty-templates'
] as const

export type SetupLockedSettingId = (typeof SETUP_LOCKED_SETTING_IDS)[number]

export const SETUP_UNLOCK_TTL_OPTIONS = [15, 30, 45, 60, 90, 120] as const

export type SetupAccessStatus = {
  pin_configured: boolean
  unlock_ttl_minutes: number
}

export type SetupUnlockPayload = {
  token: string
  expires_at: number
}

export type StoredSetupUnlock = {
  token: string
  expires_at: number
}

export function readStoredSetupUnlock(): StoredSetupUnlock | null {
  if (!import.meta.client) return null
  try {
    const raw = sessionStorage.getItem(SETUP_UNLOCK_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<StoredSetupUnlock>
    if (!parsed.token || !parsed.expires_at) return null
    return { token: String(parsed.token), expires_at: Number(parsed.expires_at) }
  } catch {
    return null
  }
}

export function writeStoredSetupUnlock(payload: StoredSetupUnlock | null) {
  if (!import.meta.client) return
  if (!payload) {
    sessionStorage.removeItem(SETUP_UNLOCK_STORAGE_KEY)
    return
  }
  sessionStorage.setItem(SETUP_UNLOCK_STORAGE_KEY, JSON.stringify(payload))
}

/** Sync helper for useApi — reads a still-valid unlock token from sessionStorage. */
export function setupUnlockHeaders(): Record<string, string> {
  const stored = readStoredSetupUnlock()
  if (!stored) return {}
  if (stored.expires_at * 1000 <= Date.now()) {
    writeStoredSetupUnlock(null)
    return {}
  }
  return { 'X-Setup-Unlock': stored.token }
}

export function isSetupSectionLocked(id: string): id is SetupLockedSettingId {
  return (SETUP_LOCKED_SETTING_IDS as readonly string[]).includes(id)
}
