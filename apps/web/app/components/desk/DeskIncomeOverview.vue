<script setup lang="ts">
import {
  formatInr,
  MONTH_OPTIONS,
  shiftMonth,
  type IncomeYearMode,
  type MonthlyIncomeOverview,
  type OverviewTab,
  type YearlyIncomeOverview
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
const mode = ref<IncomeYearMode>('calendar')
const monthYear = ref(now.getFullYear())
const month = ref(now.getMonth() + 1)

const loading = ref(true)
const error = ref<string | null>(null)
const yearlyData = ref<YearlyIncomeOverview | null>(null)
const monthlyData = ref<MonthlyIncomeOverview | null>(null)

const monthTitle = computed(() => {
  const label = MONTH_OPTIONS.find(m => m.value === month.value)?.label ?? ''
  return `${label} ${monthYear.value}`
})

const yearTitle = computed(() =>
  mode.value === 'financial'
    ? `FY ${year.value}–${String(year.value + 1).slice(-2)}`
    : String(year.value)
)

async function loadYearly() {
  loading.value = true
  error.value = null
  try {
    yearlyData.value = await api<YearlyIncomeOverview>('/statistics/income-yearly', {
      query: { year: year.value, mode: mode.value }
    })
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load yearly income'
    yearlyData.value = null
  } finally {
    loading.value = false
  }
}

async function loadMonthly() {
  loading.value = true
  error.value = null
  try {
    monthlyData.value = await api<MonthlyIncomeOverview>('/statistics/income-monthly', {
      query: { year: monthYear.value, month: month.value }
    })
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load monthly income'
    monthlyData.value = null
  } finally {
    loading.value = false
  }
}

watch(
  [tab, year, mode, monthYear, month],
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
          <h3 class="m-0 min-w-[5.5rem] text-center text-xl font-bold">{{ yearTitle }}</h3>
          <button
            type="button"
            class="rounded-md bg-white/20 px-3 py-1.5 text-sm font-medium hover:bg-white/30"
            @click="year += 1"
          >
            Next →
          </button>
        </div>
        <div class="flex flex-wrap items-center justify-center gap-2">
          <div class="flex gap-1 rounded-lg bg-black/15 p-1">
            <button
              v-for="opt in ([
                { key: 'calendar' as const, label: 'Calendar' },
                { key: 'financial' as const, label: 'Financial' }
              ])"
              :key="opt.key"
              type="button"
              class="rounded-md px-3 py-1.5 text-sm font-semibold transition"
              :class="mode === opt.key ? 'bg-white text-[#0097A7]' : 'text-white/90 hover:bg-white/10'"
              @click="mode = opt.key"
            >
              {{ opt.label }}
            </button>
          </div>
          <span class="rounded-md bg-white/90 px-3 py-1.5 text-sm font-semibold text-[#0097A7]">
            Total: {{ loading ? '…' : formatInr(yearlyData?.total_income ?? 0) }}
          </span>
          <span class="rounded-md bg-amber-300 px-3 py-1.5 text-sm font-semibold text-amber-950">
            Avg: {{ loading ? '…' : formatInr(yearlyData?.average_monthly_income ?? 0) }}
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
            Total: {{ loading ? '…' : formatInr(monthlyData?.total_income ?? 0) }}
          </span>
          <span class="rounded-md bg-amber-300 px-3 py-1.5 text-sm font-semibold text-amber-950">
            {{ loading ? '…' : `${monthlyData?.transaction_count ?? 0} receipts` }}
          </span>
        </div>
      </template>
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
    <DeskYearlyIncomeReportBody
      v-else-if="tab === 'yearly' && yearlyData"
      :total-income="yearlyData.total_income"
      :average-monthly-income="yearlyData.average_monthly_income"
      :significant-months="yearlyData.significant_months"
      :months-in-range="yearlyData.months_in_range"
      :significant-threshold="yearlyData.significant_month_threshold"
      :date-range-label="yearlyData.date_range_label"
      :monthly-flow="yearlyData.monthly_flow"
      :payment-modes="yearlyData.payment_modes"
    />
    <DeskMonthlyIncomeReportBody
      v-else-if="tab === 'monthly' && monthlyData"
      :total-income="monthlyData.total_income"
      :transaction-count="monthlyData.transaction_count"
      :average-per-day="monthlyData.average_per_day"
      :payment-modes="monthlyData.payment_modes"
      :daily-flow="monthlyData.daily_flow"
      :transactions="monthlyData.transactions"
    />
  </div>
</template>
