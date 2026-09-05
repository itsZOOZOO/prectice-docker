<script setup lang="ts">
type NoteAttachment = { id: number | null, key: string, url: string | null }
type PendingFile = { file: File, preview: string | null }

const open = defineModel<boolean>('open', { default: false })
const props = defineProps<{
  clientId: number | null
  noteId: number | null
  initialBody?: string
  initialDatetime?: string
  initialAttachments?: NoteAttachment[]
}>()
const emit = defineEmits<{ saved: [] }>()

const { api } = useApi()
const toast = useToast()

const MAX_NOTE_FILES = 10
const MAX_FILE_BYTES = 10 * 1024 * 1024

const body = ref('')
const noteDatetime = ref(localDatetimeInputValue())
const showDatetime = ref(false)
const kept = ref<NoteAttachment[]>([])
const removeIds = ref<number[]>([])
const pending = ref<PendingFile[]>([])
const saveOriginalQuality = ref(false)
const processingFiles = ref(false)
const saving = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

const totalFiles = computed(() => kept.value.length + pending.value.length)
const canSave = computed(() => Boolean(body.value.trim() || totalFiles.value > 0))

function isImageFile(file: File) {
  return file.type.startsWith('image/') || /\.(jpe?g|png|gif|webp|heic)$/i.test(file.name)
}

function isImageAtt(att: NoteAttachment) {
  return /\.(jpe?g|png|gif|webp|heic|bmp)(\?|$)/i.test(att.key || att.url || '')
}

function fileLabel(key: string) {
  const part = key.split('/').pop() || key
  return part.length > 28 ? `…${part.slice(-24)}` : part
}

function clearPending() {
  for (const p of pending.value) {
    if (p.preview) URL.revokeObjectURL(p.preview)
  }
  pending.value = []
}

function resetFromProps() {
  body.value = props.initialBody || ''
  const raw = props.initialDatetime || ''
  noteDatetime.value = raw
    ? localDatetimeInputValue(new Date(raw))
    : localDatetimeInputValue()
  showDatetime.value = false
  kept.value = (props.initialAttachments || []).filter(a => a.id != null)
  removeIds.value = []
  clearPending()
  saveOriginalQuality.value = false
}

watch(open, (v) => {
  if (v) resetFromProps()
  else clearPending()
})

function removeKept(att: NoteAttachment) {
  if (att.id == null) return
  removeIds.value.push(att.id)
  kept.value = kept.value.filter(a => a.id !== att.id)
}

function removePendingAt(idx: number) {
  const p = pending.value[idx]
  if (p?.preview) URL.revokeObjectURL(p.preview)
  pending.value.splice(idx, 1)
}

async function onPickFiles(ev: Event) {
  const input = ev.target as HTMLInputElement
  const picked = Array.from(input.files || [])
  input.value = ''
  if (!picked.length) return
  const room = MAX_NOTE_FILES - totalFiles.value
  if (room <= 0) {
    toast.add({ title: `Max ${MAX_NOTE_FILES} files per note`, color: 'warning' })
    return
  }
  const next = picked.slice(0, room)
  processingFiles.value = true
  try {
    for (const file of next) {
      if (file.size > MAX_FILE_BYTES) {
        toast.add({ title: `${file.name} exceeds 10 MB`, color: 'error' })
        continue
      }
      const okType = file.type.startsWith('image/') || file.type === 'application/pdf'
        || /\.(jpe?g|png|gif|webp|heic|pdf)$/i.test(file.name)
      if (!okType) {
        toast.add({ title: `${file.name}: images or PDF only`, color: 'error' })
        continue
      }

      let processed = file
      if (isImageFile(file) && !saveOriginalQuality.value) {
        try {
          processed = await compressImage(file)
        } catch {
          toast.add({
            title: `Couldn’t compress ${file.name}, uploading original`,
            color: 'warning'
          })
          processed = file
        }
      }

      if (processed.size > MAX_FILE_BYTES) {
        toast.add({ title: `${file.name} exceeds 10 MB after processing`, color: 'error' })
        continue
      }

      pending.value.push({
        file: processed,
        preview: isImageFile(processed) ? URL.createObjectURL(processed) : null
      })
    }
  } finally {
    processingFiles.value = false
  }
}

async function save() {
  if (!props.clientId || !props.noteId || !canSave.value) return
  saving.value = true
  try {
    const fd = new FormData()
    fd.append('body', body.value.trim())
    fd.append('note_datetime', noteDatetime.value || localDatetimeInputValue())
    if (removeIds.value.length) {
      fd.append('remove_attachment_ids', removeIds.value.join(','))
    }
    for (const p of pending.value) {
      fd.append('files', p.file)
    }
    await api(`/clients/${props.clientId}/notes/${props.noteId}`, {
      method: 'PATCH',
      body: fd
    })
    toast.add({ title: 'Note updated', color: 'success' })
    open.value = false
    emit('saved')
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to update note', color: 'error' })
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <UModal v-model:open="open" title="Edit note">
    <template #body>
      <div class="flex max-h-[min(70vh,560px)] flex-col">
        <div class="min-h-0 flex-1 space-y-3 overflow-y-auto pb-2">
          <input
            v-if="showDatetime"
            v-model="noteDatetime"
            type="datetime-local"
            class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-[#0097A7]"
          >
          <div
            v-else
            class="flex items-center gap-2 rounded-lg bg-sky-50 px-2.5 py-1.5 text-xs text-sky-800"
          >
            <UIcon name="i-lucide-clock" class="h-3.5 w-3.5 shrink-0" />
            <span class="min-w-0 flex-1 truncate">{{ formatNoteDatetimePreview(noteDatetime) }}</span>
            <button
              type="button"
              class="shrink-0 text-sky-700 hover:text-sky-900"
              title="Change date & time"
              @click="showDatetime = true"
            >
              Change
            </button>
          </div>

          <textarea
            v-model="body"
            rows="5"
            class="w-full resize-y rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-[#0097A7]"
            placeholder="Note text…"
          />

          <div v-if="kept.length || pending.length" class="space-y-2">
            <div
              v-for="att in kept"
              :key="att.id ?? att.key"
              class="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-2"
            >
              <img
                v-if="att.url && isImageAtt(att)"
                :src="att.url"
                alt=""
                class="h-10 w-10 shrink-0 rounded object-cover"
              >
              <UIcon v-else name="i-lucide-paperclip" class="h-4 w-4 shrink-0 text-slate-400" />
              <a
                v-if="att.url"
                :href="att.url"
                target="_blank"
                rel="noopener"
                class="min-w-0 flex-1 truncate text-xs text-[#0097A7] underline"
              >
                {{ fileLabel(att.key) }}
              </a>
              <span v-else class="min-w-0 flex-1 truncate text-xs text-slate-500">{{ fileLabel(att.key) }}</span>
              <button
                type="button"
                class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-red-600 hover:bg-red-50"
                title="Remove attachment"
                @click="removeKept(att)"
              >
                <UIcon name="i-lucide-x" class="h-4 w-4" />
              </button>
            </div>
            <div
              v-for="(p, idx) in pending"
              :key="`p-${idx}`"
              class="flex items-center gap-2 rounded-lg border border-dashed border-[#0097A7]/40 bg-[#e0f7fa]/40 px-2.5 py-2"
            >
              <img
                v-if="p.preview"
                :src="p.preview"
                alt=""
                class="h-10 w-10 shrink-0 rounded object-cover"
              >
              <UIcon v-else name="i-lucide-paperclip" class="h-4 w-4 shrink-0 text-slate-400" />
              <span class="min-w-0 flex-1 truncate text-xs text-slate-600">{{ p.file.name }}</span>
              <button
                type="button"
                class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-red-600 hover:bg-red-50"
                title="Remove"
                @click="removePendingAt(idx)"
              >
                <UIcon name="i-lucide-x" class="h-4 w-4" />
              </button>
            </div>
          </div>

          <div class="flex flex-wrap items-center gap-2">
            <button
              type="button"
              class="flex h-9 items-center gap-1.5 rounded-lg border border-slate-200 px-3 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50"
              :disabled="processingFiles || totalFiles >= MAX_NOTE_FILES"
              @click="fileInput?.click()"
            >
              <UIcon name="i-lucide-paperclip" class="h-4 w-4" />
              Add files
            </button>
            <label
              v-if="pending.some(p => isImageFile(p.file)) || processingFiles"
              class="flex items-center gap-1.5 text-[11px] text-slate-500"
            >
              <input v-model="saveOriginalQuality" type="checkbox" class="rounded">
              Original quality
            </label>
            <input
              ref="fileInput"
              type="file"
              multiple
              accept="image/*,.pdf,application/pdf"
              class="hidden"
              @change="onPickFiles"
            >
          </div>
        </div>

        <div class="mt-3 flex shrink-0 items-center justify-between gap-2 border-t border-slate-100 pt-3">
          <UButton color="neutral" variant="ghost" @click="open = false">
            Cancel
          </UButton>
          <UButton
            class="bg-[#0097A7]"
            :loading="saving"
            :disabled="!canSave || processingFiles"
            @click="save"
          >
            Save
          </UButton>
        </div>
      </div>
    </template>
  </UModal>
</template>
