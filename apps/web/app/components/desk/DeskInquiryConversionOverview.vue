<script setup lang="ts">
import {
  MONTH_OPTIONS,
  shiftMonth,
  type InquiryConversionOverview,
  type OverviewTab
} from '~/utils/statistics'

const props = withDefaults(defineProps<{
  tab?: OverviewTab
}>(), { tab: undefined })

const emit = defineEmits<{ 'update:tab': [tab: OverviewTab] }>()
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
const monthYear = ref(now.getFullYear())
const month = ref(now.getMonth() + 1)

const loading = ref(true)
const error = ref<string | null>(null)
const data = ref<InquiryConversionOverview | null>(null)

const monthTitle = computed(() => {
  const label = MONTH_OPTIONS.find(m => m.value === month.value)?.label ?? ''
  return `${label} ${monthYear.value}`
})

async function load() {
  loading.value = true
  error.value = null
  try {
    if (tab.value === 'yearly') {
      data.value = await api<InquiryConversionOverview>('/statistics/inquiry-conversion-yearly', {
        query: { year: year.value }
      })
    } else {
      data.value = await api<InquiryConversionOverview>('/statistics/inquiry-conversion-monthly', {
        query: { year: monthYear.value, month: month.value }
      })
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load conversion'
    data.value = null
  } finally {
    loading.value = false
  }
}

watch([tab, year, monthYear, month], () => { void load() }, { immediate: true })
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
            Conv: {{ loading ? '…' : `${data?.avg_conversion_pct ?? 0}%` }}
          </span>
          <span class="rounded-md bg-amber-300 px-3 py-1.5 text-sm font-semibold text-amber-950">
            {{ loading ? '…' : `${data?.total_conversion ?? 0} / ${data?.total_clients ?? 0}` }}
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
            Conv: {{ loading ? '…' : `${data?.avg_conversion_pct ?? 0}%` }}
          </span>
          <span class="rounded-md bg-amber-300 px-3 py-1.5 text-sm font-semibold text-amber-950">
            {{ loading ? '…' : `${data?.total_conversion ?? 0} / ${data?.total_clients ?? 0}` }}
          </span>
        </div>
      </template>
    </div>

    <div v-if="loading" class="flex items-center justify-center py-16 text-slate-400">
      <UIcon name="i-lucide-loader-circle" class="h-6 w-6 animate-spin" />
    </div>
    <div v-else-if="error" class="rounded-xl border border-red-200 bg-red-50 p-6 text-center text-sm text-red-700">
      <p>{{ error }}</p>
      <button type="button" class="mt-3 rounded-lg border border-red-300 px-3 py-1.5 text-xs font-medium" @click="load()">Retry</button>
    </div>
    <DeskInquiryConversionReportBody
      v-else-if="data"
      :mode="tab"
      :date-range-label="data.date_range_label"
      :total-clients="data.total_clients"
      :total-inquiry="data.total_inquiry"
      :total-conversion="data.total_conversion"
      :avg-conversion-pct="data.avg_conversion_pct"
      :monthly-flow="data.monthly_flow"
      :conversion-statuses="data.conversion_statuses"
    />
  </div>
</template>
