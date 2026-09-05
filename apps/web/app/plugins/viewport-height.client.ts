/**
 * Keep --app-height in sync with the visible viewport.
 * Android Chrome often reports wrong % heights on first paint; scrolling
 * only starts working after a layout remount (e.g. desk ↔ mobile). Using
 * visualViewport.height fixes the cold-start scrollport.
 */
export default defineNuxtPlugin(() => {
  if (!import.meta.client) return

  function setAppHeight() {
    const vv = window.visualViewport
    const h = Math.round(vv?.height ?? window.innerHeight)
    if (h > 0) {
      document.documentElement.style.setProperty('--app-height', `${h}px`)
    }
  }

  setAppHeight()
  // Second pass after first layout / font / UI chrome settle
  requestAnimationFrame(() => {
    setAppHeight()
    requestAnimationFrame(setAppHeight)
  })
  window.setTimeout(setAppHeight, 50)
  window.setTimeout(setAppHeight, 250)
  window.setTimeout(setAppHeight, 1000)

  window.addEventListener('resize', setAppHeight)
  window.addEventListener('orientationchange', setAppHeight)
  window.addEventListener('pageshow', setAppHeight)
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') setAppHeight()
  })

  const vv = window.visualViewport
  vv?.addEventListener('resize', setAppHeight)
  vv?.addEventListener('scroll', setAppHeight)

  const router = useRouter()
  router.afterEach(() => {
    setAppHeight()
    requestAnimationFrame(setAppHeight)
  })
})
