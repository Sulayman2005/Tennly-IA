<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'
import MatchCard from '@/components/MatchCard.vue'

const router = useRouter()

const matches = ref([])
const loading = ref(true)
const error = ref(null)
let pollTimer = null

async function fetchAllPages(query) {
  let path = `/api/tennis_matches${query}`
  const all = []
  while (path) {
    const data = await api.get(path)
    all.push(...(data['hydra:member'] ?? data['member'] ?? data))
    path = data['hydra:view']?.['hydra:next'] ?? null
  }
  return all
}

// Corrigé le 10/09/2026 : cette fonction ne récupérait QUE les matchs
// 'scheduled' à venir et les matchs 'finished'/'walkover' — un match
// 'live' (en cours) n'était interrogé nulle part et disparaissait donc
// purement et simplement de la page, alors que c'est justement le plus
// urgent à voir. Ajout d'un troisième appel dédié, mis en tête de liste
// (voir aussi le badge .mc-live sur MatchCard.vue).
async function loadMatches({ silent = false } = {}) {
  if (!silent) {
    loading.value = true
    error.value = null
  }
  try {
    const nowIso = new Date().toISOString()
    const [liveData, upcoming, finishedData] = await Promise.all([
      api.get('/api/tennis_matches?status=live&order[scheduledAt]=asc&itemsPerPage=50'),
      fetchAllPages(`?status=scheduled&scheduledAt[strictly_after]=${encodeURIComponent(nowIso)}&order[scheduledAt]=asc&order[id]=asc&itemsPerPage=50`),
      api.get('/api/tennis_matches?status[]=finished&status[]=walkover&order[scheduledAt]=desc&order[id]=desc&itemsPerPage=50'),
    ])
    const live = liveData['hydra:member'] ?? liveData['member'] ?? liveData
    const rest = finishedData['hydra:member'] ?? finishedData['member'] ?? finishedData
    matches.value = [...live, ...upcoming, ...rest]
    error.value = null
  } catch (e) {
    if (!silent) error.value = e
  } finally {
    if (!silent) loading.value = false
  }
}

onMounted(() => {
  loadMatches()
  pollTimer = setInterval(() => loadMatches({ silent: true }), 60000)
})
onUnmounted(() => clearInterval(pollTimer))

function openMatch(match) {
  router.push({ name: 'match-detail', params: { id: match.id } })
}

// Filtres (10/09/2026, passe "rendu premium") : purement client — tout est
// déjà chargé en mémoire (voir matches ci-dessus), donc filtrer ne relance
// aucun appel réseau. "Tous" en premier et sélectionné par défaut pour ne
// rien cacher au premier affichage.
const activeFilter = ref('all')
const filters = [
  { key: 'all', label: 'Tous' },
  { key: 'live', label: 'En direct' },
  { key: 'scheduled', label: 'À venir' },
  { key: 'done', label: 'Terminés' },
]
const filteredMatches = computed(() => {
  if (activeFilter.value === 'all') return matches.value
  if (activeFilter.value === 'done') {
    return matches.value.filter((m) => m.status === 'finished' || m.status === 'walkover')
  }
  return matches.value.filter((m) => m.status === activeFilter.value)
})
function filterCount(key) {
  if (key === 'all') return matches.value.length
  if (key === 'done') return matches.value.filter((m) => m.status === 'finished' || m.status === 'walkover').length
  return matches.value.filter((m) => m.status === key).length
}
</script>

<template>
  <section class="matches">
    <!-- Fond décoratif de l'en-tête : plusieurs taches de couleur (teal,
         lime, bleu dur, terre battue — les mêmes familles que les surfaces
         des cartes juste en dessous) qui dérivent très lentement, plutôt
         qu'un unique aplat vert. Purement décoratif (aria-hidden), toujours
         derrière le texte (z-index), et neutralisé si l'utilisateur préfère
         moins de mouvement. -->
    <div class="hero-glow" aria-hidden="true">
      <span class="blob blob-a"></span>
      <span class="blob blob-b"></span>
      <span class="blob blob-c"></span>
    </div>

    <div class="page-head">
      <div class="eyebrow"><i></i>CIRCUIT ATP & WTA · PROGRAMME DU JOUR</div>
      <h1>Chaque <span class="accent">match</span>, une analyse claire.</h1>
      <p class="sub">Favori pressenti, probabilité et analyse complète (radar, facteurs, cote de valeur) réservés à nos abonnés — le calendrier des matchs à venir reste consultable par tous.</p>
    </div>

    <!-- Squelette de chargement (10/09/2026, passe "rendu premium") :
         remplace le simple texte "Chargement…" par des cartes fantômes qui
         imitent la forme d'une vraie MatchCard (shimmer qui balaie),
         puisque la liste peut mettre un instant à arriver et qu'un texte
         seul, sur une page par ailleurs déjà très visuelle, détonnait. -->
    <div v-if="loading" class="match-list" aria-hidden="true">
      <div v-for="n in 4" :key="n" class="skeleton-card" :style="{ animationDelay: n * 0.06 + 's' }"></div>
    </div>
    <p v-else-if="error" class="state-msg error">Impossible de charger les matchs pour le moment.</p>
    <div v-else-if="!matches.length" class="state-empty">
      <div class="icon">🎾</div>
      <p>Aucun match pour le moment — reviens un peu plus tard.</p>
    </div>
    <template v-else>
      <!-- Filtres (10/09/2026) : purement client, voir filteredMatches dans
           le script — aucun rechargement réseau au clic. -->
      <div class="filter-row" role="tablist" aria-label="Filtrer les matchs">
        <button
          v-for="f in filters"
          :key="f.key"
          type="button"
          role="tab"
          class="filter-chip"
          :class="{ active: activeFilter === f.key, live: f.key === 'live' && filterCount('live') > 0 }"
          :aria-selected="activeFilter === f.key"
          @click="activeFilter = f.key"
        >
          <i v-if="f.key === 'live' && filterCount('live') > 0"></i>
          {{ f.label }}
          <span class="filter-count">{{ filterCount(f.key) }}</span>
        </button>
      </div>

      <p v-if="!filteredMatches.length" class="state-empty-inline">Aucun match dans cette catégorie pour le moment.</p>
      <div v-else class="match-list">
        <div v-for="(match, i) in filteredMatches" :key="match.id" class="match-item" :style="{ animationDelay: Math.min(i, 10) * 0.05 + 's' }">
          <MatchCard :match="match" @open="openMatch" />
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.matches {
  position: relative;
  padding: 48px 0 60px;
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
@keyframes drift {
  0% {
    transform: translate(0, 0) scale(1);
  }
  50% {
    transform: translate(var(--drift-x, 24px), var(--drift-y, -18px)) scale(1.08);
  }
  100% {
    transform: translate(0, 0) scale(1);
  }
}
@media (prefers-reduced-motion: reduce) {
  .match-item {
    animation-duration: 0.001ms !important;
  }
  .blob {
    animation: none !important;
  }
}

.hero-glow {
  position: absolute;
  top: -60px;
  left: -10%;
  right: -10%;
  height: 340px;
  z-index: 0;
  overflow: hidden;
  pointer-events: none;
}
.blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  opacity: 0.35;
  animation: drift 16s ease-in-out infinite;
}
.blob-a {
  width: 320px;
  height: 320px;
  top: -80px;
  left: 2%;
  background: radial-gradient(circle, var(--lime), transparent 70%);
  --drift-x: 30px;
  --drift-y: 14px;
}
.blob-b {
  width: 280px;
  height: 280px;
  top: -40px;
  left: 32%;
  background: radial-gradient(circle, var(--blue), transparent 70%);
  animation-duration: 20s;
  animation-delay: -4s;
  --drift-x: -26px;
  --drift-y: 20px;
}
.blob-c {
  width: 260px;
  height: 260px;
  top: 10px;
  right: 6%;
  background: radial-gradient(circle, var(--clay), transparent 70%);
  animation-duration: 18s;
  animation-delay: -9s;
  --drift-x: -20px;
  --drift-y: -16px;
}

.page-head {
  position: relative;
  z-index: 1;
  max-width: 640px;
  margin: 0 0 32px;
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
  animation: pulse 2.4s ease-in-out infinite;
}
@keyframes pulse {
  0%,
  100% {
    box-shadow: 0 0 0 3px rgba(199, 255, 60, 0.25);
  }
  50% {
    box-shadow: 0 0 0 6px rgba(199, 255, 60, 0.12);
  }
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
.sub {
  font-size: 16px;
  line-height: 1.55;
  color: var(--grey);
  margin: 0;
}

.state-msg {
  position: relative;
  z-index: 1;
  color: var(--grey);
  font-size: 14px;
  padding: 8px 0;
}
.state-msg.error {
  color: var(--red);
}
.state-empty {
  position: relative;
  z-index: 1;
  border: 1.5px dashed var(--line);
  border-radius: 22px;
  padding: 52px 20px;
  text-align: center;
  color: var(--grey);
}
.state-empty .icon {
  font-size: 26px;
  margin-bottom: 10px;
}
.state-empty p {
  margin: 0;
  font-size: 14px;
}
.state-empty-inline {
  position: relative;
  z-index: 1;
  color: var(--grey);
  font-size: 14px;
  padding: 24px 0;
}

/* -- Filtres (10/09/2026) -- */
.filter-row {
  position: relative;
  z-index: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0 0 22px;
}
.filter-chip {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border: 1px solid var(--line);
  background: var(--bg);
  color: var(--grey);
  font-size: 13px;
  font-weight: 600;
  padding: 9px 16px;
  border-radius: 999px;
  cursor: pointer;
  transition:
    background 0.25s ease,
    border-color 0.25s ease,
    color 0.25s ease,
    transform 0.3s var(--ease-premium);
}
.filter-chip:hover {
  border-color: var(--green);
  color: var(--ink);
  transform: translateY(-1px);
}
.filter-chip.active {
  background: var(--btn);
  border-color: var(--btn);
  color: #fff;
}
.filter-chip.live:not(.active) {
  border-color: rgba(255, 69, 58, 0.4);
  color: var(--red);
}
.filter-chip i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--red);
  animation: pulse 1.6s ease-in-out infinite;
}
.filter-chip.active i {
  background: #fff;
}
.filter-count {
  font-size: 11px;
  font-weight: 700;
  color: inherit;
  opacity: 0.6;
  font-variant-numeric: tabular-nums;
}

.match-list {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.match-item {
  animation: fadeUp 0.5s ease both;
}

/* -- Squelette de chargement (10/09/2026) --
   Même gabarit qu'une MatchCard (hauteur/rayon proches) pour que le
   passage au vrai contenu ne "saute" pas visuellement, avec un shimmer qui
   balaie en boucle plutôt qu'un simple gris figé. */
.skeleton-card {
  position: relative;
  overflow: hidden;
  height: 172px;
  border-radius: 20px;
  margin-bottom: 16px;
  background: var(--card);
  animation: fadeUp 0.4s ease both;
}
.skeleton-card::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(100deg, transparent 30%, rgba(255, 255, 255, 0.7) 50%, transparent 70%);
  transform: translateX(-100%);
  animation: skeletonShimmer 1.6s ease-in-out infinite;
}
@keyframes skeletonShimmer {
  to {
    transform: translateX(100%);
  }
}
@media (prefers-reduced-motion: reduce) {
  .skeleton-card::after {
    animation: none;
  }
}
</style>
