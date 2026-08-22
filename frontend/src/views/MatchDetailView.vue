<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, ApiError } from '@/api/client'
import ProbabilityGauge from '@/components/ProbabilityGauge.vue'
import RadarChart from '@/components/RadarChart.vue'
import PaywallModal from '@/components/PaywallModal.vue'

const props = defineProps({ id: { type: [String, Number], required: true } })
const route = useRoute()
const router = useRouter()

const match = ref(null)
const prediction = ref(null)
const loading = ref(true)
const forbidden = ref(false)
const paywallOpen = ref(false)

onMounted(async () => {
  try {
    // GET /api/tennis_matches/{id} : infos publiques du match (aperçu gratuit).
    match.value = await api.get(`/api/tennis_matches/${props.id}`)

    // match.value.prediction est désormais un objet embarqué (groupe
    // "match:read" — voir Player::class et Prediction::class côté backend) et
    // non plus une simple IRI : il contient déjà id/favoritePlayer/
    // probabilityFavorite/confidenceLevel pour l'aperçu gratuit (section
    // 3.3.1). La fiche détaillée (section 3.3.2-3.3.4 : radar, facteurs
    // d'explication, cote de marché) est chargée séparément via son id, car
    // l'opération GET /api/predictions/{id} exige un abonnement actif.
    if (match.value.prediction) {
      prediction.value = await api.get(`/api/predictions/${match.value.prediction.id}`)
    }
  } catch (e) {
    if (e instanceof ApiError && e.status === 403) {
      forbidden.value = true
    } else {
      console.error(e)
    }
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="detail">
    <a class="back" @click="router.push('/matchs')">← Retour au tableau des matchs</a>

    <p v-if="loading">Chargement…</p>

    <template v-else-if="match">
      <div class="card face-off">
        <div class="player">
          <div class="avatar">{{ match.playerA.fullName.split(' ').map((w) => w[0]).join('') }}</div>
          <div class="name">{{ match.playerA.fullName }}</div>
          <div class="rank">N°{{ match.playerA.atpWtaRank }} mondial</div>
        </div>

        <ProbabilityGauge
          v-if="match.prediction"
          :probability="match.prediction.probabilityFavorite"
          :label="'Favori : ' + match.prediction.favoritePlayer.fullName"
        />

        <div class="player">
          <div class="avatar blue">{{ match.playerB.fullName.split(' ').map((w) => w[0]).join('') }}</div>
          <div class="name">{{ match.playerB.fullName }}</div>
          <div class="rank">N°{{ match.playerB.atpWtaRank }} mondial</div>
        </div>
      </div>

      <div v-if="forbidden" class="card locked">
        <p>🔒 Analyse complète réservée aux abonnés.</p>
        <button class="btn-primary" @click="paywallOpen = true">Débloquer l'analyse complète</button>
      </div>

      <template v-else-if="prediction">
        <div class="card">
          <h3>Profil comparatif</h3>
          <RadarChart :profile="prediction.radarProfile" :label-a="match.playerA.fullName" :label-b="match.playerB.fullName" />
        </div>

        <div class="card">
          <h3>Pourquoi ce pronostic ?</h3>
          <ul class="factors">
            <li v-for="(factor, i) in prediction.explanationFactors" :key="i" :class="factor.tone">
              <span class="tag">{{ factor.tone === 'warn' ? '!' : '✓' }}</span>
              {{ factor.label }}
            </li>
          </ul>
        </div>
      </template>
    </template>
  </div>

  <PaywallModal :open="paywallOpen" @close="paywallOpen = false" />
</template>

<style scoped>
.detail {
  padding: 24px 0 60px;
}
.back {
  color: var(--grey);
  font-size: 13px;
  cursor: pointer;
  display: inline-block;
  margin-bottom: 20px;
}
.card {
  padding: 28px;
  margin-bottom: 18px;
}
.face-off {
  display: flex;
  align-items: center;
  justify-content: space-around;
}
.player {
  text-align: center;
}
.avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--green);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  margin: 0 auto 10px;
}
.avatar.blue {
  background: var(--blue);
}
.name {
  font-weight: 700;
}
.rank {
  font-size: 12px;
  color: var(--grey);
}
.locked {
  text-align: center;
}
.locked p {
  margin-bottom: 16px;
}
h3 {
  font-size: 15px;
  margin: 0 0 16px;
}
.factors {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  font-size: 14px;
}
.factors .tag {
  margin-right: 8px;
}
.factors .warn .tag {
  color: var(--amber);
}
.factors li:not(.warn) .tag {
  color: #2e9e4d;
}
</style>
