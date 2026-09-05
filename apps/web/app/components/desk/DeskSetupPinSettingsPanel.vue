<script setup lang="ts">
import { SETUP_UNLOCK_TTL_OPTIONS } from '~/utils/setupAccess'

const {
  status,
  pinConfigured,
  isUnlocked,
  expiresAt,
  fetchStatus,
  createPin,
  changePin,
  setTtl,
  lock
} = useSetupAccess()
const toast = useToast()

const loading = ref(true)
const saving = ref(false)
const error = ref('')

const createForm = reactive({ pin: '', confirm: '' })
const changeForm = reactive({ current: '', next: '', confirm: '' })
const ttlMinutes = ref(45)

onMounted(async () => {
  loading.value = true
  try {
    const data = await fetchStatus()
    ttlMinutes.value = data.unlock_ttl_minutes || 45
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to load setup access'
  } finally {
    loading.value = false
  }
})

watch(() => status.value?.unlock_ttl_minutes, (v) => {
  if (v) ttlMinutes.value = v
})

async function submitCreate() {
  saving.value = true
  error.value = ''
  try {
    await createPin(createForm.pin, createForm.confirm)
    createForm.pin = ''
    createForm.confirm = ''
    toast.add({ title: 'Setup PIN created', color: 'success' })
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to create PIN'
  } finally {
    saving.value = false
  }
}

async function submitChange() {
  saving.value = true
  error.value = ''
  try {
    await changePin(changeForm.current, changeForm.next, changeForm.confirm)
    changeForm.current = ''
    changeForm.next = ''
    changeForm.confirm = ''
    toast.add({ title: 'Setup PIN updated', color: 'success' })
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to change PIN'
  } finally {
    saving.value = false
  }
}

async function saveTtl() {
  saving.value = true
  error.value = ''
  try {
    await setTtl(ttlMinutes.value)
    toast.add({ title: 'Auto-lock duration saved', color: 'success' })
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to save duration'
  } finally {
    saving.value = false
  }
}

async function lockNow() {
  await lock()
  toast.add({ title: 'Setup locked', color: 'success' })
}

const unlockedUntilLabel = computed(() => {
  if (!isUnlocked.value || !expiresAt.value) return null
  return new Date(expiresAt.value * 1000).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit'
  })
})
</script>

<template>
  <div class="mx-auto max-w-xl space-y-5 p-5">
    <div>
      <h2 class="text-lg font-semibold text-slate-800">Setup PIN</h2>
      <p class="mt-1 text-sm text-slate-500">
        Protect sensitive clinic settings. Once set, unlock is required to edit locked sections.
      </p>
    </div>

    <p v-if="loading" class="text-sm text-slate-400">Loading…</p>
    <p v-else-if="error" class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
      {{ error }}
    </p>

    <template v-else>
      <div class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div class="flex flex-wrap items-center gap-2 text-sm">
          <span
            class="rounded-full px-2.5 py-0.5 text-xs font-semibold"
            :class="pinConfigured
              ? 'bg-emerald-50 text-emerald-700'
              : 'bg-amber-50 text-amber-700'"
          >
            {{ pinConfigured ? 'PIN configured' : 'PIN not set' }}
          </span>
          <span
            v-if="pinConfigured"
            class="rounded-full px-2.5 py-0.5 text-xs font-semibold"
            :class="isUnlocked
              ? 'bg-[#e0f7fa] text-[#006874]'
              : 'bg-slate-100 text-slate-600'"
          >
            {{ isUnlocked ? `Unlocked until ${unlockedUntilLabel}` : 'Currently locked' }}
          </span>
        </div>
      </div>

      <form
        v-if="!pinConfigured"
        class="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
        @submit.prevent="submitCreate"
      >
        <h3 class="text-sm font-semibold text-slate-800">Create setup PIN</h3>
        <p class="text-xs text-slate-500">4–6 digits. You’ll need this to edit locked settings.</p>
        <UFormField label="New PIN" required>
          <UInput
            v-model="createForm.pin"
            type="password"
            inputmode="numeric"
            maxlength="6"
            class="w-full"
          />
        </UFormField>
        <UFormField label="Confirm PIN" required>
          <UInput
            v-model="createForm.confirm"
            type="password"
            inputmode="numeric"
            maxlength="6"
            class="w-full"
          />
        </UFormField>
        <div class="flex justify-end">
          <UButton type="submit" :loading="saving" class="bg-[#0097A7] hover:bg-[#00838f]">
            Create PIN
          </UButton>
        </div>
      </form>

      <template v-else>
        <form
          class="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
          @submit.prevent="submitChange"
        >
          <h3 class="text-sm font-semibold text-slate-800">Change PIN</h3>
          <p class="text-xs text-slate-500">Requires an active unlock session.</p>
          <UFormField label="Current PIN" required>
            <UInput
              v-model="changeForm.current"
              type="password"
              inputmode="numeric"
              maxlength="6"
              class="w-full"
            />
          </UFormField>
          <UFormField label="New PIN" required>
            <UInput
              v-model="changeForm.next"
              type="password"
              inputmode="numeric"
              maxlength="6"
              class="w-full"
            />
          </UFormField>
          <UFormField label="Confirm new PIN" required>
            <UInput
              v-model="changeForm.confirm"
              type="password"
              inputmode="numeric"
              maxlength="6"
              class="w-full"
            />
          </UFormField>
          <div class="flex justify-end">
            <UButton
              type="submit"
              :loading="saving"
              :disabled="!isUnlocked"
              class="bg-[#0097A7] hover:bg-[#00838f]"
            >
              Update PIN
            </UButton>
          </div>
        </form>

        <div class="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h3 class="text-sm font-semibold text-slate-800">Auto-lock duration</h3>
          <p class="text-xs text-slate-500">
            How long setup stays unlocked after entering the PIN.
          </p>
          <label class="block">
            <span class="mb-1 block text-xs font-medium text-slate-600">Minutes</span>
            <select
              v-model.number="ttlMinutes"
              class="h-9 w-full rounded-lg border border-slate-200 bg-white px-2 text-sm outline-none focus:border-[#0097A7]"
            >
              <option v-for="m in SETUP_UNLOCK_TTL_OPTIONS" :key="m" :value="m">
                {{ m }} minutes
              </option>
            </select>
          </label>
          <div class="flex flex-wrap justify-end gap-2">
            <UButton
              color="neutral"
              variant="outline"
              :disabled="!isUnlocked"
              @click="lockNow"
            >
              Lock now
            </UButton>
            <UButton
              :loading="saving"
              :disabled="!isUnlocked"
              class="bg-[#0097A7] hover:bg-[#00838f]"
              @click="saveTtl"
            >
              Save duration
            </UButton>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>
