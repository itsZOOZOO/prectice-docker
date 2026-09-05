<script setup lang="ts">
import {
  canPromptPwaInstall,
  dismissPwaInstallBanner,
  getPwaDeferredPrompt,
  initPwaInstallListeners,
  isIosSafari,
  isPwaDismissedRecently,
  isPwaStandalone,
  subscribePwaInstall,
  triggerPwaInstall
} from '~/utils/pwaInstall'

const PROACTIVE_DELAY_MS = 2500

const visible = ref(false)
const iosHint = ref(false)
const installing = ref(false)
const canInstall = ref(false)
const hasNativePrompt = ref(false)

function refresh() {
  const ios = isIosSafari()
  const installable = canPromptPwaInstall()
  iosHint.value = ios
  canInstall.value = installable
  hasNativePrompt.value = getPwaDeferredPrompt() != null
  if (installable && !isPwaDismissedRecently() && !isPwaStandalone()) {
    visible.value = true
  }
}

onMounted(() => {
  initPwaInstallListeners()
  refresh()
  const unsub = subscribePwaInstall(refresh)
  onUnmounted(unsub)
})

watch(canInstall, (ok) => {
  if (!ok || isPwaDismissedRecently() || isPwaStandalone()) return
  const timer = window.setTimeout(() => {
    if (canPromptPwaInstall() && !isPwaDismissedRecently()) {
      visible.value = true
    }
  }, PROACTIVE_DELAY_MS)
  return () => window.clearTimeout(timer)
})

function dismiss() {
  dismissPwaInstallBanner()
  visible.value = false
}

async function install() {
  if (!getPwaDeferredPrompt() && !iosHint.value) return
  installing.value = true
  try {
    const outcome = await triggerPwaInstall()
    if (outcome === 'accepted') {
      visible.value = false
    }
  } finally {
    installing.value = false
  }
}
</script>

<template>
  <div
    v-if="visible"
    role="dialog"
    aria-labelledby="pwa-install-title"
    aria-describedby="pwa-install-desc"
    class="fixed inset-x-0 bottom-[calc(4.25rem+env(safe-area-inset-bottom))] z-[60] px-4 lg:bottom-6"
  >
    <div class="mx-auto max-w-[480px] rounded-xl border border-[#0097A7]/25 bg-white p-4 shadow-[0_8px_24px_rgba(0,151,167,0.18)]">
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
          <p
            id="pwa-install-title"
            class="text-sm font-semibold text-[#1C2B35]"
          >
            Install Nav Dental
          </p>
          <p
            id="pwa-install-desc"
            class="mt-1 text-xs leading-relaxed text-slate-600"
          >
            <template v-if="iosHint">
              Tap <span class="font-semibold">Share</span> in Safari, then
              <span class="font-semibold">Add to Home Screen</span>
              for quick access like a native app.
            </template>
            <template v-else>
              Add Nav Dental to your home screen for faster access and a full-screen app experience.
            </template>
          </p>
        </div>
        <button
          type="button"
          class="shrink-0 rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
          aria-label="Dismiss install prompt"
          @click="dismiss"
        >
          ✕
        </button>
      </div>

      <div class="mt-3 flex gap-2">
        <button
          v-if="!iosHint && hasNativePrompt"
          type="button"
          class="flex-1 rounded-lg bg-[#0097A7] px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
          :disabled="installing"
          @click="install"
        >
          {{ installing ? 'Installing…' : 'Install app' }}
        </button>
        <button
          type="button"
          class="rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50"
          :class="iosHint || !hasNativePrompt ? 'flex-1' : ''"
          @click="dismiss"
        >
          Not now
        </button>
      </div>
    </div>
  </div>
</template>
