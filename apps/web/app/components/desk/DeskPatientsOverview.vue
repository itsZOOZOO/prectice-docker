<script setup lang="ts">
import {
  MONTH_OPTIONS,
  shiftMonth,
  type MonthlyClientsOverview,
  type OverviewTab,
  type YearlyClientsOverview
} from '~/utils/statistics'

const props = withDefaults(defineProps<{
  tab?: OverviewTab
}>(), {
  tab: undefined
})

const emit = defineEmits<{
  'update:tab': [tab: OverviewTab]
}>()

const { api } = useApi()
const now = new Date()

const internalTab = ref<OverviewTab>('yearly')
const tab = computed({
  get: () => props.tab ?? internalTab.value,
  set: (v: OverviewTab) => {
    if (props.tab === undefined) internalTab.value = v
    emit('update:tab', v)
  }
})

const year = ref(now.getFullYear())
const startMonth = ref(1)
const endMonth = ref(12)
const showFilter = ref(false)

const monthYear = ref(now.getFullYear())
const month = ref(now.getMonth() + 1)

const loading = ref(true)
const error = ref<string | null>(null)
const yearlyData = ref<YearlyClientsOverview | null>(null)
const monthlyData = ref<MonthlyClientsOverview | null>(null)

const monthTitle = computed(() => {
  const label = MONTH_OPTIONS.find(m => m.value === month.value)?.label ?? ''
  return `${label} ${monthYear.value}`
})

async function loadYearly() {
  loading.value = true
  error.value = null
  try {
    yearlyData.value = await api<YearlyClientsOverview>('/statistics/clients-yearly', {
      query: {
        year: year.value,
        start_month: startMonth.value,
        end_month: endMonth.value
      }
    })
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load yearly patients'
    yearlyData.value = null
  } finally {
    loading.value = false
  }
}

async function loadMonthly() {
  loading.value = true
  error.value = null
  try {
    monthlyData.value = await api<MonthlyClientsOverview>('/statistics/clients-monthly', {
      query: { year: monthYear.value, month: month.value }
    })
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load monthly patients'
    monthlyData.value = null
  } finally {
    loading.value = false
  }
}

function resetFilter() {
  startMonth.value = 1
  endMonth.value = 12
}

watch(
  [tab, year, startMonth, endMonth, monthYear, month],
  () => {
    if (tab.value === 'yearly') void loadYearly()
    else void loadMonthly()
  },
  { immediate: true }
)
</script>

<template>
  <div class="p-4 md:p-5">
    <div
      class="mb-4 flex flex-col gap-3 rounded-xl bg-gradient-to-br from-[#0097A7] to-[#00838f] p-4 text-white shadow-sm md:flex-row md:items-center md:justify-between"
    >
      <template v-if="tab === 'yearly'">
        <div class="flex items-center justify-center gap-3">
          <button
            type="button"
            class="rounded-md bg-white/20 px-3 py-1.5 text-sm font-medium hover:bg-white/30"
            @click="year -= 1"
          >
            ← Prev
          </button>
          <h3 class="m-0 min-w-[5.5rem] text-center text-xl font-bold">{{ year }}</h3>
          <button
            type="button"
            class="rounded-md bg-white/20 px-3 py-1.5 text-sm font-medium hover:bg-white/30"
            @click="year += 1"
          >
            Next →
          </button>
        </div>
        <div class="flex flex-wrap items-center justify-center gap-2">
          <button
            type="button"
            class="rounded-md bg-white/20 px-3 py-1.5 text-sm font-medium hover:bg-white/30"
            @click="showFilter = !showFilter"
          >
            Filter
          </button>
          <span class="rounded-md bg-white/90 px-3 py-1.5 text-sm font-semibold text-[#0097A7]">
            Total: {{ loading ? '…' : (yearlyData?.total_clients ?? 0) }}
          </span>
          <span class="rounded-md bg-amber-300 px-3 py-1.5 text-sm font-semibold text-amber-950">
            Avg/mo: {{ loading ? '…' : (yearlyData?.average_per_month ?? 0) }}
          </span>
        </div>
      </template>
      <template v-else>
        <div class="flex items-center justify-center gap-3">
          <button
            type="button"
            class="rounded-md bg-white/20 px-3 py-1.5 text-sm font-medium hover:bg-white/30"
            @click="(() => { const p = shiftMonth(monthYear, month, -1); monthYear = p.year; month = p.month })()"
          >
            ← Prev
          </button>
          <h3 class="m-0 min-w-[7rem] text-center text-xl font-bold">{{ monthTitle }}</h3>
          <button
            type="button"
            class="rounded-md bg-white/20 px-3 py-1.5 text-sm font-medium hover:bg-white/30"
            @click="(() => { const n = shiftMonth(monthYear, month, 1); monthYear = n.year; month = n.month })()"
          >
            Next →
          </button>
        </div>
        <div class="flex flex-wrap items-center justify-center gap-2">
          <span class="rounded-md bg-white/90 px-3 py-1.5 text-sm font-semibold text-[#0097A7]">
            Total: {{ loading ? '…' : (monthlyData?.total_clients ?? 0) }}
          </span>
          <span class="rounded-md bg-amber-300 px-3 py-1.5 text-sm font-semibold text-amber-950">
            Avg/day: {{ loading ? '…' : (monthlyData?.average_per_day ?? 0) }}
          </span>
        </div>
      </template>
    </div>

    <div
      v-if="tab === 'yearly' && showFilter"
      class="mb-4 flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white p-3"
    >
      <label class="text-xs font-medium text-slate-600">
        From
        <select v-model.number="startMonth" class="mt-1 block rounded-md border border-slate-200 px-2 py-1.5 text-sm">
          <option v-for="m in MONTH_OPTIONS" :key="m.value" :value="m.value">{{ m.label }}</option>
        </select>
      </label>
      <label class="text-xs font-medium text-slate-600">
        To
        <select v-model.number="endMonth" class="mt-1 block rounded-md border border-slate-200 px-2 py-1.5 text-sm">
          <option v-for="m in MONTH_OPTIONS" :key="m.value" :value="m.value">{{ m.label }}</option>
        </select>
      </label>
      <button
        type="button"
        class="rounded-md border border-slate-200 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
        @click="resetFilter"
      >
        Reset
      </button>
    </div>

    <div v-if="loading" class="flex items-center justify-center py-16 text-slate-400">
      <UIcon name="i-lucide-loader-circle" class="h-6 w-6 animate-spin" />
    </div>
    <div
      v-else-if="error"
      class="rounded-xl border border-red-200 bg-red-50 p-6 text-center text-sm text-red-700"
    >
      <p>{{ error }}</p>
      <button
        type="button"
        class="mt-3 rounded-lg border border-red-300 px-3 py-1.5 text-xs font-medium"
        @click="tab === 'yearly' ? loadYearly() : loadMonthly()"
      >
        Retry
      </button>
    </div>
    <DeskPatientsOverviewReportBody
      v-else-if="tab === 'yearly' && yearlyData"
      :total-clients="yearlyData.total_clients"
      :status-counts="yearlyData.status_counts"
      :conversion="yearlyData.conversion"
      :lead-sources="yearlyData.lead_sources"
      :flow="yearlyData.monthly_flow.map(m => ({ label: m.label, count: m.count }))"
      flow-title="Monthly new patients"
      :flow-average="yearlyData.average_per_month"
      flow-average-label="Avg / month"
      list-title="Patients added"
      :clients="yearlyData.clients"
    />
    <DeskPatientsOverviewReportBody
      v-else-if="tab === 'monthly' && monthlyData"
      :total-clients="monthlyData.total_clients"
      :status-counts="monthlyData.status_counts"
      :conversion="monthlyData.conversion"
      :lead-sources="monthlyData.lead_sources"
      :flow="monthlyData.daily_flow.map(d => ({ label: d.label, count: d.count }))"
      flow-title="Daily new patients"
      :flow-average="monthlyData.average_per_day"
      flow-average-label="Avg / day"
      list-title="Patients added"
      :clients="monthlyData.clients"
    />
  </div>
</template>
