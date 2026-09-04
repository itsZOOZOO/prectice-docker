/** Desktop/mobile home routing — matches Next.js `lg` = 1024px. */
export const DESKTOP_HOME_MQ = '(min-width: 1024px)'

/** Loud mismatch pulse window (ms), then quiet rest style. */
export const VIEW_MISMATCH_ATTENTION_MS = 9000

export function isDesktopHomeViewport(): boolean {
  if (!import.meta.client) return true
  return window.matchMedia(DESKTOP_HOME_MQ).matches
}

export function homePathForViewport(): string {
  return isDesktopHomeViewport() ? '/desk?view=dashboard' : '/dashboard'
}

export function useDeviceHome() {
  const isDesktop = ref(true)

  function refresh() {
    isDesktop.value = isDesktopHomeViewport()
  }

  onMounted(() => {
    refresh()
    const mq = window.matchMedia(DESKTOP_HOME_MQ)
    const onChange = () => { isDesktop.value = mq.matches }
    mq.addEventListener('change', onChange)
    onUnmounted(() => mq.removeEventListener('change', onChange))
  })

  return {
    isDesktop,
    homePath: computed(() => (isDesktop.value ? '/desk?view=dashboard' : '/dashboard')),
    refresh
  }
}

/**
 * Loud attention for a few seconds when a mismatch view is shown, then rests.
 * Re-informs when mismatch turns on again or the tab becomes visible.
 */
export function useViewMismatchAttention(isMismatch: MaybeRefOrGetter<boolean>) {
  const attention = ref(false)
  let timer: ReturnType<typeof setTimeout> | null = null

  function clearTimer() {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
  }

  function inform() {
    attention.value = true
    clearTimer()
    timer = setTimeout(() => {
      attention.value = false
      timer = null
    }, VIEW_MISMATCH_ATTENTION_MS)
  }

  watch(
    () => toValue(isMismatch),
    (mismatch) => {
      if (!mismatch) {
        attention.value = false
        clearTimer()
        return
      }
      inform()
    },
    { immediate: true }
  )

  function onVisibility() {
    if (document.visibilityState === 'visible' && toValue(isMismatch)) inform()
  }

  onMounted(() => {
    document.addEventListener('visibilitychange', onVisibility)
  })

  onUnmounted(() => {
    document.removeEventListener('visibilitychange', onVisibility)
    clearTimer()
  })

  return attention
}

export function viewSwitchClass(isMismatch: boolean, attention: boolean) {
  if (!isMismatch) return 'border-slate-200 text-slate-600 hover:bg-slate-50'
  if (attention) return 'view-mismatch-beam border-[#0097A7]'
  return 'view-mismatch-rest font-semibold'
}
