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
  planId?: number
  prescriptionId?: number
  appointmentId?: number
  appointmentDate?: string
  appointmentStatus?: string
  cardId?: number
  uniqueCode?: string
  warrantyPeriod?: number | null
  billId?: number
  billStatus?: string
  billAmountDue?: number
  billTotalPaid?: number
  billLinkedReceipts?: number
  receiptId?: number
  kind: 'note' | 'bill' | 'receipt' | 'rx' | 'appointment' | 'task' | 'lab' | 'plan' | 'warranty'
  title: string
  body?: string
  at: string
  author?: string | null
  attachments?: NoteAttachment[]
  planLocked?: boolean
  planCost?: number | null
  /** Appointment calendar day relative label (Today / After 30 days / 45 days ago). */
  apptRelative?: string
}

type Client = ClientRow & {
  age: number | null
  gender: string | null
  client_personal_note: string | null
  checked_in_at: string | null
}

type PendingFile = { file: File, preview: string | null }

const props = withDefaults(defineProps<{
  mobileChart?: boolean
  fixedPatientId?: number | null
}>(), {
  mobileChart: false,
  fixedPatientId: null
})

const lightbox = ref<string | null>(null)
const noteFiles = ref<PendingFile[]>([])
const fileInput = ref<HTMLInputElement | null>(null)
const photoInput = ref<HTMLInputElement | null>(null)
const uploadingPhoto = ref(false)
const removingAttach = ref<string | null>(null)
const saveOriginalQuality = ref(false)
const processingFiles = ref(false)
const expandedNoteId = ref<number | null>(null)
const expandedRxId = ref<number | null>(null)
const printingRxId = ref<number | null>(null)
const sendingRxWaId = ref<number | null>(null)
const noteEditOpen = ref(false)
const noteEditTarget = ref<TimelineItem | null>(null)
const deletingNoteId = ref<number | null>(null)

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

const { api, apiBlob } = useApi()
const deskUrl = useDeskUrl()
const patientId = computed(() => props.fixedPatientId ?? deskUrl.patientId.value)

function openPatient(id: number) {
  if (props.mobileChart) {
    void navigateTo(`/clients/${id}`)
    return
  }
  void deskUrl.openPatient(id)
}

function clearPatient() {
  if (props.mobileChart) {
    void navigateTo('/dashboard')
    return
  }
  void deskUrl.clearPatient()
}

function onMobileBack() {
  if (mobileView.value === 'profile') {
    mobileView.value = 'timeline'
    nextTick(() => scrollTimelineToBottom())
    return
  }
  clearPatient()
}

function openMobileProfile() {
  mobileView.value = 'profile'
}

const telHref = computed(() => {
  const digits = (client.value?.number || '').replace(/\D/g, '')
  return digits ? `tel:${digits}` : null
})

const waHref = computed(() => {
  const digits = (client.value?.number || '').replace(/\D/g, '')
  if (!digits) return null
  const withCountry = digits.length === 10 ? `91${digits}` : digits
  return `https://wa.me/${withCountry}`
})

const profileBalance = computed(() =>
  Math.max(0, profileStats.value.totalBilling - profileStats.value.paid)
)

function formatInr(n: number) {
  return `₹${n.toLocaleString('en-IN')}`
}

const toast = useToast()
const refreshBadges = inject<() => void>('deskRefreshBadges', () => {})
const mobileRefreshBadges = inject<() => void>('mobileRefreshBadges', () => {})
function bumpBadges() {
  refreshBadges()
  mobileRefreshBadges()
}

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
const editAppointmentId = ref<number | null>(null)
const detailOpen = ref(false)
const detailAppointmentId = ref<number | null>(null)
const waEnabled = ref(false)
/** Mobile chart: timeline (default) vs lite profile (name/photo tap). */
const mobileView = ref<'timeline' | 'profile'>('timeline')
const profileStats = ref({ visits: 0, activeRx: 0, totalBilling: 0, paid: 0 })
const labCreateOpen = ref(false)
const labDetailOpen = ref(false)
const labDetailCaseId = ref<number | null>(null)
const planCreateOpen = ref(false)
const planEditId = ref<number | null>(null)
const planViewOpen = ref(false)
const planViewId = ref<number | null>(null)
const planPricingOpen = ref(false)
const planPricingId = ref<number | null>(null)
const warrantyOpen = ref(false)
const warrantyEditId = ref<number | null>(null)
const expandedCardId = ref<number | null>(null)
const cardActionBusy = ref(false)
const sendingCardWaId = ref<number | null>(null)
const expandedBillId = ref<number | null>(null)
const expandedReceiptId = ref<number | null>(null)
const billActionBusy = ref(false)
const collectOpen = ref(false)
const collectBillId = ref<number | null>(null)
const collectAmountDue = ref(0)
const collectBillTotal = ref(0)
const collectTotalPaid = ref(0)
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

/** After expanding a foldable bubble, keep mid-list items in view; last item → scroll to end. */
function afterExpandScroll(isLast: boolean, selector?: string) {
  nextTick(() => {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (isLast) {
          const el = timelineEl.value
          if (el) el.scrollTop = el.scrollHeight
          return
        }
        if (!selector || !timelineEl.value) return
        const target = timelineEl.value.querySelector(selector) as HTMLElement | null
        target?.scrollIntoView({ block: 'nearest', behavior: 'smooth', inline: 'nearest' })
      })
    })
  })
}

function isLastTimelineItem(item: TimelineItem) {
  const list = timeline.value
  if (!list.length) return false
  return list[list.length - 1].id === item.id
}

const floatingDateLabel = ref('')
const showFloatingDate = ref(false)
let floatingDateTimer: ReturnType<typeof setTimeout> | null = null

const timelineRows = computed(() => {
  let last = ''
  return timeline.value.map((item) => {
    const dk = dateKey(item.at)
    const showSep = dk !== last
    last = dk
    return { item, showSep, dateKey: dk }
  })
})

function onTimelineScroll() {
  const area = timelineEl.value
  if (!area) return

  const nodes = area.querySelectorAll<HTMLElement>('[data-date]')
  const containerTop = area.getBoundingClientRect().top
  const viewportMiddle = containerTop + 120

  for (const node of nodes) {
    const rect = node.getBoundingClientRect()
    if (rect.top <= viewportMiddle && rect.bottom >= containerTop) {
      const d = node.getAttribute('data-date')
      if (d) floatingDateLabel.value = formatFloatingDate(d)
      break
    }
  }

  showFloatingDate.value = true
  if (floatingDateTimer) clearTimeout(floatingDateTimer)
  floatingDateTimer = setTimeout(() => {
    showFloatingDate.value = false
  }, 1000)
}

onUnmounted(() => {
  if (floatingDateTimer) clearTimeout(floatingDateTimer)
})

/** Clock time only — day comes from separators / sticky date pill. */
function formatWhen(iso: string) {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleTimeString('en-IN', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true
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
    const [c, notes, bills, receipts, rxs, appts, tasks, labs, plans, cards] = await Promise.all([
      api<Client>(`/clients/${id}`),
      api<{ note_id: number, body: string, created_at: string, author_name: string | null, attachments?: NoteAttachment[] }[]>(`/clients/${id}/notes`),
      api<{ bill_id: number, amount_due: number, status: string, description: string | null, issued_at: string, total_paid?: number, linked_receipt_count?: number }[]>(`/clients/${id}/bills`),
      api<{ receipt_id: number, amount: number, payment_mode: string, description: string | null, received_at: string, bill_id?: number | null }[]>(`/clients/${id}/receipts`),
      api<{ prescription_id: number, prescription_date: string, notes: string | null, created_at?: string, items: { medicine_name: string }[] }[]>(`/clients/${id}/prescriptions`),
      api<{ items: { appointment_id: number, appointment_date: string, appointment_time: string, status: string, doctor_name: string | null, service_name: string | null }[] }>('/appointments', { query: { client_id: id, limit: 50 } }),
      api<{ items: { task_id: number, task_description: string, status: string, due_date: string | null, created_at: string }[] }>('/tasks', { query: { client_id: id } }),
      api<{ cases: { case_id: number, case_ref: string, case_type: string | null, lab_name: string, stage: string, status: string, created_at: string, expected_return_date: string | null }[] }>(`/clients/${id}/lab-cases`),
      api<{ plan_id: number, title: string, summary: string | null, total_cost: number | null, locked_at: string | null, created_at: string, photos: { url: string | null }[] }[]>(`/clients/${id}/treatment-plans`),
      api<{ card_id: number, type_name: string, unique_code: string, warranty_period: number, date_of_purchase: string, product_name: string, number_of_units: number, created_at?: string | null }[]>(`/clients/${id}/warranty-cards`)
    ])
    client.value = c
    const totalBilling = bills.reduce((sum, b) => sum + Number(b.amount_due || 0), 0)
    const paid = receipts.reduce((sum, r) => sum + Number(r.amount || 0), 0)
    profileStats.value = {
      visits: appts.items.length,
      activeRx: rxs.length,
      totalBilling,
      paid
    }
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
      const status = normalizeBillStatus(b.status)
      const paid = Number(b.total_paid || 0)
      const due = Number(b.amount_due)
      const balance = Math.max(0, due - paid)
      const bodyParts = [
        b.description || null,
        `Paid ₹${paid.toLocaleString('en-IN')} · Due ₹${balance.toLocaleString('en-IN')}`
      ].filter(Boolean)
      items.push({
        id: `bill-${b.bill_id}`,
        billId: b.bill_id,
        billStatus: status,
        billAmountDue: due,
        billTotalPaid: paid,
        billLinkedReceipts: Number(b.linked_receipt_count ?? 0),
        kind: 'bill',
        title: `Bill · ₹${due.toLocaleString('en-IN')} · ${formatBillStatus(status)}`,
        body: bodyParts.join(' · ') || undefined,
        at: b.issued_at
      })
    }
    for (const r of receipts) {
      items.push({
        id: `rcpt-${r.receipt_id}`,
        receiptId: r.receipt_id,
        kind: 'receipt',
        title: `Receipt · ₹${Number(r.amount).toLocaleString('en-IN')} · ${r.payment_mode}`,
        body: r.description || undefined,
        at: r.received_at
      })
    }
    for (const rx of rxs) {
      items.push({
        id: `rx-${rx.prescription_id}`,
        prescriptionId: rx.prescription_id,
        kind: 'rx',
        title: `Rx · ${rx.items.map(i => i.medicine_name).join(', ') || 'Prescription'}`,
        body: rx.notes || undefined,
        at: rx.created_at || `${rx.prescription_date}T12:00:00`
      })
    }
    for (const a of appts.items) {
      items.push({
        id: `appt-${a.appointment_id}`,
        appointmentId: a.appointment_id,
        appointmentDate: a.appointment_date,
        appointmentStatus: a.status,
        kind: 'appointment',
        title: `Appt · ${formatAmPm(a.appointment_time)} · ${a.status}`,
        body: [a.doctor_name, a.service_name].filter(Boolean).join(' · ') || undefined,
        at: `${a.appointment_date}T${a.appointment_time}:00`,
        apptRelative: apptRelativeLabel(a.appointment_date)
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
    for (const p of plans) {
      const cost = p.total_cost != null
        ? `₹${Number(p.total_cost).toLocaleString('en-IN')}`
        : 'Not priced'
      items.push({
        id: `plan-${p.plan_id}`,
        planId: p.plan_id,
        kind: 'plan',
        title: `Plan · ${p.title || 'Treatment plan'}`,
        body: [p.summary, cost, p.locked_at ? 'Locked' : null].filter(Boolean).join(' · ') || undefined,
        at: p.created_at,
        planLocked: !!p.locked_at,
        planCost: p.total_cost,
        attachments: (p.photos || [])
          .filter(ph => ph.url)
          .map((ph, i) => ({ id: i, key: ph.url || '', url: ph.url }))
      })
    }
    for (const card of cards) {
      items.push({
        id: `card-${card.card_id}`,
        cardId: card.card_id,
        uniqueCode: card.unique_code,
        warrantyPeriod: card.warranty_period,
        kind: 'warranty',
        title: `Warranty · ${card.type_name || 'Card'}`,
        body: [card.unique_code, card.product_name, card.warranty_period ? `${card.warranty_period} days` : null]
          .filter(Boolean)
          .join(' · ') || undefined,
        // Real create time when present; imported rows fall back to purchase date at noon.
        at: card.created_at || `${card.date_of_purchase}T12:00:00`
      })
    }
    timeline.value = items.sort((a, b) => Date.parse(a.at) - Date.parse(b.at))
    scrollTimelineToBottom()
  } finally {
    loadingChart.value = false
  }
}

watch(q, () => { if (!props.mobileChart) loadList() })
watch(patientId, (id) => {
  mobileView.value = 'timeline'
  if (id) loadChart(id)
  else {
    client.value = null
    timeline.value = []
    profileStats.value = { visits: 0, activeRx: 0, totalBilling: 0, paid: 0 }
  }
}, { immediate: true })

onMounted(() => {
  if (!props.mobileChart) void loadList()
  void refreshWaEnabled()
})

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
    if (!props.mobileChart) await loadList()
    bumpBadges()
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
  if (!window.confirm('Delete this attachment? This cannot be undone.')) return
  const key = `${item.noteId}-${att.id}`
  removingAttach.value = key
  try {
    await api(`/clients/${client.value.client_id}/notes/${item.noteId}/attachments/${att.id}`, {
      method: 'DELETE'
    })
    await loadChart(client.value.client_id)
    toast.add({ title: 'Attachment deleted', color: 'success' })
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Delete failed', color: 'error' })
  } finally {
    removingAttach.value = null
  }
}

function toggleNoteExpand(item: TimelineItem) {
  if (!item.noteId) return
  const next = expandedNoteId.value === item.noteId ? null : item.noteId
  expandedNoteId.value = next
  if (next) afterExpandScroll(isLastTimelineItem(item), `[data-note-id="${next}"] [data-note-actions]`)
}

function openNoteEdit(item: TimelineItem) {
  if (!item.noteId) return
  expandedNoteId.value = null
  noteEditTarget.value = item
  noteEditOpen.value = true
}

async function deleteNote(item: TimelineItem) {
  if (!client.value || !item.noteId || deletingNoteId.value) return
  if (!window.confirm('Delete this note? This cannot be undone.')) return
  deletingNoteId.value = item.noteId
  try {
    await api(`/clients/${client.value.client_id}/notes/${item.noteId}`, { method: 'DELETE' })
    expandedNoteId.value = null
    await loadChart(client.value.client_id)
    toast.add({ title: 'Note deleted', color: 'success' })
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Delete failed', color: 'error' })
  } finally {
    deletingNoteId.value = null
  }
}

function kindColor(kind: TimelineItem['kind']) {
  const map: Record<TimelineItem['kind'], string> = {
    note: 'border-l-[#0097A7]',
    bill: 'border-l-orange-500',
    receipt: 'border-l-emerald-500',
    rx: 'border-l-violet-500',
    appointment: 'border-l-sky-500',
    task: 'border-l-slate-400',
    lab: 'border-l-orange-500',
    plan: 'border-l-teal-600',
    warranty: 'border-l-indigo-500'
  }
  return map[kind]
}

/** Unsatisfied (pending/partial) → orange; paid → green; cancelled → muted. */
function billBorderColor(status: string | null | undefined) {
  const s = normalizeBillStatus(status)
  if (s === 'paid') return 'border-l-emerald-500'
  if (s === 'cancelled') return 'border-l-slate-400'
  return 'border-l-orange-500'
}

function isMissedAppointment(item: TimelineItem) {
  const s = (item.appointmentStatus || '').toLowerCase()
  return s === 'cancelled' || s === 'no show'
}

function openApptDetail(item: TimelineItem) {
  if (!item.appointmentId) return
  detailAppointmentId.value = item.appointmentId
  detailOpen.value = true
}

function openBook() {
  editAppointmentId.value = null
  bookOpen.value = true
}

function onApptDetailEdit(id: number) {
  editAppointmentId.value = id
  bookOpen.value = true
}

function onApptDetailUpdated() {
  if (client.value) void loadChart(client.value.client_id)
}

async function refreshWaEnabled() {
  try {
    const wa = await api<{ enabled: boolean }>('/settings/whatsapp')
    waEnabled.value = Boolean(wa.enabled)
  } catch {
    waEnabled.value = false
  }
}

function openLabCase(item: TimelineItem) {
  if (!item.labCaseId) return
  labDetailCaseId.value = item.labCaseId
  labDetailOpen.value = true
}

function openPlanCreate() {
  planEditId.value = null
  planCreateOpen.value = true
}

function openWarrantyCreate() {
  warrantyEditId.value = null
  warrantyOpen.value = true
}

function openWarrantyEdit(cardId: number) {
  warrantyEditId.value = cardId
  warrantyOpen.value = true
}

function toggleCardExpand(item: TimelineItem) {
  if (!item.cardId) return
  const next = expandedCardId.value === item.cardId ? null : item.cardId
  expandedCardId.value = next
  if (next) afterExpandScroll(isLastTimelineItem(item), `[data-card-id="${next}"] [data-card-actions]`)
}

async function sendCardWhatsApp(cardId: number, code?: string) {
  if (!window.confirm(`Send warranty card ${code || `#${cardId}`} to the patient on WhatsApp? A PDF will be attached.`)) {
    return
  }
  sendingCardWaId.value = cardId
  try {
    await api(`/warranty-cards/${cardId}/send-whatsapp`, { method: 'POST' })
    toast.add({ title: 'Warranty card sent on WhatsApp', color: 'success' })
    if (client.value) await loadChart(client.value.client_id)
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'WhatsApp send failed', color: 'error' })
  } finally {
    sendingCardWaId.value = null
  }
}

async function deleteWarrantyCard(cardId: number, code?: string) {
  if (!window.confirm(`Delete warranty card ${code || `#${cardId}`}? This cannot be undone.`)) {
    return
  }
  cardActionBusy.value = true
  try {
    await api(`/warranty-cards/${cardId}`, { method: 'DELETE' })
    toast.add({ title: 'Warranty card deleted', color: 'success' })
    expandedCardId.value = null
    if (client.value) await loadChart(client.value.client_id)
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Delete failed', color: 'error' })
  } finally {
    cardActionBusy.value = false
  }
}

function normalizeBillStatus(status: string | null | undefined) {
  const s = (status || 'pending').toLowerCase()
  return s === 'open' ? 'pending' : s
}

function formatBillStatus(status: string | null | undefined) {
  const s = normalizeBillStatus(status)
  if (s === 'partial') return 'Partial'
  return s.charAt(0).toUpperCase() + s.slice(1)
}

function canCollectBill(status: string | null | undefined) {
  const s = normalizeBillStatus(status)
  return s === 'pending' || s === 'partial'
}

function billHasLinkedReceipts(item: TimelineItem) {
  return (item.billLinkedReceipts || 0) > 0
}

function collectAmountForBill(amountDue: number, totalPaid: number, status: string | null | undefined) {
  if (normalizeBillStatus(status) === 'partial') {
    return Math.max(0, amountDue - totalPaid)
  }
  return amountDue
}

function toggleBillExpand(item: TimelineItem) {
  if (!item.billId) return
  const next = expandedBillId.value === item.billId ? null : item.billId
  expandedBillId.value = next
  if (next) afterExpandScroll(isLastTimelineItem(item), `[data-bill-id="${next}"] [data-bill-actions]`)
}

function toggleReceiptExpand(item: TimelineItem) {
  if (!item.receiptId) return
  const next = expandedReceiptId.value === item.receiptId ? null : item.receiptId
  expandedReceiptId.value = next
  if (next) afterExpandScroll(isLastTimelineItem(item), `[data-receipt-id="${next}"] [data-receipt-actions]`)
}

function openCollect(item: TimelineItem) {
  if (!item.billId) return
  collectBillId.value = item.billId
  collectBillTotal.value = item.billAmountDue || 0
  collectTotalPaid.value = item.billTotalPaid || 0
  collectAmountDue.value = collectAmountForBill(
    item.billAmountDue || 0,
    item.billTotalPaid || 0,
    item.billStatus
  )
  collectOpen.value = true
}

async function cancelBill(item: TimelineItem) {
  if (!item.billId || billActionBusy.value) return
  if (billHasLinkedReceipts(item)) {
    const n = item.billLinkedReceipts || 0
    toast.add({
      title: n === 1
        ? 'Delete the linked receipt first, then cancel this bill'
        : `Delete ${n} linked receipts first, then cancel this bill`,
      color: 'warning'
    })
    return
  }
  if (!window.confirm(
    `Cancel bill #${item.billId} for ₹${item.billAmountDue}? This cannot be undone.`
  )) return
  billActionBusy.value = true
  try {
    await api(`/bills/${item.billId}/cancel`, { method: 'POST' })
    toast.add({ title: 'Bill cancelled', color: 'success' })
    expandedBillId.value = null
    if (client.value) await loadChart(client.value.client_id)
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Cancel failed', color: 'error' })
  } finally {
    billActionBusy.value = false
  }
}

async function deleteBill(item: TimelineItem) {
  if (!item.billId || billActionBusy.value) return
  if (!window.confirm(
    `Permanently delete bill #${item.billId}? This cannot be undone.`
  )) return
  billActionBusy.value = true
  try {
    await api(`/bills/${item.billId}`, { method: 'DELETE' })
    toast.add({ title: 'Bill deleted', color: 'success' })
    expandedBillId.value = null
    if (client.value) await loadChart(client.value.client_id)
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Delete failed', color: 'error' })
  } finally {
    billActionBusy.value = false
  }
}

async function deleteReceipt(item: TimelineItem) {
  if (!item.receiptId || billActionBusy.value) return
  if (!window.confirm('Delete this receipt? This cannot be undone.')) return
  billActionBusy.value = true
  try {
    await api(`/receipts/${item.receiptId}`, { method: 'DELETE' })
    toast.add({ title: 'Receipt deleted', color: 'success' })
    expandedReceiptId.value = null
    if (client.value) await loadChart(client.value.client_id)
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Delete failed', color: 'error' })
  } finally {
    billActionBusy.value = false
  }
}

function openPlanView(item: TimelineItem) {
  if (!item.planId) return
  planViewId.value = item.planId
  planViewOpen.value = true
}

function openPlanEdit(planId: number) {
  planEditId.value = planId
  planCreateOpen.value = true
}

function openPlanPricing(planId: number) {
  planPricingId.value = planId
  planPricingOpen.value = true
}

function onPlanTimelineClick(item: TimelineItem) {
  if (item.kind === 'lab') openLabCase(item)
  else if (item.kind === 'plan') openPlanView(item)
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

async function saveRx(printAfter = false) {
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
    const created = await api<{ prescription_id: number }>(`/clients/${client.value.client_id}/prescriptions`, {
      method: 'POST',
      body: { notes: rxNotes.value.trim() || null, items }
    })
    rxOpen.value = false
    toast.add({ title: 'Prescription saved', color: 'success' })
    await loadChart(client.value.client_id)
    scrollTimelineToBottom()
    if (printAfter && created.prescription_id) {
      await printPrescription(created.prescription_id)
    }
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
  } finally {
    savingRx.value = false
  }
}

async function printPrescription(prescriptionId: number) {
  if (!client.value || printingRxId.value) return
  printingRxId.value = prescriptionId
  try {
    const blob = await apiBlob(`/clients/${client.value.client_id}/prescriptions/${prescriptionId}/pdf`)
    const url = URL.createObjectURL(blob)
    const win = window.open(url, '_blank', 'noopener,noreferrer')
    if (!win) {
      // Popup blocked — force download
      const a = document.createElement('a')
      a.href = url
      a.download = `prescription-${prescriptionId}.pdf`
      a.rel = 'noopener'
      document.body.appendChild(a)
      a.click()
      a.remove()
    }
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Print failed', color: 'error' })
  } finally {
    printingRxId.value = null
  }
}

function toggleRxExpand(item: TimelineItem) {
  if (!item.prescriptionId) return
  const next = expandedRxId.value === item.prescriptionId ? null : item.prescriptionId
  expandedRxId.value = next
  if (next) afterExpandScroll(isLastTimelineItem(item), `[data-rx-id="${next}"] [data-rx-actions]`)
}

async function sendRxWhatsApp(prescriptionId: number) {
  if (!client.value || sendingRxWaId.value) return
  if (
    !window.confirm(
      'Send this prescription to the patient on WhatsApp? A letterhead PDF will be attached.'
    )
  ) {
    return
  }
  sendingRxWaId.value = prescriptionId
  try {
    await api(`/clients/${client.value.client_id}/prescriptions/${prescriptionId}/whatsapp`, {
      method: 'POST'
    })
    toast.add({ title: 'Prescription sent on WhatsApp', color: 'success' })
    expandedRxId.value = null
    await loadChart(client.value.client_id)
    scrollTimelineToBottom()
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'WhatsApp failed', color: 'error' })
  } finally {
    sendingRxWaId.value = null
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
    <div
      class="grid h-full min-h-0 w-full overflow-hidden"
      :class="mobileChart ? 'grid-cols-1' : 'grid-cols-[320px_minmax(0,1fr)]'"
    >
      <!-- List -->
      <div v-if="!mobileChart" class="flex h-full min-h-0 flex-col overflow-hidden border-r border-slate-200 bg-white">
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
          <!-- Mobile: Next-style chat header -->
          <template v-if="mobileChart">
            <header class="flex shrink-0 items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-2.5">
              <div class="flex min-w-0 flex-1 items-center gap-3">
                <button
                  type="button"
                  class="flex h-[34px] w-[34px] shrink-0 items-center justify-center rounded-full border border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100"
                  :aria-label="mobileView === 'profile' ? 'Back to timeline' : 'Back to patients'"
                  @click="onMobileBack"
                >
                  <UIcon name="i-lucide-arrow-left" class="h-4 w-4" />
                </button>
                <button
                  type="button"
                  class="relative flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-full bg-[#e0f7fa] text-sm font-semibold text-[#0097A7]"
                  :title="mobileView === 'profile' ? 'Change photo' : 'Open profile'"
                  :disabled="mobileView === 'profile' && uploadingPhoto"
                  @click="mobileView === 'profile' ? photoInput?.click() : openMobileProfile()"
                >
                  <img
                    v-if="client.profile_photo_url"
                    :src="client.profile_photo_url"
                    :alt="client.name"
                    class="h-full w-full object-cover"
                  >
                  <span v-else>{{ client.name.charAt(0) }}</span>
                </button>
                <input ref="photoInput" type="file" accept="image/*" class="hidden" @change="onPickPhoto">
                <button
                  type="button"
                  class="min-w-0 flex-1 text-left"
                  :title="mobileView === 'timeline' ? 'Open profile' : undefined"
                  @click="mobileView === 'timeline' && openMobileProfile()"
                >
                  <h1
                    class="truncate text-[15px] font-semibold"
                    :class="client.check_in_status ? 'text-[#00838f]' : 'text-[#1C2B35]'"
                  >
                    {{ mobileView === 'profile' ? 'Patient profile' : client.name }}
                  </h1>
                  <p class="truncate text-xs text-slate-500">
                    <template v-if="mobileView === 'profile'">{{ client.name }}</template>
                    <template v-else-if="client.status">{{ client.status }}</template>
                    <template v-else>Tap for profile</template>
                  </p>
                </button>
              </div>
              <NuxtLink
                to="/dashboard"
                class="flex h-[34px] w-[34px] shrink-0 items-center justify-center rounded-full border border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100"
                title="Home"
                aria-label="Home"
              >
                <UIcon name="i-lucide-home" class="h-4 w-4" />
              </NuxtLink>
            </header>
          </template>

          <!-- Desk chart header -->
          <div
            v-else
            class="flex shrink-0 flex-wrap items-start justify-between gap-3 border-b border-slate-200 bg-white px-5 py-4"
          >
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
                  <button type="button" class="text-xs text-slate-400 hover:text-slate-600" @click="clearPatient">
                    Close
                  </button>
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
                @click="openBook"
              >
                Book
              </button>
            </div>
          </div>

          <!-- Mobile lite profile (name/photo tap) -->
          <template v-if="mobileChart && mobileView === 'profile'">
            <div class="min-h-0 flex-1 overflow-y-auto overscroll-contain bg-[#F0F4F8]">
              <div class="border-b border-slate-200 bg-white px-4 pb-4 pt-5">
                <div class="mb-3.5 flex items-center gap-3.5">
                  <button
                    type="button"
                    class="relative flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-full bg-[#e0f7fa] text-xl font-semibold text-[#0097A7] ring-2 ring-[#e0f7fa]"
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
                  </button>
                  <div class="min-w-0 flex-1">
                    <h2 class="truncate text-lg font-semibold text-[#1C2B35]">{{ client.name }}</h2>
                    <p class="mt-0.5 text-[13px] text-slate-500">
                      <template v-if="client.age != null">{{ client.age }} y · </template>
                      <template v-if="client.gender">{{ client.gender }} · </template>
                      {{ client.place || '—' }}
                    </p>
                    <p class="mt-1 text-xs text-slate-400">
                      #{{ client.client_id }}
                      <span v-if="client.check_in_status" class="ml-2 font-semibold text-[#00838f]">Checked in</span>
                    </p>
                  </div>
                </div>

                <p class="text-sm text-slate-600">
                  {{ client.number || 'No phone' }}
                  <span v-if="client.status" class="text-slate-400"> · {{ client.status }}</span>
                </p>
                <p v-if="client.client_personal_note" class="mt-2 text-sm text-slate-500">
                  {{ client.client_personal_note }}
                </p>

                <div class="mt-3.5 grid grid-cols-3 gap-2">
                  <a
                    :href="telHref || undefined"
                    class="flex flex-col items-center gap-1 rounded-[10px] bg-[#e0f7fa] px-1.5 py-2.5 no-underline"
                    :class="!telHref ? 'pointer-events-none opacity-50' : ''"
                  >
                    <UIcon name="i-lucide-phone" class="h-5 w-5 text-[#00838f]" />
                    <span class="text-[11px] font-medium text-[#00838f]">Call</span>
                  </a>
                  <a
                    :href="waHref || undefined"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="flex flex-col items-center gap-1 rounded-[10px] bg-[#dcfce7] px-1.5 py-2.5 no-underline"
                    :class="!waHref ? 'pointer-events-none opacity-50' : ''"
                  >
                    <UIcon name="i-lucide-message-circle" class="h-5 w-5 text-[#15803d]" />
                    <span class="text-[11px] font-medium text-[#15803d]">WhatsApp</span>
                  </a>
                  <button
                    type="button"
                    class="flex flex-col items-center gap-1 rounded-[10px] bg-[#fef9ec] px-1.5 py-2.5"
                    @click="openBook"
                  >
                    <UIcon name="i-lucide-calendar" class="h-5 w-5 text-[#b8860b]" />
                    <span class="text-[11px] font-medium text-[#b8860b]">Book</span>
                  </button>
                </div>
              </div>

              <div class="mb-2.5 grid grid-cols-3 gap-px bg-slate-200">
                <div class="bg-white px-3 py-3 text-center">
                  <p class="m-0 text-xl font-semibold text-[#1C2B35]">{{ profileStats.visits }}</p>
                  <p class="mt-0.5 text-[11px] text-slate-400">Visits</p>
                </div>
                <div class="bg-white px-3 py-3 text-center">
                  <p class="m-0 text-xl font-semibold text-[#0097A7]">{{ profileStats.activeRx }}</p>
                  <p class="mt-0.5 text-[11px] text-slate-400">Rx</p>
                </div>
                <div class="bg-white px-3 py-3 text-center">
                  <p class="m-0 text-xl font-semibold text-[#C49A3C]">{{ formatInr(profileStats.totalBilling) }}</p>
                  <p class="mt-0.5 text-[11px] text-slate-400">Total billing</p>
                  <p
                    v-if="profileStats.totalBilling > 0 || profileStats.paid > 0"
                    class="mt-1 text-[11px] font-semibold"
                    :class="profileBalance > 0 ? 'text-orange-600' : 'text-green-600'"
                  >
                    Due {{ formatInr(profileBalance) }}
                  </p>
                </div>
              </div>

              <div class="mx-2.5 mb-2.5 rounded-xl border border-slate-200 bg-white px-4 py-3.5">
                <p class="m-0 text-xs font-semibold uppercase tracking-wider text-slate-400">Billing</p>
                <div class="mt-3 grid grid-cols-2 gap-3">
                  <div>
                    <p class="text-[11px] text-slate-400">Billed</p>
                    <p class="text-sm font-semibold text-[#1C2B35]">{{ formatInr(profileStats.totalBilling) }}</p>
                  </div>
                  <div>
                    <p class="text-[11px] text-slate-400">Paid</p>
                    <p class="text-sm font-semibold text-[#1C2B35]">{{ formatInr(profileStats.paid) }}</p>
                  </div>
                </div>
              </div>

              <div class="mx-2.5 mb-4 rounded-xl border border-slate-200 bg-white px-4 py-3.5">
                <p class="m-0 text-xs font-semibold uppercase tracking-wider text-slate-400">Warranty</p>
                <button
                  type="button"
                  class="mt-2 w-full rounded-xl bg-[#0097A7] px-3 py-2.5 text-sm font-semibold text-white active:bg-[#00838f]"
                  @click="openWarrantyCreate"
                >
                  Add warranty card
                </button>
              </div>
            </div>

            <div class="flex shrink-0 gap-2 border-t border-slate-200 bg-white px-3 py-2.5 pb-[max(0.625rem,env(safe-area-inset-bottom))]">
              <button
                type="button"
                class="flex-1 rounded-xl px-3 py-2.5 text-sm font-semibold text-white disabled:opacity-60"
                :class="client.check_in_status ? 'bg-red-500 active:bg-red-600' : 'bg-emerald-600 active:bg-emerald-700'"
                :disabled="toggling"
                @click="toggleCheckin"
              >
                {{ client.check_in_status ? 'Check out' : 'Check in' }}
              </button>
              <button
                type="button"
                class="flex-1 rounded-xl border border-[#0097A7] bg-[#e0f7fa] px-3 py-2.5 text-sm font-semibold text-[#00838f] active:bg-[#b2ebf2]"
                @click="openBook"
              >
                Book
              </button>
            </div>
          </template>

          <template v-else>
          <!-- flex-1 + overflow-y-auto (not nested h-full) so mobile notes/timeline can scroll -->
          <div class="relative flex min-h-0 flex-1 flex-col overflow-hidden">
            <div
              class="pointer-events-none absolute left-1/2 top-2 z-20 -translate-x-1/2 rounded-full bg-[#1C2B35]/90 px-3.5 py-1.5 text-xs font-semibold whitespace-nowrap text-white shadow-sm transition-opacity duration-200"
              :class="showFloatingDate && floatingDateLabel ? 'opacity-100' : 'opacity-0'"
              aria-hidden="true"
            >
              {{ floatingDateLabel }}
            </div>
            <div
              ref="timelineEl"
              class="min-h-0 flex-1 overflow-y-auto overscroll-y-contain px-4 py-4 sm:px-5 [-webkit-overflow-scrolling:touch]"
              @scroll="onTimelineScroll"
            >
            <div class="mx-auto w-full max-w-[30rem] pb-2">
              <p v-if="loadingChart" class="text-sm text-slate-400">Loading timeline…</p>
              <ul v-else class="space-y-3">
                <li
                  v-for="{ item, showSep, dateKey: dk } in timelineRows"
                  :key="item.id"
                  :data-date="dk"
                >
                  <div v-if="showSep" class="py-1 text-center">
                    <span class="inline-block rounded-lg border border-slate-200 bg-white px-3 py-1 text-[11px] font-semibold tracking-wide text-slate-500 shadow-sm">
                      {{ formatDateSeparator(item.at) }}
                    </span>
                  </div>
                  <!-- Note bubble -->
                  <div
                    v-if="item.kind === 'note'"
                    :data-note-id="item.noteId"
                    class="w-full overflow-hidden rounded-2xl bg-[#0097A7] text-white shadow-sm"
                  >
                    <div class="px-4 py-3">
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
                      <button
                        type="button"
                        class="mt-2 flex w-full items-center justify-end gap-1 text-right text-[11px] text-white/75 hover:text-white"
                        :aria-expanded="expandedNoteId === item.noteId"
                        @click="toggleNoteExpand(item)"
                      >
                        <span>
                          <span v-if="item.author">{{ item.author }} · </span>{{ formatWhen(item.at) }}
                        </span>
                        <UIcon
                          name="i-lucide-chevron-down"
                          class="h-3.5 w-3.5 transition"
                          :class="expandedNoteId === item.noteId ? 'rotate-180' : ''"
                        />
                      </button>
                    </div>
                    <div
                      v-if="expandedNoteId === item.noteId"
                      data-note-actions
                      class="grid grid-cols-2 gap-px border-t border-white/20 bg-slate-100"
                      @click.stop
                    >
                      <button
                        type="button"
                        class="flex items-center justify-center gap-1.5 bg-white px-2 py-2.5 text-xs font-semibold text-[#00838f] hover:bg-[#e0f7fa]"
                        @click="openNoteEdit(item)"
                      >
                        <UIcon name="i-lucide-pencil" class="h-3.5 w-3.5" />
                        Edit
                      </button>
                      <button
                        type="button"
                        class="flex items-center justify-center gap-1.5 bg-white px-2 py-2.5 text-xs font-semibold text-red-600 hover:bg-red-50 disabled:opacity-50"
                        :disabled="deletingNoteId === item.noteId"
                        @click="deleteNote(item)"
                      >
                        <UIcon name="i-lucide-trash-2" class="h-3.5 w-3.5" />
                        Delete
                      </button>
                    </div>
                  </div>

                  <!-- Appointment bubble → detail modal -->
                  <div
                    v-else-if="item.kind === 'appointment'"
                    :data-appt-id="item.appointmentId"
                    class="cursor-pointer overflow-hidden rounded-lg border border-slate-200 border-l-4 bg-white"
                    :class="[
                      kindColor(item.kind),
                      isMissedAppointment(item) ? 'border-l-red-400' : ''
                    ]"
                    @click="openApptDetail(item)"
                  >
                    <div class="px-3 py-2">
                      <div class="flex items-center justify-between gap-2">
                        <p class="text-sm font-medium text-[#1C2B35]">{{ item.title }}</p>
                        <p
                          v-if="item.apptRelative"
                          class="shrink-0 text-[11px] font-semibold"
                          :class="item.apptRelative.includes('ago') || item.apptRelative === 'Yesterday'
                            ? 'text-slate-400'
                            : 'text-[#0097A7]'"
                        >
                          {{ item.apptRelative }}
                        </p>
                      </div>
                      <p v-if="item.body" class="mt-0.5 truncate text-xs text-slate-500">{{ item.body }}</p>
                    </div>
                  </div>

                  <!-- Prescription bubble -->
                  <div
                    v-else-if="item.kind === 'rx'"
                    :data-rx-id="item.prescriptionId"
                    class="overflow-hidden rounded-lg border border-slate-200 border-l-4 bg-white"
                    :class="kindColor(item.kind)"
                  >
                    <button
                      type="button"
                      class="flex w-full cursor-pointer items-start justify-between gap-2 px-3 py-2 text-left hover:bg-slate-50"
                      @click="toggleRxExpand(item)"
                    >
                      <div class="min-w-0">
                        <p class="text-sm font-medium text-[#1C2B35]">{{ item.title }}</p>
                        <p v-if="item.body" class="mt-0.5 truncate text-xs text-slate-500">{{ item.body }}</p>
                      </div>
                      <div class="flex shrink-0 items-center gap-1">
                        <p class="text-[11px] text-slate-400">{{ formatWhen(item.at) }}</p>
                        <UIcon
                          name="i-lucide-chevron-down"
                          class="h-3.5 w-3.5 text-slate-400 transition"
                          :class="expandedRxId === item.prescriptionId ? 'rotate-180' : ''"
                        />
                      </div>
                    </button>
                    <div
                      v-if="expandedRxId === item.prescriptionId"
                      data-rx-actions
                      class="grid gap-px border-t border-slate-200 bg-slate-100"
                      :class="waEnabled ? 'grid-cols-2' : 'grid-cols-1'"
                      @click.stop
                    >
                      <button
                        type="button"
                        class="flex items-center justify-center gap-1.5 bg-white px-2 py-2.5 text-xs font-semibold text-[#00838f] hover:bg-[#e0f7fa] disabled:opacity-50"
                        :disabled="printingRxId === item.prescriptionId || sendingRxWaId === item.prescriptionId"
                        @click="item.prescriptionId && printPrescription(item.prescriptionId)"
                      >
                        <UIcon name="i-lucide-printer" class="h-3.5 w-3.5" />
                        {{ printingRxId === item.prescriptionId ? 'Printing…' : 'Print' }}
                      </button>
                      <button
                        v-if="waEnabled"
                        type="button"
                        class="flex items-center justify-center gap-1.5 bg-white px-2 py-2.5 text-xs font-semibold text-emerald-700 hover:bg-emerald-50 disabled:opacity-50"
                        :disabled="printingRxId === item.prescriptionId || sendingRxWaId === item.prescriptionId"
                        @click="item.prescriptionId && sendRxWhatsApp(item.prescriptionId)"
                      >
                        <UIcon name="i-lucide-message-circle" class="h-3.5 w-3.5" />
                        {{ sendingRxWaId === item.prescriptionId ? 'Sending…' : 'WhatsApp' }}
                      </button>
                    </div>
                  </div>

                  <!-- Warranty card bubble -->
                  <div
                    v-else-if="item.kind === 'warranty'"
                    :data-card-id="item.cardId"
                    class="overflow-hidden rounded-lg border border-slate-200 border-l-4 bg-white"
                    :class="kindColor(item.kind)"
                  >
                    <button
                      type="button"
                      class="flex w-full cursor-pointer items-start justify-between gap-2 px-3 py-2 text-left hover:bg-slate-50"
                      @click="toggleCardExpand(item)"
                    >
                      <div class="min-w-0">
                        <p class="text-sm font-medium text-[#1C2B35]">{{ item.title }}</p>
                        <p v-if="item.body" class="mt-0.5 truncate text-xs text-slate-500">{{ item.body }}</p>
                      </div>
                      <div class="flex shrink-0 items-center gap-1">
                        <p class="text-[11px] text-slate-400">{{ formatWhen(item.at) }}</p>
                        <UIcon
                          name="i-lucide-chevron-down"
                          class="h-3.5 w-3.5 text-slate-400 transition"
                          :class="expandedCardId === item.cardId ? 'rotate-180' : ''"
                        />
                      </div>
                    </button>
                    <div
                      v-if="expandedCardId === item.cardId"
                      data-card-actions
                      class="grid gap-px border-t border-slate-200 bg-slate-100"
                      :class="waEnabled ? 'grid-cols-3' : 'grid-cols-2'"
                      @click.stop
                    >
                      <button
                        type="button"
                        class="flex items-center justify-center gap-1.5 bg-white px-2 py-2.5 text-xs font-semibold text-[#00838f] hover:bg-[#e0f7fa] disabled:opacity-50"
                        :disabled="cardActionBusy || sendingCardWaId === item.cardId"
                        @click="item.cardId && openWarrantyEdit(item.cardId)"
                      >
                        <UIcon name="i-lucide-pencil" class="h-3.5 w-3.5" />
                        Edit
                      </button>
                      <button
                        v-if="waEnabled"
                        type="button"
                        class="flex items-center justify-center gap-1.5 bg-white px-2 py-2.5 text-xs font-semibold text-emerald-700 hover:bg-emerald-50 disabled:opacity-50"
                        :disabled="cardActionBusy || sendingCardWaId === item.cardId"
                        @click="item.cardId && sendCardWhatsApp(item.cardId, item.uniqueCode)"
                      >
                        <UIcon name="i-lucide-message-circle" class="h-3.5 w-3.5" />
                        {{ sendingCardWaId === item.cardId ? 'Sending…' : 'WhatsApp' }}
                      </button>
                      <button
                        type="button"
                        class="flex items-center justify-center gap-1.5 bg-white px-2 py-2.5 text-xs font-semibold text-red-600 hover:bg-red-50 disabled:opacity-50"
                        :disabled="cardActionBusy || sendingCardWaId === item.cardId"
                        @click="item.cardId && deleteWarrantyCard(item.cardId, item.uniqueCode)"
                      >
                        <UIcon name="i-lucide-trash-2" class="h-3.5 w-3.5" />
                        Delete
                      </button>
                    </div>
                  </div>

                  <!-- Bill bubble -->
                  <div
                    v-else-if="item.kind === 'bill'"
                    :data-bill-id="item.billId"
                    class="overflow-hidden rounded-lg border border-slate-200 border-l-4 bg-white"
                    :class="billBorderColor(item.billStatus)"
                  >
                    <button
                      type="button"
                      class="flex w-full cursor-pointer items-start justify-between gap-2 px-3 py-2 text-left hover:bg-slate-50"
                      @click="toggleBillExpand(item)"
                    >
                      <div class="min-w-0">
                        <p class="text-sm font-medium text-[#1C2B35]">{{ item.title }}</p>
                        <p v-if="item.body" class="mt-0.5 truncate text-xs text-slate-500">{{ item.body }}</p>
                      </div>
                      <div class="flex shrink-0 items-center gap-1">
                        <p class="text-[11px] text-slate-400">{{ formatWhen(item.at) }}</p>
                        <UIcon
                          name="i-lucide-chevron-down"
                          class="h-3.5 w-3.5 text-slate-400 transition"
                          :class="expandedBillId === item.billId ? 'rotate-180' : ''"
                        />
                      </div>
                    </button>
                    <div
                      v-if="expandedBillId === item.billId"
                      data-bill-actions
                      class="grid gap-px border-t border-slate-200 bg-slate-100"
                      :class="canCollectBill(item.billStatus) ? 'grid-cols-2' : 'grid-cols-1'"
                      @click.stop
                    >
                      <button
                        v-if="canCollectBill(item.billStatus)"
                        type="button"
                        class="flex items-center justify-center gap-1.5 bg-white px-2 py-2.5 text-xs font-semibold text-emerald-700 hover:bg-emerald-50 disabled:opacity-50"
                        :disabled="billActionBusy"
                        @click="openCollect(item)"
                      >
                        <UIcon name="i-lucide-banknote" class="h-3.5 w-3.5" />
                        Collect
                      </button>
                      <button
                        v-if="normalizeBillStatus(item.billStatus) !== 'cancelled'"
                        type="button"
                        class="flex items-center justify-center gap-1.5 bg-white px-2 py-2.5 text-xs font-semibold text-amber-700 hover:bg-amber-50 disabled:opacity-50"
                        :disabled="billActionBusy"
                        :class="billHasLinkedReceipts(item) ? 'opacity-50' : ''"
                        :title="billHasLinkedReceipts(item) ? 'Delete linked receipts first' : 'Cancel bill'"
                        @click="cancelBill(item)"
                      >
                        <UIcon name="i-lucide-ban" class="h-3.5 w-3.5" />
                        Cancel
                      </button>
                      <button
                        v-if="normalizeBillStatus(item.billStatus) === 'cancelled'"
                        type="button"
                        class="flex items-center justify-center gap-1.5 bg-white px-2 py-2.5 text-xs font-semibold text-red-600 hover:bg-red-50 disabled:opacity-50"
                        :disabled="billActionBusy"
                        @click="deleteBill(item)"
                      >
                        <UIcon name="i-lucide-trash-2" class="h-3.5 w-3.5" />
                        Delete
                      </button>
                    </div>
                  </div>

                  <!-- Receipt bubble -->
                  <div
                    v-else-if="item.kind === 'receipt'"
                    :data-receipt-id="item.receiptId"
                    class="overflow-hidden rounded-lg border border-slate-200 border-l-4 bg-white"
                    :class="kindColor(item.kind)"
                  >
                    <button
                      type="button"
                      class="flex w-full cursor-pointer items-start justify-between gap-2 px-3 py-2 text-left hover:bg-slate-50"
                      @click="toggleReceiptExpand(item)"
                    >
                      <div class="min-w-0">
                        <p class="text-sm font-medium text-[#1C2B35]">{{ item.title }}</p>
                        <p v-if="item.body" class="mt-0.5 truncate text-xs text-slate-500">{{ item.body }}</p>
                      </div>
                      <div class="flex shrink-0 items-center gap-1">
                        <p class="text-[11px] text-slate-400">{{ formatWhen(item.at) }}</p>
                        <UIcon
                          name="i-lucide-chevron-down"
                          class="h-3.5 w-3.5 text-slate-400 transition"
                          :class="expandedReceiptId === item.receiptId ? 'rotate-180' : ''"
                        />
                      </div>
                    </button>
                    <div
                      v-if="expandedReceiptId === item.receiptId"
                      data-receipt-actions
                      class="grid grid-cols-1 gap-px border-t border-slate-200 bg-slate-100"
                      @click.stop
                    >
                      <button
                        type="button"
                        class="flex items-center justify-center gap-1.5 bg-white px-2 py-2.5 text-xs font-semibold text-red-600 hover:bg-red-50 disabled:opacity-50"
                        :disabled="billActionBusy"
                        @click="deleteReceipt(item)"
                      >
                        <UIcon name="i-lucide-trash-2" class="h-3.5 w-3.5" />
                        Delete
                      </button>
                    </div>
                  </div>

                  <!-- Compact other events -->
                  <div
                    v-else
                    class="rounded-lg border border-slate-200 border-l-4 bg-white px-3 py-2"
                    :class="[kindColor(item.kind), (item.kind === 'lab' || item.kind === 'plan') ? 'cursor-pointer hover:bg-slate-50' : '']"
                    @click="onPlanTimelineClick(item)"
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
            </div>
          </div>

          <div class="shrink-0 border-t border-slate-200 bg-white px-4 py-3">
            <div class="mx-auto w-full max-w-[30rem] space-y-2">
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
                  class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50 disabled:opacity-50"
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
                <input
                  v-model="noteBody"
                  placeholder="Add note"
                  class="h-10 flex-1 rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm outline-none focus:border-[#0097A7] focus:bg-white"
                >
                <button
                  type="submit"
                  class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[#0097A7] text-white hover:bg-[#00838f] disabled:opacity-50"
                  title="Send note"
                  aria-label="Send note"
                  :disabled="savingNote || processingFiles || (!noteBody.trim() && !noteFiles.length)"
                >
                  <UIcon name="i-lucide-send" class="h-4 w-4" />
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

            <div class="mt-2 flex gap-2">
              <div class="grid min-w-0 flex-1 grid-cols-4 gap-2">
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
                  @click="openPlanCreate"
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
              <button
                type="button"
                class="flex h-[52px] w-14 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-slate-500 to-slate-600 text-white shadow-[0_2px_8px_rgba(108,117,125,0.35)] transition hover:from-slate-600 hover:to-slate-700"
                title="AI summarise patient history"
                aria-label="AI summarise patient history"
                @click="toast.add({ title: 'AI coming soon', color: 'neutral' })"
              >
                <UIcon name="i-lucide-bot" class="h-6 w-6" />
              </button>
            </div>
            </div>
          </div>
          </template>
        </template>
        <div v-else-if="loadingChart" class="flex flex-1 items-center justify-center text-sm text-slate-400">Loading…</div>
      </div>
    </div>

    <DeskBookModal
      v-model:open="bookOpen"
      :client-id="client?.client_id"
      :client-name="client?.name"
      :edit-appointment-id="editAppointmentId"
      @booked="() => { editAppointmentId = null; client && loadChart(client.client_id) }"
      @saved="() => { editAppointmentId = null; client && loadChart(client.client_id) }"
      @update:open="(v) => { if (!v) editAppointmentId = null }"
    />
    <DeskAppointmentDetailModal
      v-model:open="detailOpen"
      :appointment-id="detailAppointmentId"
      hide-open-patient
      @edit="onApptDetailEdit"
      @updated="onApptDetailUpdated"
    />
    <DeskNoteEditModal
      v-model:open="noteEditOpen"
      :client-id="client?.client_id ?? null"
      :note-id="noteEditTarget?.noteId ?? null"
      :initial-body="noteEditTarget?.body || ''"
      :initial-datetime="noteEditTarget?.at || ''"
      :initial-attachments="noteEditTarget?.attachments || []"
      @saved="() => { noteEditTarget = null; client && loadChart(client.client_id) }"
      @update:open="(v) => { if (!v) noteEditTarget = null }"
    />
    <DeskLabCreateModal
      v-model:open="labCreateOpen"
      :client-id="client?.client_id"
      :client-name="client?.name"
      @created="() => { client && loadChart(client.client_id).then(() => scrollTimelineToBottom()); bumpBadges() }"
    />
    <DeskLabCaseModal
      v-model:open="labDetailOpen"
      :case-id="labDetailCaseId"
      @changed="() => { client && loadChart(client.client_id); bumpBadges() }"
      @book="() => openBook()"
    />
    <DeskPlanCreateModal
      v-model:open="planCreateOpen"
      :client-id="client?.client_id ?? null"
      :plan-id="planEditId"
      @saved="() => { client && loadChart(client.client_id).then(() => scrollTimelineToBottom()) }"
    />
    <DeskPlanViewModal
      v-model:open="planViewOpen"
      :plan-id="planViewId"
      @edit="openPlanEdit"
      @pricing="openPlanPricing"
      @deleted="() => { client && loadChart(client.client_id) }"
    />
    <DeskPlanPricingModal
      v-model:open="planPricingOpen"
      :plan-id="planPricingId"
      @saved="() => { client && loadChart(client.client_id) }"
    />
    <DeskWarrantyCardModal
      v-model:open="warrantyOpen"
      :client-id="client?.client_id ?? null"
      :card-id="warrantyEditId"
      @saved="() => { warrantyEditId = null; client && loadChart(client.client_id).then(() => scrollTimelineToBottom()) }"
      @update:open="(v) => { if (!v) warrantyEditId = null }"
    />
    <DeskCollectBillModal
      v-model:open="collectOpen"
      :bill-id="collectBillId"
      :amount-due="collectAmountDue"
      :bill-total="collectBillTotal"
      :total-paid="collectTotalPaid"
      :client-name="client?.name"
      @saved="() => { collectBillId = null; expandedBillId = null; client && loadChart(client.client_id).then(() => scrollTimelineToBottom()) }"
      @update:open="(v) => { if (!v) collectBillId = null }"
    />

    <UModal v-model:open="rxOpen" title="New prescription">
      <template #body>
        <form class="space-y-3" @submit.prevent="saveRx(false)">
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
          <div class="grid grid-cols-2 gap-2 pt-1">
            <UButton
              type="button"
              class="bg-rose-500 hover:bg-rose-600"
              :loading="savingRx"
              :disabled="!rxItems.length"
              @click="saveRx(true)"
            >
              <UIcon name="i-lucide-printer" class="h-4 w-4" />
              Print
            </UButton>
            <UButton
              type="button"
              class="bg-[#0097A7]"
              :loading="savingRx"
              :disabled="!rxItems.length"
              @click="saveRx(false)"
            >
              Save
            </UButton>
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
