export type AuthUser = {
  user_id: number
  clinic_id: number
  username: string
  full_name: string
  role: string
  email?: string | null
}

const TOKEN_KEY = 'prectice_token'
const USER_KEY = 'prectice_user'
const CLINIC_KEY = 'prectice_clinic'

export function useAuth() {
  const token = useState<string | null>('auth_token', () => null)
  const user = useState<AuthUser | null>('auth_user', () => null)
  const clinicName = useState<string | null>('auth_clinic', () => null)

  function hydrate() {
    if (!import.meta.client) return
    if (!token.value) token.value = localStorage.getItem(TOKEN_KEY)
    if (!user.value) {
      const raw = localStorage.getItem(USER_KEY)
      user.value = raw ? JSON.parse(raw) as AuthUser : null
    }
    if (!clinicName.value) clinicName.value = localStorage.getItem(CLINIC_KEY)
  }

  function setSession(payload: { access_token: string, user: AuthUser, clinic_name: string }) {
    token.value = payload.access_token
    user.value = payload.user
    clinicName.value = payload.clinic_name
    if (import.meta.client) {
      localStorage.setItem(TOKEN_KEY, payload.access_token)
      localStorage.setItem(USER_KEY, JSON.stringify(payload.user))
      localStorage.setItem(CLINIC_KEY, payload.clinic_name)
    }
  }

  function clearSession() {
    token.value = null
    user.value = null
    clinicName.value = null
    if (import.meta.client) {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
      localStorage.removeItem(CLINIC_KEY)
    }
  }

  async function logout() {
    clearSession()
    await navigateTo('/login')
  }

  const isLoggedIn = computed(() => Boolean(token.value))

  return { token, user, clinicName, isLoggedIn, hydrate, setSession, clearSession, logout }
}
