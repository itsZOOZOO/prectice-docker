<script setup lang="ts">
import {
  MONTH_OPTIONS,
  shiftMonth,
  type MonthlyAppointmentsOverview,
  type OverviewTab,
  type YearlyAppointmentsOverview
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
const startMonth = ref(1)
const endMonth = ref(12)
const showFilter = ref(false)
const monthYear = ref(now.getFullYear())
const month = ref(now.getMonth() + 1)

const loading = ref(true)
const error = ref<string | null>(null)
const yearlyData = ref<YearlyAppointmentsOverview | null>(null)
const monthlyData = ref<MonthlyAppointmentsOverview | null>(null)

const monthTitle = computed(() => {
  const label = MONTH_OPTIONS.find(m => m.value === month.value)?.label ?? ''
  return `${label} ${monthYear.value}`
})

async function loadYearly() {
  loading.value = true
  error.value = null
  try {
    yearlyData.value = await api<YearlyAppointmentsOverview>('/statistics/appointments-yearly', {
      query: { year: year.value, start_month: startMonth.value, end_month: endMonth.value }
    })
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load appointments'
    yearlyData.value = null
  } finally {
    loading.value = false
  }
}

async function loadMonthly() {
  loading.value = true
  error.value = null
  try {
    monthlyData.value = await api<MonthlyAppointmentsOverview>('/statistics/appointments-monthly', {
      query: { year: monthYear.value, month: month.value }
    })
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load appointments'
    monthlyData.value = null
  } finally {
    loading.value = false
  }
}

watch([tab, year, startMonth, endMonth, monthYear, month], () => {
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
          <button type="button" class="rounded-md bg-white/20 px-3 py-1.5 text-sm font-medium hover:bg-white/30" @click="showFilter = !showFilter">Filter</button>
          <span class="rounded-md bg-white/90 px-3 py-1.5 text-sm font-semibold text-[#0097A7]">
            Total: {{ loading ? '…' : (yearlyData?.total ?? 0) }}
          </span>
          <span class="rounded-md bg-amber-300 px-3 py-1.5 text-sm font-semibold text-amber-950">
            Attend: {{ loading ? '…' : `${yearlyData?.attendance_rate ?? 0}%` }}
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
            Total: {{ loading ? '…' : (monthlyData?.total ?? 0) }}
          </span>
          <span class="rounded-md bg-amber-300 px-3 py-1.5 text-sm font-semibold text-amber-950">
            Attend: {{ loading ? '…' : `${monthlyData?.attendance_rate ?? 0}%` }}
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
        @click="startMonth = 1; endMonth = 12"
      >
        Reset
      </button>
    </div>

    <div v-if="loading" class="flex items-center justify-center py-16 text-slate-400">
      <UIcon name="i-lucide-loader-circle" class="h-6 w-6 animate-spin" />
    </div>
    <div v-else-if="error" class="rounded-xl border border-red-200 bg-red-50 p-6 text-center text-sm text-red-700">
      <p>{{ error }}</p>
      <button type="button" class="mt-3 rounded-lg border border-red-300 px-3 py-1.5 text-xs font-medium" @click="tab === 'yearly' ? loadYearly() : loadMonthly()">Retry</button>
    </div>
    <DeskAppointmentsOverviewReportBody
      v-else-if="tab === 'yearly' && yearlyData"
      :total="yearlyData.total"
      :completed="yearlyData.completed"
      :confirmed="yearlyData.confirmed"
      :cancelled="yearlyData.cancelled"
      :no-show="yearlyData.no_show"
      :pending="yearlyData.pending"
      :attendance-rate="yearlyData.attendance_rate"
      :shown-count="yearlyData.shown_count"
      :flow="yearlyData.monthly_flow.map(m => ({ label: m.label, count: m.count }))"
      flow-title="Monthly appointments"
      :flow-average="yearlyData.average_per_month"
      flow-average-label="Avg / month"
      :doctors="yearlyData.doctors"
      :no-shows="yearlyData.no_shows"
      :rebooked-count="yearlyData.rebooked_count"
      :rebook-rate="yearlyData.rebook_rate"
    />
    <DeskAppointmentsOverviewReportBody
      v-else-if="tab === 'monthly' && monthlyData"
      :total="monthlyData.total"
      :completed="monthlyData.completed"
      :confirmed="monthlyData.confirmed"
      :cancelled="monthlyData.cancelled"
      :no-show="monthlyData.no_show"
      :pending="monthlyData.pending"
      :attendance-rate="monthlyData.attendance_rate"
      :shown-count="monthlyData.shown_count"
      :flow="monthlyData.daily_flow.map(d => ({ label: d.label, count: d.count }))"
      flow-title="Daily appointments"
      :flow-average="monthlyData.average_per_day"
      flow-average-label="Avg / day"
      :doctors="monthlyData.doctors"
      :no-shows="monthlyData.no_shows"
      :rebooked-count="monthlyData.rebooked_count"
      :rebook-rate="monthlyData.rebook_rate"
    />
  </div>
</template>
