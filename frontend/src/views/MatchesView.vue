<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import MatchCard from '@/components/MatchCard.vue'
import PaywallModal from '@/components/PaywallModal.vue'

const router = useRouter()
const auth = useAuthStore()

const matches = ref([])
const loading = ref(true)
const error = ref(null)
const paywallOpen = ref(false)

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

/**
 * Cahier des charges section 3.2.1 : un abonné accède directement à la fiche
 * détaillée ; un visiteur non abonné voit la popup paywall, jamais l'inverse.
 */
function openMatch(match) {
  if (auth.hasActiveSubscription) {
    router.push({ name: 'match-detail', params: { id: match.id } })
  } else {
    paywallOpen.value = true
  }
}
</script>

<template>
  <section class="matches">
    <h1>Matchs du jour</h1>
    <p class="sub">Mis à jour en continu</p>

    <p v-if="loading">Chargement des pronostics…</p>
    <p v-else-if="error">Impossible de charger les matchs pour le moment.</p>
    <template v-else>
      <MatchCard v-for="match in matches" :key="match.id" :match="match" @open="openMatch" />
    </template>
  </section>

  <PaywallModal :open="paywallOpen" @close="paywallOpen = false" />
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
