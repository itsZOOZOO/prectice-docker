type ApiEnvelope<T> = {
  ok: boolean
  data?: T
  error?: string | null
}

export function useApi() {
  const config = useRuntimeConfig()
  const auth = useAuth()

  async function api<T>(path: string, opts: {
    method?: string
    body?: unknown
    query?: Record<string, string | number | boolean | undefined | null>
  } = {}): Promise<T> {
    const headers: Record<string, string> = {}
    if (auth.token.value) {
      headers.Authorization = `Bearer ${auth.token.value}`
    }

    try {
      const res = await $fetch<ApiEnvelope<T>>(`${config.public.apiBase}${path}`, {
        method: (opts.method || 'GET') as 'GET',
        body: opts.body as Record<string, unknown> | undefined,
        query: opts.query as Record<string, string | number | boolean> | undefined,
        headers
      })
      if (!res.ok) {
        throw new Error(res.error || 'Request failed')
      }
      return res.data as T
    } catch (err: unknown) {
      const e = err as { data?: { detail?: string | { msg: string }[] }, statusCode?: number, message?: string }
      if (e.statusCode === 401) {
        auth.clearSession()
        if (import.meta.client) {
          await navigateTo('/login')
        }
      }
      const detail = e.data?.detail
      if (typeof detail === 'string') throw new Error(detail)
      if (Array.isArray(detail)) throw new Error(detail.map(d => d.msg).join(', '))
      throw new Error(e.message || 'Request failed')
    }
  }

  return { api }
}
