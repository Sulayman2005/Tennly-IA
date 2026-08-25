<script setup>
import { computed } from 'vue'

const props = defineProps({
  /** list<{date: 'YYYY-MM-DD', count: number}> — voir AdminDashboardProvider::computeSubscriptionsGrowth(). */
  points: { type: Array, default: () => [] },
})

const W = 300
const H = 92
const PAD_X = 4
const PAD_TOP = 10
const PAD_BOTTOM = 4

const maxCount = computed(() => Math.max(...props.points.map((p) => p.count), 1))

const coords = computed(() => {
  const n = props.points.length
  if (n === 0) return []
  const usableW = W - PAD_X * 2
  const usableH = H - PAD_TOP - PAD_BOTTOM
  return props.points.map((p, i) => {
    const x = n === 1 ? PAD_X + usableW / 2 : PAD_X + (i / (n - 1)) * usableW
    const y = PAD_TOP + usableH * (1 - p.count / maxCount.value)
    return { x, y, count: p.count, date: p.date }
  })
})

const linePath = computed(() =>
  coords.value.map((c, i) => `${i === 0 ? 'M' : 'L'} ${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(' '),
)

const areaPath = computed(() => {
  if (coords.value.length === 0) return ''
  const first = coords.value[0]
  const last = coords.value[coords.value.length - 1]
  return `${linePath.value} L ${last.x.toFixed(1)},${H - PAD_BOTTOM} L ${first.x.toFixed(1)},${H - PAD_BOTTOM} Z`
})

const lastPoint = computed(() => coords.value[coords.value.length - 1] ?? null)

// Variation "7 derniers jours" vs "7 jours précédents" — un vrai delta calculé
// sur la fenêtre de 14 jours renvoyée par l'API, pas une tendance inventée.
const weekOverWeek = computed(() => {
  const n = props.points.length
  if (n < 14) return null
  const previous = props.points.slice(0, n - 7).reduce((sum, p) => sum + p.count, 0)
  const recent = props.points.slice(n - 7).reduce((sum, p) => sum + p.count, 0)
  if (previous === 0) {
    return recent === 0 ? { kind: 'flat', value: 0 } : { kind: 'up', value: recent }
  }
  const pct = Math.round(((recent - previous) / previous) * 100)
  return { kind: pct >= 0 ? 'up' : 'down', value: Math.abs(pct), isPercent: true }
})

function formatDay(dateStr) {
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })
}
</script>

<template>
  <div class="growth-wrap">
    <svg :viewBox="`0 0 ${W} ${H}`" preserveAspectRatio="none" class="growth-svg">
      <defs>
        <linearGradient id="growthFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="var(--green)" stop-opacity="0.28" />
          <stop offset="100%" stop-color="var(--green)" stop-opacity="0" />
        </linearGradient>
      </defs>
      <path v-if="areaPath" :d="areaPath" fill="url(#growthFill)" />
      <path v-if="linePath" :d="linePath" fill="none" stroke="var(--green)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />
      <circle v-if="lastPoint" :cx="lastPoint.x" :cy="lastPoint.y" r="3.4" fill="var(--green)" stroke="var(--admin-card)" stroke-width="1.6" />
    </svg>

    <div class="growth-foot">
      <span class="growth-range" v-if="points.length">
        {{ formatDay(points[0].date) }} – {{ formatDay(points[points.length - 1].date) }}
      </span>
      <span v-if="weekOverWeek" class="growth-badge" :class="weekOverWeek.kind">
        <template v-if="weekOverWeek.kind === 'flat'">stable</template>
        <template v-else-if="weekOverWeek.isPercent">{{ weekOverWeek.kind === 'up' ? '+' : '-' }}{{ weekOverWeek.value }} %</template>
        <template v-else>+{{ weekOverWeek.value }}</template>
        <span class="growth-badge-sub">7j</span>
      </span>
    </div>
  </div>
</template>

<style scoped>
.growth-wrap {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.growth-svg {
  width: 100%;
  height: 92px;
  display: block;
}
.growth-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.growth-range {
  font-size: 11px;
  color: var(--grey);
}
.growth-badge {
  font-size: 12px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 999px;
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
}
.growth-badge.up {
  background: #eef7f1;
  color: #1f8a4d;
}
.growth-badge.down {
  background: #fdecea;
  color: var(--red);
}
.growth-badge.flat {
  background: var(--admin-bg);
  color: var(--grey);
}
.growth-badge-sub {
  font-size: 10px;
  font-weight: 600;
  opacity: 0.7;
}
</style>