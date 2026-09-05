<script setup lang="ts">
import type { InquiryConversionMonthRow } from '~/utils/statistics'

defineProps<{
  mode?: 'yearly' | 'monthly'
  dateRangeLabel: string
  totalClients: number
  totalInquiry: number
  totalConversion: number
  avgConversionPct: number
  monthlyFlow: InquiryConversionMonthRow[]
  conversionStatuses: string[]
}>()
</script>

<template>
  <div class="space-y-4">
    <p class="text-sm text-slate-500">{{ dateRangeLabel }}</p>

    <div class="grid grid-cols-2 gap-2 lg:grid-cols-4">
      <div class="rounded-xl border border-slate-200 bg-white px-3 py-3 shadow-sm">
        <div class="text-2xl font-bold text-[#0097A7]">{{ totalClients }}</div>
        <div class="mt-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
          Total clients
        </div>
      </div>
      <div class="rounded-xl border border-slate-200 bg-white px-3 py-3 shadow-sm">
        <div class="text-2xl font-bold text-amber-700">{{ totalInquiry }}</div>
        <div class="mt-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
          Inquiry
        </div>
      </div>
      <div class="rounded-xl border border-slate-200 bg-white px-3 py-3 shadow-sm">
        <div class="text-2xl font-bold text-emerald-700">{{ totalConversion }}</div>
        <div class="mt-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
          Conversion
        </div>
      </div>
      <div class="rounded-xl border border-slate-200 bg-white px-3 py-3 shadow-sm">
        <div class="text-2xl font-bold text-slate-800">{{ avgConversionPct }}%</div>
        <div class="mt-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
          Avg conversion
        </div>
      </div>
    </div>

    <p class="text-xs text-slate-400">
      Converted statuses: {{ conversionStatuses.join(', ') }}
    </p>

    <section class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div class="mb-2 flex items-center justify-between gap-2">
        <h4 class="m-0 text-sm font-semibold text-slate-800">
          {{ mode === 'monthly' ? 'This month’s conversion rate (%)' : 'Conversion rate by month (%)' }}
        </h4>
        <span class="text-xs font-medium text-slate-500">Avg: {{ avgConversionPct }}%</span>
      </div>
      <DeskStatisticsFlowChart
        :flow="monthlyFlow.map(row => ({
          label: mode === 'yearly' ? row.label.replace(/ \d{4}$/, '') : row.label,
          count: row.conversion_pct
        }))"
        :average="avgConversionPct"
        aria-label="Conversion rate"
        :format-value="(v: number) => `${v}%`"
        value-label="conversion"
        average-label="Avg"
      />
    </section>

    <section class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h4 class="mb-2 text-sm font-semibold text-slate-800">
        {{ mode === 'monthly' ? 'This month’s client counts' : 'Client counts by month' }}
      </h4>
      <DeskStatisticsBarChart
        :points="monthlyFlow.map(row => ({
          label: mode === 'yearly' ? row.label.replace(/ \d{4}$/, '') : row.label,
          count: row.total_clients
        }))"
        aria-label="Client counts"
        value-label="clients"
      />
    </section>

    <section class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div class="border-b border-slate-100 px-4 py-3">
        <h4 class="m-0 text-sm font-semibold text-slate-800">
          {{ mode === 'monthly' ? 'Month summary' : 'Detailed monthly data' }}
        </h4>
      </div>
      <div class="overflow-x-auto">
        <table class="min-w-full text-left text-sm">
          <thead class="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th class="px-3 py-2 font-semibold">Month</th>
              <th class="px-3 py-2 font-semibold">Inquiry</th>
              <th class="px-3 py-2 font-semibold">Converted</th>
              <th class="px-3 py-2 font-semibold">Total</th>
              <th class="px-3 py-2 font-semibold">Conv %</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in monthlyFlow"
              :key="row.month_key"
              class="border-t border-slate-100"
            >
              <td class="px-3 py-2 font-medium text-slate-800">{{ row.label }}</td>
              <td class="px-3 py-2">{{ row.inquiry_count }}</td>
              <td class="px-3 py-2">{{ row.conversion_count }}</td>
              <td class="px-3 py-2">{{ row.total_clients }}</td>
              <td class="px-3 py-2 font-semibold text-emerald-700">{{ row.conversion_pct }}%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
