<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, ApiError } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import RadarChart from '@/components/RadarChart.vue'
import PaywallModal from '@/components/PaywallModal.vue'
import PostPaymentModal from '@/components/PostPaymentModal.vue'
import TourBadge from '@/components/TourBadge.vue'
import ProbabilityGauge from '@/components/ProbabilityGauge.vue'
import { initials, avatarGradient, flagUrl, surfaceCardVars, hasPhoto, surfaceLabel } from '@/utils/playerVisuals'

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
      <div class="card face-off" :style="surfaceCardVars(match.surface)">
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
          <div class="name">{{ match.playerA.fullName }}</div>
          <div class="rank">N°{{ match.playerA.atpWtaRank }} mondial</div>
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
          <div class="name">{{ match.playerB.fullName }}</div>
          <div class="rank">N°{{ match.playerB.atpWtaRank }} mondial</div>
        </div>
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
