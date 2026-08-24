<script setup>
import { computed } from 'vue'

const props = defineProps({
  /** list<{surface, accuracy, sampleSize}> — voir AdminDashboardProvider. Peut être partiel ou vide. */
  bySurface: { type: Array, default: () => [] },
  overall: { type: Number, default: null },
})

// Les 4 surfaces existent toujours (voir Surface::class côté backend) : on les
// affiche systématiquement, même sans donnée, plutôt que de ne montrer que
// les surfaces déjà jouées — un axe sans échantillon reste visuellement
// distinct (secteur clair, pointillé) au lieu d'être masqué ou inventé.
const SURFACES = [
  { key: 'dur', label: 'Dur', color: '#0071E3' },
  { key: 'gazon', label: 'Gazon', color: '#1F8A6B' },
  { key: 'indoor', label: 'Indoor', color: '#7C5CFF' },
  { key: 'terre_battue', label: 'Terre battue', color: '#C1652E' },
]

const CX = 100
const CY = 100
const R = 72

function point(angle, r) {
  return [CX + r * Math.cos(angle), CY + r * Math.sin(angle)]
}

const sectors = computed(() => {
  const n = SURFACES.length
  return SURFACES.map((s, i) => {
    const data = props.bySurface.find((x) => x.surface === s.key)
    const axisAngle = (2 * Math.PI * i) / n - Math.PI / 2
    const start = axisAngle - Math.PI / n
    const end = axisAngle + Math.PI / n
    const hasData = Boolean(data)
    const radius = hasData ? Math.max(6, (data.accuracy / 100) * R) : R * 0.16
    const p1 = point(start, radius)
    const p2 = point(end, radius)
    const trackP1 = point(start, R)
    const trackP2 = point(end, R)
    const labelPos = point(axisAngle, R + 22)
    return {
      ...s,
      hasData,
      accuracy: data?.accuracy ?? null,
      sampleSize: data?.sampleSize ?? 0,
      path: `M ${CX},${CY} L ${p1[0]},${p1[1]} A ${radius},${radius} 0 0 1 ${p2[0]},${p2[1]} Z`,
      trackPath: `M ${CX},${CY} L ${trackP1[0]},${trackP1[1]} A ${R},${R} 0 0 1 ${trackP2[0]},${trackP2[1]} Z`,
      labelX: labelPos[0],
      labelY: labelPos[1],
    }
  })
})
</script>

<template>
  <div class="rose-wrap">
    <svg viewBox="0 0 200 200" width="200" height="200">
      <circle :cx="CX" :cy="CY" :r="R" fill="none" stroke="var(--admin-bg)" stroke-width="1" />
      <circle :cx="CX" :cy="CY" :r="R * 0.5" fill="none" stroke="var(--admin-bg)" stroke-width="1" />
      <path v-for="s in sectors" :key="'track-' + s.key" :d="s.trackPath" fill="var(--admin-bg)" />
      <path
        v-for="s in sectors"
        :key="s.key"
        :d="s.path"
        :fill="s.color"
        :fill-opacity="s.hasData ? 0.88 : 0.35"
        :stroke="s.color"
        stroke-width="1"
        :stroke-dasharray="s.hasData ? 'none' : '2 2'"
      />
      <circle :cx="CX" :cy="CY" r="34" fill="var(--admin-card)" />
      <text :x="CX" :y="CY - 4" text-anchor="middle" font-size="20" font-weight="700" fill="var(--ink)">
        {{ overall !== null ? Math.round(overall) + '%' : '—' }}
      </text>
      <text :x="CX" :y="CY + 14" text-anchor="middle" font-size="8" fill="var(--grey)">toutes surfaces</text>
    </svg>

    <div class="rose-legend">
      <div v-for="s in sectors" :key="'legend-' + s.key" class="rose-legend-item">
        <i :style="{ background: s.color, opacity: s.hasData ? 1 : 0.35 }"></i>
        <span class="rl-label">{{ s.label }}</span>
        <span class="rl-value">{{ s.hasData ? s.accuracy + ' %' : '—' }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.rose-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}
.rose-legend {
  width: 100%;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px 14px;
  margin-top: 4px;
}
.rose-legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
}
.rose-legend-item i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex: none;
}
.rl-label {
  color: var(--grey);
  flex: 1;
}
.rl-value {
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
</style>