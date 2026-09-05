<script setup lang="ts">
definePageMeta({ layout: 'mobile' })

const route = useRoute()
const patientId = computed(() => {
  const n = Number(route.params.id)
  return Number.isFinite(n) && n > 0 ? n : null
})
</script>

<template>
  <div class="flex h-full min-h-0 flex-col overflow-hidden">
    <DeskPatientsPanel
      v-if="patientId"
      class="min-h-0 flex-1"
      mobile-chart
      :fixed-patient-id="patientId"
    />
    <p v-else class="p-6 text-center text-sm text-slate-500">Patient not found.</p>
  </div>
</template>
