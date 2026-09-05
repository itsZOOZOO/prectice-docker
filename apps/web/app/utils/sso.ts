const REMEMBER_PREF_KEY = 'prectice_sso_remember'

export function getSsoCallbackUrl(): string {
  const config = useRuntimeConfig()
  const explicit = String(config.public.ssoCallbackUrl || '').trim()
  if (explicit) {
    return explicit.replace(/\/$/, '')
  }
  if (import.meta.client) {
    return `${window.location.origin}/sso/callback`
  }
  return 'https://dental.navapp.in/sso/callback'
}

export function buildSsoLoginUrl(redirectAfter = '/'): string {
  const config = useRuntimeConfig()
  const base = String(config.public.ssoAuthBaseUrl || 'https://auth.pratikp.com').replace(/\/$/, '')
  const slug = String(config.public.ssoAppSlug || 'navapp-dental')
  const callback = getSsoCallbackUrl()
  const params = new URLSearchParams({
    app: slug,
    return: callback,
    redirect: redirectAfter
  })
  return `${base}/login.php?${params.toString()}`
}

export function storeSsoRememberPref(remember: boolean) {
  if (!import.meta.client) return
  sessionStorage.setItem(REMEMBER_PREF_KEY, remember ? '1' : '0')
}

export function takeSsoRememberPref(): boolean {
  if (!import.meta.client) return false
  const raw = sessionStorage.getItem(REMEMBER_PREF_KEY)
  sessionStorage.removeItem(REMEMBER_PREF_KEY)
  return raw === '1'
}

export function safePostLoginPath(path: string | null | undefined, fallback = '/'): string {
  const candidate = (path ?? '').trim()
  if (candidate.startsWith('/') && !candidate.startsWith('//')) {
    return candidate
  }
  return fallback
}
