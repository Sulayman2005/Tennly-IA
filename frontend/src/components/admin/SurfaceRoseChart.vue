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
// distinct (marqueur clair, trait pointillé) au lieu d'être masqué ou inventé.
const SURFACES = [
  { key: 'dur', label: 'Dur', color: '#0071E3' },
  { key: 'gazon', label: 'Gazon', color: '#1F8A6B' },
  { key: 'indoor', label: 'Indoor', color: '#7C5CFF' },
  { key: 'terre_battue', label: 'Terre battue', color: '#C1652E' },
]

const CX = 100
const CY = 100
const R = 66
const N = SURFACES.length

function point(angle, r) {
  return [CX + r * Math.cos(angle), CY + r * Math.sin(angle)]
}

function axisAngle(i) {
  return (2 * Math.PI * i) / N - Math.PI / 2
}

// Grille de fond : anneaux concentriques à 33/66/100 % du rayon, tracés comme
// des polygones à 4 côtés (et non des cercles) pour lire un vrai radar plutôt
// que l'ancienne rose en camembert.
const gridRings = computed(() =>
  [0.33, 0.66, 1].map((frac) =>
    Array.from({ length: N }, (_, i) => point(axisAngle(i), R * frac))
      .map((p) => p.join(','))
      .join(' '),
  ),
)

const axisEnds = computed(() => Array.from({ length: N }, (_, i) => point(axisAngle(i), R)))

const vertices = computed(() =>
  SURFACES.map((s, i) => {
    const data = props.bySurface.find((x) => x.surface === s.key)
    const hasData = Boolean(data)
    const radius = hasData ? Math.max(6, (data.accuracy / 100) * R) : R * 0.12
    const angle = axisAngle(i)
    const [x, y] = point(angle, radius)
    const [lx, ly] = point(angle, R + 24)
    return {
      ...s,
      hasData,
      accuracy: data?.accuracy ?? null,
      sampleSize: data?.sampleSize ?? 0,
      x,
      y,
      labelX: lx,
      labelY: ly,
    }
  }),
)

const polygonPoints = computed(() => vertices.value.map((v) => `${v.x},${v.y}`).join(' '))
</script>

<template>
  <div class="radar-wrap">
    <svg viewBox="0 0 200 200" width="200" height="200">
      <defs>
        <linearGradient id="radarFill" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="var(--lime)" stop-opacity="0.6" />
          <stop offset="100%" stop-color="var(--green)" stop-opacity="0.4" />
        </linearGradient>
      </defs>

      <polygon
        v-for="(ring, i) in gridRings"
        :key="'ring-' + i"
        :points="ring"
        fill="none"
        stroke="var(--admin-bg)"
        stroke-width="1.2"
      />
      <line
        v-for="(p, i) in axisEnds"
        :key="'axis-' + i"
        :x1="CX"
        :y1="CY"
        :x2="p[0]"
        :y2="p[1]"
        stroke="var(--admin-bg)"
        stroke-width="1.2"
      />

      <polygon
        :points="polygonPoints"
        fill="url(#radarFill)"
        stroke="var(--green)"
        stroke-width="1.6"
        stroke-linejoin="round"
      />

      <circle
        v-for="v in vertices"
        :key="'dot-' + v.key"
        :cx="v.x"
        :cy="v.y"
        r="4"
        :fill="v.hasData ? v.color : 'var(--admin-card)'"
        :stroke="v.color"
        stroke-width="1.6"
        :stroke-dasharray="v.hasData ? 'none' : '1.6 1.6'"
      />

      <circle :cx="CX" :cy="CY" r="25" fill="var(--admin-card)" />
      <text :x="CX" :y="CY - 3" text-anchor="middle" font-size="17" font-weight="700" fill="var(--ink)">
        {{ overall !== null ? Math.round(overall) + '%' : '—' }}
      </text>
      <text :x="CX" :y="CY + 11" text-anchor="middle" font-size="7" fill="var(--grey)">global</text>

      <text
        v-for="v in vertices"
        :key="'label-' + v.key"
        :x="v.labelX"
        :y="v.labelY"
        text-anchor="middle"
        font-size="8.5"
        font-weight="700"
        fill="var(--ink)"
      >
        {{ v.label }}
      </text>
    </svg>

    <div class="radar-legend">
      <div v-for="v in vertices" :key="'legend-' + v.key" class="radar-legend-item">
        <i :style="{ background: v.color, opacity: v.hasData ? 1 : 0.35 }"></i>
        <span class="rl-label">{{ v.label }}</span>
        <span class="rl-value">{{ v.hasData ? v.accuracy + ' %' : '—' }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.radar-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  max-width: 100%;
}
.radar-wrap svg {
  max-width: 100%;
  height: auto;
}
.radar-legend {
  width: 100%;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px 14px;
  margin-top: 4px;
}
.radar-legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
}
.radar-legend-item i {
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