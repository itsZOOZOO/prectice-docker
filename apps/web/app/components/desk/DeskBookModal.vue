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
}>(), {
  clientId: null,
  clientName: null,
  date: null,
  time: null,
  doctorId: null
})
const emit = defineEmits<{ booked: [] }>()
const { api } = useApi()
const toast = useToast()

const step = ref(1)
const entryStep = ref(1)
const doctors = ref<Doctor[]>([])
const services = ref<Service[]>([])
const clients = ref<ClientOpt[]>([])
const clientQ = ref('')
const slots = ref<string[]>([])
const booking = ref(false)
const waEnabled = ref(false)
const sendWhatsapp = ref(false)
const walkInMode = ref(false)

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
const hasOpenPatient = computed(() => Boolean(props.clientId))

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

async function loadSlots(preserveTime = false) {
  if (!form.doctor_id) {
    slots.value = []
    return
  }
  const data = await api<{ slots: string[] }>('/appointments/slots', {
    query: { on: form.date, doctor_id: form.doctor_id, service_id: form.service_id || undefined }
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

  const [meta, wa] = await Promise.all([
    api<{ doctors: Doctor[], services: Service[] }>('/appointments/meta'),
    api<{ enabled: boolean }>('/settings/whatsapp').catch(() => ({ enabled: false }))
  ])
  doctors.value = meta.doctors
  services.value = meta.services
  waEnabled.value = Boolean(wa.enabled)

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
  if (canSendWa.value && !sendWhatsapp.value) {
    // keep user choice; only force off when can't send
  }
  if (!canSendWa.value) sendWhatsapp.value = false
})

watch(() => [form.doctor_id, form.service_id, form.date], () => {
  if (step.value === 3 && form.doctor_id) loadSlots(false)
})

function pickService(id: number) {
  form.service_id = id
  step.value = 2
}

function pickDoctor(id: number) {
  form.doctor_id = id
  form.appointment_time = ''
  step.value = 3
}

function pickSlot(slot: string) {
  form.appointment_time = slot
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
  sendWhatsapp.value = waEnabled.value && Boolean((form.phone || '').trim())
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
  sendWhatsapp.value = waEnabled.value && Boolean((form.phone || '').trim())
  step.value = 5
}

function goBack() {
  if (step.value <= entryStep.value) return
  if (step.value === 5 && hasOpenPatient.value) {
    // Skip patient step when going back
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
    const result = await api<{ whatsapp_sent?: boolean, whatsapp_message?: string }>('/appointments', {
      method: 'POST',
      body: {
        client_id: form.client_id,
        doctor_id: form.doctor_id,
        service_id: form.service_id,
        name: form.name,
        phone: form.phone || null,
        appointment_date: form.date,
        appointment_time: form.appointment_time,
        send_whatsapp: sendWhatsapp.value && canSendWa.value
      }
    })
    if (sendWhatsapp.value && canSendWa.value) {
      if (result.whatsapp_sent) {
        toast.add({ title: 'Booked · WhatsApp sent', color: 'success' })
      } else {
        toast.add({
          title: 'Booked',
          description: result.whatsapp_message || 'WhatsApp failed',
          color: 'warning'
        })
      }
    } else {
      toast.add({ title: 'Appointment booked', color: 'success' })
    }
    open.value = false
    emit('booked')
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
  } finally {
    booking.value = false
  }
}
</script>

<template>
  <UModal v-model:open="open" title="Book appointment">
    <template #body>
      <div class="flex max-h-[min(70vh,560px)] flex-col">
        <div class="mb-3 flex flex-wrap gap-1.5 text-[11px] font-medium text-slate-400">
          <span
            v-for="(s, i) in stepLabels"
            :key="s.n"
            class="inline-flex items-center gap-1.5"
          >
            <span
              class="rounded-full px-2 py-0.5"
              :class="step === s.n ? 'bg-[#0097A7] text-white' : step > s.n ? 'bg-[#0097A7]/15 text-[#0097A7]' : 'bg-slate-100'"
            >
              {{ s.label }}
            </span>
            <span v-if="i < stepLabels.length - 1" class="text-slate-300">→</span>
          </span>
        </div>

        <p class="mb-3 text-xs text-slate-500">
          <template v-if="step === 1">Tap a service to continue</template>
          <template v-else-if="step === 2">Tap a doctor to continue</template>
          <template v-else-if="step === 3">Tap a time slot to continue</template>
          <template v-else-if="step === 4">Pick a patient, or walk-in</template>
          <template v-else>Review and confirm</template>
        </p>

        <div class="min-h-0 flex-1 overflow-y-auto pb-2">
          <div v-if="step === 1" class="space-y-2">
            <button
              v-for="s in services"
              :key="s.service_id"
              type="button"
              class="flex w-full items-center justify-between rounded-lg border border-slate-200 px-3 py-2.5 text-left text-sm hover:border-[#0097A7] hover:bg-[#0097A7]/5"
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
              class="flex w-full rounded-lg border border-slate-200 px-3 py-2.5 text-left text-sm hover:border-[#0097A7] hover:bg-[#0097A7]/5"
              @click="pickDoctor(d.doctor_id)"
            >
              {{ d.doctor_name }}
            </button>
          </div>

          <div v-else-if="step === 3" class="space-y-3">
            <UInput
              :model-value="form.date"
              type="date"
              class="w-full"
              @update:model-value="(v: string) => { form.date = v; form.appointment_time = '' }"
            />
            <div v-if="!slots.length" class="text-sm text-slate-500">No free slots this day.</div>
            <div v-else class="flex flex-wrap gap-2">
              <button
                v-for="slot in slots"
                :key="slot"
                type="button"
                class="rounded-lg border border-slate-200 px-3 py-2 text-sm hover:border-[#0097A7] hover:bg-[#0097A7] hover:text-white"
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
            <div class="space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm">
              <p><span class="text-slate-500">Patient:</span> {{ form.name }}</p>
              <p><span class="text-slate-500">When:</span> {{ form.date }} · {{ formatAmPm(form.appointment_time) }}</p>
              <p><span class="text-slate-500">Doctor:</span> {{ doctors.find(d => d.doctor_id === form.doctor_id)?.doctor_name }}</p>
              <p><span class="text-slate-500">Service:</span> {{ services.find(s => s.service_id === form.service_id)?.service_name }}</p>
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
              </span>
            </label>
          </div>
        </div>

        <!-- Sticky footer — no scroll hunting -->
        <div class="mt-3 flex shrink-0 items-center justify-between gap-2 border-t border-slate-100 pt-3">
          <UButton
            color="neutral"
            variant="ghost"
            :disabled="step <= entryStep"
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
            @click="book"
          >
            Confirm book
          </UButton>
          <span v-else class="text-xs text-slate-400">Select to continue</span>
        </div>
      </div>
    </template>
  </UModal>
</template>
