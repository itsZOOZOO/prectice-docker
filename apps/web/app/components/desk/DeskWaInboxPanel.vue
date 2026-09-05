<script setup lang="ts">
import type {
  WaInboxApiResponse,
  WaInboxConversation,
  WaInboxConversationDetail,
  WaInboxConversationStatus,
  WaInboxFlow,
  WaInboxLeadSourceOption,
  WaInboxMessage,
  WaInboxScheduleMessageType,
  WaInboxSmartList,
  WaInboxTag,
  WaInboxTemplate,
  WaInboxThreadContext,
} from '~/utils/waInbox'
import {
  fmtWaInboxDateShort,
  fmtWaInboxTime,
  isWaInboxMessageAreaNearBottom,
  messageHasPendingMedia,
  playWaInboxNotificationSound,
  unlockWaInboxNotificationSound,
  waInboxLeadStatusLabel,
} from '~/utils/waInbox'

const { api } = useApi()

const conversations = ref<WaInboxConversation[]>([])
const listLoading = ref(true)
const search = ref('')
const statusFilter = ref<WaInboxConversationStatus>('active')
const tagFilterId = ref<number | null>(null)
const smartListId = ref<number | null>(null)
const accountTags = ref<WaInboxTag[]>([])
const smartLists = ref<WaInboxSmartList[]>([])
const activeSmartList = ref<WaInboxSmartList | null>(null)
const catalogReady = ref(false)
const tagMenuOpen = ref(false)
const tagBusy = ref(false)
const selectedId = ref(0)
const selectedConvo = ref<WaInboxConversationDetail | null>(null)
const messages = ref<WaInboxMessage[]>([])
const replyText = ref('')
const sending = ref(false)
const templates = ref<WaInboxTemplate[]>([])
const templatesLoaded = ref(false)
const flows = ref<WaInboxFlow[]>([])
const flowsLoaded = ref(false)
const templateModalOpen = ref(false)
const flowModalOpen = ref(false)
const scheduleModalOpen = ref(false)
const selectedTemplateId = ref('')
const selectedFlowId = ref('')
const aiDrafting = ref(false)
const schedMsgType = ref<WaInboxScheduleMessageType>('text')
const schedTextBody = ref('')
const schedTemplateId = ref('')
const schedFlowId = ref('')
const schedSendAt = ref('')
const schedNotes = ref('')
const schedFeedback = ref<string | null>(null)
const schedSubmitting = ref(false)
const flowSending = ref(false)
const threadContext = ref<WaInboxThreadContext | null>(null)
const leadSourceOptions = ref<WaInboxLeadSourceOption[]>([])
const pastConvosModalOpen = ref(false)
const sendCrmModalOpen = ref(false)
const leadSource = ref('WhatsApp Manual')
const sendLeadSubmitting = ref(false)

const lastMessageId = ref(0)
const pendingMedia = ref(false)
const seenInboundIds = ref<Set<number>>(new Set())
const convSnapshot = ref(new Map<number, { last_message_at: string | null, needs_attention: boolean }>())
const messageAreaRef = ref<HTMLDivElement | null>(null)
const selectedIdRef = ref(0)

const actionBtnClass =
  'inline-flex items-center gap-1 rounded-md border px-2.5 py-1 text-xs transition disabled:opacity-50'

watch(selectedId, (id) => {
  selectedIdRef.value = id
})

watch(messages, (msgs) => {
  pendingMedia.value = msgs.some(messageHasPendingMedia)
}, { deep: true })

async function apiGet(action: string, params: Record<string, string | number | undefined | null> = {}): Promise<WaInboxApiResponse> {
  try {
    const query: Record<string, string | number> = { action }
    for (const [k, v] of Object.entries(params)) {
      if (v === undefined || v === null || v === '') continue
      query[k] = v
    }
    return await api<WaInboxApiResponse>('/wa-inbox', { query })
  } catch (e: unknown) {
    return { success: false, error: e instanceof Error ? e.message : 'Request failed' }
  }
}

async function apiPost(action: string, payload: Record<string, unknown> = {}): Promise<WaInboxApiResponse> {
  try {
    return await api<WaInboxApiResponse>('/wa-inbox', {
      method: 'POST',
      query: { action },
      body: payload,
    })
  } catch (e: unknown) {
    return { success: false, error: e instanceof Error ? e.message : 'Request failed' }
  }
}

function seedInboundSeen(msgs: WaInboxMessage[]) {
  seenInboundIds.value = new Set(msgs.filter(m => m.direction === 'in').map(m => m.id))
}

function notifyInboundMessages(msgs: WaInboxMessage[], isFullLoad: boolean) {
  if (isFullLoad) {
    seedInboundSeen(msgs)
    return
  }
  let hasNewInbound = false
  for (const m of msgs) {
    if (m.direction !== 'in') continue
    if (seenInboundIds.value.has(m.id)) continue
    seenInboundIds.value.add(m.id)
    hasNewInbound = true
  }
  if (hasNewInbound) playWaInboxNotificationSound()
}

function notifyFromConversationList(items: WaInboxConversation[]) {
  const activeId = selectedIdRef.value
  let shouldPlay = false

  for (const cv of items) {
    const prev = convSnapshot.value.get(cv.id)
    const snapshot = {
      last_message_at: cv.last_message_at,
      needs_attention: Boolean(cv.needs_attention),
    }

    if (prev && cv.id !== activeId) {
      const attentionTurnedOn = !prev.needs_attention && snapshot.needs_attention
      const newActivity = Boolean(cv.last_message_at) && cv.last_message_at !== prev.last_message_at
      if (attentionTurnedOn || newActivity) shouldPlay = true
    }

    convSnapshot.value.set(cv.id, snapshot)
  }

  if (shouldPlay) playWaInboxNotificationSound()
}

async function loadCatalog() {
  const [tagsRes, listsRes] = await Promise.all([
    apiGet('list_tags'),
    apiGet('list_smart_lists'),
  ])
  if (tagsRes.success) accountTags.value = tagsRes.tags ?? []
  if (listsRes.success) {
    const lists = listsRes.smart_lists ?? []
    smartLists.value = lists
    const preferred = listsRes.default_list_id ?? lists[0]?.id ?? null
    if (!(smartListId.value && lists.some(l => l.id === smartListId.value))) {
      smartListId.value = preferred
    }
  }
  catalogReady.value = true
}

async function loadConversations() {
  if (!catalogReady.value) return
  const q = search.value.trim()
  let data: WaInboxApiResponse
  if (q.length >= 2) {
    const params: Record<string, string | number> = {
      q,
      status: statusFilter.value === 'all' ? '' : statusFilter.value,
    }
    if (smartListId.value) params.list_id = smartListId.value
    if (tagFilterId.value) params.tag_id = tagFilterId.value
    data = await apiGet('search_conversations', params)
  } else if (smartListId.value) {
    const params: Record<string, string | number> = { list_id: smartListId.value }
    if (tagFilterId.value) params.tag_id = tagFilterId.value
    data = await apiGet('list_conversations', params)
  } else {
    const params: Record<string, string | number> = { status: statusFilter.value }
    if (tagFilterId.value) params.tag_id = tagFilterId.value
    data = await apiGet('list_conversations', params)
  }
  if (data.success) {
    const items = data.conversations ?? []
    notifyFromConversationList(items)
    conversations.value = items
    if (smartListId.value) {
      activeSmartList.value =
        data.smart_list ?? smartLists.value.find(l => l.id === smartListId.value) ?? null
    } else {
      activeSmartList.value = null
    }
  }
  listLoading.value = false
}

function appendMessages(msgs: WaInboxMessage[], replace = false) {
  if (replace) {
    lastMessageId.value = 0
    const next = msgs.slice()
    for (const m of next) {
      lastMessageId.value = Math.max(lastMessageId.value, m.id)
    }
    messages.value = next
    return
  }

  const byId = new Map(messages.value.map(m => [m.id, m]))
  for (const m of msgs) {
    const existing = byId.get(m.id)
    if (existing) {
      if (messageHasPendingMedia(existing) && m.media_url) {
        byId.set(m.id, m)
        lastMessageId.value = Math.max(lastMessageId.value, m.id)
      }
      continue
    }
    byId.set(m.id, m)
    lastMessageId.value = Math.max(lastMessageId.value, m.id)
  }
  messages.value = Array.from(byId.values()).sort((a, b) => a.id - b.id)
}

async function loadMessages(conversationId: number, full = false, forceScroll = false) {
  if (!conversationId) return
  let doFull = full
  if (!doFull && pendingMedia.value) doFull = true

  const areaBefore = messageAreaRef.value
  const shouldStickToBottom =
    forceScroll || !areaBefore || isWaInboxMessageAreaNearBottom(areaBefore)

  const params: Record<string, string | number> = { conversation_id: conversationId }
  if (!doFull && lastMessageId.value > 0) {
    params.since_id = lastMessageId.value
  }
  const data = await apiGet('list_messages', params)
  if (data.success) {
    const msgs = data.messages ?? []
    notifyInboundMessages(msgs, doFull)
    appendMessages(msgs, doFull)
    if (!shouldStickToBottom) return
    if (!forceScroll && !doFull && msgs.length === 0) return
    requestAnimationFrame(() => {
      const area = messageAreaRef.value
      if (area) area.scrollTop = area.scrollHeight
    })
  }
}

async function openConversation(id: number) {
  unlockWaInboxNotificationSound()
  selectedId.value = id
  lastMessageId.value = 0
  seenInboundIds.value = new Set()
  messages.value = []

  const data = await apiGet('get_conversation', { id })
  if (!data.success || !data.conversation) {
    window.alert(data.error || 'Could not load conversation')
    selectedId.value = 0
    return
  }
  selectedConvo.value = data.conversation
  threadContext.value = data.thread ?? null
  leadSourceOptions.value = data.lead_source_options ?? []
  leadSource.value = 'WhatsApp Manual'
  await loadMessages(id, true, true)
  void loadConversations()
}

function clearSelection() {
  selectedId.value = 0
  selectedConvo.value = null
  threadContext.value = null
  leadSourceOptions.value = []
  messages.value = []
}

async function sendLeadToCrm() {
  if (!selectedId.value) return
  sendLeadSubmitting.value = true
  try {
    const data = await apiPost('send_lead', {
      id: selectedId.value,
      source: leadSource.value || 'WhatsApp Manual',
    })
    if (data.success) {
      sendCrmModalOpen.value = false
      const cid = data.client_id ? ` (client #${data.client_id})` : ''
      window.alert(`Lead sent to CRM successfully${cid}`)
      await openConversation(selectedId.value)
    } else {
      window.alert(`Failed to send lead: ${data.error || 'Unknown error'}`)
    }
  } catch {
    window.alert('Network error — could not reach server.')
  } finally {
    sendLeadSubmitting.value = false
  }
}

async function closeConvo() {
  if (!window.confirm('Close this conversation?')) return
  await apiPost('close', { id: selectedId.value })
  void openConversation(selectedId.value)
}

async function reopenConvo() {
  await apiPost('reopen', { id: selectedId.value })
  void openConversation(selectedId.value)
}

async function resolveAttention() {
  await apiPost('resolve_attention', { id: selectedId.value })
  void openConversation(selectedId.value)
}

function applyConvoTags(tags: WaInboxTag[]) {
  if (selectedConvo.value) {
    selectedConvo.value = { ...selectedConvo.value, tags }
  }
  conversations.value = conversations.value.map(cv =>
    cv.id === selectedId.value ? { ...cv, tags } : cv,
  )
}

async function addTagToConvo(tagId: number) {
  if (!selectedId.value || tagBusy.value) return
  tagBusy.value = true
  try {
    const data = await apiPost('tag_add', {
      conversation_id: selectedId.value,
      tag_id: tagId,
    })
    if (data.success && data.tags) {
      applyConvoTags(data.tags)
      tagMenuOpen.value = false
    } else {
      window.alert(data.error || 'Could not add tag')
    }
  } finally {
    tagBusy.value = false
  }
}

async function removeTagFromConvo(tagId: number) {
  if (!selectedId.value || tagBusy.value) return
  tagBusy.value = true
  try {
    const data = await apiPost('tag_remove', {
      conversation_id: selectedId.value,
      tag_id: tagId,
    })
    if (data.success && data.tags) {
      applyConvoTags(data.tags)
    } else {
      window.alert(data.error || 'Could not remove tag')
    }
  } finally {
    tagBusy.value = false
  }
}

function selectSmartList(id: number) {
  smartListId.value = id
  listLoading.value = true
}

function selectTagFilter(id: number | null) {
  tagFilterId.value = id
  listLoading.value = true
}

async function sendText() {
  const text = replyText.value.trim()
  if (!text || !selectedId.value) return
  sending.value = true
  try {
    const data = await apiPost('send_text', {
      conversation_id: selectedId.value,
      text,
    })
    if (data.success) {
      replyText.value = ''
      lastMessageId.value = 0
      await loadMessages(selectedId.value, true, true)
      const convo = await apiGet('get_conversation', { id: selectedId.value })
      if (convo.success && convo.conversation) selectedConvo.value = convo.conversation
    } else {
      window.alert(data.error || 'Send failed')
    }
  } finally {
    sending.value = false
  }
}

async function loadTemplates() {
  if (templatesLoaded.value) return
  const data = await apiGet('list_templates')
  if (data.success) {
    templates.value = data.templates ?? []
    templatesLoaded.value = true
  }
}

async function loadFlows() {
  if (flowsLoaded.value) return
  const data = await apiGet('list_flows')
  if (data.success) {
    flows.value = data.flows ?? []
    flowsLoaded.value = true
  }
}

async function sendFlow() {
  const flowId = parseInt(selectedFlowId.value, 10)
  if (!flowId || !selectedId.value) return
  flowSending.value = true
  try {
    const data = await apiPost('send_flow', {
      conversation_id: selectedId.value,
      flow_id: flowId,
    })
    if (data.success) {
      flowModalOpen.value = false
      selectedFlowId.value = ''
      lastMessageId.value = 0
      await loadMessages(selectedId.value, true, true)
      const convo = await apiGet('get_conversation', { id: selectedId.value })
      if (convo.success && convo.conversation) selectedConvo.value = convo.conversation
    } else {
      window.alert(data.error || 'Could not start flow')
    }
  } finally {
    flowSending.value = false
  }
}

async function runAiDraft() {
  if (!selectedId.value) return
  aiDrafting.value = true
  const prev = replyText.value
  replyText.value = 'Generating draft…'
  try {
    const data = await apiPost('ai_draft', { conversation_id: selectedId.value })
    if (data.success && data.draft) {
      replyText.value = data.draft
    } else {
      replyText.value = prev
      window.alert(`AI draft failed: ${data.error || 'Unknown error'}`)
    }
  } catch {
    replyText.value = prev
    window.alert('Network error — could not reach AI.')
  } finally {
    aiDrafting.value = false
  }
}

async function openScheduleModal() {
  if (!selectedId.value || !selectedConvo.value) return
  await Promise.all([loadTemplates(), loadFlows()])
  schedMsgType.value = 'text'
  schedTextBody.value = replyText.value.trim()
  schedTemplateId.value = ''
  schedFlowId.value = ''
  schedSendAt.value = ''
  schedNotes.value = ''
  schedFeedback.value = null
  scheduleModalOpen.value = true
}

async function submitSchedule() {
  if (!selectedId.value || !schedSendAt.value) {
    window.alert('Please pick a send date and time.')
    return
  }
  schedSubmitting.value = true
  schedFeedback.value = null
  try {
    const payload: Record<string, unknown> = {
      conversation_id: selectedId.value,
      message_type: schedMsgType.value,
      send_at: schedSendAt.value,
      notes: schedNotes.value.trim(),
    }
    if (schedMsgType.value === 'text') payload.text_body = schedTextBody.value
    if (schedMsgType.value === 'template') {
      payload.template_id = parseInt(schedTemplateId.value, 10) || 0
    }
    if (schedMsgType.value === 'flow') {
      payload.flow_id = parseInt(schedFlowId.value, 10) || 0
    }
    const data = await apiPost('schedule_message', payload)
    if (data.success) {
      schedFeedback.value = `Scheduled for ${data.scheduled_at ?? schedSendAt.value} IST.`
      if (schedMsgType.value === 'text') replyText.value = ''
      window.setTimeout(() => {
        scheduleModalOpen.value = false
      }, 2000)
    } else {
      window.alert(`Error: ${data.error || 'Could not schedule'}`)
    }
  } catch {
    window.alert('Network error — please try again.')
  } finally {
    schedSubmitting.value = false
  }
}

const schedMinDatetime = computed(() =>
  new Date(Date.now() - new Date().getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16),
)

async function sendTemplate() {
  const templateId = parseInt(selectedTemplateId.value, 10)
  if (!templateId || !selectedId.value) return
  sending.value = true
  try {
    const data = await apiPost('send_template', {
      conversation_id: selectedId.value,
      template_id: templateId,
    })
    if (data.success) {
      templateModalOpen.value = false
      selectedTemplateId.value = ''
      lastMessageId.value = 0
      await loadMessages(selectedId.value, true, true)
      const convo = await apiGet('get_conversation', { id: selectedId.value })
      if (convo.success && convo.conversation) selectedConvo.value = convo.conversation
    } else {
      window.alert(data.error || 'Template send failed')
    }
  } finally {
    sending.value = false
  }
}

let listPollTimer: ReturnType<typeof setInterval> | null = null
let msgPollTimer: ReturnType<typeof setInterval> | null = null
let searchTimer: ReturnType<typeof setTimeout> | null = null

function onVisibility() {
  if (!document.hidden && selectedId.value) void loadMessages(selectedId.value, false)
}

function onDocMouseDown(e: MouseEvent) {
  const t = e.target as HTMLElement | null
  if (t?.closest('[data-wa-tag-menu]')) return
  tagMenuOpen.value = false
}

onMounted(() => {
  void loadCatalog()
  listPollTimer = setInterval(() => {
    if (document.hidden) return
    void loadConversations()
  }, 12000)
  document.addEventListener('visibilitychange', onVisibility)
})

watch(catalogReady, (ready) => {
  if (ready) void loadConversations()
})

watch(search, () => {
  if (!catalogReady.value) return
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    listLoading.value = true
    void loadConversations()
  }, 350)
})

watch([statusFilter, tagFilterId, smartListId], () => {
  if (!catalogReady.value) return
  listLoading.value = true
  void loadConversations()
})

watch(selectedId, (id) => {
  tagMenuOpen.value = false
  if (msgPollTimer) {
    clearInterval(msgPollTimer)
    msgPollTimer = null
  }
  if (!id) return
  msgPollTimer = setInterval(() => {
    if (document.hidden) return
    void loadMessages(id, false)
  }, 4000)
})

watch(tagMenuOpen, (open) => {
  if (open) {
    document.addEventListener('mousedown', onDocMouseDown)
  } else {
    document.removeEventListener('mousedown', onDocMouseDown)
  }
})

onUnmounted(() => {
  if (listPollTimer) clearInterval(listPollTimer)
  if (msgPollTimer) clearInterval(msgPollTimer)
  if (searchTimer) clearTimeout(searchTimer)
  document.removeEventListener('visibilitychange', onVisibility)
  document.removeEventListener('mousedown', onDocMouseDown)
})

const chatOpen = computed(() => selectedId.value > 0)
const windowOpen = computed(() => selectedConvo.value?.window_open === true)
const isActive = computed(() => selectedConvo.value?.status === 'active')
const threadTotal = computed(() => threadContext.value?.total ?? 1)
const threadOrdinal = computed(() => threadContext.value?.ordinal ?? 1)
const previousThreads = computed(() => threadContext.value?.previous ?? [])
const leadStatus = computed(() => selectedConvo.value?.lead_status ?? null)
const leadSent = computed(() => leadStatus.value === 'lead_sent')
const convoTags = computed(() => selectedConvo.value?.tags ?? [])
const assignedTagIds = computed(() => new Set(convoTags.value.map(t => t.id)))
const availableTagsToAdd = computed(() =>
  accountTags.value.filter(t => !assignedTagIds.value.has(t.id)),
)
const leadSourceSelectOptions = computed(() => [
  'WhatsApp Manual',
  ...leadSourceOptions.value
    .map(row => row.campaign_name)
    .filter((name): name is string => Boolean(name) && name !== 'WhatsApp Manual'),
])

function closeSendCrmModal() {
  if (!sendLeadSubmitting.value) sendCrmModalOpen.value = false
}

function onReplyKeydown(e: KeyboardEvent) {
  if (e.ctrlKey && e.key === 'Enter') void sendText()
}

function tagChipStyle(tag: WaInboxTag, active?: boolean) {
  const color = tag.color || '#6b7280'
  if (active) return { backgroundColor: color, color: '#fff' }
  return {
    backgroundColor: `${color}14`,
    color,
    border: `1px solid ${color}33`,
  }
}

function tagChipInlineStyle(tag: WaInboxTag) {
  const color = tag.color || '#6b7280'
  return {
    backgroundColor: `${color}18`,
    color,
    border: `1px solid ${color}44`,
  }
}
</script>

<template>
  <div
    class="flex h-full min-h-0 bg-[#f4f6f9]"
    @pointerdown="unlockWaInboxNotificationSound()"
  >
    <!-- Conversation list -->
    <div
      class="flex h-full w-[300px] min-w-[260px] max-w-[360px] shrink-0 flex-col border-r border-slate-200 bg-white"
      :class="chatOpen ? 'hidden md:flex' : 'flex'"
    >
      <div class="flex flex-wrap gap-2 border-b border-slate-200 p-3">
        <input
          v-model="search"
          type="text"
          placeholder="Search name or phone…"
          class="min-w-0 flex-1 rounded-md border border-slate-200 px-2.5 py-1.5 text-sm outline-none focus:border-[#0097A7]"
        >
        <select
          v-if="smartLists.length === 0"
          v-model="statusFilter"
          class="rounded-md border border-slate-200 px-2 py-1.5 text-sm outline-none focus:border-[#0097A7]"
        >
          <option value="active">Active</option>
          <option value="closed">Closed</option>
          <option value="all">All</option>
        </select>
      </div>

      <div
        v-if="smartLists.length > 0"
        class="flex flex-wrap gap-1.5 border-b border-slate-100 px-3 py-2"
      >
        <span class="self-center text-[10px] font-medium uppercase tracking-wide text-slate-400">
          Lists
        </span>
        <button
          v-for="list in smartLists"
          :key="list.id"
          type="button"
          :title="list.summary || list.name"
          class="max-w-[140px] truncate rounded-full px-2.5 py-0.5 text-[11px] font-medium transition"
          :class="smartListId === list.id
            ? 'bg-[#0097A7] text-white'
            : 'bg-slate-100 text-slate-600 hover:bg-slate-200'"
          @click="selectSmartList(list.id)"
        >
          {{ list.name }}{{ list.mode === 'frozen' ? ' ❄' : '' }}
        </button>
      </div>

      <div
        v-if="accountTags.length > 0"
        class="flex flex-wrap gap-1.5 border-b border-slate-100 px-3 py-2"
      >
        <span class="self-center text-[10px] font-medium uppercase tracking-wide text-slate-400">
          Tags
        </span>
        <button
          type="button"
          class="rounded-full px-2.5 py-0.5 text-[11px] font-medium transition"
          :class="!tagFilterId
            ? 'bg-slate-700 text-white'
            : 'bg-slate-100 text-slate-600 hover:bg-slate-200'"
          @click="selectTagFilter(null)"
        >
          All
        </button>
        <button
          v-for="tag in accountTags"
          :key="tag.id"
          type="button"
          class="max-w-[120px] truncate rounded-full px-2.5 py-0.5 text-[11px] font-medium transition"
          :style="tagChipStyle(tag, tagFilterId === tag.id)"
          @click="selectTagFilter(tagFilterId === tag.id ? null : tag.id)"
        >
          {{ tag.name }}
        </button>
      </div>

      <div
        v-if="activeSmartList"
        class="border-b border-slate-100 bg-slate-50 px-3 py-2 text-[11px] text-slate-500"
      >
        <span class="font-semibold text-slate-700">{{ activeSmartList.name }}</span>
        <span class="ml-1.5 rounded bg-white px-1.5 py-px text-[10px] uppercase tracking-wide text-slate-500">
          {{ activeSmartList.mode === 'frozen' ? 'Frozen' : 'Dynamic' }}
        </span>
        <span
          v-if="activeSmartList.is_system"
          class="ml-1 rounded bg-white px-1.5 py-px text-[10px] uppercase tracking-wide text-slate-500"
        >
          Default
        </span>
        <div
          v-if="activeSmartList.summary"
          class="mt-0.5 truncate"
          :title="activeSmartList.summary"
        >
          {{ activeSmartList.summary }}
        </div>
      </div>

      <div class="min-h-0 flex-1 overflow-y-auto">
        <div
          v-if="listLoading && conversations.length === 0"
          class="flex items-center justify-center p-8 text-slate-400"
        >
          <UIcon name="i-lucide-loader-circle" class="h-5 w-5 animate-spin" />
        </div>
        <div
          v-else-if="conversations.length === 0"
          class="p-8 text-center text-sm text-slate-400"
        >
          No conversations found.
        </div>
        <template v-else>
          <button
            v-for="cv in conversations"
            :key="cv.id"
            type="button"
            class="block w-full border-b border-l-[3px] border-slate-100 py-3 text-left transition"
            :class="cv.id === selectedId
              ? 'border-l-[#0097A7] bg-[#0097A7]/15 pl-[calc(0.875rem-3px)] pr-3.5 shadow-[inset_0_0_0_1px_rgba(0,151,167,0.12)]'
              : `border-l-transparent px-3.5 hover:bg-slate-50${cv.needs_attention ? ' bg-amber-50/80' : ''}`"
            @click="openConversation(cv.id)"
          >
            <div class="flex justify-between gap-2">
              <span
                class="truncate text-sm font-semibold"
                :class="cv.id === selectedId ? 'text-[#006874]' : 'text-slate-800'"
              >
                {{ cv.contact_name }}
              </span>
              <span
                class="shrink-0 text-[11px]"
                :class="cv.id === selectedId ? 'font-medium text-[#0097A7]' : 'text-slate-400'"
              >
                {{ fmtWaInboxTime(cv.last_message_at) }}
              </span>
            </div>
            <div
              class="truncate text-xs"
              :class="cv.id === selectedId ? 'text-slate-600' : 'text-slate-500'"
            >
              {{ (cv.last_msg ?? '').substring(0, 45) }}
            </div>
            <div v-if="(cv.tags ?? []).length" class="mt-1.5 flex flex-wrap gap-1">
              <span
                v-for="tag in (cv.tags ?? []).slice(0, 3)"
                :key="tag.id"
                class="inline-flex max-w-full items-center gap-0.5 rounded px-1 py-px text-[9px] font-medium"
                :style="tagChipInlineStyle(tag)"
                :title="tag.name"
              >
                <span class="truncate">{{ tag.name }}</span>
              </span>
              <span
                v-if="(cv.tags ?? []).length > 3"
                class="text-[9px] text-slate-400"
              >
                +{{ (cv.tags ?? []).length - 3 }}
              </span>
            </div>
            <span
              v-if="cv.needs_attention"
              class="mt-1 inline-block rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-800"
            >
              Needs attention
            </span>
          </button>
        </template>
      </div>
    </div>

    <!-- Chat pane -->
    <div
      class="flex min-w-0 flex-1 flex-col"
      :class="chatOpen ? 'flex' : 'hidden md:flex'"
    >
      <div
        v-if="!chatOpen"
        class="flex h-full flex-col items-center justify-center text-slate-400"
      >
        <span class="mb-3 text-5xl opacity-20">💬</span>
        <p class="text-sm">Select a conversation</p>
      </div>

      <template v-else>
        <div class="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-2.5">
          <div class="flex min-w-0 items-center gap-2">
            <button
              type="button"
              class="rounded-md border border-slate-200 px-2 py-1 text-sm md:hidden"
              @click="clearSelection"
            >
              ←
            </button>
            <div class="min-w-0">
              <div class="truncate font-semibold text-slate-800">
                {{ selectedConvo?.contact_name || selectedConvo?.wa_id || '—' }}
              </div>
              <div class="truncate text-xs text-slate-400">
                {{ selectedConvo?.wa_id }}
              </div>
              <div
                v-if="selectedConvo && threadTotal <= 1"
                class="mt-1 text-[11px] text-slate-500"
              >
                First conversation · Started {{ fmtWaInboxDateShort(selectedConvo.started_at) }}
                <span
                  v-if="leadStatus"
                  class="ml-1.5 rounded px-1.5 py-0.5 font-medium"
                  :class="leadStatus === 'lead_sent'
                    ? 'bg-emerald-50 text-emerald-700'
                    : leadStatus === 'lead_failed'
                      ? 'bg-red-50 text-red-700'
                      : 'bg-slate-100 text-slate-600'"
                >
                  Lead: {{ waInboxLeadStatusLabel(leadStatus, selectedConvo.lead_status_label) }}
                </span>
              </div>
            </div>
          </div>
          <div class="flex shrink-0 flex-wrap items-center justify-end gap-1">
            <span
              v-if="leadSent"
              class="rounded bg-emerald-50 px-2 py-1 text-[11px] font-medium text-emerald-700"
            >
              ✓ {{ waInboxLeadStatusLabel(leadStatus, selectedConvo?.lead_status_label) || 'Sent to CRM' }}
            </span>
            <button
              v-else
              type="button"
              class="rounded-md border border-[#0097A7]/40 px-2.5 py-1 text-xs font-medium text-[#0097A7] hover:bg-[#0097A7]/5"
              @click="sendCrmModalOpen = true"
            >
              {{ leadStatus === 'lead_failed' ? 'Retry CRM' : 'Send to CRM' }}
            </button>
            <button
              v-if="selectedConvo?.needs_attention"
              type="button"
              class="rounded-md border border-amber-300 px-2 py-1 text-xs text-amber-700 hover:bg-amber-50"
              title="Resolve attention"
              @click="resolveAttention()"
            >
              ✓
            </button>
            <button
              type="button"
              class="rounded-md border border-slate-200 px-2.5 py-1 text-xs text-slate-600 hover:bg-slate-50"
              @click="selectedConvo?.status === 'active' ? closeConvo() : reopenConvo()"
            >
              {{ selectedConvo?.status === 'active' ? 'Close' : 'Reopen' }}
            </button>
          </div>
        </div>

        <div
          v-if="selectedConvo && accountTags.length > 0"
          data-wa-tag-menu
          class="flex flex-wrap items-center gap-1.5 border-b border-slate-100 bg-white px-4 py-2"
        >
          <UIcon name="i-lucide-tag" class="h-3.5 w-3.5 shrink-0 text-slate-400" />
          <span v-if="convoTags.length === 0" class="text-[11px] text-slate-400">No tags</span>
          <span
            v-for="tag in convoTags"
            :key="tag.id"
            class="inline-flex max-w-full items-center gap-0.5 rounded px-1.5 py-0.5 text-[10px] font-medium"
            :style="tagChipInlineStyle(tag)"
            :title="tag.name"
          >
            <span class="truncate">{{ tag.name }}</span>
            <button
              type="button"
              class="ml-0.5 rounded p-px hover:bg-black/10"
              :aria-label="`Remove ${tag.name}`"
              @click.stop="removeTagFromConvo(tag.id)"
            >
              <UIcon name="i-lucide-x" class="h-2.5 w-2.5" />
            </button>
          </span>
          <div class="relative">
            <button
              type="button"
              :disabled="tagBusy || availableTagsToAdd.length === 0"
              class="rounded-md border border-dashed border-slate-300 px-2 py-0.5 text-[11px] text-slate-500 hover:border-[#0097A7] hover:text-[#0097A7] disabled:cursor-not-allowed disabled:opacity-40"
              @click="tagMenuOpen = !tagMenuOpen"
            >
              + Tag
            </button>
            <div
              v-if="tagMenuOpen"
              class="absolute top-full left-0 z-20 mt-1 max-h-48 min-w-[160px] overflow-y-auto rounded-md border border-slate-200 bg-white py-1 shadow-lg"
            >
              <button
                v-for="tag in availableTagsToAdd"
                :key="tag.id"
                type="button"
                :disabled="tagBusy"
                class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs hover:bg-slate-50"
                @click="addTagToConvo(tag.id)"
              >
                <span
                  class="h-2.5 w-2.5 shrink-0 rounded-full"
                  :style="{ backgroundColor: tag.color || '#6b7280' }"
                />
                <span class="truncate text-slate-700">{{ tag.name }}</span>
              </button>
            </div>
          </div>
        </div>

        <div
          v-if="selectedConvo && threadTotal > 1"
          class="border-b-2 border-amber-300 bg-gradient-to-r from-amber-100 via-amber-50 to-amber-100 px-4 py-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.6)]"
        >
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div class="flex min-w-0 items-start gap-3">
              <span
                class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-amber-500 text-white shadow-md ring-4 ring-amber-200/80"
                aria-hidden="true"
              >
                <UIcon name="i-lucide-sparkles" class="h-5 w-5" />
              </span>
              <div class="min-w-0">
                <p class="text-sm font-bold text-amber-950">
                  Returning patient
                  <span class="ml-2 inline-flex rounded-full bg-amber-500 px-2 py-0.5 text-[10px] font-bold tracking-wide text-white uppercase">
                    Priority
                  </span>
                </p>
                <p class="mt-0.5 text-xs font-semibold text-amber-900">
                  Previously engaged — strong chance to convert. Handle with care.
                </p>
                <p class="mt-1 text-[11px] text-amber-800/90">
                  Conversation {{ threadOrdinal }} of {{ threadTotal }} · Started
                  {{ fmtWaInboxDateShort(selectedConvo.started_at) }}
                  <span
                    v-if="leadStatus"
                    class="ml-1.5 rounded bg-white/70 px-1.5 py-0.5 font-medium text-amber-950"
                  >
                    Lead: {{ waInboxLeadStatusLabel(leadStatus, selectedConvo.lead_status_label) }}
                  </span>
                </p>
              </div>
            </div>
            <button
              v-if="previousThreads.length > 0"
              type="button"
              class="shrink-0 rounded-lg border-2 border-amber-400 bg-white px-3 py-1.5 text-xs font-bold text-amber-900 shadow-sm transition hover:bg-amber-50"
              @click="pastConvosModalOpen = true"
            >
              View {{ previousThreads.length }} previous
            </button>
          </div>
        </div>

        <div
          v-if="selectedConvo"
          class="px-4 py-1 text-xs"
          :class="windowOpen ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-red-600'"
        >
          {{ windowOpen
            ? `Messaging window open — ${Math.floor((selectedConvo.window_seconds_left || 0) / 60)} min left`
            : '24-hour window closed — send a template to re-engage' }}
        </div>

        <div ref="messageAreaRef" class="min-h-0 flex-1 overflow-y-auto p-4">
          <DeskWaInboxMessageBubble
            v-for="msg in messages"
            :key="msg.id"
            :msg="msg"
          />
        </div>

        <div v-if="isActive" class="border-t border-slate-200 bg-white p-3">
          <div class="mb-2 flex flex-wrap items-center gap-2">
            <button
              type="button"
              :class="`${actionBtnClass} border-slate-200 text-slate-600 hover:bg-slate-50`"
              @click="templateModalOpen = true; loadTemplates()"
            >
              <UIcon name="i-lucide-layers" class="h-3.5 w-3.5" />
              Template
            </button>
            <button
              v-if="windowOpen"
              type="button"
              :class="`${actionBtnClass} border-sky-200 text-sky-700 hover:bg-sky-50`"
              @click="flowModalOpen = true; loadFlows()"
            >
              <UIcon name="i-lucide-git-branch" class="h-3.5 w-3.5" />
              Flow
            </button>
            <button
              type="button"
              :disabled="aiDrafting || !windowOpen"
              :class="`${actionBtnClass} border-amber-200 text-amber-800 hover:bg-amber-50`"
              @click="runAiDraft()"
            >
              <UIcon
                :name="aiDrafting ? 'i-lucide-loader-circle' : 'i-lucide-wand-2'"
                class="h-3.5 w-3.5"
                :class="{ 'animate-spin': aiDrafting }"
              />
              AI Draft
            </button>
            <button
              type="button"
              :class="`${actionBtnClass} border-slate-200 text-slate-600 hover:bg-slate-50`"
              @click="openScheduleModal()"
            >
              <UIcon name="i-lucide-calendar-clock" class="h-3.5 w-3.5" />
              Schedule
            </button>
            <span v-if="!windowOpen" class="text-[11px] text-red-600">
              Free text unavailable — use a template to re-open window
            </span>
          </div>
          <div v-if="windowOpen" class="flex gap-2">
            <textarea
              v-model="replyText"
              rows="2"
              :disabled="aiDrafting"
              placeholder="Type a message… (Ctrl+Enter to send)"
              class="min-h-[44px] flex-1 resize-none rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-[#0097A7] disabled:bg-slate-50"
              @keydown="onReplyKeydown"
            />
            <button
              type="button"
              :disabled="sending || aiDrafting || !replyText.trim()"
              class="flex h-[44px] w-[44px] shrink-0 items-center justify-center rounded-md bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50"
              @click="sendText()"
            >
              <UIcon
                :name="sending ? 'i-lucide-loader-circle' : 'i-lucide-send'"
                class="h-4 w-4"
                :class="{ 'animate-spin': sending }"
              />
            </button>
          </div>
          <div v-else class="flex gap-2">
            <textarea
              rows="2"
              disabled
              placeholder="24-hour window expired — send a template to re-engage"
              class="min-h-[44px] flex-1 resize-none rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-400"
            />
            <button
              type="button"
              disabled
              class="flex h-[44px] w-[44px] shrink-0 items-center justify-center rounded-md bg-slate-300 text-white"
            >
              <UIcon name="i-lucide-send" class="h-4 w-4" />
            </button>
          </div>
        </div>
      </template>
    </div>

    <!-- Template modal -->
    <DeskWaInboxModal
      :open="templateModalOpen"
      title="Send template"
      @close="templateModalOpen = false"
    >
      <select
        v-model="selectedTemplateId"
        class="w-full rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-[#0097A7]"
      >
        <option value="">— Select template —</option>
        <option v-for="t in templates" :key="t.id" :value="String(t.id)">
          {{ t.name }} ({{ t.language }})
        </option>
      </select>
      <template #footer>
        <div class="flex w-full justify-end gap-2">
          <button
            type="button"
            class="rounded-md border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:bg-white"
            @click="templateModalOpen = false"
          >
            Cancel
          </button>
          <button
            type="button"
            :disabled="sending || !selectedTemplateId"
            class="rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-40"
            @click="sendTemplate()"
          >
            Send
          </button>
        </div>
      </template>
    </DeskWaInboxModal>

    <!-- Flow modal -->
    <DeskWaInboxModal
      :open="flowModalOpen"
      @close="flowModalOpen = false"
    >
      <template #title>
        <span class="flex items-center gap-2">
          <UIcon name="i-lucide-git-branch" class="h-4 w-4 text-sky-600" />
          Trigger Flow
        </span>
      </template>
      <p class="mb-3 text-sm text-slate-600">
        Start a conversation flow for this customer now.
      </p>
      <label class="mb-1 block text-sm font-medium text-slate-700">Flow</label>
      <select
        v-model="selectedFlowId"
        class="w-full rounded-md border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-[#0097A7] focus:ring-2 focus:ring-[#0097A7]/20"
      >
        <option value="">— Select flow —</option>
        <option v-for="f in flows" :key="f.id" :value="String(f.id)">
          {{ f.name }}
        </option>
      </select>
      <button
        type="button"
        :disabled="flowSending || !selectedFlowId"
        class="mt-4 flex w-full items-center justify-center gap-2 rounded-lg border-2 border-[#007A87] bg-[#0097A7] px-4 py-3 text-base font-semibold text-white shadow-md hover:bg-[#007A87] disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-200 disabled:text-slate-500 disabled:shadow-none"
        @click="sendFlow()"
      >
        <UIcon
          :name="flowSending ? 'i-lucide-loader-circle' : 'i-lucide-git-branch'"
          class="h-5 w-5"
          :class="{ 'animate-spin': flowSending }"
        />
        {{ flowSending ? 'Starting flow…' : 'Start Flow Now' }}
      </button>
      <p v-if="!selectedFlowId" class="mt-2 text-center text-xs text-slate-500">
        Select a flow above to enable Start Flow.
      </p>
      <template #footer>
        <div class="grid w-full grid-cols-2 gap-3">
          <button
            type="button"
            class="rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-100"
            @click="flowModalOpen = false"
          >
            Cancel
          </button>
          <button
            type="button"
            :disabled="flowSending || !selectedFlowId"
            class="rounded-lg border-2 border-[#007A87] bg-[#0097A7] px-3 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-[#007A87] disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-200 disabled:text-slate-500"
            @click="sendFlow()"
          >
            <span v-if="flowSending" class="inline-flex items-center justify-center gap-1.5">
              <UIcon name="i-lucide-loader-circle" class="h-4 w-4 animate-spin" />
              Starting…
            </span>
            <span v-else>Start Flow</span>
          </button>
        </div>
      </template>
    </DeskWaInboxModal>

    <!-- Schedule modal -->
    <DeskWaInboxModal
      :open="scheduleModalOpen"
      body-class="space-y-3 p-4"
      @close="scheduleModalOpen = false"
    >
      <template #title>
        <span class="flex items-center gap-2">
          <UIcon name="i-lucide-calendar-clock" class="h-4 w-4 text-slate-500" />
          Schedule Message
        </span>
      </template>

      <div class="rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
        To: <strong>{{ selectedConvo?.contact_name || selectedConvo?.wa_id }}</strong>
        <span class="text-emerald-700/70">({{ selectedConvo?.wa_id }})</span>
      </div>

      <div>
        <label class="mb-1 block text-sm font-medium text-slate-700">Message Type</label>
        <select
          v-model="schedMsgType"
          class="w-full rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-[#0097A7]"
        >
          <option value="text">Plain Text</option>
          <option value="template">Template</option>
          <option value="flow">Flow (scheduled start)</option>
        </select>
        <p
          v-if="schedMsgType === 'text'"
          class="mt-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800"
        >
          Text only reaches patients who messaged in the last 24 hours. Use
          <strong>Template</strong> for guaranteed delivery.
        </p>
        <p v-if="schedMsgType === 'flow'" class="mt-2 text-xs text-slate-500">
          To start a flow immediately, use the <strong>Flow</strong> button in the reply bar.
        </p>
      </div>

      <div v-if="schedMsgType === 'text'">
        <label class="mb-1 block text-sm font-medium text-slate-700">Message</label>
        <textarea
          v-model="schedTextBody"
          rows="4"
          placeholder="Type your message…"
          class="w-full resize-none rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-[#0097A7]"
        />
      </div>

      <div v-if="schedMsgType === 'template'">
        <label class="mb-1 block text-sm font-medium text-slate-700">Template</label>
        <select
          v-model="schedTemplateId"
          class="w-full rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-[#0097A7]"
        >
          <option value="">— pick template —</option>
          <option v-for="t in templates" :key="t.id" :value="String(t.id)">
            {{ t.name }} ({{ t.language }})
          </option>
        </select>
      </div>

      <div v-if="schedMsgType === 'flow'">
        <label class="mb-1 block text-sm font-medium text-slate-700">Flow</label>
        <select
          v-model="schedFlowId"
          class="w-full rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-[#0097A7]"
        >
          <option value="">— pick flow —</option>
          <option v-for="f in flows" :key="f.id" :value="String(f.id)">
            {{ f.name }}
          </option>
        </select>
      </div>

      <div>
        <label class="mb-1 block text-sm font-medium text-slate-700">
          Send At (IST) <span class="text-red-500">*</span>
        </label>
        <input
          v-model="schedSendAt"
          type="datetime-local"
          :min="schedMinDatetime"
          class="w-full rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-[#0097A7]"
        >
      </div>

      <div>
        <label class="mb-1 block text-sm font-medium text-slate-700">
          Notes <span class="font-normal text-slate-400">(optional)</span>
        </label>
        <input
          v-model="schedNotes"
          type="text"
          placeholder="e.g. follow-up reminder"
          class="w-full rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-[#0097A7]"
        >
      </div>

      <div
        v-if="schedFeedback"
        class="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800"
      >
        {{ schedFeedback }}
      </div>

      <template #footer>
        <div class="flex w-full justify-end gap-2">
          <button
            type="button"
            class="rounded-md border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:bg-white"
            @click="scheduleModalOpen = false"
          >
            Cancel
          </button>
          <button
            type="button"
            :disabled="schedSubmitting || !schedSendAt"
            class="rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-40"
            @click="submitSchedule()"
          >
            {{ schedSubmitting ? 'Saving…' : 'Schedule' }}
          </button>
        </div>
      </template>
    </DeskWaInboxModal>

    <!-- Past conversations modal -->
    <DeskWaInboxModal
      :open="pastConvosModalOpen"
      body-class="p-0"
      @close="pastConvosModalOpen = false"
    >
      <template #title>
        <span class="flex items-center gap-2">
          <UIcon name="i-lucide-history" class="h-4 w-4 text-slate-500" />
          Previous conversations
        </span>
      </template>
      <div v-if="previousThreads.length === 0" class="p-4 text-sm text-slate-400">
        No previous conversations.
      </div>
      <div v-else class="divide-y divide-slate-100">
        <button
          v-for="past in previousThreads"
          :key="past.id"
          type="button"
          class="flex w-full items-start justify-between gap-3 px-4 py-3 text-left hover:bg-slate-50"
          @click="pastConvosModalOpen = false; openConversation(past.id)"
        >
          <div>
            <div class="flex flex-wrap items-center gap-2 text-sm font-semibold text-slate-800">
              {{ fmtWaInboxDateShort(past.started_at) }}
              <span
                class="rounded px-1.5 py-0.5 text-[10px] font-medium"
                :class="past.status === 'active'
                  ? 'bg-emerald-50 text-emerald-700'
                  : 'bg-slate-100 text-slate-600'"
              >
                {{ past.status }}
              </span>
            </div>
            <div class="mt-0.5 text-xs text-slate-500">
              {{ past.msg_count || 0 }} messages
              <template v-if="past.last_message_at">
                · Last activity {{ fmtWaInboxDateShort(past.last_message_at) }}
              </template>
              <template v-if="past.lead_status">
                · Lead: {{ past.lead_status.replace(/_/g, ' ') }}
              </template>
            </div>
          </div>
          <span class="mt-1 text-xs text-slate-400">›</span>
        </button>
      </div>
    </DeskWaInboxModal>

    <!-- Send to CRM modal -->
    <DeskWaInboxModal
      v-if="selectedConvo"
      :open="sendCrmModalOpen"
      @close="closeSendCrmModal"
    >
      <template #title>
        <span class="flex items-center gap-2">
          <UIcon name="i-lucide-send" class="h-4 w-4 text-[#0097A7]" />
          Send to CRM
        </span>
      </template>
      <p class="mb-3 text-sm text-slate-600">
        Push
        <strong>{{ selectedConvo.contact_name || selectedConvo.wa_id }}</strong>
        ({{ selectedConvo.wa_id }}) to the leads app with the full conversation transcript.
      </p>
      <label class="mb-1 block text-sm font-medium text-slate-700">Source / campaign</label>
      <select
        v-model="leadSource"
        class="mb-3 w-full rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-[#0097A7]"
      >
        <option v-for="name in leadSourceSelectOptions" :key="name" :value="name">
          {{ name }}
        </option>
      </select>
      <div
        v-if="leadStatus === 'not_a_lead'"
        class="rounded-md bg-slate-100 px-3 py-2 text-xs text-slate-700"
      >
        Auto-check marked this as <strong>not a lead</strong>. You can still push manually.
      </div>
      <div
        v-if="leadStatus === 'lead_failed'"
        class="rounded-md bg-red-50 px-3 py-2 text-xs text-red-800"
      >
        Previous send <strong>failed</strong>. Retry will attempt the CRM webhook again.
      </div>
      <template #footer>
        <div class="flex w-full justify-end gap-2">
          <button
            type="button"
            :disabled="sendLeadSubmitting"
            class="rounded-md border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:bg-white disabled:opacity-50"
            @click="sendCrmModalOpen = false"
          >
            Cancel
          </button>
          <button
            type="button"
            :disabled="sendLeadSubmitting"
            class="inline-flex items-center gap-1.5 rounded-md bg-[#0097A7] px-3 py-1.5 text-sm font-medium text-white hover:bg-[#007A87] disabled:opacity-50"
            @click="sendLeadToCrm()"
          >
            <UIcon
              :name="sendLeadSubmitting ? 'i-lucide-loader-circle' : 'i-lucide-send'"
              class="h-3.5 w-3.5"
              :class="{ 'animate-spin': sendLeadSubmitting }"
            />
            {{ sendLeadSubmitting ? 'Sending…' : 'Send & mark processed' }}
          </button>
        </div>
      </template>
    </DeskWaInboxModal>
  </div>
</template>
