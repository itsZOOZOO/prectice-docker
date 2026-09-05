/** Light device vibration for touch UI (Android Chrome / many WebViews). iOS Safari usually ignores this. */

export type HapticKind = 'light' | 'medium' | 'success' | 'warning'

const PATTERNS: Record<HapticKind, number | number[]> = {
  light: 12,
  medium: 20,
  success: [10, 40, 14],
  warning: [16, 30, 16]
}

export function canHaptic(): boolean {
  return import.meta.client && typeof navigator !== 'undefined' && typeof navigator.vibrate === 'function'
}

export function haptic(kind: HapticKind = 'light'): void {
  if (!canHaptic()) return
  try {
    navigator.vibrate(PATTERNS[kind])
  } catch {
    // ignore — unsupported or blocked
  }
}

export function hapticLight(): void {
  haptic('light')
}
