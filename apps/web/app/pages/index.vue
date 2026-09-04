<script setup lang="ts">
const auth = useAuth()
auth.hydrate()

if (!auth.isLoggedIn.value) {
  await navigateTo('/login')
} else if (import.meta.client) {
  await navigateTo(homePathForViewport())
} else {
  await navigateTo('/desk?view=dashboard')
}
</script>

<template>
  <div />
</template>
