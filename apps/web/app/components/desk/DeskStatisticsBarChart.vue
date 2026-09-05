<script setup lang="ts">
import type { FlowChartPoint } from '~/utils/statistics'

const props = withDefaults(defineProps<{
  points: FlowChartPoint[]
  ariaLabel: string
  barColor?: string
  valueLabel?: string
}>(), {
  barColor: '#0097A7',
  valueLabel: 'check-ins'
})

const hoverIdx = ref<number | null>(null)
const width = 720
const height = 220
const padX = 28
const padY = 20
const chartW = width - padX * 2
const chartH = height - padY - 28

const maxCount = computed(() => Math.max(1, ...props.points.map(p => p.count)))
const barGap = computed(() => (props.points.length > 16 ? 2 : 6))
const slotW = computed(() => chartW / Math.max(props.points.length, 1))
const barWidth = computed(() => Math.max(4, slotW.value - barGap.value))
const active = computed(() =>
  hoverIdx.value != null ? props.points[hoverIdx.value] ?? null : null
)

const tooltipStyle = computed(() => {
  if (hoverIdx.value == null) return null
  const cx = padX + hoverIdx.value * slotW.value + barWidth.value / 2
  const leftPct = (cx / width) * 100
  const preferLeft = leftPct > 72
  return {
    left: `${leftPct}%`,
    top: '12%',
    transform: preferLeft ? 'translate(-100%, 0)' : 'translate(8px, 0)'
  }
})

function onMove(e: MouseEvent) {
  const svg = e.currentTarget as SVGSVGElement
  const rect = svg.getBoundingClientRect()
  const x = ((e.clientX - rect.left) / rect.width) * width
  const idx = Math.max(0, Math.min(props.points.length - 1, Math.floor((x - padX) / slotW.value)))
  if (x >= padX && x <= width - padX) hoverIdx.value = idx
}

const labelStep = computed(() =>
  props.points.length <= 12 ? 1 : Math.ceil(props.points.length / 12)
)
</script>

<template>
  <div class="relative" @mouseleave="hoverIdx = null">
    <svg
      :viewBox="`0 0 ${width} ${height}`"
      class="h-[220px] w-full touch-pan-y"
      role="img"
      :aria-label="ariaLabel"
      @mousemove="onMove"
      @click="onMove"
    >
      <g v-for="tick in [0, 0.5, 1]" :key="tick">
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
          {{ Math.round(tick * maxCount) }}
        </text>
      </g>
      <g v-for="(point, idx) in points" :key="`${point.label}-${idx}`">
        <rect
          :x="padX + idx * slotW + barGap / 2"
          :y="padY + chartH - (point.count / maxCount) * chartH"
          :width="barWidth"
          :height="Math.max(0, (point.count / maxCount) * chartH)"
          :fill="barColor"
          :opacity="hoverIdx == null || hoverIdx === idx ? 1 : 0.45"
          rx="2"
        />
        <text
          v-if="idx % labelStep === 0 || idx === points.length - 1"
          :x="padX + idx * slotW + barWidth / 2"
          :y="height - 6"
          text-anchor="middle"
          class="fill-slate-500 text-[9px]"
        >
          {{ point.label }}
        </text>
      </g>
    </svg>
    <div
      v-if="active && tooltipStyle"
      class="pointer-events-none absolute z-10 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs shadow-lg"
      :style="tooltipStyle"
    >
      <div class="font-semibold text-slate-800">{{ active.label }}</div>
      <div class="text-slate-600">{{ valueLabel }}: {{ active.count }}</div>
    </div>
  </div>
</template>
