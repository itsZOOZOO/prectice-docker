<script setup lang="ts">
import {
  formatInr,
  type IncomeMonthlyFlowPoint,
  type IncomePaymentModeBreakdown
} from '~/utils/statistics'

defineProps<{
  totalIncome: number
  averageMonthlyIncome: number
  significantMonths: number
  monthsInRange: number
  significantThreshold: number
  dateRangeLabel: string
  monthlyFlow: IncomeMonthlyFlowPoint[]
  paymentModes: IncomePaymentModeBreakdown[]
}>()

function statusBadge(status: IncomeMonthlyFlowPoint['status']) {
  if (status === 'significant') return 'bg-emerald-100 text-emerald-800'
  if (status === 'low') return 'bg-amber-100 text-amber-900'
  return 'bg-slate-100 text-slate-600'
}

function statusLabel(status: IncomeMonthlyFlowPoint['status']) {
  if (status === 'significant') return 'Significant'
  if (status === 'low') return 'Low'
  return 'No income'
}

function significantPct(significantMonths: number, monthsInRange: number) {
  return monthsInRange > 0 ? Math.round((significantMonths / monthsInRange) * 100) : 0
}
</script>

<template>
  <div class="space-y-4">
    <p class="text-sm text-slate-500">{{ dateRangeLabel }}</p>

    <div class="grid grid-cols-1 gap-2 sm:grid-cols-3">
      <div class="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
        <div class="text-2xl font-bold text-[#0097A7]">{{ formatInr(totalIncome) }}</div>
        <div class="mt-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
          Total income
        </div>
      </div>
      <div class="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
        <div class="text-2xl font-bold text-emerald-700">{{ formatInr(averageMonthlyIncome) }}</div>
        <div class="mt-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
          Avg monthly (&gt;{{ formatInr(significantThreshold) }})
        </div>
      </div>
      <div class="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
        <div class="text-2xl font-bold text-amber-700">
          {{ significantMonths }}/{{ monthsInRange }}
        </div>
        <div class="mt-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
          Significant months ({{ significantPct(significantMonths, monthsInRange) }}%)
        </div>
      </div>
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h4 class="mb-2 text-sm font-semibold text-slate-800">Monthly income</h4>
      <DeskStatisticsFlowChart
        :flow="monthlyFlow.map(m => ({ label: m.label, count: m.income }))"
        :average="averageMonthlyIncome"
        aria-label="Monthly income flow"
        :format-value="formatInr"
        value-label="Income"
        average-label="Avg (significant)"
      />
    </div>

    <div class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div class="border-b border-slate-100 px-4 py-2.5 text-sm font-semibold text-slate-800">
        Payment modes
      </div>
      <div v-if="!paymentModes.length" class="px-4 py-5 text-center text-sm text-slate-500">
        No payment mode data.
      </div>
      <div v-else class="overflow-x-auto">
        <table class="min-w-full text-left text-sm">
          <thead class="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th class="px-3 py-2 font-semibold">Mode</th>
              <th class="px-3 py-2 font-semibold">Receipts</th>
              <th class="px-3 py-2 font-semibold">Total</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in paymentModes"
              :key="row.payment_mode"
              class="border-t border-slate-100"
            >
              <td class="px-3 py-2 font-medium text-slate-800">{{ row.payment_mode }}</td>
              <td class="px-3 py-2 text-slate-700">{{ row.count }}</td>
              <td class="px-3 py-2 font-semibold text-slate-900">{{ formatInr(row.total) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div class="border-b border-slate-100 px-4 py-2.5 text-sm font-semibold text-slate-800">
        Month breakdown
      </div>
      <div class="overflow-x-auto">
        <table class="min-w-full text-left text-sm">
          <thead class="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th class="px-3 py-2 font-semibold">Month</th>
              <th class="px-3 py-2 font-semibold">Income</th>
              <th class="px-3 py-2 font-semibold">Status</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in monthlyFlow"
              :key="row.month_key"
              class="border-t border-slate-100"
            >
              <td class="px-3 py-2 text-slate-800">{{ row.label }}</td>
              <td class="px-3 py-2 font-semibold text-slate-900">{{ formatInr(row.income) }}</td>
              <td class="px-3 py-2">
                <span
                  class="inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold"
                  :class="statusBadge(row.status)"
                >
                  {{ statusLabel(row.status) }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
