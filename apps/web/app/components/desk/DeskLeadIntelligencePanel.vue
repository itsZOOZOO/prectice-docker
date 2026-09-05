<script setup lang="ts">
import {
  avgResponseTone,
  contactRateTone,
  currentYmInIst,
  formatLeadDateTime,
  isInquiryOnDuty,
  responseMinutesTone,
  shiftYm,
  toneBadge,
  toneText,
  type LeadIntelligenceDuty,
  type LeadIntelligencePeriod,
  type LeadIntelligenceResponseLog
} from '~/utils/leadIntelligence'

const PERIODS: { id: LeadIntelligencePeriod, label: string }[] = [
  { id: '7d', label: 'Last 7 Days' },
  { id: '15d', label: 'Last 15 Days' },
  { id: '30d', label: 'Last 30 Days' },
  { id: 'month', label: 'This Month' },
  { id: 'custom', label: 'Custom' }
]

const DUTY_OPTIONS: { id: LeadIntelligenceDuty, label: string }[] = [
  { id: 'all', label: 'Both' },
  { id: 'on', label: 'Duty hours only' },
  { id: 'off', label: 'Off-duty only' }
]

const DIST_TILES = [
  { key: 'under_5min' as const, label: '≤ 5 mins', hint: 'Excellent', color: 'emerald' },
  { key: 'between_5_15min' as const, label: '5–15 mins', hint: 'Good', color: 'cyan' },
  { key: 'between_15_30min' as const, label: '15–30 mins', hint: 'Needs work', color: 'amber' },
  { key: 'over_30min' as const, label: '> 30 mins', hint: 'Critical', color: 'red' }
]

const { api } = useApi()

const period = ref<LeadIntelligencePeriod>('7d')
const duty = ref<LeadIntelligenceDuty>('on')
const ym = ref(currentYmInIst())
const customFrom = ref('')
const customTo = ref('')
const appliedCustomFrom = ref('')
const appliedCustomTo = ref('')
const groupOr = ref<number[]>([])
const groupAnd = ref<number[]>([])
const allGroups = ref(false)
const groupsTouched = ref(false)
const initialLoading = ref(true)
const refreshing = ref(false)
const error = ref<string | null>(null)
const data = ref<LeadIntelligenceResponseLog | null>(null)

const availableGroups = computed(() => data.value?.available_groups ?? [])
const summary = computed(() => data.value?.summary)
const contacted = computed(() => summary.value?.leads_contacted ?? 0)
const loading = computed(() => initialLoading.value || refreshing.value)

const contactTone = computed(() => contactRateTone(summary.value?.contact_rate ?? 0))
const avgTone = computed(() => avgResponseTone(summary.value?.avg_response_minutes ?? null))

const donutLegend = computed(() => {
  const cats = summary.value?.response_categories
  const total = contacted.value
  if (!cats || total <= 0) return []
  return [
    { label: '≤ 5 mins', value: cats.under_5min, color: '#198754' },
    { label: '5–15 mins', value: cats.between_5_15min, color: '#0dcaf0' },
    { label: '15–30 mins', value: cats.between_15_30min, color: '#ffc107' },
    { label: '> 30 mins', value: cats.over_30min, color: '#dc3545' }
  ].filter(s => s.value > 0).map(s => ({
    ...s,
    pct: Math.round((s.value / total) * 100)
  }))
})

function tileShell(color: string) {
  const map: Record<string, string> = {
    emerald: 'border-emerald-200 bg-emerald-50 text-emerald-900',
    cyan: 'border-cyan-200 bg-cyan-50 text-cyan-900',
    amber: 'border-amber-200 bg-amber-50 text-amber-900',
    red: 'border-red-200 bg-red-50 text-red-900'
  }
  return map[color] ?? 'border-slate-200 bg-slate-50 text-slate-800'
}

function pillClass(active: boolean) {
  return active
    ? 'rounded-lg bg-slate-900 px-3 py-1.5 text-sm font-medium text-white'
    : 'rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50'
}

async function load() {
  if (period.value === 'custom' && (!appliedCustomFrom.value || !appliedCustomTo.value)) return
  refreshing.value = true
  error.value = null
  try {
    const query: Record<string, string | number | boolean | undefined | null> = {
      period: period.value,
      duty: duty.value,
      limit: 500
    }
    if (period.value === 'month') query.ym = ym.value
    if (period.value === 'custom') {
      query.from = appliedCustomFrom.value
      query.to = appliedCustomTo.value
    }
    if (groupsTouched.value) {
      if (allGroups.value || (groupOr.value.length === 0 && groupAnd.value.length === 0)) {
        query.all_groups = '1'
      }
    }

    // Build with repeated group params via URLSearchParams for arrays
    const params = new URLSearchParams()
    for (const [k, v] of Object.entries(query)) {
      if (v != null && v !== '') params.set(k, String(v))
    }
    if (groupsTouched.value && !allGroups.value) {
      for (const id of groupOr.value) params.append('group_or', String(id))
      for (const id of groupAnd.value) params.append('group_and', String(id))
    }

    const payload = await api<LeadIntelligenceResponseLog>(
      `/statistics/lead-intelligence/response-log?${params.toString()}`
    )
    data.value = payload
    if (!groupsTouched.value) {
      groupOr.value = payload.group_or ?? []
      groupAnd.value = payload.group_and ?? []
      allGroups.value = Boolean(payload.all_groups)
    }
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to load'
  } finally {
    initialLoading.value = false
    refreshing.value = false
  }
}

function applyCustom() {
  appliedCustomFrom.value = customFrom.value
  appliedCustomTo.value = customTo.value
  void load()
}

function toggleOr(id: number) {
  groupsTouched.value = true
  allGroups.value = false
  groupAnd.value = groupAnd.value.filter(x => x !== id)
  groupOr.value = groupOr.value.includes(id)
    ? groupOr.value.filter(x => x !== id)
    : [...groupOr.value, id]
}

function toggleAnd(id: number) {
  groupsTouched.value = true
  allGroups.value = false
  groupOr.value = groupOr.value.filter(x => x !== id)
  groupAnd.value = groupAnd.value.includes(id)
    ? groupAnd.value.filter(x => x !== id)
    : [...groupAnd.value, id]
}

function clearGroups() {
  groupsTouched.value = true
  allGroups.value = true
  groupOr.value = []
  groupAnd.value = []
}

watch([period, duty, ym], () => {
  if (!groupsTouched.value) {
    groupOr.value = []
    groupAnd.value = []
    allGroups.value = false
  }
  if (period.value !== 'custom') void load()
})

watch([groupOr, groupAnd, allGroups], () => {
  if (groupsTouched.value) void load()
}, { deep: true })

onMounted(() => { void load() })
</script>

<template>
  <div class="h-full overflow-y-auto p-4 lg:p-6">
    <div class="mx-auto max-w-6xl space-y-4">
      <div class="flex items-start justify-between gap-3">
        <div>
          <h2 class="m-0 text-lg font-semibold text-slate-900">Lead Intelligence</h2>
          <p class="mt-1 text-sm text-slate-500">
            Response times & contact rate
            <template v-if="data"> · {{ data.period_label }}</template>
          </p>
        </div>
        <div
          v-if="loading && data"
          class="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600"
        >
          <UIcon name="i-lucide-loader-circle" class="h-3 w-3 animate-spin" />
          Updating…
        </div>
      </div>

      <div class="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div class="flex flex-wrap gap-2">
          <button
            v-for="p in PERIODS"
            :key="p.id"
            type="button"
            :class="pillClass(period === p.id)"
            @click="period = p.id"
          >
            {{ p.label }}
          </button>
        </div>
        <div v-if="period === 'month'" class="flex items-center gap-2">
          <button type="button" class="rounded-md border border-slate-200 px-2 py-1 text-sm" @click="ym = shiftYm(ym, -1)">←</button>
          <span class="min-w-[6rem] text-center text-sm font-semibold">{{ ym }}</span>
          <button type="button" class="rounded-md border border-slate-200 px-2 py-1 text-sm" @click="ym = shiftYm(ym, 1)">→</button>
        </div>
        <div v-if="period === 'custom'" class="flex flex-wrap items-end gap-2">
          <label class="text-xs font-medium text-slate-600">
            From
            <input v-model="customFrom" type="date" class="mt-1 block rounded-md border border-slate-200 px-2 py-1.5 text-sm">
          </label>
          <label class="text-xs font-medium text-slate-600">
            To
            <input v-model="customTo" type="date" class="mt-1 block rounded-md border border-slate-200 px-2 py-1.5 text-sm">
          </label>
          <button type="button" class="rounded-md bg-[#0097A7] px-3 py-1.5 text-xs font-semibold text-white" @click="applyCustom">
            Apply
          </button>
        </div>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="d in DUTY_OPTIONS"
            :key="d.id"
            type="button"
            :class="pillClass(duty === d.id)"
            @click="duty = d.id"
          >
            {{ d.label }}
          </button>
        </div>
        <div v-if="availableGroups.length" class="space-y-2">
          <div class="flex items-center justify-between gap-2">
            <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Groups</p>
            <button type="button" class="text-xs font-semibold text-[#0097A7]" @click="clearGroups">All groups</button>
          </div>
          <div class="flex flex-wrap gap-1.5">
            <button
              v-for="g in availableGroups"
              :key="`or-${g.id}`"
              type="button"
              class="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium"
              :style="{
                borderColor: g.color || '#64748b',
                background: groupOr.includes(g.id) ? `${g.color || '#64748b'}33` : '#fff'
              }"
              @click="toggleOr(g.id)"
            >
              <span class="h-2 w-2 rounded-full" :style="{ background: g.color || '#64748b' }" />
              {{ g.name }}{{ g.is_priority ? ' ★' : '' }}
              <span class="text-[10px] opacity-60">OR</span>
            </button>
          </div>
          <div class="flex flex-wrap gap-1.5">
            <button
              v-for="g in availableGroups"
              :key="`and-${g.id}`"
              type="button"
              class="inline-flex items-center gap-1.5 rounded-full border border-dashed px-2.5 py-1 text-xs font-medium"
              :style="{
                borderColor: g.color || '#64748b',
                background: groupAnd.includes(g.id) ? `${g.color || '#64748b'}33` : '#fff'
              }"
              @click="toggleAnd(g.id)"
            >
              <span class="h-2 w-2 rounded-full" :style="{ background: g.color || '#64748b' }" />
              {{ g.name }}
              <span class="text-[10px] opacity-60">AND</span>
            </button>
          </div>
        </div>
      </div>

      <div v-if="error" class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
        {{ error }}
        <button type="button" class="ml-2 font-semibold underline" @click="load">Retry</button>
      </div>

      <div v-if="initialLoading" class="flex justify-center py-16 text-slate-400">
        <UIcon name="i-lucide-loader-circle" class="h-6 w-6 animate-spin" />
      </div>

      <template v-else-if="summary">
        <div class="grid grid-cols-2 gap-2 lg:grid-cols-4">
          <div class="rounded-xl border border-slate-200 bg-white px-3 py-3 shadow-sm">
            <div class="text-2xl font-bold text-[#0097A7]">{{ summary.leads_received }}</div>
            <div class="text-[11px] font-semibold uppercase text-slate-500">Received</div>
          </div>
          <div class="rounded-xl border border-slate-200 bg-white px-3 py-3 shadow-sm">
            <div class="text-2xl font-bold text-slate-800">{{ summary.leads_contacted }}</div>
            <div class="text-[11px] font-semibold uppercase text-slate-500">Contacted</div>
          </div>
          <div class="rounded-xl border border-slate-200 bg-white px-3 py-3 shadow-sm">
            <div class="text-2xl font-bold" :class="toneText(contactTone)">{{ summary.contact_rate }}%</div>
            <div class="text-[11px] font-semibold uppercase text-slate-500">Contact rate</div>
          </div>
          <div class="rounded-xl border border-slate-200 bg-white px-3 py-3 shadow-sm">
            <div class="text-2xl font-bold" :class="toneText(avgTone)">{{ summary.avg_response_label }}</div>
            <div class="text-[11px] font-semibold uppercase text-slate-500">Avg response</div>
          </div>
        </div>

        <div class="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          <div
            v-for="tile in DIST_TILES"
            :key="tile.key"
            class="rounded-xl border px-3 py-3"
            :class="tileShell(tile.color)"
          >
            <div class="text-2xl font-bold">{{ summary.response_categories[tile.key] }}</div>
            <div class="text-xs font-semibold">{{ tile.label }}</div>
            <div class="text-[11px] opacity-80">{{ tile.hint }}</div>
          </div>
        </div>

        <div v-if="donutLegend.length" class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h4 class="mb-3 text-sm font-semibold text-slate-800">Response time mix</h4>
          <div class="flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <div
              class="relative h-52 w-52 shrink-0 rounded-full"
              :style="{ background: `conic-gradient(${donutLegend.map((s, i, arr) => {
                const start = arr.slice(0, i).reduce((a, b) => a + (b.value / contacted) * 360, 0)
                const end = start + (s.value / contacted) * 360
                return `${s.color} ${start}deg ${end}deg`
              }).join(', ')})` }"
            >
              <div class="absolute inset-[22%] flex flex-col items-center justify-center rounded-full bg-white text-center shadow-inner">
                <div class="text-2xl font-semibold text-slate-900">{{ contacted }}</div>
                <div class="text-xs text-slate-500">contacted</div>
              </div>
            </div>
            <ul class="space-y-2 text-sm">
              <li v-for="s in donutLegend" :key="s.label" class="flex items-center gap-2 text-slate-700">
                <span class="h-3 w-3 rounded-sm" :style="{ background: s.color }" />
                <span>{{ s.label }}: <strong>{{ s.value }}</strong> ({{ s.pct }}%)</span>
              </li>
            </ul>
          </div>
        </div>

        <div class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <div class="border-b border-slate-100 px-4 py-3 text-sm font-semibold text-slate-800">
            Leads ({{ data?.rows.length ?? 0 }})
          </div>
          <div class="overflow-x-auto">
            <table class="min-w-full text-left text-sm">
              <thead class="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th class="px-3 py-2 font-semibold">Lead</th>
                  <th class="px-3 py-2 font-semibold">Inquiry</th>
                  <th class="px-3 py-2 font-semibold">First contact</th>
                  <th class="px-3 py-2 font-semibold">Response</th>
                  <th class="px-3 py-2 font-semibold">Groups</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in data?.rows || []" :key="row.id" class="border-t border-slate-100">
                  <td class="px-3 py-2">
                    <div class="font-medium text-slate-800">{{ row.display_name || '—' }}</div>
                    <div class="text-xs text-slate-500">{{ row.phone || '—' }}</div>
                  </td>
                  <td class="whitespace-nowrap px-3 py-2 text-slate-700">{{ formatLeadDateTime(row.created_at) }}</td>
                  <td class="whitespace-nowrap px-3 py-2 text-slate-700">{{ formatLeadDateTime(row.first_contact_date) }}</td>
                  <td class="px-3 py-2">
                    <span
                      class="inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold"
                      :class="toneBadge(responseMinutesTone(row.response_minutes, isInquiryOnDuty(row.inquiry_on_duty)))"
                    >
                      {{ row.response_time_label || 'N/A' }}
                    </span>
                    <div v-if="row.inquiry_on_duty === false" class="mt-0.5 text-[10px] text-slate-400">Off duty</div>
                  </td>
                  <td class="px-3 py-2">
                    <div class="flex flex-wrap gap-1">
                      <span
                        v-for="g in row.groups || []"
                        :key="g.id"
                        class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium text-white"
                        :style="{ background: g.color || '#64748b' }"
                      >
                        {{ g.name }}
                      </span>
                      <span v-if="!(row.groups || []).length" class="text-slate-400">—</span>
                    </div>
                  </td>
                </tr>
                <tr v-if="!(data?.rows || []).length">
                  <td colspan="5" class="px-3 py-8 text-center text-slate-400">No leads in this range.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>
