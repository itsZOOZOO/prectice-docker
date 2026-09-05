export type PlanLang = 'en' | 'gu'

export function pickLocalized(lang: PlanLang, en?: string | null, gu?: string | null): string {
  const e = (en || '').trim()
  const g = (gu || '').trim()
  if (lang === 'gu' && g) return g
  return e || g
}

export function formatVisits(count: number, lang: PlanLang): string {
  if (count <= 1) return lang === 'gu' ? '1 મુલાકાત' : '1 visit'
  return lang === 'gu' ? `${count} મુલાકાત` : `${count} visits`
}

export function formatRecovery(days: number | null | undefined, lang: PlanLang): string {
  if (days == null || days <= 0) return lang === 'gu' ? 'ત્યાં જ' : 'Same day'
  if (days === 1) return lang === 'gu' ? '1 દિવસ' : '1 day'
  return lang === 'gu' ? `${days} દિવસ` : `${days} days`
}

export function formatInr(n: number): string {
  return `₹${Math.round(n).toLocaleString('en-IN')}`
}
