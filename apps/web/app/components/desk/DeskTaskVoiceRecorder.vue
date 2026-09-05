<script setup lang="ts">
export type TaskVoiceBlob = {
  blob: Blob
  mimeType: string
  fileName: string
}

const props = withDefaults(defineProps<{
  modelValue?: TaskVoiceBlob | null
  disabled?: boolean
  compact?: boolean
}>(), {
  modelValue: null,
  disabled: false,
  compact: false
})

const emit = defineEmits<{
  'update:modelValue': [value: TaskVoiceBlob | null]
}>()

const recording = ref(false)
const previewUrl = ref<string | null>(null)
const error = ref<string | null>(null)
const rootEl = ref<HTMLElement | null>(null)

const mediaRecorderRef = shallowRef<MediaRecorder | null>(null)
const chunksRef = shallowRef<Blob[]>([])
const streamRef = shallowRef<MediaStream | null>(null)
let previewObjectUrl: string | null = null

function preferredMimeType(): string | undefined {
  if (typeof MediaRecorder === 'undefined') return undefined
  const candidates = [
    'audio/mp4',
    'audio/aac',
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/ogg'
  ]
  return candidates.find(type => MediaRecorder.isTypeSupported(type))
}

function extensionForMime(mime: string): string {
  if (mime.includes('mp4') || mime.includes('aac') || mime.includes('m4a')) return 'm4a'
  if (mime.includes('ogg')) return 'ogg'
  if (mime.includes('wav')) return 'wav'
  return 'webm'
}

function createRecorder(stream: MediaStream): MediaRecorder {
  const mimeType = preferredMimeType()
  try {
    return mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream)
  } catch {
    return new MediaRecorder(stream)
  }
}

function stopTracks() {
  streamRef.value?.getTracks().forEach(t => t.stop())
  streamRef.value = null
}

function clearPreviewUrl() {
  if (previewObjectUrl) {
    URL.revokeObjectURL(previewObjectUrl)
    previewObjectUrl = null
  }
  previewUrl.value = null
}

watch(
  () => props.modelValue,
  (value) => {
    clearPreviewUrl()
    if (!value) return
    previewObjectUrl = URL.createObjectURL(value.blob)
    previewUrl.value = previewObjectUrl
    requestAnimationFrame(() => {
      rootEl.value?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
    })
  },
  { immediate: true }
)

onUnmounted(() => {
  stopTracks()
  if (mediaRecorderRef.value?.state === 'recording') {
    try { mediaRecorderRef.value.stop() } catch { /* ignore */ }
  }
  clearPreviewUrl()
})

async function startRecording() {
  if (props.disabled || recording.value) return
  error.value = null
  if (typeof MediaRecorder === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
    error.value = 'Voice recording is not supported in this browser.'
    return
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    streamRef.value = stream
    const recorder = createRecorder(stream)
    chunksRef.value = []
    recorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) chunksRef.value.push(e.data)
    }
    recorder.onerror = () => {
      error.value = 'Recording failed.'
      recording.value = false
      stopTracks()
    }
    recorder.onstop = () => {
      const blobMime = recorder.mimeType || preferredMimeType() || 'audio/webm'
      const blob = new Blob(chunksRef.value, { type: blobMime })
      stopTracks()
      recording.value = false
      if (blob.size <= 0) {
        error.value = 'Recording was empty.'
        return
      }
      emit('update:modelValue', {
        blob,
        mimeType: blobMime,
        fileName: `task-voice-${Date.now()}.${extensionForMime(blobMime)}`
      })
    }
    mediaRecorderRef.value = recorder
    recorder.start()
    recording.value = true
  } catch {
    error.value = 'Microphone permission is required to record voice.'
    stopTracks()
    recording.value = false
  }
}

function stopRecording() {
  const recorder = mediaRecorderRef.value
  if (recorder && recorder.state === 'recording') {
    try { recorder.stop() } catch { /* ignore */ }
  }
}

function removeRecording() {
  if (recording.value) stopRecording()
  emit('update:modelValue', null)
  error.value = null
}
</script>

<template>
  <div ref="rootEl" :class="compact ? 'space-y-1.5' : 'space-y-2'">
    <p
      class="font-semibold uppercase tracking-wide text-slate-500"
      :class="compact ? 'text-[10px]' : 'text-xs'"
    >
      Voice note {{ compact ? '(optional)' : '— optional' }}
    </p>

    <div class="flex flex-wrap items-center gap-2">
      <button
        v-if="!recording && !modelValue"
        type="button"
        class="inline-flex items-center gap-1 rounded-lg border border-[#0097A7]/40 bg-[#e0f7fa] font-medium text-[#00838f] disabled:opacity-60"
        :class="compact ? 'px-2 py-1 text-[11px]' : 'px-3 py-1.5 text-xs'"
        :disabled="disabled"
        @click="startRecording"
      >
        <UIcon name="i-lucide-mic" :class="compact ? 'h-3.5 w-3.5' : 'h-4 w-4'" />
        Record
      </button>

      <button
        v-if="recording"
        type="button"
        class="inline-flex items-center gap-1 rounded-lg border border-red-200 bg-red-50 font-medium text-red-700 disabled:opacity-60"
        :class="compact ? 'px-2 py-1 text-[11px]' : 'px-3 py-1.5 text-xs'"
        :disabled="disabled"
        @click="stopRecording"
      >
        <UIcon name="i-lucide-circle-stop" class="animate-pulse" :class="compact ? 'h-3.5 w-3.5' : 'h-4 w-4'" />
        Stop recording
      </button>

      <button
        v-if="modelValue && !recording"
        type="button"
        class="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white font-medium text-slate-600 disabled:opacity-60"
        :class="compact ? 'px-2 py-1 text-[11px]' : 'px-3 py-1.5 text-xs'"
        :disabled="disabled"
        @click="removeRecording"
      >
        <UIcon name="i-lucide-trash-2" :class="compact ? 'h-3.5 w-3.5' : 'h-4 w-4'" />
        Remove
      </button>
    </div>

    <p v-if="recording" class="text-xs font-medium text-red-600">Recording… tap Stop when finished</p>

    <div v-if="previewUrl" class="rounded-lg border border-slate-200 bg-white p-2">
      <p class="mb-1 text-[11px] font-medium text-slate-500">Preview</p>
      <audio controls preload="metadata" :src="previewUrl" class="block w-full" />
    </div>

    <p v-if="error" class="text-xs text-red-600">{{ error }}</p>
  </div>
</template>
