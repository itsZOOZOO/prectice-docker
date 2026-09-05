<script setup lang="ts">
import {
  MAX_TPLAN_PHOTOS_PER_ROW,
  TPLAN_PHOTO_ACCEPT,
  createTreatmentPlanPhotoPreview,
  isImageFile,
  resizeTreatmentPlanImage,
  revokePhotoPreview
} from '~/utils/treatmentPlanImage'
import { fetchUrlAsFile } from '~/utils/cropImageCanvas'

type CatalogItem = { treatment_id: number, name: string }
type ExistingPhoto = { photo_id?: number, key: string, url: string | null }
type PendingPhoto = { file?: File, preview: string | null, existingKey?: string }

type SubPlanRow = {
  key: string
  subPlanId?: number
  treatment_id: number | null
  type: 'Definitive' | 'Tentative'
  qty: number
  tooth_fdi: string
  location_text: string
  notes: string
  showDetails: boolean
  photos: PendingPhoto[]
}

type CropTarget = {
  rowKey: string
  photoIndex: number
  file: File | null
  previewUrl: string | null
  fileName: string
}

const props = defineProps<{
  open: boolean
  clientId: number | null
  planId?: number | null
}>()

const emit = defineEmits<{
  'update:open': [boolean]
  saved: []
}>()

const { api } = useApi()
const toast = useToast()

const cropEdit = ref<CropTarget | null>(null)
const dragOverKey = ref<string | null>(null)

const isOpen = computed({
  get: () => props.open,
  set: (v: boolean) => {
    if (!v && cropEdit.value) return
    emit('update:open', v)
  }
})

const isEdit = computed(() => props.planId != null && props.planId > 0)
const catalog = ref<CatalogItem[]>([])
const title = ref('')
const rows = ref<SubPlanRow[]>([])
const saving = ref(false)
const loading = ref(false)
const processingPhoto = ref(false)
const fileInputs = ref<Record<string, HTMLInputElement | null>>({})

function rowHasNonDefaultDetails(row: Pick<SubPlanRow, 'type' | 'qty' | 'tooth_fdi' | 'location_text' | 'notes'>) {
  return (
    row.type === 'Tentative'
    || (row.qty || 1) !== 1
    || !!row.tooth_fdi.trim()
    || !!row.location_text.trim()
    || !!row.notes.trim()
  )
}

function emptyRow(): SubPlanRow {
  return {
    key: crypto.randomUUID(),
    treatment_id: null,
    type: 'Definitive',
    qty: 1,
    tooth_fdi: '',
    location_text: '',
    notes: '',
    showDetails: false,
    photos: []
  }
}

function revokeRows(list: SubPlanRow[]) {
  for (const row of list) {
    for (const p of row.photos) {
      if (p.preview && !p.existingKey) revokePhotoPreview(p.preview)
    }
  }
}

async function loadCatalog() {
  catalog.value = await api<CatalogItem[]>('/treatments/catalog')
}

async function loadPlan() {
  if (!props.planId) return
  loading.value = true
  try {
    const plan = await api<{
      title: string | null
      sub_plans: {
        sub_plan_id: number
        treatment_id: number
        type: string
        qty: number
        tooth_fdi: string | null
        location_text: string | null
        notes: string | null
        photos: ExistingPhoto[]
      }[]
    }>(`/treatment-plans/${props.planId}`)
    title.value = plan.title || ''
    revokeRows(rows.value)
    rows.value = plan.sub_plans.map((sp) => {
      const row: SubPlanRow = {
        key: crypto.randomUUID(),
        subPlanId: sp.sub_plan_id,
        treatment_id: sp.treatment_id,
        type: (sp.type === 'Tentative' ? 'Tentative' : 'Definitive') as 'Definitive' | 'Tentative',
        qty: sp.qty || 1,
        tooth_fdi: sp.tooth_fdi || '',
        location_text: sp.location_text || '',
        notes: sp.notes || '',
        showDetails: false,
        photos: (sp.photos || []).map(p => ({
          preview: p.url,
          existingKey: p.key
        }))
      }
      row.showDetails = rowHasNonDefaultDetails(row)
      return row
    })
    if (!rows.value.length) rows.value = [emptyRow()]
  } finally {
    loading.value = false
  }
}

watch(isOpen, async (open) => {
  if (!open) {
    cropEdit.value = null
    dragOverKey.value = null
    return
  }
  loading.value = true
  try {
    if (!catalog.value.length) await loadCatalog()
    if (isEdit.value) {
      await loadPlan()
    } else {
      revokeRows(rows.value)
      title.value = ''
      rows.value = [emptyRow()]
    }
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to load', color: 'error' })
  } finally {
    loading.value = false
  }
})

function addRow() {
  rows.value.push(emptyRow())
}

function removeRow(idx: number) {
  const [removed] = rows.value.splice(idx, 1)
  if (removed) revokeRows([removed])
  if (!rows.value.length) rows.value = [emptyRow()]
}

async function addPhotoFiles(row: SubPlanRow, picked: File[]) {
  if (!picked.length) return
  const room = MAX_TPLAN_PHOTOS_PER_ROW - row.photos.length
  if (room <= 0) {
    toast.add({ title: `Max ${MAX_TPLAN_PHOTOS_PER_ROW} photos per treatment`, color: 'warning' })
    return
  }
  processingPhoto.value = true
  try {
    const images = picked.filter(isImageFile)
    if (images.length < picked.length) {
      toast.add({ title: 'Some files skipped (not images)', color: 'warning' })
    }
    for (const file of images.slice(0, room)) {
      try {
        const resized = await resizeTreatmentPlanImage(file)
        const preview = await createTreatmentPlanPhotoPreview(resized)
        row.photos.push({ file: resized, preview })
      } catch {
        row.photos.push({
          file,
          preview: URL.createObjectURL(file)
        })
      }
    }
  } finally {
    processingPhoto.value = false
  }
}

async function onPickPhotos(row: SubPlanRow, ev: Event) {
  const input = ev.target as HTMLInputElement
  const picked = Array.from(input.files || [])
  input.value = ''
  await addPhotoFiles(row, picked)
}

function onPhotoDragOver(row: SubPlanRow, ev: DragEvent) {
  ev.preventDefault()
  if (processingPhoto.value || !!cropEdit.value || row.photos.length >= MAX_TPLAN_PHOTOS_PER_ROW) return
  dragOverKey.value = row.key
}

function onPhotoDragLeave(row: SubPlanRow) {
  if (dragOverKey.value === row.key) dragOverKey.value = null
}

async function onPhotoDrop(row: SubPlanRow, ev: DragEvent) {
  ev.preventDefault()
  dragOverKey.value = null
  if (processingPhoto.value || !!cropEdit.value || row.photos.length >= MAX_TPLAN_PHOTOS_PER_ROW) return
  const picked = Array.from(ev.dataTransfer?.files || [])
  await addPhotoFiles(row, picked)
}

function removePhoto(row: SubPlanRow, idx: number) {
  const [p] = row.photos.splice(idx, 1)
  if (p?.preview && !p.existingKey) revokePhotoPreview(p.preview)
}

async function openCrop(row: SubPlanRow, photoIndex: number) {
  const photo = row.photos[photoIndex]
  if (!photo || processingPhoto.value || cropEdit.value) return

  processingPhoto.value = true
  try {
    let file = photo.file ?? null
    if (!file && photo.preview) {
      file = await fetchUrlAsFile(photo.preview, photo.existingKey?.split('/').pop() || 'photo.jpg')
    }
    if (!file && !photo.preview) {
      toast.add({ title: 'Photo unavailable for editing', color: 'error' })
      return
    }
    cropEdit.value = {
      rowKey: row.key,
      photoIndex,
      file,
      previewUrl: photo.preview,
      fileName: file?.name || 'photo.jpg'
    }
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Could not open photo editor', color: 'error' })
  } finally {
    processingPhoto.value = false
  }
}

async function onCropComplete(result: File | null) {
  const target = cropEdit.value
  cropEdit.value = null
  if (!target || !result) return

  processingPhoto.value = true
  try {
    const resized = await resizeTreatmentPlanImage(result)
    const preview = await createTreatmentPlanPhotoPreview(resized)
    const row = rows.value.find(r => r.key === target.rowKey)
    if (!row) return
    const existing = row.photos[target.photoIndex]
    if (!existing) return
    if (existing.preview && !existing.existingKey) revokePhotoPreview(existing.preview)
    row.photos[target.photoIndex] = {
      file: resized,
      preview,
      existingKey: undefined
    }
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to process cropped photo', color: 'error' })
  } finally {
    processingPhoto.value = false
  }
}

async function save() {
  if (!props.clientId) return
  const valid = rows.value.filter(r => r.treatment_id)
  if (!valid.length) {
    toast.add({ title: 'Select a treatment', color: 'warning' })
    return
  }
  saving.value = true
  try {
    const planPayload = {
      title: title.value.trim() || null,
      sub_plans: valid.map(r => ({
        id: r.subPlanId,
        treatment_id: r.treatment_id,
        type: r.type,
        qty: r.qty || 1,
        tooth_fdi: r.tooth_fdi.trim() || null,
        location_text: r.location_text.trim() || null,
        notes: r.notes.trim() || null,
        keep_photo_keys: r.photos.filter(p => p.existingKey).map(p => p.existingKey as string)
      }))
    }
    const fd = new FormData()
    fd.append('plan', JSON.stringify(planPayload))
    valid.forEach((r, rowIdx) => {
      for (const p of r.photos) {
        if (p.file && !p.existingKey) {
          fd.append('files', p.file)
          fd.append('file_rows', String(rowIdx))
        }
      }
    })
    if (isEdit.value && props.planId) {
      await api(`/treatment-plans/${props.planId}`, { method: 'PUT', body: fd })
      toast.add({ title: 'Plan updated', color: 'success' })
    } else {
      await api(`/clients/${props.clientId}/treatment-plans`, { method: 'POST', body: fd })
      toast.add({ title: 'Plan created', color: 'success' })
    }
    isOpen.value = false
    emit('saved')
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
  } finally {
    saving.value = false
  }
}

const catalogItems = computed(() =>
  catalog.value.map(t => ({ label: t.name, value: t.treatment_id }))
)
</script>

<template>
  <UModal
    v-model:open="isOpen"
    :title="cropEdit ? 'Edit photo' : (isEdit ? 'Edit treatment plan' : 'New treatment plan')"
    :dismissible="!cropEdit"
    :close="!cropEdit"
    :ui="{ content: 'sm:max-w-xl' }"
  >
    <template #body>
      <DeskPlanPhotoCropper
        v-if="cropEdit"
        :file="cropEdit.file"
        :preview-url="cropEdit.previewUrl"
        :file-name="cropEdit.fileName"
        @cancel="cropEdit = null"
        @complete="onCropComplete"
      />
      <div v-else-if="loading" class="py-8 text-center text-sm text-slate-500">Loading…</div>
      <form v-else class="space-y-4" @submit.prevent="save">
        <UFormField label="Title">
          <UInput v-model="title" class="w-full" placeholder="Optional plan title" autofocus />
        </UFormField>

        <p v-if="!catalog.length" class="text-sm text-slate-500">
          No treatments in catalog. Import treatments first.
        </p>

        <div
          v-for="(row, idx) in rows"
          :key="row.key"
          class="space-y-3 rounded-2xl border border-slate-200 bg-white p-3 shadow-sm"
        >
          <div class="flex items-center justify-between gap-2">
            <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {{ rows.length > 1 ? `Treatment ${idx + 1}` : 'Treatment' }}
            </p>
            <button
              v-if="rows.length > 1"
              type="button"
              class="text-xs text-red-500 hover:underline"
              @click="removeRow(idx)"
            >
              Remove
            </button>
          </div>

          <UFormField label="Select treatment" required>
            <USelect
              v-model="row.treatment_id"
              :items="catalogItems"
              value-key="value"
              label-key="label"
              placeholder="Choose treatment…"
              class="w-full"
              :disabled="!catalog.length"
            />
          </UFormField>

          <!-- Primary photo zone -->
          <div>
            <p class="mb-1.5 text-sm font-medium text-slate-700">Photos</p>
            <button
              type="button"
              class="flex w-full flex-col items-center justify-center gap-1.5 rounded-2xl border-2 border-dashed px-4 py-6 text-center transition-colors disabled:opacity-50"
              :class="dragOverKey === row.key
                ? 'border-[#0097A7] bg-[#e0f7fa]'
                : 'border-slate-300 bg-slate-50 hover:border-[#0097A7] hover:bg-[#f0fafb]'"
              :disabled="processingPhoto || !!cropEdit || row.photos.length >= MAX_TPLAN_PHOTOS_PER_ROW"
              @click="fileInputs[row.key]?.click()"
              @dragover="onPhotoDragOver(row, $event)"
              @dragleave="onPhotoDragLeave(row)"
              @drop="onPhotoDrop(row, $event)"
            >
              <UIcon name="i-lucide-image-plus" class="h-7 w-7 text-[#0097A7]" />
              <span class="text-sm font-semibold text-[#1C2B35]">
                {{ processingPhoto ? 'Processing…' : 'Add photos' }}
              </span>
              <span class="text-xs text-slate-500">
                Tap or drop images here · optional · up to {{ MAX_TPLAN_PHOTOS_PER_ROW }}
              </span>
            </button>
            <input
              :ref="(el) => { fileInputs[row.key] = el as HTMLInputElement | null }"
              type="file"
              :accept="TPLAN_PHOTO_ACCEPT"
              multiple
              class="hidden"
              @change="onPickPhotos(row, $event)"
            >

            <div v-if="row.photos.length" class="mt-2 flex flex-wrap gap-2">
              <div
                v-for="(p, pidx) in row.photos"
                :key="`${row.key}-p-${pidx}`"
                class="relative overflow-hidden rounded-xl border border-slate-200"
              >
                <img v-if="p.preview" :src="p.preview" alt="" class="h-20 w-20 object-cover">
                <div class="absolute inset-x-0 bottom-0 flex gap-px bg-black/55">
                  <button
                    type="button"
                    class="flex flex-1 items-center justify-center py-1 text-white disabled:opacity-40"
                    title="Crop / rotate"
                    :disabled="processingPhoto || !!cropEdit"
                    @click="openCrop(row, pidx)"
                  >
                    <UIcon name="i-lucide-crop" class="h-3.5 w-3.5" />
                  </button>
                  <button
                    type="button"
                    class="flex flex-1 items-center justify-center py-1 text-white"
                    title="Remove"
                    @click="removePhoto(row, pidx)"
                  >
                    <UIcon name="i-lucide-x" class="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Optional details on demand -->
          <div class="border-t border-slate-100 pt-2">
            <button
              type="button"
              class="flex w-full items-center justify-between text-left text-xs font-medium text-slate-600 hover:text-[#0097A7]"
              @click="row.showDetails = !row.showDetails"
            >
              <span>{{ row.showDetails ? 'Hide details' : 'Details (type, qty, tooth, notes)' }}</span>
              <UIcon
                :name="row.showDetails ? 'i-lucide-chevron-up' : 'i-lucide-chevron-down'"
                class="h-4 w-4"
              />
            </button>
            <div v-if="row.showDetails" class="mt-3 space-y-3">
              <div class="flex gap-2">
                <button
                  type="button"
                  class="rounded-lg px-3 py-1.5 text-xs font-semibold"
                  :class="row.type === 'Definitive' ? 'bg-[#0097A7] text-white' : 'bg-white text-slate-600 ring-1 ring-slate-200'"
                  @click="row.type = 'Definitive'"
                >
                  Confirmed
                </button>
                <button
                  type="button"
                  class="rounded-lg px-3 py-1.5 text-xs font-semibold"
                  :class="row.type === 'Tentative' ? 'bg-amber-500 text-white' : 'bg-white text-slate-600 ring-1 ring-slate-200'"
                  @click="row.type = 'Tentative'"
                >
                  Exploratory
                </button>
              </div>
              <div class="grid grid-cols-3 gap-2">
                <UFormField label="Qty">
                  <UInput v-model.number="row.qty" type="number" min="1" class="w-full" />
                </UFormField>
                <UFormField label="Tooth" class="col-span-2">
                  <UInput v-model="row.tooth_fdi" class="w-full" placeholder="FDI" />
                </UFormField>
              </div>
              <UFormField label="Location">
                <UInput v-model="row.location_text" class="w-full" />
              </UFormField>
              <UFormField label="Notes">
                <UInput v-model="row.notes" class="w-full" />
              </UFormField>
            </div>
          </div>
        </div>

        <button
          type="button"
          class="text-sm font-medium text-[#0097A7] hover:underline"
          @click="addRow"
        >
          + Add another treatment
        </button>

        <div class="flex justify-end gap-2 pt-1">
          <UButton color="neutral" variant="ghost" type="button" :disabled="!!cropEdit" @click="isOpen = false">
            Cancel
          </UButton>
          <UButton type="submit" class="bg-[#0097A7]" :loading="saving" :disabled="!!cropEdit || !catalog.length">
            {{ isEdit ? 'Save changes' : 'Create plan' }}
          </UButton>
        </div>
      </form>
    </template>
  </UModal>
</template>
