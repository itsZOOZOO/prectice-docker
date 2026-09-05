<script setup lang="ts">
type TreatmentPhoto = {
  photo_id: number
  photo_url: string
  key?: string
  sort_order?: number
}

type PriceOptionPhoto = {
  photo_id: number
  photo_url: string
  key?: string
}

type PriceOptionDraft = {
  id: number | null
  price_option_id: number | null
  label: string
  price: number
  explainer: string
  is_foc: boolean
  photos: PriceOptionPhoto[]
}

type TreatmentListItem = {
  id: number
  name: string
  short_explainer: string | null
  default_appts: number
  active: boolean
  sort_order: number
  price_option_count: number
  photo_count: number
}

type TreatmentDetail = {
  id: number
  treatment_id: number
  name: string
  short_explainer: string | null
  default_appts: number
  active: boolean
  sort_order: number
  price_options: Array<{
    id: number
    price_option_id: number
    label: string
    price: number
    explainer: string | null
    is_foc: boolean
    photos: PriceOptionPhoto[]
  }>
  photos: TreatmentPhoto[]
  price_option_count: number
  photo_count: number
}

function emptyPriceOption(): PriceOptionDraft {
  return {
    id: null,
    price_option_id: null,
    label: '',
    price: 0,
    explainer: '',
    is_foc: false,
    photos: []
  }
}

const { api } = useApi()
const toast = useToast()

const treatments = ref<TreatmentListItem[]>([])
const loading = ref(false)
const saving = ref(false)
const uploading = ref(false)
const search = ref('')
const error = ref('')

const selectedId = ref<number | null>(null)
const creating = ref(false)
const detail = ref<TreatmentDetail | null>(null)

const form = reactive({
  name: '',
  short_explainer: '',
  default_appts: '0',
  active: true,
  sort_order: '0'
})
const priceOptions = ref<PriceOptionDraft[]>([])
const formError = ref('')

const photoInputRef = ref<HTMLInputElement | null>(null)
const optionPhotoInputRef = ref<HTMLInputElement | null>(null)
const pendingOptionPhotoId = ref<number | null>(null)

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return treatments.value
  return treatments.value.filter(t =>
    t.name.toLowerCase().includes(q)
    || (t.short_explainer ?? '').toLowerCase().includes(q)
  )
})

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const data = await api<{ treatments: TreatmentListItem[] }>('/settings/treatments')
    treatments.value = data.treatments ?? []
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to load treatments'
    toast.add({ title: error.value, color: 'error' })
  } finally {
    loading.value = false
  }
}

function applyDetail(t: TreatmentDetail) {
  detail.value = t
  form.name = t.name
  form.short_explainer = t.short_explainer ?? ''
  form.default_appts = String(t.default_appts ?? 0)
  form.active = !!t.active
  form.sort_order = String(t.sort_order ?? 0)
  priceOptions.value = (t.price_options ?? []).map(po => ({
    id: po.id ?? po.price_option_id,
    price_option_id: po.price_option_id ?? po.id,
    label: po.label,
    price: Number(po.price) || 0,
    explainer: po.explainer ?? '',
    is_foc: !!po.is_foc,
    photos: po.photos ?? []
  }))
  formError.value = ''
}

function resetCreateForm() {
  detail.value = null
  form.name = ''
  form.short_explainer = ''
  form.default_appts = '0'
  form.active = true
  form.sort_order = '0'
  priceOptions.value = [emptyPriceOption()]
  formError.value = ''
}

async function openTreatment(id: number) {
  creating.value = false
  selectedId.value = id
  loading.value = true
  error.value = ''
  try {
    const data = await api<TreatmentDetail>(`/settings/treatments/${id}`)
    applyDetail(data)
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to load treatment'
    toast.add({ title: error.value, color: 'error' })
    selectedId.value = null
  } finally {
    loading.value = false
  }
}

function openCreate() {
  selectedId.value = null
  creating.value = true
  resetCreateForm()
}

function backToList() {
  selectedId.value = null
  creating.value = false
  detail.value = null
  void loadList()
}

function addPriceOption() {
  priceOptions.value = [...priceOptions.value, emptyPriceOption()]
}

function removePriceOption(index: number) {
  priceOptions.value = priceOptions.value.filter((_, i) => i !== index)
}

function buildPayload() {
  return {
    name: form.name.trim(),
    short_explainer: form.short_explainer.trim() || null,
    default_appts: Number(form.default_appts) || 0,
    active: form.active,
    sort_order: Number(form.sort_order) || 0,
    price_options: priceOptions.value
      .filter(po => po.label.trim())
      .map(po => ({
        id: po.id ?? undefined,
        price_option_id: po.price_option_id ?? undefined,
        label: po.label.trim(),
        price: Number(po.price) || 0,
        explainer: po.explainer.trim() || null,
        is_foc: !!po.is_foc
      }))
  }
}

async function saveTreatment() {
  if (!form.name.trim()) {
    formError.value = 'Treatment name is required.'
    return
  }
  saving.value = true
  formError.value = ''
  try {
    const payload = buildPayload()
    if (creating.value || selectedId.value == null) {
      const data = await api<TreatmentDetail>('/settings/treatments', {
        method: 'POST',
        body: payload
      })
      toast.add({ title: 'Treatment created', color: 'success' })
      creating.value = false
      selectedId.value = data.id ?? data.treatment_id
      applyDetail(data)
    } else {
      const data = await api<TreatmentDetail>(`/settings/treatments/${selectedId.value}`, {
        method: 'PUT',
        body: payload
      })
      toast.add({ title: 'Treatment updated', color: 'success' })
      applyDetail(data)
    }
  } catch (e: unknown) {
    formError.value = e instanceof Error ? e.message : 'Failed to save treatment'
  } finally {
    saving.value = false
  }
}

async function toggleActive(row: TreatmentListItem) {
  try {
    await api(`/settings/treatments/${row.id}/active`, {
      method: 'PATCH',
      body: { active: !row.active }
    })
    treatments.value = treatments.value.map(t =>
      t.id === row.id ? { ...t, active: !row.active } : t
    )
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to update', color: 'error' })
  }
}

async function deleteTreatment(row: TreatmentListItem) {
  if (!window.confirm(`Delete “${row.name}”? If in use it will be deactivated instead.`)) return
  try {
    const data = await api<{ id: number, deleted: boolean, active?: boolean }>(
      `/settings/treatments/${row.id}`,
      { method: 'DELETE' }
    )
    if (data.deleted) {
      toast.add({ title: 'Treatment deleted', color: 'success' })
    } else {
      toast.add({ title: 'Treatment deactivated (in use)', color: 'warning' })
    }
    if (selectedId.value === row.id) backToList()
    else await loadList()
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to delete', color: 'error' })
  }
}

function triggerPhotoUpload() {
  photoInputRef.value?.click()
}

function triggerOptionPhotoUpload(optionId: number) {
  pendingOptionPhotoId.value = optionId
  optionPhotoInputRef.value?.click()
}

async function onTreatmentPhotoSelected(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || selectedId.value == null) return
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    await api(`/settings/treatments/${selectedId.value}/photos`, {
      method: 'POST',
      body: fd
    })
    toast.add({ title: 'Photo uploaded', color: 'success' })
    await openTreatment(selectedId.value)
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Upload failed', color: 'error' })
  } finally {
    uploading.value = false
  }
}

async function onOptionPhotoSelected(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  const optionId = pendingOptionPhotoId.value
  pendingOptionPhotoId.value = null
  if (!file || selectedId.value == null || optionId == null) return
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    await api(`/settings/treatments/${selectedId.value}/price-options/${optionId}/photos`, {
      method: 'POST',
      body: fd
    })
    toast.add({ title: 'Option photo uploaded', color: 'success' })
    await openTreatment(selectedId.value)
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Upload failed', color: 'error' })
  } finally {
    uploading.value = false
  }
}

async function deleteTreatmentPhoto(photoId: number) {
  if (selectedId.value == null) return
  if (!window.confirm('Delete this photo?')) return
  try {
    await api(`/settings/treatments/${selectedId.value}/photos/${photoId}`, { method: 'DELETE' })
    toast.add({ title: 'Photo deleted', color: 'success' })
    await openTreatment(selectedId.value)
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to delete photo', color: 'error' })
  }
}

async function deleteOptionPhoto(optionId: number, photoId: number) {
  if (selectedId.value == null) return
  if (!window.confirm('Delete this photo?')) return
  try {
    await api(
      `/settings/treatments/${selectedId.value}/price-options/${optionId}/photos/${photoId}`,
      { method: 'DELETE' }
    )
    toast.add({ title: 'Photo deleted', color: 'success' })
    await openTreatment(selectedId.value)
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to delete photo', color: 'error' })
  }
}

onMounted(() => {
  void loadList()
})
</script>

<template>
  <div class="p-4 md:p-5">
    <input
      ref="photoInputRef"
      type="file"
      accept="image/*"
      class="hidden"
      @change="onTreatmentPhotoSelected"
    >
    <input
      ref="optionPhotoInputRef"
      type="file"
      accept="image/*"
      class="hidden"
      @change="onOptionPhotoSelected"
    >

    <!-- List view -->
    <template v-if="!creating && selectedId == null">
      <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
        <UInput v-model="search" class="w-full max-w-sm" placeholder="Search treatments…" />
        <UButton size="sm" class="bg-[#0097A7]" @click="openCreate">
          Add treatment
        </UButton>
      </div>

      <div
        v-if="error"
        class="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
      >
        {{ error }}
      </div>

      <div class="rounded-xl border border-slate-200 bg-white shadow-sm">
        <p v-if="loading" class="px-4 py-8 text-center text-sm text-slate-400">
          Loading treatments…
        </p>
        <ul v-else class="divide-y divide-slate-100">
          <li v-if="!filtered.length" class="py-8 text-center text-sm text-slate-500">
            No treatments yet.
          </li>
          <li
            v-for="row in filtered"
            :key="row.id"
            class="flex flex-wrap items-start justify-between gap-3 px-4 py-3 hover:bg-slate-50"
          >
            <button type="button" class="min-w-0 flex-1 text-left" @click="openTreatment(row.id)">
              <div class="flex flex-wrap items-center gap-2">
                <p class="text-sm font-medium text-slate-800">{{ row.name }}</p>
                <span
                  class="rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase"
                  :class="row.active
                    ? 'bg-emerald-100 text-emerald-800'
                    : 'bg-slate-200 text-slate-600'"
                >
                  {{ row.active ? 'Active' : 'Inactive' }}
                </span>
              </div>
              <p v-if="row.short_explainer" class="mt-0.5 text-xs text-slate-500 line-clamp-2">
                {{ row.short_explainer }}
              </p>
              <p class="mt-1 text-xs text-slate-400">
                {{ row.price_option_count }} options · {{ row.photo_count }} photos ·
                sort {{ row.sort_order }}
              </p>
            </button>
            <div class="flex shrink-0 flex-wrap gap-2">
              <UButton size="xs" color="neutral" variant="outline" @click="openTreatment(row.id)">
                Edit
              </UButton>
              <UButton size="xs" color="neutral" variant="ghost" @click="toggleActive(row)">
                {{ row.active ? 'Deactivate' : 'Activate' }}
              </UButton>
              <UButton size="xs" color="error" variant="ghost" @click="deleteTreatment(row)">
                Delete
              </UButton>
            </div>
          </li>
        </ul>
      </div>
    </template>

    <!-- Detail / create -->
    <template v-else>
      <div class="mb-4 flex flex-wrap items-center gap-3">
        <UButton size="sm" color="neutral" variant="outline" @click="backToList">
          ← Back
        </UButton>
        <div class="min-w-0">
          <h3 class="m-0 text-sm font-semibold text-slate-800">
            {{ creating ? 'New treatment' : (detail?.name || 'Edit treatment') }}
          </h3>
          <p class="m-0 text-xs text-slate-500">
            Pin fields, price options, and photos
          </p>
        </div>
      </div>

      <div
        v-if="loading && !creating"
        class="py-16 text-center text-sm text-slate-400"
      >
        Loading…
      </div>

      <form v-else class="space-y-4" @submit.prevent="saveTreatment">
        <div class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h4 class="mb-3 text-sm font-semibold text-slate-800">Details</h4>
          <div class="grid gap-3 md:grid-cols-2">
            <UFormField label="Name *" class="md:col-span-2">
              <UInput v-model="form.name" class="w-full" required />
            </UFormField>
            <UFormField label="Short explainer" class="md:col-span-2">
              <UTextarea v-model="form.short_explainer" class="w-full" :rows="2" />
            </UFormField>
            <UFormField label="Default appointments">
              <UInput v-model="form.default_appts" type="number" :min="0" class="w-full" />
            </UFormField>
            <UFormField label="Sort order">
              <UInput v-model="form.sort_order" type="number" class="w-full" />
            </UFormField>
            <label class="flex items-center gap-2 text-sm text-slate-700 md:col-span-2">
              <input v-model="form.active" type="checkbox" class="accent-[#0097A7]">
              Active
            </label>
          </div>
        </div>

        <div class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h4 class="m-0 text-sm font-semibold text-slate-800">Price options</h4>
            <UButton size="xs" color="neutral" variant="outline" type="button" @click="addPriceOption">
              Add option
            </UButton>
          </div>
          <div v-if="!priceOptions.length" class="py-4 text-center text-sm text-slate-400">
            No price options. Add one above.
          </div>
          <div class="space-y-4">
            <div
              v-for="(po, index) in priceOptions"
              :key="po.id ?? `new-${index}`"
              class="rounded-lg border border-slate-100 bg-slate-50/80 p-3"
            >
              <div class="grid gap-3 md:grid-cols-2">
                <UFormField label="Label *" class="md:col-span-2">
                  <UInput v-model="po.label" class="w-full" placeholder="e.g. Standard" />
                </UFormField>
                <UFormField label="Price">
                  <UInput v-model.number="po.price" type="number" :min="0" step="0.01" class="w-full" />
                </UFormField>
                <label class="flex items-center gap-2 self-end pb-1 text-sm text-slate-700">
                  <input v-model="po.is_foc" type="checkbox" class="accent-[#0097A7]">
                  FOC (free of charge)
                </label>
                <UFormField label="Explainer" class="md:col-span-2">
                  <UInput v-model="po.explainer" class="w-full" />
                </UFormField>
              </div>

              <div v-if="po.id != null" class="mt-3">
                <div class="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <p class="text-xs font-medium text-slate-600">Option photos</p>
                  <UButton
                    size="xs"
                    color="neutral"
                    variant="ghost"
                    type="button"
                    :loading="uploading"
                    @click="triggerOptionPhotoUpload(po.id!)"
                  >
                    Upload photo
                  </UButton>
                </div>
                <div v-if="po.photos.length" class="flex flex-wrap gap-2">
                  <div
                    v-for="ph in po.photos"
                    :key="ph.photo_id"
                    class="group relative h-16 w-16 overflow-hidden rounded-lg border border-slate-200"
                  >
                    <img :src="ph.photo_url" alt="" class="h-full w-full object-cover">
                    <button
                      type="button"
                      class="absolute inset-0 flex items-center justify-center bg-black/50 text-xs text-white opacity-0 transition group-hover:opacity-100"
                      @click="deleteOptionPhoto(po.id!, ph.photo_id)"
                    >
                      Delete
                    </button>
                  </div>
                </div>
                <p v-else class="text-xs text-slate-400">No photos yet.</p>
              </div>
              <p v-else class="mt-2 text-xs text-slate-400">
                Save the treatment first to upload option photos.
              </p>

              <div class="mt-3 flex justify-end">
                <UButton
                  size="xs"
                  color="error"
                  variant="ghost"
                  type="button"
                  @click="removePriceOption(index)"
                >
                  Remove option
                </UButton>
              </div>
            </div>
          </div>
        </div>

        <div
          v-if="!creating && selectedId != null"
          class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
        >
          <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h4 class="m-0 text-sm font-semibold text-slate-800">Treatment photos</h4>
            <UButton
              size="xs"
              class="bg-[#0097A7]"
              type="button"
              :loading="uploading"
              @click="triggerPhotoUpload"
            >
              Upload photo
            </UButton>
          </div>
          <div v-if="detail?.photos?.length" class="flex flex-wrap gap-3">
            <div
              v-for="ph in detail.photos"
              :key="ph.photo_id"
              class="group relative h-24 w-24 overflow-hidden rounded-lg border border-slate-200"
            >
              <img :src="ph.photo_url" alt="" class="h-full w-full object-cover">
              <button
                type="button"
                class="absolute inset-0 flex items-center justify-center bg-black/50 text-xs text-white opacity-0 transition group-hover:opacity-100"
                @click="deleteTreatmentPhoto(ph.photo_id)"
              >
                Delete
              </button>
            </div>
          </div>
          <p v-else class="text-sm text-slate-400">No photos yet.</p>
        </div>

        <p v-if="formError" class="text-sm text-red-600">{{ formError }}</p>

        <div class="flex flex-wrap gap-2">
          <UButton type="submit" class="bg-[#0097A7]" :loading="saving">
            {{ creating ? 'Create treatment' : 'Save changes' }}
          </UButton>
          <UButton type="button" color="neutral" variant="outline" @click="backToList">
            Cancel
          </UButton>
        </div>
      </form>
    </template>
  </div>
</template>
