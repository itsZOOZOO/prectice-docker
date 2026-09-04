<script setup lang="ts">
import type { DentalLab } from '~/utils/labTypes'
import { LAB_CASE_TYPE_CHIPS } from '~/utils/labTypes'

const props = defineProps<{
  open: boolean
  clientId?: number | null
  clientName?: string | null
}>()

const emit = defineEmits<{
  'update:open': [boolean]
  created: [payload: { case_id: number, case_ref: string, client_id: number }]
}>()

const { api } = useApi()
const toast = useToast()

const labs = ref<DentalLab[]>([])
const clients = ref<{ client_id: number, name: string }[]>([])
const saving = ref(false)
const form = reactive({
  client_id: null as number | null,
  lab_id: null as number | null,
  case_type: 'Crown & Bridge',
  tooth_numbers: '',
  description: ''
})

const isOpen = computed({
  get: () => props.open,
  set: (v: boolean) => emit('update:open', v)
})

const lockedClient = computed(() => Boolean(props.clientId))

async function prepare() {
  labs.value = (await api<{ items: DentalLab[] }>('/labs')).items
  if (!lockedClient.value) {
    const data = await api<{ items: { client_id: number, name: string }[] }>('/clients', {
      query: { limit: 100 }
    })
    clients.value = data.items
  }
  form.client_id = props.clientId ?? null
  form.lab_id = labs.value[0]?.lab_id ?? null
  form.case_type = 'Crown & Bridge'
  form.tooth_numbers = ''
  form.description = ''
}

watch(
  () => props.open,
  (open) => {
    if (open) void prepare()
  }
)

async function submit() {
  if (!form.client_id || !form.lab_id || !form.case_type.trim()) {
    toast.add({ title: 'Patient, lab, and type are required', color: 'warning' })
    return
  }
  saving.value = true
  try {
    const data = await api<{ case_id: number, case_ref: string }>('/lab-cases', {
      method: 'POST',
      body: {
        client_id: form.client_id,
        lab_id: form.lab_id,
        case_type: form.case_type.trim(),
        tooth_numbers: form.tooth_numbers || null,
        description: form.description || null
      }
    })
    emit('created', { ...data, client_id: form.client_id })
    isOpen.value = false
    toast.add({ title: `Created ${data.case_ref}`, color: 'success' })
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <UModal v-model:open="isOpen" title="New lab case">
    <template #body>
      <form class="space-y-3" @submit.prevent="submit">
        <UFormField v-if="lockedClient" label="Patient">
          <p class="text-sm font-medium text-[#1C2B35]">{{ clientName || `Patient #${clientId}` }}</p>
        </UFormField>
        <UFormField v-else label="Patient" required>
          <USelect
            v-model="form.client_id"
            :items="clients.map(c => ({ label: c.name, value: c.client_id }))"
            value-key="value"
            label-key="label"
            class="w-full"
            placeholder="Select patient"
          />
        </UFormField>
        <UFormField label="Lab" required>
          <USelect
            v-model="form.lab_id"
            :items="labs.map(l => ({ label: l.name, value: l.lab_id }))"
            value-key="value"
            label-key="label"
            class="w-full"
            placeholder="Select lab"
          />
          <p v-if="!labs.length" class="mt-1 text-xs text-amber-600">Add a lab vendor in Settings first.</p>
        </UFormField>
        <UFormField label="Case type" required>
          <div class="mb-2 flex flex-wrap gap-1">
            <button
              v-for="chip in LAB_CASE_TYPE_CHIPS"
              :key="chip"
              type="button"
              class="rounded-full border px-2.5 py-0.5 text-[11px]"
              :class="form.case_type === chip ? 'border-[#0097A7] bg-[#e0f7fa] text-[#0097A7]' : 'border-slate-200 text-slate-600'"
              @click="form.case_type = chip"
            >
              {{ chip }}
            </button>
          </div>
          <UInput v-model="form.case_type" class="w-full" />
        </UFormField>
        <UFormField label="Teeth">
          <UInput v-model="form.tooth_numbers" class="w-full" placeholder="e.g. 11,12,21" />
        </UFormField>
        <UFormField label="Notes">
          <UTextarea v-model="form.description" class="w-full" :rows="2" />
        </UFormField>
        <div class="flex justify-end gap-2">
          <UButton color="neutral" variant="ghost" @click="isOpen = false">Cancel</UButton>
          <UButton type="submit" class="bg-[#0097A7]" :loading="saving" :disabled="!labs.length">Create</UButton>
        </div>
      </form>
    </template>
  </UModal>
</template>
