export default defineNuxtRouteMiddleware((to) => {
  const auth = useAuth()
  auth.hydrate()
  if (!auth.isLoggedIn.value) {
    return navigateTo('/login')
  }
  if (!auth.isSuperadmin.value) {
    return navigateTo('/desk?view=dashboard')
  }
  // Desktop admin only — send phones to mobile home
  if (import.meta.client && window.matchMedia('(max-width: 900px)').matches) {
    return navigateTo('/dashboard')
  }
})
