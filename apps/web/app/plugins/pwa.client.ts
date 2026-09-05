import {
  initPwaInstallListeners,
  initStandaloneViewportZoomLock,
  shouldRegisterPwaServiceWorker,
  syncStandaloneViewportZoomLock
} from '~/utils/pwaInstall'

export default defineNuxtPlugin(() => {
  if (!import.meta.client) return

  initPwaInstallListeners()
  const stopViewportLock = initStandaloneViewportZoomLock()

  if (shouldRegisterPwaServiceWorker()) {
    void navigator.serviceWorker.register('/sw.js', {
      scope: '/',
      updateViaCache: 'none'
    })
  }

  const router = useRouter()
  router.afterEach(() => {
    syncStandaloneViewportZoomLock()
    window.setTimeout(syncStandaloneViewportZoomLock, 0)
    window.setTimeout(syncStandaloneViewportZoomLock, 50)
    window.setTimeout(syncStandaloneViewportZoomLock, 250)
  })

  if (import.meta.hot) {
    import.meta.hot.dispose(() => {
      stopViewportLock()
    })
  }
})
