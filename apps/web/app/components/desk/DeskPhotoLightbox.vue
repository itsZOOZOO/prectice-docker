<script setup lang="ts">
const open = defineModel<boolean>('open', { default: false })

const props = withDefaults(defineProps<{
  photos: string[]
  startIndex?: number
}>(), {
  startIndex: 0
})

const index = ref(0)
const touchDeltaX = ref(0)
let touchStartX = 0
let dragging = false

const count = computed(() => props.photos.length)
const current = computed(() => props.photos[index.value] || null)
const canPrev = computed(() => index.value > 0)
const canNext = computed(() => index.value < count.value - 1)

watch(
  () => [open.value, props.startIndex, props.photos] as const,
  ([isOpen, start]) => {
    if (!isOpen) return
    const max = Math.max(props.photos.length - 1, 0)
    index.value = Math.min(Math.max(start || 0, 0), max)
    touchDeltaX.value = 0
  }
)

function close() {
  open.value = false
}

function go(delta: number) {
  const next = index.value + delta
  if (next < 0 || next >= count.value) return
  index.value = next
  touchDeltaX.value = 0
}

function onTouchStart(e: TouchEvent) {
  if (count.value <= 1) return
  dragging = true
  touchStartX = e.touches[0]?.clientX ?? 0
  touchDeltaX.value = 0
}

function onTouchMove(e: TouchEvent) {
  if (!dragging) return
  touchDeltaX.value = (e.touches[0]?.clientX ?? 0) - touchStartX
}

function onTouchEnd() {
  if (!dragging) return
  dragging = false
  if (Math.abs(touchDeltaX.value) > 56) {
    go(touchDeltaX.value < 0 ? 1 : -1)
  }
  touchDeltaX.value = 0
}

function onKey(e: KeyboardEvent) {
  if (!open.value) return
  if (e.key === 'Escape') close()
  if (e.key === 'ArrowLeft') go(-1)
  if (e.key === 'ArrowRight') go(1)
}

onMounted(() => {
  window.addEventListener('keydown', onKey)
})
onUnmounted(() => {
  window.removeEventListener('keydown', onKey)
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open && photos.length"
      class="fixed inset-0 z-50 flex flex-col bg-black/90"
      role="dialog"
      aria-modal="true"
      aria-label="Photo gallery"
    >
      <div class="flex shrink-0 items-center justify-between gap-2 px-3 pt-[max(0.75rem,env(safe-area-inset-top))] pb-2">
        <p class="text-sm font-medium text-white/90">
          {{ index + 1 }} / {{ count }}
        </p>
        <button
          type="button"
          class="inline-flex h-10 w-10 items-center justify-center rounded-full text-white hover:bg-white/10"
          aria-label="Close"
          @click="close"
        >
          <UIcon name="i-lucide-x" class="h-6 w-6" />
        </button>
      </div>

      <div
        class="relative min-h-0 flex-1 touch-pan-y select-none"
        @touchstart.passive="onTouchStart"
        @touchmove.passive="onTouchMove"
        @touchend="onTouchEnd"
        @click.self="close"
      >
        <div class="flex h-full items-center justify-center px-10">
          <img
            v-if="current"
            :src="current"
            alt=""
            class="max-h-full max-w-full rounded-lg object-contain transition-transform duration-150"
            :style="Math.abs(touchDeltaX) > 4
              ? { transform: `translateX(${touchDeltaX * 0.35}px)` }
              : undefined"
            draggable="false"
            @click.stop
          >
        </div>

        <button
          v-if="canPrev"
          type="button"
          class="absolute left-1 top-1/2 inline-flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full bg-black/40 text-white hover:bg-black/60"
          aria-label="Previous photo"
          @click.stop="go(-1)"
        >
          <UIcon name="i-lucide-chevron-left" class="h-7 w-7" />
        </button>
        <button
          v-if="canNext"
          type="button"
          class="absolute right-1 top-1/2 inline-flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full bg-black/40 text-white hover:bg-black/60"
          aria-label="Next photo"
          @click.stop="go(1)"
        >
          <UIcon name="i-lucide-chevron-right" class="h-7 w-7" />
        </button>
      </div>

      <div
        v-if="count > 1"
        class="flex shrink-0 justify-center gap-1.5 px-4 pb-[max(1rem,env(safe-area-inset-bottom))] pt-2"
      >
        <span
          v-for="(_, i) in photos"
          :key="i"
          class="h-1.5 w-1.5 rounded-full transition-colors"
          :class="i === index ? 'bg-white' : 'bg-white/35'"
        />
      </div>
    </div>
  </Teleport>
</template>
