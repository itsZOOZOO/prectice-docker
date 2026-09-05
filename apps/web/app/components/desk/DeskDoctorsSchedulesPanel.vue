<script setup lang="ts">
import { CLINIC_WEEK_DAYS, type ClinicDayHours } from '~/utils/clinicSettings'
import {
  DOCTOR_DETAIL_TABS,
  createDefaultTimeOffForm,
  formatTimeOffRange,
  timeOffFormFromItem,
  timeOffPayloadFromForm,
  type ClinicTimeOffItem,
  type DoctorBreak,
  type DoctorDetail,
  type DoctorDetailTab,
  type DoctorListItem,
  type DoctorTimeOff,
  type DoctorsListPayload,
  type EligibleDoctorUser,
  type TimeOffFormState
} from '~/utils/doctorSettings'

const props = withDefaults(defineProps<{
  detailTab?: DoctorDetailTab
  hideDetailTabBar?: boolean
}>(), {
  hideDetailTabBar: false
})

const emit = defineEmits<{
  'update:detailTab': [tab: DoctorDetailTab]
  detailViewChange: [inDetail: boolean]
}>()

const { api } = useApi()
const toast = useToast()

const internalDetailTab = ref<DoctorDetailTab>('schedule')
const detailTab = computed(() => props.detailTab ?? internalDetailTab.value)

function setDetailTab(next: DoctorDetailTab) {
  if (props.detailTab != null) emit('update:detailTab', next)
  else internalDetailTab.value = next
}

const loading = ref(true)
const saving = ref(false)
const error = ref('')

const doctors = ref<DoctorListItem[]>([])
const eligibleUsers = ref<EligibleDoctorUser[]>([])
const upcomingTimeOff = ref<ClinicTimeOffItem[]>([])
const addUserId = ref('')
const addDoctorName = ref('')
const addMode = ref<'user' | 'name'>('user')

const selectedDoctorId = ref<number | null>(null)
const doctor = ref<DoctorDetail | null>(null)
const scheduleDraft = ref<ClinicDayHours[]>([])

const breakFormOpen = ref(false)
const editingBreakId = ref<number | null>(null)
const breakDay = ref('Monday')
const breakName = ref('')
const breakStart = ref('13:00')
const breakEnd = ref('14:00')
const breakAllowBooking = ref(false)

const timeOffFormOpen = ref(false)
const editingTimeOffId = ref<number | null>(null)
const editingTimeOffDoctorId = ref<number | null>(null)
const timeOffForm = ref<TimeOffFormState>(createDefaultTimeOffForm())

watch(selectedDoctorId, (id) => {
  emit('detailViewChange', id != null)
}, { immediate: true })

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const data = await api<DoctorsListPayload>('/settings/doctors')
    doctors.value = data.doctors ?? []
    eligibleUsers.value = data.eligible_users ?? []
    upcomingTimeOff.value = data.upcoming_time_off ?? []
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to load doctors'
  } finally {
    loading.value = false
  }
}

async function loadDoctor(doctorId: number) {
  loading.value = true
  error.value = ''
  try {
    const data = await api<{ doctor: DoctorDetail }>(`/settings/doctors/${doctorId}`)
    doctor.value = data.doctor
    scheduleDraft.value = data.doctor.schedule ?? []
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to load doctor'
  } finally {
    loading.value = false
  }
}

watch(selectedDoctorId, (id) => {
  if (id == null) void loadList()
  else void loadDoctor(id)
}, { immediate: true })

async function handleAddDoctor() {
  saving.value = true
  error.value = ''
  try {
    const body
      = addMode.value === 'user'
        ? { user_id: Number(addUserId.value) || undefined }
        : { doctor_name: addDoctorName.value.trim() || undefined }
    if (addMode.value === 'user' && !body.user_id) return
    if (addMode.value === 'name' && !('doctor_name' in body && body.doctor_name)) {
      toast.add({ title: 'Doctor name required', color: 'warning' })
      return
    }
    await api('/settings/doctors', { method: 'POST', body })
    addUserId.value = ''
    addDoctorName.value = ''
    toast.add({ title: 'Doctor added', color: 'success' })
    await loadList()
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to add doctor'
    toast.add({ title: error.value, color: 'error' })
  } finally {
    saving.value = false
  }
}

function openDoctor(id: number) {
  selectedDoctorId.value = id
  setDetailTab('schedule')
  resetBreakForm()
  resetTimeOffForm()
}

function backToList() {
  selectedDoctorId.value = null
  doctor.value = null
  resetTimeOffForm()
}

function updateScheduleDay(index: number, patch: Partial<ClinicDayHours>) {
  scheduleDraft.value = scheduleDraft.value.map((d, i) => (i === index ? { ...d, ...patch } : d))
}

async function saveSchedule() {
  if (!doctor.value) return
  saving.value = true
  error.value = ''
  try {
    const data = await api<{ doctor: DoctorDetail }>(
      `/settings/doctors/${doctor.value.doctor_id}/schedule`,
      { method: 'PUT', body: { days: scheduleDraft.value } }
    )
    doctor.value = data.doctor
    scheduleDraft.value = data.doctor.schedule
    toast.add({ title: 'Schedule saved', color: 'success' })
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to save schedule'
    toast.add({ title: error.value, color: 'error' })
  } finally {
    saving.value = false
  }
}

async function resetScheduleFromClinic() {
  if (!doctor.value) return
  if (!window.confirm('Replace this doctor’s weekly hours with the clinic default hours?')) return
  saving.value = true
  try {
    const data = await api<{ doctor: DoctorDetail }>(
      `/settings/doctors/${doctor.value.doctor_id}/schedule/reset-from-clinic`,
      { method: 'POST' }
    )
    doctor.value = data.doctor
    scheduleDraft.value = data.doctor.schedule
    toast.add({ title: 'Schedule reset to clinic hours', color: 'success' })
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to reset', color: 'error' })
  } finally {
    saving.value = false
  }
}

async function toggleDoctorActive() {
  if (!doctor.value) return
  saving.value = true
  try {
    const data = await api<{ doctor: DoctorDetail }>(
      `/settings/doctors/${doctor.value.doctor_id}/active`,
      { method: 'PATCH', body: { is_active: !doctor.value.is_active } }
    )
    doctor.value = data.doctor
    toast.add({
      title: data.doctor.is_active ? 'Doctor activated' : 'Doctor deactivated',
      color: 'success'
    })
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to update status', color: 'error' })
  } finally {
    saving.value = false
  }
}

function startEditBreak(brk: DoctorBreak) {
  editingBreakId.value = brk.break_id
  breakDay.value = brk.day_name
  breakName.value = brk.break_name
  breakStart.value = brk.start_time
  breakEnd.value = brk.end_time
  breakAllowBooking.value = brk.allow_booking
  breakFormOpen.value = true
}

function resetBreakForm() {
  breakFormOpen.value = false
  editingBreakId.value = null
  breakDay.value = 'Monday'
  breakName.value = ''
  breakStart.value = '13:00'
  breakEnd.value = '14:00'
  breakAllowBooking.value = false
}

async function saveBreak() {
  if (!doctor.value) return
  saving.value = true
  const payload = {
    day_name: breakDay.value,
    break_name: breakName.value,
    start_time: breakStart.value,
    end_time: breakEnd.value,
    allow_booking: breakAllowBooking.value
  }
  try {
    const path = editingBreakId.value != null
      ? `/settings/doctors/${doctor.value.doctor_id}/breaks/${editingBreakId.value}`
      : `/settings/doctors/${doctor.value.doctor_id}/breaks`
    const wasEdit = editingBreakId.value != null
    const data = await api<{ doctor: DoctorDetail }>(path, {
      method: wasEdit ? 'PATCH' : 'POST',
      body: payload
    })
    doctor.value = data.doctor
    resetBreakForm()
    toast.add({
      title: wasEdit ? 'Break updated' : 'Break added',
      color: 'success'
    })
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to save break', color: 'error' })
  } finally {
    saving.value = false
  }
}

async function deleteBreak(breakId: number) {
  if (!doctor.value || !window.confirm('Delete this break?')) return
  saving.value = true
  try {
    const data = await api<{ doctor: DoctorDetail }>(
      `/settings/doctors/${doctor.value.doctor_id}/breaks/${breakId}`,
      { method: 'DELETE' }
    )
    doctor.value = data.doctor
    toast.add({ title: 'Break deleted', color: 'success' })
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to delete break', color: 'error' })
  } finally {
    saving.value = false
  }
}

function resetTimeOffForm(doctorId = '') {
  timeOffFormOpen.value = false
  editingTimeOffId.value = null
  editingTimeOffDoctorId.value = null
  timeOffForm.value = createDefaultTimeOffForm(doctorId)
}

function openTimeOffForm(doctorId = '') {
  timeOffForm.value = createDefaultTimeOffForm(doctorId)
  editingTimeOffId.value = null
  editingTimeOffDoctorId.value = null
  timeOffFormOpen.value = true
}

function startEditTimeOff(item: DoctorTimeOff | ClinicTimeOffItem, doctorId: number) {
  editingTimeOffId.value = item.time_off_id
  editingTimeOffDoctorId.value = doctorId
  timeOffForm.value = timeOffFormFromItem(item, String(doctorId))
  timeOffFormOpen.value = true
}

async function saveTimeOff(targetDoctorId?: number) {
  const doctorId
    = targetDoctorId
      ?? editingTimeOffDoctorId.value
      ?? doctor.value?.doctor_id
      ?? Number(timeOffForm.value.doctorId)
  if (!doctorId) {
    toast.add({ title: 'Select a doctor', color: 'warning' })
    return
  }
  saving.value = true
  try {
    const path = editingTimeOffId.value != null
      ? `/settings/doctors/${doctorId}/time-off/${editingTimeOffId.value}`
      : `/settings/doctors/${doctorId}/time-off`
    const data = await api<{ doctor: DoctorDetail }>(path, {
      method: editingTimeOffId.value != null ? 'PATCH' : 'POST',
      body: timeOffPayloadFromForm(timeOffForm.value)
    })
    if (selectedDoctorId.value === doctorId && data.doctor) {
      doctor.value = data.doctor
    }
    const wasEdit = editingTimeOffId.value != null
    resetTimeOffForm()
    toast.add({ title: wasEdit ? 'Time off updated' : 'Time off added', color: 'success' })
    await loadList()
    if (selectedDoctorId.value === doctorId) await loadDoctor(doctorId)
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to save time off', color: 'error' })
  } finally {
    saving.value = false
  }
}

async function deleteTimeOffEntry(docId: number, timeOffId: number) {
  if (!window.confirm('Delete this time off entry?')) return
  saving.value = true
  try {
    const data = await api<{ doctor: DoctorDetail }>(
      `/settings/doctors/${docId}/time-off/${timeOffId}`,
      { method: 'DELETE' }
    )
    if (selectedDoctorId.value === docId && data.doctor) doctor.value = data.doctor
    if (editingTimeOffId.value === timeOffId) resetTimeOffForm()
    toast.add({ title: 'Time off removed', color: 'success' })
    await loadList()
    if (selectedDoctorId.value === docId) await loadDoctor(docId)
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to delete time off', color: 'error' })
  } finally {
    saving.value = false
  }
}

async function toggleService(serviceId: number, assigned: boolean) {
  if (!doctor.value) return
  const current = doctor.value.services.filter(s => s.assigned).map(s => s.service_id)
  const next = assigned ? current.filter(id => id !== serviceId) : [...current, serviceId]
  saving.value = true
  try {
    const data = await api<{ doctor: DoctorDetail }>(
      `/settings/doctors/${doctor.value.doctor_id}/services`,
      { method: 'PUT', body: { service_ids: next } }
    )
    doctor.value = data.doctor
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to update services', color: 'error' })
  } finally {
    saving.value = false
  }
}

const doctorUpcomingTimeOff = computed(() =>
  (doctor.value?.time_off ?? []).filter(t => !t.is_past)
)
const doctorPastTimeOff = computed(() =>
  (doctor.value?.time_off ?? []).filter(t => t.is_past)
)

function initials(name: string) {
  return (name || '?').slice(0, 2).toUpperCase()
}
</script>

<template>
  <div v-if="selectedDoctorId != null && doctor" class="p-4 md:p-5">
    <div class="mb-4 flex flex-wrap items-center gap-3">
      <UButton color="neutral" variant="outline" size="sm" @click="backToList">
        ← All doctors
      </UButton>
      <div
        class="flex h-10 w-10 items-center justify-center rounded-full text-sm font-bold text-white"
        :style="{ backgroundColor: doctor.color_code }"
      >
        {{ initials(doctor.full_name) }}
      </div>
      <div class="min-w-0 flex-1">
        <h3 class="m-0 truncate text-base font-semibold text-slate-800">{{ doctor.full_name }}</h3>
        <p class="m-0 text-xs text-slate-500">
          {{ doctor.specialization || doctor.role || 'Doctor' }}
          <span v-if="doctor.username"> · @{{ doctor.username }}</span>
        </p>
      </div>
      <UButton
        size="sm"
        :color="doctor.is_active ? 'warning' : 'success'"
        variant="soft"
        :loading="saving"
        @click="toggleDoctorActive"
      >
        {{ doctor.is_active ? 'Deactivate' : 'Activate' }}
      </UButton>
    </div>

    <div v-if="!hideDetailTabBar" class="mb-4">
      <div class="flex max-w-2xl gap-1 overflow-x-auto rounded-lg bg-slate-100 p-1">
        <button
          v-for="entry in DOCTOR_DETAIL_TABS"
          :key="entry.key"
          type="button"
          class="shrink-0 rounded-md px-3 py-2 text-sm font-medium transition"
          :class="detailTab === entry.key
            ? 'bg-white text-[#0097A7] shadow-sm'
            : 'text-slate-600 hover:text-slate-800'"
          @click="setDetailTab(entry.key)"
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
      v-else-if="detailTab === 'schedule'"
      class="rounded-xl border border-slate-200 bg-white shadow-sm"
    >
      <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 px-4 py-3">
        <p class="m-0 text-sm text-slate-600">Weekly working hours for this doctor.</p>
        <button
          type="button"
          class="text-sm font-medium text-[#0097A7] hover:underline"
          :disabled="saving"
          @click="resetScheduleFromClinic"
        >
          Reset to clinic hours
        </button>
      </div>
      <div class="divide-y divide-slate-100">
        <div
          v-for="(day, index) in scheduleDraft"
          :key="day.day_name"
          class="flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
          :class="!day.is_working ? 'bg-slate-50' : ''"
        >
          <label class="flex items-center gap-2 text-sm font-medium text-slate-800">
            <input
              type="checkbox"
              class="accent-[#0097A7]"
              :checked="day.is_working"
              @change="updateScheduleDay(index, { is_working: ($event.target as HTMLInputElement).checked })"
            >
            {{ day.day_name }}
          </label>
          <div v-if="day.is_working" class="flex items-center gap-2">
            <input
              type="time"
              class="rounded-lg border border-slate-200 px-2 py-1.5 text-sm"
              :value="day.start_time"
              @change="updateScheduleDay(index, { start_time: ($event.target as HTMLInputElement).value })"
            >
            <span class="text-slate-400">to</span>
            <input
              type="time"
              class="rounded-lg border border-slate-200 px-2 py-1.5 text-sm"
              :value="day.end_time"
              @change="updateScheduleDay(index, { end_time: ($event.target as HTMLInputElement).value })"
            >
          </div>
          <span v-else class="text-xs font-semibold uppercase text-slate-500">Closed</span>
        </div>
      </div>
      <div class="border-t border-slate-100 px-4 py-3">
        <UButton class="bg-[#0097A7]" :loading="saving" @click="saveSchedule">Save schedule</UButton>
      </div>
    </div>

    <div v-else-if="detailTab === 'breaks'" class="space-y-4">
      <div v-if="breakFormOpen" class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h4 class="mb-3 text-sm font-semibold text-slate-800">
          {{ editingBreakId != null ? 'Edit break' : 'Add break' }}
        </h4>
        <div class="grid gap-3 md:grid-cols-2">
          <UFormField label="Day">
            <select
              v-model="breakDay"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            >
              <option v-for="d in CLINIC_WEEK_DAYS" :key="d" :value="d">{{ d }}</option>
            </select>
          </UFormField>
          <UFormField label="Name">
            <UInput v-model="breakName" class="w-full" placeholder="Lunch break" />
          </UFormField>
          <UFormField label="Start">
            <input
              v-model="breakStart"
              type="time"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            >
          </UFormField>
          <UFormField label="End">
            <input
              v-model="breakEnd"
              type="time"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            >
          </UFormField>
          <label class="flex items-center gap-2 text-sm md:col-span-2">
            <input v-model="breakAllowBooking" type="checkbox" class="accent-[#0097A7]">
            Allow booking during this break
          </label>
        </div>
        <div class="mt-3 flex gap-2">
          <UButton class="bg-[#0097A7]" :loading="saving" @click="saveBreak">Save break</UButton>
          <UButton color="neutral" variant="outline" @click="resetBreakForm">Cancel</UButton>
        </div>
      </div>
      <UButton v-else class="bg-[#0097A7]" @click="breakFormOpen = true">Add break</UButton>

      <div class="rounded-xl border border-slate-200 bg-white shadow-sm">
        <p v-if="!doctor.breaks.length" class="p-6 text-center text-sm text-slate-500">
          No breaks configured.
        </p>
        <div v-else class="divide-y divide-slate-100">
          <div
            v-for="brk in doctor.breaks"
            :key="brk.break_id"
            class="flex flex-wrap items-center justify-between gap-2 px-4 py-3"
          >
            <div>
              <div class="font-medium text-slate-800">
                {{ brk.break_name || 'Break' }} · {{ brk.day_name }}
              </div>
              <div class="text-sm text-slate-500">
                {{ brk.start_time }} – {{ brk.end_time }}
                <span v-if="brk.allow_booking"> · Booking allowed</span>
              </div>
            </div>
            <div class="flex gap-1">
              <UButton size="xs" color="neutral" variant="ghost" @click="startEditBreak(brk)">
                Edit
              </UButton>
              <UButton size="xs" color="error" variant="ghost" @click="deleteBreak(brk.break_id)">
                Delete
              </UButton>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="detailTab === 'time-off'" class="space-y-4">
      <div v-if="timeOffFormOpen" class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h4 class="mb-3 text-sm font-semibold text-slate-800">
          {{ editingTimeOffId != null ? 'Edit time off' : 'Add time off' }}
        </h4>
        <div class="grid gap-3 md:grid-cols-2">
          <UFormField label="Start date">
            <UInput v-model="timeOffForm.startDate" type="date" class="w-full" />
          </UFormField>
          <UFormField label="End date">
            <UInput v-model="timeOffForm.endDate" type="date" class="w-full" />
          </UFormField>
          <label class="flex items-center gap-2 text-sm md:col-span-2">
            <input v-model="timeOffForm.fullDay" type="checkbox" class="accent-[#0097A7]">
            Full day(s)
          </label>
          <template v-if="!timeOffForm.fullDay">
            <UFormField label="Start time">
              <input
                v-model="timeOffForm.startTime"
                type="time"
                class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              >
            </UFormField>
            <UFormField label="End time">
              <input
                v-model="timeOffForm.endTime"
                type="time"
                class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              >
            </UFormField>
          </template>
          <UFormField label="Reason" class="md:col-span-2">
            <UInput v-model="timeOffForm.reason" class="w-full" />
          </UFormField>
        </div>
        <div class="mt-3 flex gap-2">
          <UButton class="bg-[#0097A7]" :loading="saving" @click="saveTimeOff(doctor.doctor_id)">
            Save
          </UButton>
          <UButton color="neutral" variant="outline" @click="resetTimeOffForm(String(doctor.doctor_id))">
            Cancel
          </UButton>
        </div>
      </div>
      <UButton v-else class="bg-[#0097A7]" @click="openTimeOffForm(String(doctor.doctor_id))">
        Add time off
      </UButton>

      <div class="rounded-xl border border-slate-200 bg-white shadow-sm">
        <div class="border-b border-slate-100 px-4 py-3 text-sm font-semibold text-slate-800">
          Upcoming
        </div>
        <p v-if="!doctorUpcomingTimeOff.length" class="p-4 text-sm text-slate-500">None</p>
        <div v-else class="divide-y divide-slate-100">
          <div
            v-for="item in doctorUpcomingTimeOff"
            :key="item.time_off_id"
            class="flex flex-wrap items-center justify-between gap-2 px-4 py-3"
          >
            <div>
              <div class="text-sm font-medium text-slate-800">{{ formatTimeOffRange(item) }}</div>
              <div v-if="item.reason" class="text-xs text-slate-500">{{ item.reason }}</div>
            </div>
            <div class="flex gap-1">
              <UButton size="xs" color="neutral" variant="ghost" @click="startEditTimeOff(item, doctor.doctor_id)">
                Edit
              </UButton>
              <UButton
                size="xs"
                color="error"
                variant="ghost"
                @click="deleteTimeOffEntry(doctor.doctor_id, item.time_off_id)"
              >
                Delete
              </UButton>
            </div>
          </div>
        </div>
      </div>

      <div v-if="doctorPastTimeOff.length" class="rounded-xl border border-slate-200 bg-white shadow-sm">
        <div class="border-b border-slate-100 px-4 py-3 text-sm font-semibold text-slate-500">
          Past
        </div>
        <div class="divide-y divide-slate-100">
          <div
            v-for="item in doctorPastTimeOff"
            :key="item.time_off_id"
            class="flex flex-wrap items-center justify-between gap-2 px-4 py-3 opacity-70"
          >
            <div>
              <div class="text-sm font-medium text-slate-800">{{ formatTimeOffRange(item) }}</div>
              <div v-if="item.reason" class="text-xs text-slate-500">{{ item.reason }}</div>
            </div>
            <UButton
              size="xs"
              color="error"
              variant="ghost"
              @click="deleteTimeOffEntry(doctor.doctor_id, item.time_off_id)"
            >
              Delete
            </UButton>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div class="border-b border-slate-100 px-4 py-3">
        <p class="m-0 text-sm text-slate-600">Services this doctor can book appointments for.</p>
      </div>
      <div class="divide-y divide-slate-100">
        <label
          v-for="svc in doctor.services"
          :key="svc.service_id"
          class="flex cursor-pointer items-center justify-between gap-3 px-4 py-3 hover:bg-slate-50"
        >
          <div>
            <div class="font-medium text-slate-800">{{ svc.service_name }}</div>
            <div class="text-xs text-slate-500">{{ svc.duration_minutes }} min</div>
          </div>
          <input
            type="checkbox"
            class="h-4 w-4 accent-[#0097A7]"
            :checked="svc.assigned"
            :disabled="saving"
            @change="toggleService(svc.service_id, svc.assigned)"
          >
        </label>
        <p v-if="!doctor.services.length" class="p-6 text-center text-sm text-slate-500">
          No clinic services yet. Add some under Clinic settings.
        </p>
      </div>
    </div>
  </div>

  <div v-else class="p-4 md:p-5">
    <div
      v-if="error"
      class="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
    >
      {{ error }}
    </div>

    <div class="mb-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 class="mb-2 text-sm font-semibold text-slate-800">Add doctor</h3>
      <div class="mb-3 flex gap-2 text-sm">
        <button
          type="button"
          class="rounded-md px-2 py-1"
          :class="addMode === 'user' ? 'bg-[#0097A7]/15 text-[#0097A7]' : 'text-slate-500'"
          @click="addMode = 'user'"
        >
          From user
        </button>
        <button
          type="button"
          class="rounded-md px-2 py-1"
          :class="addMode === 'name' ? 'bg-[#0097A7]/15 text-[#0097A7]' : 'text-slate-500'"
          @click="addMode = 'name'"
        >
          By name
        </button>
      </div>
      <div class="flex flex-col gap-2 sm:flex-row">
        <select
          v-if="addMode === 'user'"
          v-model="addUserId"
          class="min-w-0 flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm"
        >
          <option value="">Select user…</option>
          <option v-for="u in eligibleUsers" :key="u.user_id" :value="u.user_id">
            {{ u.full_name }} ({{ u.role }})
          </option>
        </select>
        <UInput
          v-else
          v-model="addDoctorName"
          class="min-w-0 flex-1"
          placeholder="Doctor display name"
        />
        <UButton
          class="bg-[#0097A7]"
          :loading="saving"
          :disabled="addMode === 'user' ? !addUserId : !addDoctorName.trim()"
          @click="handleAddDoctor"
        >
          Add doctor
        </UButton>
      </div>
      <p
        v-if="addMode === 'user' && !eligibleUsers.length"
        class="mt-2 text-xs text-slate-500"
      >
        No eligible users left to link. Add by name instead.
      </p>
    </div>

    <div
      v-if="doctors.length"
      class="mb-4 rounded-xl border border-slate-200 bg-[#F8FAFC] p-4 shadow-sm"
    >
      <h3 class="mb-1 text-sm font-semibold text-slate-800">Doctor time off</h3>
      <p class="mb-3 text-xs text-slate-500">
        Block doctors from appointments — full days or specific time ranges.
      </p>

      <div v-if="timeOffFormOpen" class="mb-3 rounded-xl border border-slate-200 bg-white p-4">
        <div class="grid gap-3 md:grid-cols-2">
          <UFormField label="Doctor" class="md:col-span-2">
            <select
              v-model="timeOffForm.doctorId"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            >
              <option value="">Select doctor…</option>
              <option v-for="d in doctors" :key="d.doctor_id" :value="String(d.doctor_id)">
                {{ d.full_name }}
              </option>
            </select>
          </UFormField>
          <UFormField label="Start date">
            <UInput v-model="timeOffForm.startDate" type="date" class="w-full" />
          </UFormField>
          <UFormField label="End date">
            <UInput v-model="timeOffForm.endDate" type="date" class="w-full" />
          </UFormField>
          <label class="flex items-center gap-2 text-sm md:col-span-2">
            <input v-model="timeOffForm.fullDay" type="checkbox" class="accent-[#0097A7]">
            Full day(s)
          </label>
          <template v-if="!timeOffForm.fullDay">
            <UFormField label="Start time">
              <input
                v-model="timeOffForm.startTime"
                type="time"
                class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              >
            </UFormField>
            <UFormField label="End time">
              <input
                v-model="timeOffForm.endTime"
                type="time"
                class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              >
            </UFormField>
          </template>
          <UFormField label="Reason" class="md:col-span-2">
            <UInput v-model="timeOffForm.reason" class="w-full" />
          </UFormField>
        </div>
        <div class="mt-3 flex gap-2">
          <UButton class="bg-[#0097A7]" :loading="saving" @click="saveTimeOff()">Save</UButton>
          <UButton color="neutral" variant="outline" @click="resetTimeOffForm()">Cancel</UButton>
        </div>
      </div>
      <UButton v-else size="sm" class="mb-3 bg-[#0097A7]" @click="openTimeOffForm()">
        Add time off
      </UButton>

      <div class="rounded-lg border border-slate-200 bg-white">
        <p v-if="!upcomingTimeOff.length" class="p-4 text-sm text-slate-500">No upcoming time off.</p>
        <div v-else class="divide-y divide-slate-100">
          <div
            v-for="item in upcomingTimeOff"
            :key="item.time_off_id"
            class="flex flex-wrap items-center justify-between gap-2 px-3 py-2.5"
          >
            <div class="flex items-center gap-2">
              <span
                class="h-2.5 w-2.5 rounded-full"
                :style="{ backgroundColor: item.color_code }"
              />
              <div>
                <div class="text-sm font-medium text-slate-800">
                  {{ item.doctor_name }} · {{ formatTimeOffRange(item) }}
                </div>
                <div v-if="item.reason" class="text-xs text-slate-500">{{ item.reason }}</div>
              </div>
            </div>
            <div class="flex gap-1">
              <UButton size="xs" color="neutral" variant="ghost" @click="startEditTimeOff(item, item.doctor_id)">
                Edit
              </UButton>
              <UButton
                size="xs"
                color="error"
                variant="ghost"
                @click="deleteTimeOffEntry(item.doctor_id, item.time_off_id)"
              >
                Delete
              </UButton>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="loading" class="py-16 text-center text-sm text-slate-400">Loading…</div>
    <div
      v-else-if="!doctors.length"
      class="rounded-xl border border-slate-200 bg-white p-10 text-center text-sm text-slate-500"
    >
      No doctors in the appointments system yet. Add one above.
    </div>
    <div v-else class="rounded-xl border border-slate-200 bg-white shadow-sm">
      <button
        v-for="d in doctors"
        :key="d.doctor_id"
        type="button"
        class="flex w-full items-center gap-3 border-b border-slate-100 px-4 py-3 text-left last:border-b-0 hover:bg-slate-50"
        @click="openDoctor(d.doctor_id)"
      >
        <div
          class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-bold text-white"
          :style="{ backgroundColor: d.color_code }"
        >
          {{ initials(d.full_name) }}
        </div>
        <div class="min-w-0 flex-1">
          <div class="font-medium text-slate-800">{{ d.full_name }}</div>
          <div class="text-xs text-slate-500">
            {{ d.specialization || d.role }}
            <span v-if="!d.is_active"> · Inactive</span>
          </div>
        </div>
        <span class="text-sm text-slate-400">→</span>
      </button>
    </div>
  </div>
</template>
