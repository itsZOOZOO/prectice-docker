<script setup lang="ts">
import type { CatalogBrowseItem } from '~/components/desk/DeskTreatmentCatalogCard.vue'

definePageMeta({ layout: 'mobile' })

const { api } = useApi()

const treatments = ref<CatalogBrowseItem[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const lightbox = ref<string | null>(null)

const stats = computed(() => {
  const priceOptions = treatments.value.reduce((sum, t) => sum + t.price_options.length, 0)
  const photos = treatments.value.reduce((sum, t) => sum + t.photo_count, 0)
  const appointments = treatments.value.reduce((sum, t) => sum + t.default_appts, 0)
  return { priceOptions, photos, appointments }
})

async function load() {
  loading.value = true
  error.value = null
  try {
    treatments.value = await api<CatalogBrowseItem[]>('/treatments/catalog/browse')
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Could not load treatments'
    treatments.value = []
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="flex h-full min-h-0 flex-col bg-[#F0F4F8]">
    <header class="shrink-0 border-b border-slate-200 bg-white px-4 py-4">
      <div class="flex items-start justify-between gap-3">
        <div>
          <h1 class="text-lg font-semibold text-[#1C2B35]">
            Treatments Catalog
          </h1>
          <p class="mt-0.5 text-xs text-slate-500">
            Browse treatments with pricing and photos
          </p>
        </div>
        <button
          type="button"
          class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-[#0097A7] hover:bg-slate-100 disabled:opacity-50"
          aria-label="Refresh catalog"
          :disabled="loading"
          @click="load"
        >
          <UIcon name="i-lucide-refresh-cw" class="h-5 w-5" :class="loading ? 'animate-spin' : ''" />
        </button>
      </div>
      <span
        v-if="!loading && !error"
        class="mt-2 inline-flex rounded-full bg-[#e0f7fa] px-2.5 py-0.5 text-xs font-semibold text-[#00838f]"
      >
        {{ treatments.length }} available
      </span>
    </header>

    <main class="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-4 pb-24">
      <div
        v-if="loading"
        class="flex items-center justify-center gap-2 py-16 text-sm text-slate-400"
      >
        <span class="inline-block h-5 w-5 animate-spin rounded-full border-2 border-[#b2ebf2] border-t-[#0097A7]" />
        Loading treatments…
      </div>

      <div
        v-else-if="error"
        class="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-center text-sm text-red-700"
      >
        <p>{{ error }}</p>
        <button
          type="button"
          class="mt-2 rounded-lg border border-red-300 px-3 py-1 text-xs font-medium"
          @click="load"
        >
          Retry
        </button>
      </div>

      <div
        v-else-if="!treatments.length"
        class="rounded-2xl border border-slate-200 bg-white px-4 py-12 text-center shadow-sm"
      >
        <UIcon name="i-lucide-package" class="mx-auto h-12 w-12 text-slate-300" />
        <p class="mt-3 text-sm font-medium text-slate-600">
          No treatments available
        </p>
        <p class="mt-1 text-xs text-slate-400">
          Treatments appear here once added and activated in the catalog
        </p>
      </div>

      <template v-else>
        <DeskTreatmentCatalogCard
          v-for="t in treatments"
          :key="t.id"
          :treatment="t"
          @open-photo="lightbox = $event"
        />

        <section class="grid grid-cols-2 gap-2 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div class="text-center">
            <p class="text-xl font-bold text-[#0097A7]">
              {{ treatments.length }}
            </p>
            <p class="text-xs text-slate-500">
              Treatments
            </p>
          </div>
          <div class="text-center">
            <p class="text-xl font-bold text-emerald-600">
              {{ stats.priceOptions }}
            </p>
            <p class="text-xs text-slate-500">
              Price options
            </p>
          </div>
          <div class="text-center">
            <p class="text-xl font-bold text-sky-600">
              {{ stats.photos }}
            </p>
            <p class="text-xs text-slate-500">
              Photos
            </p>
          </div>
          <div class="text-center">
            <p class="text-xl font-bold text-amber-600">
              {{ stats.appointments }}
            </p>
            <p class="text-xs text-slate-500">
              Appts (est.)
            </p>
          </div>
        </section>
      </template>
    </main>

    <div
      v-if="lightbox"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
      @click="lightbox = null"
    >
      <img
        :src="lightbox"
        alt=""
        class="max-h-full max-w-full rounded-lg object-contain"
        @click.stop
      >
    </div>
  </div>
</template>
