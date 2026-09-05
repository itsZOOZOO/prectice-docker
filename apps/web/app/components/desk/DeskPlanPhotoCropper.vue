<script setup lang="ts">
import { Cropper } from 'vue-advanced-cropper'
import 'vue-advanced-cropper/dist/style.css'
import { canvasToJpegFile } from '~/utils/cropImageCanvas'
import { loadImageDataUrlForCropper } from '~/utils/treatmentPlanImage'

type CropperExpose = {
  // Second arg is supported by vue-advanced-cropper; transitions default true.
  // While transitions are active, rotate() is a no-op — fine slider must disable them.
  rotate: (angle: number, options?: { transitions?: boolean }) => void
  flip: (horizontal?: boolean, vertical?: boolean) => void
  getResult: () => {
    canvas?: HTMLCanvasElement | null
    image?: { transforms?: { rotate?: number } }
  }
}

const props = defineProps<{
  file: File | null
  previewUrl?: string | null
  fileName?: string
}>()

const emit = defineEmits<{
  complete: [file: File | null]
  cancel: []
}>()

const cropperRef = ref<CropperExpose | null>(null)
const imageSrc = ref<string | null>(null)
const loading = ref(true)
const processing = ref(false)
const loadError = ref<string | null>(null)
const fineRotation = ref(0)
const lastFine = ref(0)
const flipH = ref(false)
const flipV = ref(false)

const FINE_MIN = -45
const FINE_MAX = 45

function getCropper(): CropperExpose | null {
  const raw = cropperRef.value as CropperExpose | { $?: CropperExpose } | null
  if (!raw) return null
  if (typeof (raw as CropperExpose).rotate === 'function') return raw as CropperExpose
  const nested = (raw as { $?: CropperExpose }).$
  if (nested && typeof nested.rotate === 'function') return nested
  return null
}

watch(
  () => [props.file, props.previewUrl] as const,
  async ([file, preview]) => {
    fineRotation.value = 0
    lastFine.value = 0
    flipH.value = false
    flipV.value = false
    loadError.value = null
    loading.value = true
    imageSrc.value = null

    try {
      if (preview && (preview.startsWith('blob:') || preview.startsWith('data:') || preview.startsWith('http'))) {
        if (file) {
          const dataUrl = await loadImageDataUrlForCropper(file)
          imageSrc.value = dataUrl || preview
        } else {
          imageSrc.value = preview
        }
      } else if (file) {
        const dataUrl = await loadImageDataUrlForCropper(file)
        if (!dataUrl) {
          loadError.value = 'Could not load this image for editing.'
          return
        }
        imageSrc.value = dataUrl
      } else {
        loadError.value = 'No image to edit.'
      }
    } catch {
      loadError.value = 'Could not load this image for editing.'
    } finally {
      loading.value = false
    }
  },
  { immediate: true }
)

/** Absolute image angle currently applied by the cropper (degrees). */
function currentAppliedRotation(): number {
  return getCropper()?.getResult()?.image?.transforms?.rotate ?? 0
}

/**
 * Apply absolute fine angle relative to last 90° snap.
 * Uses transitions:false so rapid slider events are not dropped.
 */
function setFineRotationAbsolute(next: number) {
  const cropper = getCropper()
  if (!cropper) return
  const clamped = Math.max(FINE_MIN, Math.min(FINE_MAX, Math.round(next)))
  // Strip current fine offset, then apply the new fine angle from the 90° base.
  const applied = currentAppliedRotation()
  const base = applied - lastFine.value
  const target = base + clamped
  const delta = target - applied
  if (delta !== 0) {
    cropper.rotate(delta, { transitions: false })
  }
  lastFine.value = clamped
  fineRotation.value = clamped
}

function rotateQuarter(dir: 1 | -1) {
  const cropper = getCropper()
  if (!cropper) return
  // Clear fine offset first so 90° lands on a clean multiple.
  if (fineRotation.value !== 0) {
    cropper.rotate(-fineRotation.value, { transitions: false })
    fineRotation.value = 0
    lastFine.value = 0
  }
  cropper.rotate(dir * 90, { transitions: false })
}

function onFineInput(val: number) {
  setFineRotationAbsolute(Number(val))
}

function toggleFlipH() {
  getCropper()?.flip(true, false)
  flipH.value = !flipH.value
}

function toggleFlipV() {
  getCropper()?.flip(false, true)
  flipV.value = !flipV.value
}

function resetTransforms() {
  const cropper = getCropper()
  if (!cropper) return
  const applied = currentAppliedRotation()
  if (applied !== 0) {
    cropper.rotate(-applied, { transitions: false })
  }
  if (flipH.value) cropper.flip(true, false)
  if (flipV.value) cropper.flip(false, true)
  fineRotation.value = 0
  lastFine.value = 0
  flipH.value = false
  flipV.value = false
}

async function applyEdits() {
  const cropper = getCropper()
  if (!cropper || !imageSrc.value) {
    loadError.value = 'Draw a crop area first.'
    return
  }
  processing.value = true
  loadError.value = null
  try {
    const result = cropper.getResult()
    const canvas = result.canvas
    if (!canvas) {
      loadError.value = 'Could not export edited image.'
      return
    }
    const name = props.fileName || props.file?.name || 'photo.jpg'
    const cropped = await canvasToJpegFile(canvas, name, 0.9)
    if (!cropped) {
      loadError.value = 'Could not export edited image.'
      return
    }
    emit('complete', cropped)
  } catch {
    loadError.value = 'Could not edit this image.'
  } finally {
    processing.value = false
  }
}

const hasTransforms = computed(
  () => fineRotation.value !== 0 || flipH.value || flipV.value
)

function onCancel() {
  emit('cancel')
}
</script>

<template>
  <!--
    Embedded inside UModal (not teleported). Teleporting sat outside Reka's
    DialogContent, so the modal layer swallowed clicks on controls / close.
  -->
  <div class="-m-4 flex min-h-[min(80dvh,640px)] flex-col sm:-m-6">
    <div class="relative shrink-0 bg-slate-900" style="height: min(42dvh, 320px)">
      <div
        v-if="loading"
        class="absolute inset-0 z-10 flex items-center justify-center bg-slate-900/80 text-sm text-white/90"
      >
        Loading image…
      </div>
      <div
        v-else-if="loadError && !imageSrc"
        class="flex h-full items-center justify-center px-4 text-center text-sm text-amber-200"
      >
        {{ loadError }}
      </div>
      <Cropper
        v-else-if="imageSrc"
        ref="cropperRef"
        class="h-full w-full"
        :src="imageSrc"
        :canvas="true"
        image-restriction="stencil"
      />
    </div>

    <div
      v-if="imageSrc && !loading"
      class="shrink-0 space-y-3 border-t border-slate-100 bg-white p-3"
    >
      <div class="flex flex-wrap items-center justify-center gap-2">
        <button
          type="button"
          class="flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-slate-50 text-slate-700"
          title="Rotate left 90°"
          @click="rotateQuarter(-1)"
        >
          <UIcon name="i-lucide-rotate-ccw" class="h-5 w-5" />
        </button>
        <button
          type="button"
          class="flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-slate-50 text-slate-700"
          title="Rotate right 90°"
          @click="rotateQuarter(1)"
        >
          <UIcon name="i-lucide-rotate-cw" class="h-5 w-5" />
        </button>
        <button
          type="button"
          class="flex h-10 w-10 items-center justify-center rounded-xl border text-slate-700"
          :class="flipH ? 'border-[#0097A7] bg-[#e0f7fa] text-[#00838f]' : 'border-slate-200 bg-slate-50'"
          title="Flip horizontal (mirror)"
          @click="toggleFlipH"
        >
          <UIcon name="i-lucide-flip-horizontal-2" class="h-5 w-5" />
        </button>
        <button
          type="button"
          class="flex h-10 w-10 items-center justify-center rounded-xl border text-slate-700"
          :class="flipV ? 'border-[#0097A7] bg-[#e0f7fa] text-[#00838f]' : 'border-slate-200 bg-slate-50'"
          title="Flip vertical"
          @click="toggleFlipV"
        >
          <UIcon name="i-lucide-flip-vertical-2" class="h-5 w-5" />
        </button>
        <button
          v-if="hasTransforms"
          type="button"
          class="rounded-xl border border-slate-200 px-3 py-2 text-xs font-medium text-slate-600"
          @click="resetTransforms"
        >
          Reset
        </button>
      </div>

      <div>
        <div class="mb-2 flex items-center justify-between gap-2">
          <label class="text-xs font-medium text-slate-600">Straighten</label>
          <span class="text-xs tabular-nums text-slate-500">
            {{ fineRotation > 0 ? '+' : '' }}{{ fineRotation }}°
          </span>
        </div>
        <input
          type="range"
          class="h-2 w-full cursor-pointer appearance-none rounded-full bg-slate-200 accent-[#0097A7]"
          :min="FINE_MIN"
          :max="FINE_MAX"
          step="1"
          :value="fineRotation"
          @input="onFineInput(Number(($event.target as HTMLInputElement).value))"
        >
        <div class="mt-1 flex justify-between text-[10px] text-slate-400">
          <span>{{ FINE_MIN }}°</span>
          <span>0°</span>
          <span>{{ FINE_MAX }}°</span>
        </div>
      </div>

      <p v-if="loadError" class="text-center text-xs text-red-600">{{ loadError }}</p>
      <p class="text-center text-xs text-slate-500">
        Drag corners to crop. Use rotate, flip, and straighten below.
      </p>
    </div>

    <div class="mt-auto flex shrink-0 gap-2 border-t border-slate-100 bg-white px-4 py-3">
      <button
        type="button"
        class="flex-1 rounded-xl border border-slate-200 py-2.5 text-sm font-medium text-slate-700"
        @click="onCancel"
      >
        Cancel
      </button>
      <button
        type="button"
        class="flex-1 rounded-xl bg-[#0097A7] py-2.5 text-sm font-semibold text-white disabled:opacity-60"
        :disabled="!imageSrc || loading || processing"
        @click="applyEdits"
      >
        {{ processing ? 'Processing…' : 'Apply' }}
      </button>
    </div>
  </div>
</template>
