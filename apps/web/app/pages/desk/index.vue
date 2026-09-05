<script setup lang="ts">
definePageMeta({ layout: 'desk' })

const { view, setView } = useDeskUrl()
const canUseWaInbox = inject<Ref<boolean>>('deskCanUseWaInbox', ref(false))
const waInboxGateReady = inject<Ref<boolean>>('deskWaInboxGateReady', ref(true))

watch(
  [view, canUseWaInbox, waInboxGateReady],
  () => {
    if (view.value !== 'wa-inbox') return
    if (!waInboxGateReady.value) return
    if (!canUseWaInbox.value) void setView('dashboard')
  },
  { immediate: true }
)
</script>

<template>
  <div class="h-full min-h-0 w-full overflow-hidden">
    <DeskDashboardPanel v-if="view === 'dashboard'" />
    <DeskPatientsPanel v-else-if="view === 'patients'" />
    <DeskCalendarPanel v-else-if="view === 'calendar'" />
    <DeskTasksPanel v-else-if="view === 'tasks'" />
    <DeskLabPanel v-else-if="view === 'lab'" />
    <div
      v-else-if="view === 'wa-inbox' && !waInboxGateReady"
      class="flex h-full items-center justify-center text-sm text-slate-400"
    >
      Loading…
    </div>
    <DeskWaInboxPanel v-else-if="view === 'wa-inbox' && canUseWaInbox" />
    <DeskStatisticsPanel v-else-if="view === 'statistics'" />
    <DeskSettingsPanel v-else-if="view === 'settings'" />
  </div>
</template>
