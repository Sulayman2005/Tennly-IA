<script setup>
import { computed, reactive, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, ApiError } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import RadarChart from '@/components/RadarChart.vue'
import PaywallModal from '@/components/PaywallModal.vue'
import PostPaymentModal from '@/components/PostPaymentModal.vue'
import TourBadge from '@/components/TourBadge.vue'
import ProbabilityGauge from '@/components/ProbabilityGauge.vue'
import { initials, avatarGradient, flagUrl, surfaceCardVars, hasPhoto, surfaceLabel, eloForSurface, handLabel } from '@/utils/playerVisuals'

const props = defineProps({ id: { type: [String, Number], required: true } })
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

function goToLogin() {
  router.push({ name: 'connexion', query: { redirect: route.fullPath } })
}

function isFavorite(player) {
  return match.value?.prediction?.favoritePlayer?.id === player.id
}

// Même repli photo → avatar initiales qu'en liste (MatchCard.vue) : voir
// son commentaire sur photoErrored/showPhoto pour le pourquoi (URL Wikimedia
// en base mais image devenue inaccessible).
const photoErrored = reactive(new Set())
function onPhotoError(playerId) {
  photoErrored.add(playerId)
}
function showPhoto(player) {
  return hasPhoto(player) && !photoErrored.has(player.id)
}

const match = ref(null)
const prediction = ref(null)
const loading = ref(true)
const forbidden = ref(false)
const paywallOpen = ref(false)
const postPaymentOpen = ref(false)

// Carte "résultat" (11/09/2026) : visuel dédié affiché uniquement une fois
// le match terminé (status 'finished'/'walkover' avec un winner connu — un
// match 'live', par ex., n'a pas encore de vainqueur et ne doit rien
// afficher ici). `winner` est une vraie relation Player (Groups
// 'match:read' déjà présent sur TennisMatch::$winner), donc match.winner
// porte les mêmes champs que playerA/playerB (photoUrl, countryCode, etc.).
const matchLoser = computed(() => {
  const m = match.value
  if (!m?.winner) return null
  return m.winner.id === m.playerA.id ? m.playerB : m.playerA
})

// Découpe "6-7, 6-1, 6-3, 1-6, 7-6" (voir build_score_text() dans
// update_match_results.py) en sets individuels, avec le camp gagnant de
// CHAQUE set déduit du nombre de jeux le plus élevé — le premier nombre de
// chaque paire est TOUJOURS celui de playerA (voir le commentaire sur le
// mapping p1/p2 -> player_a_id/player_b_id dans import_upcoming_matches.py,
// respecté à l'identique par le script de clôture). Purement indicatif
// (mise en valeur visuelle set par set) : en cas de nombres égaux ou
// illisibles, le set est affiché sans mise en valeur plutôt que de deviner.
const resultSets = computed(() => {
  const m = match.value
  if (!m?.scoreText) return []
  return m.scoreText.split(',').map((part) => {
    const text = part.trim()
    const [a, b] = text.split('-').map((n) => parseInt(n.trim(), 10))
    if (Number.isNaN(a) || Number.isNaN(b) || a === b) return { text, wonByWinner: null }
    const aWonSet = a > b
    const winnerIsPlayerA = m.winner?.id === m.playerA.id
    return { text, wonByWinner: aWonSet === winnerIsPlayerA }
  })
})

// Palmarès carrière (table player_career_stats, cf.
// PlayerCareerStatsController) : réservé aux abonnés comme prediction, donc
// chargé juste après elle dans loadMatch(). Certains joueurs n'ont pas de
// ligne (import LiveTennisAPI encore partiel) — fetchCareerStats renvoie
// alors null sans lever d'erreur, et careerRows masque la carte entière si
// aucun des deux joueurs n'a la moindre donnée.
const careerStatsA = ref(null)
const careerStatsB = ref(null)

// Bilan des confrontations directes entre les deux joueurs de CE match
// précis (table player_head_to_head, cf. PlayerHeadToHeadController) — même
// donnée que celle qui alimente déjà l'axe "H2H" du radar comparatif, mais
// ici sous forme du vrai décompte de victoires plutôt qu'un score normalisé.
// null tant qu'aucune confrontation n'est connue en base (jamais joué l'un
// contre l'autre, ou historique pas encore importé) — la carte est alors
// simplement masquée, jamais un "0-0" trompeur.
const headToHead = ref(null)

// L'endpoint renvoie du JSON brut via Doctrine DBAL (fetchAssociative), donc
// des clés snake_case telles quelles en base (wins_hard, first_in_pct, …) —
// pas de camelCase ici, contrairement aux entités normalisées par API Platform.
async function fetchCareerStats(playerId) {
  try {
    return await api.get(`/api/players/${playerId}/career-stats`)
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null
    console.error(e)
    return null
  }
}

async function fetchHeadToHead(playerId, opponentId) {
  try {
    return await api.get(`/api/players/${playerId}/head-to-head/${opponentId}`)
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null
    console.error(e)
    return null
  }
}

// "Forme du moment" (table player_snapshot, cf. PlayerSnapshotController) :
// les mêmes chiffres qui alimentent déjà EN INTERNE les axes "Service",
// "Retour", "Forme" et "Repos" du radar comparatif (normalisés 1-99 côté
// backend) — ici sous leur vraie valeur (jours, minutes, %, delta Elo), qui
// n'était jusqu'ici visible nulle part.
const snapshotA = ref(null)
const snapshotB = ref(null)

async function fetchSnapshot(playerId) {
  try {
    return await api.get(`/api/players/${playerId}/snapshot`)
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null
    console.error(e)
    return null
  }
}

function pctRow(label, statsA, statsB, key, { higher = true } = {}) {
  const rawA = statsA?.[key]
  const rawB = statsB?.[key]
  const a = rawA != null ? Math.round(rawA * 1000) / 10 : null
  const b = rawB != null ? Math.round(rawB * 1000) / 10 : null
  if (a == null && b == null) return null
  return {
    label,
    valueA: a != null ? `${a}%` : '—',
    valueB: b != null ? `${b}%` : '—',
    rawA: a,
    rawB: b,
    higher,
  }
}

function numberRow(label, statsA, statsB, key, { suffix = '', higher = true, compare = true, signed = false } = {}) {
  const rawA = statsA?.[key] ?? null
  const rawB = statsB?.[key] ?? null
  if (rawA == null && rawB == null) return null
  const fmt = (v) => {
    if (v == null) return '—'
    const n = Math.round(v)
    return signed && n > 0 ? `+${n}${suffix}` : `${n}${suffix}`
  }
  return {
    label,
    valueA: fmt(rawA),
    valueB: fmt(rawB),
    rawA: compare ? rawA : null,
    rawB: compare ? rawB : null,
    higher,
  }
}

const snapshotRows = computed(() => {
  if (!snapshotA.value && !snapshotB.value) return []
  const a = snapshotA.value
  const b = snapshotB.value

  return [
    pctRow('Forme récente (victoires)', a, b, 'recent_form'),
    numberRow('Dynamique (Elo, 8 derniers matchs)', a, b, 'momentum', { signed: true }),
    numberRow('Repos avant ce match', a, b, 'days_rest', { suffix: ' j', compare: false }),
    numberRow('Minutes jouées (10 derniers jours)', a, b, 'fatigue_minutes', { suffix: ' min', higher: false }),
    pctRow("Taux d'exploit (vs mieux classé)", a, b, 'upset_rate'),
    pctRow('Efficacité vs gauchers', a, b, 'winrate_vs_left'),
    pctRow('Efficacité vs droitiers', a, b, 'winrate_vs_right'),
    numberRow('Indice de service', a, b, 'serve_score'),
    numberRow('Indice de retour', a, b, 'return_score'),
  ].filter(Boolean)
})

// Association surface du match → colonnes bilan carrière correspondantes.
// 'indoor' est rapproché de carpet faute d'une colonne indoor dédiée dans
// player_career_stats (hard/clay/grass/carpet seulement).
const SURFACE_CAREER_FIELD = {
  dur: { wins: 'wins_hard', losses: 'losses_hard', label: 'sur dur' },
  terre_battue: { wins: 'wins_clay', losses: 'losses_clay', label: 'sur terre battue' },
  gazon: { wins: 'wins_grass', losses: 'losses_grass', label: 'sur gazon' },
  indoor: { wins: 'wins_carpet', losses: 'losses_carpet', label: 'en indoor' },
}

function winPct(wins, losses) {
  const total = (wins ?? 0) + (losses ?? 0)
  if (!total) return null
  return Math.round((wins / total) * 1000) / 10
}

function recordRow(label, statsA, statsB, winsKey, lossesKey) {
  const wA = statsA?.[winsKey]
  const lA = statsA?.[lossesKey]
  const wB = statsB?.[winsKey]
  const lB = statsB?.[lossesKey]
  const pctA = wA != null && lA != null ? winPct(wA, lA) : null
  const pctB = wB != null && lB != null ? winPct(wB, lB) : null
  if (pctA == null && pctB == null) return null
  return {
    label,
    valueA: pctA != null ? `${wA}V-${lA}D (${pctA}%)` : '—',
    valueB: pctB != null ? `${wB}V-${lB}D (${pctB}%)` : '—',
    rawA: pctA,
    rawB: pctB,
    higher: true,
  }
}

function statRow(label, statsA, statsB, key, { suffix = '', higher = true } = {}) {
  const rawA = statsA?.[key] ?? null
  const rawB = statsB?.[key] ?? null
  if (rawA == null && rawB == null) return null
  return {
    label,
    valueA: rawA != null ? `${rawA}${suffix}` : '—',
    valueB: rawB != null ? `${rawB}${suffix}` : '—',
    rawA,
    rawB,
    higher,
  }
}

const careerRows = computed(() => {
  if (!careerStatsA.value && !careerStatsB.value) return []
  const a = careerStatsA.value
  const b = careerStatsB.value
  const rows = [recordRow('Bilan carrière', a, b, 'wins', 'losses')]

  const surfaceField = SURFACE_CAREER_FIELD[match.value?.surface]
  if (surfaceField) {
    rows.push(recordRow(`Bilan ${surfaceField.label}`, a, b, surfaceField.wins, surfaceField.losses))
  }

  rows.push(
    statRow('Titres', a, b, 'titles'),
    statRow('Aces / match', a, b, 'aces_per_match'),
    statRow('Doubles fautes', a, b, 'double_faults', { higher: false }),
    statRow('1ères balles in', a, b, 'first_in_pct', { suffix: '%' }),
    statRow('Pts gagnés en 1ère balle', a, b, 'first_won_pct', { suffix: '%' }),
    statRow('Pts gagnés en 2e balle', a, b, 'second_won_pct', { suffix: '%' }),
    statRow('Balles de break sauvées', a, b, 'bp_saved_pct', { suffix: '%' }),
  )

  return rows.filter(Boolean)
})

function winsA(row) {
  if (row.rawA == null || row.rawB == null) return false
  return row.higher ? row.rawA > row.rawB : row.rawA < row.rawB
}
function winsB(row) {
  if (row.rawA == null || row.rawB == null) return false
  return row.higher ? row.rawB > row.rawA : row.rawB < row.rawA
}

const justPaid = ref(route.query.paiement === 'reussi')
const checkoutSessionId = ref(typeof route.query.session_id === 'string' ? route.query.session_id : '')
const activating = ref(false)

async function onPostPaymentLinked() {
  postPaymentOpen.value = false
  router.replace({ path: route.path })
  await loadMatch()
}

async function loadMatch() {
  try {
    match.value = await api.get(`/api/tennis_matches/${props.id}`)
    forbidden.value = false

    if (match.value.prediction) {
      prediction.value = await api.get(`/api/predictions/${match.value.prediction.id}`)

      const [statsA, statsB, h2h, snapA, snapB] = await Promise.all([
        fetchCareerStats(match.value.playerA.id),
        fetchCareerStats(match.value.playerB.id),
        fetchHeadToHead(match.value.playerA.id, match.value.playerB.id),
        fetchSnapshot(match.value.playerA.id),
        fetchSnapshot(match.value.playerB.id),
      ])
      careerStatsA.value = statsA
      careerStatsB.value = statsB
      headToHead.value = h2h
      snapshotA.value = snapA
      snapshotB.value = snapB
    }
  } catch (e) {
    if (e instanceof ApiError && (e.status === 401 || e.status === 403)) {
      forbidden.value = true
    } else {
      console.error(e)
    }
  }
}

onMounted(async () => {
  await loadMatch()
  loading.value = false

  if (justPaid.value && !auth.isAuthenticated) {
    postPaymentOpen.value = true
  } else if (justPaid.value && forbidden.value) {
    activating.value = true
    setTimeout(async () => {
      await loadMatch()
      activating.value = false
    }, 3000)
  } else if (forbidden.value && auth.isAuthenticated) {
    paywallOpen.value = true
  }
})
</script>

<template>
  <div class="detail">
    <a class="back" @click="router.push('/matchs')"><span class="arrow">←</span> Retour au tableau des matchs</a>

    <p v-if="loading" class="state-msg">Chargement…</p>

    <template v-else-if="match">
      <!-- Tournoi/round (11/09/2026) : déjà affichés sur MatchCard.vue (liste
           /matchs) depuis le début, jamais repris ici — un oubli, pas un
           choix. Placés en ligne au-dessus de la carte plutôt qu'ajoutés aux
           badges déjà positionnés en absolu dans .face-off (circuit-badge
           centré, surface-badge à droite) : un nom de tournoi long
           entrerait en collision avec eux, alors qu'une ligne simple
           au-dessus n'a pas cette contrainte. -->
      <p class="match-meta">{{ match.tournamentName }} · {{ match.round }}</p>

      <!-- Face-off (11/09/2026) : masqué une fois le match terminé, sur
           demande explicite — "enlève ce qui est en bleu en haut quand le
           match est terminé, garde juste l'image du joueur qui a gagné".
           Reste affiché pour 'scheduled'/'live' (avant/pendant le match,
           la confrontation des deux joueurs a du sens), remplacé par
           .result-showcase juste en dessous une fois 'finished'/'walkover'. -->
      <div v-if="match.status === 'scheduled' || match.status === 'live'" class="card face-off" :style="surfaceCardVars(match.surface)">
        <TourBadge :tour="match.playerA.tour" on-dark class="circuit-badge" />
        <span class="surface-badge">{{ surfaceLabel(match.surface) }}</span>
        <div class="player">
          <div class="avatar" :class="{ 'is-favorite': isFavorite(match.playerA) }" :style="!showPhoto(match.playerA) ? avatarGradient(match.playerA.fullName) : null">
            <img
              v-if="showPhoto(match.playerA)"
              :src="match.playerA.photoUrl"
              class="avatar-photo"
              alt=""
              loading="lazy"
              @error="onPhotoError(match.playerA.id)"
            />
            <span v-else class="avatar-initials">{{ initials(match.playerA.fullName) }}</span>
            <img
              v-if="flagUrl(match.playerA.countryCode)"
              :src="flagUrl(match.playerA.countryCode)"
              class="avatar-flag"
              alt=""
              loading="lazy"
              @error="$event.target.style.display = 'none'"
            />
          </div>
          <div class="name">
            {{ match.playerA.fullName }}
            <svg v-if="match.winner?.id === match.playerA.id" class="winner-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" aria-label="Vainqueur">
              <circle cx="12" cy="12" r="10" fill="currentColor" opacity="0.22" />
              <path d="M7 12.5l3 3 7-7" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </div>
          <div class="rank">N°{{ match.playerA.atpWtaRank }} mondial</div>
          <div class="chips">
            <span v-if="eloForSurface(match.playerA, match.surface) != null" class="chip">Elo {{ Math.round(eloForSurface(match.playerA, match.surface)) }}</span>
            <span v-if="handLabel(match.playerA.dominantHand)" class="chip">{{ handLabel(match.playerA.dominantHand) }}</span>
          </div>
        </div>

        <div class="mid">
          <template v-if="match.prediction?.favoritePlayer">
            <div class="vslabel">PROBABILITÉ</div>
            <ProbabilityGauge
              :probability="match.prediction.probabilityFavorite"
              :label="match.prediction.favoritePlayer.fullName.split(' ').at(-1) + ' favori'"
            />
          </template>
          <div v-else class="vs-plain">VS</div>

          <!-- Score réel (voir ml-service/update_match_results.py,
               11/09/2026) : donnée publique, affichée à tout le monde y
               compris hors abonnement (comme le statut "Terminé" déjà
               visible sur MatchCard.vue) — jamais conditionnée à
               `prediction`, contrairement au reste de cette carte. -->
          <div v-if="match.status !== 'scheduled' && match.scoreText" class="final-score">
            <span class="final-score-label">{{ match.status === 'walkover' ? 'Forfait' : 'Score final' }}</span>
            <span class="final-score-text">{{ match.scoreText }}</span>
          </div>
        </div>

        <div class="player">
          <div class="avatar" :class="{ 'is-favorite': isFavorite(match.playerB) }" :style="!showPhoto(match.playerB) ? avatarGradient(match.playerB.fullName) : null">
            <img
              v-if="showPhoto(match.playerB)"
              :src="match.playerB.photoUrl"
              class="avatar-photo"
              alt=""
              loading="lazy"
              @error="onPhotoError(match.playerB.id)"
            />
            <span v-else class="avatar-initials">{{ initials(match.playerB.fullName) }}</span>
            <img
              v-if="flagUrl(match.playerB.countryCode)"
              :src="flagUrl(match.playerB.countryCode)"
              class="avatar-flag"
              alt=""
              loading="lazy"
              @error="$event.target.style.display = 'none'"
            />
          </div>
          <div class="name">
            {{ match.playerB.fullName }}
            <svg v-if="match.winner?.id === match.playerB.id" class="winner-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" aria-label="Vainqueur">
              <circle cx="12" cy="12" r="10" fill="currentColor" opacity="0.22" />
              <path d="M7 12.5l3 3 7-7" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </div>
          <div class="rank">N°{{ match.playerB.atpWtaRank }} mondial</div>
          <div class="chips">
            <span v-if="eloForSurface(match.playerB, match.surface) != null" class="chip">Elo {{ Math.round(eloForSurface(match.playerB, match.surface)) }}</span>
            <span v-if="handLabel(match.playerB.dominantHand)" class="chip">{{ handLabel(match.playerB.dominantHand) }}</span>
          </div>
        </div>
      </div>

      <!-- Carte "résultat" (11/09/2026, agrandie le 11/09/2026 sur demande
           explicite — "meilleur design, fond avec un terrain de tennis sur
           toute la page") : bannière plein format affichée UNIQUEMENT une
           fois le match réellement terminé (jamais pour 'scheduled'/'live')
           — voir matchLoser/resultSets dans le script. Le "terrain" est un
           schéma SVG dessiné à la main (lignes de court réelles : lignes de
           fond, couloirs, ligne de service, ligne médiane, filet) plutôt
           qu'une photo — pas de souci de droits, aucun poids d'image
           supplémentaire, et ça reste net à n'importe quelle taille d'écran.
           Coloré selon la VRAIE surface du match (surfaceCardVars, déjà
           utilisé sur le face-off juste au-dessus) : un match sur terre
           battue a un terrain ocre, un match sur dur un terrain bleu, etc. -->
      <div v-if="match.status !== 'scheduled' && match.winner" class="card result-showcase" :style="surfaceCardVars(match.surface)">
        <svg class="result-court" viewBox="0 0 400 200" preserveAspectRatio="none" aria-hidden="true">
          <rect x="20" y="20" width="360" height="160" fill="none" stroke="currentColor" stroke-width="2.4" />
          <line x1="20" y1="42" x2="380" y2="42" stroke="currentColor" stroke-width="1.6" />
          <line x1="20" y1="158" x2="380" y2="158" stroke="currentColor" stroke-width="1.6" />
          <line x1="200" y1="12" x2="200" y2="188" stroke="currentColor" stroke-width="3" />
          <line x1="106" y1="42" x2="106" y2="158" stroke="currentColor" stroke-width="1.6" />
          <line x1="294" y1="42" x2="294" y2="158" stroke="currentColor" stroke-width="1.6" />
          <line x1="106" y1="100" x2="294" y2="100" stroke="currentColor" stroke-width="1.6" />
          <line x1="20" y1="94" x2="20" y2="106" stroke="currentColor" stroke-width="2.4" />
          <line x1="380" y1="94" x2="380" y2="106" stroke="currentColor" stroke-width="2.4" />
        </svg>

        <div class="result-inner">
          <div class="result-photo-wrap">
            <img
              v-if="showPhoto(match.winner)"
              :src="match.winner.photoUrl"
              class="result-photo"
              alt=""
              loading="lazy"
              @error="onPhotoError(match.winner.id)"
            />
            <div v-else class="result-photo result-photo-fallback" :style="avatarGradient(match.winner.fullName)">
              <span class="result-initials">{{ initials(match.winner.fullName) }}</span>
            </div>
            <img
              v-if="flagUrl(match.winner.countryCode)"
              :src="flagUrl(match.winner.countryCode)"
              class="result-flag"
              alt=""
              loading="lazy"
              @error="$event.target.style.display = 'none'"
            />
          </div>

          <div class="result-body">
            <span class="result-eyebrow">{{ match.status === 'walkover' ? 'Victoire par forfait' : 'Match terminé' }}</span>
            <h2 class="result-winner">{{ match.winner.fullName }}</h2>
            <p v-if="matchLoser" class="result-sub">bat {{ matchLoser.fullName }}</p>

            <div v-if="resultSets.length" class="result-sets">
              <span
                v-for="(s, i) in resultSets"
                :key="i"
                class="result-set-pill"
                :class="{ won: s.wonByWinner === true, lost: s.wonByWinner === false }"
              >{{ s.text }}</span>
            </div>
            <p v-else-if="match.scoreText" class="result-sub">{{ match.scoreText }}</p>

            <div class="result-meta">{{ match.tournamentName }} · {{ match.round }} · {{ surfaceLabel(match.surface) }}</div>
          </div>
        </div>

        <span class="result-brand">TENNLY</span>
      </div>

      <div v-if="forbidden" class="card locked">
        <template v-if="activating">
          <div class="lock-icon">⏳</div>
          <p>Paiement reçu, activation de ton abonnement en cours…</p>
        </template>
        <template v-else>
          <div class="lock-icon">🔒</div>
          <p>Analyse complète réservée aux abonnés.</p>
          <button class="btn-primary" @click="paywallOpen = true">Débloquer l'analyse complète</button>
          <a v-if="!auth.isAuthenticated" class="already-sub" @click="goToLogin">Déjà abonné ? Se connecter</a>
        </template>
      </div>

      <template v-else-if="prediction">
        <div class="card">
          <h3>Profil comparatif</h3>
          <RadarChart :profile="prediction.radarProfile" :label-a="match.playerA.fullName" :label-b="match.playerB.fullName" />
        </div>

        <div v-if="snapshotRows.length" class="card">
          <h3>Forme du moment</h3>
          <div class="stats-table-wrap">
            <table class="stats-table">
              <thead>
                <tr>
                  <th class="th-a">{{ match.playerA.fullName.split(' ').at(-1) }}</th>
                  <th></th>
                  <th class="th-b">{{ match.playerB.fullName.split(' ').at(-1) }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in snapshotRows" :key="row.label">
                  <td :class="{ win: winsA(row) }">{{ row.valueA }}</td>
                  <td class="label">{{ row.label }}</td>
                  <td :class="{ win: winsB(row) }">{{ row.valueB }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div v-if="headToHead && headToHead.wins_player + headToHead.wins_opponent > 0" class="card h2h-card">
          <h3>Face-à-face</h3>
          <div class="h2h-row">
            <div class="h2h-score" :class="{ lead: headToHead.wins_player > headToHead.wins_opponent }">
              <span class="h2h-number">{{ headToHead.wins_player }}</span>
              <span class="h2h-name">{{ match.playerA.fullName.split(' ').at(-1) }}</span>
            </div>
            <span class="h2h-sep">—</span>
            <div class="h2h-score" :class="{ lead: headToHead.wins_opponent > headToHead.wins_player }">
              <span class="h2h-number">{{ headToHead.wins_opponent }}</span>
              <span class="h2h-name">{{ match.playerB.fullName.split(' ').at(-1) }}</span>
            </div>
          </div>
        </div>

        <div v-if="careerRows.length" class="card career-card">
          <h3>Palmarès carrière</h3>
          <div class="stats-table-wrap">
            <table class="stats-table">
              <thead>
                <tr>
                  <th class="th-a">{{ match.playerA.fullName.split(' ').at(-1) }}</th>
                  <th></th>
                  <th class="th-b">{{ match.playerB.fullName.split(' ').at(-1) }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in careerRows" :key="row.label">
                  <td :class="{ win: winsA(row) }">{{ row.valueA }}</td>
                  <td class="label">{{ row.label }}</td>
                  <td :class="{ win: winsB(row) }">{{ row.valueB }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="card why">
          <h3>Pourquoi cette analyse ?</h3>
          <ul class="factors">
            <li v-for="(factor, i) in prediction.explanationFactors" :key="i" :class="factor.tone">
              <span class="tag" :class="factor.tone === 'warn' ? 'warn' : 'ok'">{{ factor.tone === 'warn' ? '!' : '✓' }}</span>
              {{ factor.label }}
            </li>
          </ul>
        </div>
      </template>
    </template>
  </div>

  <PaywallModal :open="paywallOpen" @close="paywallOpen = false" />
  <PostPaymentModal :open="postPaymentOpen" :session-id="checkoutSessionId" @linked="onPostPaymentLinked" />
</template>

<style scoped>
.detail {
  padding: 24px 0 60px;
}

@keyframes fadeUp {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
@media (prefers-reduced-motion: reduce) {
  .card {
    animation-duration: 0.001ms !important;
  }
}

.back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--grey);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  margin-bottom: 24px;
  transition: color 0.15s ease;
}
.back:hover {
  color: var(--ink);
}
.back .arrow {
  transition: transform 0.15s ease;
}
.back:hover .arrow {
  transform: translateX(-3px);
}

.state-msg {
  color: var(--grey);
  font-size: 14px;
}

.card {
  padding: 28px;
  margin-bottom: 18px;
  animation: fadeUp 0.5s ease both;
}

.face-off {
  position: relative;
  overflow: hidden;
  isolation: isolate;
  display: grid;
  grid-template-columns: 1fr 200px 1fr;
  gap: 24px;
  align-items: center;
  padding: 36px;
  color: #fff;
  background:
    radial-gradient(130% 160% at 50% -20%, var(--surface-glow) 0%, transparent 60%),
    linear-gradient(135deg, var(--surface-from), var(--surface-to));
  --card: rgba(255, 255, 255, 0.16);
  --green: var(--lime);
  box-shadow: 0 22px 44px -18px var(--surface-shadow);
  animation: cardIn 0.6s cubic-bezier(0.16, 1, 0.3, 1) both;
}
@keyframes cardIn {
  from {
    opacity: 0;
    transform: translateY(10px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
.face-off::after {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 0;
  opacity: 0.07;
  background-image: repeating-linear-gradient(115deg, #fff 0 1.5px, transparent 1.5px 26px);
  pointer-events: none;
}
.circuit-badge {
  position: absolute;
  top: 14px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 2;
}
.surface-badge {
  position: absolute;
  top: 16px;
  right: 20px;
  z-index: 2;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 4px 11px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.16);
}
.player {
  position: relative;
  z-index: 2;
  text-align: center;
}
.avatar {
  position: relative;
  width: 88px;
  height: 88px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  margin: 0 auto 14px;
  box-shadow:
    inset 0 0 0 2px rgba(255, 255, 255, 0.22),
    0 8px 20px rgba(0, 0, 0, 0.3);
  transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}
.avatar.is-favorite {
  box-shadow:
    inset 0 0 0 2px rgba(255, 255, 255, 0.3),
    0 0 0 3px var(--lime),
    0 8px 22px rgba(199, 255, 60, 0.32);
}
.avatar-photo {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.avatar-initials {
  font-weight: 800;
  font-size: 26px;
  color: #fff;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
}
.avatar-flag {
  position: absolute;
  bottom: 0;
  right: 2px;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #fff;
  object-fit: cover;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.4);
}
.name {
  font-weight: 700;
  font-size: 16px;
}
.rank {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
  margin-top: 4px;
  font-variant-numeric: tabular-nums;
}
.chips {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}
.chip {
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: rgba(255, 255, 255, 0.85);
  background: rgba(255, 255, 255, 0.14);
  padding: 3px 9px;
  border-radius: 999px;
  font-variant-numeric: tabular-nums;
}
.winner-icon {
  color: var(--lime);
  vertical-align: -2px;
  margin-left: 2px;
}

.match-meta {
  max-width: 880px;
  margin: 0 auto 14px;
  text-align: center;
  font-size: 13px;
  color: var(--grey);
}

.mid {
  position: relative;
  z-index: 2;
  text-align: center;
}
.vslabel {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: 8px;
}
.vs-plain {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--line);
}
.final-score {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.16);
}
.final-score-label {
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.65);
}
.final-score-text {
  font-size: 14px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  color: #fff;
}

/* Carte "résultat" (11/09/2026, agrandie sur demande explicite le
   11/09/2026 — "meilleur design, fond avec un terrain de tennis") :
   bannière plein format, hauteur généreuse, fond coloré par la vraie
   surface du match (--surface-from/to, voir surfaceCardVars) assombri par
   un voile sombre pour que le texte blanc reste lisible — même logique que
   .face-off juste au-dessus, poussée beaucoup plus loin ici puisque cette
   carte doit se lire comme une affiche, pas comme une carte de données. */
.result-showcase {
  position: relative;
  overflow: hidden;
  isolation: isolate;
  min-height: 300px;
  display: flex;
  align-items: center;
  padding: 44px 48px;
  background:
    linear-gradient(160deg, rgba(6, 10, 8, 0.93) 0%, rgba(6, 10, 8, 0.86) 45%, rgba(6, 10, 8, 0.94) 100%),
    linear-gradient(135deg, var(--surface-from), var(--surface-to));
  color: #fff;
}
/* Halo lime en surimpression, comme .face-off::after, mais plus marqué
   puisqu'il n'y a pas d'autre source de couleur ici que le fond. */
.result-showcase::after {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 0;
  background: radial-gradient(90% 120% at 82% 8%, var(--surface-glow) 0%, transparent 60%);
  pointer-events: none;
}
/* Le "terrain" : schéma de court dessiné en SVG (voir le template), posé en
   fond plein format, très discret (les lignes ne doivent jamais rivaliser
   avec le vainqueur/le score par-dessus) et légèrement zoomé/décentré pour
   un effet "plan large" plutôt qu'un diagramme scolaire centré. */
.result-court {
  position: absolute;
  z-index: 0;
  top: 50%;
  left: 50%;
  width: 145%;
  height: 145%;
  transform: translate(-50%, -50%) rotate(-4deg);
  color: rgba(255, 255, 255, 0.16);
  pointer-events: none;
}
.result-inner {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 36px;
  width: 100%;
}
.result-photo-wrap {
  position: relative;
  flex: none;
}
.result-photo {
  width: 176px;
  height: 176px;
  border-radius: 32px;
  object-fit: cover;
  box-shadow:
    0 0 0 3px var(--lime),
    0 22px 48px -10px rgba(0, 0, 0, 0.55);
}
.result-photo-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
}
.result-initials {
  font-size: 56px;
  font-weight: 800;
  color: #fff;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}
.result-flag {
  position: absolute;
  bottom: -8px;
  right: -8px;
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: #fff;
  object-fit: cover;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.5);
}
.result-body {
  min-width: 0;
}
.result-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--lime);
  margin-bottom: 10px;
}
.result-eyebrow::before {
  content: '';
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--lime);
  box-shadow: 0 0 10px 2px rgba(199, 255, 60, 0.7);
}
.result-winner {
  margin: 0;
  font-size: clamp(28px, 4vw, 44px);
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.08;
  text-wrap: balance;
}
.result-sub {
  margin: 6px 0 0;
  font-size: 16px;
  color: rgba(255, 255, 255, 0.68);
}
.result-sets {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 20px;
}
.result-set-pill {
  padding: 6px 15px;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.14);
  backdrop-filter: blur(2px);
}
.result-set-pill.won {
  background: rgba(199, 255, 60, 0.18);
  color: var(--lime);
  border-color: rgba(199, 255, 60, 0.5);
}
.result-meta {
  margin-top: 18px;
  font-size: 13px;
  letter-spacing: 0.01em;
  color: rgba(255, 255, 255, 0.55);
}
.result-brand {
  position: absolute;
  z-index: 1;
  top: 24px;
  right: 28px;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.14em;
  color: rgba(255, 255, 255, 0.45);
}

@media (max-width: 640px) {
  .result-showcase {
    min-height: 0;
    padding: 32px 22px;
  }
  .result-inner {
    flex-direction: column;
    text-align: center;
    gap: 18px;
  }
  .result-photo {
    width: 120px;
    height: 120px;
    border-radius: 26px;
  }
  .result-sets {
    justify-content: center;
  }
  .result-brand {
    top: 16px;
    right: 18px;
  }
}

/* Face-à-face — décompte brut des confrontations directes, présenté en
   gros pour être lu d'un coup d'œil (contrairement au tableau détaillé du
   palmarès carrière juste en dessous). Le joueur actuellement devant
   ressort en vert ; égalité : aucun des deux n'est mis en avant. */
.h2h-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 28px;
}
.h2h-score {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  min-width: 84px;
}
.h2h-number {
  font-size: 34px;
  font-weight: 800;
  line-height: 1;
  font-variant-numeric: tabular-nums;
  color: var(--ink);
}
.h2h-score.lead .h2h-number {
  color: var(--green);
}
.h2h-name {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--grey);
  text-transform: uppercase;
  letter-spacing: 0.02em;
}
.h2h-sep {
  font-size: 20px;
  font-weight: 700;
  color: var(--line);
}

/* Palmarès carrière — même schéma visuel que le tableau comparatif de
   ComparateurView.vue (en-têtes vert/bleu par joueur, colonne label au
   centre, valeur la plus favorable en vert gras). Dupliqué ici plutôt que
   partagé : les styles scoped de Vue ne traversent pas les composants. */
.stats-table-wrap {
  overflow-x: auto;
}
.stats-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}
.stats-table th {
  font-size: 12.5px;
  font-weight: 700;
  letter-spacing: 0.02em;
  padding-bottom: 10px;
}
.stats-table th.th-a {
  color: var(--green);
  text-align: left;
}
.stats-table th.th-b {
  color: var(--blue);
  text-align: right;
}
.stats-table td {
  padding: 9px 4px;
  text-align: center;
  border-top: 1px solid var(--line);
  font-variant-numeric: tabular-nums;
}
.stats-table td:first-child {
  text-align: left;
}
.stats-table td:last-child {
  text-align: right;
}
.stats-table td.label {
  color: var(--grey);
  font-size: 12.5px;
  white-space: nowrap;
}
.stats-table td.win {
  font-weight: 700;
  color: var(--green);
}

.locked {
  text-align: center;
  padding: 44px 28px;
}
.lock-icon {
  font-size: 30px;
  margin-bottom: 12px;
}
.locked p {
  margin: 0 0 18px;
  color: var(--ink);
  font-size: 15px;
}
.already-sub {
  display: block;
  margin-top: 14px;
  font-size: 13px;
  color: var(--grey);
  text-decoration: underline;
  cursor: pointer;
}

h3 {
  font-size: 15px;
  font-weight: 700;
  margin: 0 0 18px;
}
.factors {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  font-size: 14px;
  line-height: 1.5;
}
.factors li {
  display: flex;
  gap: 10px;
}
.factors .tag {
  flex: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  margin-top: 1px;
}
.factors .tag.ok {
  background: #e6f9ea;
  color: #1f7d33;
}
.factors .tag.warn {
  background: #fff3cd;
  color: #8a6100;
}

@media (max-width: 640px) {
  .face-off {
    grid-template-columns: 1fr;
    text-align: center;
    gap: 20px;
    padding-top: 44px;
  }
  .circuit-badge {
    position: static;
    display: inline-flex;
    justify-self: center;
    width: auto;
    margin-bottom: 8px;
  }
  .surface-badge {
    top: 16px;
    right: 50%;
    transform: translateX(50%);
  }
}
</style>
