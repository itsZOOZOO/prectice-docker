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
  kind: 'note' | 'bill' | 'receipt' | 'rx' | 'appointment' | 'task'
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

const MAX_NOTE_FILES = 10
const MAX_FILE_BYTES = 10 * 1024 * 1024

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
const toggling = ref(false)
const bookOpen = ref(false)

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
    const [c, notes, bills, receipts, rxs, appts, tasks] = await Promise.all([
      api<Client>(`/clients/${id}`),
      api<{ note_id: number, body: string, created_at: string, author_name: string | null, attachments?: NoteAttachment[] }[]>(`/clients/${id}/notes`),
      api<{ bill_id: number, amount_due: number, status: string, description: string | null, issued_at: string }[]>(`/clients/${id}/bills`),
      api<{ receipt_id: number, amount: number, payment_mode: string, description: string | null, received_at: string }[]>(`/clients/${id}/receipts`),
      api<{ prescription_id: number, prescription_date: string, notes: string | null, items: { medicine_name: string }[] }[]>(`/clients/${id}/prescriptions`),
      api<{ items: { appointment_id: number, appointment_date: string, appointment_time: string, status: string, doctor_name: string | null, service_name: string | null }[] }>('/appointments', { query: { client_id: id, limit: 50 } }),
      api<{ items: { task_id: number, task_description: string, status: string, due_date: string | null, created_at: string }[] }>('/tasks', { query: { client_id: id } })
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
    timeline.value = items.sort((a, b) => Date.parse(b.at) - Date.parse(a.at))
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
    for (const p of noteFiles.value) {
      fd.append('files', p.file)
    }
    await api(`/clients/${client.value.client_id}/notes`, {
      method: 'POST',
      body: fd
    })
    noteBody.value = ''
    clearNoteFiles()
    await loadChart(client.value.client_id)
    toast.add({ title: 'Note saved', color: 'success' })
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
  } finally {
    savingNote.value = false
  }
}

function onPickFiles(ev: Event) {
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
    noteFiles.value.push({
      file,
      preview: isImageFile(file) ? URL.createObjectURL(file) : null
    })
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
    const fd = new FormData()
    fd.append('file', file)
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
    task: 'border-l-slate-400'
  }
  return map[kind]
}
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

          <div class="shrink-0 border-b border-slate-200 bg-white px-5 py-3">
            <form class="space-y-2" @submit.prevent="addNote">
              <div class="flex gap-2">
                <input
                  v-model="noteBody"
                  placeholder="Add a note to the timeline…"
                  class="h-10 flex-1 rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm outline-none focus:border-[#0097A7] focus:bg-white"
                >
                <button
                  type="button"
                  class="flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50"
                  title="Attach images or PDF"
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
                  :disabled="savingNote || (!noteBody.trim() && !noteFiles.length)"
                >
                  Save
                </button>
              </div>
              <div v-if="noteFiles.length" class="flex flex-wrap gap-2">
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
            </form>
          </div>

          <div class="min-h-0 flex-1 overflow-y-auto px-5 py-4">
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
                  :class="kindColor(item.kind)"
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
