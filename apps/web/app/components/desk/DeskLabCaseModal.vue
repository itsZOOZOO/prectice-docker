<script setup lang="ts">
import type { DentalLab, LabCaseListItem } from '~/utils/labTypes'
import {
  LAB_CASE_TYPE_CHIPS,
  addClinicWorkingDays,
  todayYmdLocal
} from '~/utils/labTypes'

const props = defineProps<{
  open: boolean
  caseId: number | null
}>()

const emit = defineEmits<{
  'update:open': [boolean]
  changed: []
  book: [payload: { clientId: number, clientName: string }]
}>()

const { api } = useApi()
const toast = useToast()

const detail = ref<LabCaseListItem | null>(null)
const loading = ref(false)
const busy = ref(false)
const expectedReturn = ref('')
const editType = ref('')
const editTeeth = ref('')
const editDesc = ref('')

const isOpen = computed({
  get: () => props.open,
  set: (v: boolean) => emit('update:open', v)
})

async function load() {
  if (!props.caseId) return
  loading.value = true
  try {
    detail.value = await api<LabCaseListItem>(`/lab-cases/${props.caseId}`)
    expectedReturn.value = detail.value.expected_return_date || addClinicWorkingDays(todayYmdLocal(), 3)
    editType.value = detail.value.case_type || ''
    editTeeth.value = detail.value.tooth_numbers || ''
    editDesc.value = detail.value.description || ''
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to load case', color: 'error' })
    isOpen.value = false
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.open, props.caseId] as const,
  ([open]) => {
    if (open && props.caseId) void load()
  }
)

async function setStage(stage: 'sent' | 'received', action: 'set' | 'clear' = 'set') {
  if (!detail.value) return
  busy.value = true
  try {
    const body: Record<string, string> = { stage, action }
    if (stage === 'sent' && action === 'set') {
      body.expected_return_date = expectedReturn.value
    }
    const data = await api<{ case: LabCaseListItem }>(
      `/lab-cases/${detail.value.case_id}/cycles/${detail.value.current_cycle_number}/stages`,
      { method: 'POST', body }
    )
    detail.value = data.case
    emit('changed')
    toast.add({ title: action === 'clear' ? 'Stage undone' : 'Stage updated', color: 'success' })
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
  } finally {
    busy.value = false
  }
}

async function saveEdit() {
  if (!detail.value) return
  busy.value = true
  try {
    detail.value = await api<LabCaseListItem>(`/lab-cases/${detail.value.case_id}`, {
      method: 'PATCH',
      body: {
        case_type: editType.value,
        tooth_numbers: editTeeth.value,
        description: editDesc.value,
        expected_return_date: expectedReturn.value || null
      }
    })
    emit('changed')
    toast.add({ title: 'Case updated', color: 'success' })
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
  } finally {
    busy.value = false
  }
}

async function closeCase() {
  if (!detail.value) return
  busy.value = true
  try {
    const data = await api<{ case: LabCaseListItem }>(`/lab-cases/${detail.value.case_id}/close`, {
      method: 'POST'
    })
    detail.value = data.case
    emit('changed')
    toast.add({ title: 'Case closed', color: 'success' })
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
  } finally {
    busy.value = false
  }
}

async function cancelCase() {
  if (!detail.value) return
  busy.value = true
  try {
    const data = await api<{ case: LabCaseListItem }>(`/lab-cases/${detail.value.case_id}/cancel`, {
      method: 'POST'
    })
    detail.value = data.case
    emit('changed')
    toast.add({ title: 'Case cancelled', color: 'success' })
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
  } finally {
    busy.value = false
  }
}

async function rework() {
  if (!detail.value) return
  busy.value = true
  try {
    const data = await api<{ case: LabCaseListItem }>(`/lab-cases/${detail.value.case_id}/cycles`, {
      method: 'POST'
    })
    detail.value = data.case
    expectedReturn.value = addClinicWorkingDays(todayYmdLocal(), 3)
    emit('changed')
    toast.add({ title: 'Rework cycle started', color: 'success' })
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
  } finally {
    busy.value = false
  }
}

function applyOffset(days: 3 | 4) {
  expectedReturn.value = addClinicWorkingDays(todayYmdLocal(), days)
}
</script>

<template>
  <UModal v-model:open="isOpen" :title="detail?.case_ref || 'Lab case'">
    <template #body>
      <p v-if="loading" class="text-sm text-slate-400">Loading…</p>
      <div v-else-if="detail" class="space-y-4">
        <div>
          <p class="text-sm font-medium text-[#1C2B35]">{{ detail.client_name }}</p>
          <p class="text-xs text-slate-500">
            {{ detail.lab_name }}
            <span v-if="detail.case_type"> · {{ detail.case_type }}</span>
            <span v-if="detail.tooth_numbers"> · #{{ detail.tooth_numbers }}</span>
            · cycle {{ detail.current_cycle_number }}
          </p>
          <p class="mt-1 text-xs capitalize text-slate-500">{{ detail.stage.replace('_', ' ') }} · {{ detail.status }}</p>
        </div>

        <div v-if="detail.status === 'open'" class="space-y-3 rounded-xl border border-slate-200 p-3">
          <UFormField label="Case type">
            <div class="mb-2 flex flex-wrap gap-1">
              <button
                v-for="chip in LAB_CASE_TYPE_CHIPS"
                :key="chip"
                type="button"
                class="rounded-full border px-2.5 py-0.5 text-[11px]"
                :class="editType === chip ? 'border-[#0097A7] bg-[#e0f7fa] text-[#0097A7]' : 'border-slate-200 text-slate-600'"
                @click="editType = chip"
              >
                {{ chip }}
              </button>
            </div>
            <UInput v-model="editType" class="w-full" />
          </UFormField>
          <UFormField label="Teeth">
            <UInput v-model="editTeeth" class="w-full" placeholder="e.g. 11,12" />
          </UFormField>
          <UFormField label="Notes">
            <UTextarea v-model="editDesc" class="w-full" :rows="2" />
          </UFormField>
          <UFormField label="Expected return">
            <div class="mb-2 flex gap-1">
              <UButton size="xs" color="neutral" variant="outline" @click="applyOffset(3)">After 3 days</UButton>
              <UButton size="xs" color="neutral" variant="outline" @click="applyOffset(4)">After 4 days</UButton>
            </div>
            <UInput v-model="expectedReturn" type="date" class="w-full" />
          </UFormField>
          <UButton size="sm" color="neutral" variant="outline" :loading="busy" @click="saveEdit">Save details</UButton>
        </div>

        <div v-if="detail.status === 'open'" class="flex flex-wrap gap-2">
          <UButton
            v-if="detail.stage === 'send_pending'"
            class="bg-[#0097A7]"
            :loading="busy"
            @click="setStage('sent')"
          >
            Mark sent
          </UButton>
          <UButton
            v-if="detail.stage === 'at_lab'"
            class="bg-[#0097A7]"
            :loading="busy"
            @click="setStage('received')"
          >
            Mark received
          </UButton>
          <UButton
            v-if="detail.stage === 'at_lab'"
            color="neutral"
            variant="outline"
            :loading="busy"
            @click="setStage('sent', 'clear')"
          >
            Undo sent
          </UButton>
          <UButton
            v-if="detail.stage === 'received'"
            color="neutral"
            variant="outline"
            :loading="busy"
            @click="setStage('received', 'clear')"
          >
            Undo received
          </UButton>
          <UButton
            v-if="detail.stage === 'received'"
            color="neutral"
            variant="outline"
            :loading="busy"
            @click="rework"
          >
            Start rework
          </UButton>
          <UButton
            v-if="detail.action_category === 'received_no_future_appointment'"
            color="primary"
            variant="soft"
            @click="emit('book', { clientId: detail.client_id, clientName: detail.client_name })"
          >
            Book appointment
          </UButton>
          <UButton color="success" variant="soft" :loading="busy" @click="closeCase">Close</UButton>
          <UButton color="error" variant="ghost" :loading="busy" @click="cancelCase">Cancel</UButton>
        </div>

        <div v-if="detail.cycles?.length" class="space-y-2">
          <p class="text-xs font-medium uppercase tracking-wide text-slate-400">Cycles</p>
          <div
            v-for="c in detail.cycles"
            :key="c.cycle_id"
            class="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-xs text-slate-600"
          >
            #{{ c.cycle_number }} · {{ c.stage }}
            <span v-if="c.expected_return_date"> · return {{ c.expected_return_date }}</span>
          </div>
        </div>
      </div>
    </template>
  </UModal>
</template>
