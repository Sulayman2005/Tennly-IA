<script setup>
import { computed, onMounted } from 'vue'
import { RouterView, RouterLink, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

// Le lien "Se connecter" du header emporte la page courante en ?redirect=
// (voir ConnexionView.vue) pour qu'un utilisateur qui cliquait sur un match
// précis y retourne après connexion, plutôt que d'atterrir systématiquement
// sur la liste générique des matchs.
const loginTarget = computed(() => ({
  name: 'connexion',
  query: route.name === 'connexion' ? {} : { redirect: route.fullPath },
}))

// auth.logout() existait déjà côté store (il vide les tokens en
// sessionStorage — voir client.js) mais rien dans l'interface ne l'appelait
// jamais : c'est pour ça que "se déconnecter" ne faisait rien. On appelle le
// store, puis on renvoie vers la liste des matchs — jamais vers une page qui
// exigerait justement d'être encore connecté (ex. /admin).
function handleLogout() {
  auth.logout()
  router.push('/matchs')
}

// Recharge l'utilisateur courant (et son statut d'abonnement, voir
// User::hasActiveSubscription() / GET /api/me) au chargement de l'app —
// sinon un rafraîchissement de page laisserait un abonné actif voir la popup
// paywall à tort, faute d'avoir jamais appelé fetchCurrentUser() ailleurs
// qu'après login()/register().
onMounted(() => {
  if (auth.isAuthenticated) {
    auth.fetchCurrentUser()
  }
})
</script>

<template>
  <header class="topbar">
    <RouterLink to="/" class="logo">
      <span class="mark">
        <svg viewBox="0 0 24 24" fill="none" style="width: 62%; height: 62%">
          <circle cx="12" cy="12" r="8.4" stroke="#fff" stroke-width="1.7" />
          <path d="M5.4 6C8.3 8.5 8.3 15.5 5.4 18" stroke="#fff" stroke-width="1.7" stroke-linecap="round" />
          <path d="M18.6 6C15.7 8.5 15.7 15.5 18.6 18" stroke="#fff" stroke-width="1.7" stroke-linecap="round" />
        </svg>
      </span>
      Tennly IA
    </RouterLink>
    <nav>
      <RouterLink to="/matchs">Analyse IA</RouterLink>
      <!-- Visible seulement pour un compte ROLE_ADMIN (section 3.7) — voir
           auth.isAdmin, dérivé de User::getRoles() exposé sur GET /api/me. -->
      <RouterLink v-if="auth.isAdmin" to="/admin">Back-office</RouterLink>
    </nav>
    <div v-if="auth.isAuthenticated" class="account">
      <span class="account-email">{{ auth.user?.email }}</span>
      <button type="button" class="cta-mini logout-btn" @click="handleLogout">Se déconnecter</button>
    </div>
    <RouterLink v-else :to="loginTarget" class="cta-mini">Se connecter</RouterLink>
  </header>

  <main>
    <RouterView />
  </main>
</template>

<style scoped>
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 22px 32px;
  border-bottom: 1px solid var(--line);
  position: sticky;
  top: 0;
  background: rgba(255, 255, 255, 0.86);
  backdrop-filter: blur(12px);
  z-index: 20;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
  font-size: 19px;
}

.logo .mark {
  width: 30px;
  height: 30px;
  border-radius: 9px;
  background: linear-gradient(135deg, var(--green), var(--lime));
  display: flex;
  align-items: center;
  justify-content: center;
}

nav {
  display: flex;
  gap: 34px;
  font-size: 14px;
  color: var(--grey);
}

.cta-mini {
  font-size: 14px;
  font-weight: 600;
}

.account {
  display: flex;
  align-items: center;
  gap: 14px;
}

.account-email {
  font-size: 13px;
  color: var(--grey);
}

.logout-btn {
  background: none;
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 7px 16px;
  cursor: pointer;
  color: var(--ink);
}

.logout-btn:hover {
  background: var(--card);
}

main {
  max-width: 1120px;
  margin: 0 auto;
  padding: 0 32px;
}
</style>