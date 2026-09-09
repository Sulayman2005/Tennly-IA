<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
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

async function loadMatches({ silent = false } = {}) {
  if (!silent) {
    loading.value = true
    error.value = null
  }
  try {
    const nowIso = new Date().toISOString()
    const [upcoming, finishedData] = await Promise.all([
      fetchAllPages(`?status=scheduled&scheduledAt[strictly_after]=${encodeURIComponent(nowIso)}&order[scheduledAt]=asc&order[id]=asc&itemsPerPage=50`),
      api.get('/api/tennis_matches?status[]=finished&status[]=walkover&order[scheduledAt]=desc&order[id]=desc&itemsPerPage=50'),
    ])
    const rest = finishedData['hydra:member'] ?? finishedData['member'] ?? finishedData
    matches.value = [...upcoming, ...rest]
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

    <p v-if="loading" class="state-msg">Chargement des analyses…</p>
    <p v-else-if="error" class="state-msg error">Impossible de charger les matchs pour le moment.</p>
    <div v-else-if="!matches.length" class="state-empty">
      <div class="icon">🎾</div>
      <p>Aucun match pour le moment — reviens un peu plus tard.</p>
    </div>
    <div v-else class="match-list">
      <div v-for="(match, i) in matches" :key="match.id" class="match-item" :style="{ animationDelay: i * 0.05 + 's' }">
        <MatchCard :match="match" @open="openMatch" />
      </div>
    </div>
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
</style>
