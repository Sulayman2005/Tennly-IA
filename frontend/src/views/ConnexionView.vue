<script setup>
import { ref, computed, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const activeTab = ref('login')

const loginForm = reactive({ email: '', password: '' })
const signupForm = reactive({ firstName: '', lastName: '', email: '', password: '', acceptTerms: false })
const submitting = ref(false)
const errorMessage = ref('')

// Redirection après connexion/inscription : si l'utilisateur arrivait d'une
// page précise (ex. le lien "Déjà abonné ? Se connecter" ou "Débloquer
// l'analyse complète" depuis une fiche match — voir PaywallModal.vue et
// MatchDetailView.vue — ou "Se connecter" cliqué depuis une page donnée, voir
// App.vue), on le renvoie sur cette même page plutôt que sur la liste
// générique. Le choix d'une formule et le paiement se font entièrement sur la
// fiche du match une fois connecté (voir PaywallModal.vue) — cet écran ne
// s'occupe plus jamais de formule ni de paiement. On n'accepte qu'un chemin
// relatif commençant par "/" (et jamais "//...", qui serait interprété comme
// une URL externe par le navigateur) pour ne jamais rediriger vers un site
// tiers à partir d'un ?redirect= qu'un utilisateur pourrait bricoler dans l'URL.
const safeRedirect = computed(() => {
  const target = route.query.redirect
  return typeof target === 'string' && target.startsWith('/') && !target.startsWith('//') ? target : '/matchs'
})

async function submitLogin() {
  submitting.value = true
  errorMessage.value = ''
  try {
    await auth.login(loginForm.email, loginForm.password)
    router.push(safeRedirect.value)
  } catch {
    errorMessage.value = 'Email ou mot de passe incorrect.'
  } finally {
    submitting.value = false
  }
}

async function submitSignup() {
  if (!signupForm.acceptTerms) {
    errorMessage.value = 'Merci d’accepter les CGU et la politique de confidentialité.'
    return
  }
  submitting.value = true
  errorMessage.value = ''
  try {
    // Créer un compte n'entraîne jamais de paiement (voir
    // UserRegistrationProcessor côté backend) : le paiement ne se déclenche
    // que plus tard, depuis la fiche d'un match, quand l'utilisateur veut
    // réellement voir l'analyse complète.
    await auth.register({
      email: signupForm.email,
      password: signupForm.password,
      firstName: signupForm.firstName,
      lastName: signupForm.lastName,
    })
    router.push(safeRedirect.value)
  } catch {
    errorMessage.value = "Impossible de créer le compte pour le moment."
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="auth-wrap">
    <div class="auth-form-panel">
      <div class="auth-card">
        <div class="tabswitch">
          <button :class="{ active: activeTab === 'login' }" @click="activeTab = 'login'">Connexion</button>
          <button :class="{ active: activeTab === 'signup' }" @click="activeTab = 'signup'">Créer un compte</button>
        </div>

        <p v-if="errorMessage" class="error">{{ errorMessage }}</p>

        <form v-if="activeTab === 'login'" @submit.prevent="submitLogin">
          <h2>Content de te revoir</h2>
          <p class="lead">Connecte-toi pour retrouver tes analyses et ton abonnement.</p>
          <label>Adresse email<input v-model="loginForm.email" type="email" required /></label>
          <label>Mot de passe<input v-model="loginForm.password" type="password" required /></label>
          <button class="btn-primary" type="submit" :disabled="submitting">Se connecter</button>
        </form>

        <form v-else @submit.prevent="submitSignup">
          <h2>Crée ton compte</h2>
          <p class="lead">Crée ton compte gratuitement — tu ne paieras que si tu veux débloquer l'analyse complète d'un match.</p>
          <label>Prénom<input v-model="signupForm.firstName" type="text" required /></label>
          <label>Nom<input v-model="signupForm.lastName" type="text" required /></label>
          <label>Adresse email<input v-model="signupForm.email" type="email" required /></label>
          <label>Mot de passe<input v-model="signupForm.password" type="password" minlength="8" required /></label>
          <label class="checkline"><input v-model="signupForm.acceptTerms" type="checkbox" /> J'accepte les CGU et la politique de confidentialité</label>
          <button class="btn-primary" type="submit" :disabled="submitting">Créer mon compte</button>
          <p class="fine">
            En créant un compte, tu confirmes avoir pris connaissance de l'avertissement jeu responsable : nos
            analyses sont un outil d'aide à la décision, elles ne garantissent aucun gain.
          </p>
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>
.auth-wrap {
  display: flex;
  justify-content: center;
  padding: 48px 0;
}
.auth-card {
  width: 100%;
  max-width: 420px;
}
.tabswitch {
  display: flex;
  background: var(--card);
  border-radius: 999px;
  padding: 4px;
  margin-bottom: 28px;
}
.tabswitch button {
  flex: 1;
  border: none;
  background: transparent;
  padding: 11px 0;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 600;
  color: var(--grey);
  cursor: pointer;
}
.tabswitch button.active {
  background: var(--ink);
  color: #fff;
}
form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
form h2 {
  margin: 0;
  font-size: 22px;
}
.lead {
  margin: -8px 0 0;
  font-size: 13px;
  color: var(--grey);
}
label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
}
label input[type='text'],
label input[type='email'],
label input[type='password'] {
  border: 1px solid var(--line);
  background: var(--card);
  border-radius: 12px;
  padding: 12px 14px;
  font-size: 14px;
  font-weight: 400;
}
.checkline {
  flex-direction: row;
  align-items: center;
  font-weight: 400;
}
.fine {
  font-size: 11px;
  color: var(--grey);
  line-height: 1.5;
}
.error {
  background: #fdecea;
  color: #b3261e;
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 13px;
}
</style>

