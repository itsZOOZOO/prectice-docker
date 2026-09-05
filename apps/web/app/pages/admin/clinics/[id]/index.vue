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

type UserRow = {
  user_id: number
  clinic_id: number
  username: string
  full_name: string
  role: string
  email: string | null
  active: boolean
}

const route = useRoute()
const clinicId = computed(() => Number(route.params.id))
const { api } = useApi()
const toast = useToast()

const clinic = ref<ClinicRow | null>(null)
const users = ref<UserRow[]>([])
const loading = ref(true)

const editClinicOpen = ref(false)
const clinicForm = reactive({
  clinic_name: '',
  clinic_address: '',
  clinic_phone: '',
  clinic_email: '',
  is_active: true
})
const savingClinic = ref(false)

const userModalOpen = ref(false)
const editingUser = ref<UserRow | null>(null)
const userForm = reactive({
  username: '',
  full_name: '',
  email: '',
  role: 'staff',
  password: '',
  active: true
})
const savingUser = ref(false)

const resetOpen = ref(false)
const resetUserId = ref<number | null>(null)
const resetPassword = ref('')
const resetting = ref(false)

const roles = [
  { value: 'admin', label: 'Admin' },
  { value: 'doctor', label: 'Doctor' },
  { value: 'staff', label: 'Staff' }
]

const comingSoon = [
  { title: 'Medicine templates', desc: 'Prescription medicine catalog', icon: 'i-lucide-pill' },
  { title: 'Treatment plans', desc: 'Treatment catalog & pricing', icon: 'i-lucide-stethoscope' },
  { title: 'WhatsApp', desc: 'API key, enable / disable messaging', icon: 'i-lucide-message-circle' },
  { title: 'WA message templates', desc: 'Appointment, prescription & other defaults', icon: 'i-lucide-mail' },
  { title: 'Leads module', desc: 'Enable / disable leads for this clinic', icon: 'i-lucide-target' },
  { title: 'Call module', desc: 'Enable / disable call desk features', icon: 'i-lucide-phone' }
]

async function load() {
  if (!Number.isFinite(clinicId.value) || clinicId.value <= 0) return
  loading.value = true
  try {
    const [c, u] = await Promise.all([
      api<ClinicRow>(`/admin/clinics/${clinicId.value}`),
      api<UserRow[]>(`/admin/clinics/${clinicId.value}/users`)
    ])
    clinic.value = c
    users.value = u
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to load', color: 'error' })
  } finally {
    loading.value = false
  }
}

function openEditClinic() {
  if (!clinic.value) return
  clinicForm.clinic_name = clinic.value.clinic_name
  clinicForm.clinic_address = clinic.value.clinic_address || ''
  clinicForm.clinic_phone = clinic.value.clinic_phone || ''
  clinicForm.clinic_email = clinic.value.clinic_email || ''
  clinicForm.is_active = clinic.value.is_active
  editClinicOpen.value = true
}

async function saveClinic() {
  if (!clinic.value || !clinicForm.clinic_name.trim()) return
  savingClinic.value = true
  try {
    clinic.value = await api<ClinicRow>(`/admin/clinics/${clinic.value.clinic_id}`, {
      method: 'PATCH',
      body: {
        clinic_name: clinicForm.clinic_name.trim(),
        clinic_address: clinicForm.clinic_address.trim() || null,
        clinic_phone: clinicForm.clinic_phone.trim() || null,
        clinic_email: clinicForm.clinic_email.trim() || null,
        is_active: clinicForm.is_active
      }
    })
    toast.add({ title: 'Clinic updated', color: 'success' })
    editClinicOpen.value = false
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Update failed', color: 'error' })
  } finally {
    savingClinic.value = false
  }
}

function openCreateUser() {
  editingUser.value = null
  userForm.username = ''
  userForm.full_name = ''
  userForm.email = ''
  userForm.role = 'staff'
  userForm.password = ''
  userForm.active = true
  userModalOpen.value = true
}

function openEditUser(u: UserRow) {
  editingUser.value = u
  userForm.username = u.username
  userForm.full_name = u.full_name
  userForm.email = u.email || ''
  userForm.role = u.role === 'superadmin' ? 'admin' : u.role
  userForm.password = ''
  userForm.active = u.active
  userModalOpen.value = true
}

async function saveUser() {
  if (!clinic.value) return
  if (!userForm.full_name.trim()) return
  savingUser.value = true
  try {
    if (editingUser.value) {
      await api(`/admin/clinics/${clinic.value.clinic_id}/users/${editingUser.value.user_id}`, {
        method: 'PATCH',
        body: {
          full_name: userForm.full_name.trim(),
          email: userForm.email.trim() || null,
          role: editingUser.value.role === 'superadmin' ? undefined : userForm.role,
          active: userForm.active
        }
      })
      toast.add({ title: 'User updated', color: 'success' })
    } else {
      if (!userForm.username.trim() || userForm.password.length < 6) {
        toast.add({ title: 'Username and password (6+) required', color: 'warning' })
        savingUser.value = false
        return
      }
      await api(`/admin/clinics/${clinic.value.clinic_id}/users`, {
        method: 'POST',
        body: {
          username: userForm.username.trim(),
          full_name: userForm.full_name.trim(),
          email: userForm.email.trim() || null,
          role: userForm.role,
          password: userForm.password
        }
      })
      toast.add({ title: 'User created', color: 'success' })
    }
    userModalOpen.value = false
    await load()
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Save failed', color: 'error' })
  } finally {
    savingUser.value = false
  }
}

function openReset(u: UserRow) {
  resetUserId.value = u.user_id
  resetPassword.value = ''
  resetOpen.value = true
}

async function doReset() {
  if (!clinic.value || !resetUserId.value || resetPassword.value.length < 6) return
  resetting.value = true
  try {
    await api(`/admin/clinics/${clinic.value.clinic_id}/users/${resetUserId.value}/reset-password`, {
      method: 'POST',
      body: { password: resetPassword.value }
    })
    toast.add({ title: 'Password reset', color: 'success' })
    resetOpen.value = false
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Reset failed', color: 'error' })
  } finally {
    resetting.value = false
  }
}

watch(clinicId, load, { immediate: true })
</script>

<template>
  <div class="h-full min-h-0 overflow-y-auto bg-[#F0F4F8] p-6">
    <div class="mx-auto max-w-5xl space-y-6">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <NuxtLink to="/admin" class="text-xs font-semibold text-[#0097A7] hover:underline">← All clinics</NuxtLink>
          <h2 class="mt-1 text-xl font-semibold text-[#1C2B35]">
            {{ clinic?.clinic_name || (loading ? 'Loading…' : 'Clinic') }}
          </h2>
          <p v-if="clinic" class="mt-0.5 text-sm text-slate-500">
            ID {{ clinic.clinic_id }}
            <span v-if="clinic.clinic_phone"> · {{ clinic.clinic_phone }}</span>
            <span v-if="clinic.clinic_email"> · {{ clinic.clinic_email }}</span>
          </p>
        </div>
        <UButton v-if="clinic" color="neutral" variant="outline" @click="openEditClinic">
          Edit clinic
        </UButton>
      </div>

      <!-- Users -->
      <section class="overflow-hidden rounded-xl border border-slate-200 bg-white">
        <div class="flex items-center justify-between gap-2 border-b border-slate-100 px-4 py-3">
          <h3 class="text-sm font-semibold text-[#1C2B35]">Users</h3>
          <UButton size="sm" class="bg-[#0097A7]" @click="openCreateUser">
            <UIcon name="i-lucide-user-plus" class="h-3.5 w-3.5" />
            Add user
          </UButton>
        </div>
        <table class="w-full text-left text-sm">
          <thead class="border-b border-slate-100 bg-slate-50 text-[11px] uppercase tracking-wide text-slate-500">
            <tr>
              <th class="px-4 py-2.5 font-semibold">Name</th>
              <th class="px-4 py-2.5 font-semibold">Username</th>
              <th class="px-4 py-2.5 font-semibold">Role</th>
              <th class="px-4 py-2.5 font-semibold">Status</th>
              <th class="px-4 py-2.5 font-semibold" />
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="u in users"
              :key="u.user_id"
              class="border-b border-slate-50 last:border-b-0"
            >
              <td class="px-4 py-2.5">
                <p class="font-medium text-[#1C2B35]">{{ u.full_name }}</p>
                <p v-if="u.email" class="text-xs text-slate-400">{{ u.email }}</p>
              </td>
              <td class="px-4 py-2.5 text-slate-600">{{ u.username }}</td>
              <td class="px-4 py-2.5">
                <span class="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600">
                  {{ u.role }}
                </span>
              </td>
              <td class="px-4 py-2.5">
                <span
                  class="text-[11px] font-semibold"
                  :class="u.active ? 'text-emerald-700' : 'text-slate-400'"
                >
                  {{ u.active ? 'Active' : 'Inactive' }}
                </span>
              </td>
              <td class="px-4 py-2.5 text-right">
                <button type="button" class="mr-2 text-xs font-semibold text-[#0097A7] hover:underline" @click="openEditUser(u)">
                  Edit
                </button>
                <button type="button" class="text-xs font-semibold text-slate-500 hover:underline" @click="openReset(u)">
                  Reset password
                </button>
              </td>
            </tr>
            <tr v-if="!loading && !users.length">
              <td colspan="5" class="px-4 py-8 text-center text-slate-400">No users yet.</td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- Letterhead + coming soon -->
      <section>
        <h3 class="mb-3 text-sm font-semibold text-[#1C2B35]">Clinic settings</h3>
        <div class="grid gap-3 sm:grid-cols-2">
          <NuxtLink
            :to="`/admin/clinics/${clinicId}/letterhead`"
            class="rounded-xl border border-slate-200 bg-white p-4 transition hover:border-[#0097A7]/40 hover:shadow-sm"
          >
            <div class="flex items-start gap-3">
              <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[#e0f7fa] text-[#0097A7]">
                <UIcon name="i-lucide-file-text" class="h-4 w-4" />
              </div>
              <div>
                <p class="text-sm font-semibold text-[#1C2B35]">Letterhead</p>
                <p class="mt-0.5 text-xs text-slate-500">Print & WhatsApp PDF templates per clinic</p>
              </div>
            </div>
          </NuxtLink>
          <div
            v-for="card in comingSoon"
            :key="card.title"
            class="relative rounded-xl border border-dashed border-slate-200 bg-white/80 p-4 opacity-90"
          >
            <span class="absolute right-3 top-3 rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-amber-700">
              Coming soon
            </span>
            <div class="flex items-start gap-3 pr-20">
              <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-500">
                <UIcon :name="card.icon" class="h-4 w-4" />
              </div>
              <div>
                <p class="text-sm font-semibold text-[#1C2B35]">{{ card.title }}</p>
                <p class="mt-0.5 text-xs text-slate-500">{{ card.desc }}</p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>

    <UModal v-model:open="editClinicOpen" title="Edit clinic">
      <template #body>
        <form class="space-y-3" @submit.prevent="saveClinic">
          <UFormField label="Name" required>
            <UInput v-model="clinicForm.clinic_name" class="w-full" />
          </UFormField>
          <UFormField label="Address">
            <UInput v-model="clinicForm.clinic_address" class="w-full" />
          </UFormField>
          <div class="grid grid-cols-2 gap-2">
            <UFormField label="Phone">
              <UInput v-model="clinicForm.clinic_phone" class="w-full" />
            </UFormField>
            <UFormField label="Email">
              <UInput v-model="clinicForm.clinic_email" class="w-full" />
            </UFormField>
          </div>
          <label class="flex items-center gap-2 text-sm">
            <input v-model="clinicForm.is_active" type="checkbox" class="rounded">
            Active
          </label>
          <div class="flex justify-end gap-2">
            <UButton color="neutral" variant="ghost" type="button" @click="editClinicOpen = false">Cancel</UButton>
            <UButton type="submit" class="bg-[#0097A7]" :loading="savingClinic">Save</UButton>
          </div>
        </form>
      </template>
    </UModal>

    <UModal v-model:open="userModalOpen" :title="editingUser ? 'Edit user' : 'Add user'">
      <template #body>
        <form class="space-y-3" @submit.prevent="saveUser">
          <UFormField v-if="!editingUser" label="Username" required>
            <UInput v-model="userForm.username" class="w-full" autocomplete="off" />
          </UFormField>
          <UFormField v-else label="Username">
            <UInput :model-value="userForm.username" class="w-full" disabled />
          </UFormField>
          <UFormField label="Full name" required>
            <UInput v-model="userForm.full_name" class="w-full" />
          </UFormField>
          <UFormField label="Email">
            <UInput v-model="userForm.email" class="w-full" />
          </UFormField>
          <UFormField v-if="!editingUser || editingUser.role !== 'superadmin'" label="Role">
            <select
              v-model="userForm.role"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-[#0097A7]"
            >
              <option v-for="r in roles" :key="r.value" :value="r.value">{{ r.label }}</option>
            </select>
          </UFormField>
          <UFormField v-if="!editingUser" label="Password" required>
            <UInput v-model="userForm.password" type="password" class="w-full" autocomplete="new-password" />
          </UFormField>
          <label v-if="editingUser" class="flex items-center gap-2 text-sm">
            <input v-model="userForm.active" type="checkbox" class="rounded">
            Active
          </label>
          <div class="flex justify-end gap-2">
            <UButton color="neutral" variant="ghost" type="button" @click="userModalOpen = false">Cancel</UButton>
            <UButton type="submit" class="bg-[#0097A7]" :loading="savingUser">
              {{ editingUser ? 'Save' : 'Create' }}
            </UButton>
          </div>
        </form>
      </template>
    </UModal>

    <UModal v-model:open="resetOpen" title="Reset password">
      <template #body>
        <form class="space-y-3" @submit.prevent="doReset">
          <UFormField label="New password" required>
            <UInput v-model="resetPassword" type="password" class="w-full" autocomplete="new-password" />
          </UFormField>
          <div class="flex justify-end gap-2">
            <UButton color="neutral" variant="ghost" type="button" @click="resetOpen = false">Cancel</UButton>
            <UButton
              type="submit"
              class="bg-[#0097A7]"
              :loading="resetting"
              :disabled="resetPassword.length < 6"
            >
              Reset
            </UButton>
          </div>
        </form>
      </template>
    </UModal>
  </div>
</template>
