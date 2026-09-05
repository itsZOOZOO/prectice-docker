<script setup lang="ts">
import {
  CLINIC_SETTINGS_TABS,
  type ClinicAppointmentSettings,
  type ClinicDayHours,
  type ClinicServiceItem,
  type ClinicSettingsTab
} from '~/utils/clinicSettings'

const props = withDefaults(defineProps<{
  tab?: ClinicSettingsTab
  hideTabBar?: boolean
}>(), {
  hideTabBar: false
})

const emit = defineEmits<{
  'update:tab': [tab: ClinicSettingsTab]
}>()

const { api } = useApi()
const toast = useToast()

const internalTab = ref<ClinicSettingsTab>('hours')
const tab = computed(() => props.tab ?? internalTab.value)

function setTab(next: ClinicSettingsTab) {
  if (props.tab != null) emit('update:tab', next)
  else internalTab.value = next
}

const loading = ref(true)
const saving = ref(false)
const error = ref('')
const hours = ref<ClinicDayHours[]>([])
const booking = ref<ClinicAppointmentSettings | null>(null)
const services = ref<ClinicServiceItem[]>([])
const serviceSearch = ref('')
const editingServiceId = ref<number | null>(null)
const serviceFormError = ref('')
const serviceFormRef = ref<HTMLElement | null>(null)
const serviceForm = reactive({
  service_name: '',
  duration_minutes: '30',
  description: ''
})
const loadedTabs = ref(new Set<ClinicSettingsTab>())

const filteredServices = computed(() => {
  const q = serviceSearch.value.trim().toLowerCase()
  if (!q) return services.value
  return services.value.filter(s => s.service_name.toLowerCase().includes(q))
})

async function loadTab(activeTab: ClinicSettingsTab) {
  loading.value = true
  error.value = ''
  try {
    if (activeTab === 'hours') {
      const data = await api<{ days: ClinicDayHours[] }>('/settings/clinic/hours')
      hours.value = data.days ?? []
    } else if (activeTab === 'booking') {
      const data = await api<{ settings: ClinicAppointmentSettings }>('/settings/clinic/appointment-settings')
      booking.value = data.settings
    } else {
      const data = await api<{ services: ClinicServiceItem[] }>('/settings/clinic/services')
      services.value = data.services ?? []
    }
    loadedTabs.value.add(activeTab)
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to load settings'
  } finally {
    loading.value = false
  }
}

watch(tab, (activeTab) => {
  if (!loadedTabs.value.has(activeTab)) void loadTab(activeTab)
  else loading.value = false
}, { immediate: true })

function updateDay(index: number, patch: Partial<ClinicDayHours>) {
  hours.value = hours.value.map((day, i) => (i === index ? { ...day, ...patch } : day))
}

async function saveHours() {
  saving.value = true
  error.value = ''
  try {
    const data = await api<{ days: ClinicDayHours[] }>('/settings/clinic/hours', {
      method: 'PATCH',
      body: { days: hours.value }
    })
    hours.value = data.days ?? hours.value
    toast.add({
      title: 'Clinic hours saved',
      description: 'Applied to all doctors’ schedules',
      color: 'success'
    })
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to save clinic hours'
    toast.add({ title: error.value, color: 'error' })
  } finally {
    saving.value = false
  }
}

async function saveBooking() {
  if (!booking.value) return
  saving.value = true
  error.value = ''
  try {
    const data = await api<{ settings: ClinicAppointmentSettings }>('/settings/clinic/appointment-settings', {
      method: 'PATCH',
      body: booking.value
    })
    booking.value = data.settings
    toast.add({ title: 'Booking rules saved', color: 'success' })
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to save booking settings'
    toast.add({ title: error.value, color: 'error' })
  } finally {
    saving.value = false
  }
}

function resetServiceForm() {
  editingServiceId.value = null
  serviceForm.service_name = ''
  serviceForm.duration_minutes = '30'
  serviceForm.description = ''
  serviceFormError.value = ''
}

function startEditService(service: ClinicServiceItem) {
  editingServiceId.value = service.service_id
  serviceForm.service_name = service.service_name
  serviceForm.duration_minutes = String(service.duration_minutes)
  serviceForm.description = service.description
  serviceFormError.value = ''
  nextTick(() => {
    serviceFormRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
}

async function saveService() {
  if (!serviceForm.service_name.trim()) {
    serviceFormError.value = 'Service name is required.'
    return
  }
  saving.value = true
  serviceFormError.value = ''
  const payload = {
    service_name: serviceForm.service_name.trim(),
    duration_minutes: Number(serviceForm.duration_minutes) || 30,
    description: serviceForm.description.trim() || undefined
  }
  try {
    const data = editingServiceId.value != null
      ? await api<{ service: ClinicServiceItem }>(`/settings/clinic/services/${editingServiceId.value}`, {
          method: 'PATCH',
          body: payload
        })
      : await api<{ service: ClinicServiceItem }>('/settings/clinic/services', {
          method: 'POST',
          body: payload
        })
    const saved = data.service
    if (editingServiceId.value != null) {
      services.value = services.value.map(s => (s.service_id === editingServiceId.value ? saved : s))
      toast.add({ title: 'Service updated', color: 'success' })
    } else {
      services.value = [...services.value, saved].sort((a, b) =>
        a.service_name.localeCompare(b.service_name)
      )
      toast.add({ title: 'Service added', color: 'success' })
    }
    resetServiceForm()
  } catch (e: unknown) {
    serviceFormError.value = e instanceof Error ? e.message : 'Failed to save service'
  } finally {
    saving.value = false
  }
}

async function toggleServiceActive(service: ClinicServiceItem) {
  try {
    const data = await api<{ service: ClinicServiceItem }>(
      `/settings/clinic/services/${service.service_id}/active`,
      { method: 'PATCH', body: { is_active: !service.is_active } }
    )
    services.value = services.value.map(s =>
      s.service_id === service.service_id ? data.service : s
    )
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to update service', color: 'error' })
  }
}

async function toggleServicePublic(service: ClinicServiceItem) {
  try {
    const data = await api<{ service: ClinicServiceItem }>(
      `/settings/clinic/services/${service.service_id}/public-booking`,
      { method: 'PATCH', body: { allow_public_booking: !service.allow_public_booking } }
    )
    services.value = services.value.map(s =>
      s.service_id === service.service_id ? data.service : s
    )
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to update service', color: 'error' })
  }
}
</script>

<template>
  <div class="p-4 md:p-5">
    <div v-if="!hideTabBar" class="mb-4">
      <div class="flex max-w-xl gap-1 rounded-lg bg-slate-100 p-1">
        <button
          v-for="entry in CLINIC_SETTINGS_TABS"
          :key="entry.key"
          type="button"
          class="flex-1 rounded-md px-3 py-2 text-sm font-medium transition"
          :class="tab === entry.key
            ? 'bg-white text-[#0097A7] shadow-sm'
            : 'text-slate-600 hover:text-slate-800'"
          @click="setTab(entry.key)"
        >
          {{ entry.label }}
        </button>
      </div>
    </div>

    <div
      v-if="error"
      class="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
    >
      {{ error }}
    </div>

    <div v-if="loading" class="py-16 text-center text-sm text-slate-400">Loading…</div>

    <div
      v-else-if="tab === 'hours'"
      class="rounded-xl border border-slate-200 bg-white shadow-sm"
    >
      <div class="border-b border-slate-100 px-4 py-3">
        <h3 class="m-0 text-sm font-semibold text-slate-800">Weekly clinic hours</h3>
        <p class="mt-0.5 text-xs text-slate-500">
          Sets default open/close times for every active doctor in this clinic.
        </p>
      </div>
      <div class="divide-y divide-slate-100">
        <div
          v-for="(day, index) in hours"
          :key="day.day_name"
          class="flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
          :class="!day.is_working ? 'bg-slate-50' : ''"
        >
          <div class="flex items-center gap-3">
            <label class="flex items-center gap-2 text-sm font-medium text-slate-800">
              <input
                type="checkbox"
                class="accent-[#0097A7]"
                :checked="day.is_working"
                @change="updateDay(index, { is_working: ($event.target as HTMLInputElement).checked })"
              >
              {{ day.day_name }}
            </label>
            <span
              v-if="!day.is_working"
              class="rounded-full bg-slate-200 px-2 py-0.5 text-[10px] font-bold uppercase text-slate-600"
            >
              Closed
            </span>
          </div>
          <div v-if="day.is_working" class="flex flex-wrap items-center gap-2">
            <input
              type="time"
              class="rounded-lg border border-slate-200 px-2 py-1.5 text-sm"
              :value="day.start_time"
              @change="updateDay(index, { start_time: ($event.target as HTMLInputElement).value })"
            >
            <span class="text-slate-400">to</span>
            <input
              type="time"
              class="rounded-lg border border-slate-200 px-2 py-1.5 text-sm"
              :value="day.end_time"
              @change="updateDay(index, { end_time: ($event.target as HTMLInputElement).value })"
            >
          </div>
        </div>
      </div>
      <div class="border-t border-slate-100 px-4 py-3">
        <UButton class="bg-[#0097A7]" :loading="saving" @click="saveHours">
          Save clinic hours
        </UButton>
      </div>
    </div>

    <div
      v-else-if="tab === 'booking' && booking"
      class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
    >
      <h3 class="m-0 text-sm font-semibold text-slate-800">Appointment booking rules</h3>
      <p class="mb-4 mt-0.5 text-xs text-slate-500">
        Slot spacing, lead time, and public booking window.
      </p>
      <div class="grid gap-4 md:grid-cols-2">
        <UFormField label="Slot interval (minutes)">
          <UInput
            v-model.number="booking.slot_interval"
            type="number"
            :min="5"
            :max="60"
            class="w-full"
          />
        </UFormField>
        <UFormField label="Booking lead time (hours)">
          <UInput
            v-model.number="booking.booking_lead_time_hours"
            type="number"
            :min="0"
            :max="48"
            class="w-full"
          />
        </UFormField>
        <UFormField label="Max advance booking (days)">
          <UInput
            v-model.number="booking.max_advance_booking_days"
            type="number"
            :min="1"
            :max="365"
            class="w-full"
          />
        </UFormField>
        <label class="flex items-center gap-2 self-end text-sm">
          <input
            v-model="booking.allow_overlapping_appointments"
            type="checkbox"
            class="accent-[#0097A7]"
          >
          Allow overlapping appointments
        </label>
        <UFormField label="Public booking — earliest (days from today)">
          <UInput
            v-model.number="booking.public_booking_min_days_ahead"
            type="number"
            :min="0"
            :max="30"
            class="w-full"
          />
        </UFormField>
        <UFormField label="Public booking — latest (days from today)">
          <UInput
            v-model.number="booking.public_booking_max_days_ahead"
            type="number"
            :min="1"
            :max="90"
            class="w-full"
          />
        </UFormField>
      </div>
      <UButton class="mt-4 bg-[#0097A7]" :loading="saving" @click="saveBooking">
        Save booking rules
      </UButton>
    </div>

    <template v-else-if="tab === 'services'">
      <div
        ref="serviceFormRef"
        class="mb-4 scroll-mt-4 rounded-xl p-4 shadow-sm"
        :class="editingServiceId != null
          ? 'border-2 border-amber-400 bg-amber-50 ring-4 ring-amber-100'
          : 'border border-slate-200 bg-white'"
      >
        <div
          v-if="editingServiceId != null"
          class="mb-3 rounded-lg border border-amber-300 bg-amber-100/80 px-3 py-2 text-sm text-amber-900"
        >
          Editing service — update fields and click <strong>Save changes</strong>.
        </div>
        <h3 v-else class="mb-3 text-sm font-semibold text-slate-800">Add service</h3>
        <form class="grid gap-3 md:grid-cols-3" @submit.prevent="saveService">
          <UFormField label="Service name *" class="md:col-span-2">
            <UInput v-model="serviceForm.service_name" class="w-full" required />
          </UFormField>
          <UFormField label="Duration (min) *">
            <UInput
              v-model="serviceForm.duration_minutes"
              type="number"
              :min="5"
              :max="240"
              :step="5"
              class="w-full"
              required
            />
          </UFormField>
          <UFormField label="Description" class="md:col-span-3">
            <UInput v-model="serviceForm.description" class="w-full" />
          </UFormField>
          <div class="flex flex-wrap items-center gap-2 md:col-span-3">
            <UButton
              type="submit"
              :class="editingServiceId != null ? 'bg-amber-600' : 'bg-[#0097A7]'"
              :loading="saving"
            >
              {{ editingServiceId != null ? 'Save changes' : 'Add service' }}
            </UButton>
            <UButton
              v-if="editingServiceId != null"
              type="button"
              color="neutral"
              variant="outline"
              @click="resetServiceForm"
            >
              Cancel
            </UButton>
            <p v-if="serviceFormError" class="text-sm text-red-600">{{ serviceFormError }}</p>
          </div>
        </form>
      </div>

      <div class="rounded-xl border border-slate-200 bg-white shadow-sm">
        <div class="flex flex-col gap-3 border-b border-slate-100 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
          <h3 class="m-0 text-sm font-semibold text-slate-800">Services ({{ services.length }})</h3>
          <UInput v-model="serviceSearch" class="w-full sm:max-w-xs" placeholder="Search services…" />
        </div>
        <div class="overflow-x-auto">
          <table class="min-w-full text-left text-sm">
            <thead class="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th class="px-4 py-3 font-semibold">Service</th>
                <th class="px-4 py-3 font-semibold">Duration</th>
                <th class="px-4 py-3 font-semibold">Status</th>
                <th class="px-4 py-3 font-semibold">Public</th>
                <th class="px-4 py-3 text-right font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="service in filteredServices"
                :key="service.service_id"
                class="border-t border-slate-100"
                :class="editingServiceId === service.service_id ? 'bg-amber-50' : 'hover:bg-slate-50'"
              >
                <td class="px-4 py-3">
                  <div class="font-medium text-slate-800">{{ service.service_name }}</div>
                  <div v-if="service.description" class="text-xs text-slate-500">
                    {{ service.description }}
                  </div>
                </td>
                <td class="px-4 py-3 text-slate-600">{{ service.duration_minutes }} min</td>
                <td class="px-4 py-3">
                  <button
                    type="button"
                    class="rounded-full px-2 py-0.5 text-xs font-semibold"
                    :class="service.is_active
                      ? 'bg-emerald-100 text-emerald-800'
                      : 'bg-slate-200 text-slate-600'"
                    @click="toggleServiceActive(service)"
                  >
                    {{ service.is_active ? 'Active' : 'Inactive' }}
                  </button>
                </td>
                <td class="px-4 py-3">
                  <button
                    type="button"
                    class="rounded-full px-2 py-0.5 text-xs font-semibold"
                    :class="service.allow_public_booking
                      ? 'bg-sky-100 text-sky-800'
                      : 'bg-slate-200 text-slate-600'"
                    @click="toggleServicePublic(service)"
                  >
                    {{ service.allow_public_booking ? 'On' : 'Off' }}
                  </button>
                </td>
                <td class="px-4 py-3 text-right">
                  <UButton
                    size="xs"
                    :color="editingServiceId === service.service_id ? 'warning' : 'neutral'"
                    :variant="editingServiceId === service.service_id ? 'solid' : 'ghost'"
                    @click="startEditService(service)"
                  >
                    Edit
                  </UButton>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>
