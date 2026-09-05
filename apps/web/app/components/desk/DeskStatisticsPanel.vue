<script setup lang="ts">
import type { DeskMasterItem } from '~/components/desk/DeskMasterDetailPanel.vue'
import type { CallIntelligenceClinicStatus } from '~/utils/callStatistics'
import type { LeadIntelligenceClinicStatus } from '~/utils/leadIntelligence'
import type { OverviewTab } from '~/utils/statistics'

const BASE_ITEMS: DeskMasterItem[] = [
  {
    id: 'total-patients',
    label: 'Total patients',
    description: 'Yearly new cases report',
    icon: '👥'
  },
  {
    id: 'appointments-overview',
    label: 'Appointments overview',
    description: 'Status, attendance & no-shows',
    icon: '📅'
  },
  {
    id: 'total-income',
    label: 'Total income',
    description: 'Revenue & collections',
    icon: '₹'
  },
  {
    id: 'checkins-overview',
    label: 'Check-ins overview',
    description: 'Visit volume, weekday & hourly trends',
    icon: '✓'
  },
  {
    id: 'inquiry-conversion',
    label: 'Client conversion',
    description: 'Inquiry vs converted — yearly & by month',
    icon: '📈'
  }
]

const CALL_ITEM: DeskMasterItem = {
  id: 'call-statistics',
  label: 'Call statistics',
  description: 'Incoming & outgoing call volume',
  icon: '📞'
}

const LEAD_ITEM: DeskMasterItem = {
  id: 'lead-intelligence',
  label: 'Lead Intelligence',
  description: 'Lead response times & contact rate',
  icon: '📈'
}

const OVERVIEW_IDS = new Set([
  'total-patients',
  'appointments-overview',
  'total-income',
  'checkins-overview',
  'inquiry-conversion'
])

const TABBED_IDS = new Set([
  'total-patients',
  'appointments-overview',
  'total-income',
  'checkins-overview',
  'inquiry-conversion'
])

const { statisticsSection, setStatisticsSection } = useDeskUrl()
const { api } = useApi()
const { pinConfigured, isUnlocked, fetchStatus } = useSetupAccess()
const unlockOpen = ref(false)

const reportsLocked = computed(() => pinConfigured.value && !isUnlocked.value)
const callStatus = ref<CallIntelligenceClinicStatus | null>(null)
const leadStatus = ref<LeadIntelligenceClinicStatus | null>(null)

const items = computed<DeskMasterItem[]>(() => {
  const next = [...BASE_ITEMS]
  if (callStatus.value?.can_use) next.push(CALL_ITEM)
  if (leadStatus.value?.can_use) next.push(LEAD_ITEM)
  return next
})

const patientsTab = ref<OverviewTab>('yearly')
const appointmentsTab = ref<OverviewTab>('monthly')
const incomeTab = ref<OverviewTab>('yearly')
const checkinsTab = ref<OverviewTab>('monthly')
const conversionTab = ref<OverviewTab>('yearly')

const selectedId = computed({
  get: () => statisticsSection.value,
  set: (id: string | null) => {
    void setStatisticsSection(id)
  }
})

const activeTab = computed({
  get: () => {
    const id = selectedId.value
    if (id === 'total-patients') return patientsTab.value
    if (id === 'appointments-overview') return appointmentsTab.value
    if (id === 'total-income') return incomeTab.value
    if (id === 'checkins-overview') return checkinsTab.value
    if (id === 'inquiry-conversion') return conversionTab.value
    return 'yearly' as OverviewTab
  },
  set: (v: OverviewTab) => {
    const id = selectedId.value
    if (id === 'total-patients') patientsTab.value = v
    else if (id === 'appointments-overview') appointmentsTab.value = v
    else if (id === 'total-income') incomeTab.value = v
    else if (id === 'checkins-overview') checkinsTab.value = v
    else if (id === 'inquiry-conversion') conversionTab.value = v
  }
})

async function loadIntegrationStatus() {
  try {
    callStatus.value = await api<CallIntelligenceClinicStatus>('/settings/call-intelligence')
  } catch {
    callStatus.value = { enabled: false, has_token: false, can_use: false }
  }
  try {
    leadStatus.value = await api<LeadIntelligenceClinicStatus>('/settings/lead-intelligence')
  } catch {
    leadStatus.value = {
      enabled: false,
      has_api_key: false,
      can_use: false,
      can_manage_link: false,
      linked_user: null
    }
  }
}

onMounted(() => {
  void fetchStatus().catch(() => { /* ignore */ })
  void loadIntegrationStatus()
  if (!statisticsSection.value) {
    void setStatisticsSection('total-patients')
  }
})

watch(items, (list) => {
  if (selectedId.value === 'call-statistics' && !list.some(i => i.id === 'call-statistics')) {
    void setStatisticsSection('total-patients')
  }
  if (selectedId.value === 'lead-intelligence' && !list.some(i => i.id === 'lead-intelligence')) {
    void setStatisticsSection('total-patients')
  }
})

function hideHeader(itemId: string) {
  return OVERVIEW_IDS.has(itemId) || itemId === 'call-statistics' || itemId === 'lead-intelligence'
}
</script>

<template>
  <div class="relative h-full min-h-0">
    <div
      v-if="reportsLocked"
      class="absolute inset-0 z-20 flex flex-col items-center justify-center gap-3 bg-[#f4f6f9]/95 p-8 text-center"
    >
      <span class="text-4xl opacity-40">🔒</span>
      <h3 class="text-base font-semibold text-slate-800">Reports are locked</h3>
      <p class="max-w-sm text-sm text-slate-500">
        Unlock with the clinic setup PIN to view clinic reports.
      </p>
      <button
        type="button"
        class="rounded-lg bg-[#0097A7] px-4 py-2 text-sm font-semibold text-white hover:bg-[#00838f]"
        @click="unlockOpen = true"
      >
        Unlock
      </button>
      <DeskSetupUnlockModal v-model:open="unlockOpen" />
    </div>

    <DeskMasterDetailPanel
      v-model:selected-id="selectedId"
      :items="items"
      empty-message="Select a report"
      :hide-detail-header="hideHeader"
    >
      <template #detail-header="{ item }">
        <div
          v-if="TABBED_IDS.has(item.id)"
          class="flex w-full items-center gap-2"
        >
          <div class="flex min-w-0 flex-1 gap-1 rounded-lg bg-slate-100 p-1">
            <button
              v-for="opt in (['yearly', 'monthly'] as const)"
              :key="opt"
              type="button"
              class="flex-1 rounded-md px-3 py-1.5 text-sm font-semibold capitalize transition"
              :class="activeTab === opt
                ? 'bg-white text-[#0097A7] shadow-sm'
                : 'text-slate-600 hover:text-slate-800'"
              @click="activeTab = opt"
            >
              {{ opt }}
            </button>
          </div>
        </div>
        <template v-else-if="item.id === 'call-statistics' || item.id === 'lead-intelligence'">
          <h2 class="truncate text-base font-semibold text-slate-800">{{ item.label }}</h2>
        </template>
        <template v-else>
          <h2 class="truncate text-base font-semibold text-slate-800">{{ item.label }}</h2>
        </template>
      </template>

      <template #detail="{ item }">
        <DeskPatientsOverview
          v-if="item.id === 'total-patients'"
          v-model:tab="patientsTab"
        />
        <DeskAppointmentsOverview
          v-else-if="item.id === 'appointments-overview'"
          v-model:tab="appointmentsTab"
        />
        <DeskIncomeOverview
          v-else-if="item.id === 'total-income'"
          v-model:tab="incomeTab"
        />
        <DeskCheckinsOverview
          v-else-if="item.id === 'checkins-overview'"
          v-model:tab="checkinsTab"
        />
        <DeskInquiryConversionOverview
          v-else-if="item.id === 'inquiry-conversion'"
          v-model:tab="conversionTab"
        />
        <DeskCallStatisticsPanel
          v-else-if="item.id === 'call-statistics'"
        />
        <DeskLeadIntelligencePanel
          v-else-if="item.id === 'lead-intelligence'"
        />
      </template>
    </DeskMasterDetailPanel>
  </div>
</template>
