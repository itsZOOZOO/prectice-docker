<script setup lang="ts">
import {
  MONTH_OPTIONS,
  shiftMonth,
  type MonthlyCheckinsOverview,
  type OverviewTab,
  type YearlyCheckinsOverview
} from '~/utils/statistics'

const props = withDefaults(defineProps<{
  tab?: OverviewTab
}>(), { tab: undefined })

const emit = defineEmits<{ 'update:tab': [tab: OverviewTab] }>()
const { api } = useApi()
const now = new Date()

const internalTab = ref<OverviewTab>('monthly')
const tab = computed({
  get: () => props.tab ?? internalTab.value,
  set: (v: OverviewTab) => {
    if (props.tab === undefined) internalTab.value = v
    emit('update:tab', v)
  }
})

const year = ref(now.getFullYear())
const monthYear = ref(now.getFullYear())
const month = ref(now.getMonth() + 1)

const loading = ref(true)
const error = ref<string | null>(null)
const yearlyData = ref<YearlyCheckinsOverview | null>(null)
const monthlyData = ref<MonthlyCheckinsOverview | null>(null)

const monthTitle = computed(() => {
  const label = MONTH_OPTIONS.find(m => m.value === month.value)?.label ?? ''
  return `${label} ${monthYear.value}`
})

async function loadYearly() {
  loading.value = true
  error.value = null
  try {
    yearlyData.value = await api<YearlyCheckinsOverview>('/statistics/checkins-yearly', {
      query: { year: year.value }
    })
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load check-ins'
    yearlyData.value = null
  } finally {
    loading.value = false
  }
}

async function loadMonthly() {
  loading.value = true
  error.value = null
  try {
    monthlyData.value = await api<MonthlyCheckinsOverview>('/statistics/checkins-monthly', {
      query: { year: monthYear.value, month: month.value }
    })
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load check-ins'
    monthlyData.value = null
  } finally {
    loading.value = false
  }
}

watch([tab, year, monthYear, month], () => {
  if (tab.value === 'yearly') void loadYearly()
  else void loadMonthly()
}, { immediate: true })
</script>

<template>
  <div class="p-4 md:p-5">
    <div
      class="mb-4 flex flex-col gap-3 rounded-xl bg-gradient-to-br from-[#0097A7] to-[#00838f] p-4 text-white shadow-sm md:flex-row md:items-center md:justify-between"
    >
      <template v-if="tab === 'yearly'">
        <div class="flex items-center justify-center gap-3">
          <button type="button" class="rounded-md bg-white/20 px-3 py-1.5 text-sm font-medium hover:bg-white/30" @click="year -= 1">← Prev</button>
          <h3 class="m-0 min-w-[5.5rem] text-center text-xl font-bold">{{ year }}</h3>
          <button type="button" class="rounded-md bg-white/20 px-3 py-1.5 text-sm font-medium hover:bg-white/30" @click="year += 1">Next →</button>
        </div>
        <div class="flex flex-wrap items-center justify-center gap-2">
          <span class="rounded-md bg-white/90 px-3 py-1.5 text-sm font-semibold text-[#0097A7]">
            Total: {{ loading ? '…' : (yearlyData?.total ?? 0) }}
          </span>
          <span class="rounded-md bg-amber-300 px-3 py-1.5 text-sm font-semibold text-amber-950">
            Avg/day: {{ loading ? '…' : (yearlyData?.average_per_day ?? 0) }}
          </span>
        </div>
      </template>
      <template v-else>
        <div class="flex items-center justify-center gap-3">
          <button
            type="button"
            class="rounded-md bg-white/20 px-3 py-1.5 text-sm font-medium hover:bg-white/30"
            @click="(() => { const p = shiftMonth(monthYear, month, -1); monthYear = p.year; month = p.month })()"
          >← Prev</button>
          <h3 class="m-0 min-w-[7rem] text-center text-xl font-bold">{{ monthTitle }}</h3>
          <button
            type="button"
            class="rounded-md bg-white/20 px-3 py-1.5 text-sm font-medium hover:bg-white/30"
            @click="(() => { const n = shiftMonth(monthYear, month, 1); monthYear = n.year; month = n.month })()"
          >Next →</button>
        </div>
        <div class="flex flex-wrap items-center justify-center gap-2">
          <span class="rounded-md bg-white/90 px-3 py-1.5 text-sm font-semibold text-[#0097A7]">
            Month: {{ loading ? '…' : (monthlyData?.month_total ?? 0) }}
          </span>
          <span class="rounded-md bg-amber-300 px-3 py-1.5 text-sm font-semibold text-amber-950">
            Year: {{ loading ? '…' : (monthlyData?.year_total ?? 0) }}
          </span>
        </div>
      </template>
    </div>

    <div v-if="loading" class="flex items-center justify-center py-16 text-slate-400">
      <UIcon name="i-lucide-loader-circle" class="h-6 w-6 animate-spin" />
    </div>
    <div v-else-if="error" class="rounded-xl border border-red-200 bg-red-50 p-6 text-center text-sm text-red-700">
      <p>{{ error }}</p>
      <button type="button" class="mt-3 rounded-lg border border-red-300 px-3 py-1.5 text-xs font-medium" @click="tab === 'yearly' ? loadYearly() : loadMonthly()">Retry</button>
    </div>
    <DeskCheckinsOverviewReportBody
      v-else-if="tab === 'yearly' && yearlyData"
      mode="yearly"
      :total="yearlyData.total"
      :average-per-day="yearlyData.average_per_day"
      :average-per-month="yearlyData.average_per_month"
      :busiest-weekday="yearlyData.busiest_weekday"
      :busiest-hour-label="yearlyData.busiest_hour_label"
      :flow="yearlyData.monthly_flow.map(m => ({ label: m.label, count: m.count }))"
      flow-title="Monthly check-ins"
      :flow-average="yearlyData.average_per_month"
      flow-average-label="Avg / month"
      :weekday-flow="yearlyData.weekday_flow"
      :hour-flow="yearlyData.hour_flow"
    />
    <DeskCheckinsOverviewReportBody
      v-else-if="tab === 'monthly' && monthlyData"
      mode="monthly"
      :month-total="monthlyData.month_total"
      :year-total="monthlyData.year_total"
      :average-per-day="monthlyData.average_per_day"
      :year-average-per-day="monthlyData.year_average_per_day"
      :busiest-weekday="monthlyData.busiest_weekday"
      :busiest-hour-label="monthlyData.busiest_hour_label"
      :flow="monthlyData.daily_flow.map(d => ({ label: d.label, count: d.count }))"
      flow-title="Daily check-ins"
      :flow-average="monthlyData.average_per_day"
      flow-average-label="Avg / day"
      :weekday-flow="monthlyData.weekday_flow"
      :hour-flow="monthlyData.hour_flow"
    />
  </div>
</template>
