<script setup lang="ts">
import type { FlowChartPoint } from '~/utils/statistics'

const props = withDefaults(defineProps<{
  flow: FlowChartPoint[]
  average: number
  ariaLabel: string
  formatValue?: (value: number) => string
  valueLabel?: string
  averageLabel?: string
}>(), {
  formatValue: (v: number) => String(Math.round(v)),
  valueLabel: 'Value',
  averageLabel: 'Average'
})

const hoverIdx = ref<number | null>(null)
const glowId = `fc-glow-${Math.random().toString(36).slice(2, 9)}`

const width = 720
const height = 260
const padX = 36
const padY = 24
const chartW = width - padX * 2
const chartH = height - padY - 28

const maxCount = computed(() =>
  Math.max(1, ...props.flow.map(p => p.count), props.average)
)

const points = computed(() =>
  props.flow.map((point, idx) => {
    const x = padX + (props.flow.length <= 1 ? chartW / 2 : (idx / (props.flow.length - 1)) * chartW)
    const y = padY + chartH - (point.count / maxCount.value) * chartH
    return { x, y, ...point }
  })
)

const linePath = computed(() =>
  points.value.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ')
)

const areaPath = computed(() => {
  if (!points.value.length) return ''
  const last = points.value[points.value.length - 1]!
  const first = points.value[0]!
  return `${linePath.value} L ${last.x} ${padY + chartH} L ${first.x} ${padY + chartH} Z`
})

const avgY = computed(() => padY + chartH - (props.average / maxCount.value) * chartH)
const active = computed(() =>
  hoverIdx.value != null ? points.value[hoverIdx.value] ?? null : null
)

const tooltipStyle = computed(() => {
  if (!active.value) return null
  const leftPct = (active.value.x / width) * 100
  const topPct = (active.value.y / height) * 100
  const preferLeft = leftPct > 72
  return {
    left: `${leftPct}%`,
    top: `${Math.max(8, topPct - 6)}%`,
    transform: preferLeft ? 'translate(-100%, -100%)' : 'translate(8px, -100%)'
  }
})

const labelStep = computed(() =>
  props.flow.length <= 12 ? 1 : Math.ceil(props.flow.length / 12)
)

function nearestIndex(clientX: number, svg: SVGSVGElement) {
  const rect = svg.getBoundingClientRect()
  const x = ((clientX - rect.left) / rect.width) * width
  if (!points.value.length) return null
  let best = 0
  let bestDist = Infinity
  for (let i = 0; i < points.value.length; i++) {
    const d = Math.abs(points.value[i]!.x - x)
    if (d < bestDist) {
      bestDist = d
      best = i
    }
  }
  return best
}

function onMove(e: MouseEvent) {
  const idx = nearestIndex(e.clientX, e.currentTarget as SVGSVGElement)
  if (idx != null) hoverIdx.value = idx
}
</script>

<template>
  <div class="relative" @mouseleave="hoverIdx = null">
    <svg
      :viewBox="`0 0 ${width} ${height}`"
      class="h-[260px] w-full cursor-crosshair touch-pan-y"
      role="img"
      :aria-label="ariaLabel"
      @mousemove="onMove"
      @click="onMove"
    >
      <defs>
        <filter :id="glowId" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="2.5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <g v-for="tick in [0, 0.25, 0.5, 0.75, 1]" :key="tick">
        <line
          :x1="padX"
          :y1="padY + chartH - tick * chartH"
          :x2="width - padX"
          :y2="padY + chartH - tick * chartH"
          stroke="#e2e8f0"
          stroke-width="1"
        />
        <text
          :x="4"
          :y="padY + chartH - tick * chartH + 4"
          class="fill-slate-400 text-[10px]"
        >
          {{ formatValue(Math.round(tick * maxCount)) }}
        </text>
      </g>
      <path v-if="areaPath" :d="areaPath" fill="rgba(0,151,167,0.12)" />
      <path
        v-if="linePath"
        :d="linePath"
        fill="none"
        stroke="#0097A7"
        stroke-width="2.5"
        stroke-linejoin="round"
      />
      <line
        :x1="padX"
        :y1="avgY"
        :x2="width - padX"
        :y2="avgY"
        stroke="#ef4444"
        stroke-width="1.5"
        stroke-dasharray="6 4"
      />
      <g v-for="(p, idx) in points" :key="`${p.label}-${idx}`">
        <circle
          v-if="idx === hoverIdx"
          :cx="p.x"
          :cy="p.y"
          r="7"
          fill="#0097A7"
          :filter="`url(#${glowId})`"
        />
        <circle :cx="p.x" :cy="p.y" r="3.5" fill="#0097A7" />
        <text
          v-if="idx % labelStep === 0 || idx === points.length - 1"
          :x="p.x"
          :y="height - 8"
          text-anchor="middle"
          class="fill-slate-500 text-[10px]"
        >
          {{ p.label }}
        </text>
      </g>
      <line
        v-if="active"
        :x1="active.x"
        :y1="padY"
        :x2="active.x"
        :y2="padY + chartH"
        stroke="#94a3b8"
        stroke-width="1"
        stroke-dasharray="3 3"
      />
    </svg>
    <div
      v-if="active && tooltipStyle"
      class="pointer-events-none absolute z-10 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs shadow-lg"
      :style="tooltipStyle"
    >
      <div class="font-semibold text-slate-800">{{ active.label }}</div>
      <div class="text-slate-600">{{ valueLabel }}: {{ formatValue(active.count) }}</div>
      <div class="text-slate-500">
        {{ averageLabel }}: {{ formatValue(Math.round(average * 10) / 10) }}
      </div>
    </div>
    <p
      v-if="flow.length > 0 && hoverIdx == null"
      class="mt-1 text-center text-[11px] text-slate-400 sm:text-left"
    >
      Hover or tap along the chart to see details
    </p>
  </div>
</template>
