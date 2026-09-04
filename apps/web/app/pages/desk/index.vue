<script setup lang="ts">
definePageMeta({ layout: 'desk' })

const { view } = useDeskUrl()
</script>

<template>
  <div class="h-full min-h-0 w-full">
    <DeskDashboardPanel v-if="view === 'dashboard'" />
    <DeskPatientsPanel v-else-if="view === 'patients'" />
    <DeskCalendarPanel v-else-if="view === 'calendar'" />
    <DeskTasksPanel v-else-if="view === 'tasks'" />
  </div>
</template>
