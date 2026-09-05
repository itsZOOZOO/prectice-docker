<script setup lang="ts">
import { formatInrAmount } from '~/utils/lastPayment'

type TodayReceipt = {
  receipt_id: number
  client_id: number
  client_name?: string
  amount: number
  payment_mode: string
  description?: string | null
  received_at: string
}

const props = defineProps<{
  open: boolean
  receipts: TodayReceipt[]
  total: number
}>()

const emit = defineEmits<{
  'update:open': [boolean]
  openPatient: [clientId: number]
}>()

const isOpen = computed({
  get: () => props.open,
  set: (v: boolean) => emit('update:open', v)
})

const hasAnyNote = computed(() =>
  props.receipts.some(r => !!(r.description && r.description.trim()))
)

function formatReceiptTime(iso: string) {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('en-IN', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true
  })
}

function onPatient(clientId: number) {
  emit('openPatient', clientId)
  isOpen.value = false
}
</script>

<template>
  <UModal
    v-model:open="isOpen"
    title="Today's receipts"
    :ui="{ content: 'sm:max-w-3xl' }"
  >
    <template #body>
      <div v-if="!receipts.length" class="py-8 text-center text-sm text-slate-400">
        No receipts recorded today.
      </div>
      <div
        v-else
        class="max-h-[60vh] overflow-auto"
      >
        <table class="w-full border-collapse text-sm">
          <thead>
            <tr class="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <th class="px-3 py-2">Patient</th>
              <th class="px-3 py-2">Amount</th>
              <th class="px-3 py-2">Mode</th>
              <th
                v-if="hasAnyNote"
                class="px-3 py-2"
              >
                Note
              </th>
              <th class="px-3 py-2">Time</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in receipts"
              :key="row.receipt_id"
              class="border-b border-slate-100"
            >
              <td class="px-3 py-2">
                <button
                  type="button"
                  class="font-medium text-[#0097A7] hover:underline"
                  @click="onPatient(row.client_id)"
                >
                  {{ row.client_name || `Patient #${row.client_id}` }}
                </button>
              </td>
              <td class="px-3 py-2 font-semibold text-[#1C2B35]">
                {{ formatInrAmount(row.amount) }}
              </td>
              <td class="px-3 py-2 text-slate-600">
                {{ row.payment_mode || '—' }}
              </td>
              <td
                v-if="hasAnyNote"
                class="max-w-[12rem] px-3 py-2 text-slate-600"
              >
                {{ (row.description && row.description.trim()) || '—' }}
              </td>
              <td class="whitespace-nowrap px-3 py-2 text-slate-600">
                {{ formatReceiptTime(row.received_at) }}
              </td>
            </tr>
          </tbody>
          <tfoot>
            <tr class="bg-slate-50 font-semibold text-[#1C2B35]">
              <td
                class="px-3 py-3"
                :colspan="hasAnyNote ? 5 : 4"
              >
                Total: {{ formatInrAmount(total) }}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </template>
  </UModal>
</template>
