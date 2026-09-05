/**
 * Android Chrome cold-start: layout viewport (100dvh / innerHeight) is often
 * taller than the visible area, so overflow scrollports think they have no
 * overflow until a remount. Always use the *smallest* positive viewport metric.
 */
export function measureAppHeightPx(): number {
  if (typeof window === 'undefined') return 0
  const candidates = [
    window.visualViewport?.height,
    window.innerHeight,
    document.documentElement?.clientHeight
  ].filter((n): n is number => typeof n === 'number' && Number.isFinite(n) && n > 0)
  if (!candidates.length) return 0
  return Math.round(Math.min(...candidates))
}

export function applyAppHeight(): number {
  const h = measureAppHeightPx()
  if (h > 0) {
    document.documentElement.style.setProperty('--app-height', `${h}px`)
  }
  return h
}
