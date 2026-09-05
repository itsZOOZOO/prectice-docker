<script setup lang="ts">
type TagRow = { client_tag_id: number, tag_name: string }

const { api } = useApi()
const toast = useToast()

const tags = ref<TagRow[]>([])
const loading = ref(false)
const saving = ref(false)
const formOpen = ref(false)
const editingId = ref<number | null>(null)
const tagName = ref('')

async function load() {
  loading.value = true
  try {
    const data = await api<{ tags: TagRow[] }>('/settings/client-tags')
    tags.value = data.tags || []
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed to load tags', color: 'error' })
  } finally {
    loading.value = false
  }
}

function openNew() {
  editingId.value = null
  tagName.value = ''
  formOpen.value = true
}

function openEdit(tag: TagRow) {
  editingId.value = tag.client_tag_id
  tagName.value = tag.tag_name
  formOpen.value = true
}

async function save() {
  const name = tagName.value.trim()
  if (!name) {
    toast.add({ title: 'Tag name required', color: 'warning' })
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await api(`/settings/client-tags/${editingId.value}`, {
        method: 'PATCH',
        body: { tag_name: name }
      })
      toast.add({ title: 'Tag updated', color: 'success' })
    } else {
      await api('/settings/client-tags', {
        method: 'POST',
        body: { tag_name: name }
      })
      toast.add({ title: 'Tag added', color: 'success' })
    }
    formOpen.value = false
    await load()
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
  } finally {
    saving.value = false
  }
}

async function removeTag(tag: TagRow) {
  if (!window.confirm(`Delete tag “${tag.tag_name}”?\n\nIt will be removed from all patients.`)) return
  try {
    await api(`/settings/client-tags/${tag.client_tag_id}`, { method: 'DELETE' })
    toast.add({ title: 'Tag deleted', color: 'success' })
    await load()
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Failed', color: 'error' })
  }
}

onMounted(() => { void load() })
</script>

<template>
  <div class="flex h-full min-h-0 flex-col">
    <div class="flex shrink-0 items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
      <p class="text-sm text-slate-500">
        Tags you can assign on patient profiles. Used by patient list filters.
      </p>
      <UButton class="bg-[#0097A7]" @click="openNew">
        Add tag
      </UButton>
    </div>

    <div class="min-h-0 flex-1 overflow-y-auto p-4">
      <p v-if="loading" class="text-sm text-slate-400">Loading…</p>
      <p v-else-if="!tags.length" class="text-sm text-slate-400">No tags yet.</p>
      <ul v-else class="divide-y divide-slate-100 rounded-xl border border-slate-200 bg-white">
        <li
          v-for="tag in tags"
          :key="tag.client_tag_id"
          class="flex items-center justify-between gap-3 px-4 py-3"
        >
          <span class="text-sm font-medium text-slate-800">{{ tag.tag_name }}</span>
          <div class="flex gap-2">
            <button
              type="button"
              class="text-xs font-semibold text-[#0097A7] hover:underline"
              @click="openEdit(tag)"
            >
              Edit
            </button>
            <button
              type="button"
              class="text-xs font-semibold text-red-600 hover:underline"
              @click="removeTag(tag)"
            >
              Delete
            </button>
          </div>
        </li>
      </ul>
    </div>

    <UModal v-model:open="formOpen" :title="editingId ? 'Edit tag' : 'Add tag'">
      <template #body>
        <form class="space-y-4" @submit.prevent="save">
          <UFormField label="Tag name" required>
            <UInput v-model="tagName" class="w-full" autofocus placeholder="e.g. HNI" />
          </UFormField>
          <div class="flex justify-end gap-2">
            <UButton color="neutral" variant="ghost" type="button" @click="formOpen = false">
              Cancel
            </UButton>
            <UButton type="submit" class="bg-[#0097A7]" :loading="saving">
              {{ editingId ? 'Save' : 'Add' }}
            </UButton>
          </div>
        </form>
      </template>
    </UModal>
  </div>
</template>
