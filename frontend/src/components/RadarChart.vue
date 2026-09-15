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
  // Clarté "qui le modèle donne gagnant ?" (15/09/2026) — ajoutée suite à un
  // retour explicite : le radar seul (deux polygones de couleur) ne dit pas
  // qui est le favori du modèle, ni — une fois le match terminé — si ce
  // pronostic s'est vérifié. 0 = joueur A (labelA), 1 = joueur B (labelB),
  // `null`/`undefined` = information non disponible (pas de prédiction, ou
  // page publique sans abonnement) : dans ce cas, aucune étiquette ni bandeau
  // ne s'affiche, le radar reste tel quel plutôt que d'afficher une valeur
  // inventée.
  favoriteIndex: { type: Number, default: null },
  winnerIndex: { type: Number, default: null },
  probabilityFavorite: { type: Number, default: null },
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

const hasFavorite = computed(() => props.favoriteIndex === 0 || props.favoriteIndex === 1)
const hasWinner = computed(() => props.winnerIndex === 0 || props.winnerIndex === 1)
// Un pronostic "confirmé" veut dire : le joueur donné favori par le modèle
// est bien celui qui a effectivement gagné — jamais déduit autrement.
const predictionCorrect = computed(() => (hasFavorite.value && hasWinner.value ? props.favoriteIndex === props.winnerIndex : null))
const favoriteName = computed(() => (props.favoriteIndex === 0 ? props.labelA : props.favoriteIndex === 1 ? props.labelB : null))
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
      <span :class="{ 'is-favorite': favoriteIndex === 0 }">
        <i style="background: var(--green)"></i>{{ labelA }}
        <b v-if="favoriteIndex === 0" class="tag fav">favori</b>
        <b v-if="winnerIndex === 0" class="tag win">✓ vainqueur</b>
      </span>
      <span :class="{ 'is-favorite': favoriteIndex === 1 }">
        <i style="background: var(--blue)"></i>{{ labelB }}
        <b v-if="favoriteIndex === 1" class="tag fav">favori</b>
        <b v-if="winnerIndex === 1" class="tag win">✓ vainqueur</b>
      </span>
    </div>

    <!-- Bandeau de synthèse : répond explicitement à "qui le modèle donne
         gagnant, et est-ce qu'il avait raison ?" plutôt que de laisser le
         radar seul le suggérer implicitement par ses couleurs. -->
    <div v-if="hasFavorite" class="verdict">
      <span class="verdict-line">
        Favori du modèle : <b>{{ favoriteName }}</b>
        <template v-if="probabilityFavorite !== null">({{ Math.round(probabilityFavorite * 100) }} %)</template>
      </span>
      <span v-if="predictionCorrect !== null" class="verdict-badge" :class="predictionCorrect ? 'ok' : 'bad'">
        {{ predictionCorrect ? '✓ Pronostic confirmé' : '✗ Le favori n’a pas gagné' }}
      </span>
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
  flex-wrap: wrap;
  justify-content: center;
  font-size: 12px;
}
.legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.legend i {
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  flex: none;
}
.legend .tag {
  font-size: 9.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  padding: 2px 6px;
  border-radius: 5px;
}
.legend .tag.fav {
  color: var(--green);
  background: rgba(15, 61, 62, 0.1);
}
.legend .tag.win {
  color: #1f7d33;
  background: #e6f9ea;
}

.verdict {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  text-align: center;
}
.verdict-line {
  font-size: 12.5px;
  color: var(--grey);
}
.verdict-line b {
  color: var(--ink);
}
.verdict-badge {
  font-size: 11.5px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 999px;
}
.verdict-badge.ok {
  color: #1f7d33;
  background: #e6f9ea;
}
.verdict-badge.bad {
  color: #b3261e;
  background: #fdecea;
}
</style>