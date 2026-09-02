<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'
import MatchCard from '@/components/MatchCard.vue'

const router = useRouter()

// "À venir" par défaut : c'est là que l'analyse IA sert le plus (avant le
// match, pas après) — voir le calendrier des matchs à venir (roadmap).
const activeTab = ref('a-venir')

const matches = ref([])
const loading = ref(true)
const error = ref(null)

async function loadMatches(tab) {
  loading.value = true
  error.value = null
  try {
    // Statuts réels de MatchStatus (voir cahier des charges) : "scheduled"
    // = pas encore joué, "finished"/"walkover" = déjà joué. order[scheduledAt]
    // est fourni par l'OrderFilter ajouté sur TennisMatch — l'ordre par
    // défaut de l'API reste ASC pour tout le reste, on ne le change qu'ici.
    //
    // scheduledAt[strictly_after] (DateFilter) : un match "scheduled" reste
    // "scheduled" en base tant que le script d'import n'est pas relancé —
    // sans ce filtre, un match dont l'heure est déjà passée resterait
    // affiché dans "À venir" au lieu de disparaître naturellement.
    const query = tab === 'a-venir'
      ? `?status=scheduled&order[scheduledAt]=asc&scheduledAt[strictly_after]=${encodeURIComponent(new Date().toISOString())}`
      : '?status[]=finished&status[]=walkover&order[scheduledAt]=desc'
    const data = await api.get(`/api/tennis_matches${query}`)
    matches.value = data['hydra:member'] ?? data['member'] ?? data
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}

onMounted(() => loadMatches(activeTab.value))
watch(activeTab, (tab) => loadMatches(tab))

const emptyMessage = computed(() =>
  activeTab.value === 'a-venir'
    ? "Aucun match à venir pour le moment — reviens un peu plus tard."
    : 'Aucun résultat récent pour le moment.',
)

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
    <h1>Matchs</h1>
    <p class="sub">Analyse IA avant et après chaque match</p>

    <div class="tabs" role="tablist">
      <button
        role="tab"
        :aria-selected="activeTab === 'a-venir'"
        :class="{ active: activeTab === 'a-venir' }"
        @click="activeTab = 'a-venir'"
      >
        À venir
      </button>
      <button
        role="tab"
        :aria-selected="activeTab === 'recents'"
        :class="{ active: activeTab === 'recents' }"
        @click="activeTab = 'recents'"
      >
        Résultats récents
      </button>
    </div>

    <p v-if="loading">Chargement des analyses…</p>
    <p v-else-if="error">Impossible de charger les matchs pour le moment.</p>
    <p v-else-if="!matches.length" class="empty">{{ emptyMessage }}</p>
    <template v-else>
      <MatchCard v-for="match in matches" :key="match.id" :match="match" @open="openMatch" />
    </template>
  </section>
</template>

<style scoped>
.matches {
  padding: 32px 0 60px;
}
h1 {
  font-size: 28px;
  font-weight: 700;
  margin: 0 0 4px;
}
.sub {
  color: var(--grey);
  font-size: 13px;
  margin-bottom: 20px;
}
.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
  border-bottom: 1px solid var(--line);
}
.tabs button {
  background: none;
  border: none;
  padding: 10px 4px;
  margin-right: 20px;
  font-size: 14px;
  font-weight: 600;
  color: var(--grey);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: color 0.15s ease, border-color 0.15s ease;
}
.tabs button.active {
  color: var(--ink);
  border-bottom-color: var(--green);
}
.empty {
  color: var(--grey);
  font-size: 14px;
}
</style>