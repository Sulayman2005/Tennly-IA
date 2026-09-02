<script setup>
import { computed } from 'vue'

const props = defineProps({
  /** { <cle-axe>: [a,b], ... }, valeurs 0-100 — les clés doivent correspondre à celles de `axes`. */
  profile: { type: Object, required: true },
  labelA: { type: String, required: true },
  labelB: { type: String, required: true },
  // Personnalise les axes affichés — utilisé par ComparateurView.vue, qui
  // compare deux joueurs hors contexte d'un match précis (donc pas les mêmes
  // signaux disponibles que le radar d'analyse de match). Par défaut : les
  // 6 axes historiques du radar d'analyse de match (MatchDetailView.vue),
  // comportement inchangé pour tout le reste de l'app. Le littéral est
  // recopié directement ici (et non référencé via une constante externe) car
  // le compilateur Vue interdit à defineProps() de référencer une variable
  // déclarée ailleurs dans <script setup> (son contenu est hoisté hors de
  // setup()).
  axes: {
    type: Array,
    default: () => [
      { key: 'eloSurface', label: 'Elo surface' },
      { key: 'forme', label: 'Forme' },
      { key: 'service', label: 'Service' },
      { key: 'retour', label: 'Retour' },
      { key: 'repos', label: 'Repos' },
      { key: 'h2h', label: 'H2H' },
    ],
  },
})

const axes = computed(() => props.axes)

const CX = 110
const CY = 110
const R = 90
const N = computed(() => axes.value.length)

function pointFor(index, value) {
  const angle = (Math.PI * 2 * index) / N.value - Math.PI / 2
  const dist = (Math.max(0, Math.min(100, value)) / 100) * R
  return [CX + dist * Math.cos(angle), CY + dist * Math.sin(angle)]
}

function axisEndpoint(index) {
  const angle = (Math.PI * 2 * index) / N.value - Math.PI / 2
  return [CX + R * Math.cos(angle), CY + R * Math.sin(angle)]
}

function polygonPoints(playerIndex) {
  return axes.value
    .map((axis, i) => pointFor(i, props.profile[axis.key]?.[playerIndex] ?? 0).join(','))
    .join(' ')
}

const pointsA = computed(() => polygonPoints(0))
const pointsB = computed(() => polygonPoints(1))
const axisLines = computed(() => axes.value.map((axis, i) => ({ ...axis, end: axisEndpoint(i) })))
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
  max-width: 100%;
}
.radar-wrap svg {
  max-width: 100%;
  height: auto;
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