<script setup lang="ts">
import type { WaInboxMessage } from '~/utils/waInbox'
import {
  applyTemplateParams,
  buildWaFormattedHtml,
  isWaInboxMediaType,
} from '~/utils/waInbox'

const props = defineProps<{
  msg: WaInboxMessage
}>()

const out = computed(() => props.msg.direction === 'out')
const failed = computed(() => Boolean(props.msg.has_send_error))
const isMedia = computed(() => isWaInboxMediaType(props.msg.type))
const showMediaCaption = computed(
  () => Boolean(props.msg.body) && props.msg.type !== 'document',
)
const templateComps = computed(() => props.msg.template_components || [])

const formattedTime = computed(() =>
  new Date(props.msg.created_at.replace(' ', 'T')).toLocaleString('en-IN', {
    day: '2-digit',
    month: '2-digit',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  }),
)

const sendErrorText = computed(() => {
  if (!props.msg.has_send_error) return ''
  return (
    props.msg.send_error
    || (props.msg.latest_status === 'failed'
      ? 'Message undeliverable — recipient is not on WhatsApp or the number is invalid.'
      : 'Not delivered')
  )
})

function html(text: string) {
  return buildWaFormattedHtml(text)
}

function bodyWithParams(text: string) {
  return html(applyTemplateParams(text, props.msg.template_params))
}

function carouselCardBody(ci: number): string {
  const dc = props.msg.carousel_draft?.cards_json?.[ci] || {}
  let bodyText = dc.body_text || ''
  ;(dc.body_variables || []).forEach((eg, vi) => {
    bodyText = bodyText.split(`{{${vi + 1}}}`).join(eg)
  })
  return bodyText
}

function carouselBtnText(ci: number, bi: number, fallback?: string): string {
  return props.msg.carousel_draft?.cards_json?.[ci]?.buttons?.[bi]?.text || fallback || ''
}

function upper(v?: string) {
  return (v || '').toUpperCase()
}
</script>

<template>
  <div
    class="mb-2 flex flex-col"
    :class="out ? 'items-end' : 'items-start'"
    :data-msg-id="msg.id"
    :data-pending-media="msg.media_queue_status === 'pending' && !msg.media_url ? '1' : undefined"
  >
    <div
      class="max-w-[75%] break-words rounded-[10px] px-2.5 py-1.5"
      :class="out
        ? `rounded-br-sm bg-[#dcf8c6] text-slate-900${failed ? ' ring-1 ring-red-200' : ''}`
        : 'rounded-bl-sm bg-white text-slate-900 shadow-sm'"
    >
      <!-- Media (in or out, non-template) -->
      <template v-if="(msg.direction === 'in' && isMedia) || (out && isMedia && msg.type !== 'template')">
        <template v-if="!msg.media_url">
          <span
            v-if="msg.media_queue_status === 'failed'"
            class="inline-flex items-center gap-1 text-xs text-amber-600"
          >
            <UIcon name="i-lucide-triangle-alert" class="h-3.5 w-3.5" />
            Media unavailable
          </span>
          <span
            v-else-if="isMedia"
            class="inline-flex items-center gap-1 text-xs text-slate-400"
          >
            <UIcon name="i-lucide-loader-circle" class="h-3.5 w-3.5 animate-spin" />
            {{ msg.type }} downloading…
          </span>
        </template>
        <template v-else>
          <template v-if="['image', 'sticker'].includes(msg.type)">
            <a :href="msg.media_url" target="_blank" rel="noreferrer">
              <img
                :src="msg.media_url"
                alt=""
                class="block max-h-[220px] max-w-[220px] rounded-md object-contain"
              >
            </a>
            <div
              v-if="showMediaCaption"
              class="mt-1 text-[13px] leading-snug [&_em]:italic [&_strong]:font-semibold"
              v-html="html(msg.body || '')"
            />
          </template>
          <template v-else-if="msg.type === 'video'">
            <video controls class="block max-w-[220px] rounded-md">
              <source :src="msg.media_url" :type="msg.media_mime_type || 'video/mp4'">
            </video>
            <div
              v-if="showMediaCaption"
              class="mt-1 text-[13px] leading-snug [&_em]:italic [&_strong]:font-semibold"
              v-html="html(msg.body || '')"
            />
          </template>
          <template v-else-if="['audio', 'voice'].includes(msg.type)">
            <audio controls class="block w-[200px]">
              <source :src="msg.media_url" :type="msg.media_mime_type || 'audio/mpeg'">
            </audio>
            <div
              v-if="showMediaCaption"
              class="mt-1 text-[13px] leading-snug [&_em]:italic [&_strong]:font-semibold"
              v-html="html(msg.body || '')"
            />
          </template>
          <a
            v-else-if="msg.type === 'document'"
            :href="msg.media_url"
            target="_blank"
            rel="noreferrer"
            class="flex items-center gap-2 text-inherit no-underline"
          >
            <UIcon name="i-lucide-file-text" class="h-8 w-8 shrink-0 text-red-500" />
            <span class="break-all text-[13px]">{{ msg.media_file_name || msg.body || 'Document' }}</span>
          </a>
          <template v-else>
            <a
              :href="msg.media_url"
              target="_blank"
              rel="noreferrer"
              class="inline-flex items-center gap-1 text-sm"
            >
              <UIcon name="i-lucide-file-text" class="h-4 w-4 text-sky-600" />
              {{ msg.media_file_name || 'File' }}
            </a>
            <div
              v-if="showMediaCaption"
              class="mt-1 text-[13px] leading-snug [&_em]:italic [&_strong]:font-semibold"
              v-html="html(msg.body || '')"
            />
          </template>
        </template>
      </template>

      <!-- Template -->
      <template v-else-if="out && msg.type === 'template'">
        <div v-if="!templateComps.length" class="text-[13px]">
          {{ msg.template_name || msg.body || 'Template' }}
        </div>
        <div v-else class="space-y-1">
          <template v-for="(comp, idx) in templateComps" :key="`${upper(comp.type)}-${idx}`">
            <template v-if="upper(comp.type) === 'HEADER'">
              <div v-if="upper(comp.format) === 'TEXT'" class="text-[13px] font-semibold">
                {{ comp.text || '' }}
              </div>
              <template v-else>
                <a
                  v-if="msg.media_url && upper(comp.format) === 'IMAGE'"
                  :href="msg.media_url"
                  target="_blank"
                  rel="noreferrer"
                  class="mb-1.5 block"
                >
                  <img :src="msg.media_url" alt="" class="block max-w-[200px] rounded-md">
                </a>
                <video
                  v-else-if="msg.media_url && upper(comp.format) === 'VIDEO'"
                  controls
                  class="mb-1.5 block max-w-[200px] rounded-md"
                >
                  <source :src="msg.media_url">
                </video>
                <a
                  v-else-if="msg.media_url"
                  :href="msg.media_url"
                  target="_blank"
                  rel="noreferrer"
                  class="mb-2 flex items-center gap-2 text-inherit no-underline"
                >
                  <UIcon name="i-lucide-file-text" class="h-8 w-8 text-red-500" />
                  <span class="break-all text-[13px]">{{ msg.media_file_name || 'Document' }}</span>
                </a>
                <div
                  v-else-if="upper(comp.format) === 'IMAGE'"
                  class="mb-1 flex items-center gap-1 text-xs text-slate-400"
                >
                  <UIcon name="i-lucide-image" class="h-3.5 w-3.5" />
                  Image attachment
                </div>
                <div
                  v-else-if="upper(comp.format) === 'VIDEO'"
                  class="mb-1 flex items-center gap-1 text-xs text-slate-400"
                >
                  <UIcon name="i-lucide-video" class="h-3.5 w-3.5" />
                  Video attachment
                </div>
                <div
                  v-else-if="upper(comp.format) === 'DOCUMENT'"
                  class="mb-1 flex items-center gap-1 text-xs text-slate-400"
                >
                  <UIcon name="i-lucide-file-text" class="h-3.5 w-3.5" />
                  Document attachment
                </div>
              </template>
            </template>

            <div
              v-else-if="upper(comp.type) === 'BODY'"
              class="text-[13px] leading-relaxed [&_em]:italic [&_strong]:font-semibold"
              v-html="bodyWithParams(comp.text || '')"
            />

            <div
              v-else-if="upper(comp.type) === 'FOOTER'"
              class="mt-1 text-[11px] text-slate-400"
            >
              {{ comp.text || '' }}
            </div>

            <div
              v-else-if="upper(comp.type) === 'BUTTONS'"
              class="mt-2 flex flex-wrap gap-1"
            >
              <span
                v-for="(btn, bi) in (comp.buttons || [])"
                :key="bi"
                class="rounded-full bg-sky-50 px-2.5 py-1 text-[11px] font-medium text-sky-700"
              >
                {{ btn.text || '' }}
              </span>
            </div>

            <div
              v-else-if="upper(comp.type) === 'CAROUSEL'"
              class="mt-2"
            >
              <div class="mb-1 flex items-center gap-1 text-[11px] text-slate-400">
                <UIcon name="i-lucide-layers" class="h-3 w-3" />
                CAROUSEL · {{ (comp.cards || []).length }} cards
              </div>
              <div
                v-for="(_card, ci) in (comp.cards || [])"
                :key="ci"
                class="mt-1 rounded border border-slate-200 bg-slate-50 p-2 text-xs"
              >
                <div class="mb-0.5 text-[10px] text-slate-400">
                  Card {{ Number(ci) + 1 }}
                </div>
                <div
                  v-if="carouselCardBody(Number(ci))"
                  class="leading-snug [&_em]:italic [&_strong]:font-semibold"
                  v-html="html(carouselCardBody(Number(ci)))"
                />
                <div
                  v-if="(msg.carousel_draft?.button_structure || []).length"
                  class="mt-1 flex flex-wrap gap-1"
                >
                  <span
                    v-for="(btnDef, bi) in (msg.carousel_draft?.button_structure || [])"
                    :key="bi"
                    class="rounded-full bg-slate-200/80 px-2 py-0.5 text-[10px] text-slate-700"
                  >
                    {{ carouselBtnText(Number(ci), Number(bi), btnDef.text) }}
                  </span>
                </div>
              </div>
            </div>
          </template>

          <div class="mt-1 flex items-center gap-1 text-[10px] text-slate-400">
            <UIcon name="i-lucide-layers" class="h-3 w-3" />
            {{ msg.template_name || '' }}
          </div>
        </div>
      </template>

      <!-- Reaction -->
      <template v-else-if="msg.type === 'reaction'">
        <template v-if="msg.body">
          <span class="block text-[26px] leading-none">{{ msg.body }}</span>
          <span class="text-[11px] text-slate-400">Reacted to a message</span>
        </template>
        <span v-else class="inline-flex items-center gap-1 text-xs text-slate-400">
          <UIcon name="i-lucide-heart-crack" class="h-3.5 w-3.5" />
          Reaction removed
        </span>
      </template>

      <!-- Plain text -->
      <div
        v-else-if="msg.body"
        class="text-sm leading-snug [&_em]:italic [&_strong]:font-semibold"
        v-html="html(msg.body)"
      />
      <span v-else-if="msg.type" class="text-slate-400">[{{ msg.type }}]</span>

      <div
        v-if="msg.has_send_error"
        class="mt-2 rounded border border-red-200 bg-red-50 px-2 py-1 text-[11px] text-red-700"
      >
        <span class="font-medium">Not delivered</span>
        <span class="mt-0.5 block text-red-600">{{ sendErrorText }}</span>
      </div>
    </div>

    <div class="mt-0.5 flex items-center gap-1 text-[11px] text-slate-400">
      {{ formattedTime }}
      <template v-if="out">
        <UIcon
          v-if="msg.latest_status === 'read'"
          name="i-lucide-check-check"
          class="inline h-3 w-3 text-sky-500"
        />
        <UIcon
          v-else-if="msg.latest_status === 'delivered'"
          name="i-lucide-check-check"
          class="inline h-3 w-3 text-slate-400"
        />
        <UIcon
          v-else-if="msg.latest_status === 'sent'"
          name="i-lucide-check"
          class="inline h-3 w-3 text-slate-400"
        />
        <UIcon
          v-else-if="msg.latest_status === 'failed'"
          name="i-lucide-x"
          class="inline h-3 w-3 text-red-500"
        />
      </template>
    </div>
  </div>
</template>
