<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'
import MatchCard from '@/components/MatchCard.vue'

const router = useRouter()

const matches = ref([])
const loading = ref(true)
const error = ref(null)

onMounted(async () => {
  try {
    // GET /api/tennis_matches (aperçu gratuit, accès public — section 3.2).
    const data = await api.get('/api/tennis_matches')
    matches.value = data['hydra:member'] ?? data['member'] ?? data
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
})

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
    <h1>Matchs du jour</h1>
    <p class="sub">Mis à jour en continu</p>

    <p v-if="loading">Chargement des analyses…</p>
    <p v-else-if="error">Impossible de charger les matchs pour le moment.</p>
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
  margin-bottom: 24px;
}
</style>