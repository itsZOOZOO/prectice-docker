<script setup lang="ts">
import {
  buildSsoLoginUrl,
  safePostLoginPath,
  storeSsoRememberPref
} from '~/utils/sso'
import { homePathForViewport } from '~/utils/deviceHome'

definePageMeta({ layout: 'auth' })

const auth = useAuth()
const { api } = useApi()
const route = useRoute()

const username = ref('')
const password = ref('')
const remember = ref(false)
const showPassword = ref(false)
const loading = ref(false)
const ssoLoading = ref(false)
const error = ref('')

onMounted(() => {
  auth.hydrate()
  if (auth.isLoggedIn.value) {
    void navigateTo(homePathForViewport())
    return
  }
  const q = route.query.error
  if (typeof q === 'string' && q.trim()) {
    error.value = q.trim()
  }
})

async function submitPassword() {
  loading.value = true
  error.value = ''
  try {
    const data = await api<{
      access_token: string
      user: {
        user_id: number
        clinic_id: number
        username: string
        full_name: string
        role: string
        email?: string | null
      }
      clinic_name: string
    }>('/auth/login', {
      method: 'POST',
      body: {
        username: username.value,
        password: password.value,
        remember: remember.value
      }
    })
    auth.setSession(data)
    await navigateTo(homePathForViewport())
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Login failed'
  } finally {
    loading.value = false
  }
}

function startSso() {
  error.value = ''
  ssoLoading.value = true
  storeSsoRememberPref(remember.value)
  const redirect = safePostLoginPath(
    typeof route.query.redirect === 'string' ? route.query.redirect : homePathForViewport()
  )
  window.location.href = buildSsoLoginUrl(redirect)
}
</script>

<template>
  <div class="login-stage relative isolate min-h-screen overflow-hidden">
    <!-- Ambient geometric field (decorative only) -->
    <div
      class="login-ambient pointer-events-none absolute inset-0 -z-10"
      aria-hidden="true"
    >
      <div class="login-ambient__wash" />
      <div class="login-ambient__grid" />
      <div class="login-ambient__mesh" />
      <div class="login-ambient__carving" />

      <!-- Intricate web / carving SVGs -->
      <svg
        class="login-web login-web--primary"
        viewBox="0 0 800 800"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <g class="login-web__spin" stroke="currentColor" stroke-width="1" opacity="0.55">
          <circle cx="400" cy="400" r="60" />
          <circle cx="400" cy="400" r="120" />
          <circle cx="400" cy="400" r="190" />
          <circle cx="400" cy="400" r="270" />
          <circle cx="400" cy="400" r="350" />
          <path d="M400 50 L400 750 M50 400 L750 400 M152 152 L648 648 M648 152 L152 648" />
          <path d="M400 50 L648 152 L750 400 L648 648 L400 750 L152 648 L50 400 L152 152 Z" />
          <path d="M400 120 L580 220 L640 400 L580 580 L400 680 L220 580 L160 400 L220 220 Z" />
          <path d="M280 280 L520 280 L520 520 L280 520 Z" />
          <path d="M320 320 L480 320 L480 480 L320 480 Z" />
          <circle cx="400" cy="50" r="5" fill="currentColor" stroke="none" />
          <circle cx="648" cy="152" r="4" fill="currentColor" stroke="none" />
          <circle cx="750" cy="400" r="5" fill="currentColor" stroke="none" />
          <circle cx="648" cy="648" r="4" fill="currentColor" stroke="none" />
          <circle cx="400" cy="750" r="5" fill="currentColor" stroke="none" />
          <circle cx="152" cy="648" r="4" fill="currentColor" stroke="none" />
          <circle cx="50" cy="400" r="5" fill="currentColor" stroke="none" />
          <circle cx="152" cy="152" r="4" fill="currentColor" stroke="none" />
          <circle cx="400" cy="400" r="8" fill="currentColor" stroke="none" opacity="0.7" />
        </g>
      </svg>

      <svg
        class="login-web login-web--secondary"
        viewBox="0 0 600 600"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <g class="login-web__counter" stroke="currentColor" stroke-width="0.9" opacity="0.45">
          <path d="M300 40 L520 160 L520 400 L300 520 L80 400 L80 160 Z" />
          <path d="M300 100 L460 190 L460 370 L300 460 L140 370 L140 190 Z" />
          <path d="M300 160 L400 220 L400 340 L300 400 L200 340 L200 220 Z" />
          <path d="M300 40 L300 520 M80 160 L520 400 M520 160 L80 400" />
          <path d="M180 120 L420 120 L500 280 L420 440 L180 440 L100 280 Z" opacity="0.7" />
          <circle cx="300" cy="40" r="3.5" fill="currentColor" stroke="none" />
          <circle cx="520" cy="160" r="3" fill="currentColor" stroke="none" />
          <circle cx="520" cy="400" r="3" fill="currentColor" stroke="none" />
          <circle cx="300" cy="520" r="3.5" fill="currentColor" stroke="none" />
          <circle cx="80" cy="400" r="3" fill="currentColor" stroke="none" />
          <circle cx="80" cy="160" r="3" fill="currentColor" stroke="none" />
        </g>
      </svg>

      <svg
        class="login-web login-web--tertiary"
        viewBox="0 0 400 400"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <g class="login-web__pulse" stroke="currentColor" stroke-width="1">
          <path d="M40 40 L360 40 L360 360 L40 360 Z" />
          <path d="M80 80 L320 80 L320 320 L80 320 Z" />
          <path d="M120 120 L280 120 L280 280 L120 280 Z" />
          <path d="M40 40 L360 360 M360 40 L40 360 M200 40 L200 360 M40 200 L360 200" />
          <circle cx="200" cy="200" r="28" />
          <circle cx="200" cy="200" r="56" />
        </g>
      </svg>

      <span class="login-node login-node--1" />
      <span class="login-node login-node--2" />
      <span class="login-node login-node--3" />
      <span class="login-node login-node--4" />
      <span class="login-node login-node--5" />
      <span class="login-node login-node--6" />
      <span class="login-filament login-filament--a" />
      <span class="login-filament login-filament--b" />
      <span class="login-filament login-filament--c" />
      <span class="login-filament login-filament--d" />
      <span class="login-shape login-shape--ring login-shape--a" />
      <span class="login-shape login-shape--hex login-shape--b" />
      <span class="login-shape login-shape--ring login-shape--d" />
    </div>

    <div class="relative z-10 mx-auto flex min-h-screen max-w-md flex-col justify-center px-4 py-10">
      <div class="mb-8 flex items-center gap-3">
        <img
          src="/icons/icon-192.png"
          alt=""
          width="48"
          height="48"
          class="size-12 rounded-xl shadow-sm"
          aria-hidden="true"
        >
        <div>
          <p class="text-4xl font-semibold text-[#0097A7]">
            Nav Dental
          </p>
          <p class="mt-2 text-slate-600">
            Clinic desk & mobile
          </p>
        </div>
      </div>

      <div class="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <p
          v-if="error"
          class="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700"
        >
          {{ error }}
        </p>

        <UButton
          block
          size="lg"
          color="neutral"
          variant="outline"
          :loading="ssoLoading"
          class="justify-center gap-2"
          @click="startSso"
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 48 48"
            aria-hidden="true"
          >
            <path
              fill="#FFC107"
              d="M43.611 20.083H42V20H24v8h11.303C33.654 32.657 29.083 36 24 36c-5.522 0-10-4.478-10-10s4.478-10 10-10c2.837 0 5.352 1.174 7.196 3.064l5.657-5.657C34.046 10.846 29.268 9 24 9 14.059 9 6 17.059 6 27s8.059 18 18 18 18-8.059 18-18c0-1.341-.138-2.65-.389-3.917z"
            />
            <path
              fill="#FF3D00"
              d="M6 27c0-1.657.276-3.25.783-4.741l8.564 6.548C14.655 30.657 19.026 33 24 33c2.837 0 5.352 1.174 7.196 3.064l5.657 5.657C34.046 41.154 29.268 43 24 43 14.059 43 6 34.941 6 27z"
            />
            <path
              fill="#4CAF50"
              d="M42.459 15.917l-8.564 6.548C32.345 19.343 28.374 17 24 17c-2.837 0-5.352 1.174-7.196 3.064l-5.657-5.657C13.954 10.846 18.732 9 24 9c5.268 0 10.046 1.846 13.459 4.917z"
            />
            <path
              fill="#1976D2"
              d="M43.611 20.083H42V20H24v8h11.303a12.04 12.04 0 0 1-4.087 5.571l.003-.002 8.564-6.548C42.654 25.657 43 26.309 43 27c0 .691-.346 1.343-.389 1.917z"
            />
          </svg>
          Sign in with Google
        </UButton>

        <label class="flex cursor-pointer items-center gap-2 text-sm text-slate-600">
          <input
            v-model="remember"
            type="checkbox"
            class="size-4 rounded border-slate-300 text-[#0097A7] focus:ring-[#0097A7]"
          >
          Remember me for 30 days
        </label>

        <div class="flex items-center gap-3 py-1">
          <div class="h-px flex-1 bg-slate-200" />
          <span class="text-xs text-slate-400">or</span>
          <div class="h-px flex-1 bg-slate-200" />
        </div>

        <button
          type="button"
          class="w-full text-center text-sm font-medium text-slate-600 hover:text-[#0097A7]"
          @click="showPassword = !showPassword"
        >
          {{ showPassword ? 'Hide password login' : 'Sign in with password' }}
        </button>

        <form
          v-if="showPassword"
          class="space-y-4"
          @submit.prevent="submitPassword"
        >
          <UFormField label="Username">
            <UInput
              v-model="username"
              autocomplete="username"
              class="w-full"
              size="lg"
            />
          </UFormField>
          <UFormField label="Password">
            <UInput
              v-model="password"
              type="password"
              autocomplete="current-password"
              class="w-full"
              size="lg"
            />
          </UFormField>

          <UButton
            type="submit"
            block
            size="lg"
            class="bg-[#0097A7]"
            :loading="loading"
          >
            Sign in
          </UButton>
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-stage {
  --login-teal: #0097a7;
  --login-ink: #1c2b35;
  background: #e8eef3;
}

.login-ambient__wash {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 80% 60% at 12% 18%, rgb(0 151 167 / 0.22), transparent 55%),
    radial-gradient(ellipse 70% 50% at 88% 78%, rgb(0 131 143 / 0.18), transparent 50%),
    radial-gradient(ellipse 50% 40% at 70% 12%, rgb(38 198 218 / 0.14), transparent 45%),
    radial-gradient(ellipse 40% 35% at 40% 55%, rgb(0 151 167 / 0.08), transparent 60%),
    linear-gradient(165deg, #f3f7fa 0%, #e4ecf2 48%, #dce8ee 100%);
  animation: login-wash-breathe 14s ease-in-out infinite alternate;
}

.login-ambient__grid {
  position: absolute;
  inset: -30%;
  opacity: 0.42;
  background-image:
    linear-gradient(rgb(28 43 53 / 0.055) 1px, transparent 1px),
    linear-gradient(90deg, rgb(28 43 53 / 0.055) 1px, transparent 1px);
  background-size: 36px 36px;
  mask-image: radial-gradient(ellipse 75% 70% at 50% 45%, #000 15%, transparent 78%);
  animation: login-grid-drift 28s linear infinite;
}

.login-ambient__mesh {
  position: absolute;
  inset: -10%;
  opacity: 0.7;
  background-image:
    repeating-linear-gradient(
      -18deg,
      transparent 0,
      transparent 11px,
      rgb(0 151 167 / 0.05) 11px,
      rgb(0 151 167 / 0.05) 12px
    ),
    repeating-linear-gradient(
      72deg,
      transparent 0,
      transparent 17px,
      rgb(28 43 53 / 0.04) 17px,
      rgb(28 43 53 / 0.04) 18px
    ),
    repeating-linear-gradient(
      28deg,
      transparent 0,
      transparent 26px,
      rgb(0 131 143 / 0.035) 26px,
      rgb(0 131 143 / 0.035) 27px
    );
  animation: login-mesh-shift 18s ease-in-out infinite alternate;
}

.login-ambient__carving {
  position: absolute;
  inset: -15%;
  opacity: 0.5;
  background-image:
    radial-gradient(circle at 20% 30%, transparent 28px, rgb(0 151 167 / 0.06) 29px, transparent 30px),
    radial-gradient(circle at 75% 22%, transparent 22px, rgb(28 43 53 / 0.05) 23px, transparent 24px),
    radial-gradient(circle at 82% 70%, transparent 34px, rgb(0 151 167 / 0.07) 35px, transparent 36px),
    radial-gradient(circle at 18% 78%, transparent 26px, rgb(0 131 143 / 0.06) 27px, transparent 28px),
    radial-gradient(circle at 48% 48%, transparent 60px, rgb(0 151 167 / 0.04) 61px, transparent 62px);
  background-size: 100% 100%;
  animation: login-carving-sway 22s ease-in-out infinite alternate;
}

.login-web {
  position: absolute;
  color: rgb(0 151 167 / 0.55);
  filter: drop-shadow(0 0 12px rgb(0 151 167 / 0.08));
}

.login-web--primary {
  width: min(92vw, 720px);
  height: min(92vw, 720px);
  top: 50%;
  left: 50%;
  margin: calc(min(92vw, 720px) / -2) 0 0 calc(min(92vw, 720px) / -2);
  opacity: 0.55;
  animation: login-web-spin 48s linear infinite;
}

.login-web--secondary {
  width: min(55vw, 420px);
  height: min(55vw, 420px);
  top: -4%;
  right: -8%;
  color: rgb(0 131 143 / 0.5);
  opacity: 0.65;
  animation: login-web-counter 36s linear infinite;
}

.login-web--tertiary {
  width: min(42vw, 280px);
  height: min(42vw, 280px);
  bottom: -2%;
  left: -4%;
  color: rgb(28 43 53 / 0.28);
  opacity: 0.7;
  animation: login-web-pulse 10s ease-in-out infinite;
}

.login-node {
  position: absolute;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: rgb(0 151 167 / 0.55);
  box-shadow: 0 0 0 4px rgb(0 151 167 / 0.08), 0 0 16px rgb(0 151 167 / 0.25);
  animation: login-node-pulse 3.6s ease-in-out infinite;
}

.login-node--1 { top: 14%; left: 18%; animation-delay: 0s; }
.login-node--2 { top: 22%; right: 16%; animation-delay: 0.6s; width: 5px; height: 5px; }
.login-node--3 { top: 58%; left: 8%; animation-delay: 1.2s; }
.login-node--4 { bottom: 18%; right: 14%; animation-delay: 1.8s; width: 6px; height: 6px; }
.login-node--5 { bottom: 28%; left: 28%; animation-delay: 0.9s; width: 4px; height: 4px; }
.login-node--6 { top: 38%; right: 28%; animation-delay: 2.1s; width: 5px; height: 5px; }

.login-filament {
  position: absolute;
  height: 1px;
  border: none;
  background: linear-gradient(
    90deg,
    transparent,
    rgb(0 151 167 / 0.15),
    rgb(0 151 167 / 0.45),
    rgb(0 151 167 / 0.15),
    transparent
  );
  transform-origin: left center;
}

.login-filament--a {
  width: 38vw;
  max-width: 320px;
  top: 16%;
  left: 20%;
  animation: login-filament-a 12s ease-in-out infinite;
}

.login-filament--b {
  width: 32vw;
  max-width: 260px;
  top: 62%;
  right: 10%;
  animation: login-filament-b 14s ease-in-out infinite;
}

.login-filament--c {
  width: 28vw;
  max-width: 220px;
  bottom: 24%;
  left: 12%;
  animation: login-filament-c 11s ease-in-out infinite;
}

.login-filament--d {
  width: 24vw;
  max-width: 200px;
  top: 40%;
  left: 55%;
  animation: login-filament-d 13s ease-in-out infinite;
}

.login-shape {
  position: absolute;
  display: block;
  border: 1.5px solid rgb(0 151 167 / 0.22);
  will-change: transform, opacity;
}

.login-shape--ring {
  border-radius: 50%;
  background: radial-gradient(circle at 35% 30%, rgb(0 151 167 / 0.1), transparent 65%);
}

.login-shape--hex {
  width: 140px;
  height: 122px;
  background: rgb(0 151 167 / 0.07);
  clip-path: polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%);
  border: none;
}

.login-shape--a {
  width: min(48vw, 320px);
  height: min(48vw, 320px);
  top: -8%;
  right: -10%;
  animation: login-drift-a 16s ease-in-out infinite;
}

.login-shape--b {
  top: 16%;
  left: -4%;
  animation: login-drift-b 18s ease-in-out infinite;
}

.login-shape--d {
  width: min(32vw, 180px);
  height: min(32vw, 180px);
  bottom: -6%;
  left: 10%;
  opacity: 0.9;
  animation: login-drift-d 15s ease-in-out infinite;
}

@keyframes login-wash-breathe {
  from { filter: saturate(1) brightness(1); }
  to { filter: saturate(1.12) brightness(1.03); }
}

@keyframes login-grid-drift {
  from { transform: translate3d(0, 0, 0); }
  to { transform: translate3d(36px, 36px, 0); }
}

@keyframes login-mesh-shift {
  from { transform: translate3d(0, 0, 0) rotate(0deg) scale(1); }
  to { transform: translate3d(-28px, 18px, 0) rotate(1.2deg) scale(1.05); }
}

@keyframes login-carving-sway {
  from { transform: translate3d(0, 0, 0) scale(1); }
  to { transform: translate3d(20px, -14px, 0) scale(1.06); }
}

@keyframes login-web-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes login-web-counter {
  from { transform: rotate(0deg) scale(1); }
  to { transform: rotate(-360deg) scale(1.04); }
}

@keyframes login-web-pulse {
  0%, 100% { transform: rotate(0deg) scale(1); opacity: 0.55; }
  50% { transform: rotate(8deg) scale(1.08); opacity: 0.9; }
}

@keyframes login-node-pulse {
  0%, 100% { transform: scale(1); opacity: 0.55; }
  50% { transform: scale(1.55); opacity: 1; }
}

@keyframes login-filament-a {
  0%, 100% { transform: rotate(-28deg) translate3d(0, 0, 0) scaleX(1); opacity: 0.35; }
  50% { transform: rotate(-18deg) translate3d(24px, 12px, 0) scaleX(1.15); opacity: 0.85; }
}

@keyframes login-filament-b {
  0%, 100% { transform: rotate(42deg) translate3d(0, 0, 0); opacity: 0.3; }
  50% { transform: rotate(52deg) translate3d(-20px, 16px, 0); opacity: 0.8; }
}

@keyframes login-filament-c {
  0%, 100% { transform: rotate(12deg) translate3d(0, 0, 0) scaleX(0.9); opacity: 0.35; }
  50% { transform: rotate(4deg) translate3d(18px, -10px, 0) scaleX(1.2); opacity: 0.75; }
}

@keyframes login-filament-d {
  0%, 100% { transform: rotate(-55deg) translate3d(0, 0, 0); opacity: 0.25; }
  50% { transform: rotate(-40deg) translate3d(-14px, 20px, 0); opacity: 0.7; }
}

@keyframes login-drift-a {
  0%, 100% { transform: translate3d(0, 0, 0) rotate(0deg); opacity: 0.85; }
  50% { transform: translate3d(-40px, 48px, 0) rotate(18deg); opacity: 1; }
}

@keyframes login-drift-b {
  0%, 100% { transform: translate3d(0, 0, 0) rotate(0deg); }
  50% { transform: translate3d(48px, -30px, 0) rotate(-14deg); }
}

@keyframes login-drift-d {
  0%, 100% { transform: translate3d(0, 0, 0) scale(1); }
  50% { transform: translate3d(32px, -28px, 0) scale(1.12); }
}

@media (prefers-reduced-motion: reduce) {
  .login-ambient__wash,
  .login-ambient__grid,
  .login-ambient__mesh,
  .login-ambient__carving,
  .login-web,
  .login-node,
  .login-filament,
  .login-shape {
    animation: none !important;
  }
}

@media (max-width: 640px) {
  .login-web--tertiary,
  .login-node--5,
  .login-node--6,
  .login-filament--d {
    display: none;
  }

  .login-web--primary {
    opacity: 0.4;
  }

  .login-shape--a {
    width: 200px;
    height: 200px;
  }
}
</style>
