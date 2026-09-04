<script setup lang="ts">
type ClientRow = {
  client_id: number
  name: string
  number: string | null
  place: string | null
  status: string
  check_in_status: boolean
  profile_photo_url?: string | null
}

type NoteAttachment = { id: number | null, key: string, url: string | null }

type TimelineItem = {
  id: string
  noteId?: number
  labCaseId?: number
  kind: 'note' | 'bill' | 'receipt' | 'rx' | 'appointment' | 'task' | 'lab'
  title: string
  body?: string
  at: string
  author?: string | null
  attachments?: NoteAttachment[]
}

type Client = ClientRow & {
  age: number | null
  gender: string | null
  client_personal_note: string | null
  checked_in_at: string | null
}

type PendingFile = { file: File, preview: string | null }

const lightbox = ref<string | null>(null)
const noteFiles = ref<PendingFile[]>([])
const fileInput = ref<HTMLInputElement | null>(null)
const photoInput = ref<HTMLInputElement | null>(null)
const uploadingPhoto = ref(false)
const removingAttach = ref<string | null>(null)
const saveOriginalQuality = ref(false)
const processingFiles = ref(false)

const MAX_NOTE_FILES = 10
const MAX_FILE_BYTES = 10 * 1024 * 1024

function hasImagePending() {
  return noteFiles.value.some(p => isImageFile(p.file))
}

function isImageAtt(att: NoteAttachment) {
  return /\.(jpe?g|png|gif|webp|heic|bmp)(\?|$)/i.test(att.key || att.url || '')
}

function isImageFile(file: File) {
  return file.type.startsWith('image/') || /\.(jpe?g|png|gif|webp|heic)$/i.test(file.name)
}

function fileLabel(key: string) {
  const part = key.split('/').pop() || key
  return part.length > 28 ? `…${part.slice(-24)}` : part
}

function clearNoteFiles() {
  for (const p of noteFiles.value) {
    if (p.preview) URL.revokeObjectURL(p.preview)
  }
  noteFiles.value = []
  saveOriginalQuality.value = false
}

const { api } = useApi()
const { patientId, openPatient, clearPatient } = useDeskUrl()
const toast = useToast()
const refreshBadges = inject<() => void>('deskRefreshBadges', () => {})

const q = ref('')
const list = ref<ClientRow[]>([])
const loadingList = ref(false)
const client = ref<Client | null>(null)
const timeline = ref<TimelineItem[]>([])
const loadingChart = ref(false)
const noteBody = ref('')
const savingNote = ref(false)
const noteDatetime = ref(localDatetimeInputValue())
const noteShowDatetime = ref(false)
const noteDatetimeCustomized = ref(false)
const toggling = ref(false)
const bookOpen = ref(false)
const labCreateOpen = ref(false)
const labDetailOpen = ref(false)
const labDetailCaseId = ref<number | null>(null)
const timelineEl = ref<HTMLElement | null>(null)
const rxOpen = ref(false)
const billOpen = ref(false)
const savingRx = ref(false)
const savingBill = ref(false)
const medicineTemplates = ref<{ medicine_id: number, medicine_name: string, default_quantity: number | null, default_dosage: string | null, default_days: number | null, default_instructions: string | null }[]>([])
const rxNotes = ref('')
const rxItems = ref<{ medicine_id: number | null, medicine_name: string, quantity: number | null, dosage: string, days: number | null, instructions: string }[]>([
  { medicine_id: null, medicine_name: '', quantity: null, dosage: '', days: null, instructions: '' }
])
const billAmount = ref('')
const billDescription = ref('')
const billAmountInput = ref<{ $el?: HTMLElement } | null>(null)
const billDatetime = ref(localDatetimeInputValue())
const billShowDatetime = ref(false)
const billDatetimeCustomized = ref(false)

function scrollTimelineToBottom() {
  nextTick(() => {
    requestAnimationFrame(() => {
      const el = timelineEl.value
      if (el) el.scrollTop = el.scrollHeight
    })
  })
}

function formatWhen(iso: string) {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('en-IN', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit'
  })
}

async function loadList() {
  loadingList.value = true
  try {
    const [all, checked] = await Promise.all([
      api<{ items: ClientRow[] }>('/clients', { query: { q: q.value || undefined, limit: 80 } }),
      api<{ items: ClientRow[] }>('/clients', { query: { checked_in: true, limit: 50 } })
    ])
    const checkedIds = new Set(checked.items.map(c => c.client_id))
    const rest = all.items.filter(c => !checkedIds.has(c.client_id))
    list.value = [...checked.items, ...rest]
  } finally {
    loadingList.value = false
  }
}

async function loadChart(id: number) {
  loadingChart.value = true
  try {
    const [c, notes, bills, receipts, rxs, appts, tasks, labs] = await Promise.all([
      api<Client>(`/clients/${id}`),
      api<{ note_id: number, body: string, created_at: string, author_name: string | null, attachments?: NoteAttachment[] }[]>(`/clients/${id}/notes`),
      api<{ bill_id: number, amount_due: number, status: string, description: string | null, issued_at: string }[]>(`/clients/${id}/bills`),
      api<{ receipt_id: number, amount: number, payment_mode: string, description: string | null, received_at: string }[]>(`/clients/${id}/receipts`),
      api<{ prescription_id: number, prescription_date: string, notes: string | null, items: { medicine_name: string }[] }[]>(`/clients/${id}/prescriptions`),
      api<{ items: { appointment_id: number, appointment_date: string, appointment_time: string, status: string, doctor_name: string | null, service_name: string | null }[] }>('/appointments', { query: { client_id: id, limit: 50 } }),
      api<{ items: { task_id: number, task_description: string, status: string, due_date: string | null, created_at: string }[] }>('/tasks', { query: { client_id: id } }),
      api<{ cases: { case_id: number, case_ref: string, case_type: string | null, lab_name: string, stage: string, status: string, created_at: string, expected_return_date: string | null }[] }>(`/clients/${id}/lab-cases`)
    ])
    client.value = c
    const items: TimelineItem[] = []
    for (const n of notes) {
      items.push({
        id: `note-${n.note_id}`,
        noteId: n.note_id,
        kind: 'note',
        title: 'Note',
        body: n.body,
        at: n.created_at,
        author: n.author_name,
        attachments: n.attachments || []
      })
    }
    for (const b of bills) {
      items.push({
        id: `bill-${b.bill_id}`,
        kind: 'bill',
        title: `Bill · ₹${Number(b.amount_due).toLocaleString('en-IN')} · ${b.status}`,
        body: b.description || undefined,
        at: b.issued_at
      })
    }
    for (const r of receipts) {
      items.push({
        id: `rcpt-${r.receipt_id}`,
        kind: 'receipt',
        title: `Receipt · ₹${Number(r.amount).toLocaleString('en-IN')} · ${r.payment_mode}`,
        body: r.description || undefined,
        at: r.received_at
      })
    }
    for (const rx of rxs) {
      items.push({
        id: `rx-${rx.prescription_id}`,
        kind: 'rx',
        title: `Rx · ${rx.items.map(i => i.medicine_name).join(', ') || 'Prescription'}`,
        body: rx.notes || undefined,
        at: `${rx.prescription_date}T12:00:00`
      })
    }
    for (const a of appts.items) {
      items.push({
        id: `appt-${a.appointment_id}`,
        kind: 'appointment',
        title: `Appt · ${formatAmPm(a.appointment_time)} · ${a.status}`,
        body: [a.doctor_name, a.service_name].filter(Boolean).join(' · ') || undefined,
        at: `${a.appointment_date}T${a.appointment_time}:00`
      })
    }
    for (const t of tasks.items) {
      items.push({
        id: `task-${t.task_id}`,
        kind: 'task',
        title: `Task · ${t.status}`,
        body: t.task_description,
        at: t.created_at
      })
    }
    for (const lc of labs.cases) {
      items.push({
        id: `lab-${lc.case_id}`,
        labCaseId: lc.case_id,
        kind: 'lab',
        title: `Lab · ${lc.case_ref} · ${lc.stage.replace('_', ' ')}`,
        body: [lc.case_type, lc.lab_name, lc.expected_return_date ? `return ${lc.expected_return_date}` : null]
          .filter(Boolean)
          .join(' · ') || undefined,
        at: lc.created_at
      })
    }
    timeline.value = items.sort((a, b) => Date.parse(a.at) - Date.parse(b.at))
    scrollTimelineToBottom()
  } finally {
    loadingChart.value = false
  }
}

watch(q, () => { loadList() })
watch(patientId, (id) => {
  if (id) loadChart(id)
  else {
    client.value = null
    timeline.value = []
  }
}, { immediate: true })

onMounted(loadList)

async function toggleCheckin() {
  if (!client.value) return
  toggling.value = true
  try {
    const path = client.value.check_in_status ? 'check-out' : 'check-in'
    const data = await api<{ check_in_status: boolean, checked_in_at: string | null }>(
      `/clients/${client.value.client_id}/${path}`,
      { method: 'POST' }
    )
    client.value.check_in_status = data.check_in_status
    client.value.checked_in_at = data.checked_in_at
    await loadList()
    refreshBadges()
    toast.add({ title: data.check_in_status ? 'Checked in' : 'Checked out', color: 'success' })
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
  } finally {
    toggling.value = false
  }
}

async function addNote() {
  if (!client.value) return
  if (!noteBody.value.trim() && !noteFiles.value.length) return
  savingNote.value = true
  try {
    const fd = new FormData()
    fd.append('body', noteBody.value.trim())
    if (noteDatetimeCustomized.value) {
      fd.append('note_datetime', noteDatetime.value || localDatetimeInputValue())
    }
    for (const p of noteFiles.value) {
      fd.append('files', p.file)
    }
    await api(`/clients/${client.value.client_id}/notes`, {
      method: 'POST',
      body: fd
    })
    noteBody.value = ''
    clearNoteFiles()
    resetNoteDatetime()
    await loadChart(client.value.client_id)
    scrollTimelineToBottom()
    toast.add({ title: 'Note saved', color: 'success' })
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
  } finally {
    savingNote.value = false
  }
}

async function onPickFiles(ev: Event) {
  const input = ev.target as HTMLInputElement
  const picked = Array.from(input.files || [])
  input.value = ''
  if (!picked.length) return
  const room = MAX_NOTE_FILES - noteFiles.value.length
  if (room <= 0) {
    toast.add({ title: `Max ${MAX_NOTE_FILES} files per note`, color: 'warning' })
    return
  }
  const next = picked.slice(0, room)
  processingFiles.value = true
  try {
    for (const file of next) {
      if (file.size > MAX_FILE_BYTES) {
        toast.add({ title: `${file.name} exceeds 10 MB`, color: 'error' })
        continue
      }
      const okType = file.type.startsWith('image/') || file.type === 'application/pdf'
        || /\.(jpe?g|png|gif|webp|heic|pdf)$/i.test(file.name)
      if (!okType) {
        toast.add({ title: `${file.name}: images or PDF only`, color: 'error' })
        continue
      }

      let processed = file
      if (isImageFile(file) && !saveOriginalQuality.value) {
        try {
          processed = await compressImage(file)
        } catch {
          toast.add({
            title: `Couldn’t compress ${file.name}, uploading original`,
            color: 'warning'
          })
          processed = file
        }
      }

      if (processed.size > MAX_FILE_BYTES) {
        toast.add({ title: `${file.name} exceeds 10 MB after processing`, color: 'error' })
        continue
      }

      noteFiles.value.push({
        file: processed,
        preview: isImageFile(processed) ? URL.createObjectURL(processed) : null
      })
    }
  } finally {
    processingFiles.value = false
  }
}

function removePending(idx: number) {
  const p = noteFiles.value[idx]
  if (p?.preview) URL.revokeObjectURL(p.preview)
  noteFiles.value.splice(idx, 1)
}

async function onPickPhoto(ev: Event) {
  if (!client.value) return
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  if (file.size > MAX_FILE_BYTES) {
    toast.add({ title: 'Photo exceeds 10 MB', color: 'error' })
    return
  }
  uploadingPhoto.value = true
  try {
    let processed = file
    try {
      processed = await compressProfilePhoto(file)
    } catch {
      toast.add({
        title: 'Couldn’t compress photo, uploading original',
        color: 'warning'
      })
      processed = file
    }
    if (processed.size > MAX_FILE_BYTES) {
      toast.add({ title: 'Photo exceeds 10 MB after processing', color: 'error' })
      return
    }
    const fd = new FormData()
    fd.append('file', processed)
    const updated = await api<Client>(`/clients/${client.value.client_id}/photo`, {
      method: 'POST',
      body: fd
    })
    client.value = { ...client.value, ...updated }
    await loadList()
    toast.add({ title: 'Photo updated', color: 'success' })
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Upload failed', color: 'error' })
  } finally {
    uploadingPhoto.value = false
  }
}

async function removeAttachment(item: TimelineItem, att: NoteAttachment) {
  if (!client.value || !item.noteId || att.id == null) return
  const key = `${item.noteId}-${att.id}`
  removingAttach.value = key
  try {
    await api(`/clients/${client.value.client_id}/notes/${item.noteId}/attachments/${att.id}`, {
      method: 'DELETE'
    })
    await loadChart(client.value.client_id)
    toast.add({ title: 'Attachment removed', color: 'success' })
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Remove failed', color: 'error' })
  } finally {
    removingAttach.value = null
  }
}

function kindColor(kind: TimelineItem['kind']) {
  const map = {
    note: 'border-l-[#0097A7]',
    bill: 'border-l-amber-500',
    receipt: 'border-l-emerald-500',
    rx: 'border-l-violet-500',
    appointment: 'border-l-sky-500',
    task: 'border-l-slate-400',
    lab: 'border-l-orange-500'
  }
  return map[kind]
}

function openLabCase(item: TimelineItem) {
  if (!item.labCaseId) return
  labDetailCaseId.value = item.labCaseId
  labDetailOpen.value = true
}

function onPlanComingSoon() {
  toast.add({ title: 'Treatment plans coming soon', color: 'warning' })
}

async function openRx() {
  rxOpen.value = true
  rxNotes.value = ''
  rxItems.value = []
  if (!medicineTemplates.value.length) {
    try {
      medicineTemplates.value = await api<typeof medicineTemplates.value>('/medicine-templates')
    } catch {
      medicineTemplates.value = []
    }
  }
}

function addRxRow() {
  rxItems.value.push({ medicine_id: null, medicine_name: '', quantity: null, dosage: '', days: null, instructions: '' })
}

function removeRxRow(idx: number) {
  rxItems.value.splice(idx, 1)
}

function addRxFromTemplate(tmpl: (typeof medicineTemplates.value)[number]) {
  rxItems.value.push({
    medicine_id: tmpl.medicine_id,
    medicine_name: tmpl.medicine_name,
    quantity: tmpl.default_quantity,
    dosage: tmpl.default_dosage || '',
    days: tmpl.default_days,
    instructions: tmpl.default_instructions || ''
  })
}

const rxTemplateCounts = computed(() => {
  const counts: Record<number, number> = {}
  for (const row of rxItems.value) {
    if (row.medicine_id != null) {
      counts[row.medicine_id] = (counts[row.medicine_id] ?? 0) + 1
    }
  }
  return counts
})

async function saveRx() {
  if (!client.value) return
  const items = rxItems.value
    .map(r => ({
      medicine_id: r.medicine_id,
      medicine_name: r.medicine_name.trim(),
      quantity: r.quantity,
      dosage: r.dosage.trim() || null,
      days: r.days,
      instructions: r.instructions.trim() || null
    }))
    .filter(r => r.medicine_name)
  if (!items.length) {
    toast.add({ title: 'Add at least one medicine', color: 'warning' })
    return
  }
  savingRx.value = true
  try {
    await api(`/clients/${client.value.client_id}/prescriptions`, {
      method: 'POST',
      body: { notes: rxNotes.value.trim() || null, items }
    })
    rxOpen.value = false
    toast.add({ title: 'Prescription saved', color: 'success' })
    await loadChart(client.value.client_id)
    scrollTimelineToBottom()
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
  } finally {
    savingRx.value = false
  }
}

function openBill() {
  billAmount.value = ''
  billDescription.value = ''
  resetBillDatetime()
  billOpen.value = true
  nextTick(() => {
    requestAnimationFrame(() => {
      const root = billAmountInput.value?.$el ?? (billAmountInput.value as unknown as HTMLElement | null)
      const input = root?.querySelector?.('input') ?? (root instanceof HTMLInputElement ? root : null)
      input?.focus()
    })
  })
}

async function saveBill() {
  if (!client.value) return
  const amount = Number(billAmount.value)
  if (!Number.isFinite(amount) || amount <= 0) {
    toast.add({ title: 'Enter a valid amount', color: 'warning' })
    return
  }
  savingBill.value = true
  try {
    await api(`/clients/${client.value.client_id}/bills`, {
      method: 'POST',
      body: {
        amount_due: amount,
        description: billDescription.value.trim() || null,
        ...(billDatetimeCustomized.value
          ? { issued_datetime: billDatetime.value || localDatetimeInputValue() }
          : {})
      }
    })
    billOpen.value = false
    toast.add({ title: 'Bill saved', color: 'success' })
    await loadChart(client.value.client_id)
    scrollTimelineToBottom()
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
  } finally {
    savingBill.value = false
  }
}

function resetNoteDatetime() {
  noteDatetime.value = localDatetimeInputValue()
  noteDatetimeCustomized.value = false
  noteShowDatetime.value = false
}

function applyNoteDatetime(value: string) {
  noteDatetime.value = value
  noteDatetimeCustomized.value = noteDatetimeDiffersFromNow(value)
}

function toggleNoteDatetime() {
  if (!noteShowDatetime.value) {
    if (!noteDatetimeCustomized.value) {
      noteDatetime.value = localDatetimeInputValue()
    }
    noteShowDatetime.value = true
    return
  }
  noteShowDatetime.value = false
}

function resetBillDatetime() {
  billDatetime.value = localDatetimeInputValue()
  billDatetimeCustomized.value = false
  billShowDatetime.value = false
}

function applyBillDatetime(value: string) {
  billDatetime.value = value
  billDatetimeCustomized.value = noteDatetimeDiffersFromNow(value)
}

function toggleBillDatetime() {
  if (!billShowDatetime.value) {
    if (!billDatetimeCustomized.value) {
      billDatetime.value = localDatetimeInputValue()
    }
    billShowDatetime.value = true
    return
  }
  billShowDatetime.value = false
}

const noteDatetimeActive = computed(() => noteShowDatetime.value || noteDatetimeCustomized.value)
const billDatetimeActive = computed(() => billShowDatetime.value || billDatetimeCustomized.value)
</script>

<template>
  <div class="relative h-full min-h-0 w-full overflow-hidden">
    <div class="grid h-full min-h-0 w-full grid-cols-[320px_minmax(0,1fr)] overflow-hidden">
      <!-- List -->
      <div class="flex h-full min-h-0 flex-col overflow-hidden border-r border-slate-200 bg-white">
        <div class="border-b border-slate-100 p-3">
          <input
            v-model="q"
            type="search"
            placeholder="Filter patients…"
            class="h-9 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm outline-none focus:border-[#0097A7]"
          >
        </div>
        <div class="min-h-0 flex-1 overflow-y-auto">
          <p v-if="loadingList" class="px-3 py-4 text-sm text-slate-400">Loading…</p>
          <button
            v-for="c in list"
            :key="c.client_id"
            type="button"
            class="flex w-full items-start gap-2 border-b border-slate-50 px-3 py-2.5 text-left hover:bg-slate-50"
            :class="patientId === c.client_id ? 'border-l-4 border-l-[#0097A7] bg-[#0097A7]/5' : 'border-l-4 border-l-transparent'"
            @click="openPatient(c.client_id)"
          >
          <div class="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center overflow-hidden rounded-full bg-[#e0f7fa] text-xs font-semibold text-[#0097A7]">
            <img
              v-if="c.profile_photo_url"
              :src="c.profile_photo_url"
              :alt="c.name"
              class="h-full w-full object-cover"
            >
            <span v-else>{{ c.name.charAt(0) }}</span>
          </div>
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <p class="truncate text-sm font-medium text-[#1C2B35]">{{ c.name }}</p>
                <span v-if="c.check_in_status" class="rounded bg-emerald-100 px-1.5 text-[10px] font-semibold text-emerald-700">IN</span>
              </div>
              <p class="truncate text-xs text-slate-500">
                {{ c.number || '—' }}
                <span v-if="c.place"> · {{ c.place }}</span>
                <span v-if="c.status"> · {{ c.status }}</span>
              </p>
            </div>
          </button>
        </div>
      </div>

      <!-- Chart -->
      <div class="flex h-full min-h-0 min-w-0 flex-col overflow-hidden bg-[#F0F4F8]">
        <div v-if="!patientId" class="flex flex-1 items-center justify-center text-sm text-slate-500">
          Select a patient to open the timeline
        </div>
        <template v-else-if="client">
          <div class="flex shrink-0 flex-wrap items-start justify-between gap-3 border-b border-slate-200 bg-white px-5 py-4">
            <div class="flex items-center gap-3">
              <button
                type="button"
                class="relative flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-full bg-[#e0f7fa] text-lg font-semibold text-[#0097A7] ring-offset-2 hover:ring-2 hover:ring-[#0097A7]/40"
                title="Change photo"
                :disabled="uploadingPhoto"
                @click="photoInput?.click()"
              >
                <img
                  v-if="client.profile_photo_url"
                  :src="client.profile_photo_url"
                  :alt="client.name"
                  class="h-full w-full object-cover"
                >
                <span v-else>{{ client.name.charAt(0) }}</span>
                <span class="absolute inset-x-0 bottom-0 bg-black/45 py-0.5 text-[9px] font-medium text-white">
                  {{ uploadingPhoto ? '…' : 'Edit' }}
                </span>
              </button>
              <input ref="photoInput" type="file" accept="image/*" class="hidden" @change="onPickPhoto">
              <div>
                <div class="flex items-center gap-2">
                  <h2 class="text-xl font-semibold text-[#1C2B35]">{{ client.name }}</h2>
                  <button type="button" class="text-xs text-slate-400 hover:text-slate-600" @click="clearPatient">Close</button>
                </div>
                <p class="mt-1 text-sm text-slate-500">
                  {{ client.number || 'No phone' }}
                  <span v-if="client.place"> · {{ client.place }}</span>
                  <span v-if="client.age"> · {{ client.age }}y</span>
                  · {{ client.status }}
                </p>
              </div>
            </div>
            <div class="flex flex-wrap gap-2">
              <button
                type="button"
                class="rounded-lg px-3 py-2 text-sm font-medium text-white"
                :class="client.check_in_status ? 'bg-red-500 hover:bg-red-600' : 'bg-emerald-600 hover:bg-emerald-700'"
                :disabled="toggling"
                @click="toggleCheckin"
              >
                {{ client.check_in_status ? 'Check out' : 'Check in' }}
              </button>
              <button
                type="button"
                class="rounded-lg border border-[#0097A7] px-3 py-2 text-sm font-medium text-[#0097A7] hover:bg-[#0097A7]/5"
                @click="bookOpen = true"
              >
                Book
              </button>
            </div>
          </div>

          <div ref="timelineEl" class="min-h-0 flex-1 overflow-y-auto px-5 py-4">
            <p v-if="loadingChart" class="text-sm text-slate-400">Loading timeline…</p>
            <ul v-else class="space-y-3">
              <li
                v-for="item in timeline"
                :key="item.id"
              >
                <!-- Note bubble -->
                <div
                  v-if="item.kind === 'note'"
                  class="ml-auto max-w-[min(100%,28rem)] rounded-2xl rounded-br-md bg-[#0097A7] px-4 py-3 text-white shadow-sm"
                >
                  <p v-if="item.body" class="whitespace-pre-wrap text-sm leading-relaxed">{{ item.body }}</p>
                  <div v-if="item.attachments?.length" class="mt-2 flex flex-wrap gap-2">
                    <div
                      v-for="(att, idx) in item.attachments"
                      :key="att.id ?? `${item.id}-a-${idx}`"
                      class="group relative"
                    >
                      <button
                        v-if="att.url && isImageAtt(att)"
                        type="button"
                        class="block overflow-hidden rounded-lg border border-white/30"
                        @click="lightbox = att.url"
                      >
                        <img :src="att.url" alt="" class="h-20 w-20 object-cover">
                      </button>
                      <a
                        v-else-if="att.url"
                        :href="att.url"
                        target="_blank"
                        rel="noopener"
                        class="inline-block rounded bg-white/15 px-2 py-1 text-[11px] text-white underline"
                      >
                        {{ fileLabel(att.key) }}
                      </a>
                      <button
                        v-if="att.id != null"
                        type="button"
                        class="absolute -right-1 -top-1 hidden h-5 w-5 items-center justify-center rounded-full bg-black/70 text-[10px] text-white group-hover:flex"
                        :disabled="removingAttach === `${item.noteId}-${att.id}`"
                        title="Remove"
                        @click.stop="removeAttachment(item, att)"
                      >
                        ×
                      </button>
                    </div>
                  </div>
                  <p class="mt-2 text-right text-[11px] text-white/75">
                    <span v-if="item.author">{{ item.author }} · </span>{{ formatWhen(item.at) }}
                  </p>
                </div>

                <!-- Compact other events -->
                <div
                  v-else
                  class="rounded-lg border border-slate-200 border-l-4 bg-white px-3 py-2"
                  :class="[kindColor(item.kind), item.kind === 'lab' ? 'cursor-pointer hover:bg-orange-50/40' : '']"
                  @click="item.kind === 'lab' ? openLabCase(item) : undefined"
                >
                  <div class="flex items-center justify-between gap-2">
                    <p class="text-sm font-medium text-[#1C2B35]">{{ item.title }}</p>
                    <p class="shrink-0 text-[11px] text-slate-400">{{ formatWhen(item.at) }}</p>
                  </div>
                  <p v-if="item.body" class="mt-0.5 truncate text-xs text-slate-500">{{ item.body }}</p>
                </div>
              </li>
              <li v-if="!timeline.length" class="rounded-xl border border-dashed border-slate-300 px-4 py-10 text-center text-sm text-slate-500">
                No timeline items yet.
              </li>
            </ul>
          </div>

          <div class="shrink-0 border-t border-slate-200 bg-white px-4 py-3">
            <form class="space-y-2" @submit.prevent="addNote">
              <input
                v-if="noteShowDatetime"
                v-model="noteDatetime"
                type="datetime-local"
                class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-[#0097A7]"
                @change="applyNoteDatetime(noteDatetime)"
              >
              <div
                v-else-if="noteDatetimeCustomized"
                class="flex items-center gap-2 rounded-lg bg-sky-50 px-2.5 py-1.5 text-xs text-sky-800"
              >
                <UIcon name="i-lucide-clock" class="h-3.5 w-3.5 shrink-0" />
                <span class="min-w-0 flex-1 truncate">{{ formatNoteDatetimePreview(noteDatetime) }}</span>
                <button
                  type="button"
                  class="shrink-0 text-sky-700 hover:text-sky-900"
                  title="Reset to now"
                  @click="resetNoteDatetime"
                >
                  <UIcon name="i-lucide-x" class="h-3.5 w-3.5" />
                </button>
              </div>
              <div class="flex gap-2">
                <input
                  v-model="noteBody"
                  placeholder="Add a note to the timeline…"
                  class="h-10 flex-1 rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm outline-none focus:border-[#0097A7] focus:bg-white"
                >
                <button
                  type="button"
                  class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border transition"
                  :class="noteDatetimeActive
                    ? 'border-[#0097A7] bg-[#0097A7] text-white hover:bg-[#00838f]'
                    : 'border-slate-200 text-slate-500 hover:bg-slate-50'"
                  title="Set date & time"
                  @click="toggleNoteDatetime"
                >
                  <UIcon name="i-lucide-clock" class="h-4 w-4" />
                </button>
                <button
                  type="button"
                  class="flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50 disabled:opacity-50"
                  title="Attach images or PDF"
                  :disabled="processingFiles || noteFiles.length >= MAX_NOTE_FILES"
                  @click="fileInput?.click()"
                >
                  <UIcon name="i-lucide-paperclip" class="h-4 w-4" />
                </button>
                <input
                  ref="fileInput"
                  type="file"
                  multiple
                  accept="image/*,.pdf,application/pdf"
                  class="hidden"
                  @change="onPickFiles"
                >
                <button
                  type="submit"
                  class="rounded-lg bg-[#0097A7] px-4 text-sm font-medium text-white hover:bg-[#00838f] disabled:opacity-50"
                  :disabled="savingNote || processingFiles || (!noteBody.trim() && !noteFiles.length)"
                >
                  Save
                </button>
              </div>
              <div v-if="noteFiles.length" class="space-y-1.5">
                <div class="flex flex-wrap gap-2">
                  <div
                    v-for="(p, idx) in noteFiles"
                    :key="`${p.file.name}-${idx}`"
                    class="relative overflow-hidden rounded-lg border border-slate-200 bg-slate-50"
                  >
                    <img v-if="p.preview" :src="p.preview" alt="" class="h-14 w-14 object-cover">
                    <div v-else class="flex h-14 w-24 items-center px-2 text-[10px] text-slate-600">{{ p.file.name }}</div>
                    <button
                      type="button"
                      class="absolute right-0.5 top-0.5 rounded bg-black/60 px-1 text-[10px] text-white"
                      @click="removePending(idx)"
                    >
                      ×
                    </button>
                  </div>
                </div>
                <label
                  v-if="hasImagePending()"
                  class="flex cursor-pointer items-center gap-2 text-[11px] text-slate-600"
                >
                  <input
                    v-model="saveOriginalQuality"
                    type="checkbox"
                    class="rounded border-slate-300"
                  >
                  Save original quality (skip compression)
                </label>
              </div>
              <p v-if="processingFiles" class="text-[11px] text-slate-400">Compressing images…</p>
            </form>

            <div class="mt-2 grid grid-cols-4 gap-2">
              <button
                type="button"
                class="flex flex-col items-center justify-center gap-0.5 rounded-xl bg-[#0097A7] py-2 text-white hover:bg-[#00838f]"
                title="Add prescription"
                @click="openRx"
              >
                <UIcon name="i-lucide-pill" class="h-5 w-5" />
                <span class="text-[10px] font-semibold">Rx</span>
              </button>
              <button
                type="button"
                class="flex flex-col items-center justify-center gap-0.5 rounded-xl border border-[#0097A7] bg-[#e0f7fa] py-2 text-[#00838f] hover:bg-[#b2ebf2]"
                title="Add bill"
                @click="openBill"
              >
                <UIcon name="i-lucide-banknote" class="h-5 w-5" />
                <span class="text-[10px] font-semibold">Bill</span>
              </button>
              <button
                type="button"
                class="flex flex-col items-center justify-center gap-0.5 rounded-xl border border-[#0097A7] bg-[#e0f7fa] py-2 text-[#00838f] hover:bg-[#b2ebf2]"
                title="Treatment plan"
                @click="onPlanComingSoon"
              >
                <UIcon name="i-lucide-stethoscope" class="h-5 w-5" />
                <span class="text-[10px] font-semibold">Plan</span>
              </button>
              <button
                type="button"
                class="flex flex-col items-center justify-center gap-0.5 rounded-xl border border-[#0097A7] bg-[#e0f7fa] py-2 text-[#00838f] hover:bg-[#b2ebf2]"
                title="Lab case"
                @click="labCreateOpen = true"
              >
                <UIcon name="i-lucide-flask-conical" class="h-5 w-5" />
                <span class="text-[10px] font-semibold">Lab</span>
              </button>
            </div>
          </div>
        </template>
        <div v-else-if="loadingChart" class="flex flex-1 items-center justify-center text-sm text-slate-400">Loading…</div>
      </div>
    </div>

    <DeskBookModal
      v-model:open="bookOpen"
      :client-id="client?.client_id"
      :client-name="client?.name"
      @booked="client && loadChart(client.client_id)"
    />
    <DeskLabCreateModal
      v-model:open="labCreateOpen"
      :client-id="client?.client_id"
      :client-name="client?.name"
      @created="() => { client && loadChart(client.client_id).then(() => scrollTimelineToBottom()); refreshBadges() }"
    />
    <DeskLabCaseModal
      v-model:open="labDetailOpen"
      :case-id="labDetailCaseId"
      @changed="() => { client && loadChart(client.client_id); refreshBadges() }"
      @book="(p) => { bookOpen = true }"
    />

    <UModal v-model:open="rxOpen" title="New prescription">
      <template #body>
        <form class="space-y-3" @submit.prevent="saveRx">
          <div class="flex items-center justify-between gap-2">
            <p class="text-sm font-semibold text-slate-800">Medicines</p>
            <span
              v-if="rxItems.length"
              class="rounded-full bg-emerald-100 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-800"
            >
              {{ rxItems.length }} added
            </span>
          </div>

          <div v-if="medicineTemplates.length" class="grid grid-cols-2 gap-2 sm:grid-cols-3">
            <button
              v-for="t in medicineTemplates"
              :key="t.medicine_id"
              type="button"
              class="relative truncate rounded-xl px-3 py-2.5 text-xs font-medium text-white transition active:scale-95"
              :class="(rxTemplateCounts[t.medicine_id] ?? 0) > 0
                ? 'bg-[#00838f] ring-1 ring-[#4dd0e1]/50 hover:bg-[#006064]'
                : 'bg-[#0097A7] hover:bg-[#00838f]'"
              :title="`Add ${t.medicine_name}`"
              @click="addRxFromTemplate(t)"
            >
              <span class="block truncate">
                {{ t.medicine_name }}<template v-if="t.default_quantity != null"> ({{ t.default_quantity }})</template>
              </span>
              <span
                v-if="(rxTemplateCounts[t.medicine_id] ?? 0) > 0"
                class="absolute -right-1.5 -top-1.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-emerald-500 px-1 text-[10px] font-bold text-white shadow-sm ring-2 ring-white"
              >
                {{ rxTemplateCounts[t.medicine_id] }}
              </span>
            </button>
          </div>
          <p v-else class="text-sm text-slate-500">No medicine templates found.</p>

          <p
            v-if="!rxItems.length"
            class="rounded-xl border border-dashed border-slate-200 px-3 py-6 text-center text-sm text-slate-400"
          >
            Tap a medicine above or add a custom row below.
          </p>

          <div
            v-for="(row, idx) in rxItems"
            :key="idx"
            class="space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-3"
          >
            <div class="flex items-center justify-between gap-2">
              <p class="text-xs font-medium text-slate-500">Medicine {{ idx + 1 }}</p>
              <button
                type="button"
                class="text-xs text-red-500 hover:underline"
                @click="removeRxRow(idx)"
              >
                Remove
              </button>
            </div>
            <UFormField label="Name" required>
              <UInput v-model="row.medicine_name" class="w-full" />
            </UFormField>
            <div class="grid grid-cols-3 gap-2">
              <UFormField label="Qty">
                <UInput v-model.number="row.quantity" type="number" min="0" class="w-full" />
              </UFormField>
              <UFormField label="Dosage">
                <UInput v-model="row.dosage" class="w-full" placeholder="1-0-1" />
              </UFormField>
              <UFormField label="Days">
                <UInput v-model.number="row.days" type="number" min="0" class="w-full" />
              </UFormField>
            </div>
            <UFormField label="Instructions">
              <UInput v-model="row.instructions" class="w-full" />
            </UFormField>
          </div>
          <UButton color="neutral" variant="outline" size="sm" type="button" @click="addRxRow">
            Add medicine
          </UButton>
          <UFormField label="Notes">
            <UTextarea v-model="rxNotes" class="w-full" :rows="2" />
          </UFormField>
          <div class="flex justify-end gap-2">
            <UButton color="neutral" variant="ghost" type="button" @click="rxOpen = false">Cancel</UButton>
            <UButton type="submit" class="bg-[#0097A7]" :loading="savingRx">Save Rx</UButton>
          </div>
        </form>
      </template>
    </UModal>

    <UModal v-model:open="billOpen" title="New bill">
      <template #body>
        <form class="space-y-3" @submit.prevent="saveBill">
          <UFormField label="Amount (₹)" required>
            <UInput ref="billAmountInput" v-model="billAmount" type="number" min="0" step="0.01" class="w-full" autofocus />
          </UFormField>
          <UFormField label="Description">
            <UTextarea v-model="billDescription" class="w-full" :rows="2" />
          </UFormField>
          <div>
            <div class="mb-2 flex items-center gap-2">
              <button
                type="button"
                class="flex h-10 w-10 items-center justify-center rounded-xl border-2 transition"
                :class="billDatetimeActive
                  ? 'border-[#0097A7] bg-[#0097A7] text-white'
                  : 'border-transparent bg-slate-100 text-[#00838f]'"
                title="Issued date & time"
                @click="toggleBillDatetime"
              >
                <UIcon name="i-lucide-clock" class="h-5 w-5" />
              </button>
              <span class="text-sm text-slate-600">Issued at</span>
              <span v-if="billDatetimeCustomized && !billShowDatetime" class="text-xs text-slate-500">
                {{ formatNoteDatetimePreview(billDatetime) }}
              </span>
              <button
                v-if="billDatetimeCustomized"
                type="button"
                class="text-xs text-slate-500 hover:text-slate-700"
                @click="resetBillDatetime"
              >
                Reset
              </button>
            </div>
            <input
              v-if="billShowDatetime"
              v-model="billDatetime"
              type="datetime-local"
              class="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-[#0097A7]"
              @change="applyBillDatetime(billDatetime)"
            >
          </div>
          <div class="flex justify-end gap-2">
            <UButton color="neutral" variant="ghost" type="button" @click="billOpen = false">Cancel</UButton>
            <UButton type="submit" class="bg-[#0097A7]" :loading="savingBill">Save bill</UButton>
          </div>
        </form>
      </template>
    </UModal>

    <Teleport to="body">
      <div
        v-if="lightbox"
        class="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 p-4"
        @click="lightbox = null"
      >
        <img :src="lightbox" alt="" class="max-h-full max-w-full rounded-lg object-contain" @click.stop>
      </div>
    </Teleport>
  </div>
</template>
