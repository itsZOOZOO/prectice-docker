<script setup lang="ts">
import type { PatientFormInitial } from '~/utils/patientForm'

const open = defineModel<boolean>('open', { default: false })
const props = defineProps<{
  clientId: number
  initial: PatientFormInitial | null
}>()
const emit = defineEmits<{
  saved: []
  deleted: []
}>()
</script>

<template>
  <UModal v-model:open="open" title="Edit client">
    <template #body>
      <DeskPatientForm
        v-if="open && clientId"
        mode="edit"
        :client-id="clientId"
        :initial="initial"
        @success="() => { open = false; emit('saved') }"
        @deleted="() => { open = false; emit('deleted') }"
        @cancel="open = false"
      />
    </template>
  </UModal>
</template>
