import { hapticLight } from '~/utils/haptic'

const INTERACTIVE
  = 'button, a[href], [role="button"], input[type="checkbox"], input[type="radio"], input[type="submit"], select, summary, label[for]'

/**
 * Light haptic on touch taps for interactive controls (mobile / pen).
 * Desktop mouse clicks stay silent.
 */
export default defineNuxtPlugin(() => {
  if (!import.meta.client) return

  function onPointerUp(event: PointerEvent) {
    if (event.pointerType !== 'touch' && event.pointerType !== 'pen') return
    if (event.button != null && event.button !== 0) return
    const target = event.target
    if (!(target instanceof Element)) return
    if (!target.closest(INTERACTIVE)) return
    hapticLight()
  }

  document.addEventListener('pointerup', onPointerUp, { passive: true, capture: true })
})
