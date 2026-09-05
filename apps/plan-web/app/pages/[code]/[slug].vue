<script setup lang="ts">
import {
  formatInr,
  formatRecovery,
  formatVisits,
  pickLocalized,
  type PlanLang
} from '~/utils/planI18n'

type SubPlan = {
  treatment_name: string
  treatment_name_gu?: string | null
  short_explainer?: string | null
  short_explainer_gu?: string | null
  recovery_days?: number | null
  default_appts?: number
  tooth_fdi?: string
  location_text?: string | null
  qty: number
  is_foc: boolean
  price?: number | null
  photos: string[]
  treatment_photos: string[]
}

type PublicPayload = {
  plan: {
    title: string
    notes?: string | null
    created_at?: string | null
    patient_name?: string
    clinic_name?: string
    clinic_phone?: string
    sub_plans: SubPlan[]
  }
  link: {
    expires_at?: string | null
    access_log_id: number
  }
  context: {
    patient_name?: string
    clinic_name?: string
    clinic_phone?: string
  }
}

const route = useRoute()
const config = useRuntimeConfig()
const code = computed(() => String(route.params.code || ''))
const slug = computed(() => String(route.params.slug || ''))

const lang = ref<PlanLang>('en')
const errorTitle = ref('')
const errorMessage = ref('')
const payload = ref<PublicPayload | null>(null)
const startedAt = ref(Date.now())
const lastSent = ref(0)

const labels = computed(() => ({
  prepared: lang.value === 'gu' ? 'તૈયાર' : 'Prepared',
  expires: lang.value === 'gu' ? 'લિંક સમાપ્ત' : 'Link expires',
  treatments: lang.value === 'gu' ? 'સારવાર' : 'Treatments',
  total: lang.value === 'gu' ? 'અંદાજિત કુલ' : 'Estimated total',
  complimentary: lang.value === 'gu' ? 'મફત' : 'Complimentary',
  tooth: lang.value === 'gu' ? 'દાંત' : 'Tooth',
  visits: lang.value === 'gu' ? 'મુલાકાત' : 'Visits',
  recovery: lang.value === 'gu' ? 'રિકવરી' : 'Recovery',
  callClinic: lang.value === 'gu' ? 'ક્લિનિકને કૉલ કરો' : 'Call clinic',
  hello: lang.value === 'gu' ? 'નમસ્તે' : 'Hello'
}))

async function load() {
  errorTitle.value = ''
  if (!/^[A-Za-z0-9]{7}$/.test(code.value) || !/^[a-z0-9-]+$/.test(slug.value)) {
    errorTitle.value = 'Invalid link'
    errorMessage.value = 'This link looks incomplete. Please ask your clinic for a new one.'
    return
  }
  try {
    const res = await $fetch<{ ok: boolean, data?: PublicPayload, error?: string }>(
      `${config.public.apiBase}/public/treatment-plans/${encodeURIComponent(code.value)}/${encodeURIComponent(slug.value)}`
    )
    if (!res.ok || !res.data) {
      errorTitle.value = 'Link not available'
      errorMessage.value = res.error || 'This link may have expired.'
      return
    }
    payload.value = res.data
    startedAt.value = Date.now()
  } catch (e: unknown) {
    const err = e as { statusCode?: number, data?: { detail?: string } }
    errorTitle.value = err.statusCode === 410 ? 'Link expired' : 'Something went wrong'
    errorMessage.value = err.data?.detail
      || (err.statusCode === 410
        ? 'Please contact your clinic for an updated plan.'
        : 'We could not load this plan right now.')
  }
}

function sendSession(force = false) {
  const logId = payload.value?.link?.access_log_id || 0
  if (logId <= 0) return
  const duration = Math.floor((Date.now() - startedAt.value) / 1000)
  if (!force && duration - lastSent.value < 3) return
  lastSent.value = duration
  const url = `${config.public.apiBase}/public/treatment-plans/${encodeURIComponent(code.value)}/${encodeURIComponent(slug.value)}/session`
  const body = JSON.stringify({ access_log_id: logId, duration_seconds: duration })
  if (typeof navigator !== 'undefined' && navigator.sendBeacon) {
    if (navigator.sendBeacon(url, new Blob([body], { type: 'application/json' }))) return
  }
  void $fetch(url, { method: 'POST', body: { access_log_id: logId, duration_seconds: duration } }).catch(() => {})
}

const totalFee = computed(() =>
  (payload.value?.plan?.sub_plans || []).reduce((sum, sp) => sum + (sp.is_foc ? 0 : Number(sp.price || 0)), 0)
)

const telHref = computed(() => {
  const digits = (payload.value?.context?.clinic_phone || payload.value?.plan?.clinic_phone || '').replace(/\D/g, '')
  return digits ? `tel:${digits}` : null
})

onMounted(() => {
  void load()
  const tick = window.setInterval(() => sendSession(false), 5000)
  const onHide = () => sendSession(true)
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') onHide()
  })
  window.addEventListener('pagehide', onHide)
  onBeforeUnmount(() => {
    clearInterval(tick)
    window.removeEventListener('pagehide', onHide)
    sendSession(true)
  })
})
</script>

<template>
  <div class="pp-shell">
    <div v-if="errorTitle" class="pp-card pp-error">
      <h1>{{ errorTitle }}</h1>
      <p>{{ errorMessage }}</p>
    </div>

    <div v-else-if="!payload" class="pp-loading">Loading your plan…</div>

    <article v-else class="pp-card">
      <header class="pp-hero">
        <div class="pp-hero-top">
          <p class="pp-clinic">{{ payload.context.clinic_name || payload.plan.clinic_name }}</p>
          <div class="pp-lang">
            <button type="button" :class="{ active: lang === 'en' }" @click="lang = 'en'">EN</button>
            <button type="button" :class="{ active: lang === 'gu' }" @click="lang = 'gu'">ગુ</button>
          </div>
        </div>
        <h1>
          {{ labels.hello }}{{ payload.context.patient_name ? `, ${payload.context.patient_name}` : '' }}
        </h1>
        <p class="title">{{ payload.plan.title }}</p>
        <p class="meta">
          {{ labels.prepared }}
          <template v-if="payload.plan.created_at">
            · {{ new Date(payload.plan.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) }}
          </template>
          <template v-if="payload.link.expires_at">
            · {{ labels.expires }}
            {{ new Date(payload.link.expires_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }) }}
          </template>
        </p>
      </header>

      <div class="pp-body">
        <p v-if="payload.plan.notes" class="pp-notes">{{ payload.plan.notes }}</p>

        <p class="pp-section-label">{{ labels.treatments }}</p>
        <div
          v-for="(sp, idx) in payload.plan.sub_plans"
          :key="idx"
          class="pp-proc"
        >
          <img
            v-if="sp.photos[0] || sp.treatment_photos[0]"
            :src="sp.photos[0] || sp.treatment_photos[0]"
            alt=""
          >
          <div class="pp-proc-body">
            <div class="pp-proc-head">
              <h2>{{ pickLocalized(lang, sp.treatment_name, sp.treatment_name_gu) }}</h2>
              <span v-if="sp.is_foc" class="pp-foc">{{ labels.complimentary }}</span>
              <span v-else-if="sp.price" class="pp-price">{{ formatInr(sp.price) }}</span>
            </div>
            <p class="pp-desc">
              {{
                pickLocalized(lang, sp.short_explainer, sp.short_explainer_gu)
                  || sp.location_text
                  || ''
              }}
            </p>
            <div class="pp-stats">
              <div class="pp-stat">
                <div class="k">{{ labels.tooth }}</div>
                <div class="v">{{ sp.tooth_fdi || sp.location_text || '—' }}</div>
              </div>
              <div class="pp-stat">
                <div class="k">{{ labels.visits }}</div>
                <div class="v">{{ formatVisits(sp.default_appts || 1, lang) }}</div>
              </div>
              <div class="pp-stat">
                <div class="k">{{ labels.recovery }}</div>
                <div class="v">{{ formatRecovery(sp.recovery_days, lang) }}</div>
              </div>
            </div>
          </div>
        </div>

        <div class="pp-total">
          <p class="pp-section-label">{{ labels.total }}</p>
          <div class="amount">{{ formatInr(totalFee) }}</div>
        </div>

        <a v-if="telHref" class="pp-cta" :href="telHref">{{ labels.callClinic }}</a>
      </div>
    </article>
  </div>
</template>
