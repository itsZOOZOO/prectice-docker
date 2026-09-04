<script setup lang="ts">
definePageMeta({ layout: 'mobile' })

type LabCase = {
  case_id: number
  case_ref: string
  case_type: string | null
  lab_name: string
  stage: string
  status: string
  client_id: number
  client_name?: string
  expected_return_date: string | null
}

const { api } = useApi()
const toast = useToast()
const loading = ref(false)
const items = ref<LabCase[]>([])

async function load() {
  loading.value = true
  try {
    const data = await api<{ cases: LabCase[] }>('/lab-cases', {
      query: { filter: 'action_needed', limit: 80 }
    })
    items.value = data.cases || []
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="flex h-full min-h-0 flex-col">
    <div class="shrink-0 border-b border-slate-200 bg-white px-4 py-3">
      <h1 class="text-lg font-semibold text-[#1C2B35]">Lab</h1>
      <p class="text-xs text-slate-500">Action needed</p>
    </div>
    <div class="min-h-0 flex-1 overflow-y-auto px-3 py-3">
      <p v-if="loading" class="py-10 text-center text-sm text-slate-400">Loading…</p>
      <ul v-else class="space-y-2">
        <li v-for="c in items" :key="c.case_id">
          <NuxtLink
            :to="`/clients/${c.client_id}`"
            class="block rounded-2xl border border-slate-200 bg-white p-3 shadow-sm"
          >
            <p class="text-sm font-semibold text-[#1C2B35]">{{ c.case_ref }} · {{ c.stage.replace(/_/g, ' ') }}</p>
            <p class="mt-0.5 truncate text-xs text-slate-500">
              {{ [c.client_name, c.case_type, c.lab_name].filter(Boolean).join(' · ') }}
            </p>
          </NuxtLink>
        </li>
        <li v-if="!items.length" class="rounded-2xl border border-dashed border-slate-300 px-4 py-12 text-center text-sm text-slate-400">
          No lab cases need action.
        </li>
      </ul>
      <p class="mt-4 text-center text-[11px] text-slate-400">
        Full lab queue · <NuxtLink to="/desk?view=lab" class="text-[#0097A7]">Open desk</NuxtLink>
      </p>
    </div>
  </div>
</template>
