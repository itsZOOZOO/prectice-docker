import { applyAppHeight } from '~/utils/viewportHeight'

/**
 * Keep --app-height in sync. Prefer the shortest viewport metric so Android
 * cold-start scrollports actually overflow (and can scroll).
 */
export default defineNuxtPlugin(() => {
  if (!import.meta.client) return

  function sync() {
    applyAppHeight()
  }

  sync()
  requestAnimationFrame(() => {
    sync()
    requestAnimationFrame(sync)
  })
  window.setTimeout(sync, 0)
  window.setTimeout(sync, 50)
  window.setTimeout(sync, 200)
  window.setTimeout(sync, 500)
  window.setTimeout(sync, 1200)

  window.addEventListener('resize', sync)
  window.addEventListener('orientationchange', sync)
  window.addEventListener('pageshow', sync)
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') sync()
  })

  const vv = window.visualViewport
  vv?.addEventListener('resize', sync)
  vv?.addEventListener('scroll', sync)

  const router = useRouter()
  router.afterEach(() => {
    sync()
    requestAnimationFrame(sync)
  })
})
