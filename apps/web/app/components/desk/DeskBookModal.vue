<script setup lang="ts">
type Doctor = { doctor_id: number, doctor_name: string }
type Service = { service_id: number, service_name: string, duration_minutes: number }
type ClientOpt = { client_id: number, name: string, number: string | null }

const open = defineModel<boolean>('open', { default: false })
const props = defineProps<{ clientId?: number | null, clientName?: string | null }>()
const emit = defineEmits<{ booked: [] }>()
const { api } = useApi()
const toast = useToast()

const step = ref(1)
const doctors = ref<Doctor[]>([])
const services = ref<Service[]>([])
const clients = ref<ClientOpt[]>([])
const slots = ref<string[]>([])
const booking = ref(false)

const form = reactive({
  service_id: null as number | null,
  doctor_id: null as number | null,
  date: new Date().toISOString().slice(0, 10),
  appointment_time: '',
  client_id: null as number | null,
  name: '',
  phone: ''
})

watch(open, async (v) => {
  if (!v) return
  step.value = 1
  form.appointment_time = ''
  const meta = await api<{ doctors: Doctor[], services: Service[] }>('/appointments/meta')
  doctors.value = meta.doctors
  services.value = meta.services
  form.doctor_id = meta.doctors[0]?.doctor_id ?? null
  form.service_id = meta.services[0]?.service_id ?? null
  if (props.clientId) {
    form.client_id = props.clientId
    form.name = props.clientName || ''
  } else {
    const data = await api<{ items: ClientOpt[] }>('/clients', { query: { limit: 100 } })
    clients.value = data.items
  }
})

async function loadSlots() {
  if (!form.doctor_id) return
  const data = await api<{ slots: string[] }>('/appointments/slots', {
    query: { on: form.date, doctor_id: form.doctor_id, service_id: form.service_id || undefined }
  })
  slots.value = data.slots
  if (!slots.value.includes(form.appointment_time)) form.appointment_time = slots.value[0] || ''
}

watch(() => [form.doctor_id, form.service_id, form.date, step.value], () => {
  if (step.value === 3) loadSlots()
})

function pickClient(id: number | null) {
  form.client_id = id
  const c = clients.value.find(x => x.client_id === id)
  if (c) {
    form.name = c.name
    form.phone = c.number || ''
  }
}

async function book() {
  if (!form.doctor_id || !form.appointment_time || !form.name.trim()) return
  booking.value = true
  try {
    await api('/appointments', {
      method: 'POST',
      body: {
        client_id: form.client_id,
        doctor_id: form.doctor_id,
        service_id: form.service_id,
        name: form.name,
        phone: form.phone || null,
        appointment_date: form.date,
        appointment_time: form.appointment_time
      }
    })
    toast.add({ title: 'Appointment booked', color: 'success' })
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
      <div class="mb-4 flex gap-2 text-xs font-medium text-slate-500">
        <span :class="step >= 1 ? 'text-[#0097A7]' : ''">1 Service</span>
        <span>→</span>
        <span :class="step >= 2 ? 'text-[#0097A7]' : ''">2 Doctor</span>
        <span>→</span>
        <span :class="step >= 3 ? 'text-[#0097A7]' : ''">3 Slot</span>
        <span>→</span>
        <span :class="step >= 4 ? 'text-[#0097A7]' : ''">4 Patient</span>
        <span>→</span>
        <span :class="step >= 5 ? 'text-[#0097A7]' : ''">5 Confirm</span>
      </div>

      <div v-if="step === 1" class="space-y-2">
        <button
          v-for="s in services"
          :key="s.service_id"
          type="button"
          class="flex w-full items-center justify-between rounded-lg border px-3 py-2.5 text-left text-sm"
          :class="form.service_id === s.service_id ? 'border-[#0097A7] bg-[#0097A7]/10 text-[#0097A7]' : 'border-slate-200 hover:bg-slate-50'"
          @click="form.service_id = s.service_id"
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
          class="flex w-full rounded-lg border px-3 py-2.5 text-left text-sm"
          :class="form.doctor_id === d.doctor_id ? 'border-[#0097A7] bg-[#0097A7]/10 text-[#0097A7]' : 'border-slate-200 hover:bg-slate-50'"
          @click="form.doctor_id = d.doctor_id"
        >
          {{ d.doctor_name }}
        </button>
      </div>

      <div v-else-if="step === 3" class="space-y-3">
        <UInput v-model="form.date" type="date" class="w-full" />
        <div v-if="!slots.length" class="text-sm text-slate-500">No free slots.</div>
        <div v-else class="flex flex-wrap gap-2">
          <button
            v-for="slot in slots"
            :key="slot"
            type="button"
            class="rounded-lg border px-3 py-1.5 text-sm"
            :class="form.appointment_time === slot ? 'border-[#0097A7] bg-[#0097A7] text-white' : 'border-slate-200 hover:bg-slate-50'"
            @click="form.appointment_time = slot"
          >
            {{ slot }}
          </button>
        </div>
      </div>

      <div v-else-if="step === 4" class="space-y-3">
        <UFormField v-if="!props.clientId" label="Patient">
          <USelect
            :model-value="form.client_id"
            :items="[
              { label: 'Walk-in / type name', value: null },
              ...clients.map(c => ({ label: `${c.name}${c.number ? ` · ${c.number}` : ''}`, value: c.client_id }))
            ]"
            value-key="value"
            label-key="label"
            class="w-full"
            @update:model-value="pickClient($event as number | null)"
          />
        </UFormField>
        <UFormField label="Name" required>
          <UInput v-model="form.name" class="w-full" />
        </UFormField>
        <UFormField label="Phone">
          <UInput v-model="form.phone" class="w-full" />
        </UFormField>
      </div>

      <div v-else class="space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm">
        <p><span class="text-slate-500">Patient:</span> {{ form.name }}</p>
        <p><span class="text-slate-500">When:</span> {{ form.date }} · {{ form.appointment_time }}</p>
        <p><span class="text-slate-500">Doctor:</span> {{ doctors.find(d => d.doctor_id === form.doctor_id)?.doctor_name }}</p>
        <p><span class="text-slate-500">Service:</span> {{ services.find(s => s.service_id === form.service_id)?.service_name }}</p>
      </div>

      <div class="mt-4 flex justify-between gap-2">
        <UButton color="neutral" variant="ghost" :disabled="step === 1" @click="step -= 1">Back</UButton>
        <UButton
          v-if="step < 5"
          class="bg-[#0097A7]"
          :disabled="(step === 3 && !form.appointment_time) || (step === 4 && !form.name.trim())"
          @click="step += 1"
        >
          Next
        </UButton>
        <UButton v-else class="bg-[#0097A7]" :loading="booking" @click="book">Confirm book</UButton>
      </div>
    </template>
  </UModal>
</template>
