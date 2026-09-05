<script setup lang="ts">
type PlanDetail = {
  plan_id: number
  title: string | null
  notes: string | null
  locked_at: string | null
  created_at: string | null
  total_cost: number | null
  unpriced_count: number
  total_foc: number
  sub_plans: {
    sub_plan_id: number
    treatment_name: string | null
    type: string
    qty: number
    tooth_fdi: string | null
    location_text: string | null
    notes: string | null
    price_amount: number | null
    price_label: string | null
    is_foc: boolean
    photos: { photo_id: number, key: string, url: string | null }[]
  }[]
}

const props = defineProps<{
  open: boolean
  planId: number | null
}>()

const emit = defineEmits<{
  'update:open': [boolean]
  edit: [planId: number]
  pricing: [planId: number]
  deleted: []
}>()

const { api } = useApi()
const toast = useToast()

const isOpen = computed({
  get: () => props.open,
  set: (v: boolean) => emit('update:open', v)
})

const detail = ref<PlanDetail | null>(null)
const loading = ref(false)
const deleting = ref(false)
const lightbox = ref<string | null>(null)
const shareOpen = ref(false)

async function load() {
  if (!props.planId) return
  loading.value = true
  try {
    detail.value = await api<PlanDetail>(`/treatment-plans/${props.planId}`)
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
    isOpen.value = false
  } finally {
    loading.value = false
  }
}

watch(isOpen, (open) => {
  if (open) void load()
  else detail.value = null
})

async function onDelete() {
  if (!props.planId || !confirm('Delete this treatment plan? This cannot be undone.')) return
  deleting.value = true
  try {
    await api(`/treatment-plans/${props.planId}`, { method: 'DELETE' })
    toast.add({ title: 'Plan deleted', color: 'success' })
    isOpen.value = false
    emit('deleted')
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
  } finally {
    deleting.value = false
  }
}

function formatInr(n: number | null | undefined) {
  if (n == null) return 'Not priced'
  return `₹${Number(n).toLocaleString('en-IN')}`
}
</script>

<template>
  <UModal v-model:open="isOpen" title="Treatment plan" :ui="{ content: 'sm:max-w-lg' }">
    <template #body>
      <div v-if="loading" class="py-8 text-center text-sm text-slate-500">Loading…</div>
      <div v-else-if="detail" class="space-y-3">
        <div class="flex items-start justify-between gap-2">
          <div>
            <h3 class="text-base font-semibold text-[#1C2B35]">{{ detail.title || 'Treatment plan' }}</h3>
            <p class="mt-0.5 text-xs text-slate-500">
              {{ detail.locked_at ? 'Locked' : 'Unlocked' }}
              · {{ formatInr(detail.total_cost) }}
            </p>
          </div>
        </div>
        <p v-if="detail.notes" class="text-sm text-slate-600">{{ detail.notes }}</p>

        <div
          v-for="sp in detail.sub_plans"
          :key="sp.sub_plan_id"
          class="rounded-xl border border-slate-200 bg-slate-50 p-3"
        >
          <div class="flex items-start justify-between gap-2">
            <div>
              <p class="text-sm font-medium text-[#1C2B35]">
                {{ sp.treatment_name }}
                <span v-if="sp.qty > 1" class="text-slate-500">×{{ sp.qty }}</span>
              </p>
              <p class="text-[11px] text-slate-500">
                {{ sp.type === 'Tentative' ? 'Exploratory' : 'Confirmed' }}
                <template v-if="sp.tooth_fdi"> · Tooth {{ sp.tooth_fdi }}</template>
                <template v-if="sp.location_text"> · {{ sp.location_text }}</template>
              </p>
            </div>
            <p class="shrink-0 text-sm font-semibold text-[#1C2B35]">
              <template v-if="sp.is_foc">FOC</template>
              <template v-else-if="sp.price_amount != null">{{ formatInr(sp.price_amount) }}</template>
              <template v-else class="text-slate-400">—</template>
            </p>
          </div>
          <p v-if="sp.price_label && !sp.is_foc" class="mt-0.5 text-[11px] text-slate-500">{{ sp.price_label }}</p>
          <p v-if="sp.notes" class="mt-1 text-xs text-slate-600">{{ sp.notes }}</p>
          <div v-if="sp.photos.length" class="mt-2 flex flex-wrap gap-2">
            <button
              v-for="ph in sp.photos"
              :key="ph.photo_id"
              type="button"
              class="overflow-hidden rounded-lg border border-slate-200"
              @click="ph.url && (lightbox = ph.url)"
            >
              <img v-if="ph.url" :src="ph.url" alt="" class="h-16 w-16 object-cover">
            </button>
          </div>
        </div>

        <div class="flex flex-wrap justify-end gap-2 pt-1">
          <UButton color="error" variant="ghost" :loading="deleting" @click="onDelete">Delete</UButton>
          <UButton color="neutral" variant="outline" @click="shareOpen = true">
            Share
          </UButton>
          <UButton
            color="neutral"
            variant="outline"
            :disabled="!!detail.locked_at"
            @click="emit('pricing', detail.plan_id); isOpen = false"
          >
            Pricing
          </UButton>
          <UButton
            color="neutral"
            variant="outline"
            :disabled="!!detail.locked_at"
            @click="emit('edit', detail.plan_id); isOpen = false"
          >
            Edit
          </UButton>
          <UButton class="bg-[#0097A7]" @click="isOpen = false">Close</UButton>
        </div>
      </div>
    </template>
  </UModal>

  <DeskPlanShareModal
    v-model:open="shareOpen"
    :plan-id="planId"
    :plan-title="detail?.title"
  />

  <Teleport to="body">
    <div
      v-if="lightbox"
      class="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 p-4"
      @click="lightbox = null"
    >
      <img :src="lightbox" alt="" class="max-h-full max-w-full rounded-lg object-contain" @click.stop>
    </div>
  </Teleport>
</template>
