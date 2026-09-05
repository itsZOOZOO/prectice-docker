<script setup lang="ts">
const PERIOD_OPTIONS = [
  { value: 365, label: '1 Year (365 days)' },
  { value: 730, label: '2 Years (730 days)' },
  { value: 1825, label: '5 Years (1825 days)' },
  { value: 3650, label: '10 Years (3650 days)' },
  { value: 7300, label: '20 Years (7300 days)' },
  { value: 'custom', label: 'Other (custom days)' }
] as const

type WarrantyOption = { id: number, name: string }
type WarrantyOptions = {
  card_types: WarrantyOption[]
  products: WarrantyOption[]
  terms_conditions: WarrantyOption[]
  benefits: WarrantyOption[]
}

const props = defineProps<{
  open: boolean
  clientId: number | null
  cardId?: number | null
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

const isEdit = computed(() => props.cardId != null && props.cardId > 0)

const options = ref<WarrantyOptions | null>(null)
const loading = ref(false)
const saving = ref(false)

const cardTypeId = ref<number | null>(null)
const productId = ref<number | null>(null)
const termsId = ref<number | null>(null)
const benefitId = ref<number | null>(null)
const warrantyChoice = ref<number | 'custom'>(365)
const customDays = ref('')
const benefitStartDate = ref('')
const dateOfPurchase = ref('')
const numberOfUnits = ref(1)
const note = ref('')
const productNameLocked = ref('')
const uniqueCode = ref('')

function todayYmd() {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function addDaysYmd(startYmd: string, days: number): string {
  const parts = startYmd.split('-').map(n => parseInt(n, 10))
  if (parts.length !== 3 || parts.some(n => !Number.isFinite(n))) return ''
  const [y, m, d] = parts as [number, number, number]
  const dt = new Date(y, m - 1, d)
  dt.setDate(dt.getDate() + days)
  return `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}-${String(dt.getDate()).padStart(2, '0')}`
}

const warrantyDays = computed(() => {
  if (warrantyChoice.value === 'custom') {
    const val = parseInt(customDays.value, 10)
    return Number.isFinite(val) && val > 0 ? val : null
  }
  return warrantyChoice.value
})

const benefitEndDate = computed(() => {
  if (!benefitStartDate.value || !warrantyDays.value) return ''
  return addDaysYmd(benefitStartDate.value, warrantyDays.value)
})

const cardTypeItems = computed(() =>
  (options.value?.card_types || []).map(o => ({ label: o.name, value: o.id }))
)
const productItems = computed(() =>
  (options.value?.products || []).map(o => ({ label: o.name, value: o.id }))
)
const termsItems = computed(() =>
  (options.value?.terms_conditions || []).map(o => ({ label: o.name, value: o.id }))
)
const benefitItems = computed(() =>
  (options.value?.benefits || []).map(o => ({ label: o.name, value: o.id }))
)
const periodItems = computed(() =>
  PERIOD_OPTIONS.map(o => ({ label: o.label, value: String(o.value) }))
)

const periodSelect = computed({
  get: () => String(warrantyChoice.value),
  set: (v: string) => {
    warrantyChoice.value = v === 'custom' ? 'custom' : Number(v)
  }
})

function resetCreate() {
  const today = todayYmd()
  cardTypeId.value = null
  productId.value = null
  termsId.value = null
  benefitId.value = null
  warrantyChoice.value = 365
  customDays.value = ''
  benefitStartDate.value = today
  dateOfPurchase.value = today
  numberOfUnits.value = 1
  note.value = ''
  productNameLocked.value = ''
  uniqueCode.value = ''
}

async function loadOptions() {
  options.value = await api<WarrantyOptions>('/warranty-cards/options')
}

async function loadCard() {
  if (!props.cardId) return
  const data = await api<{ card: {
    card_type_id: number
    product_id: number
    product_name: string
    unique_code: string
    terms_conditions_id: number
    benefit_id: number
    number_of_units: number
    warranty_period: number
    date_of_purchase: string
    benefit_start_date: string
    benefit_end_date: string
    note: string
  } }>(`/warranty-cards/${props.cardId}`)
  const c = data.card
  cardTypeId.value = c.card_type_id
  productId.value = c.product_id
  productNameLocked.value = c.product_name
  uniqueCode.value = c.unique_code
  termsId.value = c.terms_conditions_id
  benefitId.value = c.benefit_id
  numberOfUnits.value = c.number_of_units
  dateOfPurchase.value = c.date_of_purchase
  benefitStartDate.value = c.benefit_start_date
  note.value = c.note || ''
  const preset = PERIOD_OPTIONS.find(o => o.value === c.warranty_period)
  if (preset && preset.value !== 'custom') {
    warrantyChoice.value = preset.value
    customDays.value = ''
  } else {
    warrantyChoice.value = 'custom'
    customDays.value = String(c.warranty_period)
  }
}

watch(isOpen, async (open) => {
  if (!open) return
  loading.value = true
  try {
    await loadOptions()
    if (isEdit.value) await loadCard()
    else resetCreate()
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to load', color: 'error' })
  } finally {
    loading.value = false
  }
})

async function save() {
  if (!props.clientId) return
  if (!warrantyDays.value) {
    toast.add({ title: 'Enter a valid warranty period', color: 'warning' })
    return
  }
  if (!cardTypeId.value || !termsId.value || !benefitId.value) {
    toast.add({ title: 'Fill all required fields', color: 'warning' })
    return
  }
  if (!isEdit.value && !productId.value) {
    toast.add({ title: 'Select a product', color: 'warning' })
    return
  }
  saving.value = true
  try {
    if (isEdit.value && props.cardId) {
      await api(`/warranty-cards/${props.cardId}`, {
        method: 'PATCH',
        body: {
          card_type_id: cardTypeId.value,
          terms_conditions_id: termsId.value,
          benefit_id: benefitId.value,
          number_of_units: numberOfUnits.value,
          warranty_period: warrantyDays.value,
          date_of_purchase: dateOfPurchase.value,
          benefit_start_date: benefitStartDate.value,
          benefit_end_date: benefitEndDate.value,
          note: note.value.trim() || undefined
        }
      })
      toast.add({ title: 'Warranty card updated', color: 'success' })
    } else {
      await api(`/clients/${props.clientId}/warranty-cards`, {
        method: 'POST',
        body: {
          card_type_id: cardTypeId.value,
          product_id: productId.value,
          terms_conditions_id: termsId.value,
          benefit_id: benefitId.value,
          number_of_units: numberOfUnits.value,
          warranty_period: warrantyDays.value,
          date_of_purchase: dateOfPurchase.value,
          benefit_start_date: benefitStartDate.value,
          note: note.value.trim() || undefined
        }
      })
      toast.add({ title: 'Warranty card created', color: 'success' })
    }
    isOpen.value = false
    emit('saved')
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to save', color: 'error' })
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <UModal
    v-model:open="isOpen"
    :title="isEdit ? 'Edit warranty card' : 'Add warranty card'"
    :ui="{ content: 'sm:max-w-lg' }"
  >
    <template #body>
      <div v-if="loading" class="py-8 text-center text-sm text-slate-500">Loading…</div>
      <form v-else class="space-y-3" @submit.prevent="save">
        <UFormField label="Card type" required>
          <USelect
            v-model="cardTypeId"
            :items="cardTypeItems"
            value-key="value"
            label-key="label"
            placeholder="Choose…"
            class="w-full"
          />
        </UFormField>

        <UFormField v-if="isEdit" label="Product">
          <UInput :model-value="productNameLocked || '—'" class="w-full" disabled />
          <p v-if="uniqueCode" class="mt-1 text-xs text-slate-500">Code {{ uniqueCode }} (locked)</p>
        </UFormField>
        <UFormField v-else label="Product" required>
          <USelect
            v-model="productId"
            :items="productItems"
            value-key="value"
            label-key="label"
            placeholder="Choose…"
            class="w-full"
          />
        </UFormField>

        <UFormField label="Warranty period" required>
          <USelect
            v-model="periodSelect"
            :items="periodItems"
            value-key="value"
            label-key="label"
            class="w-full"
          />
        </UFormField>
        <UFormField v-if="warrantyChoice === 'custom'" label="Custom period (days)" required>
          <UInput v-model="customDays" type="number" min="1" class="w-full" placeholder="e.g. 540" />
        </UFormField>

        <div class="grid grid-cols-2 gap-2">
          <UFormField label="Benefit start" required>
            <UInput v-model="benefitStartDate" type="date" class="w-full" />
          </UFormField>
          <UFormField label="Benefit end">
            <UInput :model-value="benefitEndDate" type="date" class="w-full" disabled />
          </UFormField>
        </div>

        <UFormField label="Date of purchase" required>
          <UInput v-model="dateOfPurchase" type="date" class="w-full" />
        </UFormField>

        <UFormField label="Number of units" required>
          <UInput v-model.number="numberOfUnits" type="number" min="1" class="w-full" />
        </UFormField>

        <UFormField label="Terms & conditions" required>
          <USelect
            v-model="termsId"
            :items="termsItems"
            value-key="value"
            label-key="label"
            placeholder="Choose…"
            class="w-full"
          />
        </UFormField>

        <UFormField label="Benefits" required>
          <USelect
            v-model="benefitId"
            :items="benefitItems"
            value-key="value"
            label-key="label"
            placeholder="Choose…"
            class="w-full"
          />
        </UFormField>

        <UFormField label="Note">
          <UInput v-model="note" class="w-full" placeholder="Optional" />
        </UFormField>

        <div class="flex justify-end gap-2 pt-1">
          <UButton color="neutral" variant="ghost" type="button" @click="isOpen = false">
            Cancel
          </UButton>
          <UButton type="submit" class="bg-[#0097A7]" :loading="saving">
            {{ isEdit ? 'Save changes' : 'Create card' }}
          </UButton>
        </div>
      </form>
    </template>
  </UModal>
</template>
