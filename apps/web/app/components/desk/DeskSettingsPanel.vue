<script setup lang="ts">
import type { ClinicSettingsTab } from '~/utils/clinicSettings'
import type { DoctorDetailTab } from '~/utils/doctorSettings'
import type { SettingsSection } from '~/composables/useDeskUrl'
import { isSetupSectionLocked } from '~/utils/setupAccess'

type DeskMasterItem = {
  id: string
  label: string
  description?: string
  icon?: string
  locked?: boolean
}

const BASE_SETTINGS_ITEMS: Omit<DeskMasterItem, 'locked'>[] = [
  {
    id: 'clinic-settings',
    label: 'Clinic settings',
    description: 'Hours, booking rules & services',
    icon: '🏢'
  },
  {
    id: 'doctors-schedules',
    label: 'Doctors & schedules',
    description: 'Per-doctor hours, breaks & leave',
    icon: '🗓️'
  },
  {
    id: 'patient-lists',
    label: 'Patient lists',
    description: 'Saved filters for dashboard & search',
    icon: '📋'
  },
  {
    id: 'client-tags',
    label: 'Client tags',
    description: 'Tags for profiles & patient list filters',
    icon: '🏷️'
  },
  {
    id: 'dental-labs',
    label: 'Dental labs',
    description: 'Lab partners for case orders',
    icon: '🔬'
  },
  {
    id: 'whatsapp',
    label: 'WhatsApp',
    description: 'Appointment confirm messaging',
    icon: '💬'
  },
  {
    id: 'medicine-templates',
    label: 'Medicine templates',
    description: 'Prescribing catalog defaults',
    icon: '💊'
  },
  {
    id: 'treatment-templates',
    label: 'Treatment templates',
    description: 'Catalog, pricing & photos',
    icon: '🦷'
  },
  {
    id: 'warranty-templates',
    label: 'Warranty templates',
    description: 'Card types, terms & issued cards',
    icon: '🛡️'
  },
  {
    id: 'lead-intelligence',
    label: 'Lead Intelligence',
    description: 'Managed by superadmin',
    icon: '📈'
  },
  {
    id: 'setup-pin',
    label: 'Setup PIN',
    description: 'Lock sensitive settings',
    icon: '🔐'
  }
]

const { settingsSection, setSettingsSection } = useDeskUrl()
const { api } = useApi()
const {
  pinConfigured,
  isUnlocked,
  fetchStatus,
  needsUnlock
} = useSetupAccess()

const clinicTab = ref<ClinicSettingsTab>('hours')
const doctorDetailTab = ref<DoctorDetailTab>('schedule')
const doctorsInDetail = ref(false)
const unlockOpen = ref(false)
const pendingSection = ref<string | null>(null)

type LeadStatus = {
  enabled: boolean
  has_api_key: boolean
  can_use: boolean
  linked_user: { id: number, name: string | null, email: string | null } | null
}
const leadStatus = ref<LeadStatus | null>(null)

async function loadLeadStatus() {
  try {
    leadStatus.value = await api<LeadStatus>('/settings/lead-intelligence')
  } catch {
    leadStatus.value = null
  }
}

const settingsItems = computed<DeskMasterItem[]>(() =>
  BASE_SETTINGS_ITEMS.map(item => ({
    ...item,
    locked: Boolean(
      pinConfigured.value
      && !isUnlocked.value
      && isSetupSectionLocked(item.id)
    )
  }))
)

const selectedId = computed({
  get: () => settingsSection.value,
  set: (id: string | null) => {
    void setSettingsSection(id)
  }
})

const detailGated = computed(() => {
  const id = selectedId.value
  if (!id) return false
  return needsUnlock(id)
})

onMounted(async () => {
  void loadLeadStatus()
  try {
    await fetchStatus()
  } catch {
    // Status fetch failure shouldn't block settings shell.
  }
  if (!settingsSection.value && import.meta.client) {
    const wide = window.matchMedia('(min-width: 1024px)').matches
    if (wide) void setSettingsSection('clinic-settings')
  }
})

function onSelect(id: string | null) {
  if (id && needsUnlock(id)) {
    pendingSection.value = id
    selectedId.value = id
    unlockOpen.value = true
    if (id !== 'doctors-schedules') doctorsInDetail.value = false
    return
  }
  pendingSection.value = null
  selectedId.value = id
  if (id !== 'doctors-schedules') doctorsInDetail.value = false
}

function onUnlocked() {
  const target = pendingSection.value || selectedId.value
  unlockOpen.value = false
  pendingSection.value = null
  if (target) selectedId.value = target
}

function isSection(id: string): id is SettingsSection {
  return BASE_SETTINGS_ITEMS.some(item => item.id === id)
}
</script>

<template>
  <DeskMasterDetailPanel
    :items="settingsItems"
    :selected-id="selectedId"
    empty-message="Select a settings section"
    :hide-detail-header="true"
    @update:selected-id="onSelect"
  >
    <template #detail-header="{ item }">
      <div v-if="item.id === 'clinic-settings' && !detailGated" class="flex max-w-xl gap-1 rounded-lg bg-slate-100 p-1">
        <button
          v-for="entry in [
            { key: 'hours' as const, label: 'Clinic hours' },
            { key: 'booking' as const, label: 'Booking rules' },
            { key: 'services' as const, label: 'Services' }
          ]"
          :key="entry.key"
          type="button"
          class="flex-1 rounded-md px-3 py-2 text-sm font-medium transition"
          :class="clinicTab === entry.key
            ? 'bg-white text-[#0097A7] shadow-sm'
            : 'text-slate-600 hover:text-slate-800'"
          @click="clinicTab = entry.key"
        >
          {{ entry.label }}
        </button>
      </div>
      <div
        v-else-if="item.id === 'doctors-schedules' && doctorsInDetail && !detailGated"
        class="flex max-w-2xl gap-1 overflow-x-auto rounded-lg bg-slate-100 p-1"
      >
        <button
          v-for="entry in [
            { key: 'schedule' as const, label: 'Schedule' },
            { key: 'breaks' as const, label: 'Breaks' },
            { key: 'time-off' as const, label: 'Time off' },
            { key: 'services' as const, label: 'Services' }
          ]"
          :key="entry.key"
          type="button"
          class="shrink-0 rounded-md px-3 py-2 text-sm font-medium transition"
          :class="doctorDetailTab === entry.key
            ? 'bg-white text-[#0097A7] shadow-sm'
            : 'text-slate-600 hover:text-slate-800'"
          @click="doctorDetailTab = entry.key"
        >
          {{ entry.label }}
        </button>
      </div>
      <div v-else-if="item.id === 'doctors-schedules'" class="min-w-0">
        <h2 class="truncate text-base font-semibold text-slate-800">{{ item.label }}</h2>
        <p v-if="item.description" class="truncate text-xs text-slate-500">{{ item.description }}</p>
      </div>
      <div v-else class="min-w-0">
        <h2 class="truncate text-base font-semibold text-slate-800">{{ item.label }}</h2>
        <p v-if="item.description" class="truncate text-xs text-slate-500">{{ item.description }}</p>
      </div>
    </template>

    <template #detail="{ itemId }">
      <div
        v-if="detailGated"
        class="flex h-full flex-col items-center justify-center gap-3 p-8 text-center"
      >
        <span class="text-4xl opacity-40">🔒</span>
        <h3 class="text-base font-semibold text-slate-800">Setup locked</h3>
        <p class="max-w-sm text-sm text-slate-500">
          Enter the clinic setup PIN to view and edit this section.
        </p>
        <button
          type="button"
          class="rounded-lg bg-[#0097A7] px-4 py-2 text-sm font-semibold text-white hover:bg-[#00838f]"
          @click="unlockOpen = true"
        >
          Unlock with PIN
        </button>
      </div>
      <template v-else>
        <DeskClinicSettingsPanel
          v-if="itemId === 'clinic-settings'"
          v-model:tab="clinicTab"
          hide-tab-bar
        />
        <DeskDoctorsSchedulesPanel
          v-else-if="itemId === 'doctors-schedules'"
          v-model:detail-tab="doctorDetailTab"
          hide-detail-tab-bar
          @detail-view-change="doctorsInDetail = $event"
        />
        <DeskClientFiltersPanel v-else-if="itemId === 'patient-lists'" />
        <DeskClientTagsSettingsPanel v-else-if="itemId === 'client-tags'" />
        <DeskLabsSettingsPanel v-else-if="itemId === 'dental-labs'" />
        <DeskWhatsAppSettingsPanel v-else-if="itemId === 'whatsapp'" />
        <DeskMedicineTemplatesPanel v-else-if="itemId === 'medicine-templates'" />
        <DeskTreatmentTemplatesPanel v-else-if="itemId === 'treatment-templates'" />
        <DeskWarrantyTemplatesPanel v-else-if="itemId === 'warranty-templates'" />
        <DeskSetupPinSettingsPanel v-else-if="itemId === 'setup-pin'" />
        <div
          v-else-if="itemId === 'lead-intelligence'"
          class="flex h-full flex-col items-center justify-center gap-2 p-8 text-center"
        >
          <span class="text-4xl opacity-30">📈</span>
          <h3 class="text-base font-semibold text-slate-800">Lead Intelligence</h3>
          <p class="max-w-sm text-sm text-slate-500">
            Linking is managed by superadmin. When enabled for your clinic, the report appears under Reports.
          </p>
          <p
            v-if="leadStatus"
            class="mt-2 rounded-full px-3 py-1 text-xs font-semibold"
            :class="leadStatus.can_use
              ? 'bg-emerald-50 text-emerald-800'
              : 'bg-slate-100 text-slate-600'"
          >
            <template v-if="leadStatus.can_use">
              Connected
              <template v-if="leadStatus.linked_user?.name || leadStatus.linked_user?.email">
                · {{ leadStatus.linked_user?.name || leadStatus.linked_user?.email }}
              </template>
            </template>
            <template v-else-if="leadStatus.enabled">
              Enabled — waiting for API token
            </template>
            <template v-else>
              Not enabled for this clinic
            </template>
          </p>
        </div>
        <div v-else-if="isSection(itemId)" class="p-6 text-sm text-slate-500">Unknown section.</div>
      </template>
    </template>
  </DeskMasterDetailPanel>

  <DeskSetupUnlockModal v-model:open="unlockOpen" @unlocked="onUnlocked" />
</template>
