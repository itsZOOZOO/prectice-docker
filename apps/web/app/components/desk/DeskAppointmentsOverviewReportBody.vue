<script setup lang="ts">
import type {
  AppointmentDoctorBreakdown,
  AppointmentNoShowRow,
  FlowChartPoint
} from '~/utils/statistics'

defineProps<{
  total: number
  completed: number
  confirmed: number
  cancelled: number
  noShow: number
  pending: number
  attendanceRate: number
  shownCount: number
  flow: FlowChartPoint[]
  flowTitle: string
  flowAverage: number
  flowAverageLabel: string
  doctors: AppointmentDoctorBreakdown[]
  noShows: AppointmentNoShowRow[]
  rebookedCount: number
  rebookRate: number
}>()

const { openPatient } = useDeskUrl()

const STAT_CARDS = [
  { key: 'total', label: 'Total booked', color: 'text-[#0097A7]' },
  { key: 'completed', label: 'Completed', color: 'text-blue-700' },
  { key: 'confirmed', label: 'Confirmed', color: 'text-green-700' },
  { key: 'cancelled', label: 'Cancelled', color: 'text-red-700' },
  { key: 'no_show', label: 'No show', color: 'text-orange-700' },
  { key: 'pending', label: 'Pending', color: 'text-amber-700' }
] as const

function formatApptDate(dateStr: string, timeStr: string) {
  try {
    const raw = timeStr ? `${dateStr}T${timeStr}` : dateStr
    const d = new Date(raw.includes('T') ? raw : raw.replace(' ', 'T'))
    if (Number.isNaN(d.getTime())) return dateStr
    return d.toLocaleString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: timeStr ? 'numeric' : undefined,
      minute: timeStr ? '2-digit' : undefined,
      hour12: true,
      timeZone: 'Asia/Kolkata'
    })
  } catch {
    return dateStr
  }
}
</script>

<template>
  <div class="space-y-4">
    <div class="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
      <div
        v-for="card in STAT_CARDS"
        :key="card.key"
        class="rounded-xl border border-slate-200 bg-white px-3 py-3 shadow-sm"
      >
        <div class="text-2xl font-bold leading-none" :class="card.color">
          {{
            card.key === 'total' ? total
            : card.key === 'completed' ? completed
              : card.key === 'confirmed' ? confirmed
                : card.key === 'cancelled' ? cancelled
                  : card.key === 'no_show' ? noShow
                    : pending
          }}
        </div>
        <div class="mt-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
          {{ card.label }}
        </div>
      </div>
    </div>

    <div class="rounded-xl bg-gradient-to-br from-emerald-600 to-emerald-800 p-4 text-white shadow-sm">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div class="text-4xl font-bold leading-none">{{ attendanceRate }}%</div>
          <div class="mt-1 text-sm text-white/90">Attendance rate</div>
        </div>
        <div class="min-w-0 flex-1 sm:max-w-md">
          <div class="h-3.5 overflow-hidden rounded-full bg-black/35 ring-1 ring-white/20">
            <div
              class="h-full rounded-full bg-lime-300 shadow-[0_0_12px_rgba(190,242,100,0.65)] transition-all"
              :style="{ width: `${Math.min(100, Math.max(0, attendanceRate))}%` }"
            />
          </div>
          <p class="mt-2 text-xs text-white/85">
            {{ completed }} completed out of {{ shownCount }} appointments that passed
            <template v-if="noShow > 0">
              · {{ noShow }} no-show{{ noShow === 1 ? '' : 's' }}
            </template>
          </p>
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
        value-label="appointments"
        average-label="Average"
      />
    </section>

    <section class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div class="border-b border-slate-100 px-4 py-3">
        <h4 class="m-0 text-sm font-semibold text-slate-800">Per-doctor breakdown</h4>
      </div>
      <p v-if="!doctors.length" class="px-4 py-6 text-center text-sm text-slate-500">
        No appointments in this period.
      </p>
      <div v-else class="overflow-x-auto">
        <table class="min-w-full text-left text-sm">
          <thead class="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th class="px-3 py-2 font-semibold">Doctor</th>
              <th class="px-3 py-2 font-semibold">Total</th>
              <th class="px-3 py-2 font-semibold">Done</th>
              <th class="px-3 py-2 font-semibold">Conf.</th>
              <th class="px-3 py-2 font-semibold">Cancel</th>
              <th class="px-3 py-2 font-semibold">No show</th>
              <th class="px-3 py-2 font-semibold">Pending</th>
              <th class="px-3 py-2 font-semibold">Attend %</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in doctors"
              :key="`${row.doctor_id ?? 'x'}-${row.doctor_name}`"
              class="border-t border-slate-100"
            >
              <td class="px-3 py-2 font-medium text-slate-800">{{ row.doctor_name }}</td>
              <td class="px-3 py-2">{{ row.total }}</td>
              <td class="px-3 py-2">{{ row.completed }}</td>
              <td class="px-3 py-2">{{ row.confirmed }}</td>
              <td class="px-3 py-2">{{ row.cancelled }}</td>
              <td class="px-3 py-2">{{ row.no_show }}</td>
              <td class="px-3 py-2">{{ row.pending }}</td>
              <td class="px-3 py-2 font-semibold text-emerald-700">{{ row.attendance_rate }}%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 px-4 py-3">
        <h4 class="m-0 text-sm font-semibold text-slate-800">No-shows</h4>
        <span class="text-xs text-slate-500">
          Rebooked {{ rebookedCount }} · {{ rebookRate }}%
        </span>
      </div>
      <p v-if="!noShows.length" class="px-4 py-6 text-center text-sm text-slate-500">
        No no-shows in this period.
      </p>
      <div v-else class="overflow-x-auto">
        <table class="min-w-full text-left text-sm">
          <thead class="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th class="px-3 py-2 font-semibold">Patient</th>
              <th class="px-3 py-2 font-semibold">When</th>
              <th class="px-3 py-2 font-semibold">Doctor</th>
              <th class="px-3 py-2 font-semibold">Service</th>
              <th class="px-3 py-2 font-semibold">Rebooked</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in noShows"
              :key="row.appointment_id"
              class="border-t border-slate-100"
            >
              <td class="px-3 py-2">
                <button
                  v-if="row.client_id"
                  type="button"
                  class="font-medium text-[#0097A7] hover:underline"
                  @click="openPatient(row.client_id)"
                >
                  {{ row.name || 'Patient' }}
                </button>
                <span v-else class="font-medium text-slate-800">{{ row.name || 'Patient' }}</span>
                <div v-if="row.phone" class="text-xs text-slate-500">{{ row.phone }}</div>
              </td>
              <td class="whitespace-nowrap px-3 py-2 text-slate-700">
                {{ formatApptDate(row.appointment_date, row.appointment_time) }}
              </td>
              <td class="px-3 py-2 text-slate-700">{{ row.doctor_name || '—' }}</td>
              <td class="px-3 py-2 text-slate-700">{{ row.service_name || '—' }}</td>
              <td class="px-3 py-2">
                <span
                  class="inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold"
                  :class="row.re_booked
                    ? 'bg-emerald-100 text-emerald-800'
                    : 'bg-slate-100 text-slate-600'"
                >
                  {{ row.re_booked ? 'Yes' : 'No' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
