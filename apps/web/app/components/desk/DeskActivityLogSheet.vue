<script setup lang="ts">
const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  'update:open': [boolean]
  readStateChange: []
  openPatient: [clientId: number]
}>()

const isOpen = computed({
  get: () => props.open,
  set: (v: boolean) => emit('update:open', v)
})

function onPatient(clientId: number) {
  emit('openPatient', clientId)
  isOpen.value = false
}
</script>

<template>
  <UModal
    v-model:open="isOpen"
    title="Activity log"
    :ui="{ content: 'sm:max-w-md' }"
  >
    <template #body>
      <p class="mb-3 text-[11px] text-slate-400">Most recent first</p>
      <div class="flex max-h-[min(70vh,32rem)] min-h-[16rem] flex-col">
        <DeskActivityLogFeed
          :active="isOpen"
          mark-read-on-view
          @read-state-change="emit('readStateChange')"
          @open-patient="onPatient"
        />
      </div>
    </template>
  </UModal>
</template>
