<script setup lang="ts">
definePageMeta({ layout: 'mobile' })

type Appt = {
  appointment_id: number
  appointment_date: string
  appointment_time: string
  status: string
  name: string
  client_id: number | null
  doctor_name: string | null
  service_name: string | null
}

const { api } = useApi()
const toast = useToast()
const loading = ref(false)
const items = ref<Appt[]>([])

function todayISO() {
  const d = new Date()
  const offset = d.getTimezoneOffset()
  return new Date(d.getTime() - offset * 60000).toISOString().slice(0, 10)
}

async function load() {
  loading.value = true
  try {
    const data = await api<{ items: Appt[] }>('/appointments', {
      query: { on: todayISO(), limit: 100 }
    })
    items.value = data.items || []
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
      <h1 class="text-lg font-semibold text-[#1C2B35]">Appointments</h1>
      <p class="text-xs text-slate-500">Today · {{ todayISO() }}</p>
    </div>
    <div class="min-h-0 flex-1 overflow-y-auto px-3 py-3">
      <p v-if="loading" class="py-10 text-center text-sm text-slate-400">Loading…</p>
      <ul v-else class="space-y-2">
        <li v-for="a in items" :key="a.appointment_id">
          <NuxtLink
            v-if="a.client_id"
            :to="`/clients/${a.client_id}`"
            class="block rounded-2xl border border-slate-200 bg-white p-3 shadow-sm active:bg-slate-50"
          >
            <div class="flex items-center justify-between gap-2">
              <p class="text-sm font-semibold text-[#1C2B35]">{{ formatAmPm(a.appointment_time) }} · {{ a.name }}</p>
              <span class="text-[10px] font-medium text-slate-500">{{ a.status }}</span>
            </div>
            <p class="mt-0.5 truncate text-xs text-slate-500">
              {{ [a.doctor_name, a.service_name].filter(Boolean).join(' · ') || '—' }}
            </p>
          </NuxtLink>
          <div
            v-else
            class="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm"
          >
            <div class="flex items-center justify-between gap-2">
              <p class="text-sm font-semibold text-[#1C2B35]">{{ formatAmPm(a.appointment_time) }} · {{ a.name }}</p>
              <span class="text-[10px] font-medium text-slate-500">{{ a.status }}</span>
            </div>
          </div>
        </li>
        <li v-if="!items.length" class="rounded-2xl border border-dashed border-slate-300 px-4 py-12 text-center text-sm text-slate-400">
          No appointments today.
        </li>
      </ul>
    </div>
  </div>
</template>
