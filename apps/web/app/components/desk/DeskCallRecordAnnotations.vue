<script setup lang="ts">
import type { CallTag } from '~/utils/callStatistics'

const props = defineProps<{
  callId: number
  tags: CallTag[]
  allTags: CallTag[]
  note: string | null
}>()

const emit = defineEmits<{
  'update:tags': [tags: CallTag[]]
  'update:allTags': [tags: CallTag[]]
  'update:note': [note: string | null]
}>()

const { api } = useApi()
const toast = useToast()

const menuOpen = ref(false)
const tagModalOpen = ref(false)
const noteOpen = ref(false)
const newTagName = ref('')
const newTagColor = ref('#0d6efd')
const noteDraft = ref('')
const busy = ref(false)
const menuRef = ref<HTMLElement | null>(null)

watch(noteOpen, (v) => {
  if (v) noteDraft.value = props.note || ''
})

function onPointerDown(event: MouseEvent) {
  if (menuRef.value && !menuRef.value.contains(event.target as Node)) {
    menuOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('mousedown', onPointerDown)
})

onBeforeUnmount(() => {
  document.removeEventListener('mousedown', onPointerDown)
})

const availableTags = computed(() =>
  props.allTags.filter(t => !props.tags.some(x => x.id === t.id))
)

async function addTag(tag: CallTag) {
  if (props.tags.some(t => t.id === tag.id)) {
    menuOpen.value = false
    return
  }
  busy.value = true
  try {
    await api(`/statistics/call-intelligence/calls/${props.callId}/tags`, {
      method: 'POST',
      body: { tag_id: tag.id }
    })
    emit('update:tags', [...props.tags, tag].sort((a, b) => a.name.localeCompare(b.name)))
    menuOpen.value = false
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Could not add tag', color: 'error' })
  } finally {
    busy.value = false
  }
}

async function removeTag(tagId: number) {
  busy.value = true
  try {
    await api(`/statistics/call-intelligence/calls/${props.callId}/tags/${tagId}`, {
      method: 'DELETE'
    })
    emit('update:tags', props.tags.filter(t => t.id !== tagId))
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Could not remove tag', color: 'error' })
  } finally {
    busy.value = false
  }
}

async function createTag() {
  const name = newTagName.value.trim()
  if (!name) return
  busy.value = true
  try {
    const data = await api<{ tag: CallTag }>('/statistics/call-intelligence/tags', {
      method: 'POST',
      body: { name, color: newTagColor.value }
    })
    const tag = data.tag
    emit('update:allTags', [...props.allTags, tag].sort((a, b) => a.name.localeCompare(b.name)))
    await addTag(tag)
    tagModalOpen.value = false
    newTagName.value = ''
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Could not create tag', color: 'error' })
  } finally {
    busy.value = false
  }
}

async function saveNote() {
  busy.value = true
  try {
    await api(`/statistics/call-intelligence/calls/${props.callId}/note`, {
      method: 'PUT',
      body: { note: noteDraft.value }
    })
    emit('update:note', noteDraft.value.trim() || null)
    noteOpen.value = false
  } catch (e: unknown) {
    toast.add({ title: e instanceof Error ? e.message : 'Could not save note', color: 'error' })
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="space-y-1.5">
    <div class="flex flex-wrap items-center gap-1">
      <span
        v-for="tag in tags"
        :key="tag.id"
        class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium text-white"
        :style="{ backgroundColor: tag.color || '#6c757d' }"
      >
        {{ tag.name }}
        <button
          type="button"
          class="opacity-80 hover:opacity-100"
          :disabled="busy"
          @click="removeTag(tag.id)"
        >
          ×
        </button>
      </span>
      <div ref="menuRef" class="relative">
        <button
          type="button"
          class="rounded-md border border-slate-200 px-1.5 py-0.5 text-[11px] text-slate-600 hover:bg-slate-50"
          :disabled="busy"
          @click="menuOpen = !menuOpen"
        >
          + Tag
        </button>
        <div
          v-if="menuOpen"
          class="absolute left-0 z-20 mt-1 max-h-48 w-44 overflow-y-auto rounded-lg border border-slate-200 bg-white py-1 shadow-lg"
        >
          <button
            v-for="tag in availableTags"
            :key="tag.id"
            type="button"
            class="flex w-full items-center gap-2 px-2 py-1.5 text-left text-xs hover:bg-slate-50"
            @click="addTag(tag)"
          >
            <span class="h-2.5 w-2.5 rounded-full" :style="{ background: tag.color }" />
            {{ tag.name }}
          </button>
          <button
            type="button"
            class="w-full border-t border-slate-100 px-2 py-1.5 text-left text-xs font-semibold text-[#0097A7]"
            @click="tagModalOpen = true; menuOpen = false"
          >
            Create tag…
          </button>
        </div>
      </div>
      <button
        type="button"
        class="rounded-md border border-slate-200 px-1.5 py-0.5 text-[11px] text-slate-600 hover:bg-slate-50"
        @click="noteOpen = !noteOpen"
      >
        Note
      </button>
    </div>
    <p v-if="note && !noteOpen" class="text-[11px] text-slate-500">{{ note }}</p>
    <div v-if="noteOpen" class="space-y-1">
      <textarea
        v-model="noteDraft"
        rows="2"
        class="w-full rounded-md border border-slate-200 px-2 py-1 text-xs"
        placeholder="Call note…"
      />
      <div class="flex gap-1">
        <button
          type="button"
          class="rounded-md bg-[#0097A7] px-2 py-1 text-[11px] font-semibold text-white"
          :disabled="busy"
          @click="saveNote"
        >
          Save
        </button>
        <button
          type="button"
          class="rounded-md border border-slate-200 px-2 py-1 text-[11px]"
          @click="noteOpen = false"
        >
          Cancel
        </button>
      </div>
    </div>

    <div
      v-if="tagModalOpen"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4"
      @click.self="tagModalOpen = false"
    >
      <div class="w-full max-w-sm rounded-xl bg-white p-4 shadow-xl">
        <h4 class="text-sm font-semibold text-slate-800">Create tag</h4>
        <label class="mt-3 block text-xs font-medium text-slate-600">
          Name
          <input v-model="newTagName" class="mt-1 w-full rounded-md border border-slate-200 px-2 py-1.5 text-sm">
        </label>
        <label class="mt-2 block text-xs font-medium text-slate-600">
          Color
          <input v-model="newTagColor" type="color" class="mt-1 h-9 w-full cursor-pointer rounded-md border border-slate-200">
        </label>
        <div class="mt-3 flex justify-end gap-2">
          <button type="button" class="rounded-md border border-slate-200 px-3 py-1.5 text-xs" @click="tagModalOpen = false">Cancel</button>
          <button
            type="button"
            class="rounded-md bg-[#0097A7] px-3 py-1.5 text-xs font-semibold text-white"
            :disabled="busy"
            @click="createTag"
          >
            Create
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
