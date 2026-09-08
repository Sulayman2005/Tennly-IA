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
// App.vue), on le renvoie sur cette même page plutôt que sur une page par
// défaut. On n'accepte qu'un chemin relatif commençant par "/" (et jamais
// "//...", qui serait interprété comme une URL externe par le navigateur)
// pour ne jamais rediriger vers un site tiers à partir d'un ?redirect= qu'un
// utilisateur pourrait bricoler dans l'URL.
const explicitRedirect = computed(() => {
  const target = route.query.redirect
  return typeof target === 'string' && target.startsWith('/') && !target.startsWith('//') ? target : null
})

// Sans page précise à retrouver (ex. arrivée directe sur /connexion, pas de
// clic sur un match), un compte ROLE_ADMIN atterrit sur le tableau de bord
// back-office plutôt que sur la liste publique des matchs — c'est là que se
// trouvent toutes les stats de l'app (voir AdminDashboardView.vue) ; un
// utilisateur normal continue d'atterrir sur /matchs. auth.login()/register()
// attendent déjà fetchCurrentUser() en interne, donc auth.isAdmin reflète le
// bon compte au moment où cette fonction est appelée, juste après connexion.
function postLoginTarget() {
  return explicitRedirect.value ?? (auth.isAdmin ? '/admin' : '/matchs')
}

async function submitLogin() {
  submitting.value = true
  errorMessage.value = ''
  try {
    await auth.login(loginForm.email, loginForm.password)
    router.push(postLoginTarget())
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
    router.push(postLoginTarget())
  } catch {
    errorMessage.value = "Impossible de créer le compte pour le moment."
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="auth-wrap">
    <!--
      Panneau de marque, dans le même esprit que le hero de HomeView.vue
      (eyebrow + accroche + palette --green/--lime) plutôt que le fond de
      carte neutre qu'avait cette page jusqu'ici — voir README.md, section
      "reste à faire" du 28/08/2026 : cette page gardait l'ancien style
      pendant que la page d'accueil et le back-office avaient déjà été
      alignés sur l'identité Apple/"terre battue" du projet. Purement
      visuel, aucune logique ici.
    -->
    <div class="auth-brand-panel">
      <div class="eyebrow"><i></i>TENNIS · TON COMPTE</div>
      <h1>Retrouve tes <span class="accent">analyses</span><br />où que tu sois.</h1>
      <p class="brand-lead">
        Historique de performance 100 % public, aucune donnée inventée — crée
        un compte gratuit en une minute.
      </p>
      <ul class="brand-points">
        <li>Analyse calibrée sur données réelles ATP + WTA</li>
        <li>Le compte est gratuit, sans engagement</li>
        <li>Paiement à la demande, uniquement pour débloquer l'analyse complète d'un match</li>
      </ul>
    </div>

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
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  align-items: stretch;
  gap: 40px;
  padding: 48px 0 60px;
}

.auth-brand-panel {
  border-radius: var(--radius-card);
  padding: 44px 40px;
  background: linear-gradient(155deg, var(--green) 0%, var(--green2) 100%);
  color: #fff;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.auth-brand-panel .eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: rgba(255, 255, 255, 0.75);
  margin-bottom: 18px;
}

.auth-brand-panel .eyebrow i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--lime);
  box-shadow: 0 0 0 3px rgba(199, 255, 60, 0.25);
}

.auth-brand-panel h1 {
  font-size: 32px;
  line-height: 1.2;
  margin: 0 0 16px;
}

.auth-brand-panel h1 .accent {
  color: var(--lime);
}

.brand-lead {
  font-size: 15px;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.8);
  margin: 0 0 28px;
  max-width: 38ch;
}

.brand-points {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.brand-points li {
  position: relative;
  padding-left: 20px;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.9);
}

.brand-points li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 7px;
  width: 8px;
  height: 8px;
  border-radius: 2px;
  background: var(--lime);
}

.auth-form-panel {
  display: flex;
  align-items: center;
  justify-content: center;
}

@media (max-width: 780px) {
  .auth-wrap {
    grid-template-columns: 1fr;
    padding: 24px 0 48px;
  }

  .auth-brand-panel {
    padding: 32px 28px;
  }

  .auth-brand-panel h1 {
    font-size: 26px;
  }
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