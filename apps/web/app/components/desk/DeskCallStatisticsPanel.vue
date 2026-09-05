<script setup lang="ts">
import {
  CALL_STATISTICS_VIEW_LABELS,
  callStatisticsViewCount,
  defaultCallDateRange,
  formatCallDateTime,
  formatCallDuration,
  formatCallElapsed,
  formatCallPct,
  type CallPriorityDevice,
  type CallStatisticsReport,
  type CallStatisticsRow,
  type CallStatisticsView,
  type CallTag
} from '~/utils/callStatistics'

const { api } = useApi()
const defaults = defaultCallDateRange()

const devices = ref<CallPriorityDevice[]>([])
const devicesLoading = ref(true)
const deviceId = ref('')
const dateFrom = ref(defaults.dateFrom)
const dateTo = ref(defaults.dateTo)
const view = ref<CallStatisticsView>('all_first')
const page = ref(1)
const applied = ref<{ deviceId: string, dateFrom: string, dateTo: string } | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const report = ref<CallStatisticsReport | null>(null)
const allTags = ref<CallTag[]>([])

const selectedDevice = computed(() =>
  devices.value.find(d => d.device_id === (applied.value?.deviceId ?? deviceId.value))
)
const stats = computed(() => report.value?.stats ?? null)

async function loadTags() {
  try {
    const data = await api<{ tags: CallTag[] }>('/statistics/call-intelligence/tags')
    allTags.value = data.tags || []
  } catch {
    // optional
  }
}

async function loadDevices() {
  devicesLoading.value = true
  error.value = null
  try {
    const data = await api<{ devices: CallPriorityDevice[] }>('/statistics/call-intelligence/priority-devices')
    const list = data.devices || []
    devices.value = list
    if (list.length > 0) {
      const range = defaultCallDateRange()
      const firstId = list[0]!.device_id
      if (!deviceId.value || !list.some(d => d.device_id === deviceId.value)) {
        deviceId.value = firstId
      }
      if (!applied.value?.deviceId || !list.some(d => d.device_id === applied.value?.deviceId)) {
        applied.value = { deviceId: firstId, dateFrom: range.dateFrom, dateTo: range.dateTo }
        dateFrom.value = range.dateFrom
        dateTo.value = range.dateTo
      }
    }
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to load priority phones'
  } finally {
    devicesLoading.value = false
  }
}

async function loadReport() {
  if (!applied.value?.deviceId) return
  loading.value = true
  error.value = null
  try {
    report.value = await api<CallStatisticsReport>('/statistics/call-intelligence/priority-report', {
      query: {
        device: applied.value.deviceId,
        date_from: applied.value.dateFrom,
        date_to: applied.value.dateTo,
        view: view.value,
        page: page.value
      }
    })
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to load call report'
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  if (!deviceId.value) {
    error.value = 'Select a priority inquiry phone.'
    return
  }
  page.value = 1
  applied.value = { deviceId: deviceId.value, dateFrom: dateFrom.value, dateTo: dateTo.value }
}

function applyQuickRange(days: number) {
  const to = new Date()
  const from = new Date()
  from.setDate(from.getDate() - (days - 1))
  dateFrom.value = from.toISOString().slice(0, 10)
  dateTo.value = to.toISOString().slice(0, 10)
  if (deviceId.value) {
    page.value = 1
    applied.value = { deviceId: deviceId.value, dateFrom: dateFrom.value, dateTo: dateTo.value }
  }
}

function patchCall(callId: number, patch: Partial<CallStatisticsRow>) {
  if (!report.value) return
  report.value = {
    ...report.value,
    calls: report.value.calls.map(row => (row.id === callId ? { ...row, ...patch } : row))
  }
}

function typeBadgeClass(type: string) {
  if (type === 'INCOMING') return 'bg-green-100 text-green-800'
  if (type === 'MISSED') return 'bg-red-100 text-red-800'
  return 'bg-slate-100 text-slate-700'
}

function outcomeBadgeClass(outcome: CallStatisticsRow['outcome']) {
  if (outcome === 'answered_first') return 'bg-green-100 text-green-800'
  if (outcome === 'answered_later') return 'bg-cyan-100 text-cyan-900'
  if (outcome === 'we_called_back') return 'bg-indigo-100 text-indigo-800'
  if (outcome === 'called_other_device') return 'bg-amber-100 text-amber-900'
  return 'bg-red-100 text-red-800'
}

function outcomeLabel(outcome: CallStatisticsRow['outcome']) {
  if (outcome === 'answered_first') return 'Answered 1st ring'
  if (outcome === 'answered_later') return 'Answered 2nd+ ring'
  if (outcome === 'we_called_back') return 'We called back'
  if (outcome === 'called_other_device') return 'Called from other device'
  return 'Abandoned'
}

const playBusy = ref<number | null>(null)
const playUrls = ref<Record<number, string>>({})
const playOpen = ref<Record<number, boolean>>({})

async function toggleRecording(row: CallStatisticsRow) {
  if (!row.s3_key) return
  if (playOpen.value[row.id]) {
    playOpen.value = { ...playOpen.value, [row.id]: false }
    return
  }
  playBusy.value = row.id
  try {
    let url = playUrls.value[row.id]
    if (!url) {
      const data = await api<{ url: string }>('/statistics/call-intelligence/recording-presign', {
        query: { s3_key: row.s3_key }
      })
      url = data.url
      playUrls.value = { ...playUrls.value, [row.id]: url }
    }
    playOpen.value = { ...playOpen.value, [row.id]: true }
  } catch {
    // toast optional
  } finally {
    playBusy.value = null
  }
}

watch([applied, view, page], () => {
  if (applied.value?.deviceId) void loadReport()
})

onMounted(() => {
  void loadDevices()
  void loadTags()
})
</script>

<template>
  <div v-if="devicesLoading" class="flex h-full items-center justify-center text-slate-400">
    <UIcon name="i-lucide-loader-circle" class="h-5 w-5 animate-spin" />
  </div>

  <div v-else-if="error && !devices.length" class="flex h-full items-center justify-center p-6">
    <div class="max-w-lg rounded-xl border border-red-200 bg-red-50 p-6 text-center text-sm text-red-800">
      <p class="font-medium">Could not load call statistics</p>
      <p class="mt-2">{{ error }}</p>
      <button type="button" class="mt-4 rounded-lg bg-red-700 px-4 py-2 text-sm font-semibold text-white" @click="loadDevices">
        Retry
      </button>
    </div>
  </div>

  <div v-else-if="!devices.length" class="flex h-full items-center justify-center p-6">
    <div class="max-w-md rounded-xl border border-amber-200 bg-amber-50 p-6 text-center text-sm text-amber-900">
      No priority inquiry phones are configured in Call Intelligence yet. Mark your inquiry phone as
      priority in Call Intelligence admin, then refresh.
    </div>
  </div>

  <div v-else class="h-full overflow-y-auto p-4 lg:p-6">
    <div class="mx-auto max-w-6xl space-y-4">
      <div class="flex items-start justify-between gap-3">
        <div>
          <h2 class="m-0 text-lg font-semibold text-slate-900">Priority device report</h2>
          <p class="mt-1 text-sm text-slate-500">
            First-time inquiry tracking on priority phones
            <template v-if="selectedDevice"> · {{ selectedDevice.device_name }}</template>
          </p>
        </div>
        <div
          v-if="loading && report"
          class="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600"
        >
          <UIcon name="i-lucide-loader-circle" class="h-3 w-3 animate-spin" />
          Updating…
        </div>
      </div>

      <form class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm" @submit.prevent="applyFilters">
        <div class="grid gap-3 md:grid-cols-12 md:items-end">
          <label class="block text-sm md:col-span-4">
            <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">Priority phone</span>
            <select v-model="deviceId" required class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm">
              <option value="">— Select priority phone —</option>
              <option v-for="d in devices" :key="d.device_id" :value="d.device_id">★ {{ d.device_name }}</option>
            </select>
          </label>
          <label class="block text-sm md:col-span-2">
            <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">From</span>
            <input v-model="dateFrom" type="date" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm">
          </label>
          <label class="block text-sm md:col-span-2">
            <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">To</span>
            <input v-model="dateTo" type="date" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm">
          </label>
          <div class="flex flex-wrap gap-2 md:col-span-4">
            <button type="button" class="rounded-md border border-slate-200 px-2 py-1.5 text-xs" @click="applyQuickRange(7)">7d</button>
            <button type="button" class="rounded-md border border-slate-200 px-2 py-1.5 text-xs" @click="applyQuickRange(30)">30d</button>
            <button type="submit" class="rounded-md bg-[#0097A7] px-3 py-1.5 text-xs font-semibold text-white">Apply</button>
          </div>
        </div>
      </form>

      <div v-if="stats" class="grid grid-cols-2 gap-2 lg:grid-cols-4">
        <div class="rounded-xl border border-slate-200 bg-white px-3 py-3 shadow-sm">
          <div class="text-2xl font-bold text-[#0097A7]">{{ stats.first_time }}</div>
          <div class="text-[11px] font-semibold uppercase text-slate-500">First-time</div>
        </div>
        <div class="rounded-xl border border-slate-200 bg-white px-3 py-3 shadow-sm">
          <div class="text-2xl font-bold text-emerald-700">{{ stats.answered_first }}</div>
          <div class="text-[11px] font-semibold uppercase text-slate-500">
            1st ring ({{ formatCallPct(stats.answered_first, stats.first_time) }})
          </div>
        </div>
        <div class="rounded-xl border border-slate-200 bg-white px-3 py-3 shadow-sm">
          <div class="text-2xl font-bold text-amber-700">{{ stats.missed_first }}</div>
          <div class="text-[11px] font-semibold uppercase text-slate-500">Missed 1st</div>
        </div>
        <div class="rounded-xl border border-slate-200 bg-white px-3 py-3 shadow-sm">
          <div class="text-2xl font-bold text-red-700">{{ stats.abandoned }}</div>
          <div class="text-[11px] font-semibold uppercase text-slate-500">Abandoned</div>
        </div>
      </div>

      <div class="flex flex-wrap gap-1 rounded-xl border border-slate-200 bg-white p-2">
        <button
          v-for="(label, key) in CALL_STATISTICS_VIEW_LABELS"
          :key="key"
          type="button"
          class="rounded-md px-2.5 py-1.5 text-xs font-semibold transition"
          :class="view === key ? 'bg-[#0097A7] text-white' : 'text-slate-600 hover:bg-slate-50'"
          @click="view = key as CallStatisticsView; page = 1"
        >
          {{ label }}
          <span v-if="stats" class="opacity-80">({{ callStatisticsViewCount(key as CallStatisticsView, stats) }})</span>
        </button>
      </div>

      <div v-if="error" class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{{ error }}</div>

      <div v-if="loading && !report" class="flex justify-center py-12 text-slate-400">
        <UIcon name="i-lucide-loader-circle" class="h-6 w-6 animate-spin" />
      </div>

      <div v-else-if="report" class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div class="overflow-x-auto">
          <table class="min-w-full text-left text-sm">
            <thead class="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th class="px-3 py-2 font-semibold">When</th>
                <th class="px-3 py-2 font-semibold">Caller</th>
                <th class="px-3 py-2 font-semibold">Type</th>
                <th class="px-3 py-2 font-semibold">Outcome</th>
                <th class="px-3 py-2 font-semibold">Dur</th>
                <th class="px-3 py-2 font-semibold">Recording</th>
                <th class="px-3 py-2 font-semibold">Tags / note</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in report.calls" :key="row.id" class="border-t border-slate-100 align-top">
                <td class="whitespace-nowrap px-3 py-2 text-slate-700">{{ formatCallDateTime(row.call_date) }}</td>
                <td class="px-3 py-2">
                  <div class="font-medium text-slate-800">{{ row.contact_name || 'Unknown' }}</div>
                  <div class="text-xs text-slate-500">{{ row.caller_number }}</div>
                  <div v-if="row.callback_out" class="mt-1 text-[11px] text-indigo-700">
                    Callback {{ formatCallElapsed(row.callback_out.elapsed_seconds) }} later
                  </div>
                  <div v-if="row.retry_in" class="mt-0.5 text-[11px] text-cyan-700">
                    Retry in {{ formatCallElapsed(row.retry_in.elapsed_seconds) }}
                  </div>
                </td>
                <td class="px-3 py-2">
                  <span class="rounded-full px-2 py-0.5 text-xs font-medium" :class="typeBadgeClass(row.call_type)">
                    {{ row.call_type }}
                  </span>
                </td>
                <td class="px-3 py-2">
                  <span class="rounded-full px-2 py-0.5 text-xs font-medium" :class="outcomeBadgeClass(row.outcome)">
                    {{ outcomeLabel(row.outcome) }}
                  </span>
                </td>
                <td class="px-3 py-2 text-slate-700">{{ formatCallDuration(row.duration) }}</td>
                <td class="px-3 py-2">
                  <template v-if="row.s3_key">
                    <button
                      type="button"
                      class="rounded-md border border-green-200 px-2 py-0.5 text-xs font-medium text-green-800 hover:bg-green-50"
                      :disabled="playBusy === row.id"
                      @click="toggleRecording(row)"
                    >
                      {{ playOpen[row.id] ? 'Hide' : 'Play' }}
                    </button>
                    <audio
                      v-if="playOpen[row.id] && playUrls[row.id]"
                      :src="playUrls[row.id]"
                      controls
                      autoplay
                      class="mt-1 block h-10 w-[220px] max-w-[70vw]"
                    />
                  </template>
                  <span v-else class="text-slate-400">—</span>
                </td>
                <td class="px-3 py-2">
                  <DeskCallRecordAnnotations
                    :call-id="row.id"
                    :tags="row.tags || []"
                    :all-tags="allTags"
                    :note="row.note"
                    @update:tags="(tags) => patchCall(row.id, { tags })"
                    @update:all-tags="(tags) => { allTags = tags }"
                    @update:note="(note) => patchCall(row.id, { note })"
                  />
                </td>
              </tr>
              <tr v-if="!report.calls.length">
                <td colspan="7" class="px-3 py-8 text-center text-slate-400">No calls in this view.</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div
          v-if="report.pagination.total_pages > 1"
          class="flex items-center justify-between border-t border-slate-100 px-3 py-2 text-xs text-slate-600"
        >
          <span>Page {{ report.pagination.page }} / {{ report.pagination.total_pages }}</span>
          <div class="flex gap-2">
            <button
              type="button"
              class="rounded-md border border-slate-200 px-2 py-1 disabled:opacity-40"
              :disabled="page <= 1"
              @click="page -= 1"
            >
              Prev
            </button>
            <button
              type="button"
              class="rounded-md border border-slate-200 px-2 py-1 disabled:opacity-40"
              :disabled="page >= report.pagination.total_pages"
              @click="page += 1"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
