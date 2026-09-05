<script setup lang="ts">
import {
  ACTIVITY_FEED_PAGE_SIZE,
  ACTIVITY_TYPE_FILTERS,
  activityEventBadgeClass,
  activityEventDisplay,
  activityEventLabel,
  formatActivityDateTime,
  markActivitySeenUpTo,
  type ActivityEvent,
  type ActivityEventFilter,
  type ActivityFeedPayload
} from '~/utils/activity'

const props = withDefaults(defineProps<{
  active?: boolean
  markReadOnView?: boolean
}>(), {
  active: true,
  markReadOnView: false
})

const emit = defineEmits<{
  readStateChange: []
  openPatient: [clientId: number]
}>()

const { api } = useApi()

const typeFilter = ref<ActivityEventFilter>('')
const events = ref<ActivityEvent[]>([])
const hasMore = ref(false)
const loading = ref(false)
const loadingMore = ref(false)
const error = ref<string | null>(null)

const scrollEl = ref<HTMLElement | null>(null)
const sentinelEl = ref<HTMLElement | null>(null)
const beforeId = ref<number | null>(null)
const loadingLock = ref(false)
const markedOnOpen = ref(false)
let observer: IntersectionObserver | null = null

async function loadPage(reset: boolean) {
  if (loadingLock.value) return
  loadingLock.value = true
  if (reset) {
    loading.value = true
    error.value = null
    beforeId.value = null
  } else {
    loadingMore.value = true
  }

  try {
    const data = await api<ActivityFeedPayload>('/activity', {
      query: {
        limit: ACTIVITY_FEED_PAGE_SIZE,
        before_id: reset ? undefined : (beforeId.value || undefined),
        type: typeFilter.value || undefined
      }
    })
    if (reset) {
      events.value = data.events
    } else {
      const seen = new Set(events.value.map(e => e.id))
      for (const event of data.events) {
        if (!seen.has(event.id)) events.value.push(event)
      }
    }
    hasMore.value = data.has_more
    beforeId.value = data.next_before_id
  } catch (e: unknown) {
    if (reset) {
      events.value = []
      hasMore.value = false
      error.value = e instanceof Error ? e.message : 'Could not load activity'
    }
  } finally {
    loadingLock.value = false
    loading.value = false
    loadingMore.value = false
  }
}

function onPatient(clientId: number) {
  emit('openPatient', clientId)
}

function displayFor(event: ActivityEvent) {
  return activityEventDisplay(event)
}

function setupObserver() {
  observer?.disconnect()
  observer = null
  if (!props.active || !import.meta.client) return
  const root = scrollEl.value
  const sentinel = sentinelEl.value
  if (!root || !sentinel) return
  observer = new IntersectionObserver(
    (entries) => {
      if (entries[0]?.isIntersecting && hasMore.value && !loadingLock.value) {
        void loadPage(false)
      }
    },
    { root, rootMargin: '120px', threshold: 0 }
  )
  observer.observe(sentinel)
}

watch(
  () => props.active,
  (active) => {
    if (!active) {
      markedOnOpen.value = false
      return
    }
    void loadPage(true)
  },
  { immediate: true }
)

watch(typeFilter, () => {
  if (props.active) void loadPage(true)
})

watch(
  () => [props.active, props.markReadOnView, loading.value, events.value] as const,
  () => {
    if (!props.active || !props.markReadOnView) return
    if (loading.value || !events.value.length || markedOnOpen.value) return
    const newestId = events.value[0]?.id
    if (!newestId) return
    if (markActivitySeenUpTo(newestId)) {
      markedOnOpen.value = true
      emit('readStateChange')
    }
  }
)

watch(
  () => [props.active, hasMore.value, events.value.length, loading.value] as const,
  async () => {
    await nextTick()
    setupObserver()
  }
)

onBeforeUnmount(() => {
  observer?.disconnect()
})
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col">
    <div class="shrink-0">
      <div class="-mx-1 flex gap-1.5 overflow-x-auto px-1 pb-2">
        <button
          v-for="f in ACTIVITY_TYPE_FILTERS"
          :key="f.key || 'all'"
          type="button"
          class="shrink-0 rounded-full border px-2.5 py-1 text-[10px] font-medium transition"
          :class="typeFilter === f.key
            ? 'border-[#0097A7] bg-[#0097A7] text-white'
            : 'border-slate-200 bg-white text-slate-600'"
          @click="typeFilter = f.key"
        >
          {{ f.label }}
        </button>
      </div>
    </div>

    <div
      ref="scrollEl"
      class="min-h-0 flex-1 space-y-2.5 overflow-y-auto"
    >
      <div
        v-if="error"
        class="rounded-xl border border-red-100 bg-red-50 px-3 py-4 text-center"
      >
        <p class="text-sm text-red-700">{{ error }}</p>
        <button
          type="button"
          class="mt-2 rounded-lg border border-red-200 px-3 py-1.5 text-xs font-medium text-red-700"
          @click="loadPage(true)"
        >
          Retry
        </button>
      </div>
      <p
        v-else-if="loading && !events.length"
        class="py-8 text-center text-sm text-slate-400"
      >
        Loading activity…
      </p>
      <div
        v-else-if="!events.length"
        class="py-8 text-center text-sm text-slate-400"
      >
        No staff activity recorded yet.
      </div>
      <template v-else>
        <div
          v-for="event in events"
          :key="event.id"
          class="rounded-xl border border-slate-200 bg-white px-3.5 py-3"
        >
          <div class="flex items-start justify-between gap-2">
            <span
              class="rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
              :class="activityEventBadgeClass(event.event_type)"
            >
              {{ activityEventLabel(event.event_type) }}
            </span>
            <span class="shrink-0 text-[11px] text-slate-400">
              {{ formatActivityDateTime(event.created_at) }}
            </span>
          </div>
          <div class="mt-1.5 text-sm font-semibold text-[#1C2B35]">
            <template v-if="(event.client_id || 0) > 0">
              <button
                type="button"
                class="text-[#0097A7] hover:underline"
                @click="onPatient(event.client_id!)"
              >
                {{ displayFor(event).patientName }}
              </button>
              <span
                v-if="displayFor(event).detail"
                class="font-semibold text-[#1C2B35]"
              > — {{ displayFor(event).detail }}</span>
            </template>
            <template v-else>
              {{ displayFor(event).patientName }}
              <template v-if="displayFor(event).detail">
                — {{ displayFor(event).detail }}
              </template>
            </template>
          </div>
          <p class="mt-1 text-xs text-slate-500">
            by {{ event.actor_name?.trim() || 'Staff' }}
          </p>
        </div>
        <div
          ref="sentinelEl"
          class="h-1"
          aria-hidden="true"
        />
        <p
          v-if="loadingMore"
          class="pb-2 text-center text-xs text-slate-400"
        >
          Loading more…
        </p>
      </template>
    </div>
  </div>
</template>
