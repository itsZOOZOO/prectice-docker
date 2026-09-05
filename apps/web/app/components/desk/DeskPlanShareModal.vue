<script setup lang="ts">
type ShareLink = {
  id: number
  share_url: string
  public_path: string
  status: string
  expires_at: string | null
  view_count: number
  validity_days: number
  notes?: string | null
  created_at?: string | null
  last_accessed?: string | null
}

type Analytics = {
  total_views: number
  unique_views: number
  avg_session_seconds: number
  max_session_seconds: number
  access_logs: Array<{
    id: number
    ip_address: string
    user_agent: string
    session_duration: number
    accessed_at: string | null
  }>
}

const open = defineModel<boolean>('open', { default: false })
const props = defineProps<{
  planId: number | null
  planTitle?: string | null
}>()
const emit = defineEmits<{ changed: [] }>()

const { api } = useApi()
const toast = useToast()

const links = ref<ShareLink[]>([])
const loading = ref(false)
const creating = ref(false)
const sendingWa = ref(false)
const validityDays = ref(7)
const analyticsOpen = ref(false)
const analytics = ref<Analytics | null>(null)
const analyticsLinkId = ref<number | null>(null)
const waEnabled = ref(false)

function formatWhen(iso: string | null | undefined) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true
  })
}

function formatDuration(seconds: number) {
  if (!seconds || seconds <= 0) return '—'
  if (seconds < 60) return `${Math.round(seconds)}s`
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return s ? `${m}m ${s}s` : `${m}m`
}

async function refreshWa() {
  try {
    const s = await api<{ enabled?: boolean, wa_enabled?: boolean }>('/settings/whatsapp')
    waEnabled.value = Boolean(s.enabled ?? s.wa_enabled)
  } catch {
    waEnabled.value = false
  }
}

async function load() {
  if (!props.planId) return
  loading.value = true
  try {
    const data = await api<{ items: ShareLink[] }>(`/treatment-plans/${props.planId}/share-links`)
    links.value = data.items || []
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to load links', color: 'error' })
  } finally {
    loading.value = false
  }
}

watch(open, (v) => {
  if (v) {
    void load()
    void refreshWa()
  } else {
    links.value = []
    analytics.value = null
  }
})

async function createLink() {
  if (!props.planId || creating.value) return
  creating.value = true
  try {
    const data = await api<{ share_url: string }>(`/treatment-plans/${props.planId}/share-links`, {
      method: 'POST',
      body: { validity_days: validityDays.value }
    })
    toast.add({ title: 'Share link created', color: 'success' })
    await load()
    emit('changed')
    if (data.share_url && navigator.clipboard) {
      await navigator.clipboard.writeText(data.share_url)
      toast.add({ title: 'Link copied', color: 'success' })
    }
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
  } finally {
    creating.value = false
  }
}

async function copyLink(url: string) {
  try {
    await navigator.clipboard.writeText(url)
    toast.add({ title: 'Copied', color: 'success' })
  } catch {
    toast.add({ title: url, color: 'neutral' })
  }
}

async function deactivate(link: ShareLink) {
  if (!props.planId || !confirm('Deactivate this link?')) return
  try {
    await api(`/treatment-plans/${props.planId}/share-links/${link.id}`, { method: 'DELETE' })
    toast.add({ title: 'Link deactivated', color: 'success' })
    await load()
    emit('changed')
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
  }
}

async function openAnalytics(link: ShareLink) {
  if (!props.planId) return
  analyticsLinkId.value = link.id
  analyticsOpen.value = true
  try {
    analytics.value = await api<Analytics>(
      `/treatment-plans/${props.planId}/share-links/${link.id}/analytics`
    )
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
    analyticsOpen.value = false
  }
}

async function sendWhatsApp() {
  if (!props.planId || sendingWa.value) return
  sendingWa.value = true
  try {
    const data = await api<{ share_url: string }>(`/treatment-plans/${props.planId}/send-whatsapp`, {
      method: 'POST'
    })
    toast.add({ title: 'Sent on WhatsApp', color: 'success' })
    await load()
    emit('changed')
    if (data.share_url) await copyLink(data.share_url)
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'WhatsApp failed', color: 'error' })
  } finally {
    sendingWa.value = false
  }
}
</script>

<template>
  <UModal v-model:open="open" :title="planTitle ? `Share · ${planTitle}` : 'Share treatment plan'">
    <template #body>
      <div class="space-y-4">
        <div class="flex flex-wrap items-end gap-2">
          <UFormField label="Valid for (days)">
            <UInput v-model.number="validityDays" type="number" min="1" max="365" class="w-28" />
          </UFormField>
          <UButton class="bg-[#0097A7]" :loading="creating" @click="createLink">
            Create link
          </UButton>
          <UButton
            color="neutral"
            variant="outline"
            :loading="sendingWa"
            :disabled="!waEnabled"
            :title="waEnabled ? 'Send via WhatsApp template' : 'WhatsApp not enabled'"
            @click="sendWhatsApp"
          >
            WhatsApp
          </UButton>
        </div>
        <p class="text-xs text-slate-500">
          Copy links use <span class="font-medium">mypln.in</span>. WhatsApp still uses the Meta-approved template path until a new template is added.
        </p>

        <p v-if="loading" class="text-sm text-slate-400">Loading…</p>
        <ul v-else class="divide-y divide-slate-100 rounded-xl border border-slate-200">
          <li v-if="!links.length" class="px-3 py-4 text-sm text-slate-400">No share links yet.</li>
          <li v-for="link in links" :key="link.id" class="space-y-2 px-3 py-3">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <span
                class="rounded px-2 py-0.5 text-xs font-medium"
                :class="{
                  'bg-emerald-100 text-emerald-800': link.status === 'active',
                  'bg-amber-100 text-amber-900': link.status === 'expired',
                  'bg-slate-200 text-slate-700': link.status === 'inactive'
                }"
              >
                {{ link.status }}
              </span>
              <span class="text-xs text-slate-500">{{ link.view_count }} views</span>
            </div>
            <p class="break-all text-xs text-slate-600">{{ link.share_url }}</p>
            <p class="text-[11px] text-slate-400">
              Expires {{ formatWhen(link.expires_at) }}
              <span v-if="link.last_accessed"> · Last {{ formatWhen(link.last_accessed) }}</span>
            </p>
            <div class="flex flex-wrap gap-2">
              <button type="button" class="text-xs font-semibold text-[#0097A7]" @click="copyLink(link.share_url)">
                Copy
              </button>
              <button type="button" class="text-xs font-semibold text-slate-600" @click="openAnalytics(link)">
                Analytics
              </button>
              <button
                v-if="link.status === 'active'"
                type="button"
                class="text-xs font-semibold text-red-600"
                @click="deactivate(link)"
              >
                Deactivate
              </button>
            </div>
          </li>
        </ul>
      </div>

      <UModal v-model:open="analyticsOpen" title="Link analytics">
        <template #body>
          <div v-if="analytics" class="space-y-3">
            <div class="grid grid-cols-2 gap-2 text-sm">
              <div class="rounded-lg bg-slate-50 p-2">
                <div class="text-xs text-slate-400">Total views</div>
                <div class="font-semibold">{{ analytics.total_views }}</div>
              </div>
              <div class="rounded-lg bg-slate-50 p-2">
                <div class="text-xs text-slate-400">Unique IPs</div>
                <div class="font-semibold">{{ analytics.unique_views }}</div>
              </div>
              <div class="rounded-lg bg-slate-50 p-2">
                <div class="text-xs text-slate-400">Avg session</div>
                <div class="font-semibold">{{ formatDuration(analytics.avg_session_seconds) }}</div>
              </div>
              <div class="rounded-lg bg-slate-50 p-2">
                <div class="text-xs text-slate-400">Max session</div>
                <div class="font-semibold">{{ formatDuration(analytics.max_session_seconds) }}</div>
              </div>
            </div>
            <ul class="max-h-56 space-y-2 overflow-y-auto text-xs">
              <li
                v-for="log in analytics.access_logs"
                :key="log.id"
                class="rounded border border-slate-100 px-2 py-1.5"
              >
                <div>{{ formatWhen(log.accessed_at) }} · {{ formatDuration(log.session_duration) }}</div>
                <div class="text-slate-400">{{ log.ip_address || '—' }}</div>
              </li>
            </ul>
          </div>
        </template>
      </UModal>
    </template>
  </UModal>
</template>
