<script setup>
import { computed } from 'vue'

const props = defineProps({
  /** { eloSurface: [a,b], forme: [a,b], service: [a,b], retour: [a,b], repos: [a,b], h2h: [a,b] }, valeurs 0-100. */
  profile: { type: Object, required: true },
  labelA: { type: String, required: true },
  labelB: { type: String, required: true },
})

const axes = [
  { key: 'eloSurface', label: 'Elo surface' },
  { key: 'forme', label: 'Forme' },
  { key: 'service', label: 'Service' },
  { key: 'retour', label: 'Retour' },
  { key: 'repos', label: 'Repos' },
  { key: 'h2h', label: 'H2H' },
]

const CX = 110
const CY = 110
const R = 90
const N = axes.length

function pointFor(index, value) {
  const angle = (Math.PI * 2 * index) / N - Math.PI / 2
  const dist = (Math.max(0, Math.min(100, value)) / 100) * R
  return [CX + dist * Math.cos(angle), CY + dist * Math.sin(angle)]
}

function axisEndpoint(index) {
  const angle = (Math.PI * 2 * index) / N - Math.PI / 2
  return [CX + R * Math.cos(angle), CY + R * Math.sin(angle)]
}

function polygonPoints(playerIndex) {
  return axes
    .map((axis, i) => pointFor(i, props.profile[axis.key]?.[playerIndex] ?? 0).join(','))
    .join(' ')
}

const pointsA = computed(() => polygonPoints(0))
const pointsB = computed(() => polygonPoints(1))
const axisLines = computed(() => axes.map((axis, i) => ({ ...axis, end: axisEndpoint(i) })))
</script>

<template>
  <div class="radar-wrap">
    <svg viewBox="0 0 220 220" width="220" height="220">
      <g v-for="ring in [0.25, 0.5, 0.75, 1]" :key="ring">
        <polygon
          :points="axes.map((_, i) => pointFor(i, ring * 100).join(',')).join(' ')"
          fill="none"
          stroke="var(--line)"
          stroke-width="1"
        />
      </g>
      <line v-for="(axis, i) in axisLines" :key="axis.key" :x1="CX" :y1="CY" :x2="axis.end[0]" :y2="axis.end[1]" stroke="var(--line)" />
      <polygon :points="pointsA" fill="rgba(15,61,62,.20)" stroke="var(--green)" stroke-width="2" />
      <polygon :points="pointsB" fill="rgba(0,113,227,.14)" stroke="var(--blue)" stroke-width="2" />
      <text
        v-for="(axis, i) in axisLines"
        :key="'label-' + axis.key"
        :x="axis.end[0]"
        :y="axis.end[1]"
        font-size="10"
        fill="var(--grey)"
        text-anchor="middle"
      >
        {{ axis.label }}
      </text>
    </svg>
    <div class="legend">
      <span><i style="background: var(--green)"></i>{{ labelA }}</span>
      <span><i style="background: var(--blue)"></i>{{ labelB }}</span>
    </div>
  </div>
</template>

<style scoped>
.radar-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}
.legend {
  display: flex;
  gap: 16px;
  font-size: 12px;
}
.legend i {
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  margin-right: 6px;
}
</style>
