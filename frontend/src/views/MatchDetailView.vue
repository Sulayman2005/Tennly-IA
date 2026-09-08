<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, ApiError } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import RadarChart from '@/components/RadarChart.vue'
import PaywallModal from '@/components/PaywallModal.vue'
import PostPaymentModal from '@/components/PostPaymentModal.vue'
import TourBadge from '@/components/TourBadge.vue'
import ProbabilityGauge from '@/components/ProbabilityGauge.vue'
import { initials, avatarGradient, flagUrl, surfaceCardVars } from '@/utils/playerVisuals'

const props = defineProps({ id: { type: [String, Number], required: true } })
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

// Un 403 sur /api/predictions/{id} peut venir de deux cas différents (voir
// Prediction::class côté backend) : un visiteur non connecté (le plus
// fréquent), ou un compte déjà connecté mais sans abonnement actif. Seul le
// premier cas doit proposer "Se connecter" — un utilisateur déjà authentifié
// n'a pas de compte à retrouver, il lui faut une formule.
function goToLogin() {
  router.push({ name: 'connexion', query: { redirect: route.fullPath } })
}

// isFavorite/avatarGradient/flag/surfaceCardVars : voir utils/playerVisuals.js
// — même traitement visuel que MatchCard.vue (liste /matchs), pour que le
// joueur retrouve exactement le même avatar entre la liste et la fiche.
function isFavorite(player) {
  return match.value?.prediction?.favoritePlayer?.id === player.id
}

const match = ref(null)
const prediction = ref(null)
const loading = ref(true)
const forbidden = ref(false)
const paywallOpen = ref(false)
const postPaymentOpen = ref(false)

// Retour depuis Stripe Checkout après paiement (voir CheckoutSessionController/
// StripeCheckoutService côté backend, qui renvoie ici avec ?paiement=reussi).
const justPaid = ref(route.query.paiement === 'reussi')
const checkoutSessionId = ref(typeof route.query.session_id === 'string' ? route.query.session_id : '')
const activating = ref(false)

/**
 * Une fois PostPaymentModal.vue arrivé à créer le compte (ou connecter
 * l'utilisateur) ET relier le paiement (CheckoutSessionLinkController), plus
 * besoin d'attendre un webhook : on recharge directement le match, qui doit
 * maintenant s'afficher débloqué. On nettoie aussi l'URL pour ne pas
 * rouvrir ce panneau à un rechargement de page.
 */
async function onPostPaymentLinked() {
  postPaymentOpen.value = false
  router.replace({ path: route.path })
  await loadMatch()
}

async function loadMatch() {
  try {
    // GET /api/tennis_matches/{id} : infos publiques du match (aperçu gratuit).
    match.value = await api.get(`/api/tennis_matches/${props.id}`)
    forbidden.value = false

    // match.value.prediction est un objet embarqué (voir Prediction::class
    // côté backend), mais son contenu dépend des droits de l'utilisateur
    // (décision produit du 02/09/2026) : tout le monde reçoit au moins
    // { id }, alors que favoritePlayer/probabilityFavorite/confidenceLevel
    // (l'aperçu gratuit, section 3.3.1) n'apparaissent que pour un
    // ROLE_ADMIN ou un abonné actif (groupe 'match:read:prediction', ajouté
    // par Serializer/TennisMatchContextBuilder.php). On teste ici sur la
    // seule présence de l'objet (donc sur son id) plutôt que sur
    // favoritePlayer : même un non-abonné doit déclencher cet appel, pour
    // que le 401/403 ci-dessous active bien la carte paywall — sans ça, un
    // visiteur non connecté ne verrait plus jamais "Débloquer l'analyse
    // complète". La fiche détaillée (section 3.3.2-3.3.4 : radar, facteurs
    // d'explication, cote de marché) est chargée séparément via cet id, car
    // l'opération GET /api/predictions/{id} exige déjà un abonnement actif.
    if (match.value.prediction) {
      prediction.value = await api.get(`/api/predictions/${match.value.prediction.id}`)
    }
  } catch (e) {
    // 403 : compte connecté mais sans abonnement actif (voir Prediction::class
    // côté backend). 401 "JWT Token not found" : visiteur non connecté du
    // tout — le firewall Symfony rejette la requête avant même d'évaluer
    // l'expression de sécurité, donc jamais de 403 dans ce cas précis. Les
    // deux veulent dire la même chose côté interface : l'analyse complète
    // n'est pas accessible à cet utilisateur, donc la carte verrouillée.
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

  // Décision produit du 03/09/2026 : le paiement peut désormais démarrer
  // avant toute connexion (voir choosePlan() dans PaywallModal.vue). Un
  // retour de paiement sans être connecté veut donc dire qu'aucun compte
  // n'existe encore pour ce paiement précis — inutile d'attendre le webhook
  // Stripe, PostPaymentModal.vue crée le compte (ou connecte l'utilisateur)
  // puis relie ce paiement lui-même (CheckoutSessionLinkController).
  if (justPaid.value && !auth.isAuthenticated) {
    postPaymentOpen.value = true
  } else if (justPaid.value && forbidden.value) {
    // Utilisateur déjà connecté au moment de payer : le webhook Stripe
    // (StripeWebhookController) active l'abonnement de façon asynchrone, et
    // au retour immédiat de Checkout il peut ne pas encore être passé. Un
    // seul nouvel essai après un court délai suffit dans l'immense majorité
    // des cas, plutôt que de laisser l'utilisateur sur l'écran verrouillé
    // alors qu'il vient tout juste de payer.
    activating.value = true
    setTimeout(async () => {
      await loadMatch()
      activating.value = false
    }, 3000)
  } else if (forbidden.value && auth.isAuthenticated) {
    // Un utilisateur déjà connecté (mais non abonné) a déjà vu la carte
    // verrouillée par le passé : lui refaire cliquer "Débloquer l'analyse
    // complète" à chaque fois est une étape en trop, vue et revue (demande
    // explicite du 03/09/2026). On ouvre donc directement la popup de choix
    // de formule dès l'arrivée sur la fiche — la carte verrouillée reste
    // affichée derrière, au cas où l'utilisateur ferme la popup sans payer.
    // Un visiteur non connecté, lui, garde la carte verrouillée telle
    // quelle : il doit d'abord choisir "Créer un compte" ou "Se connecter".
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
        <div class="player">
          <div class="avatar" :class="{ 'is-favorite': isFavorite(match.playerA) }" :style="avatarGradient(match.playerA.fullName)">
            <span class="avatar-initials">{{ initials(match.playerA.fullName) }}</span>
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
          <!-- match.prediction existe désormais pour tout le monde (au moins
               { id }, voir TennisMatch::$prediction côté backend) — seul un
               ROLE_ADMIN ou un abonné actif reçoit aussi favoritePlayer /
               probabilityFavorite (groupe 'match:read:prediction'). D'où le
               test sur favoritePlayer et non sur match.prediction seul :
               sinon la jauge tenterait de s'afficher avec des données
               absentes pour un non-abonné. -->
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
          <div class="avatar" :class="{ 'is-favorite': isFavorite(match.playerB) }" :style="avatarGradient(match.playerB.fullName)">
            <span class="avatar-initials">{{ initials(match.playerB.fullName) }}</span>
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

/* Fond "wow" cohérent avec MatchCard.vue (liste /matchs) : même dégradé
   teal + halo coloré selon la surface, plutôt que le fond clair générique
   hérité de la classe .card partagée avec le reste de l'app — voir
   utils/playerVisuals.js pour --surface-glow. Les deux règles CSS custom
   properties ci-dessous (--card, --green) sont redéfinies UNIQUEMENT dans
   ce sous-arbre : elles pilotent l'anneau de ProbabilityGauge.vue (qui les
   consomme via var(--card)/var(--green)) sans toucher au composant lui-même
   — sinon l'anneau se fondrait dans ce nouveau fond sombre. */
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
    linear-gradient(135deg, var(--green), var(--green2));
  --card: rgba(255, 255, 255, 0.16);
  --green: var(--lime);
  box-shadow: 0 22px 44px -18px var(--surface-shadow);
}
.circuit-badge {
  position: absolute;
  top: 14px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 2;
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
  margin: 0 auto 14px;
  box-shadow:
    inset 0 0 0 2px rgba(255, 255, 255, 0.22),
    0 8px 20px rgba(0, 0, 0, 0.3);
}
.avatar.is-favorite {
  box-shadow:
    inset 0 0 0 2px rgba(255, 255, 255, 0.3),
    0 0 0 3px var(--lime),
    0 8px 22px rgba(199, 255, 60, 0.32);
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
  }
  .circuit-badge {
    position: static;
    display: inline-flex;
    justify-self: center;
    width: auto;
    margin-bottom: 8px;
  }
}
</style>
