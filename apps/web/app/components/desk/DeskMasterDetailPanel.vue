<script setup lang="ts">
export type DeskMasterItem = {
  id: string
  label: string
  description?: string
  icon?: string
  locked?: boolean
}

const props = withDefaults(defineProps<{
  items: DeskMasterItem[]
  selectedId?: string | null
  emptyMessage?: string
  hideDetailHeader?: boolean | ((itemId: string) => boolean)
}>(), {
  selectedId: null,
  emptyMessage: 'Select an item',
  hideDetailHeader: false
})

const emit = defineEmits<{
  'update:selectedId': [id: string | null]
}>()

const selected = computed(() => props.items.find(item => item.id === props.selectedId) ?? null)
const detailOpen = computed(() => props.selectedId != null)

function shouldHideHeader(itemId: string) {
  const hide = props.hideDetailHeader
  if (!hide) return false
  return typeof hide === 'function' ? hide(itemId) : hide
}

function select(id: string) {
  emit('update:selectedId', id)
}

function clearSelection() {
  emit('update:selectedId', null)
}
</script>

<template>
  <div class="flex h-full min-h-0 bg-[#f4f6f9]">
    <div
      class="h-full w-[300px] min-w-[260px] max-w-[360px] shrink-0 flex-col border-r border-slate-200 bg-white"
      :class="detailOpen ? 'hidden lg:flex' : 'flex'"
    >
      <div class="min-h-0 flex-1 overflow-y-auto">
        <button
          v-for="item in items"
          :key="item.id"
          type="button"
          class="flex w-full gap-3 border-b border-slate-100 border-l-[3px] py-3 text-left transition"
          :class="item.id === selectedId
            ? 'border-l-[#0097A7] bg-[#0097A7]/15 pl-[calc(0.875rem-3px)] pr-3.5 shadow-[inset_0_0_0_1px_rgba(0,151,167,0.12)]'
            : 'border-l-transparent px-3.5 hover:bg-slate-50'"
          @click="select(item.id)"
        >
          <span
            v-if="item.icon"
            class="mt-0.5 shrink-0 text-lg leading-none"
            :class="item.id === selectedId ? 'text-[#0097A7]' : 'text-slate-400'"
          >{{ item.icon }}</span>
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-1.5">
              <div
                class="truncate text-sm font-semibold"
                :class="item.id === selectedId ? 'text-[#006874]' : 'text-slate-800'"
              >
                {{ item.label }}
              </div>
              <span
                v-if="item.locked"
                class="shrink-0 text-[11px] text-amber-600"
                title="Locked — unlock with setup PIN"
                aria-label="Locked"
              >🔒</span>
            </div>
            <p
              v-if="item.description"
              class="mt-0.5 truncate text-xs"
              :class="item.id === selectedId ? 'text-slate-600' : 'text-slate-500'"
            >
              {{ item.description }}
            </p>
          </div>
        </button>
      </div>
    </div>

    <div
      class="min-w-0 flex-1 flex-col"
      :class="detailOpen ? 'flex' : 'hidden lg:flex'"
    >
      <div
        v-if="!detailOpen"
        class="flex h-full flex-col items-center justify-center text-slate-400"
      >
        <span class="mb-3 text-5xl opacity-20">⚙️</span>
        <p class="text-sm">{{ emptyMessage }}</p>
      </div>

      <template v-else-if="selected">
        <div
          v-if="$slots['detail-header'] || !shouldHideHeader(selected.id)"
          class="flex shrink-0 items-center gap-2 border-b border-slate-200 bg-white px-4 py-2.5"
        >
          <button
            type="button"
            class="shrink-0 rounded-md border border-slate-200 px-2 py-1 text-sm lg:hidden"
            @click="clearSelection"
          >
            ←
          </button>
          <div class="min-w-0 flex-1">
            <slot name="detail-header" :item="selected">
              <h2 class="truncate text-base font-semibold text-slate-800">{{ selected.label }}</h2>
              <p v-if="selected.description" class="truncate text-xs text-slate-500">
                {{ selected.description }}
              </p>
            </slot>
          </div>
        </div>
        <div
          v-else
          class="flex shrink-0 items-center border-b border-slate-200 bg-white px-4 py-2.5 lg:hidden"
        >
          <button
            type="button"
            class="rounded-md border border-slate-200 px-2 py-1 text-sm"
            @click="clearSelection"
          >
            ←
          </button>
        </div>

        <div class="relative min-h-0 flex-1 overflow-y-auto bg-[#F0F4F8]">
          <slot name="detail" :item-id="selected.id" :item="selected" />
        </div>
      </template>
    </div>
  </div>
</template>
