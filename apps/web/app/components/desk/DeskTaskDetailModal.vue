<script setup lang="ts">
import { formatNoteTime, formatTaskDueDate, isTaskOpen, isTaskOverdue } from '~/utils/taskPanel'
import type { TaskVoiceBlob } from '~/components/desk/DeskTaskVoiceRecorder.vue'

type TaskNote = {
  note_id: number
  note_text: string
  attachment_url?: string | null
  created_at: string
  user_name: string | null
}

type TaskDetail = {
  task_id: number
  task_description: string
  status: string
  due_date: string | null
  client_id: number | null
  client_name: string | null
  assignee_name: string | null
  created_by_name: string | null
  notes?: TaskNote[]
}

const open = defineModel<boolean>('open', { default: false })
const props = defineProps<{
  taskId: number | null
}>()
const emit = defineEmits<{
  updated: []
}>()

const { api } = useApi()
const toast = useToast()
const route = useRoute()
const router = useRouter()
const { openPatient: deskOpenPatient } = useDeskUrl()

const loading = ref(false)
const saving = ref(false)
const noteSaving = ref(false)
const detail = ref<TaskDetail | null>(null)
const noteDraft = ref('')
const noteVoice = ref<TaskVoiceBlob | null>(null)

watch(
  () => [open.value, props.taskId] as const,
  async ([isOpen, id]) => {
    if (!isOpen || !id) {
      if (!isOpen) {
        detail.value = null
        noteDraft.value = ''
        noteVoice.value = null
      }
      return
    }
    await load(id)
  }
)

async function load(id: number) {
  loading.value = true
  try {
    detail.value = await api<TaskDetail>(`/tasks/${id}`)
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to load task', color: 'error' })
    open.value = false
  } finally {
    loading.value = false
  }
}

const overdue = computed(() =>
  detail.value ? isTaskOverdue(detail.value.due_date, detail.value.status) : false
)
const completed = computed(() => (detail.value?.status || '').toLowerCase() === 'completed')

async function setStatus(status: 'Open' | 'Completed') {
  if (!detail.value || saving.value) return
  saving.value = true
  try {
    detail.value = await api<TaskDetail>(`/tasks/${detail.value.task_id}`, {
      method: 'PATCH',
      body: { status }
    })
    toast.add({
      title: status === 'Completed' ? 'Marked complete' : 'Reopened',
      color: 'success'
    })
    emit('updated')
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Update failed', color: 'error' })
  } finally {
    saving.value = false
  }
}

async function addNote() {
  if (!detail.value || noteSaving.value) return
  const text = noteDraft.value.trim()
  if (!text && !noteVoice.value) return
  noteSaving.value = true
  try {
    const form = new FormData()
    form.set('note_text', text)
    if (noteVoice.value) {
      const file = new File(
        [noteVoice.value.blob],
        noteVoice.value.fileName,
        { type: noteVoice.value.mimeType || noteVoice.value.blob.type || 'audio/webm' }
      )
      form.append('voice', file)
    }
    detail.value = await api<TaskDetail>(`/tasks/${detail.value.task_id}/notes`, {
      method: 'POST',
      body: form
    })
    noteDraft.value = ''
    noteVoice.value = null
    toast.add({ title: 'Comment added', color: 'success' })
    emit('updated')
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to add comment', color: 'error' })
  } finally {
    noteSaving.value = false
  }
}

function openPatient() {
  if (!detail.value?.client_id) return
  const id = detail.value.client_id
  open.value = false
  if (route.path.startsWith('/desk')) {
    void deskOpenPatient(id)
    return
  }
  void router.push(`/clients/${id}`)
}

function showNoteText(n: TaskNote) {
  const text = (n.note_text || '').trim()
  if (!text) return false
  if (n.attachment_url && text === 'Voice note') return false
  return true
}
</script>

<template>
  <UModal
    v-model:open="open"
    :close="false"
    :ui="{ content: 'sm:max-w-md', header: 'flex items-center gap-1.5 p-4 sm:px-6' }"
  >
    <template #header>
      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-2">
          <span
            class="rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white"
            :class="completed ? 'bg-emerald-500' : overdue ? 'bg-red-500' : 'bg-amber-500'"
          >
            {{ detail?.status || 'Task' }}
          </span>
        </div>
        <p
          v-if="detail && !loading"
          class="mt-1 text-sm font-medium leading-snug text-[#1C2B35]"
          :class="completed ? 'text-slate-500 line-through' : ''"
        >
          {{ detail.task_description }}
        </p>
        <p v-else-if="loading" class="mt-1 text-sm text-slate-400">Loading…</p>
      </div>
      <UButton
        icon="i-lucide-x"
        color="neutral"
        variant="ghost"
        square
        aria-label="Close"
        @click="open = false"
      />
    </template>

    <template #body>
      <div v-if="detail && !loading" class="space-y-4">
        <div class="flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-600">
          <span>{{ formatTaskDueDate(detail.due_date) }}</span>
          <button
            v-if="detail.client_id && detail.client_name"
            type="button"
            class="font-medium text-[#0097A7]"
            @click="openPatient"
          >
            {{ detail.client_name }}
          </button>
          <span v-if="detail.assignee_name">→ {{ detail.assignee_name }}</span>
          <span v-if="detail.created_by_name" class="text-slate-400">by {{ detail.created_by_name }}</span>
        </div>

        <div class="flex flex-wrap gap-2">
          <UButton
            v-if="isTaskOpen(detail.status)"
            color="success"
            :loading="saving"
            @click="setStatus('Completed')"
          >
            Mark complete
          </UButton>
          <UButton
            v-else-if="completed"
            color="neutral"
            variant="outline"
            :loading="saving"
            @click="setStatus('Open')"
          >
            Reopen
          </UButton>
        </div>

        <div>
          <p class="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-400">Comments</p>
          <ul v-if="detail.notes?.length" class="mb-3 space-y-2">
            <li
              v-for="n in detail.notes"
              :key="n.note_id"
              class="rounded-xl border border-slate-100 bg-slate-50 px-3 py-2"
            >
              <p
                v-if="showNoteText(n)"
                class="whitespace-pre-wrap text-sm text-[#1C2B35]"
              >
                {{ n.note_text }}
              </p>
              <audio
                v-if="n.attachment_url"
                controls
                preload="metadata"
                :src="n.attachment_url"
                class="mt-1.5 block w-full"
              />
              <p
                v-else-if="n.note_text === 'Voice note'"
                class="text-sm italic text-slate-400"
              >
                Voice note unavailable
              </p>
              <p class="mt-1 text-[11px] text-slate-400">
                {{ n.user_name || 'Staff' }} · {{ formatNoteTime(n.created_at) }}
              </p>
            </li>
          </ul>
          <p v-else class="mb-3 text-sm text-slate-400">No comments yet.</p>

          <div class="space-y-2">
            <UTextarea
              v-model="noteDraft"
              :rows="3"
              placeholder="Add a comment…"
              autoresize
              :disabled="noteSaving"
            />
            <DeskTaskVoiceRecorder
              v-model="noteVoice"
              compact
              :disabled="noteSaving"
            />
            <div class="flex justify-end">
              <UButton
                class="bg-[#0097A7]"
                :disabled="!noteDraft.trim() && !noteVoice"
                :loading="noteSaving"
                @click="addNote"
              >
                Add comment
              </UButton>
            </div>
          </div>
        </div>
      </div>
    </template>
  </UModal>
</template>
