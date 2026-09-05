<script setup lang="ts">
const PAYMENT_MODES = ['Cash', 'Online', 'Cheque', 'Other'] as const

const props = defineProps<{
  open: boolean
  billId: number | null
  /** Amount suggested to collect now (full or remaining balance). */
  amountDue: number
  billTotal?: number
  totalPaid?: number
  clientName?: string
}>()

const emit = defineEmits<{
  'update:open': [boolean]
  saved: []
}>()

const { api } = useApi()
const toast = useToast()

const isOpen = computed({
  get: () => props.open,
  set: (v: boolean) => emit('update:open', v)
})

const amount = ref('')
const paymentMode = ref<string>('Cash')
const description = ref('')
const receiptDatetime = ref('')
const showDatetime = ref(false)
const saving = ref(false)

const modeItems = computed(() => PAYMENT_MODES.map(m => ({ label: m, value: m })))

function localDatetimeInputValue() {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function reset() {
  amount.value = props.amountDue > 0 ? String(props.amountDue) : ''
  paymentMode.value = 'Cash'
  description.value = ''
  receiptDatetime.value = localDatetimeInputValue()
  showDatetime.value = false
}

watch(isOpen, (open) => {
  if (open) reset()
})

async function save() {
  if (!props.billId) return
  const amt = Number(amount.value)
  if (!Number.isFinite(amt) || amt <= 0) {
    toast.add({ title: 'Enter a valid amount', color: 'warning' })
    return
  }
  saving.value = true
  try {
    await api(`/bills/${props.billId}/collect`, {
      method: 'POST',
      body: {
        amount: amt,
        payment_mode: paymentMode.value,
        description: description.value.trim() || undefined,
        receipt_datetime: showDatetime.value ? receiptDatetime.value : undefined
      }
    })
    toast.add({ title: 'Payment collected', color: 'success' })
    isOpen.value = false
    emit('saved')
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Collect failed', color: 'error' })
  } finally {
    saving.value = false
  }
}

const balanceHint = computed(() => {
  const total = props.billTotal ?? props.amountDue
  const paid = props.totalPaid ?? 0
  if (paid > 0 && total > paid) {
    return `Bill ₹${total.toLocaleString('en-IN')} · Paid ₹${paid.toLocaleString('en-IN')} · Due ₹${Math.max(0, total - paid).toLocaleString('en-IN')}`
  }
  return null
})
</script>

<template>
  <UModal v-model:open="isOpen" title="Collect payment" :ui="{ content: 'sm:max-w-md' }">
    <template #body>
      <form class="space-y-3" @submit.prevent="save">
        <p v-if="clientName" class="text-sm text-slate-600">{{ clientName }}</p>
        <p v-if="balanceHint" class="text-xs text-slate-500">{{ balanceHint }}</p>

        <UFormField label="Amount" required>
          <UInput v-model="amount" type="number" min="0.01" step="0.01" class="w-full" autofocus />
        </UFormField>

        <UFormField label="Payment mode" required>
          <USelect
            v-model="paymentMode"
            :items="modeItems"
            value-key="value"
            label-key="label"
            class="w-full"
          />
        </UFormField>

        <UFormField label="Description">
          <UInput v-model="description" class="w-full" placeholder="Optional" />
        </UFormField>

        <button
          type="button"
          class="text-xs font-medium text-[#0097A7] hover:underline"
          @click="showDatetime = !showDatetime"
        >
          {{ showDatetime ? 'Hide date & time' : 'Set receipt date & time' }}
        </button>
        <UFormField v-if="showDatetime" label="Receipt date & time">
          <UInput v-model="receiptDatetime" type="datetime-local" class="w-full" />
        </UFormField>

        <div class="flex justify-end gap-2 pt-1">
          <UButton color="neutral" variant="ghost" type="button" @click="isOpen = false">
            Cancel
          </UButton>
          <UButton type="submit" class="bg-[#0097A7]" :loading="saving">
            Collect
          </UButton>
        </div>
      </form>
    </template>
  </UModal>
</template>
