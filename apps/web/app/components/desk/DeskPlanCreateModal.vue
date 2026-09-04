<script setup lang="ts">
import { compressImage } from '~/utils/compressImage'

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
  showMore: boolean
  photos: PendingPhoto[]
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

const isOpen = computed({
  get: () => props.open,
  set: (v: boolean) => emit('update:open', v)
})

const isEdit = computed(() => props.planId != null && props.planId > 0)
const catalog = ref<CatalogItem[]>([])
const title = ref('')
const rows = ref<SubPlanRow[]>([])
const saving = ref(false)
const loading = ref(false)
const processingPhoto = ref(false)
const fileInputs = ref<Record<string, HTMLInputElement | null>>({})

function emptyRow(treatmentId: number | null = null): SubPlanRow {
  return {
    key: crypto.randomUUID(),
    treatment_id: treatmentId,
    type: 'Definitive',
    qty: 1,
    tooth_fdi: '',
    location_text: '',
    notes: '',
    showMore: false,
    photos: []
  }
}

function revokeRows(list: SubPlanRow[]) {
  for (const row of list) {
    for (const p of row.photos) {
      if (p.preview && !p.existingKey) URL.revokeObjectURL(p.preview)
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
    rows.value = plan.sub_plans.map(sp => ({
      key: crypto.randomUUID(),
      subPlanId: sp.sub_plan_id,
      treatment_id: sp.treatment_id,
      type: (sp.type === 'Tentative' ? 'Tentative' : 'Definitive') as 'Definitive' | 'Tentative',
      qty: sp.qty || 1,
      tooth_fdi: sp.tooth_fdi || '',
      location_text: sp.location_text || '',
      notes: sp.notes || '',
      showMore: !!(sp.tooth_fdi || sp.location_text || sp.notes),
      photos: (sp.photos || []).map(p => ({
        preview: p.url,
        existingKey: p.key
      }))
    }))
    if (!rows.value.length) rows.value = [emptyRow(catalog.value[0]?.treatment_id ?? null)]
  } finally {
    loading.value = false
  }
}

watch(isOpen, async (open) => {
  if (!open) return
  loading.value = true
  try {
    if (!catalog.value.length) await loadCatalog()
    if (isEdit.value) {
      await loadPlan()
    } else {
      revokeRows(rows.value)
      title.value = ''
      rows.value = [emptyRow(catalog.value[0]?.treatment_id ?? null)]
    }
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to load', color: 'error' })
  } finally {
    loading.value = false
  }
})

function addRow() {
  rows.value.push(emptyRow(catalog.value[0]?.treatment_id ?? null))
}

function removeRow(idx: number) {
  const [removed] = rows.value.splice(idx, 1)
  if (removed) revokeRows([removed])
  if (!rows.value.length) rows.value = [emptyRow(catalog.value[0]?.treatment_id ?? null)]
}

function addFromChip(t: CatalogItem) {
  rows.value.push(emptyRow(t.treatment_id))
}

async function onPickPhotos(row: SubPlanRow, ev: Event) {
  const input = ev.target as HTMLInputElement
  const picked = Array.from(input.files || [])
  input.value = ''
  if (!picked.length) return
  const room = 10 - row.photos.length
  if (room <= 0) {
    toast.add({ title: 'Max 10 photos per treatment', color: 'warning' })
    return
  }
  processingPhoto.value = true
  try {
    for (const file of picked.slice(0, room)) {
      let processed = file
      try {
        processed = await compressImage(file)
      } catch {
        processed = file
      }
      row.photos.push({
        file: processed,
        preview: URL.createObjectURL(processed)
      })
    }
  } finally {
    processingPhoto.value = false
  }
}

function removePhoto(row: SubPlanRow, idx: number) {
  const [p] = row.photos.splice(idx, 1)
  if (p?.preview && !p.existingKey) URL.revokeObjectURL(p.preview)
}

async function save() {
  if (!props.clientId) return
  const valid = rows.value.filter(r => r.treatment_id)
  if (!valid.length) {
    toast.add({ title: 'Add at least one treatment', color: 'warning' })
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
    :title="isEdit ? 'Edit treatment plan' : 'New treatment plan'"
    :ui="{ content: 'sm:max-w-xl' }"
  >
    <template #body>
      <div v-if="loading" class="py-8 text-center text-sm text-slate-500">Loading…</div>
      <form v-else class="space-y-3" @submit.prevent="save">
        <UFormField label="Title">
          <UInput v-model="title" class="w-full" placeholder="Optional plan title" autofocus />
        </UFormField>

        <div v-if="catalog.length" class="flex flex-wrap gap-1.5">
          <button
            v-for="t in catalog"
            :key="t.treatment_id"
            type="button"
            class="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] font-medium text-slate-700 hover:border-[#0097A7] hover:bg-[#e0f7fa] hover:text-[#0097A7]"
            @click="addFromChip(t)"
          >
            + {{ t.name }}
          </button>
        </div>
        <p v-else class="text-sm text-slate-500">No treatments in catalog. Import treatments first.</p>

        <div
          v-for="(row, idx) in rows"
          :key="row.key"
          class="space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-3"
        >
          <div class="flex items-center justify-between gap-2">
            <p class="text-xs font-medium text-slate-500">Treatment {{ idx + 1 }}</p>
            <button type="button" class="text-xs text-red-500 hover:underline" @click="removeRow(idx)">
              Remove
            </button>
          </div>
          <UFormField label="Treatment" required>
            <USelect
              v-model="row.treatment_id"
              :items="catalogItems"
              value-key="value"
              label-key="label"
              class="w-full"
            />
          </UFormField>
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
            <div class="col-span-2 flex items-end">
              <button
                type="button"
                class="mb-1 text-xs text-[#0097A7] hover:underline"
                @click="row.showMore = !row.showMore"
              >
                {{ row.showMore ? 'Hide details' : 'More (tooth / notes)' }}
              </button>
            </div>
          </div>
          <div v-if="row.showMore" class="grid grid-cols-2 gap-2">
            <UFormField label="Tooth">
              <UInput v-model="row.tooth_fdi" class="w-full" placeholder="FDI" />
            </UFormField>
            <UFormField label="Location">
              <UInput v-model="row.location_text" class="w-full" />
            </UFormField>
            <UFormField label="Notes" class="col-span-2">
              <UInput v-model="row.notes" class="w-full" />
            </UFormField>
          </div>
          <div>
            <div class="mb-1 flex items-center justify-between">
              <p class="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Photos</p>
              <button
                type="button"
                class="text-xs text-[#0097A7] hover:underline disabled:opacity-50"
                :disabled="processingPhoto || row.photos.length >= 10"
                @click="fileInputs[row.key]?.click()"
              >
                Add photos
              </button>
              <input
                :ref="(el) => { fileInputs[row.key] = el as HTMLInputElement | null }"
                type="file"
                accept="image/*"
                multiple
                class="hidden"
                @change="onPickPhotos(row, $event)"
              >
            </div>
            <div v-if="row.photos.length" class="flex flex-wrap gap-2">
              <div
                v-for="(p, pidx) in row.photos"
                :key="`${row.key}-p-${pidx}`"
                class="relative overflow-hidden rounded-lg border border-slate-200"
              >
                <img v-if="p.preview" :src="p.preview" alt="" class="h-14 w-14 object-cover">
                <button
                  type="button"
                  class="absolute right-0.5 top-0.5 rounded bg-black/60 px-1 text-[10px] text-white"
                  @click="removePhoto(row, pidx)"
                >
                  ×
                </button>
              </div>
            </div>
          </div>
        </div>

        <UButton color="neutral" variant="outline" size="sm" type="button" @click="addRow">
          Add treatment
        </UButton>

        <div class="flex justify-end gap-2 pt-1">
          <UButton color="neutral" variant="ghost" type="button" @click="isOpen = false">Cancel</UButton>
          <UButton type="submit" class="bg-[#0097A7]" :loading="saving">
            {{ isEdit ? 'Save changes' : 'Create plan' }}
          </UButton>
        </div>
      </form>
    </template>
  </UModal>
</template>
