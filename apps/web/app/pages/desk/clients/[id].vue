<script setup lang="ts">
const route = useRoute()
await navigateTo({ path: '/desk', query: { view: 'patients', patient: String(route.params.id) } })
</script>

<template>
  <div />
</template>
