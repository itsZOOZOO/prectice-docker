<script setup lang="ts">
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ created: [id: number] }>()
const { api } = useApi()
const toast = useToast()

const form = reactive({ name: '', number: '', place: '', status: 'Inquiry' })
const saving = ref(false)

async function submit() {
  if (!form.name.trim()) return
  saving.value = true
  try {
    const created = await api<{ client_id: number }>('/clients', {
      method: 'POST',
      body: {
        name: form.name,
        number: form.number || null,
        place: form.place || null,
        status: form.status
      }
    })
    toast.add({ title: 'Patient added', color: 'success' })
    open.value = false
    form.name = ''
    form.number = ''
    form.place = ''
    emit('created', created.client_id)
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <UModal v-model:open="open" title="Add patient">
    <template #body>
      <form class="space-y-3" @submit.prevent="submit">
        <UFormField label="Name" required>
          <UInput v-model="form.name" class="w-full" autofocus />
        </UFormField>
        <UFormField label="Phone">
          <UInput v-model="form.number" class="w-full" />
        </UFormField>
        <UFormField label="Place">
          <UInput v-model="form.place" class="w-full" />
        </UFormField>
        <UFormField label="Status">
          <USelect v-model="form.status" :items="['Inquiry', 'Under Rx', 'Completed', 'Follow-up']" class="w-full" />
        </UFormField>
        <div class="flex justify-end gap-2 pt-2">
          <UButton color="neutral" variant="ghost" @click="open = false">Cancel</UButton>
          <UButton type="submit" :loading="saving" class="bg-[#0097A7]">Add</UButton>
        </div>
      </form>
    </template>
  </UModal>
</template>
