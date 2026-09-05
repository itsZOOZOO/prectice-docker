<script setup lang="ts">
definePageMeta({ layout: 'desk', middleware: 'admin' })

type WhatsappForm = {
  clinic_name: string
  doctor_name: string
  tagline: string
  qualification: string
  timing: string
  website: string
  email: string
  phone: string
  address: string
}

type PrintForm = {
  date_x: number
  date_y: number
  content_x: number
  tagline: string
}

type LetterheadData = {
  clinic_id: number
  whatsapp: WhatsappForm
  print: PrintForm
  logo_path: string | null
  logo_url: string | null
}

const route = useRoute()
const clinicId = computed(() => Number(route.params.id))
const { api, apiBlob } = useApi()
const toast = useToast()

const tab = ref<'whatsapp' | 'print'>('whatsapp')
const loading = ref(true)
const saving = ref(false)
const previewing = ref(false)
const clinicName = ref('')
const logoUrl = ref<string | null>(null)
const logoPath = ref<string | null>(null)
const removeBackground = ref(false)
const pendingBgFile = ref<File | null>(null)
const pendingBgPreview = ref<string | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)

const wa = reactive<WhatsappForm>({
  clinic_name: '',
  doctor_name: '',
  tagline: '',
  qualification: '',
  timing: '',
  website: '',
  email: '',
  phone: '',
  address: ''
})

const printForm = reactive<PrintForm>({
  date_x: 175,
  date_y: 38,
  content_x: 30,
  tagline: 'Your Smile Matters :)'
})

const bgDisplayUrl = computed(() => {
  if (removeBackground.value) return null
  return pendingBgPreview.value || logoUrl.value
})

async function load() {
  if (!Number.isFinite(clinicId.value) || clinicId.value <= 0) return
  loading.value = true
  try {
    const [clinic, data] = await Promise.all([
      api<{ clinic_name: string }>(`/admin/clinics/${clinicId.value}`),
      api<LetterheadData>(`/admin/clinics/${clinicId.value}/letterhead`)
    ])
    clinicName.value = clinic.clinic_name
    Object.assign(wa, data.whatsapp)
    Object.assign(printForm, data.print)
    logoPath.value = data.logo_path
    logoUrl.value = data.logo_url
    removeBackground.value = false
    pendingBgFile.value = null
    if (pendingBgPreview.value) {
      URL.revokeObjectURL(pendingBgPreview.value)
      pendingBgPreview.value = null
    }
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to load', color: 'error' })
  } finally {
    loading.value = false
  }
}

function onPickBg(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (file.size > 5 * 1024 * 1024) {
    toast.add({ title: 'Background must be under 5MB', color: 'error' })
    input.value = ''
    return
  }
  pendingBgFile.value = file
  removeBackground.value = false
  if (pendingBgPreview.value) URL.revokeObjectURL(pendingBgPreview.value)
  pendingBgPreview.value = URL.createObjectURL(file)
}

function clearBg() {
  if (logoPath.value || pendingBgFile.value) {
    if (!window.confirm('Remove letterhead background? Save to apply. This cannot be undone after save.')) {
      return
    }
  }
  removeBackground.value = true
  pendingBgFile.value = null
  if (pendingBgPreview.value) {
    URL.revokeObjectURL(pendingBgPreview.value)
    pendingBgPreview.value = null
  }
  if (fileInput.value) fileInput.value.value = ''
}

async function preview() {
  if (previewing.value) return
  previewing.value = true
  try {
    const fd = new FormData()
    fd.append('template_type', tab.value)
    fd.append(
      'payload',
      JSON.stringify({
        whatsapp: { ...wa },
        print: { ...printForm },
        remove_background: removeBackground.value && !pendingBgFile.value
      })
    )
    if (tab.value === 'whatsapp' && pendingBgFile.value) {
      fd.append('background', pendingBgFile.value)
    }
    const blob = await apiBlob(`/admin/clinics/${clinicId.value}/letterhead/preview`, {
      method: 'POST',
      body: fd
    })
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank', 'noopener,noreferrer')
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Preview failed', color: 'error' })
  } finally {
    previewing.value = false
  }
}

async function save() {
  if (saving.value) return
  saving.value = true
  try {
    if (pendingBgFile.value) {
      const fd = new FormData()
      fd.append('file', pendingBgFile.value)
      const uploaded = await api<{ logo_path: string, logo_url: string }>(
        `/admin/clinics/${clinicId.value}/letterhead/background`,
        { method: 'POST', body: fd }
      )
      logoPath.value = uploaded.logo_path
      logoUrl.value = uploaded.logo_url
      pendingBgFile.value = null
      if (pendingBgPreview.value) {
        URL.revokeObjectURL(pendingBgPreview.value)
        pendingBgPreview.value = null
      }
      removeBackground.value = false
    } else if (removeBackground.value && logoPath.value) {
      await api(`/admin/clinics/${clinicId.value}/letterhead/background`, { method: 'DELETE' })
      logoPath.value = null
      logoUrl.value = null
      removeBackground.value = false
    }

    await api(`/admin/clinics/${clinicId.value}/letterhead`, {
      method: 'PUT',
      body: {
        whatsapp: { ...wa },
        print: { ...printForm },
        remove_background: false
      }
    })
    toast.add({ title: 'Letterhead saved', color: 'success' })
    await load()
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Save failed', color: 'error' })
  } finally {
    saving.value = false
  }
}

onMounted(load)
onBeforeUnmount(() => {
  if (pendingBgPreview.value) URL.revokeObjectURL(pendingBgPreview.value)
})
</script>

<template>
  <div class="mx-auto flex h-full max-w-3xl flex-col gap-4 overflow-y-auto p-4 md:p-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <NuxtLink
          :to="`/admin/clinics/${clinicId}`"
          class="text-xs font-semibold text-[#0097A7] hover:underline"
        >
          ← Back to clinic
        </NuxtLink>
        <h2 class="mt-1 text-lg font-semibold text-[#1C2B35]">
          Letterhead
          <span v-if="clinicName" class="font-normal text-slate-500">· {{ clinicName }}</span>
        </h2>
        <p class="text-xs text-slate-500">WhatsApp digital PDF + print layout for pre-printed paper.</p>
      </div>
      <div class="flex gap-2">
        <UButton color="neutral" variant="outline" :loading="previewing" :disabled="loading" @click="preview">
          Preview
        </UButton>
        <UButton class="bg-[#0097A7]" :loading="saving" :disabled="loading" @click="save">
          Save
        </UButton>
      </div>
    </div>

    <div class="flex gap-1 rounded-lg bg-slate-100 p-1">
      <button
        type="button"
        class="flex-1 rounded-md px-3 py-2 text-sm font-semibold transition"
        :class="tab === 'whatsapp' ? 'bg-white text-[#0097A7] shadow-sm' : 'text-slate-600'"
        @click="tab = 'whatsapp'"
      >
        WhatsApp
      </button>
      <button
        type="button"
        class="flex-1 rounded-md px-3 py-2 text-sm font-semibold transition"
        :class="tab === 'print' ? 'bg-white text-[#0097A7] shadow-sm' : 'text-slate-600'"
        @click="tab = 'print'"
      >
        Print
      </button>
    </div>

    <div v-if="loading" class="py-12 text-center text-sm text-slate-400">Loading…</div>

    <template v-else>
      <section v-show="tab === 'whatsapp'" class="space-y-4 rounded-xl border border-slate-200 bg-white p-4">
        <div>
          <p class="mb-2 text-sm font-semibold text-[#1C2B35]">Background image</p>
          <p class="mb-3 text-xs text-slate-500">Full-page JPG/PNG/WebP, max 5MB. Shown behind WhatsApp PDF text.</p>
          <div class="flex flex-wrap items-start gap-4">
            <div
              class="flex h-40 w-28 items-center justify-center overflow-hidden rounded-lg border border-dashed border-slate-200 bg-slate-50"
            >
              <img
                v-if="bgDisplayUrl"
                :src="bgDisplayUrl"
                alt="Letterhead background"
                class="h-full w-full object-cover"
              >
              <span v-else class="px-2 text-center text-[11px] text-slate-400">No background</span>
            </div>
            <div class="flex flex-col gap-2">
              <input
                ref="fileInput"
                type="file"
                accept="image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp"
                class="text-xs"
                @change="onPickBg"
              >
              <UButton
                v-if="bgDisplayUrl || logoPath"
                color="neutral"
                variant="ghost"
                size="sm"
                class="self-start"
                @click="clearBg"
              >
                Remove background
              </UButton>
            </div>
          </div>
        </div>

        <div class="grid gap-3 sm:grid-cols-2">
          <UFormField label="Clinic name">
            <UInput v-model="wa.clinic_name" class="w-full" />
          </UFormField>
          <UFormField label="Doctor name">
            <UInput v-model="wa.doctor_name" class="w-full" />
          </UFormField>
          <UFormField label="Tagline">
            <UInput v-model="wa.tagline" class="w-full" />
          </UFormField>
          <UFormField label="Qualification">
            <UInput v-model="wa.qualification" class="w-full" />
          </UFormField>
          <UFormField label="Timing" class="sm:col-span-2">
            <UInput v-model="wa.timing" class="w-full" />
          </UFormField>
          <UFormField label="Website">
            <UInput v-model="wa.website" class="w-full" />
          </UFormField>
          <UFormField label="Email">
            <UInput v-model="wa.email" class="w-full" />
          </UFormField>
          <UFormField label="Phone">
            <UInput v-model="wa.phone" class="w-full" />
          </UFormField>
          <UFormField label="Address" class="sm:col-span-2">
            <UInput v-model="wa.address" class="w-full" />
          </UFormField>
        </div>
      </section>

      <section v-show="tab === 'print'" class="space-y-4 rounded-xl border border-slate-200 bg-white p-4">
        <p class="text-xs text-slate-500">
          For pre-printed letterhead paper — no background image. Adjust where date and body text sit.
        </p>
        <div class="grid gap-3 sm:grid-cols-3">
          <UFormField label="Date X (mm)">
            <UInput v-model.number="printForm.date_x" type="number" step="0.5" class="w-full" />
          </UFormField>
          <UFormField label="Date Y (mm)">
            <UInput v-model.number="printForm.date_y" type="number" step="0.5" class="w-full" />
          </UFormField>
          <UFormField label="Content X (mm)">
            <UInput v-model.number="printForm.content_x" type="number" step="0.5" class="w-full" />
          </UFormField>
          <UFormField label="Closing tagline" class="sm:col-span-3">
            <UInput v-model="printForm.tagline" class="w-full" />
          </UFormField>
        </div>
      </section>
    </template>
  </div>
</template>
