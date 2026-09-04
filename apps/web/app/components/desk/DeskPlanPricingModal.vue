<script setup lang="ts">
type PriceOption = {
  price_option_id: number
  label: string
  price: number
  explainer: string | null
  is_foc: boolean
}

type PricingRow = {
  sub_plan_id: number
  treatment_id: number
  treatment_name: string | null
  qty: number
  price_option_id: number | null
  is_foc: boolean
  options: PriceOption[]
}

const props = defineProps<{
  open: boolean
  planId: number | null
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

const title = ref('')
const notes = ref('')
const rows = ref<PricingRow[]>([])
const lockPlan = ref(true)
const loading = ref(false)
const saving = ref(false)

const allPriced = computed(() =>
  rows.value.every(r => r.is_foc || (r.price_option_id != null && r.price_option_id > 0))
)

watch(allPriced, (ok) => {
  if (!ok) lockPlan.value = false
  else if (!saving.value) lockPlan.value = true
})

async function load() {
  if (!props.planId) return
  loading.value = true
  try {
    const plan = await api<{
      title: string | null
      notes: string | null
      sub_plans: {
        sub_plan_id: number
        treatment_id: number
        treatment_name: string | null
        qty: number
        chosen_price_option_id: number | null
        is_foc: boolean
      }[]
    }>(`/treatment-plans/${props.planId}`)
    title.value = plan.title || ''
    notes.value = plan.notes || ''
    const next: PricingRow[] = []
    for (const sp of plan.sub_plans) {
      const options = await api<PriceOption[]>(`/treatments/${sp.treatment_id}/price-options`)
      next.push({
        sub_plan_id: sp.sub_plan_id,
        treatment_id: sp.treatment_id,
        treatment_name: sp.treatment_name,
        qty: sp.qty || 1,
        price_option_id: sp.chosen_price_option_id,
        is_foc: sp.is_foc,
        options
      })
    }
    rows.value = next
    lockPlan.value = allPriced.value
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
    isOpen.value = false
  } finally {
    loading.value = false
  }
}

watch(isOpen, (open) => {
  if (open) void load()
})

async function save() {
  if (!props.planId) return
  if (lockPlan.value && !allPriced.value) {
    toast.add({ title: 'Price every treatment before locking', color: 'warning' })
    return
  }
  saving.value = true
  try {
    await api(`/treatment-plans/${props.planId}/pricing`, {
      method: 'PUT',
      body: {
        title: title.value.trim() || null,
        notes: notes.value.trim() || null,
        lock_plan: lockPlan.value,
        sub_plans: rows.value.map(r => ({
          id: r.sub_plan_id,
          price_option_id: r.is_foc ? null : r.price_option_id,
          is_foc: r.is_foc
        }))
      }
    })
    toast.add({
      title: lockPlan.value ? 'Pricing saved & plan locked' : 'Pricing saved',
      color: 'success'
    })
    isOpen.value = false
    emit('saved')
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
  } finally {
    saving.value = false
  }
}

function formatInr(n: number) {
  return `₹${Number(n).toLocaleString('en-IN')}`
}
</script>

<template>
  <UModal v-model:open="isOpen" title="Set pricing & lock" :ui="{ content: 'sm:max-w-lg' }">
    <template #body>
      <div v-if="loading" class="py-8 text-center text-sm text-slate-500">Loading…</div>
      <form v-else class="space-y-3" @submit.prevent="save">
        <UFormField label="Title">
          <UInput v-model="title" class="w-full" />
        </UFormField>
        <UFormField label="Notes">
          <UTextarea v-model="notes" class="w-full" :rows="2" />
        </UFormField>

        <div
          v-for="row in rows"
          :key="row.sub_plan_id"
          class="space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-3"
        >
          <p class="text-sm font-medium text-[#1C2B35]">
            {{ row.treatment_name }}
            <span v-if="row.qty > 1" class="text-slate-500">×{{ row.qty }}</span>
          </p>
          <label class="flex items-center gap-2 text-xs text-slate-600">
            <input v-model="row.is_foc" type="checkbox" class="rounded border-slate-300">
            Free of charge (FOC)
          </label>
          <UFormField v-if="!row.is_foc" label="Price option">
            <USelect
              v-model="row.price_option_id"
              :items="[
                { label: '— Select —', value: null },
                ...row.options.map(o => ({
                  label: `${o.label} · ${formatInr(o.price)}`,
                  value: o.price_option_id
                }))
              ]"
              value-key="value"
              label-key="label"
              class="w-full"
            />
          </UFormField>
          <p v-if="!row.options.length && !row.is_foc" class="text-xs text-amber-600">
            No price options for this treatment.
          </p>
        </div>

        <label class="flex items-center gap-2 text-sm text-slate-700">
          <input
            v-model="lockPlan"
            type="checkbox"
            class="rounded border-slate-300"
            :disabled="!allPriced"
          >
          Lock plan after saving
          <span v-if="!allPriced" class="text-xs text-slate-400">(price all first)</span>
        </label>

        <div class="flex justify-end gap-2">
          <UButton color="neutral" variant="ghost" type="button" @click="isOpen = false">Cancel</UButton>
          <UButton type="submit" class="bg-[#0097A7]" :loading="saving">Save pricing</UButton>
        </div>
      </form>
    </template>
  </UModal>
</template>
