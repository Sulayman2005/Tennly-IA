<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'
import MatchCard from '@/components/MatchCard.vue'

const router = useRouter()

// Avant : deux onglets "À venir" / "Résultats récents" filtrant chacun sur
// le statut + une date de coupure — source de confusion (le principe
// n'était pas clair) et surtout d'un onglet "À venir" vide dès qu'aucun
// match n'a une date strictement future en base, même quand des matchs
// existent bel et bien. Remplacé par une liste unique, tous statuts et
// toutes compétitions confondus, la plus simple à comprendre : "tous les
// matchs, un point c'est tout" (voir MatchCard, qui indique désormais
// lui-même "À venir"/"Terminé" par carte plutôt que par onglet).
const matches = ref([])
const loading = ref(true)
const error = ref(null)
let pollTimer = null

// Une seule requête sans itemsPerPage explicite ne renvoie qu'une page de la
// taille par défaut d'API Platform (bien en dessous du nombre réel de matchs
// à venir une fois le calendrier ATP/WTA importé — voir ml-service/
// import_upcoming_matches.py) : on suivait silencieusement une troncature,
// jamais un vrai "tous les matchs". On demande donc explicitement le
// itemsPerPage maximum autorisé par l'API PUIS on parcourt hydra:view/
// hydra:next tant qu'il y en a, pour ne jamais couper la liste.
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
    // Priorité absolue aux matchs "scheduled" (à venir) — c'est là que
    // l'analyse IA sert vraiment (voir demande explicite : "les matchs finis
    // on s'en fout un peu, ce qu'on veut c'est analyser les prochains
    // matchs") — récupérés en intégralité (toutes les pages), triés du plus
    // imminent au plus lointain. Les matchs déjà joués passent ensuite, en
    // second plan, une seule page suffit largement pour ceux-là.
    const [upcoming, finishedData] = await Promise.all([
      fetchAllPages('?status=scheduled&order[scheduledAt]=asc&itemsPerPage=50'),
      api.get('/api/tennis_matches?status[]=finished&status[]=walkover&order[scheduledAt]=desc&itemsPerPage=50'),
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
  // Rafraîchissement automatique : un match "scheduled" peut passer à
  // "finished" (résultat réel + nouvelle prédiction) entre deux visites, dès
  // que le script d'import ml-service tourne à nouveau. On réinterroge
  // l'API en tâche de fond toutes les 60s (sans état de chargement ni
  // erreur visible entre-temps, `silent: true`) pour que la page reste à
  // jour sans que l'utilisateur ait besoin de la recharger lui-même.
  pollTimer = setInterval(() => loadMatches({ silent: true }), 60000)
})
onUnmounted(() => clearInterval(pollTimer))

// Un clic sur un match amène toujours à sa fiche détaillée (MatchDetailView.vue),
// qu'il soit abonné ou non. C'est cette fiche, et elle seule, qui décide si
// l'aperçu suffit ou si elle affiche la carte verrouillée + le bouton
// "Débloquer l'analyse complète" ouvrant PaywallModal — jamais cette liste.
function openMatch(match) {
  router.push({ name: 'match-detail', params: { id: match.id } })
}
</script>

<template>
  <section class="matches">
    <div class="page-head">
      <div class="eyebrow"><i></i>IA TENNIS · ANALYSES DU JOUR</div>
      <h1>Chaque <span class="accent">match</span>, une analyse claire.</h1>
      <p class="sub">Favori pressenti et probabilité en aperçu gratuit sur chaque match — l'analyse complète (radar, facteurs, cote de valeur) juste en dessous pour les abonnés.</p>
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
@media (prefers-reduced-motion: reduce) {
  .match-item {
    animation-duration: 0.001ms !important;
  }
}

.page-head {
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
  color: var(--grey);
  font-size: 14px;
  padding: 8px 0;
}
.state-msg.error {
  color: var(--red);
}
.state-empty {
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
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.match-item {
  animation: fadeUp 0.5s ease both;
}
</style>