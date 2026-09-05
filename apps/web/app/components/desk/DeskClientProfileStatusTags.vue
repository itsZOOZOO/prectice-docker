<script setup lang="ts">
import { CLIENT_STATUSES } from '~/utils/patientForm'

export type ClientTagDef = {
  client_tag_id: number
  tag_name: string
}

const props = defineProps<{
  clientId: number
  status: string | null
  tagIds: number[]
}>()

const emit = defineEmits<{
  'update:status': [status: string]
  'update:tags': [tagIds: number[], tagNames: string | null]
}>()

const { api } = useApi()
const toast = useToast()

const crmStatus = ref(props.status || 'Inquiry')
const selectedIds = ref<number[]>([...props.tagIds])
const allTags = ref<ClientTagDef[]>([])
const statusBusy = ref(false)
const tagsBusy = ref(false)
const pickerOpen = ref(false)
const loadError = ref<string | null>(null)
const triggerRef = ref<HTMLElement | null>(null)
const menuRef = ref<HTMLElement | null>(null)
const menuStyle = ref<Record<string, string>>({})

watch(() => props.status, (v) => { crmStatus.value = v || 'Inquiry' })
watch(() => props.tagIds, (v) => { selectedIds.value = [...v] }, { deep: true })
watch(() => props.clientId, () => { void loadTags() })

const selectedSet = computed(() => new Set(selectedIds.value))
const selectedTags = computed(() =>
  allTags.value.filter(t => selectedSet.value.has(t.client_tag_id))
)
const availableTags = computed(() =>
  allTags.value.filter(t => !selectedSet.value.has(t.client_tag_id))
)

async function loadTags() {
  try {
    const data = await api<{ tags: ClientTagDef[] }>('/settings/client-tags')
    allTags.value = data.tags || []
    loadError.value = null
  } catch (e: unknown) {
    loadError.value = e instanceof Error ? e.message : 'Failed to load tags'
  }
}

function placeMenu() {
  const el = triggerRef.value
  if (!el || !import.meta.client) return
  const r = el.getBoundingClientRect()
  const width = 224
  let left = r.left
  if (left + width > window.innerWidth - 8) left = Math.max(8, window.innerWidth - width - 8)
  const spaceBelow = window.innerHeight - r.bottom
  const openUp = spaceBelow < 220 && r.top > spaceBelow
  menuStyle.value = {
    position: 'fixed',
    left: `${left}px`,
    width: `${width}px`,
    zIndex: '80',
    ...(openUp
      ? { bottom: `${window.innerHeight - r.top + 4}px`, top: 'auto' }
      : { top: `${r.bottom + 4}px`, bottom: 'auto' })
  }
}

function togglePicker() {
  if (tagsBusy.value || allTags.value.length === 0) return
  pickerOpen.value = !pickerOpen.value
  if (pickerOpen.value) {
    nextTick(() => placeMenu())
  }
}

function onDocPointer(event: MouseEvent) {
  if (!pickerOpen.value) return
  const t = event.target as Node
  if (triggerRef.value?.contains(t) || menuRef.value?.contains(t)) return
  pickerOpen.value = false
}

function onResize() {
  if (pickerOpen.value) placeMenu()
}

onMounted(() => {
  void loadTags()
  document.addEventListener('mousedown', onDocPointer)
  window.addEventListener('resize', onResize)
  window.addEventListener('scroll', onResize, true)
})
onBeforeUnmount(() => {
  document.removeEventListener('mousedown', onDocPointer)
  window.removeEventListener('resize', onResize)
  window.removeEventListener('scroll', onResize, true)
})

async function saveStatus(next: string) {
  const previous = crmStatus.value
  crmStatus.value = next
  statusBusy.value = true
  try {
    await api(`/clients/${props.clientId}/status`, {
      method: 'PATCH',
      body: { status: next }
    })
    emit('update:status', next)
  } catch (e: unknown) {
    crmStatus.value = previous
    toast.add({ title: e instanceof Error ? e.message : 'Status update failed', color: 'error' })
  } finally {
    statusBusy.value = false
  }
}

async function saveTags(nextIds: number[]) {
  const previous = selectedIds.value
  selectedIds.value = nextIds
  tagsBusy.value = true
  try {
    const data = await api<{
      client_tag_ids: number[]
      client_tags: string | null
    }>(`/clients/${props.clientId}/tags`, {
      method: 'PUT',
      body: { tag_ids: nextIds }
    })
    const saved = Array.isArray(data.client_tag_ids) ? data.client_tag_ids : nextIds
    selectedIds.value = saved
    emit('update:tags', saved, data.client_tags ?? null)
  } catch (e: unknown) {
    selectedIds.value = previous
    toast.add({ title: e instanceof Error ? e.message : 'Tag update failed', color: 'error' })
  } finally {
    tagsBusy.value = false
  }
}

function toggleTag(id: number) {
  if (tagsBusy.value) return
  const next = selectedSet.value.has(id)
    ? selectedIds.value.filter(x => x !== id)
    : [...selectedIds.value, id]
  void saveTags(next)
}
</script>

<template>
  <div class="mt-3">
    <div class="flex flex-wrap items-center gap-1.5">
      <select
        class="max-w-[9.5rem] shrink-0 rounded-lg border border-slate-200 bg-slate-50 px-2 py-1.5 text-xs font-medium text-[#1C2B35] outline-none focus:border-[#0097A7] disabled:opacity-60"
        :value="crmStatus"
        :disabled="statusBusy"
        aria-label="Status"
        @change="saveStatus(String(($event.target as HTMLSelectElement).value))"
      >
        <option v-for="s in CLIENT_STATUSES" :key="s" :value="s">{{ s }}</option>
        <option
          v-if="crmStatus && !(CLIENT_STATUSES as readonly string[]).includes(crmStatus)"
          :value="crmStatus"
        >
          {{ crmStatus }}
        </option>
      </select>

      <button
        v-for="tag in selectedTags"
        :key="tag.client_tag_id"
        type="button"
        class="inline-flex items-center gap-1 rounded-full border border-[#0097A7]/30 bg-[#e0f7fa] px-2 py-1 text-[11px] font-medium text-[#00838f] disabled:opacity-60"
        :disabled="tagsBusy"
        title="Remove tag"
        @click="toggleTag(tag.client_tag_id)"
      >
        {{ tag.tag_name }}
        <span class="text-[10px] opacity-70">×</span>
      </button>

      <button
        ref="triggerRef"
        type="button"
        class="inline-flex h-7 items-center gap-0.5 rounded-full border border-dashed border-slate-300 bg-white px-2 text-[11px] font-medium text-slate-600 hover:border-[#0097A7] hover:text-[#00838f] disabled:opacity-50"
        :disabled="tagsBusy || allTags.length === 0"
        :title="allTags.length === 0 ? 'Add tags in Settings → Client tags' : 'Add tag'"
        @click="togglePicker"
      >
        <UIcon name="i-lucide-plus" class="h-3.5 w-3.5" />
        Tag
      </button>
    </div>

    <p v-if="loadError" class="mt-1 text-[11px] text-red-600">{{ loadError }}</p>
    <p v-else-if="allTags.length === 0" class="mt-1 text-[11px] text-slate-400">
      No tag definitions for this clinic — add them in Settings → Client tags
    </p>

    <Teleport to="body">
      <div
        v-if="pickerOpen"
        ref="menuRef"
        class="max-h-56 overflow-y-auto rounded-xl border border-slate-200 bg-white p-1.5 shadow-lg"
        :style="menuStyle"
      >
        <p v-if="availableTags.length === 0" class="px-2 py-2 text-xs text-slate-500">
          All tags selected
        </p>
        <button
          v-for="tag in availableTags"
          :key="tag.client_tag_id"
          type="button"
          class="flex w-full items-center rounded-lg px-2.5 py-2 text-left text-sm text-slate-700 hover:bg-[#e0f7fa] hover:text-[#00838f] disabled:opacity-60"
          :disabled="tagsBusy"
          @click="toggleTag(tag.client_tag_id); pickerOpen = false"
        >
          {{ tag.tag_name }}
        </button>
      </div>
    </Teleport>
  </div>
</template>
