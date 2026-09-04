<script setup lang="ts">
definePageMeta({ layout: 'mobile' })

type Task = {
  task_id: number
  task_description: string
  status: string
  due_date: string | null
  client_id: number | null
}

const { api } = useApi()
const toast = useToast()
const loading = ref(false)
const items = ref<Task[]>([])

async function load() {
  loading.value = true
  try {
    const data = await api<{ items: Task[] }>('/tasks', { query: { status: 'Open', limit: 80 } })
    items.value = data.items || []
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="flex h-full min-h-0 flex-col">
    <div class="shrink-0 border-b border-slate-200 bg-white px-4 py-3">
      <h1 class="text-lg font-semibold text-[#1C2B35]">Tasks</h1>
      <p class="text-xs text-slate-500">Open tasks</p>
    </div>
    <div class="min-h-0 flex-1 overflow-y-auto px-3 py-3">
      <p v-if="loading" class="py-10 text-center text-sm text-slate-400">Loading…</p>
      <ul v-else class="space-y-2">
        <li v-for="t in items" :key="t.task_id">
          <NuxtLink
            v-if="t.client_id"
            :to="`/clients/${t.client_id}`"
            class="block rounded-2xl border border-slate-200 bg-white p-3 shadow-sm"
          >
            <p class="text-sm font-medium text-[#1C2B35]">{{ t.task_description }}</p>
            <p class="mt-0.5 text-xs text-slate-500">
              {{ t.status }}<template v-if="t.due_date"> · due {{ t.due_date }}</template>
            </p>
          </NuxtLink>
          <div v-else class="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
            <p class="text-sm font-medium text-[#1C2B35]">{{ t.task_description }}</p>
            <p class="mt-0.5 text-xs text-slate-500">
              {{ t.status }}<template v-if="t.due_date"> · due {{ t.due_date }}</template>
            </p>
          </div>
        </li>
        <li v-if="!items.length" class="rounded-2xl border border-dashed border-slate-300 px-4 py-12 text-center text-sm text-slate-400">
          No open tasks.
        </li>
      </ul>
      <p class="mt-4 text-center text-[11px] text-slate-400">
        Full desk tasks · <NuxtLink to="/desk?view=tasks" class="text-[#0097A7]">Open desk</NuxtLink>
      </p>
    </div>
  </div>
</template>
