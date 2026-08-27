<script setup>
import { ref, computed } from 'vue'
import { api, ApiError } from '@/api/client'
import RadarChart from '@/components/RadarChart.vue'
import TourBadge from '@/components/TourBadge.vue'

// Comparateur de joueurs, réservé aux abonnés + à l'admin (voir
// router/index.js et App.vue pour le contrôle d'accès côté navigation — le
// vrai garde-fou reste côté backend, sur GET /api/comparateur/analyser, voir
// ComparateurController).
//
// Deux niveaux d'information, volontairement séparés :
//  1. Une comparaison Elo instantanée (4 axes), calculée ici en local dès que
//     les deux joueurs sont choisis — aucun appel réseau, juste les champs
//     déjà présents sur Player.
//  2. Une "vraie" analyse IA à la demande (probabilité, confiance, facteurs,
//     radar 6 axes), déclenchée explicitement par le bouton "Lancer
//     l'analyse complète" : ça appelle le modèle XGBoost entraîné côté
//     backend (voir PlayerComparisonService.php), donc on ne le fait pas
//     automatiquement à chaque changement de joueur.

const RADAR_AXES_ELO = [
  { key: 'eloGlobal', label: 'Elo global' },
  { key: 'eloDur', label: 'Dur' },
  { key: 'eloTerre', label: 'Terre battue' },
  { key: 'eloGazon', label: 'Gazon' },
]

const SURFACES = [
  { value: 'dur', label: 'Dur' },
  { value: 'terre_battue', label: 'Terre battue' },
  { value: 'gazon', label: 'Gazon' },
]

function makeSlot() {
  return {
    query: ref(''),
    results: ref([]),
    loading: ref(false),
    error: ref(''),
    selected: ref(null),
    timer: null,
  }
}

const slotA = makeSlot()
const slotB = makeSlot()
const surface = ref('dur')

const analysis = ref(null)
const analysisLoading = ref(false)
const analysisError = ref('')

function resetAnalyse() {
  analysis.value = null
  analysisError.value = ''
}

async function search(slot, otherSlot) {
  const term = slot.query.value.trim()
  if (term.length < 2) {
    slot.results.value = []
    return
  }
  slot.loading.value = true
  slot.error.value = ''
  try {
    const data = await api.get(`/api/players?fullName=${encodeURIComponent(term)}`)
    const members = data['hydra:member'] || data['member'] || []
    // On retire le joueur déjà choisi dans l'autre slot : comparer un joueur
    // avec lui-même n'a pas de sens.
    slot.results.value = members.filter((p) => p.id !== otherSlot.selected.value?.id)
  } catch {
    slot.error.value = "Impossible de charger les joueurs pour l'instant — réessaie dans un instant."
    slot.results.value = []
  } finally {
    slot.loading.value = false
  }
}

function onInput(slot, otherSlot) {
  clearTimeout(slot.timer)
  slot.timer = setTimeout(() => search(slot, otherSlot), 300)
}

function select(slot, player) {
  slot.selected.value = player
  slot.query.value = ''
  slot.results.value = []
  resetAnalyse()
}

function reset(slot) {
  slot.selected.value = null
  slot.query.value = ''
  slot.results.value = []
  resetAnalyse()
}

function swap() {
  const tmp = slotA.selected.value
  slotA.selected.value = slotB.selected.value
  slotB.selected.value = tmp
  resetAnalyse()
}

function onSurfaceChange() {
  resetAnalyse()
}

// Même formule de normalisation que celle déjà utilisée côté ml-service pour
// l'axe "Elo surface" des radars d'analyse de match (clamp((elo-1500)/8)) —
// pour qu'un même score radar signifie la même chose partout dans l'app.
function normalizeElo(value) {
  return Math.max(1, Math.min(99, Math.round((value - 1500) / 8)))
}

const bothSelected = computed(() => Boolean(slotA.selected.value && slotB.selected.value))

// Le comparateur n'empêche pas de choisir deux joueurs de circuits
// différents, mais l'analyse IA reste alors calée sur le circuit du joueur A
// uniquement (voir PlayerComparisonService::analyser, tour_is_wta) — cas rare
// et peu sensé sportivement, qu'on préfère signaler plutôt que cacher.
const crossTour = computed(() =>
  bothSelected.value && slotA.selected.value.tour !== slotB.selected.value.tour,
)

const radarProfileElo = computed(() => {
  if (!bothSelected.value) return null
  const a = slotA.selected.value
  const b = slotB.selected.value
  return {
    eloGlobal: [normalizeElo(a.eloOverall), normalizeElo(b.eloOverall)],
    eloDur: [normalizeElo(a.eloHard), normalizeElo(b.eloHard)],
    eloTerre: [normalizeElo(a.eloClay), normalizeElo(b.eloClay)],
    eloGazon: [normalizeElo(a.eloGrass), normalizeElo(b.eloGrass)],
  }
})

function handLabel(hand) {
  if (hand === 'L') return 'Gaucher'
  if (hand === 'R') return 'Droitier'
  return 'Inconnue'
}

// Lignes du tableau de comparaison : `higher` indique si la meilleure valeur
// est la plus grande (Elo) ou la plus petite (classement — N°1 est le
// meilleur), pour savoir laquelle des deux colonnes mettre en avant.
const comparisonRows = computed(() => {
  if (!bothSelected.value) return []
  const a = slotA.selected.value
  const b = slotB.selected.value
  return [
    { label: 'Classement', valueA: a.atpWtaRank ? `N°${a.atpWtaRank}` : 'Inconnu', valueB: b.atpWtaRank ? `N°${b.atpWtaRank}` : 'Inconnu', rawA: a.atpWtaRank, rawB: b.atpWtaRank, higher: false },
    { label: 'Elo global', valueA: Math.round(a.eloOverall), valueB: Math.round(b.eloOverall), rawA: a.eloOverall, rawB: b.eloOverall, higher: true },
    { label: 'Elo dur', valueA: Math.round(a.eloHard), valueB: Math.round(b.eloHard), rawA: a.eloHard, rawB: b.eloHard, higher: true },
    { label: 'Elo terre battue', valueA: Math.round(a.eloClay), valueB: Math.round(b.eloClay), rawA: a.eloClay, rawB: b.eloClay, higher: true },
    { label: 'Elo gazon', valueA: Math.round(a.eloGrass), valueB: Math.round(b.eloGrass), rawA: a.eloGrass, rawB: b.eloGrass, higher: true },
    { label: 'Main', valueA: handLabel(a.dominantHand), valueB: handLabel(b.dominantHand), rawA: null, rawB: null, higher: true },
    { label: 'Pays', valueA: a.countryCode || 'Inconnu', valueB: b.countryCode || 'Inconnu', rawA: null, rawB: null, higher: true },
  ]
})

function winsA(row) {
  if (row.rawA == null || row.rawB == null || row.rawA === row.rawB) return false
  return row.higher ? row.rawA > row.rawB : row.rawA < row.rawB
}

function winsB(row) {
  if (row.rawA == null || row.rawB == null || row.rawA === row.rawB) return false
  return row.higher ? row.rawB > row.rawA : row.rawB < row.rawA
}

async function lancerAnalyse() {
  if (!bothSelected.value) return
  analysisLoading.value = true
  analysisError.value = ''
  analysis.value = null
  try {
    const params = new URLSearchParams({
      joueurA: String(slotA.selected.value.id),
      joueurB: String(slotB.selected.value.id),
      surface: surface.value,
    })
    analysis.value = await api.get(`/api/comparateur/analyser?${params.toString()}`)
  } catch (e) {
    analysisError.value =
      e instanceof ApiError && e.status === 403
        ? 'Analyse complète réservée aux abonnés et à l\'admin.'
        : "Impossible de lancer l'analyse pour l'instant — réessaie dans un instant."
  } finally {
    analysisLoading.value = false
  }
}

const favoriteLabel = computed(() => {
  if (!analysis.value) return ''
  return analysis.value.favoritePlayerId === slotA.selected.value?.id
    ? slotA.selected.value.fullName
    : slotB.selected.value.fullName
})

const confidenceMeta = computed(() => {
  const level = analysis.value?.confidenceLevel
  if (level === 'eleve') return { label: 'Confiance élevée', tone: 'ok' }
  if (level === 'moyen') return { label: 'Confiance moyenne', tone: 'mid' }
  return { label: 'Confiance faible', tone: 'warn' }
})

function factorPlayerLabel(factor) {
  return factor.favors === 'A' ? slotA.selected.value?.fullName : slotB.selected.value?.fullName
}
</script>

<template>
  <section class="comparateur">
    <h1>Comparateur</h1>
    <p class="subtitle">Compare deux joueurs et lance une analyse IA complète entre eux.</p>

    <div class="picker-grid">
      <div class="picker">
        <div v-if="slotA.selected.value" class="chosen chosen-a">
          <span class="chosen-name">
            <TourBadge :tour="slotA.selected.value.tour" />
            {{ slotA.selected.value.fullName }}
          </span>
          <button type="button" class="change-btn" @click="reset(slotA)">Changer</button>
        </div>
        <div v-else class="search-box">
          <input
            v-model="slotA.query.value"
            type="text"
            placeholder="Chercher le joueur A…"
            @input="onInput(slotA, slotB)"
          />
          <p v-if="slotA.error.value" class="error">{{ slotA.error.value }}</p>
          <ul v-else-if="slotA.results.value.length" class="results">
            <li v-for="p in slotA.results.value" :key="p.id">
              <button type="button" @click="select(slotA, p)">
                <span class="result-name"><TourBadge :tour="p.tour" /> {{ p.fullName }}</span>
                <span v-if="p.atpWtaRank" class="rank">N°{{ p.atpWtaRank }}</span>
              </button>
            </li>
          </ul>
          <p v-else-if="slotA.query.value.trim().length >= 2 && !slotA.loading.value" class="empty">
            Aucun joueur trouvé.
          </p>
        </div>
      </div>

      <button type="button" class="swap-btn" :disabled="!bothSelected" title="Inverser" @click="swap">
        VS
      </button>

      <div class="picker">
        <div v-if="slotB.selected.value" class="chosen chosen-b">
          <span class="chosen-name">
            <TourBadge :tour="slotB.selected.value.tour" />
            {{ slotB.selected.value.fullName }}
          </span>
          <button type="button" class="change-btn" @click="reset(slotB)">Changer</button>
        </div>
        <div v-else class="search-box">
          <input
            v-model="slotB.query.value"
            type="text"
            placeholder="Chercher le joueur B…"
            @input="onInput(slotB, slotA)"
          />
          <p v-if="slotB.error.value" class="error">{{ slotB.error.value }}</p>
          <ul v-else-if="slotB.results.value.length" class="results">
            <li v-for="p in slotB.results.value" :key="p.id">
              <button type="button" @click="select(slotB, p)">
                <span class="result-name"><TourBadge :tour="p.tour" /> {{ p.fullName }}</span>
                <span v-if="p.atpWtaRank" class="rank">N°{{ p.atpWtaRank }}</span>
              </button>
            </li>
          </ul>
          <p v-else-if="slotB.query.value.trim().length >= 2 && !slotB.loading.value" class="empty">
            Aucun joueur trouvé.
          </p>
        </div>
      </div>
    </div>

    <p v-if="!bothSelected" class="hint">
      Choisis deux joueurs (tape au moins 2 lettres de leur nom) pour voir la comparaison.
    </p>

    <div v-else class="comparison">
      <div class="radar-block">
        <RadarChart
          :profile="radarProfileElo"
          :axes="RADAR_AXES_ELO"
          :label-a="slotA.selected.value.fullName"
          :label-b="slotB.selected.value.fullName"
        />
      </div>

      <table class="stats-table">
        <thead>
          <tr>
            <th>{{ slotA.selected.value.fullName }}</th>
            <th></th>
            <th>{{ slotB.selected.value.fullName }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in comparisonRows" :key="row.label">
            <td :class="{ win: winsA(row) }">{{ row.valueA }}</td>
            <td class="label">{{ row.label }}</td>
            <td :class="{ win: winsB(row) }">{{ row.valueB }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="bothSelected" class="analyse-block">
      <h2>Analyse complète</h2>

      <p v-if="crossTour" class="cross-tour-note">
        Comparaison entre un circuit ATP et un circuit WTA : les deux joueurs
        ne s'affrontent jamais en réalité, l'analyse reste indicative.
      </p>

      <div class="analyse-controls">
        <label class="surface-label">
          Surface
          <select v-model="surface" @change="onSurfaceChange">
            <option v-for="s in SURFACES" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </label>
        <button type="button" class="analyse-btn" :disabled="analysisLoading" @click="lancerAnalyse">
          {{ analysisLoading ? 'Analyse en cours…' : 'Lancer l\'analyse complète' }}
        </button>
      </div>

      <p v-if="analysisError" class="error analyse-error">{{ analysisError }}</p>

      <div v-if="analysis" class="analyse-result">
        <div class="result-headline">
          <div class="proba-block">
            <span class="proba-value">{{ Math.round(analysis.probabilityFavorite * 100) }}%</span>
            <span class="proba-label">de chances pour {{ favoriteLabel }}</span>
          </div>
          <span class="confidence-badge" :class="`tone-${confidenceMeta.tone}`">{{ confidenceMeta.label }}</span>
        </div>

        <p v-if="!analysis.modelAvailable" class="model-fallback-note">
          Modèle IA momentanément indisponible — estimation basée sur le classement Elo.
        </p>

        <div class="radar-block">
          <RadarChart
            :profile="analysis.radar"
            :label-a="slotA.selected.value.fullName"
            :label-b="slotB.selected.value.fullName"
          />
        </div>

        <ul class="factors">
          <li v-for="(factor, i) in analysis.factors" :key="i" class="factor" :class="`tone-${factor.tone}`">
            <span class="factor-label">{{ factor.label }}</span>
            <span class="factor-detail">favorise {{ factorPlayerLabel(factor) }}</span>
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>

<style scoped>
.comparateur {
  padding: 40px 0 80px;
}

h1 {
  font-size: 32px;
  margin: 0 0 6px;
}

.subtitle {
  color: var(--grey);
  margin: 0 0 32px;
}

.picker-grid {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 20px;
  align-items: start;
}

@media (max-width: 720px) {
  .picker-grid {
    grid-template-columns: 1fr;
  }
}

.picker {
  min-height: 54px;
}

.search-box input {
  width: 100%;
  box-sizing: border-box;
  padding: 13px 16px;
  border: 1px solid var(--line);
  border-radius: 12px;
  font-size: 15px;
  background: var(--card);
  color: var(--ink);
}

.search-box input:focus {
  outline: 2px solid var(--green);
  outline-offset: -1px;
}

.results {
  list-style: none;
  margin: 8px 0 0;
  padding: 0;
  border: 1px solid var(--line);
  border-radius: 12px;
  overflow: hidden;
}

.results li + li {
  border-top: 1px solid var(--line);
}

.results button {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 11px 16px;
  background: none;
  border: none;
  text-align: left;
  font-size: 14px;
  cursor: pointer;
  color: var(--ink);
}

.results button:hover {
  background: var(--card);
}

.rank {
  font-size: 12px;
  color: var(--grey);
}

.empty,
.error {
  margin: 8px 0 0;
  font-size: 13px;
  color: var(--grey);
}

.chosen {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 13px 16px;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: var(--card);
}

.chosen-name {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
}

.result-name {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.cross-tour-note {
  margin: -6px 0 18px;
  font-size: 13px;
  color: var(--grey);
  font-style: italic;
}

.chosen-a .chosen-name {
  color: var(--green);
}

.chosen-b .chosen-name {
  color: var(--blue);
}

.change-btn {
  background: none;
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 6px 14px;
  font-size: 13px;
  cursor: pointer;
  color: var(--ink);
}

.change-btn:hover {
  background: #fff;
}

.swap-btn {
  align-self: center;
  margin-top: 14px;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 1px solid var(--line);
  background: var(--card);
  font-size: 12px;
  font-weight: 700;
  color: var(--grey);
  cursor: pointer;
}

.swap-btn:not(:disabled):hover {
  background: #fff;
  color: var(--ink);
}

.swap-btn:disabled {
  cursor: default;
  opacity: 0.5;
}

.hint {
  margin-top: 28px;
  color: var(--grey);
  font-size: 14px;
}

.comparison {
  margin-top: 40px;
  display: flex;
  flex-wrap: wrap;
  gap: 48px;
  align-items: flex-start;
}

.radar-block {
  flex: 0 0 auto;
}

.stats-table {
  flex: 1 1 320px;
  border-collapse: collapse;
  min-width: 280px;
}

.stats-table th {
  text-align: center;
  font-size: 13px;
  color: var(--grey);
  font-weight: 600;
  padding: 0 8px 12px;
}

.stats-table td {
  padding: 11px 8px;
  border-top: 1px solid var(--line);
  text-align: center;
  font-variant-numeric: tabular-nums;
}

.stats-table td.label {
  color: var(--grey);
  font-size: 13px;
}

.stats-table td.win {
  font-weight: 700;
  color: var(--green);
}

.analyse-block {
  margin-top: 56px;
  padding-top: 40px;
  border-top: 1px solid var(--line);
}

.analyse-block h2 {
  font-size: 22px;
  margin: 0 0 20px;
}

.analyse-controls {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.surface-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--grey);
}

.surface-label select {
  padding: 8px 12px;
  border-radius: 10px;
  border: 1px solid var(--line);
  background: var(--card);
  color: var(--ink);
  font-size: 14px;
}

.analyse-btn {
  padding: 12px 22px;
  border-radius: 999px;
  border: none;
  background: var(--green);
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
}

.analyse-btn:disabled {
  opacity: 0.6;
  cursor: default;
}

.analyse-error {
  margin-top: 16px;
}

.analyse-result {
  margin-top: 32px;
}

.result-headline {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}

.proba-block {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.proba-value {
  font-size: 40px;
  font-weight: 700;
  color: var(--green);
  font-variant-numeric: tabular-nums;
}

.proba-label {
  font-size: 14px;
  color: var(--grey);
}

.confidence-badge {
  padding: 6px 14px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.confidence-badge.tone-ok {
  background: rgba(15, 61, 62, 0.12);
  color: var(--green);
}

.confidence-badge.tone-mid {
  background: rgba(0, 113, 227, 0.12);
  color: var(--blue);
}

.confidence-badge.tone-warn {
  background: rgba(0, 0, 0, 0.06);
  color: var(--grey);
}

.model-fallback-note {
  margin: 14px 0 0;
  font-size: 13px;
  color: var(--grey);
  font-style: italic;
}

.analyse-result .radar-block {
  margin-top: 28px;
}

.factors {
  list-style: none;
  margin: 28px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-width: 520px;
}

.factor {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 11px 16px;
  border-radius: 10px;
  border: 1px solid var(--line);
  font-size: 14px;
}

.factor-label {
  color: var(--ink);
}

.factor-detail {
  color: var(--grey);
  white-space: nowrap;
}

.factor.tone-warn .factor-detail {
  color: var(--blue);
}
</style>