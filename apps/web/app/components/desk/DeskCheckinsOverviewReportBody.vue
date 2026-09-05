<script setup lang="ts">
import type {
  CheckinHourFlow,
  CheckinWeekdayFlow,
  FlowChartPoint
} from '~/utils/statistics'

defineProps<{
  monthTotal?: number
  yearTotal?: number
  total?: number
  averagePerDay: number
  averagePerMonth?: number
  yearAveragePerDay?: number
  busiestWeekday: string | null
  busiestHourLabel: string | null
  flow: FlowChartPoint[]
  flowTitle: string
  flowAverage: number
  flowAverageLabel: string
  weekdayFlow: CheckinWeekdayFlow[]
  hourFlow: CheckinHourFlow[]
  mode: 'yearly' | 'monthly'
}>()
</script>

<template>
  <div class="space-y-4">
    <div class="grid grid-cols-2 gap-2 lg:grid-cols-4">
      <div class="rounded-xl border border-slate-200 bg-white px-3 py-3 shadow-sm">
        <div class="text-2xl font-bold text-[#0097A7]">
          {{ mode === 'monthly' ? monthTotal : total }}
        </div>
        <div class="mt-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
          {{ mode === 'monthly' ? 'This month' : 'Total check-ins' }}
        </div>
      </div>
      <div class="rounded-xl border border-slate-200 bg-white px-3 py-3 shadow-sm">
        <div class="text-2xl font-bold text-slate-800">{{ averagePerDay }}</div>
        <div class="mt-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
          Avg / day
        </div>
      </div>
      <div class="rounded-xl border border-slate-200 bg-white px-3 py-3 shadow-sm">
        <div class="text-2xl font-bold text-emerald-700">
          {{ mode === 'monthly' ? yearTotal : (averagePerMonth ?? 0) }}
        </div>
        <div class="mt-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
          {{ mode === 'monthly' ? 'Year total' : 'Avg / month' }}
        </div>
      </div>
      <div class="rounded-xl border border-slate-200 bg-white px-3 py-3 shadow-sm">
        <div class="text-lg font-bold leading-snug text-amber-700">
          {{ busiestWeekday || '—' }}
          <span v-if="busiestHourLabel" class="text-slate-500"> · {{ busiestHourLabel }}</span>
        </div>
        <div class="mt-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
          Busiest day · hour
        </div>
      </div>
    </div>

    <section class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div class="mb-2 flex items-center justify-between gap-2">
        <h4 class="m-0 text-sm font-semibold text-slate-800">{{ flowTitle }}</h4>
        <span class="text-xs font-medium text-slate-500">
          {{ flowAverageLabel }}: {{ flowAverage }}
        </span>
      </div>
      <DeskStatisticsFlowChart
        :flow="flow"
        :average="flowAverage"
        :aria-label="flowTitle"
        value-label="check-ins"
        average-label="Average"
      />
    </section>

    <section class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h4 class="mb-2 text-sm font-semibold text-slate-800">By weekday</h4>
      <DeskStatisticsBarChart
        :points="weekdayFlow.map(w => ({ label: w.label, count: w.count }))"
        aria-label="Check-ins by weekday"
        value-label="check-ins"
      />
    </section>

    <section class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h4 class="mb-2 text-sm font-semibold text-slate-800">By hour</h4>
      <DeskStatisticsBarChart
        :points="hourFlow.map(h => ({ label: h.label, count: h.count }))"
        aria-label="Check-ins by hour"
        bar-color="#0d9488"
        value-label="check-ins"
      />
    </section>
  </div>
</template>
