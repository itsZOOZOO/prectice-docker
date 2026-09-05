<script setup lang="ts">
type WarrantyKind = 'card-types' | 'products' | 'terms' | 'benefits'

type WarrantyTemplateItem = {
  id: number
  name: string
  note: string
  detail?: string
}

type IssuedCard = {
  id: number
  card_id: number
  client_id: number
  client_name: string
  product: string
  product_name: string
  type: string
  type_name: string
  unique_code: string
  date_of_purchase: string
  benefit_start_date: string
  benefit_end_date: string
  number_of_units: number | null
  warranty_period: string | null
}

type TemplateTab = WarrantyKind | 'issued'

const TEMPLATE_TABS: Array<{ key: TemplateTab, label: string }> = [
  { key: 'card-types', label: 'Card types' },
  { key: 'products', label: 'Products' },
  { key: 'terms', label: 'Terms' },
  { key: 'benefits', label: 'Benefits' },
  { key: 'issued', label: 'Issued' }
]

const KIND_LABELS: Record<WarrantyKind, string> = {
  'card-types': 'card type',
  products: 'product',
  terms: 'term',
  benefits: 'benefit'
}

const { api } = useApi()
const toast = useToast()

const tab = ref<TemplateTab>('card-types')
const loading = ref(false)
const saving = ref(false)
const error = ref('')

const templates = ref<Record<WarrantyKind, WarrantyTemplateItem[]>>({
  'card-types': [],
  products: [],
  terms: [],
  benefits: []
})

const issuedCards = ref<IssuedCard[]>([])
const issuedSearch = ref('')
const issuedLoaded = ref(false)

const formOpen = ref(false)
const editingId = ref<number | null>(null)
const formError = ref('')
const form = reactive({
  name: '',
  note: '',
  detail: ''
})

const isTemplateTab = computed(() => tab.value !== 'issued')
const activeKind = computed<WarrantyKind | null>(() =>
  tab.value === 'issued' ? null : tab.value
)

const currentItems = computed(() => {
  if (!activeKind.value) return []
  return templates.value[activeKind.value] ?? []
})

const needsDetail = computed(() =>
  activeKind.value === 'terms' || activeKind.value === 'benefits'
)

async function loadTemplates() {
  loading.value = true
  error.value = ''
  try {
    const data = await api<{
      templates: {
        'card-types': WarrantyTemplateItem[]
        products: WarrantyTemplateItem[]
        terms: WarrantyTemplateItem[]
        benefits: WarrantyTemplateItem[]
      }
    }>('/settings/warranty-templates')
    templates.value = {
      'card-types': data.templates?.['card-types'] ?? [],
      products: data.templates?.products ?? [],
      terms: data.templates?.terms ?? [],
      benefits: data.templates?.benefits ?? []
    }
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to load templates'
    toast.add({ title: error.value, color: 'error' })
  } finally {
    loading.value = false
  }
}

async function loadIssued() {
  loading.value = true
  error.value = ''
  try {
    const data = await api<{ cards: IssuedCard[] }>('/settings/issued-warranty-cards', {
      query: { q: issuedSearch.value.trim() || undefined }
    })
    issuedCards.value = data.cards ?? []
    issuedLoaded.value = true
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to load issued cards'
    toast.add({ title: error.value, color: 'error' })
  } finally {
    loading.value = false
  }
}

watch(tab, (next) => {
  if (next === 'issued') {
    if (!issuedLoaded.value) void loadIssued()
  }
})

function resetForm() {
  editingId.value = null
  form.name = ''
  form.note = ''
  form.detail = ''
  formError.value = ''
}

function openNew() {
  resetForm()
  formOpen.value = true
}

function openEdit(item: WarrantyTemplateItem) {
  editingId.value = item.id
  form.name = item.name
  form.note = item.note ?? ''
  form.detail = item.detail ?? ''
  formError.value = ''
  formOpen.value = true
}

async function saveItem() {
  const kind = activeKind.value
  if (!kind) return
  if (!form.name.trim()) {
    formError.value = 'Name is required.'
    return
  }
  saving.value = true
  formError.value = ''
  const payload: { name: string, note: string | null, detail?: string | null } = {
    name: form.name.trim(),
    note: form.note.trim() || null
  }
  if (needsDetail.value) {
    payload.detail = form.detail.trim() || null
  }
  try {
    if (editingId.value != null) {
      const saved = await api<WarrantyTemplateItem>(
        `/settings/warranty-templates/${kind}/${editingId.value}`,
        { method: 'PATCH', body: payload }
      )
      templates.value[kind] = templates.value[kind].map(i =>
        i.id === editingId.value ? saved : i
      )
      toast.add({ title: 'Template updated', color: 'success' })
    } else {
      const saved = await api<WarrantyTemplateItem>(
        `/settings/warranty-templates/${kind}`,
        { method: 'POST', body: payload }
      )
      templates.value[kind] = [...templates.value[kind], saved].sort((a, b) =>
        a.name.localeCompare(b.name)
      )
      toast.add({ title: 'Template added', color: 'success' })
    }
    formOpen.value = false
    resetForm()
  } catch (e: unknown) {
    formError.value = e instanceof Error ? e.message : 'Failed to save'
  } finally {
    saving.value = false
  }
}

async function deleteItem(item: WarrantyTemplateItem) {
  const kind = activeKind.value
  if (!kind) return
  if (!window.confirm(`Delete “${item.name}”?`)) return
  try {
    await api(`/settings/warranty-templates/${kind}/${item.id}`, { method: 'DELETE' })
    templates.value[kind] = templates.value[kind].filter(i => i.id !== item.id)
    toast.add({ title: 'Template deleted', color: 'success' })
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to delete', color: 'error' })
  }
}

function formatDate(iso: string) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    })
  } catch {
    return iso.slice(0, 10)
  }
}

let issuedSearchTimer: ReturnType<typeof setTimeout> | null = null
watch(issuedSearch, () => {
  if (tab.value !== 'issued') return
  if (issuedSearchTimer) clearTimeout(issuedSearchTimer)
  issuedSearchTimer = setTimeout(() => {
    void loadIssued()
  }, 300)
})

onMounted(() => {
  void loadTemplates()
})
</script>

<template>
  <div class="p-4 md:p-5">
    <div class="mb-4 flex max-w-3xl gap-1 overflow-x-auto rounded-lg bg-slate-100 p-1">
      <button
        v-for="entry in TEMPLATE_TABS"
        :key="entry.key"
        type="button"
        class="shrink-0 rounded-md px-3 py-2 text-sm font-medium transition"
        :class="tab === entry.key
          ? 'bg-white text-[#0097A7] shadow-sm'
          : 'text-slate-600 hover:text-slate-800'"
        @click="tab = entry.key"
      >
        {{ entry.label }}
      </button>
    </div>

    <div
      v-if="error"
      class="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
    >
      {{ error }}
    </div>

    <!-- Template kinds -->
    <template v-if="isTemplateTab && activeKind">
      <div class="mb-4 flex flex-wrap items-center justify-end gap-3">
        <UButton size="sm" class="bg-[#0097A7]" @click="openNew">
          Add {{ KIND_LABELS[activeKind] }}
        </UButton>
      </div>

      <div class="rounded-xl border border-slate-200 bg-white shadow-sm">
        <p v-if="loading" class="px-4 py-8 text-center text-sm text-slate-400">
          Loading…
        </p>
        <ul v-else class="divide-y divide-slate-100">
          <li v-if="!currentItems.length" class="py-8 text-center text-sm text-slate-500">
            No {{ KIND_LABELS[activeKind] }}s yet.
          </li>
          <li
            v-for="item in currentItems"
            :key="item.id"
            class="flex flex-wrap items-start justify-between gap-3 px-4 py-3 hover:bg-slate-50"
          >
            <div class="min-w-0">
              <p class="text-sm font-medium text-slate-800">{{ item.name }}</p>
              <p v-if="item.note" class="mt-0.5 text-xs text-slate-500">{{ item.note }}</p>
              <p
                v-if="needsDetail && item.detail"
                class="mt-1 text-xs text-slate-400 line-clamp-2"
              >
                {{ item.detail }}
              </p>
            </div>
            <div class="flex shrink-0 gap-2">
              <UButton size="xs" color="neutral" variant="outline" @click="openEdit(item)">
                Edit
              </UButton>
              <UButton size="xs" color="error" variant="ghost" @click="deleteItem(item)">
                Delete
              </UButton>
            </div>
          </li>
        </ul>
      </div>
    </template>

    <!-- Issued cards -->
    <template v-else>
      <div class="mb-4">
        <UInput
          v-model="issuedSearch"
          class="w-full max-w-sm"
          placeholder="Search by client, code, type…"
        />
      </div>

      <div class="rounded-xl border border-slate-200 bg-white shadow-sm">
        <p v-if="loading" class="px-4 py-8 text-center text-sm text-slate-400">
          Loading issued cards…
        </p>
        <div v-else class="overflow-x-auto">
          <table class="min-w-full text-left text-sm">
            <thead class="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th class="px-4 py-3 font-semibold">Client</th>
                <th class="px-4 py-3 font-semibold">Product</th>
                <th class="px-4 py-3 font-semibold">Type</th>
                <th class="px-4 py-3 font-semibold">Code</th>
                <th class="px-4 py-3 font-semibold">Purchase</th>
                <th class="px-4 py-3 font-semibold">Benefit period</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!issuedCards.length">
                <td colspan="6" class="px-4 py-8 text-center text-slate-500">
                  No issued warranty cards found.
                </td>
              </tr>
              <tr
                v-for="card in issuedCards"
                :key="card.id"
                class="border-t border-slate-100 hover:bg-slate-50"
              >
                <td class="px-4 py-3 font-medium text-slate-800">
                  {{ card.client_name || '—' }}
                </td>
                <td class="px-4 py-3 text-slate-600">
                  {{ card.product_name || card.product || '—' }}
                </td>
                <td class="px-4 py-3 text-slate-600">
                  {{ card.type_name || card.type || '—' }}
                </td>
                <td class="px-4 py-3 font-mono text-xs text-slate-700">
                  {{ card.unique_code || '—' }}
                </td>
                <td class="px-4 py-3 text-slate-600">
                  {{ formatDate(card.date_of_purchase) }}
                </td>
                <td class="px-4 py-3 text-slate-600">
                  {{ formatDate(card.benefit_start_date) }}
                  –
                  {{ formatDate(card.benefit_end_date) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <UModal
      v-model:open="formOpen"
      :title="editingId != null
        ? `Edit ${activeKind ? KIND_LABELS[activeKind] : 'template'}`
        : `Add ${activeKind ? KIND_LABELS[activeKind] : 'template'}`"
    >
      <template #body>
        <form class="space-y-3" @submit.prevent="saveItem">
          <UFormField label="Name *" required>
            <UInput v-model="form.name" class="w-full" required />
          </UFormField>
          <UFormField label="Note">
            <UInput v-model="form.note" class="w-full" />
          </UFormField>
          <UFormField v-if="needsDetail" label="Detail">
            <UTextarea v-model="form.detail" class="w-full" :rows="4" />
          </UFormField>
          <p v-if="formError" class="text-sm text-red-600">{{ formError }}</p>
          <div class="flex justify-end gap-2">
            <UButton color="neutral" variant="ghost" type="button" @click="formOpen = false">
              Cancel
            </UButton>
            <UButton type="submit" class="bg-[#0097A7]" :loading="saving">
              Save
            </UButton>
          </div>
        </form>
      </template>
    </UModal>
  </div>
</template>
