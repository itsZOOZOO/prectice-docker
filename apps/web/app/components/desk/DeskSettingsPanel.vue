<script setup lang="ts">
import type { DentalLab } from '~/utils/labTypes'

type WaSettings = {
  enabled: boolean
  wa_enabled: boolean
  has_api_key: boolean
  api_key_preview: string | null
  wa_api_url: string
}

const { api } = useApi()
const toast = useToast()

const loading = ref(true)
const saving = ref(false)
const error = ref('')
const form = reactive({
  wa_enabled: false,
  wa_api_url: 'https://wa.aarogyams.com/api.php',
  wa_api_key: '',
  has_api_key: false,
  api_key_preview: null as string | null,
  replace_key: false
})

const labs = ref<DentalLab[]>([])
const labsLoading = ref(false)
const labSaving = ref(false)
const labFormOpen = ref(false)
const editingLabId = ref<number | null>(null)
const labForm = reactive({
  name: '',
  contact_person: '',
  phone: '',
  notes: ''
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await api<WaSettings>('/settings/whatsapp')
    form.wa_enabled = data.wa_enabled
    form.wa_api_url = data.wa_api_url || 'https://wa.aarogyams.com/api.php'
    form.has_api_key = data.has_api_key
    form.api_key_preview = data.api_key_preview
    form.wa_api_key = ''
    form.replace_key = !data.has_api_key
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to load settings'
  } finally {
    loading.value = false
  }
}

async function loadLabs() {
  labsLoading.value = true
  try {
    labs.value = (await api<{ items: DentalLab[] }>('/labs')).items
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to load labs', color: 'error' })
  } finally {
    labsLoading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    const body: Record<string, unknown> = {
      wa_enabled: form.wa_enabled,
      wa_api_url: form.wa_api_url.trim() || null
    }
    if (form.replace_key) {
      if (form.wa_api_key.trim()) {
        body.wa_api_key = form.wa_api_key.trim()
      } else if (form.has_api_key) {
        body.clear_api_key = true
      }
    }
    const data = await api<WaSettings>('/settings/whatsapp', { method: 'PATCH', body })
    form.wa_enabled = data.wa_enabled
    form.wa_api_url = data.wa_api_url || form.wa_api_url
    form.has_api_key = data.has_api_key
    form.api_key_preview = data.api_key_preview
    form.wa_api_key = ''
    form.replace_key = !data.has_api_key
    toast.add({
      title: data.enabled ? 'WhatsApp ready' : 'WhatsApp settings saved',
      description: data.enabled ? 'Confirmations can be sent from Book' : 'Enable + API key required to send',
      color: data.enabled ? 'success' : 'warning'
    })
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Save failed', color: 'error' })
  } finally {
    saving.value = false
  }
}

function openNewLab() {
  editingLabId.value = null
  labForm.name = ''
  labForm.contact_person = ''
  labForm.phone = ''
  labForm.notes = ''
  labFormOpen.value = true
}

function openEditLab(lab: DentalLab) {
  editingLabId.value = lab.lab_id
  labForm.name = lab.name
  labForm.contact_person = lab.contact_person || ''
  labForm.phone = lab.phone || ''
  labForm.notes = lab.notes || ''
  labFormOpen.value = true
}

async function saveLab() {
  if (!labForm.name.trim()) {
    toast.add({ title: 'Lab name required', color: 'warning' })
    return
  }
  labSaving.value = true
  try {
    const body = {
      name: labForm.name.trim(),
      contact_person: labForm.contact_person || null,
      phone: labForm.phone || null,
      notes: labForm.notes || null
    }
    if (editingLabId.value) {
      await api(`/labs/${editingLabId.value}`, { method: 'PATCH', body })
      toast.add({ title: 'Lab updated', color: 'success' })
    } else {
      await api('/labs', { method: 'POST', body })
      toast.add({ title: 'Lab added', color: 'success' })
    }
    labFormOpen.value = false
    await loadLabs()
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
  } finally {
    labSaving.value = false
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
  void load()
  void loadLabs()
})
</script>

<template>
  <div class="h-full min-h-0 overflow-y-auto px-5 py-5">
    <div class="mx-auto max-w-xl space-y-8">
      <div>
        <h2 class="text-lg font-semibold text-[#1C2B35]">Settings</h2>
        <p class="mt-1 text-sm text-slate-500">Clinic WhatsApp and dental lab vendors</p>
      </div>

      <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
      <p v-else-if="loading" class="text-sm text-slate-400">Loading…</p>

      <form
        v-else
        class="space-y-4 rounded-2xl border border-slate-200 bg-white p-5"
        @submit.prevent="save"
      >
        <div class="flex items-start justify-between gap-3">
          <div>
            <p class="text-sm font-medium text-[#1C2B35]">WhatsApp messaging</p>
            <p class="mt-0.5 text-xs text-slate-500">
              Uses <span class="font-mono">appointment_confirm</span> via wa.aarogyams.com
            </p>
          </div>
          <label class="inline-flex cursor-pointer items-center gap-2 text-sm">
            <input v-model="form.wa_enabled" type="checkbox" class="h-4 w-4 accent-[#0097A7]">
            <span>{{ form.wa_enabled ? 'Enabled' : 'Disabled' }}</span>
          </label>
        </div>

        <UFormField label="API URL">
          <UInput v-model="form.wa_api_url" class="w-full" placeholder="https://wa.aarogyams.com/api.php" />
        </UFormField>

        <div class="space-y-2">
          <div class="flex items-center justify-between gap-2">
            <p class="text-sm font-medium text-[#1C2B35]">API key</p>
            <button
              v-if="form.has_api_key && !form.replace_key"
              type="button"
              class="text-xs font-medium text-[#0097A7] hover:underline"
              @click="form.replace_key = true"
            >
              Replace key
            </button>
          </div>
          <p v-if="form.has_api_key && !form.replace_key" class="rounded-lg bg-slate-50 px-3 py-2 font-mono text-sm text-slate-600">
            Key saved {{ form.api_key_preview }}
          </p>
          <template v-else>
            <UInput
              v-model="form.wa_api_key"
              type="password"
              class="w-full"
              autocomplete="off"
              :placeholder="form.has_api_key ? 'Paste new key (leave blank to clear)' : 'Paste clinic API key'"
            />
            <button
              v-if="form.has_api_key"
              type="button"
              class="text-xs text-slate-500 hover:text-slate-700"
              @click="form.replace_key = false; form.wa_api_key = ''"
            >
              Cancel replace
            </button>
          </template>
        </div>

        <div
          class="rounded-lg px-3 py-2 text-xs"
          :class="form.wa_enabled && (form.has_api_key || form.wa_api_key.trim())
            ? 'bg-emerald-50 text-emerald-800'
            : 'bg-amber-50 text-amber-800'"
        >
          <template v-if="form.wa_enabled && (form.has_api_key || form.wa_api_key.trim())">
            Ready — Book confirm will show the WhatsApp checkbox.
          </template>
          <template v-else>
            Turn on messaging and save an API key to send confirmations.
          </template>
        </div>

        <div class="flex justify-end gap-2 pt-1">
          <UButton color="neutral" variant="ghost" type="button" @click="load">Reset</UButton>
          <UButton type="submit" class="bg-[#0097A7]" :loading="saving">Save</UButton>
        </div>
      </form>

      <section class="space-y-3 rounded-2xl border border-slate-200 bg-white p-5">
        <div class="flex items-center justify-between gap-2">
          <div>
            <p class="text-sm font-medium text-[#1C2B35]">Dental lab vendors</p>
            <p class="mt-0.5 text-xs text-slate-500">Used when creating lab cases</p>
          </div>
          <UButton size="sm" class="bg-[#0097A7]" @click="openNewLab">Add lab</UButton>
        </div>
        <p v-if="labsLoading" class="text-sm text-slate-400">Loading labs…</p>
        <ul v-else class="divide-y divide-slate-100">
          <li v-if="!labs.length" class="py-6 text-center text-sm text-slate-500">No labs yet.</li>
          <li
            v-for="lab in labs"
            :key="lab.lab_id"
            class="flex flex-wrap items-center justify-between gap-2 py-3"
          >
            <div class="min-w-0">
              <p class="text-sm font-medium text-[#1C2B35]">{{ lab.name }}</p>
              <p class="text-xs text-slate-500">
                {{ [lab.contact_person, lab.phone].filter(Boolean).join(' · ') || 'No contact' }}
              </p>
            </div>
            <div class="flex gap-2">
              <UButton size="xs" color="neutral" variant="outline" @click="openEditLab(lab)">Edit</UButton>
              <UButton size="xs" color="error" variant="ghost" @click="archiveLab(lab)">Archive</UButton>
            </div>
          </li>
        </ul>
      </section>
    </div>

    <UModal v-model:open="labFormOpen" :title="editingLabId ? 'Edit lab' : 'Add lab'">
      <template #body>
        <form class="space-y-3" @submit.prevent="saveLab">
          <UFormField label="Name" required>
            <UInput v-model="labForm.name" class="w-full" />
          </UFormField>
          <UFormField label="Contact person">
            <UInput v-model="labForm.contact_person" class="w-full" />
          </UFormField>
          <UFormField label="Phone">
            <UInput v-model="labForm.phone" class="w-full" />
          </UFormField>
          <UFormField label="Notes">
            <UTextarea v-model="labForm.notes" class="w-full" :rows="2" />
          </UFormField>
          <div class="flex justify-end gap-2">
            <UButton color="neutral" variant="ghost" type="button" @click="labFormOpen = false">Cancel</UButton>
            <UButton type="submit" class="bg-[#0097A7]" :loading="labSaving">Save</UButton>
          </div>
        </form>
      </template>
    </UModal>
  </div>
</template>
