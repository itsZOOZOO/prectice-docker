<script setup lang="ts">
defineProps<{
  minutesRemaining?: number | null
  busy?: boolean
}>()

const emit = defineEmits<{
  lock: []
}>()
</script>

<template>
  <div
    class="flex flex-wrap items-center justify-between gap-2 border-b border-amber-200 bg-amber-50 px-5 py-2 text-sm text-amber-950"
  >
    <div class="flex items-center gap-2">
      <UIcon
        name="i-lucide-lock-open"
        class="h-4 w-4 shrink-0 text-amber-700"
      />
      <span>
        Clinic setup unlocked
        <template v-if="minutesRemaining != null">
          · about {{ minutesRemaining }} min left
        </template>
      </span>
    </div>
    <button
      type="button"
      class="rounded-md border border-amber-300 bg-white px-3 py-1 text-xs font-semibold text-amber-900 hover:bg-amber-100 disabled:opacity-60"
      :disabled="busy"
      @click="emit('lock')"
    >
      Lock now
    </button>
  </div>
</template>
