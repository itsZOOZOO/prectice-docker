<script setup lang="ts">
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ created: [id: number] }>()
</script>

<template>
  <UModal v-model:open="open" title="Add patient">
    <template #body>
      <DeskPatientForm
        v-if="open"
        mode="create"
        @success="(id) => { open = false; emit('created', id) }"
        @cancel="open = false"
      />
    </template>
  </UModal>
</template>
