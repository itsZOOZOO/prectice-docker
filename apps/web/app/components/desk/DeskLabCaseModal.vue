<script setup lang="ts">
import type { LabCaseListItem } from '~/utils/labTypes'
import {
  LAB_CASE_TYPE_CHIPS,
  addClinicWorkingDays,
  labCaseStatusColor,
  labCaseStatusLabel,
  todayYmdLocal
} from '~/utils/labTypes'

const open = defineModel<boolean>('open', { default: false })
const props = defineProps<{
  caseId: number | null
}>()

const emit = defineEmits<{
  changed: []
  book: [payload: { clientId: number, clientName: string }]
}>()

const { api } = useApi()
const toast = useToast()
const router = useRouter()

const detail = ref<LabCaseListItem | null>(null)
const loading = ref(false)
const busy = ref(false)
const expectedReturn = ref('')
const editType = ref('')
const editTeeth = ref('')
const editDesc = ref('')

const menuItems = computed(() => {
  const openCase = detail.value?.status === 'open'
  return [[
    {
      label: 'Close case',
      icon: 'i-lucide-check-circle',
      disabled: busy.value || !detail.value || !openCase,
      onSelect: () => { void closeCase() }
    },
    {
      label: 'Cancel case',
      color: 'error' as const,
      icon: 'i-lucide-ban',
      disabled: busy.value || !detail.value || !openCase,
      onSelect: () => { void cancelCase() }
    }
  ]]
})

watch(
  () => [open.value, props.caseId] as const,
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
    detail.value = await api<LabCaseListItem>(`/lab-cases/${id}`)
    expectedReturn.value = detail.value.expected_return_date || addClinicWorkingDays(todayYmdLocal(), 3)
    editType.value = detail.value.case_type || ''
    editTeeth.value = detail.value.tooth_numbers || ''
    editDesc.value = detail.value.description || ''
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to load case', color: 'error' })
    open.value = false
  } finally {
    loading.value = false
  }
}

async function setStage(stage: 'sent' | 'received', action: 'set' | 'clear' = 'set') {
  if (!detail.value) return
  if (action === 'set') {
    if (stage === 'sent') {
      if (!expectedReturn.value) {
        toast.add({ title: 'Set expected return date before marking sent', color: 'warning' })
        return
      }
      const msg = `Mark ${detail.value.case_ref} (cycle ${detail.value.current_cycle_number}) as sent to ${detail.value.lab_name}?\nExpected return: ${expectedReturn.value}`
      if (!window.confirm(msg)) return
    } else {
      const msg = `Mark ${detail.value.case_ref} (cycle ${detail.value.current_cycle_number}) as received from ${detail.value.lab_name}?`
      if (!window.confirm(msg)) return
    }
  }
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
  if (!window.confirm('Close this lab case?')) return
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
  if (!window.confirm('Cancel this lab case?')) return
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

async function startNextStage() {
  if (!detail.value) return
  const next = detail.value.current_cycle_number + 1
  if (!window.confirm(
    `Start next stage for ${detail.value.case_ref}?\nThis opens cycle ${next} (send pending again).`
  )) return
  busy.value = true
  try {
    const data = await api<{ case: LabCaseListItem }>(`/lab-cases/${detail.value.case_id}/cycles`, {
      method: 'POST'
    })
    detail.value = data.case
    expectedReturn.value = addClinicWorkingDays(todayYmdLocal(), 3)
    emit('changed')
    toast.add({ title: `Stage ${next} started`, color: 'success' })
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
  } finally {
    busy.value = false
  }
}

function applyOffset(days: 3 | 4) {
  expectedReturn.value = addClinicWorkingDays(todayYmdLocal(), days)
}

function openPatient() {
  if (!detail.value?.client_id) return
  const id = detail.value.client_id
  open.value = false
  void router.push(`/clients/${id}`)
}
</script>

<template>
  <UModal
    v-model:open="open"
    :close="false"
    :ui="{ content: 'sm:max-w-md', header: 'flex items-center gap-1.5 p-4 sm:px-6' }"
  >
    <template #header>
      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-2">
          <span
            v-if="detail && !loading"
            class="rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white"
            :style="{ background: labCaseStatusColor(detail) }"
          >
            {{ labCaseStatusLabel(detail) }}
          </span>
          <span
            v-else
            class="rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide bg-slate-300 text-white"
          >
            Lab case
          </span>
        </div>
        <p
          v-if="detail && !loading"
          class="mt-1 truncate text-sm font-semibold text-[#1C2B35]"
        >
          {{ detail.client_name }}
        </p>
        <p
          v-else-if="loading"
          class="mt-1 text-sm text-slate-400"
        >
          Loading…
        </p>
        <p
          v-if="detail && !loading"
          class="mt-0.5 truncate text-xs text-slate-500"
        >
          {{ detail.lab_name }}
          <span v-if="detail.case_ref"> · {{ detail.case_ref }}</span>
        </p>
      </div>
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
            :disabled="!detail || busy"
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
      <div
        v-if="detail && !loading"
        class="space-y-4"
      >
        <div class="flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-600">
          <span v-if="detail.case_type">{{ detail.case_type }}</span>
          <span v-if="detail.tooth_numbers">#{{ detail.tooth_numbers }}</span>
          <span>Cycle {{ detail.current_cycle_number }}</span>
          <span
            v-if="detail.expected_return_date"
            class="text-slate-400"
          >Expected {{ detail.expected_return_date }}</span>
        </div>

        <div class="flex flex-wrap gap-2">
          <UButton
            color="neutral"
            variant="outline"
            size="sm"
            @click="openPatient"
          >
            Open patient
          </UButton>
          <UButton
            v-if="detail.status === 'open' && detail.stage === 'send_pending'"
            class="bg-[#0097A7]"
            size="sm"
            :loading="busy"
            :disabled="!expectedReturn"
            @click="setStage('sent')"
          >
            Mark sent
          </UButton>
          <UButton
            v-if="detail.status === 'open' && detail.stage === 'at_lab'"
            class="bg-[#0097A7]"
            size="sm"
            :loading="busy"
            @click="setStage('received')"
          >
            Mark received
          </UButton>
          <UButton
            v-if="detail.status === 'open' && detail.stage === 'at_lab'"
            color="neutral"
            variant="outline"
            size="sm"
            :loading="busy"
            @click="setStage('sent', 'clear')"
          >
            Undo sent
          </UButton>
          <UButton
            v-if="detail.status === 'open' && detail.stage === 'received'"
            color="neutral"
            variant="outline"
            size="sm"
            :loading="busy"
            @click="setStage('received', 'clear')"
          >
            Undo received
          </UButton>
          <UButton
            v-if="detail.status === 'open' && detail.action_category === 'received_no_future_appointment'"
            class="bg-[#0097A7]"
            size="sm"
            @click="emit('book', { clientId: detail.client_id, clientName: detail.client_name })"
          >
            Book appointment
          </UButton>
          <UButton
            v-if="detail.status === 'open' && detail.stage === 'received'"
            color="neutral"
            variant="outline"
            size="sm"
            :loading="busy"
            @click="startNextStage"
          >
            Start next stage
          </UButton>
        </div>

        <div
          v-if="detail.status === 'open'"
          class="space-y-3 rounded-xl border border-slate-200 p-3"
        >
          <p class="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
            Edit details
          </p>
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
            <UInput
              v-model="editType"
              class="w-full"
            />
          </UFormField>
          <UFormField label="Teeth">
            <UInput
              v-model="editTeeth"
              class="w-full"
              placeholder="e.g. 11,12"
            />
          </UFormField>
          <UFormField label="Notes">
            <UTextarea
              v-model="editDesc"
              class="w-full"
              :rows="2"
            />
          </UFormField>
          <UFormField label="Expected return">
            <div class="mb-2 flex gap-1">
              <UButton
                size="xs"
                color="neutral"
                variant="outline"
                @click="applyOffset(3)"
              >
                After 3 days
              </UButton>
              <UButton
                size="xs"
                color="neutral"
                variant="outline"
                @click="applyOffset(4)"
              >
                After 4 days
              </UButton>
            </div>
            <UInput
              v-model="expectedReturn"
              type="date"
              class="w-full"
            />
          </UFormField>
          <UButton
            size="sm"
            color="neutral"
            variant="outline"
            :loading="busy"
            @click="saveEdit"
          >
            Save details
          </UButton>
        </div>

        <div
          v-if="detail.cycles?.length"
          class="space-y-2"
        >
          <p class="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
            Cycles
          </p>
          <div
            v-for="c in detail.cycles"
            :key="c.cycle_id"
            class="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-xs text-slate-600"
          >
            #{{ c.cycle_number }} · {{ c.stage.replace(/_/g, ' ') }}
            <span v-if="c.expected_return_date"> · return {{ c.expected_return_date }}</span>
          </div>
        </div>
      </div>
      <p
        v-else-if="loading"
        class="text-sm text-slate-400"
      >
        Loading…
      </p>
    </template>
  </UModal>
</template>
