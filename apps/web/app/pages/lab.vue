<script setup lang="ts">
import type { LabCaseFilter, LabCaseListItem, LabCaseSummaryCounts } from '~/utils/labTypes'
import {
  LAB_FILTER_OPTIONS,
  addClinicWorkingDays,
  labCaseStatusColor,
  labCaseStatusLabel,
  todayYmdLocal
} from '~/utils/labTypes'

definePageMeta({ layout: 'mobile' })

const { api } = useApi()
const toast = useToast()
const router = useRouter()
const refreshBadges = inject<() => void>('mobileRefreshBadges', () => {})

const filter = ref<LabCaseFilter>('action_needed')
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

function countFor(key?: keyof LabCaseSummaryCounts) {
  if (!key) return null
  return counts.value[key]
}

function initials(name: string) {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (!parts.length) return '?'
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase()
  return `${parts[0]![0] || ''}${parts[1]![0] || ''}`.toUpperCase()
}

function metaLine(item: LabCaseListItem) {
  return [
    item.case_type,
    item.tooth_numbers ? `#${item.tooth_numbers}` : null
  ].filter(Boolean).join(' · ')
}

function previewDesc(text: string | null) {
  if (!text) return ''
  return text.length > 100 ? `${text.slice(0, 100)}…` : text
}

async function load() {
  loading.value = true
  try {
    const [list, summary] = await Promise.all([
      api<{ cases: LabCaseListItem[] }>('/lab-cases', { query: { filter: filter.value } }),
      api<{ counts: LabCaseSummaryCounts }>('/lab-cases/summary')
    ])
    items.value = list.cases || []
    counts.value = summary.counts
    refreshBadges()
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to load labs', color: 'error' })
    items.value = []
  } finally {
    loading.value = false
  }
}

watch(filter, () => { void load() })
onMounted(load)

function openCase(id: number) {
  detailCaseId.value = id
  detailOpen.value = true
}

function openPatient(clientId: number) {
  void router.push(`/clients/${clientId}`)
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

function onCreated(payload: { case_id: number }) {
  void load()
  openCase(payload.case_id)
}
</script>

<template>
  <div class="flex h-full min-h-0 flex-col bg-[#F0F4F8]">
    <div class="shrink-0 border-b border-slate-200 bg-white px-4 py-3 shadow-sm">
      <div class="mb-3 flex items-center justify-between gap-2">
        <button
          type="button"
          class="inline-flex h-9 items-center gap-1 rounded-lg bg-[#0097A7] px-3 text-sm font-semibold text-white"
          @click="createOpen = true"
        >
          <UIcon name="i-lucide-plus" class="h-4 w-4" />
          New case
        </button>
        <div class="text-right">
          <h1 class="text-lg font-semibold text-[#1C2B35]">
            Lab
          </h1>
          <p
            v-if="counts.action_needed > 0"
            class="text-[11px] font-medium text-[#0097A7]"
          >
            {{ counts.action_needed }} action needed
          </p>
        </div>
      </div>

      <div class="flex gap-1.5 overflow-x-auto pb-0.5 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <button
          v-for="f in LAB_FILTER_OPTIONS"
          :key="f.value"
          type="button"
          class="inline-flex shrink-0 items-center gap-1 rounded-full px-3 py-1.5 text-xs font-semibold transition-colors"
          :class="filter === f.value
            ? 'bg-[#0097A7] text-white'
            : 'bg-slate-100 text-slate-600'"
          @click="filter = f.value"
        >
          {{ f.label }}
          <span
            v-if="countFor(f.summaryKey) != null && (countFor(f.summaryKey) || 0) > 0"
            class="opacity-80"
          >({{ countFor(f.summaryKey) }})</span>
        </button>
      </div>
    </div>

    <div class="min-h-0 flex-1 space-y-3 overflow-y-auto overscroll-y-contain px-4 py-4 pb-24 [-webkit-overflow-scrolling:touch]">
      <p
        v-if="loading"
        class="py-16 text-center text-sm text-slate-400"
      >
        Loading lab cases…
      </p>

      <template v-else>
        <article
          v-for="item in items"
          :key="item.case_id"
          class="rounded-xl border border-slate-200 bg-white p-3 shadow-sm"
          :style="{ borderLeftWidth: '4px', borderLeftColor: labCaseStatusColor(item) }"
        >
          <div class="flex items-start gap-3">
            <button
              type="button"
              class="mt-0.5 shrink-0"
              title="Open patient"
              @click="openPatient(item.client_id)"
            >
              <img
                v-if="item.profile_photo_url"
                :src="item.profile_photo_url"
                :alt="item.client_name"
                class="h-9 w-9 rounded-full object-cover"
              >
              <span
                v-else
                class="inline-flex h-9 w-9 items-center justify-center rounded-full bg-[#e0f7fa] text-xs font-semibold text-[#00838f]"
              >
                {{ initials(item.client_name) }}
              </span>
            </button>

            <div class="min-w-0 flex-1">
              <div class="flex items-start justify-between gap-2">
                <div class="min-w-0">
                  <button
                    type="button"
                    class="block min-w-0 text-left"
                    @click="openPatient(item.client_id)"
                  >
                    <p class="truncate text-sm font-semibold text-[#1C2B35]">
                      {{ item.client_name }}
                    </p>
                  </button>
                  <p class="mt-0.5 truncate text-sm font-medium text-[#0097A7]">
                    {{ item.lab_name }}
                  </p>
                </div>
                <span
                  class="inline-flex shrink-0 rounded px-2 py-0.5 text-[10px] font-semibold text-white"
                  :style="{ background: labCaseStatusColor(item) }"
                >
                  {{ labCaseStatusLabel(item) }}
                </span>
              </div>

              <p
                v-if="metaLine(item)"
                class="mt-1.5 text-xs text-slate-600"
              >
                {{ metaLine(item) }}
              </p>
              <button
                type="button"
                class="mt-0.5 text-[11px] text-slate-400 hover:text-[#0097A7]"
                @click="openCase(item.case_id)"
              >
                {{ item.case_ref }}
              </button>

              <p
                v-if="item.description"
                class="mt-1 text-xs text-slate-500"
              >
                {{ previewDesc(item.description) }}
              </p>

              <div class="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-500">
                <span v-if="item.current_cycle_number > 1">Cycle {{ item.current_cycle_number }}</span>
                <span v-if="item.expected_return_date">
                  Expected {{ item.expected_return_date }}
                  <template v-if="(item.days_overdue || 0) > 0">
                    ({{ item.days_overdue }}d overdue)
                  </template>
                </span>
              </div>

              <div
                v-if="item.status === 'open'"
                class="mt-2.5 flex flex-wrap gap-2"
              >
                <button
                  v-if="item.stage === 'send_pending'"
                  type="button"
                  class="inline-flex items-center rounded-lg bg-[#0097A7] px-2.5 py-1 text-[11px] font-semibold text-white disabled:opacity-60"
                  :disabled="busyCaseId === item.case_id"
                  @click="quickSent(item)"
                >
                  Mark sent
                </button>
                <button
                  v-if="item.stage === 'at_lab'"
                  type="button"
                  class="inline-flex items-center rounded-lg bg-[#0097A7] px-2.5 py-1 text-[11px] font-semibold text-white disabled:opacity-60"
                  :disabled="busyCaseId === item.case_id"
                  @click="quickReceived(item)"
                >
                  Mark received
                </button>
                <button
                  v-if="item.action_category === 'received_no_future_appointment'"
                  type="button"
                  class="inline-flex items-center gap-1 rounded-lg bg-[#0097A7] px-2.5 py-1 text-[11px] font-semibold text-white disabled:opacity-60"
                  :disabled="busyCaseId === item.case_id"
                  @click="bookFor(item)"
                >
                  <UIcon name="i-lucide-calendar" class="h-3.5 w-3.5" />
                  Book appointment
                </button>
                <button
                  v-if="item.stage === 'received'"
                  type="button"
                  class="inline-flex items-center rounded-lg border border-[#0097A7] px-2.5 py-1 text-[11px] font-semibold text-[#0097A7] disabled:opacity-60"
                  :disabled="busyCaseId === item.case_id"
                  @click="startNextStage(item)"
                >
                  Start next stage
                </button>
                <button
                  type="button"
                  class="inline-flex items-center rounded-lg border border-slate-200 px-2.5 py-1 text-[11px] font-semibold text-slate-700 disabled:opacity-60"
                  :disabled="busyCaseId === item.case_id"
                  @click="openCase(item.case_id)"
                >
                  Manage
                </button>
              </div>
              <button
                v-else
                type="button"
                class="mt-2 text-[11px] font-semibold text-[#0097A7]"
                @click="openCase(item.case_id)"
              >
                View case
              </button>
            </div>
          </div>
        </article>

        <p
          v-if="!items.length"
          class="rounded-xl border border-dashed border-slate-300 px-4 py-12 text-center text-sm text-slate-400"
        >
          No lab cases in this view.
        </p>
      </template>
    </div>

    <DeskLabCreateModal
      v-model:open="createOpen"
      @created="onCreated"
    />
    <DeskLabCaseModal
      v-model:open="detailOpen"
      :case-id="detailCaseId"
      @changed="load"
      @book="onDetailBook"
    />
    <DeskBookModal
      v-model:open="bookOpen"
      :client-id="bookPatient?.id"
      :client-name="bookPatient?.name"
      @booked="load"
    />
  </div>
</template>
