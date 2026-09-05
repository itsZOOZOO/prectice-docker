<script setup lang="ts">
import {
  formatInr,
  formatReceiptWhen,
  type IncomeDailyFlowPoint,
  type IncomePaymentModeBreakdown,
  type IncomeTransactionRow
} from '~/utils/statistics'

defineProps<{
  totalIncome: number
  transactionCount: number
  averagePerDay: number
  paymentModes: IncomePaymentModeBreakdown[]
  dailyFlow: IncomeDailyFlowPoint[]
  transactions: IncomeTransactionRow[]
}>()

const { openPatient } = useDeskUrl()
</script>

<template>
  <div class="space-y-4">
    <div class="grid grid-cols-1 gap-2 sm:grid-cols-3">
      <div class="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
        <div class="text-2xl font-bold text-[#0097A7]">{{ formatInr(totalIncome) }}</div>
        <div class="mt-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
          Collected
        </div>
      </div>
      <div class="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
        <div class="text-2xl font-bold text-slate-800">{{ transactionCount }}</div>
        <div class="mt-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
          Receipts
        </div>
      </div>
      <div class="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
        <div class="text-2xl font-bold text-emerald-700">{{ formatInr(averagePerDay) }}</div>
        <div class="mt-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
          Avg / day
        </div>
      </div>
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h4 class="mb-2 text-sm font-semibold text-slate-800">Daily collections</h4>
      <DeskStatisticsFlowChart
        :flow="dailyFlow.map(d => ({ label: d.label, count: d.income }))"
        :average="averagePerDay"
        aria-label="Daily income flow"
        :format-value="formatInr"
        value-label="Income"
        average-label="Avg / day"
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
        Transactions
      </div>
      <div v-if="!transactions.length" class="px-4 py-5 text-center text-sm text-slate-500">
        No receipts this month.
      </div>
      <div v-else class="overflow-x-auto">
        <table class="min-w-full text-left text-sm">
          <thead class="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th class="px-3 py-2 font-semibold">Patient</th>
              <th class="px-3 py-2 font-semibold">Amount</th>
              <th class="px-3 py-2 font-semibold">Mode</th>
              <th class="px-3 py-2 font-semibold">Note</th>
              <th class="px-3 py-2 font-semibold">When</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in transactions"
              :key="row.receipt_id"
              class="border-t border-slate-100"
            >
              <td class="px-3 py-2">
                <button
                  v-if="row.client_visible"
                  type="button"
                  class="font-medium text-[#0097A7] hover:underline"
                  @click="openPatient(row.client_id)"
                >
                  {{ row.client_name || `Patient #${row.client_id}` }}
                </button>
                <span v-else class="text-slate-500">
                  {{ row.client_name || `Patient #${row.client_id}` }}
                </span>
              </td>
              <td class="px-3 py-2 font-semibold text-slate-900">{{ formatInr(row.amount) }}</td>
              <td class="px-3 py-2 text-slate-700">{{ row.payment_mode || '—' }}</td>
              <td class="max-w-[12rem] truncate px-3 py-2 text-slate-500">
                {{ row.description || '—' }}
              </td>
              <td class="whitespace-nowrap px-3 py-2 text-slate-600">
                {{ formatReceiptWhen(row.receipt_date) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
