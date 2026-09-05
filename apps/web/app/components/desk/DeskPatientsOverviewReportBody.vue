<script setup lang="ts">
import {
  LEAD_SOURCE_COLORS,
  statusSummaryClass,
  type ClientsOverviewConversion,
  type FlowChartPoint,
  type YearlyLeadSource,
  type YearlyOverviewClient,
  type YearlyStatusCount
} from '~/utils/statistics'

defineProps<{
  totalClients: number
  statusCounts: YearlyStatusCount[]
  conversion: ClientsOverviewConversion
  leadSources: YearlyLeadSource[]
  flow: FlowChartPoint[]
  flowTitle: string
  flowAverage: number
  flowAverageLabel: string
  listTitle: string
  clients: YearlyOverviewClient[]
}>()

const { openPatient } = useDeskUrl()

function sourceColor(source: string) {
  return LEAD_SOURCE_COLORS[source] || '#94a3b8'
}

function formatCreated(iso: string | null) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      timeZone: 'Asia/Kolkata'
    })
  } catch {
    return iso
  }
}
</script>

<template>
  <div class="space-y-4">
    <div v-if="statusCounts.length" class="flex flex-wrap gap-2">
      <div
        v-for="row in statusCounts"
        :key="row.status"
        class="rounded-lg bg-white px-3 py-2 text-sm shadow-sm"
        :class="statusSummaryClass(row.status)"
      >
        {{ row.status }}: <strong>{{ row.count }}</strong>
      </div>
    </div>

    <div
      v-if="totalClients > 0"
      class="rounded-xl bg-gradient-to-br from-[#0097A7] to-[#00838f] p-5 text-white shadow-sm"
    >
      <div class="flex flex-col gap-4 md:flex-row md:items-center">
        <div>
          <div class="text-4xl font-bold leading-none">{{ conversion.overall_pct }}%</div>
          <div class="mt-1 text-sm opacity-90">Overall conversion</div>
        </div>
        <div class="min-w-0 flex-1">
          <div class="h-2.5 overflow-hidden rounded-full bg-white/25">
            <div
              class="h-full rounded-full bg-white"
              :style="{ width: `${conversion.overall_pct}%` }"
            />
          </div>
          <div class="mt-2 flex flex-wrap gap-4 text-sm opacity-90">
            <span><strong>{{ conversion.converted }}</strong> converted</span>
            <span><strong>{{ conversion.not_converted }}</strong> not converted</span>
            <span><strong>{{ conversion.total }}</strong> total</span>
          </div>
        </div>
      </div>
    </div>

    <div
      v-if="leadSources.length"
      class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm"
    >
      <div class="border-b border-slate-100 px-4 py-2.5 text-sm font-semibold text-slate-800">
        Lead sources
      </div>
      <div class="space-y-3 p-4">
        <div v-for="row in leadSources" :key="row.source">
          <div class="mb-1 flex items-center justify-between text-sm">
            <span class="font-medium text-slate-800">{{ row.source }}</span>
            <span class="text-slate-500">{{ row.total }} · {{ row.conversion_pct }}% conv.</span>
          </div>
          <div class="h-2 overflow-hidden rounded-full bg-slate-100">
            <div
              class="h-full rounded-full"
              :style="{
                width: `${totalClients ? Math.round((row.total / totalClients) * 100) : 0}%`,
                background: sourceColor(row.source)
              }"
            />
          </div>
        </div>
      </div>
      <p class="border-t border-slate-100 px-4 py-2 text-[11px] text-slate-400">
        Lead-source conversion = any status except Inquiry / None / DND
      </p>
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h4 class="mb-2 text-sm font-semibold text-slate-800">{{ flowTitle }}</h4>
      <DeskStatisticsFlowChart
        :flow="flow"
        :average="flowAverage"
        :aria-label="flowTitle"
        value-label="Patients"
        :average-label="flowAverageLabel"
      />
    </div>

    <div class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div class="border-b border-slate-100 px-4 py-2.5 text-sm font-semibold text-slate-800">
        {{ listTitle }}
      </div>
      <div v-if="!clients.length" class="px-4 py-5 text-center text-sm text-slate-500">
        No patients in this range.
      </div>
      <div v-else class="overflow-x-auto">
        <table class="min-w-full text-left text-sm">
          <thead class="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th class="px-3 py-2 font-semibold">Name</th>
              <th class="px-3 py-2 font-semibold">Phone</th>
              <th class="px-3 py-2 font-semibold">Place</th>
              <th class="px-3 py-2 font-semibold">Status</th>
              <th class="px-3 py-2 font-semibold">Added</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in clients"
              :key="row.client_id"
              class="border-t border-slate-100"
            >
              <td class="px-3 py-2">
                <button
                  type="button"
                  class="font-medium text-[#0097A7] hover:underline"
                  @click="openPatient(row.client_id)"
                >
                  {{ row.name }}
                </button>
              </td>
              <td class="px-3 py-2 text-slate-700">{{ row.number || '—' }}</td>
              <td class="px-3 py-2 text-slate-700">{{ row.place || '—' }}</td>
              <td class="px-3 py-2 text-slate-700">{{ row.status || '—' }}</td>
              <td class="whitespace-nowrap px-3 py-2 text-slate-600">
                {{ formatCreated(row.created_at) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
