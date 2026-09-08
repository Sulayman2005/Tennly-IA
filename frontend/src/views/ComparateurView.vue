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
//  2. Une "vraie" analyse à la demande (probabilité, confiance, facteurs,
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
// différents, mais l'analyse reste alors calée sur le circuit du joueur A
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

// Initiales pour l'avatar rond des cartes joueur choisi — même convention que
// MatchDetailView.vue (rien à voir avec TourBadge, purement décoratif).
function initials(fullName) {
  return (fullName || '').split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase()
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
    <div class="page-head">
      <div class="eyebrow"><i></i>TENNIS · COMPARATEUR</div>
      <h1>Mets deux joueurs <span class="accent">face à face</span>.</h1>
      <p class="subtitle">Comparaison Elo instantanée dès que les deux joueurs sont choisis, puis une analyse complète à la demande — probabilité, confiance et facteurs d'explication.</p>
    </div>

    <div class="picker-grid">
      <div class="picker">
        <div v-if="slotA.selected.value" class="chosen-card side-a">
          <button type="button" class="change-btn" title="Changer de joueur" @click="reset(slotA)">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none"><path d="M4 4l16 16M20 4L4 20" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" /></svg>
          </button>
          <div class="chosen-avatar">{{ initials(slotA.selected.value.fullName) }}</div>
          <div class="chosen-name">{{ slotA.selected.value.fullName }}</div>
          <TourBadge :tour="slotA.selected.value.tour" on-dark />
          <div class="chosen-meta">
            <span v-if="slotA.selected.value.atpWtaRank">N°{{ slotA.selected.value.atpWtaRank }} mondial</span>
            <span class="elo-chip">Elo {{ Math.round(slotA.selected.value.eloOverall) }}</span>
          </div>
        </div>
        <div v-else class="search-box">
          <div class="search-field">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none"><circle cx="11" cy="11" r="7" stroke="currentColor" stroke-width="2" /><path d="M20 20l-3.2-3.2" stroke="currentColor" stroke-width="2" stroke-linecap="round" /></svg>
            <input
              v-model="slotA.query.value"
              type="text"
              placeholder="Chercher le joueur A…"
              @input="onInput(slotA, slotB)"
            />
          </div>
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

      <button type="button" class="swap-btn" :disabled="!bothSelected" title="Inverser les deux joueurs" @click="swap">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none"><path d="M7 7h11m0 0l-4-4m4 4l-4 4M17 17H6m0 0l4 4m-4-4l4-4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" /></svg>
        <span>VS</span>
      </button>

      <div class="picker">
        <div v-if="slotB.selected.value" class="chosen-card side-b">
          <button type="button" class="change-btn" title="Changer de joueur" @click="reset(slotB)">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none"><path d="M4 4l16 16M20 4L4 20" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" /></svg>
          </button>
          <div class="chosen-avatar">{{ initials(slotB.selected.value.fullName) }}</div>
          <div class="chosen-name">{{ slotB.selected.value.fullName }}</div>
          <TourBadge :tour="slotB.selected.value.tour" on-dark />
          <div class="chosen-meta">
            <span v-if="slotB.selected.value.atpWtaRank">N°{{ slotB.selected.value.atpWtaRank }} mondial</span>
            <span class="elo-chip">Elo {{ Math.round(slotB.selected.value.eloOverall) }}</span>
          </div>
        </div>
        <div v-else class="search-box">
          <div class="search-field">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none"><circle cx="11" cy="11" r="7" stroke="currentColor" stroke-width="2" /><path d="M20 20l-3.2-3.2" stroke="currentColor" stroke-width="2" stroke-linecap="round" /></svg>
            <input
              v-model="slotB.query.value"
              type="text"
              placeholder="Chercher le joueur B…"
              @input="onInput(slotB, slotA)"
            />
          </div>
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
      <span class="hint-icon">🎾</span>
      Choisis deux joueurs (tape au moins 2 lettres de leur nom) pour voir la comparaison.
    </p>

    <div v-else class="comparison">
      <div class="card radar-card">
        <h3>Profil Elo par surface</h3>
        <RadarChart
          :profile="radarProfileElo"
          :axes="RADAR_AXES_ELO"
          :label-a="slotA.selected.value.fullName"
          :label-b="slotB.selected.value.fullName"
        />
      </div>

      <div class="card table-card">
        <h3>Comparatif détaillé</h3>
        <div class="stats-table-wrap">
          <table class="stats-table">
            <thead>
              <tr>
                <th class="th-a">{{ slotA.selected.value.fullName }}</th>
                <th></th>
                <th class="th-b">{{ slotB.selected.value.fullName }}</th>
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
      </div>
    </div>

    <div v-if="bothSelected" class="card analyse-block">
      <div class="analyse-head">
        <h2>Analyse complète</h2>
        <p class="analyse-sub">Probabilité, niveau de confiance et facteurs d'explication, calculés par le modèle entraîné sur l'historique ATP/WTA réel.</p>
      </div>

      <p v-if="crossTour" class="cross-tour-note">
        ⚠️ Comparaison entre un circuit ATP et un circuit WTA : les deux joueurs
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
            <span class="proba-label">de chances pour <b>{{ favoriteLabel }}</b></span>
          </div>
          <span class="confidence-badge" :class="`tone-${confidenceMeta.tone}`">{{ confidenceMeta.label }}</span>
        </div>

        <p v-if="!analysis.modelAvailable" class="model-fallback-note">
          Modèle momentanément indisponible — estimation basée sur le classement Elo.
        </p>

        <div class="radar-block-inner">
          <RadarChart
            :profile="analysis.radar"
            :label-a="slotA.selected.value.fullName"
            :label-b="slotB.selected.value.fullName"
          />
        </div>

        <ul class="factors">
          <li v-for="(factor, i) in analysis.factors" :key="i" class="factor">
            <span class="tag" :class="factor.tone === 'warn' ? 'warn' : 'ok'">{{ factor.tone === 'warn' ? '!' : '✓' }}</span>
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
  padding: 48px 0 80px;
}

@keyframes fadeUp {
  from {
    opacity: 0;
    transform: translateY(18px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
@media (prefers-reduced-motion: reduce) {
  .page-head,
  .picker-grid,
  .comparison,
  .analyse-block {
    animation-duration: 0.001ms !important;
  }
}

/* -- En-tête -- */
.page-head {
  max-width: 640px;
  margin: 0 0 40px;
  animation: fadeUp 0.55s ease both;
}
.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--green);
  margin: 0 0 14px;
}
.eyebrow i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--lime);
  box-shadow: 0 0 0 3px rgba(199, 255, 60, 0.25);
}
h1 {
  font-size: 34px;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.1;
  margin: 0 0 12px;
  text-wrap: balance;
}
h1 .accent {
  background: linear-gradient(90deg, var(--green), #1f8a6b);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.subtitle {
  font-size: 16px;
  color: var(--grey);
  line-height: 1.55;
  margin: 0;
}

/* -- Sélection des joueurs -- */
.picker-grid {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 20px;
  align-items: stretch;
  animation: fadeUp 0.55s 0.06s ease both;
}

@media (max-width: 720px) {
  .picker-grid {
    grid-template-columns: 1fr;
  }
  .swap-btn {
    justify-self: center;
  }
  .comparison {
    gap: 20px;
  }
  .radar-card,
  .table-card {
    width: 100%;
    box-sizing: border-box;
  }
}

@media (max-width: 480px) {
  .comparateur {
    padding: 32px 0 60px;
  }
  h1 {
    font-size: 26px;
  }
  .subtitle {
    font-size: 14.5px;
  }
  .chosen-card {
    padding: 22px 18px 18px;
  }
  .chosen-avatar {
    width: 50px;
    height: 50px;
    font-size: 17px;
  }
  .card {
    padding: 20px;
  }
  .proba-value {
    font-size: 32px;
  }
  .result-headline {
    gap: 14px;
  }
  .analyse-controls {
    gap: 12px;
  }
  .factor {
    flex-wrap: wrap;
  }
  .hint {
    padding: 16px 18px;
  }
}

/* Carte joueur choisi — même palette green/blue que le reste de l'app */
.chosen-card {
  position: relative;
  height: 100%;
  box-sizing: border-box;
  border-radius: var(--radius-card);
  padding: 28px 24px 24px;
  color: #fff;
  text-align: center;
  box-shadow: var(--shadow-soft);
  display: flex;
  flex-direction: column;
  align-items: center;
  animation: fadeUp 0.4s ease both;
}
.chosen-card.side-a {
  background: linear-gradient(150deg, var(--green) 0%, var(--green2) 100%);
}
.chosen-card.side-b {
  background: linear-gradient(150deg, var(--blue) 0%, #0058b8 100%);
}
.change-btn {
  position: absolute;
  top: 14px;
  right: 14px;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.16);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.15s ease;
}
.change-btn:hover {
  background: rgba(255, 255, 255, 0.32);
}
.chosen-avatar {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.16);
  border: 1.5px solid rgba(255, 255, 255, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 12px;
  flex: none;
}
.chosen-name {
  font-size: 17px;
  font-weight: 700;
  margin-bottom: 8px;
}
.chosen-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: center;
  margin-top: 14px;
  font-size: 12.5px;
  color: rgba(255, 255, 255, 0.85);
}
.elo-chip {
  background: rgba(255, 255, 255, 0.16);
  padding: 3px 10px;
  border-radius: 999px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

/* Recherche joueur */
.search-field {
  position: relative;
  display: flex;
  align-items: center;
}
.search-field svg {
  position: absolute;
  left: 15px;
  color: var(--grey);
  pointer-events: none;
}
.search-box input {
  width: 100%;
  box-sizing: border-box;
  padding: 15px 16px 15px 42px;
  border: 1px solid var(--line);
  border-radius: 14px;
  font-size: 15px;
  background: var(--card);
  color: var(--ink);
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}
.search-box input:focus {
  outline: none;
  border-color: var(--green);
  box-shadow: 0 0 0 3px rgba(31, 141, 107, 0.14);
}

.results {
  list-style: none;
  margin: 10px 0 0;
  padding: 0;
  border: 1px solid var(--line);
  border-radius: 14px;
  overflow: hidden;
  background: var(--card);
  box-shadow: var(--shadow-soft);
}

.results li + li {
  border-top: 1px solid var(--line);
}

.results button {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: none;
  border: none;
  text-align: left;
  font-size: 14px;
  cursor: pointer;
  color: var(--ink);
  transition: background 0.12s ease;
}

.results button:hover {
  background: var(--bg);
}

.result-name {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.rank {
  font-size: 12px;
  color: var(--grey);
}

.empty,
.error {
  margin: 10px 4px 0;
  font-size: 13px;
  color: var(--grey);
}

.cross-tour-note {
  margin: 0 0 18px;
  font-size: 13px;
  color: #8a6100;
  background: #fff8e6;
  border: 1px solid #f0d98c;
  border-radius: 12px;
  padding: 12px 16px;
  line-height: 1.5;
}

/* Bouton d'inversion */
.swap-btn {
  align-self: center;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  border: 1px solid var(--line);
  background: var(--card);
  box-shadow: var(--shadow-soft);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.05em;
  color: var(--grey);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  transition:
    transform 0.2s ease,
    color 0.15s ease,
    border-color 0.15s ease;
}
.swap-btn svg {
  transition: transform 0.3s ease;
}
.swap-btn:not(:disabled):hover {
  color: var(--green);
  border-color: var(--green);
  transform: scale(1.06);
}
.swap-btn:not(:disabled):hover svg {
  transform: rotate(180deg);
}
.swap-btn:disabled {
  cursor: default;
  opacity: 0.45;
}

.hint {
  margin-top: 32px;
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--grey);
  font-size: 14px;
  border: 1.5px dashed var(--line);
  border-radius: 18px;
  padding: 20px 24px;
}
.hint-icon {
  font-size: 18px;
}

/* -- Comparatif Elo -- */
.comparison {
  margin-top: 40px;
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
  align-items: stretch;
  animation: fadeUp 0.55s 0.06s ease both;
}

.card {
  background: var(--card);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-soft);
  padding: 28px;
}

.radar-card {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.table-card {
  flex: 1 1 320px;
  min-width: 0;
}
.radar-card h3,
.table-card h3 {
  align-self: flex-start;
  font-size: 15px;
  font-weight: 700;
  margin: 0 0 20px;
}

.stats-table-wrap {
  overflow-x: auto;
  width: 100%;
}

.stats-table {
  border-collapse: collapse;
  min-width: 280px;
  width: 100%;
}

.stats-table th {
  text-align: center;
  font-size: 13px;
  font-weight: 700;
  padding: 0 8px 14px;
}

.stats-table th.th-a {
  color: var(--green);
}
.stats-table th.th-b {
  color: var(--blue);
}

.stats-table td {
  padding: 12px 8px;
  border-top: 1px solid var(--line);
  text-align: center;
  font-variant-numeric: tabular-nums;
  font-size: 14px;
}

.stats-table td.label {
  color: var(--grey);
  font-size: 12.5px;
}

.stats-table td.win {
  font-weight: 700;
  color: var(--green);
}

/* -- Analyse complète -- */
.analyse-block {
  margin-top: 48px;
  animation: fadeUp 0.55s 0.06s ease both;
}

.analyse-head h2 {
  font-size: 21px;
  margin: 0 0 6px;
}

.analyse-sub {
  font-size: 13.5px;
  color: var(--grey);
  margin: 0 0 22px;
  max-width: 560px;
  line-height: 1.55;
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
  gap: 10px;
  font-size: 13px;
  font-weight: 600;
  color: var(--grey);
}

.surface-label select {
  padding: 10px 14px;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: var(--bg);
  color: var(--ink);
  font-size: 13px;
  font-weight: 600;
}

.analyse-btn {
  padding: 13px 26px;
  border-radius: 999px;
  border: none;
  background: var(--btn);
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: var(--shadow-soft);
  transition: transform 0.15s ease;
}
.analyse-btn:hover:not(:disabled) {
  transform: translateY(-2px);
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
  padding-top: 32px;
  border-top: 1px solid var(--line);
}

.result-headline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  flex-wrap: wrap;
}

.proba-block {
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
}

.proba-value {
  font-size: 44px;
  font-weight: 800;
  letter-spacing: -0.02em;
  background: linear-gradient(90deg, var(--green), #1f8a6b);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  font-variant-numeric: tabular-nums;
}

.proba-label {
  font-size: 14px;
  color: var(--grey);
}
.proba-label b {
  color: var(--ink);
}

.confidence-badge {
  padding: 7px 16px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
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
  margin: 16px 0 0;
  font-size: 13px;
  color: var(--grey);
  font-style: italic;
}

.radar-block-inner {
  margin-top: 28px;
  display: flex;
  justify-content: center;
}

.factors {
  list-style: none;
  margin: 28px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-width: 560px;
}

.factor {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 13px 16px;
  border-radius: 12px;
  border: 1px solid var(--line);
  font-size: 14px;
}

.tag {
  flex: none;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
}
.tag.ok {
  background: #e6f9ea;
  color: #1f7d33;
}
.tag.warn {
  background: #fff3cd;
  color: #8a6100;
}

.factor-label {
  flex: 1;
  color: var(--ink);
}

.factor-detail {
  color: var(--grey);
  font-size: 12.5px;
  white-space: nowrap;
}
</style>