export type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

const DISMISS_KEY = 'navdental-pwa-install-dismissed-at'
const DISMISS_MS = 7 * 24 * 60 * 60 * 1000

let deferredPrompt: BeforeInstallPromptEvent | null = null
let listenersInitialized = false
const listeners = new Set<() => void>()

function notify() {
  for (const listener of listeners) {
    listener()
  }
}

export function subscribePwaInstall(listener: () => void): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export function getPwaDeferredPrompt(): BeforeInstallPromptEvent | null {
  return deferredPrompt
}

export function initPwaInstallListeners(): void {
  if (typeof window === 'undefined' || listenersInitialized) return
  listenersInitialized = true

  window.addEventListener('beforeinstallprompt', (event) => {
    event.preventDefault()
    deferredPrompt = event as BeforeInstallPromptEvent
    notify()
  })

  window.addEventListener('appinstalled', () => {
    deferredPrompt = null
    notify()
  })
}

export function isPwaStandalone(): boolean {
  if (typeof window === 'undefined') return false
  if (window.matchMedia('(display-mode: standalone)').matches) return true
  if ((navigator as Navigator & { standalone?: boolean }).standalone) return true
  return false
}

const VIEWPORT_STANDALONE
  = 'width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover'
const STANDALONE_NO_ZOOM_CLASS = 'pwa-standalone-no-zoom'

let viewportLockApplying = false
let viewportLockInitialized = false

function getViewportMeta(): HTMLMetaElement | null {
  const meta = document.querySelector('meta[name="viewport"]')
  return meta instanceof HTMLMetaElement ? meta : null
}

function ensureViewportMeta(): HTMLMetaElement {
  const existing = getViewportMeta()
  if (existing) return existing
  const meta = document.createElement('meta')
  meta.name = 'viewport'
  document.head.appendChild(meta)
  return meta
}

function onMultiTouchMove(event: TouchEvent): void {
  if (event.touches.length > 1) event.preventDefault()
}

function onGesture(event: Event): void {
  event.preventDefault()
}

function setStandaloneGestureGuards(enabled: boolean): void {
  const opts: AddEventListenerOptions = { passive: false, capture: true }
  if (enabled) {
    document.addEventListener('touchmove', onMultiTouchMove, opts)
    document.addEventListener('gesturestart', onGesture, opts)
    document.addEventListener('gesturechange', onGesture, opts)
    document.addEventListener('gestureend', onGesture, opts)
  } else {
    document.removeEventListener('touchmove', onMultiTouchMove, opts)
    document.removeEventListener('gesturestart', onGesture, opts)
    document.removeEventListener('gesturechange', onGesture, opts)
    document.removeEventListener('gestureend', onGesture, opts)
  }
}

export function syncStandaloneViewportZoomLock(): void {
  if (typeof document === 'undefined') return

  const standalone = isPwaStandalone()
  document.documentElement.classList.toggle(STANDALONE_NO_ZOOM_CLASS, standalone)

  if (!standalone) return

  const meta = ensureViewportMeta()
  if (meta.content === VIEWPORT_STANDALONE) return

  viewportLockApplying = true
  meta.content = VIEWPORT_STANDALONE
  queueMicrotask(() => {
    viewportLockApplying = false
  })
}

export function initStandaloneViewportZoomLock(): () => void {
  if (typeof window === 'undefined') return () => {}
  if (viewportLockInitialized) {
    syncStandaloneViewportZoomLock()
    return () => {}
  }
  viewportLockInitialized = true

  let guardsOn = false
  const apply = () => {
    const standalone = isPwaStandalone()
    syncStandaloneViewportZoomLock()
    if (standalone !== guardsOn) {
      setStandaloneGestureGuards(standalone)
      guardsOn = standalone
    }
  }

  apply()

  const mq = window.matchMedia('(display-mode: standalone)')
  const onDisplayModeChange = () => apply()
  mq.addEventListener('change', onDisplayModeChange)

  const observer = new MutationObserver(() => {
    if (viewportLockApplying || !isPwaStandalone()) return
    const meta = getViewportMeta()
    if (!meta || meta.content === VIEWPORT_STANDALONE) return
    apply()
  })
  observer.observe(document.documentElement, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ['content', 'name']
  })

  const onNavigate = () => apply()
  window.addEventListener('pageshow', onNavigate)
  window.addEventListener('popstate', onNavigate)
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') apply()
  })

  return () => {
    viewportLockInitialized = false
    mq.removeEventListener('change', onDisplayModeChange)
    observer.disconnect()
    window.removeEventListener('pageshow', onNavigate)
    window.removeEventListener('popstate', onNavigate)
    if (guardsOn) setStandaloneGestureGuards(false)
    document.documentElement.classList.remove(STANDALONE_NO_ZOOM_CLASS)
  }
}

export function isIosSafari(): boolean {
  if (typeof navigator === 'undefined') return false
  const ua = navigator.userAgent
  const isIos = /iPad|iPhone|iPod/.test(ua)
  if (!isIos) return false
  return !/CriOS|FxiOS|EdgiOS/.test(ua)
}

export function isPwaDismissedRecently(): boolean {
  try {
    const raw = localStorage.getItem(DISMISS_KEY)
    if (!raw) return false
    const dismissedAt = Number(raw)
    if (!Number.isFinite(dismissedAt)) return false
    return Date.now() - dismissedAt < DISMISS_MS
  } catch {
    return false
  }
}

export function dismissPwaInstallBanner(): void {
  try {
    localStorage.setItem(DISMISS_KEY, String(Date.now()))
  } catch {
    // ignore storage errors
  }
}

export function canPromptPwaInstall(): boolean {
  if (isPwaStandalone()) return false
  return isIosSafari() || deferredPrompt != null
}

export type PwaInstallResult = 'accepted' | 'dismissed' | 'unavailable' | 'ios'

export async function triggerPwaInstall(): Promise<PwaInstallResult> {
  if (isIosSafari()) return 'ios'

  const prompt = deferredPrompt
  if (!prompt) return 'unavailable'

  await prompt.prompt()
  const { outcome } = await prompt.userChoice
  if (outcome === 'accepted') {
    deferredPrompt = null
    notify()
  }
  return outcome
}

export function shouldRegisterPwaServiceWorker(): boolean {
  if (typeof window === 'undefined') return false
  if (!('serviceWorker' in navigator)) return false
  if (import.meta.dev) {
    return import.meta.env.NUXT_PUBLIC_PWA_DEV === 'true'
  }
  return true
}
