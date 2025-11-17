<template>
  <div class="storage-pie">
    <div class="pie-header">
      <h4 class="pie-title">Storage Usage</h4>
      <span class="pie-subtitle">{{ formattedUsed }} / {{ formattedQuota }}</span>
    </div>
    <canvas ref="canvasEl" width="260" height="260" />
    <div class="pie-legend">
      <div class="legend-item">
        <span class="legend-swatch used"></span>
        <span>Used</span>
        <span class="legend-value">{{ formattedUsed }}</span>
      </div>
      <div class="legend-item">
        <span class="legend-swatch free"></span>
        <span>Free</span>
        <span class="legend-value">{{ formattedFree }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref, watch, computed } from 'vue'

const props = defineProps({
  usedBytes: { type: Number, required: true },
  quotaBytes: { type: Number, required: true }
})

const canvasEl = ref(null)
let ctx = null

const clamp = (v, min, max) => Math.max(min, Math.min(max, v))
const formatBytes = (bytes) => {
  if (!bytes || bytes <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const exp = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  const val = bytes / Math.pow(1024, exp)
  return `${val.toFixed(val >= 10 || exp === 0 ? 0 : 1)} ${units[exp]}`
}

const used = computed(() => clamp(props.usedBytes, 0, props.quotaBytes))
const free = computed(() => clamp(props.quotaBytes - used.value, 0, props.quotaBytes))

const formattedUsed = computed(() => formatBytes(used.value))
const formattedFree = computed(() => formatBytes(free.value))
const formattedQuota = computed(() => formatBytes(props.quotaBytes))

const drawPie = () => {
  if (!ctx) return
  const w = canvasEl.value.width
  const h = canvasEl.value.height
  const cx = w / 2
  const cy = h / 2
  const outer = Math.min(w, h) / 2 - 10
  const inner = outer * 0.6

  ctx.clearRect(0, 0, w, h)

  // base ring background
  ctx.beginPath()
  ctx.arc(cx, cy, outer, 0, Math.PI * 2)
  ctx.fillStyle = '#f3f6fa'
  ctx.fill()

  // donut hole
  ctx.globalCompositeOperation = 'destination-out'
  ctx.beginPath()
  ctx.arc(cx, cy, inner, 0, Math.PI * 2)
  ctx.fill()
  ctx.globalCompositeOperation = 'source-over'

  // compute angles
  const usedRatio = props.quotaBytes > 0 ? used.value / props.quotaBytes : 0
  const start = -Math.PI / 2
  const usedEnd = start + usedRatio * Math.PI * 2

  // used slice
  ctx.beginPath()
  ctx.arc(cx, cy, outer, start, usedEnd, false)
  ctx.lineTo(cx, cy)
  ctx.closePath()
  ctx.fillStyle = '#3a7eb9'
  ctx.fill()

  // free slice
  ctx.beginPath()
  ctx.arc(cx, cy, outer, usedEnd, start + Math.PI * 2, false)
  ctx.lineTo(cx, cy)
  ctx.closePath()
  ctx.fillStyle = '#a6c9e6'
  ctx.fill()

  // donut hole again to keep ring style
  ctx.globalCompositeOperation = 'destination-out'
  ctx.beginPath()
  ctx.arc(cx, cy, inner, 0, Math.PI * 2)
  ctx.fill()
  ctx.globalCompositeOperation = 'source-over'
}

onMounted(() => {
  ctx = canvasEl.value.getContext('2d')
  drawPie()
})

onBeforeUnmount(() => { ctx = null })

watch(() => [props.usedBytes, props.quotaBytes], () => {
  drawPie()
})
</script>

<style scoped>
.storage-pie {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.pie-header {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 8px;
}
.pie-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--waves-text-corporate);
}
.pie-subtitle { color: var(--waves-text-light); font-size: 12px; }
.pie-legend {
  width: 100%;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 8px;
}
.legend-item { display: flex; align-items: center; gap: 8px; }
.legend-swatch { width: 12px; height: 12px; border-radius: 3px; display: inline-block; }
.legend-swatch.used { background: #3a7eb9; }
.legend-swatch.free { background: #a6c9e6; }
.legend-item { gap: 6px; }
.legend-value { margin-left: 6px; color: var(--waves-text-light); font-size: 12px; }
</style>