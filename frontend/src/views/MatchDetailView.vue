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

// Mise en scène "versus" (16/09/2026, sur demande explicite) : juste après le
// chargement du match, un court écran affiche les deux joueurs face à face
// avant de révéler la suite (confrontation détaillée, puis soit l'analyse
// complète, soit son déblocage — cette dernière carte existe déjà juste
// au-dessus de l'analyse, voir plus bas dans le template, elle n'a pas
// besoin d'être déplacée). Coupé net pour prefers-reduced-motion : l'écran
// "versus" n'apparaît alors jamais, le contenu s'affiche directement.
function prefersReducedMotion() {
  return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
}
const showVersusIntro = ref(false)

// Popup "débloquer l'analyse complète" (16/09/2026, sur demande explicite,
// avec une capture de référence à l'appui) : sur un match verrouillé, plus
// de carte plate posée dans la page — une popup s'ouvre d'elle-même juste
// après l'écran "versus", construite comme une seule affiche (icône +
// message en gros, peu de texte autour) plutôt qu'un bloc de texte. Le
// bouton "Voir les formules" à l'intérieur ouvre ensuite le vrai popup de
// paiement (paywallOpen / PaywallModal.vue) — jamais l'inverse : cette
// popup-ci ne collecte ni carte ni email, elle ne fait qu'annoncer.
const showUnlockPopup = ref(false)

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

// Repère "pronostic" sur la carte résultat (16/09/2026, passe premium) :
// confronte le vainqueur RÉEL au favori donné par match.prediction AVANT le
// match — cette donnée est déjà chargée pour tout le monde (gratuite, comme
// le favori affiché sur .face-off), donc rien de nouveau à charger ici, et
// jamais rien d'inventé : si le match n'avait pas de favori déclaré
// (prediction absente), ce repère ne s'affiche simplement pas.
const resultPronostic = computed(() => {
  const m = match.value
  const fav = m?.prediction?.favoritePlayer
  if (!m?.winner || !fav) return null
  const prob = m.prediction?.probabilityFavorite
  if (fav.id === m.winner.id) {
    const pct = prob != null ? Math.round(prob * 100) : null
    return {
      tone: 'confirmed',
      label: pct != null ? `Favori confirmé · ${pct}% donnés par notre analyse` : 'Favori confirmé par notre analyse',
    }
  }
  const pct = prob != null ? Math.round((1 - prob) * 100) : null
  return {
    tone: 'upset',
    label: pct != null ? `Résultat surprise · ${pct}% de chances données` : 'Résultat surprise par rapport à notre analyse',
  }
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

// Ce qui doit se passer une fois l'écran "versus" terminé (ou immédiatement
// s'il n'a jamais été affiché, cas prefers-reduced-motion) : inchangé pour
// le retour de paiement, mais la popup "débloquer l'analyse complète"
// remplace désormais l'ouverture automatique de paywallOpen — voir
// showUnlockPopup plus haut. Ouverte pour tout visiteur bloqué (abonné non
// connecté comme visiteur anonyme), pas seulement les connectés non-abonnés
// comme avant : la popup n'étant qu'une annonce (pas un formulaire), il n'y
// a plus de raison de la réserver aux seuls connectés.
function afterVersusIntro() {
  if (justPaid.value && !auth.isAuthenticated) {
    postPaymentOpen.value = true
  } else if (justPaid.value && forbidden.value) {
    activating.value = true
    setTimeout(async () => {
      await loadMatch()
      activating.value = false
    }, 3000)
  } else if (forbidden.value) {
    showUnlockPopup.value = true
  }
}

onMounted(async () => {
  await loadMatch()
  loading.value = false

  // Écran "versus" (16/09/2026) : uniquement si le match a bien pu être
  // chargé, et jamais pour prefers-reduced-motion — dans ce cas la suite
  // s'enchaîne immédiatement, sans attente artificielle.
  if (match.value && !prefersReducedMotion()) {
    showVersusIntro.value = true
    setTimeout(() => {
      showVersusIntro.value = false
      afterVersusIntro()
    }, 1800)
  } else {
    afterVersusIntro()
  }
})
</script>

<template>
  <div class="detail">
    <a class="back" @click="router.push('/matchs')"><span class="arrow">←</span> Retour au tableau des matchs</a>

    <p v-if="loading" class="state-msg">Chargement…</p>

    <template v-else-if="match">
      <!-- Mise en scène "versus" (16/09/2026, sur demande explicite) : les
           deux joueurs face à face pendant un court instant avant que le
           reste de la page (confrontation détaillée, puis analyse ou son
           déblocage) ne se révèle. Voir showVersusIntro dans le script pour
           la durée et le cas prefers-reduced-motion. -->
      <div v-if="showVersusIntro" class="versus-intro">
        <div class="vi-player">
          <div class="vi-avatar" :style="!showPhoto(match.playerA) ? avatarGradient(match.playerA.fullName) : null">
            <img
              v-if="showPhoto(match.playerA)"
              :src="match.playerA.photoUrl"
              class="vi-avatar-photo"
              alt=""
              loading="lazy"
              @error="onPhotoError(match.playerA.id)"
            />
            <span v-else class="vi-avatar-initials">{{ initials(match.playerA.fullName) }}</span>
          </div>
          <div class="vi-name">{{ match.playerA.fullName }}</div>
        </div>

        <div class="vi-mid">
          <span class="vi-vs">VS</span>
        </div>

        <div class="vi-player">
          <div class="vi-avatar" :style="!showPhoto(match.playerB) ? avatarGradient(match.playerB.fullName) : null">
            <img
              v-if="showPhoto(match.playerB)"
              :src="match.playerB.photoUrl"
              class="vi-avatar-photo"
              alt=""
              loading="lazy"
              @error="onPhotoError(match.playerB.id)"
            />
            <span v-else class="vi-avatar-initials">{{ initials(match.playerB.fullName) }}</span>
          </div>
          <div class="vi-name">{{ match.playerB.fullName }}</div>
        </div>

        <div class="vi-progress"><span class="vi-progress-bar"></span></div>
      </div>

      <template v-else>
      <!-- Tournoi/round (11/09/2026) : déjà affichés sur MatchCard.vue (liste
           /matchs) depuis le début, jamais repris ici — un oubli, pas un
           choix. Placés en ligne au-dessus de la carte plutôt qu'ajoutés aux
           badges déjà positionnés en absolu dans .face-off (circuit-badge
           centré, surface-badge à droite) : un nom de tournoi long
           entrerait en collision avec eux, alors qu'une ligne simple
           au-dessus n'a pas cette contrainte. -->
      <!-- Repli (19/09/2026) : masque le round quand il est vide ou vaut
           "?" (voir même correctif sur MatchCard.vue). -->
      <p class="match-meta">{{ match.tournamentName }}{{ match.round && match.round !== '?' ? ' · ' + match.round : '' }}</p>

      <!-- Face-off (11/09/2026) : masqué une fois le match terminé, sur
           demande explicite — "enlève ce qui est en bleu en haut quand le
           match est terminé, garde juste l'image du joueur qui a gagné".
           Reste affiché pour 'scheduled'/'live' (avant/pendant le match,
           la confrontation des deux joueurs a du sens), remplacé par
           .result-showcase juste en dessous une fois 'finished'/'walkover'. -->
      <div v-if="match.status === 'scheduled' || match.status === 'live'" class="card face-off" :style="surfaceCardVars(match.surface)">
        <TourBadge :tour="match.playerA.tour" on-dark class="circuit-badge" />
        <span class="surface-badge">{{ surfaceLabel(match.surface) }}</span>
        <div class="player player-left">
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

        <div class="player player-right">
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

      <!-- Carte "résultat" — refonte complète (09/09/2026), suite au retour
           tranché de l'utilisateur sur la version précédente (terrain SVG
           "deux tons" + photo encadrée à gauche fondue au mask-image) :
           "enlève moi ce fond bleu et ce carré moche et met un fond qui
           prend toute la page avec un effet wow et des animations". Deux
           défauts diagnostiqués dans cette version précédente : (1) la
           photo n'était fondue que sur UN bord (mask-image horizontal ou
           vertical) — comme les photos joueurs sont souvent recadrées sur
           un fond studio uni, les 3 autres bords restaient nets, d'où le
           "carré" ; (2) le fond était coloré par surfaceCardVars(surface),
           très bleu pour le dur (#04213f → #0071e3), et dominait toute la
           carte malgré le voile.
           Nouvelle approche : la photo devient le fond PLEIN CADRE de toute
           la carte (aucun cadre séparé => plus aucun bord net possible), la
           couleur de surface n'est plus utilisée ICI DU TOUT — seul
           l'accent citron vert de la marque (--lime) ponctue le visuel, sur
           un voile neutre quasi-noir. La carte casse volontairement la
           mise en page (pleine largeur d'écran, technique
           margin:calc(50%-50vw), voir .result-showcase) pour un effet
           bannière immersif plutôt qu'une carte de plus dans la colonne.
           Animations (désactivées si prefers-reduced-motion) : zoom lent
           de la photo (Ken Burns), reveal du texte en cascade, halos qui
           respirent, reflet qui balaie la carte une fois au chargement.
           Affichée UNIQUEMENT une fois le match réellement terminé — voir
           matchLoser/resultSets dans le script. -->
      <div v-if="match.status !== 'scheduled' && match.winner" class="result-showcase">
        <div class="result-hairline"></div>
        <div class="result-bg">
          <img
            v-if="showPhoto(match.winner)"
            :src="match.winner.photoUrl"
            class="result-photo"
            alt=""
            loading="lazy"
            @error="onPhotoError(match.winner.id)"
          />
          <div v-else class="result-photo result-photo-fallback" :style="avatarGradient(match.winner.fullName)">
            <span class="result-ghost-initials">{{ initials(match.winner.fullName) }}</span>
          </div>
        </div>
        <div class="result-duo"></div>
        <div class="result-glow result-glow-a"></div>
        <div class="result-glow result-glow-b"></div>
        <div class="result-vignette"></div>
        <div class="result-grain"></div>
        <div class="result-shine"></div>

        <img
          v-if="flagUrl(match.winner.countryCode)"
          :src="flagUrl(match.winner.countryCode)"
          class="result-flag"
          alt=""
          loading="lazy"
          @error="$event.target.style.display = 'none'"
        />
        <span class="result-brand">TENNLY</span>

        <div class="result-inner">
          <div class="result-body">
            <div class="result-top-row">
              <span class="result-eyebrow">{{ match.status === 'walkover' ? 'Victoire par forfait' : 'Match terminé' }}</span>
              <span v-if="resultPronostic" class="result-pronostic" :class="resultPronostic.tone">{{ resultPronostic.label }}</span>
            </div>
            <h2 class="result-winner">{{ match.winner.fullName }}</h2>
            <p v-if="matchLoser" class="result-sub">bat {{ matchLoser.fullName }}</p>

            <div v-if="resultSets.length" class="result-sets-wrap">
              <span class="result-sets-label">Sets</span>
              <div class="result-sets">
                <span
                  v-for="(s, i) in resultSets"
                  :key="i"
                  class="result-set-pill"
                  :class="{ won: s.wonByWinner === true, lost: s.wonByWinner === false }"
                >{{ s.text }}</span>
              </div>
            </div>
            <p v-else-if="match.scoreText" class="result-sub">{{ match.scoreText }}</p>

            <div class="result-meta">{{ match.tournamentName }}{{ match.round && match.round !== '?' ? ' · ' + match.round : '' }} · {{ surfaceLabel(match.surface) }}</div>
          </div>
        </div>

        <div class="result-scrollcue" aria-hidden="true">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M6 9l6 6 6-6" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </div>
      </div>

      <div v-if="forbidden && activating" class="card locked">
        <div class="lock-icon">⏳</div>
        <p>Paiement reçu, activation de ton abonnement en cours…</p>
      </div>

      <!-- Repli minimal (16/09/2026) : la vraie invitation à s'abonner vit
           désormais dans la popup "affiche" (showUnlockPopup, ouverte toute
           seule juste après l'écran versus — voir onMounted/afterVersusIntro
           et .unlock-overlay plus bas). Ce lien reste juste au cas où le
           visiteur ferme la popup sans agir, pour ne pas le laisser bloqué
           sans aucun moyen de la rouvrir. -->
      <div v-else-if="forbidden" class="unlock-inline">
        <button type="button" class="unlock-inline-btn" @click="showUnlockPopup = true">
          <span class="unlock-inline-icon">🔒</span> Débloquer l'analyse complète
        </button>
      </div>

      <template v-else-if="prediction">
        <div class="card">
          <h3>Profil comparatif</h3>
          <div class="sub">6 dimensions clés, normalisées sur 100</div>
          <RadarChart
            :profile="prediction.radarProfile"
            :label-a="match.playerA.fullName"
            :label-b="match.playerB.fullName"
            :favorite-index="match.prediction?.favoritePlayer ? (isFavorite(match.playerA) ? 0 : 1) : null"
            :winner-index="match.winner ? (match.winner.id === match.playerA.id ? 0 : 1) : null"
            :probability-favorite="match.prediction?.probabilityFavorite ?? null"
          />
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
              <span v-if="headToHead.wins_player > headToHead.wins_opponent" class="h2h-lead-tag">En tête</span>
            </div>
            <span class="h2h-sep">—</span>
            <div class="h2h-score" :class="{ lead: headToHead.wins_opponent > headToHead.wins_player }">
              <span class="h2h-number">{{ headToHead.wins_opponent }}</span>
              <span class="h2h-name">{{ match.playerB.fullName.split(' ').at(-1) }}</span>
              <span v-if="headToHead.wins_opponent > headToHead.wins_player" class="h2h-lead-tag">En tête</span>
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
          <div class="sub">Chaque ligne indique le joueur qu'elle avantage, pas seulement le constat.</div>
          <ul class="factors">
            <li v-for="(factor, i) in prediction.explanationFactors" :key="i" :class="factor.tone">
              <span class="tag" :class="factor.tone === 'warn' ? 'warn' : 'ok'">{{ factor.tone === 'warn' ? '!' : '✓' }}</span>
              <span class="factor-text">
                {{ factor.label }}
                <b class="factor-favors">— avantage {{ (factor.favors === 'A' ? match.playerA.fullName : match.playerB.fullName).split(' ').at(-1) }}</b>
              </span>
            </li>
          </ul>
        </div>
      </template>
      </template>
    </template>
  </div>

  <PaywallModal :open="paywallOpen" @close="paywallOpen = false" />
  <PostPaymentModal :open="postPaymentOpen" :session-id="checkoutSessionId" @linked="onPostPaymentLinked" />

  <!-- Popup "affiche" (16/09/2026) : une seule affiche (icône + message en
       gros), pas un formulaire — voir showUnlockPopup dans le script pour
       le pourquoi. Son bouton ouvre le vrai popup de paiement
       (paywallOpen) plutôt que de dupliquer les formules ici.
       Croix + fermeture au clic extérieur retirées (19/09/2026, sur demande
       explicite) : le visiteur bloqué doit choisir "Voir les formules" ou
       "Déjà abonné ? Se connecter" plutôt que de pouvoir fermer ce popup
       sans rien faire. -->
  <div v-if="showUnlockPopup" class="unlock-overlay">
    <div class="unlock-modal">
      <div class="unlock-poster">
        <!-- Cadenas remplacé par le logo (17/09/2026, demande explicite),
             avec une animation "rebond" plutôt que le pulse précédent, pour
             évoquer une vraie balle de tennis qui rebondit. -->
        <img src="/logo-mark.png" alt="" class="unlock-poster-icon" />
        <h3 class="unlock-poster-text">Débloque<br />l'analyse<br />complète</h3>
      </div>
      <button class="unlock-modal-cta" @click="showUnlockPopup = false; paywallOpen = true">Voir les formules</button>
      <a v-if="!auth.isAuthenticated" class="unlock-modal-already" @click="showUnlockPopup = false; goToLogin()">Déjà abonné ? Se connecter</a>
    </div>
  </div>
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
  * {
    animation-duration: 0.001ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.001ms !important;
  }
  .player-left,
  .player-right,
  .mid {
    animation: none !important;
    opacity: 1 !important;
    transform: none !important;
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
/* Léger relief au survol (passe "premium", 11/09/2026) — même langage que
   HomeView.vue/MatchesView.vue/ModelReliabilityView.vue. Exclue .face-off :
   cette carte a déjà sa propre ombre teintée par surface (surface-shadow),
   qu'une ombre neutre générique affadirait plutôt que sublimerait. */
.card:not(.face-off) {
  transition:
    box-shadow 0.35s var(--ease-premium),
    transform 0.35s var(--ease-premium);
}
.card:not(.face-off):hover {
  box-shadow: var(--shadow-elevated);
  transform: translateY(-2px);
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
  animation: cardIn 0.6s var(--ease-premium) both;
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
/* Entrée en scène des deux joueurs (passe "premium", 11/09/2026) : chacun
   glisse depuis son côté plutôt que d'apparaître d'un bloc avec le reste de
   .face-off — un léger effet "confrontation" plus marqué que le simple
   fondu déjà porté par cardIn sur la carte entière. */
.player-left {
  animation: slideInLeft 0.7s var(--ease-premium) 0.08s both;
}
.player-right {
  animation: slideInRight 0.7s var(--ease-premium) 0.14s both;
}
.mid {
  animation: midFadeIn 0.6s var(--ease-premium) 0.2s both;
}
@keyframes slideInLeft {
  from {
    opacity: 0;
    transform: translateX(-22px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}
@keyframes slideInRight {
  from {
    opacity: 0;
    transform: translateX(22px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}
@keyframes midFadeIn {
  from {
    opacity: 0;
    transform: translateY(8px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: none;
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
  transition:
    transform 0.4s var(--ease-premium),
    box-shadow 0.4s var(--ease-premium);
}
.player:hover .avatar {
  transform: translateY(-3px) scale(1.04);
  box-shadow:
    inset 0 0 0 2px rgba(255, 255, 255, 0.3),
    0 12px 26px rgba(0, 0, 0, 0.36);
}
.player:hover .avatar.is-favorite {
  box-shadow:
    inset 0 0 0 2px rgba(255, 255, 255, 0.35),
    0 0 0 3px var(--lime),
    0 12px 28px rgba(199, 255, 60, 0.4);
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

/* Écran "versus" — refonte "affiche" (16/09/2026, sur demande explicite
   avec capture de référence à l'appui) : abandon du fond dégradé teinté par
   la surface au profit d'un visuel proche d'une affiche de combat — fond
   blanc, très grandes photos rondes, "VS" énorme en Anton (même police que
   .result-winner), noms en majuscules dessous. Chaque élément entre en
   scène (glissade, "tampon" pour le VS) au lieu d'apparaître d'un bloc, et
   une fine barre de progression matérialise l'attente avant la révélation
   du reste de la page. */
.versus-intro {
  position: relative;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 20px;
  padding: 56px 28px 44px;
  margin-bottom: 18px;
  border-radius: var(--radius-card);
  background: #fff;
  border: 1px solid var(--line);
  text-align: center;
  animation: fadeUp 0.4s ease both;
}
.vi-player {
  min-width: 0;
}
.vi-avatar {
  position: relative;
  width: clamp(120px, 20vw, 180px);
  height: clamp(120px, 20vw, 180px);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  margin: 0 auto 16px;
  box-shadow: 0 16px 32px -14px rgba(15, 61, 62, 0.28);
}
.vi-player:first-child .vi-avatar {
  animation: viSlideLeft 0.6s var(--ease-premium) both;
}
.vi-player:last-child .vi-avatar {
  animation: viSlideRight 0.6s var(--ease-premium) both;
}
.vi-avatar-photo {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.vi-avatar-initials {
  font-family: 'Anton', sans-serif;
  font-size: clamp(32px, 6vw, 52px);
  color: #fff;
}
.vi-name {
  font-family: 'Anton', sans-serif;
  font-weight: 400;
  font-size: clamp(14px, 2.1vw, 21px);
  letter-spacing: 0.01em;
  text-transform: uppercase;
  color: var(--ink);
  animation: viRise 0.5s ease 0.35s both;
}
.vi-mid {
  padding: 0 4px;
}
.vi-vs {
  display: inline-block;
  font-family: 'Anton', sans-serif;
  font-weight: 400;
  font-size: clamp(42px, 7vw, 84px);
  line-height: 1;
  color: var(--ink);
  animation: viStamp 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) 0.45s both;
}
.vi-progress {
  grid-column: 1 / -1;
  height: 3px;
  border-radius: 999px;
  background: var(--line);
  overflow: hidden;
  margin-top: 12px;
}
.vi-progress-bar {
  display: block;
  height: 100%;
  width: 100%;
  background: linear-gradient(90deg, var(--green), var(--lime));
  transform-origin: left;
  transform: scaleX(0);
  animation: viProgress 1.8s linear both;
}
@keyframes viSlideLeft {
  from {
    opacity: 0;
    transform: translateX(-32px) scale(0.85);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
@keyframes viSlideRight {
  from {
    opacity: 0;
    transform: translateX(32px) scale(0.85);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
@keyframes viRise {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
@keyframes viStamp {
  0% {
    opacity: 0;
    transform: scale(0.4) rotate(-6deg);
  }
  60% {
    opacity: 1;
    transform: scale(1.12) rotate(2deg);
  }
  100% {
    opacity: 1;
    transform: scale(1) rotate(0);
  }
}
@keyframes viProgress {
  from {
    transform: scaleX(0);
  }
  to {
    transform: scaleX(1);
  }
}
@media (prefers-reduced-motion: reduce) {
  .vi-avatar,
  .vi-name,
  .vi-vs,
  .vi-progress-bar {
    animation: none !important;
    opacity: 1 !important;
    transform: none !important;
  }
}
@media (max-width: 640px) {
  .versus-intro {
    grid-template-columns: 1fr;
    gap: 16px;
    padding: 40px 20px 32px;
  }
  .vi-vs {
    font-size: 40px;
  }
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

/* Carte "résultat" — refonte pleine page (09/09/2026, voir le commentaire
   dans le <template> pour le diagnostic complet des deux défauts de la
   version précédente). Bannière plein écran : width:100vw +
   margin:calc(50%-50vw) est la technique classique pour faire "sortir" un
   élément de son conteneur centré (ici <main>, max-width 1120px, voir
   App.vue) jusqu'aux bords du viewport, quelle que soit la largeur d'écran
   — fonctionne même avec le padding horizontal de <main> car il est
   symétrique. Volontairement PAS de classe .card ici : on réécrit fond,
   rayon, ombre et marge de zéro plutôt que de neutraliser ceux hérités. */
.result-showcase {
  position: relative;
  overflow: hidden;
  isolation: isolate;
  width: 100vw;
  margin-left: calc(50% - 50vw);
  margin-right: calc(50% - 50vw);
  margin-bottom: 28px;
  min-height: clamp(440px, 56vw, 640px);
  background: #0b0c10;
  color: #fff;
}

/* Fine ligne d'accent en haut de la bannière (passe premium, 16/09/2026) :
   un "wipe" ponctuel de gauche à droite au chargement, comme un liseré de
   couverture de magazine — même accent lime que le reste, jamais une
   couleur nouvelle. */
.result-hairline {
  position: absolute;
  z-index: 4;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, transparent, var(--lime), transparent);
  transform-origin: left;
  transform: scaleX(0);
  animation: resultHairline 1s var(--ease-premium) 0.05s both;
  pointer-events: none;
}

.result-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
}
/* Léger habillage colorimétrique de la photo (passe premium, 16/09/2026) :
   un voile teal profond en multiply, jamais une couleur nouvelle (mêmes
   --green/--green2 que le reste du site) — donne un rendu "éditorial
   sport" plus posé qu'une photo brute, sans jamais recolorer par surface
   (voir le commentaire plus haut sur le "fond bleu" à ne pas reproduire). */
.result-duo {
  position: absolute;
  inset: 0;
  z-index: 1;
  background: linear-gradient(160deg, rgba(10, 44, 45, 0.55) 0%, rgba(5, 6, 8, 0.1) 60%);
  mix-blend-mode: multiply;
  pointer-events: none;
}
/* Grain fin en overlay (passe premium, 16/09/2026) : texture SVG generée
   inline (feTurbulence), très discrète — évite l'aspect "gradient plat"
   d'un fond uni, sans ajouter de requête réseau ni de fichier image. */
.result-grain {
  position: absolute;
  inset: 0;
  z-index: 2;
  opacity: 0.05;
  mix-blend-mode: overlay;
  pointer-events: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}
/* La photo EST le fond de toute la carte (plus de cadre séparé) : plus
   aucun bord net possible, donc plus de "carré". Léger zoom-arrière au
   chargement (Ken Burns) pour la partie "wow"/animations demandée. */
.result-photo {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center 18%;
  transform: scale(1.12);
  animation: resultKenBurns 9s cubic-bezier(0.16, 1, 0.3, 1) both;
}
.result-photo-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
}
.result-ghost-initials {
  font-family: 'Anton', sans-serif;
  font-size: clamp(120px, 22vw, 260px);
  color: rgba(255, 255, 255, 0.14);
  letter-spacing: 0.02em;
}

/* Halos décoratifs : seule touche de couleur de toute la carte, l'accent
   citron vert de la marque (--lime) — jamais la couleur de surface du
   match, qui était précisément la source du "fond bleu" reproché. */
.result-glow {
  position: absolute;
  z-index: 1;
  aspect-ratio: 1 / 1;
  border-radius: 50%;
  pointer-events: none;
  filter: blur(60px);
}
.result-glow-a {
  top: -18%;
  right: -8%;
  width: 46%;
  background: radial-gradient(circle, rgba(199, 255, 60, 0.28) 0%, transparent 70%);
  animation: resultGlowDrift 14s ease-in-out infinite;
}
.result-glow-b {
  bottom: -22%;
  left: -10%;
  width: 40%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.1) 0%, transparent 70%);
  animation: resultGlowDrift 18s ease-in-out infinite reverse;
}

/* Voile neutre quasi-noir (jamais teinté par la surface) : très léger en
   haut, opaque en bas et sur la gauche pour que le texte reste lisible
   quelle que soit la photo — clair, sombre, cadrage serré ou large. */
.result-vignette {
  position: absolute;
  z-index: 2;
  inset: 0;
  background:
    linear-gradient(180deg, rgba(5, 6, 8, 0.15) 0%, rgba(5, 6, 8, 0.55) 55%, rgba(5, 6, 8, 0.94) 100%),
    linear-gradient(90deg, rgba(5, 6, 8, 0.75) 0%, rgba(5, 6, 8, 0.15) 42%, transparent 70%);
  pointer-events: none;
}

/* Reflet qui balaie la carte une seule fois au chargement — l'"effet wow"
   demandé, ponctuel plutôt qu'en boucle pour ne pas distraire. */
.result-shine {
  position: absolute;
  z-index: 2;
  top: -20%;
  left: 0;
  width: 34%;
  height: 140%;
  background: linear-gradient(100deg, transparent 0%, rgba(255, 255, 255, 0.16) 45%, transparent 100%);
  transform: translateX(-140%) skewX(-14deg);
  animation: resultShine 2.2s cubic-bezier(0.4, 0, 0.2, 1) 0.5s 1 both;
  pointer-events: none;
}

.result-flag {
  position: absolute;
  z-index: 3;
  top: 22px;
  left: 24px;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: #fff;
  object-fit: cover;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.5);
  opacity: 0;
  animation: resultRise 0.6s ease 0.05s both;
}
.result-brand {
  position: absolute;
  z-index: 3;
  top: 26px;
  right: 28px;
  font-family: 'Anton', sans-serif;
  font-size: 13px;
  font-weight: 400;
  letter-spacing: 0.14em;
  color: rgba(255, 255, 255, 0.55);
  opacity: 0;
  animation: resultRise 0.6s ease 0.1s both;
}

.result-inner {
  position: relative;
  z-index: 3;
  display: flex;
  align-items: flex-end;
  min-height: clamp(440px, 56vw, 640px);
  padding: 40px clamp(24px, 6vw, 72px) 48px;
}
.result-body {
  max-width: 720px;
}
.result-top-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 12px;
}
.result-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: 'Anton', sans-serif;
  font-size: 14px;
  font-weight: 400;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--lime);
  opacity: 0;
  animation: resultRise 0.6s ease 0.15s both;
}
.result-eyebrow::before {
  content: '';
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--lime);
  box-shadow: 0 0 12px 3px rgba(199, 255, 60, 0.75);
  animation: resultPulse 1.8s ease-in-out infinite;
}
/* Repère "pronostic" (passe premium, 16/09/2026) : confronte le résultat
   réel au favori annoncé avant le match — voir resultPronostic dans le
   script, jamais affiché si le match n'avait pas de favori déclaré. */
.result-pronostic {
  display: inline-flex;
  align-items: center;
  font-size: 11.5px;
  font-weight: 700;
  letter-spacing: 0.01em;
  padding: 4px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.18);
  backdrop-filter: blur(2px);
  opacity: 0;
  animation: resultRise 0.6s ease 0.2s both;
}
.result-pronostic.confirmed {
  color: var(--lime);
  border-color: rgba(199, 255, 60, 0.5);
  background: rgba(199, 255, 60, 0.14);
}
.result-pronostic.upset {
  color: var(--amber);
  border-color: rgba(255, 159, 10, 0.5);
  background: rgba(255, 159, 10, 0.14);
}
.result-winner {
  margin: 0;
  font-family: 'Anton', sans-serif;
  font-weight: 400;
  font-size: clamp(40px, 6.8vw, 84px);
  letter-spacing: 0.01em;
  line-height: 0.94;
  text-transform: uppercase;
  text-wrap: balance;
  text-shadow: 0 4px 24px rgba(0, 0, 0, 0.5);
  opacity: 0;
  clip-path: inset(0 0 100% 0);
  animation: resultWinnerReveal 0.9s var(--ease-premium) 0.25s both;
}
.result-sub {
  margin: 10px 0 0;
  font-size: 17px;
  color: rgba(255, 255, 255, 0.72);
  opacity: 0;
  animation: resultRise 0.6s ease 0.35s both;
}
.result-sets-wrap {
  margin-top: 26px;
  opacity: 0;
  animation: resultRise 0.6s ease 0.45s both;
}
.result-sets-label {
  display: block;
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.45);
  margin-bottom: 8px;
}
.result-sets {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.result-set-pill {
  padding: 6px 15px;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.65);
  border: 1px solid rgba(255, 255, 255, 0.16);
  backdrop-filter: blur(2px);
}
.result-set-pill.won {
  background: rgba(199, 255, 60, 0.2);
  color: var(--lime);
  border-color: rgba(199, 255, 60, 0.55);
  box-shadow:
    0 0 0 1px rgba(199, 255, 60, 0.12),
    0 6px 16px -6px rgba(199, 255, 60, 0.4);
}
.result-meta {
  margin-top: 20px;
  font-size: 13px;
  letter-spacing: 0.01em;
  color: rgba(255, 255, 255, 0.58);
  opacity: 0;
  animation: resultRise 0.6s ease 0.55s both;
}

/* Invite discrète à poursuivre (passe premium, 16/09/2026) : il y a
   toujours quelque chose juste en dessous (analyse, ou son déblocage) — un
   simple chevron qui respire, jamais insistant. */
.result-scrollcue {
  position: absolute;
  z-index: 3;
  left: 50%;
  bottom: 18px;
  transform: translateX(-50%);
  color: rgba(255, 255, 255, 0.55);
  opacity: 0;
  animation:
    resultRise 0.6s ease 0.9s both,
    resultBounce 2s ease-in-out 1.6s infinite;
}

@keyframes resultKenBurns {
  from {
    transform: scale(1.12);
  }
  to {
    transform: scale(1);
  }
}
@keyframes resultGlowDrift {
  0%,
  100% {
    transform: translate(0, 0) scale(1);
  }
  50% {
    transform: translate(-4%, 5%) scale(1.1);
  }
}
@keyframes resultShine {
  from {
    transform: translateX(-140%) skewX(-14deg);
  }
  to {
    transform: translateX(340%) skewX(-14deg);
  }
}
@keyframes resultRise {
  from {
    opacity: 0;
    transform: translateY(18px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
@keyframes resultPulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.45;
  }
}
@keyframes resultHairline {
  from {
    transform: scaleX(0);
  }
  to {
    transform: scaleX(1);
  }
}
@keyframes resultWinnerReveal {
  from {
    opacity: 0;
    transform: translateY(12px);
    clip-path: inset(0 0 100% 0);
  }
  to {
    opacity: 1;
    transform: translateY(0);
    clip-path: inset(0 0 0% 0);
  }
}
@keyframes resultBounce {
  0%,
  100% {
    transform: translateX(-50%) translateY(0);
  }
  50% {
    transform: translateX(-50%) translateY(6px);
  }
}

@media (prefers-reduced-motion: reduce) {
  .result-photo,
  .result-glow-a,
  .result-glow-b,
  .result-shine,
  .result-hairline,
  .result-flag,
  .result-brand,
  .result-eyebrow,
  .result-eyebrow::before,
  .result-pronostic,
  .result-winner,
  .result-sub,
  .result-sets-wrap,
  .result-meta,
  .result-scrollcue {
    animation: none !important;
    opacity: 1 !important;
    transform: none !important;
    clip-path: none !important;
  }
}

@media (max-width: 640px) {
  .result-showcase {
    min-height: clamp(420px, 145vw, 560px);
  }
  .result-inner {
    min-height: clamp(420px, 145vw, 560px);
    padding: 32px 22px 34px;
  }
  .result-vignette {
    background: linear-gradient(180deg, rgba(5, 6, 8, 0.1) 0%, rgba(5, 6, 8, 0.6) 55%, rgba(5, 6, 8, 0.96) 100%);
  }
  .result-photo {
    object-position: center 12%;
  }
  .result-sets {
    justify-content: flex-start;
  }
  .result-scrollcue {
    display: none;
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
.h2h-lead-tag {
  margin-top: 2px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--green);
  background: rgba(15, 61, 62, 0.08);
  padding: 2px 9px;
  border-radius: 999px;
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
/* Repère visuel du côté gagnant (passe "premium", 11/09/2026) : un point
   discret plutôt que de compter uniquement sur le gras + la couleur, pour
   rester lisible même en cas de daltonisme rouge/vert — et surlignage léger
   au survol de la ligne, pour que ce tableau dense se parcoure plus
   facilement que du texte figé. */
.stats-table td.win::after {
  content: '';
  display: inline-block;
  width: 5px;
  height: 5px;
  margin-left: 6px;
  border-radius: 50%;
  background: var(--green);
  vertical-align: middle;
}
.stats-table tbody tr {
  transition: background 0.2s ease;
}
.stats-table tbody tr:hover {
  background: rgba(15, 61, 62, 0.035);
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
  margin: 0;
  color: var(--ink);
  font-size: 15px;
}

/* Repli minimal (16/09/2026) : un simple lien-bouton, plus une carte pleine
   — la vraie invitation vit dans la popup "affiche" juste en dessous. */
.unlock-inline {
  text-align: center;
  padding: 10px 0 18px;
}
.unlock-inline-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: none;
  background: none;
  padding: 6px 4px;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--grey);
  text-decoration: underline;
  cursor: pointer;
  transition: color 0.15s ease;
}
.unlock-inline-btn:hover {
  color: var(--ink);
}
.unlock-inline-icon {
  font-size: 13px;
}

/* Popup "affiche" (16/09/2026, sur demande explicite avec capture de
   référence à l'appui) : même schéma d'overlay que PaywallModal.vue, mais
   un contenu réduit à une seule affiche (icône + message en très gros,
   fond dégradé vert/citron pleine carte façon poster) plutôt qu'un bloc de
   texte + formules — les formules restent dans le vrai popup de paiement,
   ouvert depuis le bouton "Voir les formules" ci-dessous. */
.unlock-overlay {
  position: fixed;
  inset: 0;
  /* Voile renforcé (19/09/2026, sur demande explicite) : à 0.56 d'opacité
     et 3px de flou, le nom du gagnant et le score d'un match déjà terminé
     (voir .result-showcase, affiché en dessous même quand l'analyse est
     verrouillée) restaient lisibles en transparence derrière ce popup. Le
     popup doit maintenant masquer complètement ce qu'il y a dessous. */
  background: rgba(4, 12, 12, 0.86);
  backdrop-filter: blur(28px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  z-index: 50;
  box-sizing: border-box;
}
.unlock-modal {
  position: relative;
  width: 100%;
  max-width: 360px;
  background: #fff;
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 32px 64px -20px rgba(2, 14, 14, 0.45);
  animation: modalIn 0.32s cubic-bezier(0.16, 1, 0.3, 1) both;
  padding: 22px 22px 26px;
  text-align: center;
  box-sizing: border-box;
}
@media (prefers-reduced-motion: reduce) {
  .unlock-modal {
    animation: none;
  }
}
.unlock-poster {
  position: relative;
  overflow: hidden;
  isolation: isolate;
  border-radius: 18px;
  padding: 36px 20px 30px;
  margin-bottom: 18px;
  background:
    radial-gradient(130% 160% at 50% -20%, rgba(199, 255, 60, 0.32) 0%, transparent 60%),
    linear-gradient(135deg, var(--green), var(--green2));
}
.unlock-poster-icon {
  display: block;
  width: 42px;
  height: 42px;
  margin: 0 auto 12px;
  /* Rebond façon vraie balle de tennis (17/09/2026, demande explicite) :
     un grand rebond puis un plus petit avant une pause, plutôt qu'un simple
     va-et-vient — voir unlockBallBounce ci-dessous. */
  animation: unlockBallBounce 1.8s ease-in-out infinite;
}
.unlock-poster-text {
  margin: 0;
  font-family: 'Anton', sans-serif;
  font-weight: 400;
  font-size: clamp(28px, 8vw, 36px);
  line-height: 1.05;
  letter-spacing: 0.01em;
  text-transform: uppercase;
  color: #fff;
  text-shadow: 0 4px 18px rgba(0, 0, 0, 0.3);
}
@keyframes unlockBallBounce {
  0%,
  20%,
  50%,
  80%,
  100% {
    transform: translateY(0);
  }
  40% {
    transform: translateY(-16px);
  }
  60% {
    transform: translateY(-7px);
  }
}
@media (prefers-reduced-motion: reduce) {
  .unlock-poster-icon {
    animation: none !important;
  }
}
.unlock-modal-cta {
  width: 100%;
  border: none;
  border-radius: 12px;
  padding: 13px;
  background: var(--ink);
  color: #fff;
  font-size: 14.5px;
  font-weight: 700;
  cursor: pointer;
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.unlock-modal-cta:hover {
  transform: translateY(-1px);
  opacity: 0.92;
}
.unlock-modal-already {
  display: block;
  margin-top: 14px;
  font-size: 12.5px;
  color: var(--grey);
  text-decoration: underline;
  cursor: pointer;
}

h3 {
  font-size: 15px;
  font-weight: 700;
  margin: 0 0 18px;
}
.sub {
  margin-top: -12px;
  margin-bottom: 16px;
  font-size: 13px;
  color: var(--grey);
  line-height: 1.5;
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
  padding: 8px 10px;
  margin: 0 -10px;
  border-radius: 12px;
  transition: background 0.2s ease;
}
.factors li:hover {
  background: rgba(15, 61, 62, 0.035);
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
.factor-text {
  display: block;
}
.factor-favors {
  display: inline-block;
  margin-left: 4px;
  font-size: 12px;
  font-weight: 600;
  color: var(--green);
  white-space: nowrap;
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
