<script setup lang="ts">
const open = defineModel<boolean>('open', { default: false })

const emit = defineEmits<{
  unlocked: []
}>()

const { unlock } = useSetupAccess()
const toast = useToast()

const pin = ref('')
const submitting = ref(false)
const error = ref('')

watch(open, (v) => {
  if (v) {
    pin.value = ''
    error.value = ''
  }
})

async function submit() {
  const value = pin.value.trim()
  if (value.length < 4) {
    error.value = 'Enter your 4–6 digit setup PIN.'
    return
  }
  submitting.value = true
  error.value = ''
  try {
    await unlock(value)
    toast.add({ title: 'Setup unlocked', color: 'success' })
    open.value = false
    emit('unlocked')
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Unlock failed'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <UModal v-model:open="open" title="Unlock setup">
    <template #body>
      <form class="space-y-4" @submit.prevent="submit">
        <p class="text-sm text-slate-600">
          Enter the clinic setup PIN to unlock protected desk areas.
        </p>
        <UFormField label="Setup PIN" required>
          <UInput
            v-model="pin"
            type="password"
            inputmode="numeric"
            autocomplete="one-time-code"
            maxlength="6"
            placeholder="••••"
            class="w-full"
            autofocus
          />
        </UFormField>
        <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
        <div class="flex justify-end gap-2 pt-1">
          <UButton color="neutral" variant="ghost" type="button" @click="open = false">
            Cancel
          </UButton>
          <UButton
            type="submit"
            :loading="submitting"
            class="bg-[#0097A7] hover:bg-[#00838f]"
          >
            Unlock
          </UButton>
        </div>
      </form>
    </template>
  </UModal>
</template>
