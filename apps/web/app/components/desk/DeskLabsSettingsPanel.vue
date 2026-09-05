<script setup lang="ts">
import type { DentalLab } from '~/utils/labTypes'

const { api } = useApi()
const toast = useToast()

const labs = ref<DentalLab[]>([])
const loading = ref(false)
const saving = ref(false)
const search = ref('')
const formOpen = ref(false)
const editingLabId = ref<number | null>(null)
const form = reactive({
  name: '',
  contact_person: '',
  phone: '',
  notes: ''
})

const filteredLabs = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return labs.value
  return labs.value.filter(lab =>
    lab.name.toLowerCase().includes(q)
    || (lab.phone ?? '').includes(q)
    || (lab.contact_person ?? '').toLowerCase().includes(q)
  )
})

async function loadLabs() {
  loading.value = true
  try {
    labs.value = (await api<{ items: DentalLab[] }>('/labs')).items
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to load labs', color: 'error' })
  } finally {
    loading.value = false
  }
}

function openNewLab() {
  editingLabId.value = null
  form.name = ''
  form.contact_person = ''
  form.phone = ''
  form.notes = ''
  formOpen.value = true
}

function openEditLab(lab: DentalLab) {
  editingLabId.value = lab.lab_id
  form.name = lab.name
  form.contact_person = lab.contact_person || ''
  form.phone = lab.phone || ''
  form.notes = lab.notes || ''
  formOpen.value = true
}

async function saveLab() {
  if (!form.name.trim()) {
    toast.add({ title: 'Lab name required', color: 'warning' })
    return
  }
  saving.value = true
  try {
    const body = {
      name: form.name.trim(),
      contact_person: form.contact_person || null,
      phone: form.phone || null,
      notes: form.notes || null
    }
    if (editingLabId.value) {
      await api(`/labs/${editingLabId.value}`, { method: 'PATCH', body })
      toast.add({ title: 'Lab updated', color: 'success' })
    } else {
      await api('/labs', { method: 'POST', body })
      toast.add({ title: 'Lab added', color: 'success' })
    }
    formOpen.value = false
    await loadLabs()
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
  } finally {
    saving.value = false
  }
}

async function archiveLab(lab: DentalLab) {
  if (!window.confirm(`Archive lab “${lab.name}”? This cannot be undone.`)) return
  try {
    await api(`/labs/${lab.lab_id}`, { method: 'DELETE' })
    toast.add({ title: 'Lab archived', color: 'success' })
    await loadLabs()
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
  }
}

onMounted(() => {
  void loadLabs()
})
</script>

<template>
  <div class="p-4 md:p-5">
    <div class="mb-4 flex flex-wrap items-center justify-end gap-3">
      <UButton size="sm" class="bg-[#0097A7]" @click="openNewLab">Add lab</UButton>
    </div>

    <div class="mb-3">
      <UInput v-model="search" class="w-full max-w-sm" placeholder="Search labs…" />
    </div>

    <div class="rounded-xl border border-slate-200 bg-white shadow-sm">
      <p v-if="loading" class="px-4 py-8 text-center text-sm text-slate-400">Loading labs…</p>
      <ul v-else class="divide-y divide-slate-100">
        <li v-if="!filteredLabs.length" class="py-8 text-center text-sm text-slate-500">
          No labs yet. Add one above.
        </li>
        <li
          v-for="lab in filteredLabs"
          :key="lab.lab_id"
          class="flex flex-wrap items-center justify-between gap-2 px-4 py-3"
        >
          <div class="min-w-0">
            <p class="text-sm font-medium text-[#1C2B35]">{{ lab.name }}</p>
            <p class="text-xs text-slate-500">
              {{ [lab.contact_person, lab.phone].filter(Boolean).join(' · ') || 'No contact' }}
            </p>
            <p v-if="lab.notes" class="mt-1 text-xs text-slate-400">{{ lab.notes }}</p>
          </div>
          <div class="flex gap-2">
            <UButton size="xs" color="neutral" variant="outline" @click="openEditLab(lab)">Edit</UButton>
            <UButton size="xs" color="error" variant="ghost" @click="archiveLab(lab)">Archive</UButton>
          </div>
        </li>
      </ul>
    </div>

    <UModal v-model:open="formOpen" :title="editingLabId ? 'Edit lab' : 'Add lab'">
      <template #body>
        <form class="space-y-3" @submit.prevent="saveLab">
          <UFormField label="Name" required>
            <UInput v-model="form.name" class="w-full" />
          </UFormField>
          <UFormField label="Contact person">
            <UInput v-model="form.contact_person" class="w-full" />
          </UFormField>
          <UFormField label="Phone">
            <UInput v-model="form.phone" class="w-full" />
          </UFormField>
          <UFormField label="Notes">
            <UTextarea v-model="form.notes" class="w-full" :rows="2" />
          </UFormField>
          <div class="flex justify-end gap-2">
            <UButton color="neutral" variant="ghost" type="button" @click="formOpen = false">Cancel</UButton>
            <UButton type="submit" class="bg-[#0097A7]" :loading="saving">Save</UButton>
          </div>
        </form>
      </template>
    </UModal>
  </div>
</template>
