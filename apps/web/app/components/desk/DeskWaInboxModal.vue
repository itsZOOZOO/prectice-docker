<script setup lang="ts">
withDefaults(defineProps<{
  open: boolean
  title?: string
  bodyClass?: string
  footerClass?: string
}>(), {
  title: '',
  bodyClass: 'p-4',
  footerClass: '',
})

const emit = defineEmits<{
  close: []
}>()

function onBackdropClick() {
  emit('close')
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-[200] flex items-center justify-center bg-black/40 p-4"
      role="presentation"
      @click="onBackdropClick"
    >
      <div
        class="flex max-h-[90vh] w-full max-w-md flex-col rounded-xl bg-white shadow-xl"
        role="dialog"
        aria-modal="true"
        @click.stop
      >
        <div class="flex shrink-0 items-center justify-between border-b border-slate-100 px-4 py-3">
          <div class="font-semibold text-slate-800">
            <slot name="title">{{ title }}</slot>
          </div>
          <button
            type="button"
            class="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
            aria-label="Close"
            @click="emit('close')"
          >
            <UIcon name="i-lucide-x" class="h-5 w-5" />
          </button>
        </div>
        <div class="min-h-0 flex-1 overflow-y-auto" :class="bodyClass">
          <slot />
        </div>
        <div
          v-if="$slots.footer"
          class="flex shrink-0 border-t border-slate-200 bg-slate-50 px-4 py-3"
          :class="footerClass"
        >
          <slot name="footer" />
        </div>
      </div>
    </div>
  </Teleport>
</template>
