<script setup lang="ts">
type WaSettings = {
  enabled: boolean
  wa_enabled: boolean
  has_api_key: boolean
  api_key_preview: string | null
  wa_api_url: string
  inbox_enabled: boolean
  can_use_inbox: boolean
  can_manage: boolean
}

const { api } = useApi()

const loading = ref(true)
const error = ref('')
const status = ref<WaSettings | null>(null)

async function load() {
  loading.value = true
  error.value = ''
  try {
    status.value = await api<WaSettings>('/settings/whatsapp')
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to load settings'
    status.value = null
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="p-4 md:p-5">
    <p v-if="error" class="mb-4 text-sm text-red-600">{{ error }}</p>
    <p v-else-if="loading" class="text-sm text-slate-400">Loading…</p>

    <div
      v-else-if="status"
      class="mx-auto max-w-xl space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
    >
      <div>
        <p class="text-sm font-medium text-[#1C2B35]">WhatsApp status</p>
        <p class="mt-0.5 text-xs text-slate-500">
          Managed by a superadmin. Ask them to enable messaging or Inbox on the clinic admin page.
        </p>
      </div>

      <div class="grid gap-3 sm:grid-cols-2">
        <div
          class="rounded-lg px-3 py-2 text-xs"
          :class="status.enabled ? 'bg-emerald-50 text-emerald-800' : 'bg-slate-50 text-slate-600'"
        >
          <p class="font-semibold uppercase tracking-wide">Outbound</p>
          <p class="mt-1">
            {{ status.enabled ? 'Ready — Book / Rx / warranty can send' : 'Not ready' }}
          </p>
        </div>
        <div
          class="rounded-lg px-3 py-2 text-xs"
          :class="status.can_use_inbox ? 'bg-emerald-50 text-emerald-800' : 'bg-slate-50 text-slate-600'"
        >
          <p class="font-semibold uppercase tracking-wide">Inbox</p>
          <p class="mt-1">
            {{ status.can_use_inbox ? 'Ready — Inbox nav is available' : 'Not enabled' }}
          </p>
        </div>
      </div>

      <dl class="space-y-2 text-sm text-slate-600">
        <div class="flex justify-between gap-3">
          <dt class="text-slate-500">Messaging flag</dt>
          <dd>{{ status.wa_enabled ? 'On' : 'Off' }}</dd>
        </div>
        <div class="flex justify-between gap-3">
          <dt class="text-slate-500">Inbox flag</dt>
          <dd>{{ status.inbox_enabled ? 'On' : 'Off' }}</dd>
        </div>
        <div class="flex justify-between gap-3">
          <dt class="text-slate-500">API key</dt>
          <dd class="font-mono text-xs">
            {{ status.has_api_key ? `Saved ${status.api_key_preview || ''}` : 'Not set' }}
          </dd>
        </div>
      </dl>
    </div>
  </div>
</template>
