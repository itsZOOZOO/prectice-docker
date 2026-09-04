export default defineNuxtRouteMiddleware((to) => {
  const auth = useAuth()
  auth.hydrate()

  const publicPaths = new Set(['/login'])
  if (publicPaths.has(to.path)) {
    if (auth.isLoggedIn.value) {
      if (import.meta.client) return navigateTo(homePathForViewport())
      return navigateTo('/desk?view=dashboard')
    }
    return
  }

  if (!auth.isLoggedIn.value) {
    return navigateTo('/login')
  }
})
