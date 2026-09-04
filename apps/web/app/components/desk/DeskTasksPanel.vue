<script setup lang="ts">
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

const { api } = useApi()
const toast = useToast()
const { openPatient } = useDeskUrl()

const filter = ref<'Open' | 'Completed' | 'all'>('Open')
const items = ref<TaskRow[]>([])
const staff = ref<Staff[]>([])
const clients = ref<ClientOpt[]>([])
const loading = ref(false)
const showCreate = ref(false)
const form = reactive({
  task_description: '',
  due_date: '',
  client_id: null as number | null,
  assignee_id: null as number | null
})

async function load() {
  loading.value = true
  try {
    const data = await api<{ items: TaskRow[] }>('/tasks', {
      query: { status: filter.value === 'all' ? undefined : filter.value }
    })
    items.value = data.items
  } finally {
    loading.value = false
  }
}

async function openCreate() {
  if (!staff.value.length) {
    staff.value = await api<Staff[]>('/auth/users')
  }
  if (!clients.value.length) {
    const data = await api<{ items: ClientOpt[] }>('/clients', { query: { limit: 100 } })
    clients.value = data.items
  }
  showCreate.value = true
}

async function createTask() {
  try {
    await api('/tasks', {
      method: 'POST',
      body: {
        task_description: form.task_description,
        due_date: form.due_date || null,
        client_id: form.client_id,
        assignee_id: form.assignee_id
      }
    })
    showCreate.value = false
    form.task_description = ''
    toast.add({ title: 'Task created', color: 'success' })
    await load()
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
  }
}

async function setStatus(task: TaskRow, status: string) {
  await api(`/tasks/${task.task_id}`, { method: 'PATCH', body: { status } })
  await load()
}

watch(filter, load)
onMounted(load)
</script>

<template>
  <div class="h-full overflow-y-auto p-5 space-y-5">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <p class="text-sm text-slate-500">Clinic to-dos</p>
      <UButton icon="i-lucide-plus" class="bg-[#0097A7]" @click="openCreate">New task</UButton>
    </div>

    <div class="flex gap-1">
      <UButton
        v-for="f in [
          { id: 'Open', label: 'Open' },
          { id: 'Completed', label: 'Done' },
          { id: 'all', label: 'All' }
        ]"
        :key="f.id"
        size="sm"
        :variant="filter === f.id ? 'solid' : 'ghost'"
        :color="filter === f.id ? 'primary' : 'neutral'"
        @click="filter = f.id as typeof filter"
      >
        {{ f.label }}
      </UButton>
    </div>

    <p v-if="loading" class="text-stone-500">Loading…</p>
    <ul v-else class="divide-y divide-stone-100 overflow-hidden rounded-2xl border border-stone-200 bg-white">
      <li v-if="!items.length" class="px-4 py-10 text-center text-stone-500">No tasks.</li>
      <li v-for="t in items" :key="t.task_id" class="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p class="font-medium text-stone-900">{{ t.task_description }}</p>
          <p class="text-sm text-slate-500">
            <button
              v-if="t.client_id"
              type="button"
              class="hover:underline"
              @click="openPatient(t.client_id!)"
            >
              {{ t.client_name }}
            </button>
            <span v-else>Clinic</span>
            <span v-if="t.assignee_name"> · {{ t.assignee_name }}</span>
            <span v-if="t.due_date"> · due {{ t.due_date }}</span>
          </p>
        </div>
        <div class="flex gap-2">
          <UBadge :color="t.status === 'Completed' ? 'success' : 'warning'" variant="subtle">{{ t.status }}</UBadge>
          <UButton v-if="t.status === 'Open'" size="xs" @click="setStatus(t, 'Completed')">Done</UButton>
          <UButton v-else size="xs" color="neutral" variant="outline" @click="setStatus(t, 'Open')">Reopen</UButton>
        </div>
      </li>
    </ul>

    <UModal v-model:open="showCreate" title="New task">
      <template #body>
        <form class="space-y-3" @submit.prevent="createTask">
          <UFormField label="Task" required>
            <UTextarea v-model="form.task_description" class="w-full" :rows="3" />
          </UFormField>
          <UFormField label="Patient (optional)">
            <USelect
              v-model="form.client_id"
              :items="[
                { label: 'None', value: null },
                ...clients.map(c => ({ label: c.name, value: c.client_id }))
              ]"
              value-key="value"
              label-key="label"
              class="w-full"
            />
          </UFormField>
          <UFormField label="Assignee">
            <USelect
              v-model="form.assignee_id"
              :items="[
                { label: 'Unassigned', value: null },
                ...staff.map(s => ({ label: s.full_name, value: s.user_id }))
              ]"
              value-key="value"
              label-key="label"
              class="w-full"
            />
          </UFormField>
          <UFormField label="Due date">
            <UInput v-model="form.due_date" type="date" class="w-full" />
          </UFormField>
          <div class="flex justify-end gap-2">
            <UButton color="neutral" variant="ghost" @click="showCreate = false">Cancel</UButton>
            <UButton type="submit">Create</UButton>
          </div>
        </form>
      </template>
    </UModal>
  </div>
</template>
