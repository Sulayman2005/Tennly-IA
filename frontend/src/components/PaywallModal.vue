<script setup>
import { ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { api } from '@/api/client'

defineProps({
  open: { type: Boolean, default: false },
})
const emit = defineEmits(['close'])
const route = useRoute()

const plans = [
  { code: 'classique', name: 'Classique', price: '9,99 €', per: 'par mois' },
  { code: 'premium', name: 'Premium', price: '49,99 €', per: 'tous les 3 mois', reco: true },
  { code: 'premium-annuel', name: 'Premium annuel', price: '99,99 €', per: 'par an' },
]

const startingCheckout = ref(null)
const errorMessage = ref('')

// Case à cocher obligatoire (CGV article 4) : l'abonnement donne un accès
// immédiat, donc la loi (art. L221-28 13° du Code de la consommation)
// exige une renonciation EXPRESSE au droit de rétractation de 14 jours pour
// pouvoir l'écarter légalement — pas de case pré-cochée, jamais implicite.
const withdrawalWaiverAccepted = ref(false)

/**
 * Décision produit du 03/09/2026 : le paiement démarre tout de suite au clic
 * sur une formule, QUE l'utilisateur soit déjà connecté ou non — fini le
 * détour par l'écran de connexion avant de payer (voir
 * CheckoutSessionController côté backend, qui accepte désormais un paiement
 * anonyme). Le chemin du match courant sert de point de retour Stripe.
 *
 * - Déjà connecté : rien ne change, l'abonnement s'active via le webhook
 *   Stripe dès le retour sur le match (voir MatchDetailView.vue).
 * - Pas encore connecté : Stripe Checkout collecte lui-même l'email du
 *   payeur ; au retour, MatchDetailView.vue ouvre PostPaymentModal.vue pour
 *   créer le compte (ou se connecter, si l'email a déjà un compte) et relier
 *   ce paiement précis — jamais avant que le paiement soit confirmé.
 */
async function choosePlan(code) {
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
      <button class="close" @click="emit('close')" aria-label="Fermer">✕</button>

      <!-- Bandeau "hero" sombre (même dégradé --green/--green2 + halo que
           MatchCard.vue / MatchDetailView.vue) : la popup qui invite à
           payer mérite le même effet "wow" que le reste de la page match
           plutôt que le bloc de texte plat qu'elle avait avant, tandis que
           le corps (formules, case CGV) reste sur fond clair pour que les
           mentions légales restent parfaitement lisibles. -->
      <div class="modal-hero">
        <span class="lock-tag">🔒 Contenu réservé aux abonnés</span>
        <h3>Débloquez l'analyse complète de ce match</h3>
        <p>Probabilités détaillées, comparatif des facteurs et analyse IA complète — choisissez votre formule pour continuer.</p>
      </div>

      <div class="modal-body">
        <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
        <div class="plans">
          <div v-for="plan in plans" :key="plan.code" class="plan" :class="{ reco: plan.reco }">
            <span v-if="plan.reco" class="badge">LE PLUS CHOISI</span>
            <div class="plan-info">
              <div class="p">{{ plan.name }}</div>
              <div class="price">{{ plan.price }}</div>
              <div class="per">{{ plan.per }}</div>
            </div>
            <button
              :disabled="Boolean(startingCheckout)"
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
  </div>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(4, 12, 12, 0.56);
  backdrop-filter: blur(3px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  overflow-y: auto;
  z-index: 50;
  box-sizing: border-box;
}

@keyframes modalIn {
  from {
    opacity: 0;
    transform: translateY(14px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
.modal {
  background: #fff;
  border-radius: 24px;
  max-width: 520px;
  width: 100%;
  max-height: calc(100vh - 40px);
  overflow-y: auto;
  overflow-x: hidden;
  position: relative;
  box-sizing: border-box;
  margin: auto;
  box-shadow: 0 32px 64px -20px rgba(2, 14, 14, 0.45);
  animation: modalIn 0.32s cubic-bezier(0.16, 1, 0.3, 1) both;
}
@media (prefers-reduced-motion: reduce) {
  .modal {
    animation: none;
  }
}

.close {
  position: absolute;
  top: 14px;
  right: 14px;
  z-index: 2;
  width: 30px;
  height: 30px;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.16);
  color: #fff;
  font-size: 13px;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s ease;
}
.close:hover {
  background: rgba(255, 255, 255, 0.28);
}

/* Même traitement visuel "wow" que MatchCard.vue / .face-off
   (MatchDetailView.vue) : dégradé teal → vert profond avec un halo lime en
   irradiation depuis le haut, plutôt que le bandeau de texte plat que cette
   popup avait avant. */
.modal-hero {
  position: relative;
  overflow: hidden;
  isolation: isolate;
  padding: 30px 32px 26px;
  color: #fff;
  background:
    radial-gradient(130% 160% at 50% -20%, rgba(199, 255, 60, 0.28) 0%, transparent 60%),
    linear-gradient(135deg, var(--green), var(--green2));
}
.modal-hero h3 {
  margin: 0 0 8px;
  font-size: 21px;
  font-weight: 800;
  letter-spacing: -0.01em;
}
.modal-hero p {
  margin: 0;
  font-size: 13.5px;
  line-height: 1.5;
  color: rgba(255, 255, 255, 0.82);
}
.lock-tag {
  display: inline-flex;
  align-items: center;
  background: rgba(255, 255, 255, 0.16);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  padding: 5px 12px;
  border-radius: 999px;
  margin-bottom: 14px;
}

.modal-body {
  padding: 28px 32px 32px;
}

.plans {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin: 4px 0 22px;
}
.plan {
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 20px 14px 16px;
  text-align: center;
  position: relative;
  background: #fff;
  transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.25s ease, border-color 0.25s ease;
}
.plan:hover {
  transform: translateY(-3px);
  box-shadow: 0 14px 28px -16px rgba(15, 61, 62, 0.28);
}
.plan.reco {
  border-color: var(--lime);
  background: linear-gradient(180deg, rgba(199, 255, 60, 0.08), transparent 55%);
  box-shadow: 0 0 0 1px var(--lime), 0 16px 30px -16px rgba(15, 61, 62, 0.32);
}
@media (prefers-reduced-motion: reduce) {
  .plan {
    transition: none;
  }
}
.badge {
  position: absolute;
  top: -11px;
  left: 50%;
  transform: translateX(-50%);
  background: linear-gradient(135deg, var(--green), var(--lime));
  color: #052625;
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.02em;
  padding: 4px 10px;
  border-radius: 999px;
  box-shadow: 0 4px 10px -4px rgba(15, 61, 62, 0.4);
}
.p {
  font-size: 13px;
  font-weight: 700;
  color: var(--ink);
}
.price {
  font-size: 23px;
  font-weight: 800;
  letter-spacing: -0.01em;
  margin: 8px 0 2px;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
}
.per {
  font-size: 11px;
  color: var(--grey);
  margin-bottom: 14px;
}
.plan button {
  width: 100%;
  background: var(--ink);
  color: #fff;
  border: none;
  border-radius: 10px;
  padding: 10px;
  font-weight: 700;
  font-size: 13px;
  cursor: pointer;
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.plan button:hover:not(:disabled) {
  transform: translateY(-1px);
  opacity: 0.92;
}
.plan.reco button {
  background: linear-gradient(135deg, var(--green), var(--lime) 130%);
  color: #052625;
}

.waiver {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 11.5px;
  color: var(--grey);
  line-height: 1.5;
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(15, 61, 62, 0.045);
  border: 1px solid var(--line);
  margin-bottom: 16px;
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
  margin-bottom: 16px;
}
.plan button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

@media (max-width: 560px) {
  .modal-hero {
    padding: 26px 20px 22px;
  }
  .modal-body {
    padding: 22px 20px 24px;
  }
  .plans {
    grid-template-columns: 1fr;
    gap: 10px;
    margin: 4px 0 18px;
  }
  .plan {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    padding: 14px 16px;
    text-align: left;
  }
  .plan:hover {
    transform: none;
  }
  .plan.reco {
    order: -1;
  }
  .plan-info {
    display: flex;
    align-items: baseline;
    gap: 8px;
    flex-wrap: wrap;
  }
  .plan-info .price {
    margin: 0;
  }
  .plan-info .per {
    margin: 0;
  }
  .badge {
    position: absolute;
    top: -9px;
    left: 16px;
    transform: none;
  }
  .plan button {
    width: auto;
    flex: none;
    padding: 10px 18px;
  }
}
</style>
