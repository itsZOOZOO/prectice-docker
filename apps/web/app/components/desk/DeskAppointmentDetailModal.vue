<script setup lang="ts">
import { formatAmPm } from '~/utils/formatTime'

type ApptDetail = {
  appointment_id: number
  appointment_date: string
  appointment_time: string
  end_time?: string | null
  status: string
  name: string
  phone?: string | null
  notes?: string | null
  client_id: number | null
  doctor_id?: number
  doctor_name: string | null
  doctor_color?: string | null
  service_name: string | null
  duration_minutes?: number | null
}

type StatusOpt = { status_id: number, status_name: string, color: string }

const open = defineModel<boolean>('open', { default: false })
const props = withDefaults(defineProps<{
  appointmentId: number | null
  hideOpenPatient?: boolean
}>(), {
  hideOpenPatient: false
})
const emit = defineEmits<{
  updated: []
  edit: [appointmentId: number]
  'open-patient': [clientId: number]
}>()

const { api } = useApi()
const toast = useToast()

const loading = ref(false)
const statusBusy = ref(false)
const deleteBusy = ref(false)
const reminderBusy = ref(false)
const waEnabled = ref(false)
const detail = ref<ApptDetail | null>(null)
const statuses = ref<StatusOpt[]>([])

const menuBusy = computed(() =>
  deleteBusy.value || statusBusy.value || reminderBusy.value || loading.value
)

const isMissed = computed(() => {
  const s = (detail.value?.status || '').toLowerCase()
  return s === 'cancelled' || s === 'no show'
})

const menuItems = computed(() => [[
  {
    label: 'Delete appointment',
    color: 'error' as const,
    icon: 'i-lucide-trash-2',
    disabled: menuBusy.value || !detail.value,
    onSelect: () => { void deleteAppointment() }
  }
]])

watch(
  () => [open.value, props.appointmentId] as const,
  async ([isOpen, id]) => {
    if (!isOpen || !id) {
      if (!isOpen) detail.value = null
      return
    }
    await load(id)
  }
)

async function load(id: number) {
  loading.value = true
  try {
    if (!statuses.value.length) {
      const meta = await api<{ statuses: StatusOpt[] }>('/appointments/meta')
      statuses.value = meta.statuses || []
    }
    try {
      const wa = await api<{ enabled: boolean }>('/settings/whatsapp')
      waEnabled.value = Boolean(wa.enabled)
    } catch {
      waEnabled.value = false
    }
    detail.value = await api<ApptDetail>(`/appointments/${id}`)
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to load', color: 'error' })
    open.value = false
  } finally {
    loading.value = false
  }
}

function formatDateLabel(iso: string) {
  const d = new Date(`${iso}T12:00:00`)
  return d.toLocaleDateString('en-IN', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric'
  })
}

function durationLabel(a: ApptDetail) {
  if (a.duration_minutes && a.duration_minutes > 0) return `${a.duration_minutes}m`
  return null
}

function doctorColor(a: ApptDetail) {
  return a.doctor_color || '#0097A7'
}

function doctorLabel(a: ApptDetail) {
  const name = (a.doctor_name || '').trim()
  if (!name) return '—'
  return /^dr\.?\s/i.test(name) ? name : `Dr. ${name}`
}

function statusBtnClass(name: string, active: boolean) {
  const s = (name || '').toLowerCase()
  if (s.includes('cancel')) {
    return active ? 'bg-slate-600 text-white' : 'bg-slate-100 text-slate-600'
  }
  if (s.includes('no show')) {
    return active ? 'bg-orange-600 text-white' : 'bg-orange-50 text-orange-700'
  }
  if (s.includes('complete')) {
    return active ? 'bg-sky-600 text-white' : 'bg-sky-50 text-sky-700'
  }
  if (s.includes('pending')) {
    return active ? 'bg-amber-600 text-white' : 'bg-amber-50 text-amber-800'
  }
  // Confirmed / default
  return active ? 'bg-emerald-600 text-white' : 'bg-emerald-50 text-emerald-700'
}

async function setStatus(status: string) {
  if (!detail.value || statusBusy.value || deleteBusy.value || reminderBusy.value) return
  if (detail.value.status === status) return
  if (!window.confirm(`Change status to “${status}”?`)) return
  statusBusy.value = true
  try {
    const updated = await api<ApptDetail>(`/appointments/${detail.value.appointment_id}/status`, {
      method: 'PATCH',
      body: { status }
    })
    detail.value = { ...detail.value, ...updated }
    toast.add({ title: `Marked ${status}`, color: 'success' })
    emit('updated')
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Update failed', color: 'error' })
  } finally {
    statusBusy.value = false
  }
}

async function deleteAppointment() {
  if (!detail.value || deleteBusy.value) return
  if (!window.confirm('Delete this appointment? This cannot be undone.')) return
  deleteBusy.value = true
  const id = detail.value.appointment_id
  try {
    await api(`/appointments/${id}`, { method: 'DELETE' })
    toast.add({ title: 'Appointment deleted', color: 'success' })
    open.value = false
    detail.value = null
    emit('updated')
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Delete failed', color: 'error' })
  } finally {
    deleteBusy.value = false
  }
}

async function sendMissedReminder() {
  if (!detail.value || reminderBusy.value || !isMissed.value) return
  if (!waEnabled.value) {
    toast.add({ title: 'WhatsApp not enabled for this clinic', color: 'warning' })
    return
  }
  if (!window.confirm('Send missed appointment WhatsApp reminder to this client?')) return
  reminderBusy.value = true
  try {
    await api(`/appointments/${detail.value.appointment_id}/missed-reminder`, {
      method: 'POST',
      body: {}
    })
    toast.add({ title: 'Missed appointment reminder sent', color: 'success' })
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to send reminder', color: 'error' })
  } finally {
    reminderBusy.value = false
  }
}

function onEdit() {
  if (!detail.value || deleteBusy.value || reminderBusy.value) return
  const id = detail.value.appointment_id
  open.value = false
  emit('edit', id)
}

function openPatient() {
  if (!detail.value?.client_id || deleteBusy.value || props.hideOpenPatient) return
  const id = detail.value.client_id
  open.value = false
  emit('open-patient', id)
}
</script>

<template>
  <UModal
    v-model:open="open"
    :close="false"
    :ui="{ content: 'sm:max-w-md', header: 'flex items-center gap-1.5 p-4 sm:px-6' }"
  >
    <template #header>
      <h2 class="text-base font-semibold text-[var(--ui-text-highlighted)]">
        Appointment
      </h2>
      <div class="ms-auto flex items-center gap-0.5">
        <UDropdownMenu
          v-if="detail || loading"
          :items="menuItems"
          :content="{ align: 'end' }"
        >
          <UButton
            icon="i-lucide-ellipsis-vertical"
            color="neutral"
            variant="ghost"
            square
            :disabled="!detail || deleteBusy"
            :loading="deleteBusy"
            aria-label="More actions"
          />
        </UDropdownMenu>
        <UButton
          icon="i-lucide-x"
          color="neutral"
          variant="ghost"
          square
          aria-label="Close"
          @click="open = false"
        />
      </div>
    </template>

    <template #body>
      <div v-if="loading" class="py-10 text-center text-sm text-slate-400">Loading…</div>
      <div v-else-if="detail" class="space-y-4">
        <div>
          <div class="flex items-start justify-between gap-2">
            <p class="text-lg font-semibold text-[#1C2B35]">{{ detail.name }}</p>
            <span
              class="shrink-0 rounded-full px-2.5 py-0.5 text-xs font-semibold"
              :class="statusBtnClass(detail.status, true)"
            >
              {{ detail.status }}
            </span>
          </div>
          <p class="mt-1 text-sm text-slate-500">{{ formatDateLabel(detail.appointment_date) }}</p>
          <p class="text-sm text-slate-600">
            {{ formatAmPm(detail.appointment_time) }}
            <span v-if="detail.end_time"> – {{ formatAmPm(detail.end_time) }}</span>
            <span v-if="durationLabel(detail)" class="text-slate-400"> · {{ durationLabel(detail) }}</span>
          </p>
        </div>

        <div class="space-y-2 rounded-xl border border-slate-100 bg-slate-50 px-3 py-2.5 text-sm text-slate-600">
          <p v-if="detail.service_name" class="flex justify-between gap-2">
            <span class="text-slate-400">Service</span>
            <span class="text-right font-medium text-[#1C2B35]">{{ detail.service_name }}</span>
          </p>
          <p class="flex items-center justify-between gap-2">
            <span class="text-slate-400">Doctor</span>
            <span class="inline-flex items-center gap-1.5 font-medium text-[#1C2B35]">
              <span
                class="inline-flex h-4 w-4 items-center justify-center rounded-full text-[8px] font-semibold text-white"
                :style="{ background: doctorColor(detail) }"
              >
                {{ doctorLabel(detail).replace(/^Dr\.?\s*/i, '').charAt(0) || 'D' }}
              </span>
              {{ doctorLabel(detail) }}
            </span>
          </p>
          <p v-if="detail.phone" class="flex justify-between gap-2">
            <span class="text-slate-400">Phone</span>
            <span class="font-medium text-[#1C2B35]">{{ detail.phone }}</span>
          </p>
          <p v-if="detail.notes" class="flex justify-between gap-2">
            <span class="text-slate-400">Notes</span>
            <span class="text-right text-[#1C2B35]">{{ detail.notes }}</span>
          </p>
        </div>

        <div>
          <p class="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-400">Status</p>
          <div class="flex flex-wrap gap-1.5">
            <button
              v-for="s in statuses"
              :key="s.status_id"
              type="button"
              class="rounded-full px-2.5 py-1 text-xs font-semibold transition disabled:opacity-50"
              :class="statusBtnClass(s.status_name, detail.status === s.status_name)"
              :disabled="statusBusy || deleteBusy || reminderBusy"
              @click="setStatus(s.status_name)"
            >
              {{ s.status_name }}
            </button>
          </div>
        </div>

        <div class="flex flex-wrap justify-end gap-2 pt-1">
          <UButton
            v-if="isMissed"
            color="success"
            variant="outline"
            :disabled="reminderBusy || deleteBusy || !waEnabled"
            :loading="reminderBusy"
            :title="waEnabled ? 'Send missed appt reminder' : 'WhatsApp not enabled'"
            @click="sendMissedReminder"
          >
            Send reminder
          </UButton>
          <UButton
            v-if="detail.client_id && !hideOpenPatient"
            color="neutral"
            variant="outline"
            :disabled="deleteBusy || reminderBusy"
            @click="openPatient"
          >
            Open patient
          </UButton>
          <UButton
            class="bg-[#0097A7]"
            :disabled="deleteBusy || reminderBusy"
            @click="onEdit"
          >
            Edit
          </UButton>
        </div>
      </div>
    </template>
  </UModal>
</template>
