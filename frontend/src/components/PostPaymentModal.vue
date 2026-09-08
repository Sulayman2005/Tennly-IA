<script setup>
import { ref, watch } from 'vue'
import { api, ApiError } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const props = defineProps({
  open: { type: Boolean, default: false },
  sessionId: { type: String, default: '' },
})
const emit = defineEmits(['linked'])
const auth = useAuthStore()

/**
 * Panneau affiché au retour de Stripe Checkout lorsque le paiement a été
 * démarré AVANT toute connexion (décision produit du 03/09/2026, voir
 * choosePlan() dans PaywallModal.vue et CheckoutSessionController côté
 * backend, qui accepte désormais un paiement anonyme). Le paiement est déjà
 * confirmé à ce stade — il ne reste qu'à créer le compte (ou se connecter,
 * si l'email a déjà un compte) puis relier ce paiement précis via
 * CheckoutSessionLinkController.
 */
const status = ref('loading') // loading | need-login | need-register | already-linked | error
const email = ref('')
const password = ref('')
const firstName = ref('')
const lastName = ref('')
const errorMessage = ref('')
const submitting = ref(false)

async function checkStatus() {
  errorMessage.value = ''
  password.value = ''
  if (!props.sessionId) {
    status.value = 'error'
    errorMessage.value = 'Paiement introuvable.'
    return
  }
  status.value = 'loading'
  try {
    const info = await api.getCheckoutSessionStatus(props.sessionId)
    if (!info.paid) {
      status.value = 'error'
      errorMessage.value = "Ce paiement n'a pas encore été confirmé par Stripe."
      return
    }
    email.value = info.email || ''
    if (info.alreadyLinked) {
      status.value = 'already-linked'
    } else {
      // Demande explicite du 03/09/2026 : on affiche toujours "créer un
      // compte" en premier, même si l'email a déjà un compte — la personne
      // qui vient de payer est très majoritairement un nouveau client. Le
      // lien "Déjà un compte ? Se connecter" (switchToLogin) reste
      // disponible pour l'exception.
      status.value = 'need-register'
    }
  } catch {
    status.value = 'error'
    errorMessage.value = 'Impossible de vérifier ce paiement pour le moment.'
  }
}

// `open` peut redevenir true après un premier passage (retour arrière puis
// re-avant sur la même page) : on revérifie à chaque ouverture plutôt qu'une
// seule fois au montage du composant.
watch(() => props.open, (isOpen) => {
  if (isOpen) checkStatus()
}, { immediate: true })

/**
 * checkStatus() ne fait que suggérer un point de départ (need-login si
 * l'email détecté par Stripe a déjà un compte) : demande explicite du
 * 03/09/2026, l'utilisateur doit pouvoir basculer librement vers "créer un
 * compte" même si un compte existe déjà pour cet email — par exemple s'il
 * veut plutôt en créer un nouveau. Le champ email reste modifiable dans les
 * deux cas.
 */
function switchToRegister() {
  errorMessage.value = ''
  password.value = ''
  status.value = 'need-register'
}
function switchToLogin() {
  errorMessage.value = ''
  password.value = ''
  status.value = 'need-login'
}

/**
 * Relie le paiement une fois connecté/inscrit. Erreur la plus fréquente ici :
 * l'email du compte (celui saisi dans ce formulaire) ne correspond pas à
 * l'email réellement utilisé sur la page de paiement Stripe — le message
 * renvoyé par CheckoutSessionLinkController l'explique déjà clairement, donc
 * on l'affiche tel quel plutôt qu'un message générique.
 */
async function linkAfterAuth() {
  try {
    await api.linkCheckoutSession(props.sessionId)
    emit('linked')
  } catch (e) {
    errorMessage.value = e instanceof ApiError && e.problem?.detail
      ? e.problem.detail
      : "Le compte est bien créé, mais impossible de relier ce paiement pour le moment."
    submitting.value = false
  }
}

async function submitLogin() {
  errorMessage.value = ''
  submitting.value = true
  try {
    await auth.login(email.value, password.value)
  } catch (e) {
    errorMessage.value = e instanceof ApiError && e.status === 401
      ? 'Email ou mot de passe incorrect.'
      : "Impossible de se connecter pour le moment."
    submitting.value = false
    return
  }
  await linkAfterAuth()
}

async function submitRegister() {
  errorMessage.value = ''
  if (!firstName.value.trim() || !lastName.value.trim() || password.value.length < 8) {
    errorMessage.value = "Renseigne ton prénom, ton nom et un mot de passe d'au moins 8 caractères."
    return
  }
  submitting.value = true
  try {
    await auth.register({
      email: email.value,
      password: password.value,
      firstName: firstName.value,
      lastName: lastName.value,
    })
  } catch (e) {
    errorMessage.value = e instanceof ApiError && e.problem?.detail
      ? e.problem.detail
      : 'Impossible de créer le compte pour le moment.'
    submitting.value = false
    return
  }
  await linkAfterAuth()
}
</script>

<template>
  <div v-if="open" class="overlay">
    <div class="modal">
      <div class="modal-hero">
        <span class="lock-tag">✅ Paiement confirmé</span>
        <h3>Encore une étape</h3>
        <p v-if="status === 'need-register'">Crée ton mot de passe pour accéder à ton analyse.</p>
        <p v-else-if="status === 'need-login'">Connecte-toi pour débloquer ton analyse.</p>
        <p v-else>Ton accès à l'analyse complète.</p>
      </div>

      <div class="modal-body">
        <p v-if="errorMessage" class="error">{{ errorMessage }}</p>

        <p v-if="status === 'loading'" class="state-msg">Vérification du paiement…</p>

        <p v-else-if="status === 'already-linked'" class="state-msg">
          Ton abonnement est déjà actif. Connecte-toi pour accéder à ton analyse.
        </p>

        <form v-else-if="status === 'need-login'" class="fields" autocomplete="off" @submit.prevent="submitLogin">
          <label class="field">
            <span>Email</span>
            <input v-model="email" type="email" name="tennly-checkout-email" autocomplete="off" required />
          </label>
          <label class="field">
            <span>Mot de passe</span>
            <input
              v-model="password"
              type="password"
              name="tennly-checkout-password"
              autocomplete="off"
              required
              autofocus
              placeholder="Ton mot de passe"
            />
          </label>
          <button class="btn-primary" type="submit" :disabled="submitting">
            {{ submitting ? 'Connexion…' : 'Se connecter et débloquer' }}
          </button>
          <a class="switch" @click="switchToRegister">Pas encore de compte avec cet email ? Créer un compte</a>
        </form>

        <form v-else-if="status === 'need-register'" class="fields" autocomplete="off" @submit.prevent="submitRegister">
          <label class="field">
            <span>Email</span>
            <input v-model="email" type="email" name="tennly-checkout-email" autocomplete="off" required />
          </label>
          <label class="field">
            <span>Prénom</span>
            <input v-model="firstName" type="text" name="tennly-checkout-firstname" autocomplete="off" required autofocus />
          </label>
          <label class="field">
            <span>Nom</span>
            <input v-model="lastName" type="text" name="tennly-checkout-lastname" autocomplete="off" required />
          </label>
          <label class="field">
            <span>Mot de passe</span>
            <input
              v-model="password"
              type="password"
              name="tennly-checkout-new-password"
              autocomplete="off"
              required
              minlength="8"
              placeholder="8 caractères minimum"
            />
          </label>
          <button class="btn-primary" type="submit" :disabled="submitting">
            {{ submitting ? 'Création…' : 'Créer mon compte et débloquer' }}
          </button>
          <a class="switch" @click="switchToLogin">Déjà un compte ? Se connecter</a>
        </form>
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

.modal {
  background: #fff;
  border-radius: 24px;
  max-width: 420px;
  width: 100%;
  max-height: calc(100vh - 40px);
  overflow-y: auto;
  position: relative;
  box-sizing: border-box;
  margin: auto;
  box-shadow: 0 32px 64px -20px rgba(2, 14, 14, 0.45);
}

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

.state-msg {
  color: var(--grey);
  font-size: 14px;
  margin: 0;
}

.fields {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--grey);
}
.field input {
  font: inherit;
  font-weight: 500;
  color: var(--ink);
  padding: 11px 14px;
  border-radius: 10px;
  border: 1px solid var(--line);
  background: #fff;
}
.field input:disabled {
  background: var(--card);
  color: var(--grey);
}
.field input:focus {
  outline: none;
  border-color: var(--green);
}

.fields .btn-primary {
  width: 100%;
  margin-top: 4px;
  text-align: center;
}
.fields .btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.error {
  background: #fdecea;
  color: #b3261e;
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 13px;
  margin: 0 0 16px;
}

.switch {
  display: block;
  text-align: center;
  margin-top: 2px;
  font-size: 12.5px;
  color: var(--grey);
  text-decoration: underline;
  cursor: pointer;
}
.switch:hover {
  color: var(--ink);
}
</style>
