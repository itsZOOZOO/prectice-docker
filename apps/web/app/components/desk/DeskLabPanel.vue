<script setup lang="ts">
import type { LabCaseListItem, LabCaseSummaryCounts, LabCaseFilter } from '~/utils/labTypes'
import {
  LAB_FILTER_OPTIONS,
  addClinicWorkingDays,
  labCaseStatusColor,
  labCaseStatusLabel,
  todayYmdLocal
} from '~/utils/labTypes'

const { api } = useApi()
const toast = useToast()
const { labFilter, setLabFilter, openPatient } = useDeskUrl()
const refreshBadges = inject<() => void>('deskRefreshBadges', () => {})

const items = ref<LabCaseListItem[]>([])
const counts = ref<LabCaseSummaryCounts>({
  action_needed: 0,
  blocked_on_clinic: 0,
  at_lab: 0,
  at_lab_overdue: 0,
  received_no_future_appointment: 0,
  open: 0
})
const loading = ref(false)
const busyCaseId = ref<number | null>(null)
const createOpen = ref(false)
const detailOpen = ref(false)
const detailCaseId = ref<number | null>(null)
const bookOpen = ref(false)
const bookPatient = ref<{ id: number, name: string } | null>(null)

async function load() {
  loading.value = true
  try {
    const [list, summary] = await Promise.all([
      api<{ cases: LabCaseListItem[] }>('/lab-cases', { query: { filter: labFilter.value } }),
      api<{ counts: LabCaseSummaryCounts }>('/lab-cases/summary')
    ])
    items.value = list.cases
    counts.value = summary.counts
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to load labs', color: 'error' })
  } finally {
    loading.value = false
  }
}

watch(labFilter, load)
onMounted(load)

function openCase(id: number) {
  detailCaseId.value = id
  detailOpen.value = true
}

async function quickSent(item: LabCaseListItem) {
  const due = addClinicWorkingDays(todayYmdLocal(), 3)
  if (!window.confirm(
    `Mark ${item.case_ref} (cycle ${item.current_cycle_number}) as sent to ${item.lab_name}?\nExpected return: ${due}`
  )) return
  busyCaseId.value = item.case_id
  try {
    await api(`/lab-cases/${item.case_id}/cycles/${item.current_cycle_number}/stages`, {
      method: 'POST',
      body: {
        stage: 'sent',
        action: 'set',
        expected_return_date: due
      }
    })
    toast.add({ title: 'Marked sent', color: 'success' })
    await load()
    refreshBadges()
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
  } finally {
    busyCaseId.value = null
  }
}

async function quickReceived(item: LabCaseListItem) {
  if (!window.confirm(
    `Mark ${item.case_ref} (cycle ${item.current_cycle_number}) as received from ${item.lab_name}?`
  )) return
  busyCaseId.value = item.case_id
  try {
    await api(`/lab-cases/${item.case_id}/cycles/${item.current_cycle_number}/stages`, {
      method: 'POST',
      body: { stage: 'received', action: 'set' }
    })
    toast.add({ title: 'Marked received', color: 'success' })
    await load()
    refreshBadges()
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
  } finally {
    busyCaseId.value = null
  }
}

async function startNextStage(item: LabCaseListItem) {
  const next = item.current_cycle_number + 1
  if (!window.confirm(
    `Start next stage for ${item.case_ref}?\nThis opens cycle ${next} (send pending again).`
  )) return
  busyCaseId.value = item.case_id
  try {
    await api(`/lab-cases/${item.case_id}/cycles`, { method: 'POST' })
    toast.add({ title: `Stage ${next} started`, color: 'success' })
    await load()
    refreshBadges()
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
  } finally {
    busyCaseId.value = null
  }
}

function bookFor(item: LabCaseListItem) {
  bookPatient.value = { id: item.client_id, name: item.client_name }
  bookOpen.value = true
}

function onDetailBook(payload: { clientId: number, clientName: string }) {
  bookPatient.value = { id: payload.clientId, name: payload.clientName }
  bookOpen.value = true
}

function countFor(key?: keyof LabCaseSummaryCounts) {
  if (!key) return null
  return counts.value[key]
}
</script>

<template>
  <div class="h-full overflow-y-auto p-5 space-y-5">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <p class="text-sm text-slate-500">Dental lab cases — send, track, receive</p>
      <UButton icon="i-lucide-plus" class="bg-[#0097A7]" @click="createOpen = true">New case</UButton>
    </div>

    <div class="flex flex-wrap gap-1">
      <UButton
        v-for="f in LAB_FILTER_OPTIONS"
        :key="f.value"
        size="sm"
        :variant="labFilter === f.value ? 'solid' : 'ghost'"
        :color="labFilter === f.value ? 'primary' : 'neutral'"
        @click="setLabFilter(f.value as LabCaseFilter)"
      >
        {{ f.label }}
        <span v-if="countFor(f.summaryKey) != null" class="ml-1 opacity-70">({{ countFor(f.summaryKey) }})</span>
      </UButton>
    </div>

    <p v-if="loading" class="text-slate-500">Loading…</p>
    <ul v-else class="space-y-3">
      <li v-if="!items.length" class="rounded-2xl border border-dashed border-slate-300 px-4 py-10 text-center text-sm text-slate-500">
        No cases in this filter.
      </li>
      <li
        v-for="item in items"
        :key="item.case_id"
        class="rounded-xl border border-slate-200 bg-white p-3 shadow-sm"
      >
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2">
              <button
                type="button"
                class="text-sm font-semibold text-[#1C2B35] hover:underline"
                @click="openCase(item.case_id)"
              >
                {{ item.case_ref }}
              </button>
              <span
                class="rounded-full px-2 py-0.5 text-[10px] font-medium text-white"
                :style="{ background: labCaseStatusColor(item) }"
              >
                {{ labCaseStatusLabel(item) }}
              </span>
            </div>
            <button
              type="button"
              class="mt-1 text-sm text-[#0097A7] hover:underline"
              @click="openPatient(item.client_id)"
            >
              {{ item.client_name }}
            </button>
            <p class="mt-0.5 text-xs text-slate-500">
              {{ [item.case_type, item.tooth_numbers ? `#${item.tooth_numbers}` : null, item.lab_name].filter(Boolean).join(' · ') }}
            </p>
            <p v-if="item.expected_return_date && item.stage === 'at_lab'" class="mt-0.5 text-xs text-slate-400">
              Expected return: {{ item.expected_return_date }}
            </p>
          </div>
          <div class="flex flex-wrap gap-2">
            <UButton
              v-if="item.stage === 'send_pending' && item.status === 'open'"
              size="xs"
              class="bg-[#0097A7]"
              :loading="busyCaseId === item.case_id"
              @click="quickSent(item)"
            >
              Mark sent
            </UButton>
            <UButton
              v-if="item.stage === 'at_lab' && item.status === 'open'"
              size="xs"
              class="bg-[#0097A7]"
              :loading="busyCaseId === item.case_id"
              @click="quickReceived(item)"
            >
              Mark received
            </UButton>
            <UButton
              v-if="item.action_category === 'received_no_future_appointment'"
              size="xs"
              color="primary"
              variant="soft"
              @click="bookFor(item)"
            >
              Book
            </UButton>
            <UButton
              v-if="item.stage === 'received' && item.status === 'open'"
              size="xs"
              color="primary"
              variant="outline"
              :loading="busyCaseId === item.case_id"
              @click="startNextStage(item)"
            >
              Start next stage
            </UButton>
            <UButton size="xs" color="neutral" variant="outline" @click="openCase(item.case_id)">
              Open
            </UButton>
          </div>
        </div>
      </li>
    </ul>

    <DeskLabCreateModal v-model:open="createOpen" @created="() => { load(); refreshBadges() }" />
    <DeskLabCaseModal
      v-model:open="detailOpen"
      :case-id="detailCaseId"
      @changed="() => { load(); refreshBadges() }"
      @book="onDetailBook"
    />
    <DeskBookModal
      v-model:open="bookOpen"
      :client-id="bookPatient?.id"
      :client-name="bookPatient?.name"
      @booked="() => { load(); refreshBadges() }"
    />
  </div>
</template>
