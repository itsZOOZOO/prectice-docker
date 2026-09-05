<script setup lang="ts">
import { compressProfilePhoto } from '~/utils/compressProfilePhoto'
import {
  CLIENT_STATUSES,
  COUNTRY_CODES,
  LEAD_SOURCES,
  PHONE_TYPES,
  ageFromDob,
  newPhoneDraft,
  type PatientFormInitial,
  type PatientPhoneDraft
} from '~/utils/patientForm'

export type { PatientFormInitial }

const props = withDefaults(defineProps<{
  mode?: 'create' | 'edit'
  clientId?: number | null
  initial?: PatientFormInitial | null
  submitLabel?: string
}>(), {
  mode: 'create',
  clientId: null,
  initial: null,
  submitLabel: undefined
})

const emit = defineEmits<{
  success: [clientId: number]
  cancel: []
  deleted: []
}>()

const { api } = useApi()
const toast = useToast()

const isEdit = computed(() => props.mode === 'edit')
const resolvedSubmit = computed(
  () => props.submitLabel || (isEdit.value ? 'Save changes' : 'Add patient')
)

const error = ref('')
const saving = ref(false)
const deleting = ref(false)
const name = ref('')
const place = ref('')
const leadSource = ref('')
const reference = ref('')
const status = ref('Inquiry')
const personalNote = ref('')
const dateOfBirth = ref('')
const age = ref<number | null>(null)
const gender = ref<'male' | 'female' | ''>('')
const checkIn = ref(true)
const moreOpen = ref(false)
const dangerOpen = ref(false)
const phones = ref<PatientPhoneDraft[]>([newPhoneDraft(true)])
const deletedPhoneIds = ref<number[]>([])
const photoFile = ref<File | null>(null)
const photoPreview = ref<string | null>(null)
const existingPhotoUrl = ref<string | null>(null)

function hydrate() {
  const init = props.initial
  name.value = init?.name || ''
  place.value = init?.place || ''
  leadSource.value = init?.lead_source || ''
  reference.value = init?.reference || ''
  status.value = init?.status || 'Inquiry'
  personalNote.value = init?.client_personal_note || ''
  dateOfBirth.value = (init?.date_of_birth || '').slice(0, 10)
  age.value = init?.age ?? (dateOfBirth.value ? ageFromDob(dateOfBirth.value) : null)
  const g = (init?.gender || '').toLowerCase()
  gender.value = g === 'male' || g === 'female' ? g : ''
  checkIn.value = !isEdit.value
  moreOpen.value = Boolean(
    (init?.status && init.status !== 'Inquiry') || init?.client_personal_note
  )
  dangerOpen.value = false
  deletedPhoneIds.value = []
  photoFile.value = null
  photoPreview.value = null
  existingPhotoUrl.value = init?.photoUrl || null
  if (init?.phones?.length) {
    phones.value = init.phones.map((p, i) => ({
      key: `p-${p.phone_id || i}-${Math.random().toString(36).slice(2, 6)}`,
      phone_id: p.phone_id && p.phone_id > 0 ? p.phone_id : undefined,
      country_code: (p.country_code || '+91').startsWith('+')
        ? (p.country_code || '+91')
        : `+${p.country_code || '91'}`,
      phone_number: p.phone_number || '',
      phone_type: p.phone_type || (i === 0 ? 'Primary' : 'Calling'),
      notes: p.notes || '',
      is_primary: Boolean(p.is_primary) || (i === 0 && !init.phones!.some(x => x.is_primary))
    }))
  } else {
    phones.value = [newPhoneDraft(true)]
  }
}

watch(() => [props.mode, props.clientId, props.initial] as const, () => hydrate(), { immediate: true, deep: true })

function onDob(v: string) {
  dateOfBirth.value = v
  age.value = v ? ageFromDob(v) : null
}

function setPrimary(key: string) {
  phones.value = phones.value.map(p => ({ ...p, is_primary: p.key === key }))
}

function addPhone() {
  phones.value = [...phones.value, newPhoneDraft(false)]
}

function removePhone(key: string) {
  if (phones.value.length <= 1) return
  const removed = phones.value.find(p => p.key === key)
  if (removed?.phone_id) deletedPhoneIds.value = [...deletedPhoneIds.value, removed.phone_id]
  let next = phones.value.filter(p => p.key !== key)
  if (!next.some(p => p.is_primary) && next[0]) {
    next = next.map((p, i) => ({ ...p, is_primary: i === 0 }))
  }
  phones.value = next
}

async function onPhotoPick(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  try {
    const compressed = await compressProfilePhoto(file)
    photoFile.value = compressed
    if (photoPreview.value) URL.revokeObjectURL(photoPreview.value)
    photoPreview.value = URL.createObjectURL(compressed)
  } catch (err: unknown) {
    toast.add({ title: err instanceof Error ? err.message : 'Photo failed', color: 'error' })
  }
  input.value = ''
}

function clearPhoto() {
  photoFile.value = null
  if (photoPreview.value) URL.revokeObjectURL(photoPreview.value)
  photoPreview.value = null
}

const displayPhoto = computed(() => photoPreview.value || existingPhotoUrl.value)

async function submit() {
  error.value = ''
  const nm = name.value.trim()
  if (!nm) {
    error.value = 'Name is required.'
    return
  }
  const validPhones = phones.value.filter(p => p.phone_number.trim())
  if (!validPhones.length) {
    error.value = 'At least one phone number is required.'
    return
  }
  if (!isEdit.value && !dateOfBirth.value) {
    error.value = 'Date of birth is required.'
    return
  }
  if (!gender.value) {
    error.value = 'Gender is required.'
    return
  }
  if (isEdit.value && !props.clientId) {
    error.value = 'Client id is missing.'
    return
  }

  if (!validPhones.some(p => p.is_primary)) {
    validPhones[0].is_primary = true
  }

  saving.value = true
  try {
    const body: Record<string, unknown> = {
      name: nm,
      place: place.value.trim() || null,
      lead_source: leadSource.value.trim() || null,
      reference: reference.value.trim() || null,
      status: status.value || 'Inquiry',
      client_personal_note: personalNote.value.trim() || null,
      gender: gender.value,
      date_of_birth: dateOfBirth.value || null,
      age: age.value,
      phones: validPhones.map(p => ({
        id: p.phone_id || null,
        country_code: p.country_code,
        phone_number: p.phone_number.trim(),
        phone_type: p.phone_type,
        notes: p.notes.trim() || null,
        is_primary: p.is_primary
      }))
    }
    if (!isEdit.value) body.check_in_status = checkIn.value
    if (isEdit.value && deletedPhoneIds.value.length) {
      body.deleted_phone_ids = deletedPhoneIds.value
    }

    let clientId = props.clientId || 0
    if (isEdit.value) {
      await api(`/clients/${clientId}`, { method: 'PATCH', body })
    } else {
      const created = await api<{ client_id: number }>('/clients', { method: 'POST', body })
      clientId = created.client_id
    }

    if (photoFile.value && clientId) {
      const fd = new FormData()
      fd.append('file', photoFile.value)
      await api(`/clients/${clientId}/photo`, { method: 'POST', body: fd })
    }

    toast.add({
      title: isEdit.value ? 'Client updated' : 'Patient added',
      color: 'success'
    })
    emit('success', clientId)
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Something went wrong'
  } finally {
    saving.value = false
  }
}

async function onDelete() {
  if (!isEdit.value || !props.clientId || deleting.value || saving.value) return
  const label = name.value.trim() || 'this client'
  if (!window.confirm(`Delete ${label}?\n\nThis cannot be undone.`)) return
  deleting.value = true
  error.value = ''
  try {
    await api(`/clients/${props.clientId}`, { method: 'DELETE' })
    toast.add({ title: 'Client deleted', color: 'success' })
    emit('deleted')
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to delete'
  } finally {
    deleting.value = false
  }
}

onBeforeUnmount(() => {
  if (photoPreview.value) URL.revokeObjectURL(photoPreview.value)
})
</script>

<template>
  <form class="space-y-4" @submit.prevent="submit">
    <p v-if="error" class="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
      {{ error }}
    </p>

    <div class="flex items-center gap-3">
      <div class="flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-full bg-[#e0f7fa] text-lg font-semibold text-[#0097A7]">
        <img v-if="displayPhoto" :src="displayPhoto" alt="" class="h-full w-full object-cover">
        <span v-else>{{ (name || '?').charAt(0).toUpperCase() }}</span>
      </div>
      <div class="flex flex-wrap gap-2">
        <label class="cursor-pointer rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50">
          {{ displayPhoto ? 'Change photo' : 'Add photo' }}
          <input type="file" accept="image/*" class="hidden" @change="onPhotoPick">
        </label>
        <button
          v-if="photoPreview"
          type="button"
          class="rounded-lg px-2 py-1.5 text-xs text-slate-500 hover:text-red-600"
          @click="clearPhoto"
        >
          Clear new photo
        </button>
      </div>
    </div>

    <UFormField label="Name" required>
      <UInput v-model="name" class="w-full capitalize" placeholder="Patient name" autofocus />
    </UFormField>

    <div>
      <p class="mb-2 text-sm font-medium text-slate-700">
        Phone numbers <span class="text-red-500">*</span>
      </p>
      <div class="space-y-3">
        <div
          v-for="(phone, index) in phones"
          :key="phone.key"
          class="space-y-2 rounded-xl border border-slate-100 bg-slate-50/80 p-3"
        >
          <div class="flex items-center justify-between">
            <label class="flex items-center gap-2 text-sm text-slate-600">
              <input
                type="radio"
                name="primary_phone"
                class="accent-[#0097A7]"
                :checked="phone.is_primary"
                @change="setPrimary(phone.key)"
              >
              Primary (WhatsApp)
            </label>
            <button
              v-if="phones.length > 1"
              type="button"
              class="rounded-lg px-2 text-lg text-slate-400 hover:bg-white hover:text-red-500"
              :aria-label="`Remove phone ${index + 1}`"
              @click="removePhone(phone.key)"
            >
              ×
            </button>
          </div>
          <div class="grid grid-cols-3 gap-2">
            <select
              v-model="phone.country_code"
              class="rounded-xl border border-slate-200 px-2 py-2 text-sm outline-none focus:border-[#0097A7]"
            >
              <option v-for="c in COUNTRY_CODES" :key="c" :value="c">{{ c }}</option>
            </select>
            <input
              v-model="phone.phone_number"
              type="tel"
              placeholder="Phone number"
              class="col-span-2 rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-[#0097A7]"
              :required="index === 0"
            >
          </div>
          <div class="grid grid-cols-2 gap-2">
            <select
              v-model="phone.phone_type"
              class="rounded-xl border border-slate-200 px-2 py-2 text-sm outline-none focus:border-[#0097A7]"
            >
              <option v-for="t in PHONE_TYPES" :key="t" :value="t">{{ t }}</option>
            </select>
            <input
              v-model="phone.notes"
              type="text"
              placeholder="Note (optional)"
              class="rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-[#0097A7]"
            >
          </div>
        </div>
      </div>
      <button
        type="button"
        class="mt-2 text-sm font-medium text-[#0097A7] hover:underline"
        @click="addPhone"
      >
        + Add phone
      </button>
    </div>

    <div class="grid grid-cols-2 gap-3">
      <UFormField :label="isEdit ? 'Date of birth' : 'Date of birth *'">
        <UInput
          :model-value="dateOfBirth"
          type="date"
          class="w-full"
          :required="!isEdit"
          @update:model-value="onDob(String($event || ''))"
        />
      </UFormField>
      <UFormField label="Age">
        <UInput :model-value="age == null ? '' : String(age)" class="w-full" disabled />
      </UFormField>
    </div>

    <fieldset>
      <legend class="mb-1 text-sm font-medium text-slate-700">
        Gender <span class="text-red-500">*</span>
      </legend>
      <div class="flex gap-4 text-sm">
        <label class="flex items-center gap-2">
          <input v-model="gender" type="radio" value="male" class="accent-[#0097A7]" required>
          Male
        </label>
        <label class="flex items-center gap-2">
          <input v-model="gender" type="radio" value="female" class="accent-[#0097A7]">
          Female
        </label>
      </div>
    </fieldset>

    <UFormField label="Place">
      <UInput v-model="place" class="w-full" placeholder="City / area" />
    </UFormField>

    <UFormField label="Lead source">
      <select
        v-model="leadSource"
        class="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-[#0097A7]"
      >
        <option value="">— Select —</option>
        <option v-for="s in LEAD_SOURCES" :key="s" :value="s">{{ s }}</option>
      </select>
    </UFormField>

    <UFormField label="Reference">
      <UInput v-model="reference" class="w-full" placeholder="Who referred?" />
    </UFormField>

    <button
      type="button"
      class="text-sm font-medium text-[#0097A7] hover:underline"
      @click="moreOpen = !moreOpen"
    >
      {{ moreOpen ? 'Hide more' : 'More (status, note…)' }}
    </button>

    <div v-if="moreOpen" class="space-y-3">
      <UFormField label="Status">
        <select
          v-model="status"
          class="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-[#0097A7]"
        >
          <option v-for="s in CLIENT_STATUSES" :key="s" :value="s">{{ s }}</option>
        </select>
      </UFormField>
      <UFormField label="Personal note">
        <UTextarea v-model="personalNote" class="w-full" :rows="2" />
      </UFormField>
    </div>

    <label v-if="!isEdit" class="flex items-center gap-2 text-sm text-slate-700">
      <input v-model="checkIn" type="checkbox" class="rounded border-slate-300 accent-[#0097A7]">
      Check in now
    </label>

    <div class="flex flex-wrap items-center justify-end gap-2 pt-1">
      <UButton color="neutral" variant="ghost" type="button" @click="emit('cancel')">
        Cancel
      </UButton>
      <UButton type="submit" class="bg-[#0097A7]" :loading="saving">
        {{ resolvedSubmit }}
      </UButton>
    </div>

    <div v-if="isEdit" class="border-t border-slate-100 pt-4">
      <button
        type="button"
        class="text-xs font-medium text-slate-400 hover:text-slate-600"
        @click="dangerOpen = !dangerOpen"
      >
        {{ dangerOpen ? 'Hide danger zone' : 'Show danger zone…' }}
      </button>
      <div v-if="dangerOpen" class="mt-3 rounded-xl border border-red-100 bg-red-50/60 p-3">
        <p class="mb-2 text-xs text-red-700/80">
          Deleting removes this client from the desk. This cannot be undone.
        </p>
        <button
          type="button"
          class="text-sm font-medium text-red-700 underline decoration-red-300 underline-offset-2 hover:text-red-800 disabled:opacity-50"
          :disabled="deleting || saving"
          @click="onDelete"
        >
          {{ deleting ? 'Deleting…' : 'Delete client permanently' }}
        </button>
      </div>
    </div>
  </form>
</template>
