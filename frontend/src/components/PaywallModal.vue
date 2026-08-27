<script setup>
import { ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { api } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

defineProps({
  open: { type: Boolean, default: false },
})
const emit = defineEmits(['close'])
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const plans = [
  { code: 'classique', name: 'Classique', price: '9,99 €', per: 'par mois' },
  { code: 'vip', name: 'VIP', price: '49,99 €', per: 'tous les 3 mois', reco: true },
  { code: 'vip-annuel', name: 'VIP annuel', price: '199,99 €', per: 'par an' },
]

const startingCheckout = ref(null)
const errorMessage = ref('')

// Case à cocher obligatoire (CGV article 4) : l'abonnement donne un accès
// immédiat, donc la loi (art. L221-28 13° du Code de la consommation)
// exige une renonciation EXPRESSE au droit de rétractation de 14 jours pour
// pouvoir l'écarter légalement — pas de case pré-cochée, jamais implicite.
const withdrawalWaiverAccepted = ref(false)

/**
 * Le paiement n'est plus déclenché à l'inscription (voir
 * UserRegistrationProcessor côté backend) : cette popup n'apparaît que
 * lorsque l'utilisateur clique sur "Débloquer l'analyse complète" d'un match
 * précis (voir MatchDetailView.vue), et le paiement ne démarre qu'ici,
 * jamais avant.
 *
 * - Déjà connecté : on démarre tout de suite une session Stripe Checkout
 *   pour la formule choisie (CheckoutSessionController), avec le chemin du
 *   match courant comme point de retour après paiement.
 * - Pas encore connecté : direction l'écran de connexion (qui ne s'occupe
 *   plus que de créer le compte / se connecter, jamais de formule) avec le
 *   match d'origine mémorisé en ?redirect= — une fois connecté, l'utilisateur
 *   retombe sur ce même match et peut y rouvrir cette popup pour payer.
 */
async function choosePlan(code) {
  if (!auth.isAuthenticated) {
    router.push({ name: 'connexion', query: { redirect: route.fullPath } })
    return
  }

  if (!withdrawalWaiverAccepted.value) {
    errorMessage.value = 'Coche la case ci-dessous pour continuer — elle est obligatoire pour un accès immédiat.'
    return
  }

  errorMessage.value = ''
  startingCheckout.value = code
  try {
    const { checkoutUrl } = await api.createCheckoutSession(code, route.fullPath, withdrawalWaiverAccepted.value)
    window.location.href = checkoutUrl
  } catch {
    errorMessage.value = 'Impossible de démarrer le paiement pour le moment.'
    startingCheckout.value = null
  }
}
</script>

<template>
  <div v-if="open" class="overlay" @click.self="emit('close')">
    <div class="modal">
      <div class="close" @click="emit('close')">✕</div>
      <span class="lock-tag">🔒 Contenu réservé aux abonnés</span>
      <h3>Débloquez l'analyse complète de ce match</h3>
      <p>Probabilités détaillées, comparatif des facteurs et analyse IA complète — choisissez votre formule pour continuer.</p>
      <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
      <div class="plans">
        <div v-for="plan in plans" :key="plan.code" class="plan" :class="{ reco: plan.reco }">
          <span v-if="plan.reco" class="badge">LE PLUS CHOISI</span>
          <div class="p">{{ plan.name }}</div>
          <div class="price">{{ plan.price }}</div>
          <div class="per">{{ plan.per }}</div>
          <button
            :disabled="Boolean(startingCheckout) || !withdrawalWaiverAccepted"
            @click="choosePlan(plan.code)"
          >
            {{ startingCheckout === plan.code ? 'Redirection…' : 'Choisir' }}
          </button>
        </div>
      </div>

      <label class="waiver">
        <input v-model="withdrawalWaiverAccepted" type="checkbox" />
        Je demande l'exécution immédiate de mon abonnement et je renonce en conséquence à mon droit de rétractation
        de 14 jours (<RouterLink to="/cgv">voir les CGV</RouterLink>).
      </label>

      <div class="foot">Résiliable à tout moment en un clic. Aucun engagement caché.</div>
    </div>
  </div>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
}
.modal {
  background: #fff;
  border-radius: 24px;
  padding: 32px;
  max-width: 520px;
  width: 100%;
  position: relative;
}
.close {
  position: absolute;
  top: 16px;
  right: 16px;
  cursor: pointer;
  color: var(--grey);
}
.lock-tag {
  display: inline-block;
  background: #fff3cd;
  color: #8a6100;
  font-size: 11px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 999px;
  margin-bottom: 12px;
}
.plans {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin: 20px 0;
}
.plan {
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 16px 12px;
  text-align: center;
  position: relative;
}
.plan.reco {
  border-color: var(--green);
  box-shadow: 0 0 0 2px rgba(15, 61, 62, 0.12);
}
.badge {
  position: absolute;
  top: -10px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--green);
  color: #fff;
  font-size: 9px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 999px;
}
.price {
  font-size: 20px;
  font-weight: 700;
  margin: 6px 0 2px;
}
.per {
  font-size: 11px;
  color: var(--grey);
  margin-bottom: 12px;
}
.plan button {
  width: 100%;
  background: var(--ink);
  color: #fff;
  border: none;
  border-radius: 10px;
  padding: 10px;
  font-weight: 700;
  cursor: pointer;
}
.plan.reco button {
  background: var(--green);
}
.waiver {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 11.5px;
  color: var(--grey);
  line-height: 1.5;
  margin-bottom: 14px;
}

.waiver input {
  margin-top: 2px;
  flex: none;
}

.waiver :deep(a) {
  color: var(--ink);
  text-decoration: underline;
  font-weight: 600;
}

.foot {
  text-align: center;
  font-size: 12px;
  color: var(--grey);
}
.error {
  background: #fdecea;
  color: #b3261e;
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 13px;
  margin-top: -8px;
}
.plan button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
