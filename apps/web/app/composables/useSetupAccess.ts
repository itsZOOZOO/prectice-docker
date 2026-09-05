import {
  isSetupSectionLocked,
  readStoredSetupUnlock,
  setupUnlockHeaders,
  writeStoredSetupUnlock,
  type SetupAccessStatus,
  type SetupUnlockPayload
} from '~/utils/setupAccess'

export {
  SETUP_LOCKED_SETTING_IDS,
  SETUP_UNLOCK_TTL_OPTIONS,
  setupUnlockHeaders,
  isSetupSectionLocked,
  type SetupAccessStatus,
  type SetupUnlockPayload
} from '~/utils/setupAccess'

export function useSetupAccess() {
  const { api } = useApi()

  const status = useState<SetupAccessStatus | null>('setup-access-status', () => null)
  const unlockToken = useState<string | null>('setup-access-token', () => null)
  const expiresAt = useState<number | null>('setup-access-expires', () => null)
  const hydrated = useState('setup-access-hydrated', () => false)
  const nowTick = useState('setup-access-now', () => Date.now())

  let tickTimer: ReturnType<typeof setInterval> | null = null

  function hydrateFromStorage() {
    if (!import.meta.client || hydrated.value) return
    const stored = readStoredSetupUnlock()
    if (stored && stored.expires_at * 1000 > Date.now()) {
      unlockToken.value = stored.token
      expiresAt.value = stored.expires_at
    } else if (stored) {
      writeStoredSetupUnlock(null)
      unlockToken.value = null
      expiresAt.value = null
    }
    hydrated.value = true
  }

  function persistUnlock(payload: SetupUnlockPayload) {
    unlockToken.value = payload.token
    expiresAt.value = payload.expires_at
    writeStoredSetupUnlock({ token: payload.token, expires_at: payload.expires_at })
  }

  const isUnlocked = computed(() => {
    hydrateFromStorage()
    if (!unlockToken.value || !expiresAt.value) return false
    return expiresAt.value * 1000 > nowTick.value
  })

  const minutesRemaining = computed(() => {
    if (!isUnlocked.value || !expiresAt.value) return null
    return Math.max(1, Math.ceil((expiresAt.value * 1000 - nowTick.value) / 60_000))
  })

  const pinConfigured = computed(() => Boolean(status.value?.pin_configured))

  const locking = ref(false)

  function needsUnlock(sectionId: string): boolean {
    if (!isSetupSectionLocked(sectionId)) return false
    if (!pinConfigured.value) return false
    return !isUnlocked.value
  }

  function startTicker() {
    if (!import.meta.client || tickTimer) return
    tickTimer = setInterval(() => {
      nowTick.value = Date.now()
      if (expiresAt.value && expiresAt.value * 1000 <= Date.now()) {
        unlockToken.value = null
        expiresAt.value = null
        writeStoredSetupUnlock(null)
      }
    }, 15_000)
  }

  async function fetchStatus() {
    hydrateFromStorage()
    const data = await api<SetupAccessStatus>('/settings/setup-access')
    status.value = data
    return data
  }

  async function unlock(pin: string) {
    const data = await api<SetupUnlockPayload>('/settings/setup-access/unlock', {
      method: 'POST',
      body: { pin: pin.trim() }
    })
    persistUnlock(data)
    await fetchStatus()
    return data
  }

  async function createPin(pin: string, confirmPin: string) {
    const data = await api<SetupAccessStatus>('/settings/setup-access/pin', {
      method: 'POST',
      body: { pin: pin.trim(), confirm_pin: confirmPin.trim() }
    })
    status.value = data
    return data
  }

  async function changePin(currentPin: string, newPin: string, confirmPin: string) {
    await api<{ changed: boolean }>('/settings/setup-access/pin', {
      method: 'PATCH',
      body: {
        current_pin: currentPin.trim(),
        new_pin: newPin.trim(),
        confirm_pin: confirmPin.trim()
      }
    })
    await fetchStatus()
  }

  async function setTtl(minutes: number) {
    const data = await api<{ unlock_ttl_minutes: number }>('/settings/setup-access', {
      method: 'PATCH',
      body: { unlock_ttl_minutes: minutes }
    })
    if (status.value) {
      status.value = { ...status.value, unlock_ttl_minutes: data.unlock_ttl_minutes }
    }
    return data.unlock_ttl_minutes
  }

  async function lock() {
    locking.value = true
    try {
      try {
        await api<{ locked: boolean }>('/settings/setup-access/lock', { method: 'POST' })
      } catch {
        // Local lock still applies even if the no-op endpoint fails.
      }
      unlockToken.value = null
      expiresAt.value = null
      writeStoredSetupUnlock(null)
    } finally {
      locking.value = false
    }
  }

  if (import.meta.client) {
    hydrateFromStorage()
    startTicker()
  }

  return {
    status,
    pinConfigured,
    isUnlocked,
    minutesRemaining,
    locking,
    unlockToken,
    expiresAt,
    fetchStatus,
    unlock,
    createPin,
    changePin,
    setTtl,
    lock,
    needsUnlock,
    setupUnlockHeaders,
    hydrateFromStorage
  }
}
