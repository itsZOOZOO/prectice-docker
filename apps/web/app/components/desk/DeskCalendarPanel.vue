<script setup lang="ts">
type Doctor = { doctor_id: number, doctor_name: string, color_code: string | null }
type Service = { service_id: number, service_name: string, duration_minutes: number }
type Status = { status_id: number, status_name: string, color: string }
type Appt = {
  appointment_id: number
  client_id: number | null
  doctor_id: number
  name: string
  phone: string | null
  appointment_date: string
  appointment_time: string
  end_time: string | null
  status: string
  doctor_name: string | null
  service_name: string | null
  notes: string | null
}
type ClientOpt = { client_id: number, name: string, number: string | null }

const { api } = useApi()
const toast = useToast()
const { openPatient } = useDeskUrl()

function todayISO() {
  const d = new Date()
  const offset = d.getTimezoneOffset()
  const local = new Date(d.getTime() - offset * 60000)
  return local.toISOString().slice(0, 10)
}

const day = ref(todayISO())
const doctors = ref<Doctor[]>([])
const services = ref<Service[]>([])
const statuses = ref<Status[]>([])
const items = ref<Appt[]>([])
const clients = ref<ClientOpt[]>([])
const loading = ref(false)
const error = ref('')
const doctorFilter = ref<number | 'all'>('all')

const showBook = ref(false)
const booking = ref(false)
const slots = ref<string[]>([])
const form = reactive({
  client_id: null as number | null,
  doctor_id: null as number | null,
  service_id: null as number | null,
  name: '',
  phone: '',
  appointment_time: '',
  notes: ''
})

const doctorItems = computed(() => [
  { label: 'All doctors', value: 'all' as const },
  ...doctors.value.map(d => ({ label: d.doctor_name, value: d.doctor_id }))
])

const filtered = computed(() => {
  if (doctorFilter.value === 'all') return items.value
  return items.value.filter(a => a.doctor_id === doctorFilter.value)
})

function statusColor(name: string) {
  const s = statuses.value.find(x => x.status_name === name)
  const map: Record<string, 'success' | 'warning' | 'error' | 'neutral' | 'primary'> = {
    success: 'success',
    warning: 'warning',
    danger: 'error',
    error: 'error',
    secondary: 'neutral',
    neutral: 'neutral'
  }
  return map[s?.color || ''] || 'neutral'
}

function shiftDay(delta: number) {
  const d = new Date(`${day.value}T12:00:00`)
  d.setDate(d.getDate() + delta)
  day.value = d.toISOString().slice(0, 10)
}

async function loadMeta() {
  const meta = await api<{ doctors: Doctor[], services: Service[], statuses: Status[] }>('/appointments/meta')
  doctors.value = meta.doctors
  services.value = meta.services
  statuses.value = meta.statuses
  if (!form.doctor_id && meta.doctors[0]) form.doctor_id = meta.doctors[0].doctor_id
  if (!form.service_id && meta.services[0]) form.service_id = meta.services[0].service_id
}

async function loadDay() {
  loading.value = true
  error.value = ''
  try {
    const data = await api<{ date: string, items: Appt[] }>('/appointments', {
      query: { on: day.value }
    })
    items.value = data.items
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to load'
  } finally {
    loading.value = false
  }
}

async function loadClients() {
  const data = await api<{ total: number, items: ClientOpt[] }>('/clients', { query: { limit: 100 } })
  clients.value = data.items
}

async function loadSlots() {
  if (!form.doctor_id) {
    slots.value = []
    return
  }
  const data = await api<{ slots: string[] }>('/appointments/slots', {
    query: {
      on: day.value,
      doctor_id: form.doctor_id,
      service_id: form.service_id || undefined
    }
  })
  slots.value = data.slots
  if (!slots.value.includes(form.appointment_time)) {
    form.appointment_time = slots.value[0] || ''
  }
}

function onClientPick(id: number | null) {
  form.client_id = id
  const c = clients.value.find(x => x.client_id === id)
  if (c) {
    form.name = c.name
    form.phone = c.number || ''
  }
}

async function openBook() {
  showBook.value = true
  if (!clients.value.length) await loadClients()
  await loadSlots()
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
        appointment_date: day.value,
        appointment_time: form.appointment_time,
        notes: form.notes || null
      }
    })
    toast.add({ title: 'Appointment booked', color: 'success' })
    showBook.value = false
    form.notes = ''
    form.appointment_time = ''
    await loadDay()
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Booking failed', color: 'error' })
  } finally {
    booking.value = false
  }
}

async function setStatus(appt: Appt, status: string) {
  try {
    const updated = await api<Appt>(`/appointments/${appt.appointment_id}/status`, {
      method: 'PATCH',
      body: { status }
    })
    const idx = items.value.findIndex(a => a.appointment_id === appt.appointment_id)
    if (idx >= 0) items.value[idx] = updated
    toast.add({ title: `Marked ${status}`, color: 'success' })
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Update failed', color: 'error' })
  }
}

watch(day, loadDay)
watch(() => [form.doctor_id, form.service_id, showBook.value], () => {
  if (showBook.value) loadSlots()
})

onMounted(async () => {
  try {
    await loadMeta()
    await loadDay()
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to load calendar'
  }
})
</script>

<template>
  <div class="h-full overflow-y-auto p-5 space-y-5">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <p class="text-sm text-slate-500">Day board · book · update status</p>
      </div>
      <UButton icon="i-lucide-plus" class="bg-[#0097A7]" @click="openBook">Book</UButton>
    </div>

    <div class="flex flex-wrap items-center gap-3">
      <div class="flex items-center gap-1 rounded-xl border border-stone-200 bg-white p-1">
        <UButton icon="i-lucide-chevron-left" color="neutral" variant="ghost" size="sm" @click="shiftDay(-1)" />
        <UInput v-model="day" type="date" class="w-40" size="sm" />
        <UButton icon="i-lucide-chevron-right" color="neutral" variant="ghost" size="sm" @click="shiftDay(1)" />
        <UButton color="neutral" variant="ghost" size="sm" @click="day = todayISO()">Today</UButton>
      </div>
      <USelect v-model="doctorFilter" :items="doctorItems" value-key="value" label-key="label" class="w-48" />
    </div>

    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
    <p v-if="loading" class="text-stone-500">Loading…</p>

    <ul v-else class="divide-y divide-stone-100 overflow-hidden rounded-2xl border border-stone-200 bg-white">
      <li v-if="!filtered.length" class="px-4 py-10 text-center text-stone-500">
        No appointments this day.
      </li>
      <li
        v-for="a in filtered"
        :key="a.appointment_id"
        class="flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
      >
        <div class="min-w-0">
          <div class="flex flex-wrap items-center gap-2">
            <span class="font-mono text-sm text-teal-800">{{ a.appointment_time }}{{ a.end_time ? `–${a.end_time}` : '' }}</span>
            <UBadge :color="statusColor(a.status)" variant="subtle">{{ a.status }}</UBadge>
          </div>
          <p class="mt-1 font-medium text-[#1C2B35]">
            <button
              v-if="a.client_id"
              type="button"
              class="hover:underline"
              @click="openPatient(a.client_id!)"
            >
              {{ a.name }}
            </button>
            <span v-else>{{ a.name }}</span>
          </p>
          <p class="text-sm text-slate-500">
            {{ a.doctor_name || 'Doctor' }}
            <span v-if="a.service_name"> · {{ a.service_name }}</span>
            <span v-if="a.phone"> · {{ a.phone }}</span>
          </p>
        </div>
        <div class="flex flex-wrap gap-1">
          <UButton
            v-for="s in statuses"
            :key="s.status_id"
            size="xs"
            :variant="a.status === s.status_name ? 'solid' : 'outline'"
            :color="a.status === s.status_name ? statusColor(s.status_name) : 'neutral'"
            @click="setStatus(a, s.status_name)"
          >
            {{ s.status_name }}
          </UButton>
        </div>
      </li>
    </ul>

    <UModal v-model:open="showBook" title="Book appointment">
      <template #body>
        <form class="space-y-3" @submit.prevent="book">
          <UFormField label="Patient (optional)">
            <USelect
              :model-value="form.client_id"
              :items="[
                { label: 'Walk-in / type name', value: null },
                ...clients.map(c => ({ label: `${c.name}${c.number ? ` · ${c.number}` : ''}`, value: c.client_id }))
              ]"
              value-key="value"
              label-key="label"
              class="w-full"
              @update:model-value="onClientPick($event as number | null)"
            />
          </UFormField>
          <UFormField label="Name" required>
            <UInput v-model="form.name" class="w-full" />
          </UFormField>
          <UFormField label="Phone">
            <UInput v-model="form.phone" class="w-full" />
          </UFormField>
          <div class="grid gap-3 sm:grid-cols-2">
            <UFormField label="Doctor" required>
              <USelect
                v-model="form.doctor_id"
                :items="doctors.map(d => ({ label: d.doctor_name, value: d.doctor_id }))"
                value-key="value"
                label-key="label"
                class="w-full"
              />
            </UFormField>
            <UFormField label="Service">
              <USelect
                v-model="form.service_id"
                :items="services.map(s => ({ label: `${s.service_name} (${s.duration_minutes}m)`, value: s.service_id }))"
                value-key="value"
                label-key="label"
                class="w-full"
              />
            </UFormField>
          </div>
          <UFormField label="Slot" required>
            <div v-if="!slots.length" class="text-sm text-stone-500">No free slots this day.</div>
            <div v-else class="flex flex-wrap gap-2">
              <UButton
                v-for="slot in slots"
                :key="slot"
                size="sm"
                :variant="form.appointment_time === slot ? 'solid' : 'outline'"
                :color="form.appointment_time === slot ? 'primary' : 'neutral'"
                type="button"
                @click="form.appointment_time = slot"
              >
                {{ slot }}
              </UButton>
            </div>
          </UFormField>
          <UFormField label="Notes">
            <UTextarea v-model="form.notes" class="w-full" :rows="2" />
          </UFormField>
          <div class="flex justify-end gap-2 pt-2">
            <UButton color="neutral" variant="ghost" @click="showBook = false">Cancel</UButton>
            <UButton type="submit" :loading="booking" :disabled="!form.appointment_time">Book</UButton>
          </div>
        </form>
      </template>
    </UModal>
  </div>
</template>
