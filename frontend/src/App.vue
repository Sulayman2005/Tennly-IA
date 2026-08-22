<script setup>
import { onMounted } from 'vue'
import { RouterView, RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

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
      <RouterLink to="/matchs">Pronostics</RouterLink>
    </nav>
    <RouterLink to="/connexion" class="cta-mini">Se connecter</RouterLink>
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

main {
  max-width: 1120px;
  margin: 0 auto;
  padding: 0 32px;
}
</style>
