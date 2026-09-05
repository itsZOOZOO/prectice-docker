<script setup lang="ts">
type Doctor = { doctor_id: number, doctor_name: string }
type Service = { service_id: number, service_name: string, duration_minutes: number }
type ClientOpt = { client_id: number, name: string, number: string | null }

const open = defineModel<boolean>('open', { default: false })
const props = withDefaults(defineProps<{
  clientId?: number | null
  clientName?: string | null
  date?: string | null
  time?: string | null
  doctorId?: number | null
  /** When set, modal loads this appointment and PATCHes on confirm. */
  editAppointmentId?: number | null
}>(), {
  clientId: null,
  clientName: null,
  date: null,
  time: null,
  doctorId: null,
  editAppointmentId: null
})
const emit = defineEmits<{ booked: [], saved: [] }>()
const { api } = useApi()
const toast = useToast()

const step = ref(1)
const entryStep = ref(1)
/** Editing one field from Confirm — pick then return to Confirm (keep other choices). */
const editingFromConfirm = ref(false)
const slotHint = ref('')
const doctors = ref<Doctor[]>([])
const services = ref<Service[]>([])
const clients = ref<ClientOpt[]>([])
const clientQ = ref('')
const slots = ref<string[]>([])
const booking = ref(false)
const waEnabled = ref(false)
const sendWhatsapp = ref(false)
const walkInMode = ref(false)

const isEdit = computed(() => Boolean(props.editAppointmentId))

const form = reactive({
  service_id: null as number | null,
  doctor_id: null as number | null,
  date: new Date().toISOString().slice(0, 10),
  appointment_time: '',
  client_id: null as number | null,
  name: '',
  phone: ''
})

const canSendWa = computed(() => waEnabled.value && Boolean((form.phone || '').trim() || form.client_id))
/** Patient fixed from open chart on new book — skip patient step. Edit still allows Change. */
const hasOpenPatient = computed(() => Boolean(props.clientId) && !isEdit.value)
const canChangePatient = computed(() => isEdit.value || !props.clientId)

const stepLabels = computed(() => {
  const labels = [
    { n: 1, label: 'Service' },
    { n: 2, label: 'Doctor' },
    { n: 3, label: 'Slot' },
    { n: 4, label: 'Patient' },
    { n: 5, label: 'Confirm' }
  ]
  if (hasOpenPatient.value) return labels.filter(l => l.n !== 4)
  return labels
})

const modalTitle = computed(() => (isEdit.value ? 'Edit appointment' : 'Book appointment'))
const confirmLabel = computed(() => (isEdit.value ? 'Save changes' : 'Confirm book'))

const serviceLabel = computed(() =>
  services.value.find(s => s.service_id === form.service_id)?.service_name || '—'
)
const doctorLabel = computed(() =>
  doctors.value.find(d => d.doctor_id === form.doctor_id)?.doctor_name || '—'
)
const whenLabel = computed(() => {
  const datePart = formatBookConfirmDate(form.date)
  if (!form.appointment_time) return `${datePart} · pick a time`
  return `${datePart} · ${formatAmPm(form.appointment_time)}`
})

const filteredClients = computed(() => {
  const q = clientQ.value.trim().toLowerCase()
  if (!q) return clients.value.slice(0, 40)
  return clients.value.filter(c =>
    c.name.toLowerCase().includes(q) || (c.number || '').includes(q)
  ).slice(0, 40)
})

function goAfterSlot() {
  if (hasOpenPatient.value) step.value = 5
  else step.value = 4
}

function finishEditOrContinue(next: number) {
  if (editingFromConfirm.value) {
    editingFromConfirm.value = false
    slotHint.value = ''
    step.value = 5
    return
  }
  step.value = next
}

async function ensureClientsLoaded() {
  if (clients.value.length) return
  const data = await api<{ items: ClientOpt[] }>('/clients', { query: { limit: 200 } })
  clients.value = data.items
}

/** Keep time if still free (2B); otherwise clear and jump to Slot with hint (1A). */
async function afterDoctorOrServiceChange() {
  if (!form.doctor_id) {
    form.appointment_time = ''
    editingFromConfirm.value = true
    step.value = 3
    return
  }
  const keep = form.appointment_time
  const data = await api<{ slots: string[] }>('/appointments/slots', {
    query: {
      on: form.date,
      doctor_id: form.doctor_id,
      service_id: form.service_id || undefined,
      exclude_appointment_id: props.editAppointmentId || undefined
    }
  })
  // Use raw free slots (don't inject current time) so "still free?" is accurate
  slots.value = data.slots
  if (keep && data.slots.includes(keep)) {
    form.appointment_time = keep
    finishEditOrContinue(3)
    return
  }
  form.appointment_time = ''
  slotHint.value = keep ? 'Previous time isn’t free — pick another' : ''
  editingFromConfirm.value = true
  step.value = 3
}

async function editField(n: number) {
  if (n === 4 && !canChangePatient.value) return
  if (n === 4) {
    await ensureClientsLoaded()
    clientQ.value = ''
    walkInMode.value = false
  }
  if (n === 3 && form.doctor_id) {
    await loadSlots(Boolean(form.appointment_time))
  }
  editingFromConfirm.value = true
  slotHint.value = ''
  step.value = n
}

function onStepChipClick(n: number) {
  if (n === step.value) return
  // From Confirm: edit that field and return
  if (step.value === 5 && n < 5) {
    void editField(n)
    return
  }
  // While editing from Confirm — Confirm chip returns without changing
  if (editingFromConfirm.value && n === 5) {
    editingFromConfirm.value = false
    slotHint.value = ''
    step.value = 5
    return
  }
  // While editing from Confirm, jump between fields
  if (editingFromConfirm.value && n < 5) {
    void editField(n)
    return
  }
  // Initial wizard: only jump back to completed steps
  if (!editingFromConfirm.value && n < step.value) {
    step.value = n
  }
}

async function loadSlots(preserveTime = false) {
  if (!form.doctor_id) {
    slots.value = []
    return
  }
  const data = await api<{ slots: string[] }>('/appointments/slots', {
    query: {
      on: form.date,
      doctor_id: form.doctor_id,
      service_id: form.service_id || undefined,
      exclude_appointment_id: props.editAppointmentId || undefined
    }
  })
  slots.value = data.slots
  if (preserveTime && form.appointment_time && !slots.value.includes(form.appointment_time)) {
    slots.value = [form.appointment_time, ...slots.value]
  }
  if (!preserveTime) {
    form.appointment_time = ''
  }
}

watch(open, async (v) => {
  if (!v) return
  form.appointment_time = ''
  form.date = props.date || new Date().toISOString().slice(0, 10)
  clientQ.value = ''
  walkInMode.value = false
  sendWhatsapp.value = false
  editingFromConfirm.value = false
  slotHint.value = ''

  const [meta, wa] = await Promise.all([
    api<{ doctors: Doctor[], services: Service[] }>('/appointments/meta'),
    api<{ enabled: boolean }>('/settings/whatsapp').catch(() => ({ enabled: false }))
  ])
  doctors.value = meta.doctors
  services.value = meta.services
  waEnabled.value = Boolean(wa.enabled)

  if (props.editAppointmentId) {
    try {
      const appt = await api<{
        appointment_id: number
        client_id: number | null
        name: string
        phone: string | null
        appointment_date: string
        appointment_time: string
        doctor_id: number
        service_id: number | null
      }>(`/appointments/${props.editAppointmentId}`)
      form.client_id = appt.client_id
      form.name = appt.name
      form.phone = appt.phone || ''
      form.date = appt.appointment_date
      form.appointment_time = (appt.appointment_time || '').slice(0, 5)
      form.doctor_id = appt.doctor_id
      form.service_id = appt.service_id
      await loadSlots(true)
      entryStep.value = 5
      step.value = 5
      return
    } catch (e: unknown) {
      toast.add({ title: e instanceof Error ? e.message : 'Failed to load appointment', color: 'error' })
      open.value = false
      return
    }
  }

  if (props.clientId) {
    form.client_id = props.clientId
    form.name = props.clientName || ''
    try {
      const c = await api<{ number: string | null }>(`/clients/${props.clientId}`)
      if (c.number) form.phone = c.number
    } catch { /* ignore */ }
  } else {
    form.client_id = null
    form.name = ''
    form.phone = ''
    const data = await api<{ items: ClientOpt[] }>('/clients', { query: { limit: 200 } })
    clients.value = data.items
  }

  sendWhatsapp.value = waEnabled.value && Boolean((form.phone || '').trim() || form.client_id)

  // Day-board empty slot: date + time + doctor known → patient or confirm
  if (props.time && props.doctorId) {
    form.doctor_id = props.doctorId
    form.service_id = meta.services[0]?.service_id ?? null
    form.appointment_time = props.time
    await loadSlots(true)
    entryStep.value = hasOpenPatient.value ? 5 : 4
    step.value = entryStep.value
    return
  }

  // Date + doctor known, pick slot
  if (props.date && props.doctorId) {
    form.doctor_id = props.doctorId
    form.service_id = meta.services[0]?.service_id ?? null
    entryStep.value = 3
    step.value = 3
    await loadSlots(false)
    return
  }

  // Full flow — pick service first (no pre-select)
  form.service_id = null
  form.doctor_id = null
  entryStep.value = 1
  step.value = 1
})

watch(() => [form.phone, form.client_id, waEnabled.value], () => {
  if (!waEnabled.value) {
    sendWhatsapp.value = false
    return
  }
  if (!canSendWa.value) sendWhatsapp.value = false
})

watch(() => [form.doctor_id, form.service_id, form.date], () => {
  if (step.value === 3 && form.doctor_id) loadSlots(Boolean(editingFromConfirm.value && form.appointment_time))
})

function pickService(id: number) {
  form.service_id = id
  if (editingFromConfirm.value) {
    void afterDoctorOrServiceChange()
    return
  }
  step.value = 2
}

function pickDoctor(id: number) {
  form.doctor_id = id
  if (editingFromConfirm.value) {
    void afterDoctorOrServiceChange()
    return
  }
  form.appointment_time = ''
  slotHint.value = ''
  step.value = 3
}

function pickSlot(slot: string) {
  form.appointment_time = slot
  slotHint.value = ''
  if (editingFromConfirm.value) {
    editingFromConfirm.value = false
    step.value = 5
    return
  }
  goAfterSlot()
}

function pickClient(id: number) {
  form.client_id = id
  walkInMode.value = false
  const c = clients.value.find(x => x.client_id === id)
  if (c) {
    form.name = c.name
    form.phone = c.number || ''
  }
  sendWhatsapp.value = false
  editingFromConfirm.value = false
  slotHint.value = ''
  step.value = 5
}

function startWalkIn() {
  form.client_id = null
  form.name = ''
  form.phone = ''
  walkInMode.value = true
  sendWhatsapp.value = false
}

function continueWalkIn() {
  if (!form.name.trim()) return
  sendWhatsapp.value = false
  editingFromConfirm.value = false
  slotHint.value = ''
  step.value = 5
}

function goBack() {
  // Editing a field from Confirm → Back returns to Confirm, keeps prior values
  if (editingFromConfirm.value && step.value !== 5) {
    editingFromConfirm.value = false
    slotHint.value = ''
    step.value = 5
    return
  }
  if (step.value <= entryStep.value) return
  if (step.value === 5 && hasOpenPatient.value) {
    if (entryStep.value >= 4) {
      step.value = entryStep.value
      return
    }
    step.value = 3
    return
  }
  if (step.value === 5 && !hasOpenPatient.value) {
    step.value = 4
    return
  }
  step.value -= 1
}

async function book() {
  if (!form.doctor_id || !form.appointment_time || !form.name.trim()) return
  booking.value = true
  try {
    const payload = {
      client_id: form.client_id,
      doctor_id: form.doctor_id,
      service_id: form.service_id,
      name: form.name,
      phone: form.phone || null,
      appointment_date: form.date,
      appointment_time: form.appointment_time,
      send_whatsapp: sendWhatsapp.value && canSendWa.value
    }
    const result = isEdit.value
      ? await api<{ whatsapp_sent?: boolean, whatsapp_message?: string }>(
        `/appointments/${props.editAppointmentId}`,
        { method: 'PATCH', body: payload }
      )
      : await api<{ whatsapp_sent?: boolean, whatsapp_message?: string }>('/appointments', {
        method: 'POST',
        body: payload
      })

    const doneLabel = isEdit.value ? 'Updated' : 'Booked'
    if (sendWhatsapp.value && canSendWa.value) {
      if (result.whatsapp_sent) {
        toast.add({ title: `${doneLabel} · WhatsApp sent`, color: 'success' })
      } else {
        toast.add({
          title: doneLabel,
          description: result.whatsapp_message || 'WhatsApp failed',
          color: 'warning'
        })
      }
    } else {
      toast.add({ title: isEdit.value ? 'Appointment updated' : 'Appointment booked', color: 'success' })
    }
    open.value = false
    if (isEdit.value) emit('saved')
    else emit('booked')
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
  } finally {
    booking.value = false
  }
}
</script>

<template>
  <UModal v-model:open="open" :title="modalTitle">
    <template #body>
      <div class="flex max-h-[min(70vh,560px)] flex-col">
        <div class="mb-3 flex flex-wrap gap-1.5 text-[11px] font-medium text-slate-400">
          <span
            v-for="(s, i) in stepLabels"
            :key="s.n"
            class="inline-flex items-center gap-1.5"
          >
            <button
              type="button"
              class="rounded-full px-2 py-0.5 transition"
              :class="[
                step === s.n ? 'bg-[#0097A7] text-white' : step > s.n || editingFromConfirm ? 'bg-[#0097A7]/15 text-[#0097A7]' : 'bg-slate-100',
                (step === 5 && s.n < 5) || (editingFromConfirm && s.n !== step) || (!editingFromConfirm && s.n < step)
                  ? 'cursor-pointer hover:ring-1 hover:ring-[#0097A7]/40'
                  : 'cursor-default'
              ]"
              :disabled="s.n === 4 && !canChangePatient"
              @click="onStepChipClick(s.n)"
            >
              {{ s.label }}
            </button>
            <span v-if="i < stepLabels.length - 1" class="text-slate-300">→</span>
          </span>
        </div>

        <p class="mb-3 text-xs text-slate-500">
          <template v-if="step === 1">{{ editingFromConfirm ? 'Change service — other details stay' : 'Tap a service to continue' }}</template>
          <template v-else-if="step === 2">{{ editingFromConfirm ? 'Change doctor — other details stay' : 'Tap a doctor to continue' }}</template>
          <template v-else-if="step === 3">{{ editingFromConfirm ? 'Change date or time' : 'Tap a time slot to continue' }}</template>
          <template v-else-if="step === 4">{{ editingFromConfirm ? 'Change patient' : 'Pick a patient, or walk-in' }}</template>
          <template v-else>{{ isEdit ? 'Review and save — tap Change to edit one field' : 'Review and confirm — tap Change to edit one field' }}</template>
        </p>

        <div class="min-h-0 flex-1 overflow-y-auto pb-2">
          <div v-if="step === 1" class="space-y-2">
            <button
              v-for="s in services"
              :key="s.service_id"
              type="button"
              class="flex w-full items-center justify-between rounded-lg border px-3 py-2.5 text-left text-sm hover:border-[#0097A7] hover:bg-[#0097A7]/5"
              :class="form.service_id === s.service_id ? 'border-[#0097A7] bg-[#0097A7]/10' : 'border-slate-200'"
              @click="pickService(s.service_id)"
            >
              <span>{{ s.service_name }}</span>
              <span class="text-xs text-slate-500">{{ s.duration_minutes }}m</span>
            </button>
          </div>

          <div v-else-if="step === 2" class="space-y-2">
            <button
              v-for="d in doctors"
              :key="d.doctor_id"
              type="button"
              class="flex w-full rounded-lg border px-3 py-2.5 text-left text-sm hover:border-[#0097A7] hover:bg-[#0097A7]/5"
              :class="form.doctor_id === d.doctor_id ? 'border-[#0097A7] bg-[#0097A7]/10' : 'border-slate-200'"
              @click="pickDoctor(d.doctor_id)"
            >
              {{ d.doctor_name }}
            </button>
          </div>

          <div v-else-if="step === 3" class="space-y-3">
            <p
              v-if="slotHint"
              class="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900"
            >
              {{ slotHint }}
            </p>
            <UInput
              :model-value="form.date"
              type="date"
              class="w-full"
              @update:model-value="(v: string) => { form.date = v; form.appointment_time = ''; slotHint = '' }"
            />
            <div v-if="!slots.length" class="text-sm text-slate-500">No free slots this day.</div>
            <div v-else class="flex flex-wrap gap-2">
              <button
                v-for="slot in slots"
                :key="slot"
                type="button"
                class="rounded-lg border px-3 py-2 text-sm hover:border-[#0097A7] hover:bg-[#0097A7] hover:text-white"
                :class="form.appointment_time === slot ? 'border-[#0097A7] bg-[#0097A7] text-white' : 'border-slate-200'"
                @click="pickSlot(slot)"
              >
                {{ formatAmPm(slot) }}
              </button>
            </div>
          </div>

          <div v-else-if="step === 4" class="space-y-3">
            <UFormField label="Search patient">
              <UInput v-model="clientQ" placeholder="Name or phone…" class="w-full" autofocus />
            </UFormField>
            <div class="max-h-44 space-y-1 overflow-y-auto rounded-lg border border-slate-200 p-1">
              <button
                type="button"
                class="flex w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-slate-50"
                :class="walkInMode ? 'bg-[#0097A7]/10 text-[#0097A7]' : ''"
                @click="startWalkIn"
              >
                Walk-in / type name
              </button>
              <button
                v-for="c in filteredClients"
                :key="c.client_id"
                type="button"
                class="flex w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-[#0097A7]/5"
                :class="form.client_id === c.client_id ? 'bg-[#0097A7]/10 text-[#0097A7]' : ''"
                @click="pickClient(c.client_id)"
              >
                {{ c.name }}<span v-if="c.number" class="text-slate-400"> · {{ c.number }}</span>
              </button>
            </div>
            <div v-if="walkInMode" class="space-y-2 rounded-lg border border-dashed border-slate-300 bg-slate-50 p-3">
              <UFormField label="Name" required>
                <UInput v-model="form.name" class="w-full" placeholder="Patient name" />
              </UFormField>
              <UFormField label="Phone">
                <UInput v-model="form.phone" class="w-full" />
              </UFormField>
            </div>
          </div>

          <div v-else class="space-y-3">
            <div class="divide-y divide-slate-200 overflow-hidden rounded-xl border border-slate-200 bg-slate-50 text-sm">
              <div class="flex items-center justify-between gap-3 px-4 py-3">
                <div class="min-w-0">
                  <p class="text-[11px] font-medium uppercase tracking-wide text-slate-400">Patient</p>
                  <p class="truncate font-medium text-[#1C2B35]">{{ form.name || '—' }}</p>
                </div>
                <button
                  v-if="canChangePatient"
                  type="button"
                  class="shrink-0 text-xs font-semibold text-[#0097A7] hover:underline"
                  @click="editField(4)"
                >
                  Change
                </button>
              </div>
              <div class="flex items-center justify-between gap-3 px-4 py-3">
                <div class="min-w-0">
                  <p class="text-[11px] font-medium uppercase tracking-wide text-slate-400">When</p>
                  <p class="font-medium text-[#1C2B35]">{{ whenLabel }}</p>
                </div>
                <button
                  type="button"
                  class="shrink-0 text-xs font-semibold text-[#0097A7] hover:underline"
                  @click="editField(3)"
                >
                  Change
                </button>
              </div>
              <div class="flex items-center justify-between gap-3 px-4 py-3">
                <div class="min-w-0">
                  <p class="text-[11px] font-medium uppercase tracking-wide text-slate-400">Doctor</p>
                  <p class="truncate font-medium text-[#1C2B35]">{{ doctorLabel }}</p>
                </div>
                <button
                  type="button"
                  class="shrink-0 text-xs font-semibold text-[#0097A7] hover:underline"
                  @click="editField(2)"
                >
                  Change
                </button>
              </div>
              <div class="flex items-center justify-between gap-3 px-4 py-3">
                <div class="min-w-0">
                  <p class="text-[11px] font-medium uppercase tracking-wide text-slate-400">Service</p>
                  <p class="truncate font-medium text-[#1C2B35]">{{ serviceLabel }}</p>
                </div>
                <button
                  type="button"
                  class="shrink-0 text-xs font-semibold text-[#0097A7] hover:underline"
                  @click="editField(1)"
                >
                  Change
                </button>
              </div>
            </div>
            <label
              v-if="waEnabled"
              class="flex items-start gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm"
              :class="canSendWa ? 'cursor-pointer' : 'opacity-60'"
            >
              <input
                v-model="sendWhatsapp"
                type="checkbox"
                class="mt-0.5"
                :disabled="!canSendWa"
              >
              <span>
                <span class="font-medium text-[#1C2B35]">Send WhatsApp confirmation</span>
                <span v-if="!canSendWa" class="mt-0.5 block text-xs text-slate-500">Add a phone number to enable</span>
                <span v-else-if="isEdit" class="mt-0.5 block text-xs text-slate-500">Optional — off by default when editing</span>
              </span>
            </label>
          </div>
        </div>

        <!-- Sticky footer — no scroll hunting -->
        <div class="mt-3 flex shrink-0 items-center justify-between gap-2 border-t border-slate-100 pt-3">
          <UButton
            color="neutral"
            variant="ghost"
            :disabled="!editingFromConfirm && step <= entryStep"
            @click="goBack"
          >
            Back
          </UButton>
          <UButton
            v-if="step === 4 && walkInMode"
            class="bg-[#0097A7]"
            :disabled="!form.name.trim()"
            @click="continueWalkIn"
          >
            Continue
          </UButton>
          <UButton
            v-else-if="step === 5"
            class="bg-[#0097A7]"
            :loading="booking"
            :disabled="!form.doctor_id || !form.appointment_time || !form.name.trim()"
            @click="book"
          >
            {{ confirmLabel }}
          </UButton>
          <span v-else class="text-xs text-slate-400">Select to continue</span>
        </div>
      </div>
    </template>
  </UModal>
</template>
