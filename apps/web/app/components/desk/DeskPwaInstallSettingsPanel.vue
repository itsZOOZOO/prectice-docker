<script setup lang="ts">
import {
  canPromptPwaInstall,
  getPwaDeferredPrompt,
  initPwaInstallListeners,
  isIosSafari,
  isPwaStandalone,
  subscribePwaInstall,
  triggerPwaInstall
} from '~/utils/pwaInstall'

const standalone = ref(true)
const iosHint = ref(false)
const hasNativePrompt = ref(false)
const installing = ref(false)
const showFallbackHelp = ref(false)

function refresh() {
  standalone.value = isPwaStandalone()
  iosHint.value = isIosSafari()
  hasNativePrompt.value = getPwaDeferredPrompt() != null
}

onMounted(() => {
  initPwaInstallListeners()
  refresh()
  const unsub = subscribePwaInstall(refresh)
  onUnmounted(unsub)
})

async function handleInstall() {
  showFallbackHelp.value = false
  installing.value = true
  try {
    const outcome = await triggerPwaInstall()
    if (outcome === 'ios' || outcome === 'unavailable') {
      showFallbackHelp.value = true
    }
  } finally {
    installing.value = false
  }
}

const canNativeInstall = computed(() => hasNativePrompt.value || canPromptPwaInstall())
</script>

<template>
  <div
    v-if="standalone"
    class="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900"
  >
    Nav Dental is installed on this device.
  </div>

  <div
    v-else
    class="rounded-xl border border-slate-200 bg-white p-4"
  >
    <div class="flex items-start gap-3">
      <img
        src="/icons/icon-192.png"
        alt=""
        width="40"
        height="40"
        class="size-10 shrink-0 rounded-lg"
        aria-hidden="true"
      >
      <div class="min-w-0 flex-1">
        <p class="m-0 text-sm font-semibold text-[#1C2B35]">
          Install Nav Dental
        </p>
        <p class="mt-1 text-xs leading-relaxed text-slate-500">
          Add to your home screen for faster access and a full-screen app experience.
        </p>
      </div>
    </div>

    <div
      v-if="showFallbackHelp"
      class="mt-3 rounded-lg border border-[#0097A7]/20 bg-[#e0f7fa]/40 px-3 py-2 text-xs leading-relaxed text-[#006874]"
    >
      <template v-if="iosHint">
        In Safari, tap <span class="font-semibold">Share</span>, then
        <span class="font-semibold">Add to Home Screen</span>.
      </template>
      <template v-else>
        Open the browser menu <span class="font-semibold">(⋮)</span> and choose
        <span class="font-semibold">Install app</span> or
        <span class="font-semibold">Add to Home screen</span>.
      </template>
    </div>

    <button
      type="button"
      class="mt-3 w-full rounded-lg bg-[#0097A7] px-3 py-2.5 text-sm font-semibold text-white disabled:opacity-60"
      :disabled="installing"
      @click="handleInstall"
    >
      {{
        installing
          ? 'Opening install…'
          : iosHint
            ? 'How to install on iPhone'
            : canNativeInstall
              ? 'Install app'
              : 'Install instructions'
      }}
    </button>
  </div>
</template>
