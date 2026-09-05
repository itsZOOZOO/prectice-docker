<script setup lang="ts">
definePageMeta({ layout: 'desk', middleware: 'admin' })

type ClinicRow = {
  clinic_id: number
  clinic_name: string
  clinic_address: string | null
  clinic_phone: string | null
  clinic_email: string | null
  is_active: boolean
  user_count: number
}

const { api } = useApi()
const toast = useToast()

const clinics = ref<ClinicRow[]>([])
const loading = ref(true)
const createOpen = ref(false)
const saving = ref(false)
const form = reactive({
  clinic_name: '',
  clinic_address: '',
  clinic_phone: '',
  clinic_email: '',
  is_active: true
})

async function load() {
  loading.value = true
  try {
    clinics.value = await api<ClinicRow[]>('/admin/clinics')
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to load clinics', color: 'error' })
  } finally {
    loading.value = false
  }
}

function openCreate() {
  form.clinic_name = ''
  form.clinic_address = ''
  form.clinic_phone = ''
  form.clinic_email = ''
  form.is_active = true
  createOpen.value = true
}

async function createClinic() {
  if (!form.clinic_name.trim()) return
  saving.value = true
  try {
    await api('/admin/clinics', {
      method: 'POST',
      body: {
        clinic_name: form.clinic_name.trim(),
        clinic_address: form.clinic_address.trim() || null,
        clinic_phone: form.clinic_phone.trim() || null,
        clinic_email: form.clinic_email.trim() || null,
        is_active: form.is_active
      }
    })
    toast.add({ title: 'Clinic created', color: 'success' })
    createOpen.value = false
    await load()
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Create failed', color: 'error' })
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="h-full min-h-0 overflow-y-auto bg-[#F0F4F8] p-6">
    <div class="mx-auto max-w-5xl">
      <div class="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p class="text-[11px] font-semibold uppercase tracking-wide text-slate-400">Platform</p>
          <h2 class="text-xl font-semibold text-[#1C2B35]">Clinics</h2>
        </div>
        <UButton class="bg-[#0097A7]" @click="openCreate">
          <UIcon name="i-lucide-plus" class="h-4 w-4" />
          Add clinic
        </UButton>
      </div>

      <p v-if="loading" class="text-sm text-slate-500">Loading…</p>
      <div v-else class="overflow-hidden rounded-xl border border-slate-200 bg-white">
        <table class="w-full text-left text-sm">
          <thead class="border-b border-slate-100 bg-slate-50 text-[11px] uppercase tracking-wide text-slate-500">
            <tr>
              <th class="px-4 py-3 font-semibold">ID</th>
              <th class="px-4 py-3 font-semibold">Clinic</th>
              <th class="px-4 py-3 font-semibold">Phone</th>
              <th class="px-4 py-3 font-semibold">Users</th>
              <th class="px-4 py-3 font-semibold">Status</th>
              <th class="px-4 py-3 font-semibold" />
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="c in clinics"
              :key="c.clinic_id"
              class="border-b border-slate-50 last:border-b-0 hover:bg-slate-50/80"
            >
              <td class="px-4 py-3 text-slate-500">{{ c.clinic_id }}</td>
              <td class="px-4 py-3">
                <p class="font-medium text-[#1C2B35]">{{ c.clinic_name }}</p>
                <p v-if="c.clinic_address" class="truncate text-xs text-slate-400">{{ c.clinic_address }}</p>
              </td>
              <td class="px-4 py-3 text-slate-600">{{ c.clinic_phone || '—' }}</td>
              <td class="px-4 py-3 text-slate-600">{{ c.user_count }}</td>
              <td class="px-4 py-3">
                <span
                  class="rounded-full px-2 py-0.5 text-[11px] font-semibold"
                  :class="c.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'"
                >
                  {{ c.is_active ? 'Active' : 'Inactive' }}
                </span>
              </td>
              <td class="px-4 py-3 text-right">
                <NuxtLink
                  :to="`/admin/clinics/${c.clinic_id}`"
                  class="text-xs font-semibold text-[#0097A7] hover:underline"
                >
                  Open →
                </NuxtLink>
              </td>
            </tr>
            <tr v-if="!clinics.length">
              <td colspan="6" class="px-4 py-10 text-center text-slate-400">No clinics yet.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <UModal v-model:open="createOpen" title="Add clinic">
      <template #body>
        <form class="space-y-3" @submit.prevent="createClinic">
          <UFormField label="Name" required>
            <UInput v-model="form.clinic_name" class="w-full" autofocus />
          </UFormField>
          <UFormField label="Address">
            <UInput v-model="form.clinic_address" class="w-full" />
          </UFormField>
          <div class="grid grid-cols-2 gap-2">
            <UFormField label="Phone">
              <UInput v-model="form.clinic_phone" class="w-full" />
            </UFormField>
            <UFormField label="Email">
              <UInput v-model="form.clinic_email" class="w-full" />
            </UFormField>
          </div>
          <label class="flex items-center gap-2 text-sm text-slate-700">
            <input v-model="form.is_active" type="checkbox" class="rounded">
            Active
          </label>
          <div class="flex justify-end gap-2 pt-2">
            <UButton color="neutral" variant="ghost" type="button" @click="createOpen = false">Cancel</UButton>
            <UButton type="submit" class="bg-[#0097A7]" :loading="saving" :disabled="!form.clinic_name.trim()">
              Create
            </UButton>
          </div>
        </form>
      </template>
    </UModal>
  </div>
</template>
