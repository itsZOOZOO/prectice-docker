<script setup lang="ts">
type MedicineTemplate = {
  medicine_id: number
  medicine_name: string
  strength: string | null
  default_quantity: number | null
  default_dosage: string | null
  default_days: number | null
  default_instructions: string | null
}

const { api } = useApi()
const toast = useToast()

const templates = ref<MedicineTemplate[]>([])
const loading = ref(false)
const saving = ref(false)
const search = ref('')
const formOpen = ref(false)
const editingId = ref<number | null>(null)
const formError = ref('')
const form = reactive({
  medicine_name: '',
  strength: '',
  default_quantity: '10',
  default_dosage: '',
  default_days: '5',
  default_instructions: ''
})

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return templates.value
  return templates.value.filter(t =>
    t.medicine_name.toLowerCase().includes(q)
    || (t.strength ?? '').toLowerCase().includes(q)
    || (t.default_dosage ?? '').toLowerCase().includes(q)
    || (t.default_instructions ?? '').toLowerCase().includes(q)
  )
})

async function loadTemplates() {
  loading.value = true
  try {
    const data = await api<{ templates: MedicineTemplate[] }>('/settings/medicine-templates')
    templates.value = data.templates ?? []
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to load medicines', color: 'error' })
  } finally {
    loading.value = false
  }
}

function resetForm() {
  editingId.value = null
  form.medicine_name = ''
  form.strength = ''
  form.default_quantity = '10'
  form.default_dosage = ''
  form.default_days = '5'
  form.default_instructions = ''
  formError.value = ''
}

function openNew() {
  resetForm()
  formOpen.value = true
}

function openEdit(row: MedicineTemplate) {
  editingId.value = row.medicine_id
  form.medicine_name = row.medicine_name
  form.strength = row.strength ?? ''
  form.default_quantity = row.default_quantity != null ? String(row.default_quantity) : '10'
  form.default_dosage = row.default_dosage ?? ''
  form.default_days = row.default_days != null ? String(row.default_days) : '5'
  form.default_instructions = row.default_instructions ?? ''
  formError.value = ''
  formOpen.value = true
}

async function saveTemplate() {
  if (!form.medicine_name.trim()) {
    formError.value = 'Medicine name is required.'
    return
  }
  saving.value = true
  formError.value = ''
  const payload = {
    medicine_name: form.medicine_name.trim(),
    strength: form.strength.trim() || null,
    default_quantity: form.default_quantity !== '' ? Number(form.default_quantity) : null,
    default_dosage: form.default_dosage.trim() || null,
    default_days: form.default_days !== '' ? Number(form.default_days) : null,
    default_instructions: form.default_instructions.trim() || null
  }
  try {
    if (editingId.value != null) {
      await api<MedicineTemplate>(`/settings/medicine-templates/${editingId.value}`, {
        method: 'PATCH',
        body: payload
      })
      toast.add({ title: 'Medicine updated', color: 'success' })
    } else {
      await api<MedicineTemplate>('/settings/medicine-templates', {
        method: 'POST',
        body: payload
      })
      toast.add({ title: 'Medicine added', color: 'success' })
    }
    formOpen.value = false
    resetForm()
    await loadTemplates()
  } catch (e: unknown) {
    formError.value = e instanceof Error ? e.message : 'Failed to save'
  } finally {
    saving.value = false
  }
}

async function deleteTemplate(row: MedicineTemplate) {
  if (!window.confirm(`Remove “${row.medicine_name}” from the catalog?`)) return
  try {
    await api(`/settings/medicine-templates/${row.medicine_id}`, { method: 'DELETE' })
    toast.add({ title: 'Medicine removed', color: 'success' })
    await loadTemplates()
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to delete', color: 'error' })
  }
}

function summaryLine(row: MedicineTemplate) {
  const parts = [
    row.strength,
    row.default_dosage,
    row.default_quantity != null ? `qty ${row.default_quantity}` : null,
    row.default_days != null ? `${row.default_days} days` : null
  ].filter(Boolean)
  return parts.join(' · ') || 'No defaults set'
}

onMounted(() => {
  void loadTemplates()
})
</script>

<template>
  <div class="p-4 md:p-5">
    <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
      <UInput v-model="search" class="w-full max-w-sm" placeholder="Search medicines…" />
      <UButton size="sm" class="bg-[#0097A7]" @click="openNew">
        Add medicine
      </UButton>
    </div>

    <div class="rounded-xl border border-slate-200 bg-white shadow-sm">
      <p v-if="loading" class="px-4 py-8 text-center text-sm text-slate-400">
        Loading medicines…
      </p>
      <ul v-else class="divide-y divide-slate-100">
        <li v-if="!filtered.length" class="py-8 text-center text-sm text-slate-500">
          No medicine templates yet.
        </li>
        <li
          v-for="row in filtered"
          :key="row.medicine_id"
          class="flex flex-wrap items-start justify-between gap-3 px-4 py-3 hover:bg-slate-50"
        >
          <div class="min-w-0">
            <p class="text-sm font-medium text-slate-800">{{ row.medicine_name }}</p>
            <p class="text-xs text-slate-500">{{ summaryLine(row) }}</p>
            <p v-if="row.default_instructions" class="mt-1 text-xs text-slate-400">
              {{ row.default_instructions }}
            </p>
          </div>
          <div class="flex shrink-0 gap-2">
            <UButton size="xs" color="neutral" variant="outline" @click="openEdit(row)">
              Edit
            </UButton>
            <UButton size="xs" color="error" variant="ghost" @click="deleteTemplate(row)">
              Delete
            </UButton>
          </div>
        </li>
      </ul>
    </div>

    <UModal
      v-model:open="formOpen"
      :title="editingId != null ? 'Edit medicine' : 'Add medicine'"
    >
      <template #body>
        <form class="space-y-3" @submit.prevent="saveTemplate">
          <UFormField label="Medicine name *" required>
            <UInput v-model="form.medicine_name" class="w-full" required />
          </UFormField>
          <div class="grid gap-3 sm:grid-cols-2">
            <UFormField label="Strength">
              <UInput v-model="form.strength" class="w-full" placeholder="e.g. 500mg" />
            </UFormField>
            <UFormField label="Default quantity">
              <UInput v-model="form.default_quantity" type="number" :min="0" class="w-full" />
            </UFormField>
            <UFormField label="Default dosage">
              <UInput v-model="form.default_dosage" class="w-full" placeholder="e.g. 1-0-1" />
            </UFormField>
            <UFormField label="Default days">
              <UInput v-model="form.default_days" type="number" :min="0" class="w-full" />
            </UFormField>
          </div>
          <UFormField label="Default instructions">
            <UTextarea v-model="form.default_instructions" class="w-full" :rows="2" />
          </UFormField>
          <p v-if="formError" class="text-sm text-red-600">{{ formError }}</p>
          <div class="flex justify-end gap-2">
            <UButton color="neutral" variant="ghost" type="button" @click="formOpen = false">
              Cancel
            </UButton>
            <UButton type="submit" class="bg-[#0097A7]" :loading="saving">
              Save
            </UButton>
          </div>
        </form>
      </template>
    </UModal>
  </div>
</template>
