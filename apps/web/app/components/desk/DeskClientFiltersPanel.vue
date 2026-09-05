<script setup lang="ts">
import {
  CLIENT_FILTER_RELATIVE_DAYS,
  CLIENT_FILTER_STATUSES,
  emptyClientFilterCriteria,
  normalizeCriteria,
  type ClientFilterCriteria,
  type ClientFilterMember,
  type ClientFilterPresence,
  type ClientFilterRow
} from '~/utils/clientFilters'

type ClientSearchHit = {
  client_id: number
  name: string
  number: string | null
  place: string | null
}

const { api } = useApi()
const toast = useToast()

const filters = ref<ClientFilterRow[]>([])
const loading = ref(true)
const saving = ref(false)
const previewing = ref(false)
const previewCount = ref<number | null>(null)
const error = ref('')

const editingId = ref<number | null>(null)
const formOpen = ref(false)
const formName = ref('')
const formSortOrder = ref(0)
const formShowOnDashboard = ref(false)
const criteria = ref<ClientFilterCriteria>(emptyClientFilterCriteria())

const members = ref<ClientFilterMember[]>([])
const membersLoading = ref(false)
const memberSearch = ref('')
const memberHits = ref<ClientSearchHit[]>([])
const memberSearching = ref(false)
let memberSearchTimer: ReturnType<typeof setTimeout> | null = null

const PRESENCE_OPTIONS: { label: string, value: ClientFilterPresence }[] = [
  { label: 'Any', value: 'any' },
  { label: 'Has', value: 'has' },
  { label: 'None', value: 'none' }
]

async function loadFilters() {
  loading.value = true
  error.value = ''
  try {
    const data = await api<{ filters: ClientFilterRow[], tags?: unknown[] }>('/settings/client-filters')
    filters.value = data.filters ?? []
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to load patient lists'
  } finally {
    loading.value = false
  }
}

function openNew() {
  editingId.value = null
  formName.value = ''
  formSortOrder.value = 0
  formShowOnDashboard.value = false
  criteria.value = emptyClientFilterCriteria()
  previewCount.value = null
  members.value = []
  memberSearch.value = ''
  memberHits.value = []
  formOpen.value = true
}

function openEdit(row: ClientFilterRow) {
  editingId.value = row.filter_id
  formName.value = row.name
  formSortOrder.value = row.sort_order
  formShowOnDashboard.value = row.show_on_dashboard
  criteria.value = normalizeCriteria(row.criteria)
  previewCount.value = null
  memberSearch.value = ''
  memberHits.value = []
  formOpen.value = true
  void loadMembers(row.filter_id)
}

async function loadMembers(filterId: number) {
  membersLoading.value = true
  try {
    const data = await api<{ members: ClientFilterMember[] }>(
      `/settings/client-filters/${filterId}/members`
    )
    members.value = data.members ?? []
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to load members', color: 'error' })
  } finally {
    membersLoading.value = false
  }
}

function toggleStatus(list: 'status_include' | 'status_exclude', status: string) {
  const arr = criteria.value[list]
  const idx = arr.indexOf(status)
  if (idx >= 0) arr.splice(idx, 1)
  else arr.push(status)
  // Mutual exclusion across include/exclude
  const other = list === 'status_include' ? 'status_exclude' : 'status_include'
  const oidx = criteria.value[other].indexOf(status)
  if (oidx >= 0) criteria.value[other].splice(oidx, 1)
  previewCount.value = null
}

function setDateMode(mode: ClientFilterCriteria['date']['mode']) {
  if (mode === 'any') {
    criteria.value.date = { mode: 'any' }
  } else if (mode === 'relative') {
    criteria.value.date = {
      mode: 'relative',
      relative_days: criteria.value.date.relative_days || 30
    }
  } else {
    criteria.value.date = {
      mode: 'absolute',
      from: criteria.value.date.from || '',
      to: criteria.value.date.to || ''
    }
  }
  previewCount.value = null
}

function buildPayload() {
  const c = normalizeCriteria(criteria.value)
  const body: Record<string, unknown> = {
    name: formName.value.trim(),
    sort_order: Number(formSortOrder.value) || 0,
    show_on_dashboard: formShowOnDashboard.value,
    criteria: {
      ...c,
      total_billed_min: c.total_billed_min && c.total_billed_min > 0 ? c.total_billed_min : null,
      pending_payment_min: c.pending_payment_min && c.pending_payment_min > 0
        ? c.pending_payment_min
        : null
    }
  }
  return body
}

async function saveFilter() {
  if (!formName.value.trim()) {
    toast.add({ title: 'Name is required', color: 'error' })
    return
  }
  saving.value = true
  try {
    const body = buildPayload()
    if (editingId.value != null) {
      await api<{ filter: ClientFilterRow }>(`/settings/client-filters/${editingId.value}`, {
        method: 'PATCH',
        body
      })
      toast.add({ title: 'Patient list updated', color: 'success' })
    } else {
      const data = await api<{ filter: ClientFilterRow }>('/settings/client-filters', {
        method: 'POST',
        body
      })
      editingId.value = data.filter.filter_id
      toast.add({ title: 'Patient list created', color: 'success' })
    }
    await loadFilters()
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Save failed', color: 'error' })
  } finally {
    saving.value = false
  }
}

async function runPreview() {
  previewing.value = true
  try {
    const body = buildPayload()
    const data = await api<{ count: number }>('/settings/client-filters/preview', {
      method: 'POST',
      body: {
        criteria: body.criteria,
        filter_id: editingId.value
      }
    })
    previewCount.value = data.count
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Preview failed', color: 'error' })
  } finally {
    previewing.value = false
  }
}

async function softDelete(row: ClientFilterRow) {
  if (!confirm(`Delete “${row.name}”?`)) return
  try {
    await api(`/settings/client-filters/${row.filter_id}`, { method: 'DELETE' })
    if (editingId.value === row.filter_id) formOpen.value = false
    toast.add({ title: 'Patient list deleted', color: 'success' })
    await loadFilters()
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Delete failed', color: 'error' })
  }
}

watch(memberSearch, (q) => {
  if (memberSearchTimer) clearTimeout(memberSearchTimer)
  const trimmed = q.trim()
  if (!trimmed) {
    memberHits.value = []
    return
  }
  memberSearchTimer = setTimeout(async () => {
    memberSearching.value = true
    try {
      const data = await api<{ items: ClientSearchHit[] }>('/clients', {
        query: { q: trimmed, limit: 12 }
      })
      const existing = new Set(members.value.map(m => m.client_id))
      memberHits.value = (data.items ?? []).filter(c => !existing.has(c.client_id))
    } catch {
      memberHits.value = []
    } finally {
      memberSearching.value = false
    }
  }, 220)
})

async function addMember(client: ClientSearchHit) {
  if (editingId.value == null) {
    toast.add({ title: 'Save the list first, then add members', color: 'warning' })
    return
  }
  try {
    await api(`/settings/client-filters/${editingId.value}/members`, {
      method: 'POST',
      body: { client_id: client.client_id }
    })
    memberSearch.value = ''
    memberHits.value = []
    await loadMembers(editingId.value)
    await loadFilters()
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Add failed', color: 'error' })
  }
}

async function removeMember(clientId: number) {
  if (editingId.value == null) return
  try {
    await api(`/settings/client-filters/${editingId.value}/members/${clientId}`, {
      method: 'DELETE'
    })
    await loadMembers(editingId.value)
    await loadFilters()
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Remove failed', color: 'error' })
  }
}

onMounted(() => {
  void loadFilters()
})
</script>

<template>
  <div class="flex h-full min-h-0 flex-col lg:flex-row">
    <div class="min-h-0 w-full shrink-0 overflow-y-auto border-b border-slate-200 bg-white lg:w-[280px] lg:border-b-0 lg:border-r">
      <div class="flex items-center justify-between gap-2 border-b border-slate-100 px-3 py-2.5">
        <h2 class="text-sm font-semibold text-slate-800">Patient lists</h2>
        <button
          type="button"
          class="rounded-md bg-[#0097A7] px-2.5 py-1 text-xs font-semibold text-white hover:bg-[#00838f]"
          @click="openNew"
        >
          + New
        </button>
      </div>
      <p v-if="loading" class="px-3 py-6 text-center text-xs text-slate-400">Loading…</p>
      <p v-else-if="error" class="px-3 py-4 text-xs text-red-600">{{ error }}</p>
      <ul v-else class="divide-y divide-slate-100">
        <li v-for="row in filters" :key="row.filter_id">
          <button
            type="button"
            class="flex w-full items-start gap-2 px-3 py-2.5 text-left hover:bg-slate-50"
            :class="editingId === row.filter_id && formOpen ? 'bg-[#e0f7fa]' : ''"
            @click="openEdit(row)"
          >
            <div class="min-w-0 flex-1">
              <p class="truncate text-sm font-medium text-slate-800">{{ row.name }}</p>
              <p class="mt-0.5 text-[11px] text-slate-500">
                Order {{ row.sort_order }}
                <span v-if="row.show_on_dashboard"> · Dashboard</span>
                <span v-if="row.manual_member_count"> · {{ row.manual_member_count }} manual</span>
              </p>
            </div>
            <button
              type="button"
              class="shrink-0 rounded px-1.5 py-0.5 text-[11px] text-red-600 hover:bg-red-50"
              title="Delete"
              @click.stop="softDelete(row)"
            >
              Delete
            </button>
          </button>
        </li>
        <li v-if="!filters.length" class="px-3 py-8 text-center text-xs text-slate-400">
          No saved lists yet.
        </li>
      </ul>
    </div>

    <div class="min-h-0 flex-1 overflow-y-auto p-4">
      <div
        v-if="!formOpen"
        class="flex h-full flex-col items-center justify-center text-slate-400"
      >
        <p class="text-sm">Select a list or create a new one.</p>
      </div>

      <div v-else class="mx-auto max-w-2xl space-y-4">
        <div class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h3 class="text-sm font-semibold text-slate-800">
            {{ editingId != null ? 'Edit list' : 'New list' }}
          </h3>
          <div class="mt-3 grid gap-3 sm:grid-cols-2">
            <label class="block sm:col-span-2">
              <span class="mb-1 block text-xs font-medium text-slate-600">Name</span>
              <input
                v-model="formName"
                type="text"
                class="h-9 w-full rounded-lg border border-slate-200 px-3 text-sm outline-none focus:border-[#0097A7]"
              >
            </label>
            <label class="block">
              <span class="mb-1 block text-xs font-medium text-slate-600">Sort order</span>
              <input
                v-model.number="formSortOrder"
                type="number"
                class="h-9 w-full rounded-lg border border-slate-200 px-3 text-sm outline-none focus:border-[#0097A7]"
              >
            </label>
            <label class="flex items-end gap-2 pb-1.5">
              <input
                v-model="formShowOnDashboard"
                type="checkbox"
                class="rounded border-slate-300 text-[#0097A7] focus:ring-[#0097A7]"
              >
              <span class="text-sm text-slate-700">Show on mobile dashboard</span>
            </label>
          </div>
        </div>

        <div class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h3 class="text-sm font-semibold text-slate-800">Status include</h3>
          <div class="mt-2 flex flex-wrap gap-1.5">
            <button
              v-for="s in CLIENT_FILTER_STATUSES"
              :key="`inc-${s}`"
              type="button"
              class="rounded-full px-2.5 py-1 text-xs font-medium transition"
              :class="criteria.status_include.includes(s)
                ? 'bg-[#0097A7] text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'"
              @click="toggleStatus('status_include', s)"
            >
              {{ s }}
            </button>
          </div>
          <h3 class="mt-4 text-sm font-semibold text-slate-800">Status exclude</h3>
          <div class="mt-2 flex flex-wrap gap-1.5">
            <button
              v-for="s in CLIENT_FILTER_STATUSES"
              :key="`exc-${s}`"
              type="button"
              class="rounded-full px-2.5 py-1 text-xs font-medium transition"
              :class="criteria.status_exclude.includes(s)
                ? 'bg-red-600 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'"
              @click="toggleStatus('status_exclude', s)"
            >
              {{ s }}
            </button>
          </div>
        </div>

        <div class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h3 class="text-sm font-semibold text-slate-800">Last visit / activity date</h3>
          <div class="mt-2 flex flex-wrap gap-1.5">
            <button
              v-for="mode in (['any', 'relative', 'absolute'] as const)"
              :key="mode"
              type="button"
              class="rounded-full px-2.5 py-1 text-xs font-medium capitalize"
              :class="criteria.date.mode === mode
                ? 'bg-[#0097A7] text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'"
              @click="setDateMode(mode)"
            >
              {{ mode }}
            </button>
          </div>
          <div v-if="criteria.date.mode === 'relative'" class="mt-3 flex flex-wrap gap-1.5">
            <button
              v-for="d in CLIENT_FILTER_RELATIVE_DAYS"
              :key="d"
              type="button"
              class="rounded-full px-2.5 py-1 text-xs font-medium"
              :class="criteria.date.relative_days === d
                ? 'bg-[#0097A7] text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'"
              @click="criteria.date.relative_days = d; previewCount = null"
            >
              {{ d }} days
            </button>
          </div>
          <div v-else-if="criteria.date.mode === 'absolute'" class="mt-3 grid gap-3 sm:grid-cols-2">
            <label class="block">
              <span class="mb-1 block text-xs font-medium text-slate-600">From</span>
              <input
                v-model="criteria.date.from"
                type="date"
                class="h-9 w-full rounded-lg border border-slate-200 px-3 text-sm outline-none focus:border-[#0097A7]"
                @change="previewCount = null"
              >
            </label>
            <label class="block">
              <span class="mb-1 block text-xs font-medium text-slate-600">To</span>
              <input
                v-model="criteria.date.to"
                type="date"
                class="h-9 w-full rounded-lg border border-slate-200 px-3 text-sm outline-none focus:border-[#0097A7]"
                @change="previewCount = null"
              >
            </label>
          </div>
        </div>

        <div class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div class="grid gap-3 sm:grid-cols-2">
            <label class="block">
              <span class="mb-1 block text-xs font-medium text-slate-600">Future appointment</span>
              <select
                v-model="criteria.future_appointment"
                class="h-9 w-full rounded-lg border border-slate-200 bg-white px-2 text-sm outline-none focus:border-[#0097A7]"
                @change="previewCount = null"
              >
                <option
                  v-for="opt in PRESENCE_OPTIONS"
                  :key="opt.value"
                  :value="opt.value"
                >
                  {{ opt.label }}
                </option>
              </select>
            </label>
            <label class="block">
              <span class="mb-1 block text-xs font-medium text-slate-600">Future task</span>
              <select
                v-model="criteria.future_task"
                class="h-9 w-full rounded-lg border border-slate-200 bg-white px-2 text-sm outline-none focus:border-[#0097A7]"
                @change="previewCount = null"
              >
                <option
                  v-for="opt in PRESENCE_OPTIONS"
                  :key="opt.value"
                  :value="opt.value"
                >
                  {{ opt.label }}
                </option>
              </select>
            </label>
            <label class="block">
              <span class="mb-1 block text-xs font-medium text-slate-600">Min total billed (₹)</span>
              <input
                v-model.number="criteria.total_billed_min"
                type="number"
                min="0"
                step="1"
                placeholder="Optional"
                class="h-9 w-full rounded-lg border border-slate-200 px-3 text-sm outline-none focus:border-[#0097A7]"
                @change="previewCount = null"
              >
            </label>
            <label class="block">
              <span class="mb-1 block text-xs font-medium text-slate-600">Min pending payment (₹)</span>
              <input
                v-model.number="criteria.pending_payment_min"
                type="number"
                min="0"
                step="1"
                placeholder="Optional"
                class="h-9 w-full rounded-lg border border-slate-200 px-3 text-sm outline-none focus:border-[#0097A7]"
                @change="previewCount = null"
              >
            </label>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <button
            type="button"
            class="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
            :disabled="previewing"
            @click="runPreview"
          >
            {{ previewing ? 'Counting…' : 'Preview count' }}
          </button>
          <span v-if="previewCount != null" class="text-sm text-slate-600">
            Matches <strong class="text-[#006874]">{{ previewCount }}</strong> patients
            <span v-if="editingId != null && members.length"> (+ manual members)</span>
          </span>
          <div class="ml-auto flex gap-2">
            <button
              type="button"
              class="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
              @click="formOpen = false"
            >
              Close
            </button>
            <button
              type="button"
              class="rounded-lg bg-[#0097A7] px-3 py-2 text-sm font-semibold text-white hover:bg-[#00838f] disabled:opacity-60"
              :disabled="saving"
              @click="saveFilter"
            >
              {{ saving ? 'Saving…' : 'Save' }}
            </button>
          </div>
        </div>

        <div class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h3 class="text-sm font-semibold text-slate-800">Manual members</h3>
          <p class="mt-1 text-xs text-slate-500">
            Always included in this list, regardless of criteria.
            <span v-if="editingId == null" class="text-amber-700"> Save the list first to add members.</span>
          </p>
          <div v-if="editingId != null" class="relative mt-3">
            <input
              v-model="memberSearch"
              type="search"
              placeholder="Search patients to add…"
              class="h-9 w-full rounded-lg border border-slate-200 px-3 text-sm outline-none focus:border-[#0097A7]"
            >
            <ul
              v-if="memberHits.length"
              class="absolute z-10 mt-1 max-h-48 w-full overflow-y-auto rounded-lg border border-slate-200 bg-white shadow-lg"
            >
              <li v-for="hit in memberHits" :key="hit.client_id">
                <button
                  type="button"
                  class="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm hover:bg-slate-50"
                  @click="addMember(hit)"
                >
                  <span class="truncate font-medium text-slate-800">{{ hit.name }}</span>
                  <span class="shrink-0 text-xs text-slate-400">{{ hit.number || '' }}</span>
                </button>
              </li>
            </ul>
            <p v-else-if="memberSearching" class="mt-1 text-xs text-slate-400">Searching…</p>
          </div>
          <p v-if="membersLoading" class="mt-3 text-xs text-slate-400">Loading members…</p>
          <ul v-else class="mt-3 divide-y divide-slate-100">
            <li
              v-for="m in members"
              :key="m.client_id"
              class="flex items-center justify-between gap-2 py-2"
            >
              <div class="min-w-0">
                <p class="truncate text-sm font-medium text-slate-800">{{ m.name }}</p>
                <p class="truncate text-xs text-slate-500">{{ m.number || 'No phone' }}</p>
              </div>
              <button
                type="button"
                class="shrink-0 text-xs text-red-600 hover:underline"
                @click="removeMember(m.client_id)"
              >
                Remove
              </button>
            </li>
            <li v-if="editingId != null && !members.length" class="py-3 text-xs text-slate-400">
              No manual members.
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>
