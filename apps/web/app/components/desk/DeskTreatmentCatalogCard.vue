<script setup lang="ts">
export type CatalogPriceOption = {
  id: number
  label: string
  price: number
  explainer: string | null
  is_foc: boolean
  photos: string[]
}

export type CatalogBrowseItem = {
  id: number
  name: string
  short_explainer: string | null
  default_appts: number
  photos: string[]
  all_photos: string[]
  photo_count: number
  price_options: CatalogPriceOption[]
  price_count: number
  min_price: number | null
  max_price: number | null
}

const props = defineProps<{
  treatment: CatalogBrowseItem
}>()

const emit = defineEmits<{
  openPhoto: [payload: { photos: string[], index: number }]
}>()

const pricingOpen = ref(false)

const galleryPhotos = computed(() => {
  if (props.treatment.all_photos.length) return props.treatment.all_photos
  return props.treatment.photos
})

const heroPhoto = computed(
  () => props.treatment.photos[0] ?? props.treatment.all_photos[0] ?? null
)

function openAt(url: string) {
  const photos = galleryPhotos.value
  if (!photos.length) return
  const index = Math.max(0, photos.indexOf(url))
  emit('openPhoto', { photos, index: index === -1 ? 0 : index })
}

function openHero() {
  if (!heroPhoto.value) return
  openAt(heroPhoto.value)
}

function formatInr(n: number) {
  return `₹${Number(n).toLocaleString('en-IN')}`
}

function formatPriceRange(min: number, max: number) {
  if (min === max) return formatInr(min)
  return `${formatInr(min)} – ${formatInr(max)}`
}
</script>

<template>
  <article class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
    <div class="relative h-48 overflow-hidden bg-gradient-to-br from-[#0097A7] to-[#006978]">
      <button
        v-if="heroPhoto"
        type="button"
        class="block h-full w-full"
        @click="openHero"
      >
        <img
          :src="heroPhoto"
          :alt="treatment.name"
          class="h-full w-full object-cover"
          loading="lazy"
        >
      </button>
      <div
        v-else
        class="flex h-full items-center justify-center text-white/80"
      >
        <UIcon name="i-lucide-stethoscope" class="h-12 w-12" />
      </div>
      <span
        v-if="treatment.photo_count > 1"
        class="pointer-events-none absolute right-2 top-2 inline-flex items-center gap-1 rounded-full bg-black/65 px-2 py-0.5 text-xs font-medium text-white"
      >
        <UIcon name="i-lucide-images" class="h-3.5 w-3.5" />
        {{ treatment.photo_count }}
      </span>
    </div>

    <div
      v-if="treatment.all_photos.length > 1"
      class="flex gap-2 overflow-x-auto border-b border-slate-100 px-4 py-2 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
    >
      <button
        v-for="(url, index) in treatment.all_photos"
        :key="`${url}-${index}`"
        type="button"
        class="block h-14 w-14 shrink-0 overflow-hidden rounded-lg border-2 border-slate-200"
        @click="openAt(url)"
      >
        <img
          :src="url"
          :alt="`${treatment.name} photo ${index + 1}`"
          class="h-full w-full object-cover"
          loading="lazy"
        >
      </button>
    </div>

    <div class="p-4">
      <h2 class="text-base font-semibold text-[#1C2B35]">
        {{ treatment.name }}
      </h2>
      <p
        v-if="treatment.short_explainer"
        class="mt-1 text-sm text-slate-500"
      >
        {{ treatment.short_explainer }}
      </p>
      <span
        v-if="treatment.default_appts > 0"
        class="mt-2 inline-flex items-center gap-1 rounded-full bg-[#e0f7fa] px-2.5 py-0.5 text-xs font-medium text-[#00838f]"
      >
        <UIcon name="i-lucide-calendar-check" class="h-3.5 w-3.5" />
        ~{{ treatment.default_appts }} appointment{{ treatment.default_appts === 1 ? '' : 's' }}
      </span>

      <div
        v-if="treatment.price_count > 0 && treatment.min_price != null"
        class="mt-3 overflow-hidden rounded-xl border border-slate-200"
      >
        <button
          type="button"
          class="flex w-full items-center gap-2 bg-[#f0fdfa] px-3 py-2.5 text-left"
          :aria-expanded="pricingOpen"
          @click="pricingOpen = !pricingOpen"
        >
          <div class="min-w-0 flex-1">
            <p class="text-[10px] font-semibold uppercase tracking-wide text-[#0097A7]">
              Price range
            </p>
            <p class="text-sm font-bold text-[#00838f]">
              {{ formatPriceRange(treatment.min_price, treatment.max_price ?? treatment.min_price) }}
            </p>
          </div>
          <span class="shrink-0 rounded-full bg-white/80 px-2 py-0.5 text-[10px] font-semibold text-[#00838f]">
            {{ treatment.price_options.length }} option{{ treatment.price_options.length === 1 ? '' : 's' }}
          </span>
          <UIcon
            name="i-lucide-chevron-down"
            class="h-5 w-5 shrink-0 text-[#0097A7] transition-transform"
            :class="pricingOpen ? 'rotate-180' : ''"
          />
        </button>

        <div
          v-if="pricingOpen && treatment.price_options.length"
          class="space-y-2 border-t border-slate-200 bg-white p-3"
        >
          <div
            v-for="option in treatment.price_options"
            :key="option.id"
            class="rounded-lg border-l-4 border-[#0097A7] bg-slate-50 px-3 py-2"
          >
            <div class="flex items-start justify-between gap-2">
              <p class="text-sm font-semibold text-[#1C2B35]">
                {{ option.label }}
              </p>
              <p class="shrink-0 text-sm font-bold text-emerald-700">
                {{ option.is_foc ? 'FOC' : formatInr(option.price) }}
              </p>
            </div>
            <p
              v-if="option.explainer"
              class="mt-0.5 text-xs text-slate-500"
            >
              {{ option.explainer }}
            </p>
            <span
              v-if="option.photos.length"
              class="mt-1 inline-flex items-center gap-0.5 rounded bg-slate-200 px-1.5 py-0.5 text-[10px] font-medium text-slate-600"
            >
              <UIcon name="i-lucide-image" class="h-3 w-3" />
              {{ option.photos.length }} photo{{ option.photos.length === 1 ? '' : 's' }}
            </span>
          </div>
        </div>
      </div>
      <p
        v-else
        class="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800"
      >
        No pricing options available
      </p>
    </div>
  </article>
</template>
