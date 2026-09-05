export type WaInboxConversationStatus = 'active' | 'closed' | 'all'

export type WaInboxLeadStatus = 'lead_sent' | 'lead_failed' | 'not_a_lead' | (string & {})

export interface WaInboxTag {
  id: number
  name: string
  slug: string
  color: string
  is_system: number
}

export interface WaInboxSmartList {
  id: number
  name: string
  sort_order?: number
  is_system?: number
  mode: 'dynamic' | 'frozen' | string
  status_filter: string
  include_tag_ids?: number[]
  exclude_tag_ids?: number[]
  date_mode?: string
  date_on?: string | null
  date_from?: string | null
  date_to?: string | null
  summary?: string
}

export interface WaInboxPreviousConversation {
  id: number
  started_at: string
  status: string
  msg_count: number
  last_message_at?: string | null
  lead_status?: string | null
}

export interface WaInboxThreadContext {
  total: number
  ordinal: number
  previous: WaInboxPreviousConversation[]
}

export interface WaInboxLeadSourceOption {
  campaign_name: string
}

export interface WaInboxConversation {
  id: number
  contact_name: string
  wa_id: string
  last_message_at: string | null
  last_msg: string | null
  needs_attention: number | boolean
  status: string
  tags?: WaInboxTag[]
}

export interface WaInboxConversationDetail extends WaInboxConversation {
  window_open: boolean
  window_seconds_left: number
  started_at?: string | null
  lead_status?: WaInboxLeadStatus | null
  lead_status_label?: string | null
}

export interface WaInboxTemplateComponent {
  type?: string
  format?: string
  text?: string
  buttons?: Array<{ text?: string, type?: string }>
  cards?: unknown[]
}

export interface WaInboxCarouselDraft {
  cards_json?: Array<{
    body_text?: string
    body_variables?: string[]
    buttons?: Array<{ text?: string }>
  }>
  button_structure?: Array<{ text?: string }>
}

export interface WaInboxMessage {
  id: number
  direction: 'in' | 'out'
  type: string
  body: string | null
  template_name?: string | null
  template_components?: WaInboxTemplateComponent[] | null
  template_params?: Record<string, unknown> | unknown[] | null
  carousel_draft?: WaInboxCarouselDraft | null
  media_url?: string | null
  media_file_name?: string | null
  media_mime_type?: string | null
  media_queue_status?: 'pending' | 'failed' | string | null
  local_path?: string | null
  latest_status?: string | null
  has_send_error?: boolean
  send_error?: string | null
  created_at: string
}

export interface WaInboxTemplate {
  id: number
  name: string
  language: string
  category?: string
}

export interface WaInboxFlow {
  id: number
  name: string
}

export type WaInboxScheduleMessageType = 'text' | 'template' | 'flow'

export interface WaInboxApiResponse<T = unknown> {
  success: boolean
  error?: string
  conversations?: WaInboxConversation[]
  conversation?: WaInboxConversationDetail
  messages?: WaInboxMessage[]
  templates?: WaInboxTemplate[]
  flows?: WaInboxFlow[]
  tags?: WaInboxTag[]
  smart_lists?: WaInboxSmartList[]
  smart_list?: WaInboxSmartList
  default_list_id?: number | null
  thread?: WaInboxThreadContext
  lead_source_options?: WaInboxLeadSourceOption[]
  draft?: string
  scheduled_at?: string
  client_id?: number
  data?: T
}

export const WA_INBOX_MEDIA_TYPES = [
  'image',
  'video',
  'audio',
  'document',
  'sticker',
  'voice',
] as const

export function isWaInboxMediaType(type: string | undefined): boolean {
  return WA_INBOX_MEDIA_TYPES.includes(type as (typeof WA_INBOX_MEDIA_TYPES)[number])
}

export function messageHasPendingMedia(msg: WaInboxMessage): boolean {
  return msg.media_queue_status === 'pending' && !msg.media_url
}

export function fmtWaInboxDateShort(ts: string | null | undefined): string {
  if (!ts) return '—'
  const d = new Date(ts.replace(' ', 'T'))
  return d.toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    timeZone: 'Asia/Kolkata',
  })
}

export function waInboxLeadStatusLabel(
  status: string | null | undefined,
  label?: string | null,
): string {
  if (label) return label
  if (!status) return ''
  return status.replace(/_/g, ' ')
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

/** WhatsApp-style *bold* and _italic_ on already-escaped text. */
export function buildWaFormattedHtml(text: string | null | undefined): string {
  if (!text) return ''
  let s = escapeHtml(text)
  s = s.replace(/\*(.+?)\*/gu, '<strong>$1</strong>')
  s = s.replace(/_(.+?)_/gu, '<em>$1</em>')
  return s.replace(/\n/g, '<br>')
}

export function applyTemplateParams(
  text: string | null | undefined,
  rawParams: WaInboxMessage['template_params'],
): string {
  if (!text || !rawParams) return text || ''

  const isNamed = !Array.isArray(rawParams) && rawParams !== null && typeof rawParams === 'object'
  let out = text

  if (isNamed) {
    Object.entries(rawParams as Record<string, unknown>).forEach(([k, v]) => {
      if (Array.isArray(v)) {
        v.forEach((vv, vi) => {
          out = out.split(`{{${vi + 1}}}`).join(String(vv))
        })
      } else {
        out = out.split(`{{${k}}}`).join(String(v))
      }
    })
  } else if (Array.isArray(rawParams)) {
    rawParams.forEach((v, i) => {
      out = out.split(`{{${i + 1}}}`).join(Array.isArray(v) ? '' : String(v))
    })
  }

  return out
}

let audioCtx: AudioContext | null = null
let unlocked = false

export function unlockWaInboxNotificationSound(): void {
  if (typeof window === 'undefined') return
  try {
    if (!audioCtx) {
      audioCtx = new AudioContext()
    }
    if (audioCtx.state === 'suspended') {
      void audioCtx.resume()
    }
    unlocked = audioCtx.state === 'running'
  } catch {
    unlocked = false
  }
}

/** Short two-tone chime for new inbound WhatsApp messages. */
export function playWaInboxNotificationSound(): void {
  if (typeof window === 'undefined' || document.hidden) return

  try {
    if (!audioCtx) {
      audioCtx = new AudioContext()
    }
    if (audioCtx.state === 'suspended') {
      if (!unlocked) return
      void audioCtx.resume()
    }
    if (audioCtx.state !== 'running') return

    const t = audioCtx.currentTime
    const gain = audioCtx.createGain()
    gain.connect(audioCtx.destination)
    gain.gain.setValueAtTime(0.0001, t)
    gain.gain.exponentialRampToValueAtTime(0.12, t + 0.02)
    gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.45)

    const playTone = (freq: number, start: number, duration: number) => {
      const osc = audioCtx!.createOscillator()
      osc.type = 'sine'
      osc.frequency.setValueAtTime(freq, start)
      osc.connect(gain)
      osc.start(start)
      osc.stop(start + duration)
    }

    playTone(880, t, 0.12)
    playTone(1174, t + 0.1, 0.18)
  } catch {
    // Autoplay or AudioContext unsupported — ignore silently.
  }
}

export function isWaInboxNotificationSoundUnlocked(): boolean {
  return unlocked && audioCtx?.state === 'running'
}

export function fmtWaInboxTime(ts: string | null | undefined): string {
  if (!ts) return ''
  const d = new Date(ts.replace(' ', 'T'))
  return d.toLocaleString('en-IN', {
    day: '2-digit',
    month: '2-digit',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  })
}

/** Keep stick-to-bottom only when the user is already near the latest messages. */
export const WA_INBOX_NEAR_BOTTOM_PX = 120

export function isWaInboxMessageAreaNearBottom(area: HTMLElement): boolean {
  return area.scrollHeight - area.scrollTop - area.clientHeight <= WA_INBOX_NEAR_BOTTOM_PX
}
