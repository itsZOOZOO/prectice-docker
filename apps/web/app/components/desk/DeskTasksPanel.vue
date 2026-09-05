<script setup lang="ts">
import { todayInIst } from '~/utils/agendaCalendar'
import type { TaskVoiceBlob } from '~/components/desk/DeskTaskVoiceRecorder.vue'
import {
  formatTaskDueDate,
  isTaskOverdue,
  shiftDate,
  taskDateLabel,
  type TaskPanelFilter,
  type TaskPanelScope
} from '~/utils/taskPanel'

type TaskRow = {
  task_id: number
  task_description: string
  status: string
  due_date: string | null
  client_id: number | null
  client_name: string | null
  assignee_name: string | null
}
type Staff = { user_id: number, full_name: string }
type ClientOpt = { client_id: number, name: string }

const FILTER_OPTIONS: { value: TaskPanelFilter, label: string }[] = [
  { value: 'today', label: 'Due Today' },
  { value: 'overdue', label: 'Overdue' },
  { value: 'future', label: 'Future' },
  { value: 'pending', label: 'All Pending' },
  { value: 'completed_today', label: 'Completed Today' },
  { value: 'all', label: 'All Tasks' }
]

const { api } = useApi()
const toast = useToast()
const { openPatient } = useDeskUrl()
const refreshBadges = inject<() => void>('deskRefreshBadges', () => {})

const selectedDate = ref(todayInIst())
const filter = ref<TaskPanelFilter>('today')
const scope = ref<TaskPanelScope>('all')
const loading = ref(false)
const items = ref<TaskRow[]>([])

const detailOpen = ref(false)
const detailTaskId = ref<number | null>(null)

const createOpen = ref(false)
const creating = ref(false)
const createVoice = ref<TaskVoiceBlob | null>(null)
const staff = ref<Staff[]>([])
const clients = ref<ClientOpt[]>([])
const form = reactive({
  task_description: '',
  due_date: todayInIst(),
  client_id: null as number | null,
  assignee_id: null as number | null
})

const headerLabel = computed(() => taskDateLabel(selectedDate.value))

async function load() {
  loading.value = true
  try {
    const data = await api<{ items: TaskRow[] }>('/tasks', {
      query: {
        date: selectedDate.value,
        filter: filter.value,
        scope: scope.value
      }
    })
    items.value = data.items || []
    refreshBadges()
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to load', color: 'error' })
    items.value = []
  } finally {
    loading.value = false
  }
}

function changeDate(delta: number) {
  selectedDate.value = shiftDate(selectedDate.value, delta)
}

function openDetail(task: TaskRow) {
  detailTaskId.value = task.task_id
  detailOpen.value = true
}

async function openCreate() {
  form.task_description = ''
  form.due_date = selectedDate.value
  form.client_id = null
  form.assignee_id = null
  createVoice.value = null
  try {
    if (!staff.value.length) {
      staff.value = await api<Staff[]>('/auth/users')
    }
    if (!clients.value.length) {
      const data = await api<{ items: ClientOpt[] }>('/clients', { query: { limit: 100 } })
      clients.value = data.items || []
    }
  } catch {
    /* optional fields */
  }
  createOpen.value = true
}

async function createTask() {
  const desc = form.task_description.trim()
  if (!desc || creating.value) return
  creating.value = true
  try {
    const created = await api<TaskRow>('/tasks', {
      method: 'POST',
      body: {
        task_description: desc,
        due_date: form.due_date || null,
        client_id: form.client_id,
        assignee_id: form.assignee_id
      }
    })
    if (createVoice.value && created?.task_id) {
      const fd = new FormData()
      fd.set('note_text', '')
      const file = new File(
        [createVoice.value.blob],
        createVoice.value.fileName,
        { type: createVoice.value.mimeType || createVoice.value.blob.type || 'audio/webm' }
      )
      fd.append('voice', file)
      await api(`/tasks/${created.task_id}/notes`, {
        method: 'POST',
        body: fd
      })
    }
    createOpen.value = false
    createVoice.value = null
    toast.add({ title: 'Task created', color: 'success' })
    await load()
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Create failed', color: 'error' })
  } finally {
    creating.value = false
  }
}

async function quickComplete(task: TaskRow, e: Event) {
  e.stopPropagation()
  try {
    await api(`/tasks/${task.task_id}`, { method: 'PATCH', body: { status: 'Completed' } })
    toast.add({ title: 'Marked complete', color: 'success' })
    await load()
  } catch (err: unknown) {
    toast.add({ title: err instanceof Error ? err.message : 'Update failed', color: 'error' })
  }
}

function cardBorder(task: TaskRow) {
  if ((task.status || '').toLowerCase() === 'completed') return '#22c55e'
  if (isTaskOverdue(task.due_date, task.status)) return '#ef4444'
  return '#f59e0b'
}

function preview(text: string) {
  return text.length > 140 ? `${text.slice(0, 140)}…` : text
}

watch([selectedDate, filter, scope], () => { void load() })
onMounted(load)
</script>

<template>
  <div class="flex h-full min-h-0 flex-col overflow-hidden p-5">
    <div class="mb-4 flex shrink-0 flex-wrap items-center justify-between gap-3">
      <div class="flex min-w-0 flex-wrap items-center gap-2">
        <button
          type="button"
          class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-white text-[#1C2B35] hover:bg-slate-50"
          aria-label="Previous day"
          @click="changeDate(-1)"
        >
          <UIcon name="i-lucide-chevron-left" class="h-5 w-5" />
        </button>
        <p class="min-w-[10rem] text-center text-sm font-semibold text-[#1C2B35]">
          {{ headerLabel }}
        </p>
        <button
          type="button"
          class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-white text-[#1C2B35] hover:bg-slate-50"
          aria-label="Next day"
          @click="changeDate(1)"
        >
          <UIcon name="i-lucide-chevron-right" class="h-5 w-5" />
        </button>
      </div>
      <UButton
        icon="i-lucide-plus"
        class="bg-[#0097A7]"
        @click="openCreate"
      >
        New task
      </UButton>
    </div>

    <div class="mb-4 flex shrink-0 flex-wrap items-center gap-2">
      <select
        v-model="filter"
        class="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-[#1C2B35]"
      >
        <option
          v-for="opt in FILTER_OPTIONS"
          :key="opt.value"
          :value="opt.value"
        >
          {{ opt.label }}
        </option>
      </select>
      <select
        v-model="scope"
        class="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-[#1C2B35]"
      >
        <option value="all">All Staff</option>
        <option value="mine">My Tasks</option>
      </select>
    </div>

    <div class="min-h-0 flex-1 space-y-2 overflow-y-auto">
      <p
        v-if="loading"
        class="py-16 text-center text-sm text-slate-400"
      >
        Loading tasks…
      </p>
      <template v-else>
        <div
          v-for="t in items"
          :key="t.task_id"
          class="flex items-stretch gap-2 rounded-xl border border-slate-200 bg-white shadow-sm"
          :style="{ borderLeftWidth: '4px', borderLeftColor: cardBorder(t) }"
        >
          <button
            type="button"
            class="min-w-0 flex-1 px-4 py-3 text-left hover:bg-slate-50/80"
            @click="openDetail(t)"
          >
            <p
              class="text-sm font-medium text-[#1C2B35]"
              :class="(t.status || '').toLowerCase() === 'completed' ? 'line-through opacity-70' : ''"
            >
              {{ preview(t.task_description) }}
            </p>
            <p class="mt-1.5 text-xs text-slate-500">
              <button
                v-if="t.client_id && t.client_name"
                type="button"
                class="font-medium text-[#0097A7] hover:underline"
                @click.stop="openPatient(t.client_id!)"
              >
                {{ t.client_name }}
              </button>
              <span v-else>Clinic</span>
              <span> · {{ formatTaskDueDate(t.due_date) }}</span>
              <template v-if="t.assignee_name"> · {{ t.assignee_name }}</template>
            </p>
          </button>
          <div class="flex shrink-0 items-center gap-2 pr-3">
            <UButton
              v-if="(t.status || '').toLowerCase() !== 'completed'"
              size="xs"
              color="success"
              variant="soft"
              @click="quickComplete(t, $event)"
            >
              Done
            </UButton>
            <UButton
              size="xs"
              color="neutral"
              variant="ghost"
              @click="openDetail(t)"
            >
              Open
            </UButton>
          </div>
        </div>
        <p
          v-if="!items.length"
          class="rounded-xl border border-dashed border-slate-300 px-4 py-12 text-center text-sm text-slate-400"
        >
          No tasks for this view.
        </p>
      </template>
    </div>

    <DeskTaskDetailModal
      v-model:open="detailOpen"
      :task-id="detailTaskId"
      @updated="load"
    />

    <UModal
      v-model:open="createOpen"
      title="New task"
      :ui="{ content: 'sm:max-w-md' }"
    >
      <template #body>
        <form
          class="space-y-3"
          @submit.prevent="createTask"
        >
          <UFormField
            label="Description"
            required
          >
            <UTextarea
              v-model="form.task_description"
              :rows="3"
              required
              placeholder="What needs to be done?"
              autoresize
              class="w-full"
            />
          </UFormField>
          <UFormField label="Due date">
            <UInput
              v-model="form.due_date"
              type="date"
              class="w-full"
            />
          </UFormField>
          <UFormField label="Patient (optional)">
            <select
              v-model="form.client_id"
              class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
            >
              <option :value="null">
                None
              </option>
              <option
                v-for="c in clients"
                :key="c.client_id"
                :value="c.client_id"
              >
                {{ c.name }}
              </option>
            </select>
          </UFormField>
          <UFormField label="Assignee (optional)">
            <select
              v-model="form.assignee_id"
              class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
            >
              <option :value="null">
                Unassigned
              </option>
              <option
                v-for="s in staff"
                :key="s.user_id"
                :value="s.user_id"
              >
                {{ s.full_name }}
              </option>
            </select>
          </UFormField>
          <DeskTaskVoiceRecorder
            v-model="createVoice"
            :disabled="creating"
          />
          <div class="flex justify-end gap-2 pt-1">
            <UButton
              color="neutral"
              variant="ghost"
              type="button"
              @click="createOpen = false"
            >
              Cancel
            </UButton>
            <UButton
              class="bg-[#0097A7]"
              type="submit"
              :loading="creating"
              :disabled="!form.task_description.trim()"
            >
              Create
            </UButton>
          </div>
        </form>
      </template>
    </UModal>
  </div>
</template>
