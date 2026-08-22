<script setup>
import { useRouter } from 'vue-router'

defineProps({
  open: { type: Boolean, default: false },
})
const emit = defineEmits(['close'])
const router = useRouter()

const plans = [
  { code: 'classique', name: 'Classique', price: '9,99 €', per: 'par mois' },
  { code: 'vip', name: 'VIP', price: '49,99 €', per: 'tous les 3 mois', reco: true },
  { code: 'vip-annuel', name: 'VIP annuel', price: '199,99 €', per: 'par an' },
]

/**
 * Cahier des charges section 3.2.1 / 3.9 : le clic sur une formule redirige
 * vers l'écran de connexion en mode inscription — jamais l'inverse. C'est le
 * SEUL chemin qui mène à la création d'un compte.
 */
function choosePlan(code) {
  router.push({ name: 'connexion', query: { plan: code } })
}
</script>

<template>
  <div v-if="open" class="overlay" @click.self="emit('close')">
    <div class="modal">
      <div class="close" @click="emit('close')">✕</div>
      <span class="lock-tag">🔒 Contenu réservé aux abonnés</span>
      <h3>Débloquez l'analyse complète de ce match</h3>
      <p>Probabilités détaillées, comparatif des facteurs et explication du pronostic — choisissez votre formule pour continuer.</p>
      <div class="plans">
        <div v-for="plan in plans" :key="plan.code" class="plan" :class="{ reco: plan.reco }">
          <span v-if="plan.reco" class="badge">LE PLUS CHOISI</span>
          <div class="p">{{ plan.name }}</div>
          <div class="price">{{ plan.price }}</div>
          <div class="per">{{ plan.per }}</div>
          <button @click="choosePlan(plan.code)">Choisir</button>
        </div>
      </div>
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
.foot {
  text-align: center;
  font-size: 12px;
  color: var(--grey);
}
</style>
