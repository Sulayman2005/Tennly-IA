<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterView, RouterLink, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

// Menu mobile (hamburger) : la nav + les actions du header étaient une
// simple <nav> à plat, sans jamais s'adapter en dessous d'un certain seuil
// de largeur — sur téléphone, elle débordait purement et simplement du
// header. On la cache en CSS sous 860px et on la remplace par ce panneau
// déroulant, qui reprend les mêmes liens/conditions (auth.isAdmin, etc.).
// Fermé automatiquement à chaque changement de route pour ne jamais rester
// ouvert par-dessus la page suivante.
const mobileMenuOpen = ref(false)
function toggleMobileMenu() {
  mobileMenuOpen.value = !mobileMenuOpen.value
}
function closeMobileMenu() {
  mobileMenuOpen.value = false
}
watch(
  () => route.fullPath,
  () => {
    mobileMenuOpen.value = false
  },
)

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
      Tennly
    </RouterLink>
    <nav class="nav-desktop">
      <RouterLink to="/matchs">Analyse</RouterLink>
      <!-- Comparateur retiré du menu le 09/09/2026 (décision produit : pas
           d'utilité claire identifiée, design pas à niveau avec le reste du
           site après sa refonte). La route /comparateur, son contrôleur et
           ses données restent tous intacts — seul le lien de navigation
           disparaît, décision facilement réversible si besoin. -->
      <RouterLink to="/fiabilite">Fiabilité</RouterLink>

    </nav>

    <div class="header-actions">
      <!-- Bouton "Dashboard" visible uniquement pour un compte ROLE_ADMIN
           (section 3.7) — voir auth.isAdmin, dérivé de User::getRoles()
           exposé sur GET /api/me. Avant, ce lien existait mais se fondait
           dans la nav en simple texte gris ("Back-office") : pas assez
           visible. Ici c'est un vrai bouton, toujours affiché en tête de
           page tant qu'on est connecté en admin. -->
      <RouterLink v-if="auth.isAdmin" to="/admin" class="dashboard-btn">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
          <rect x="3" y="3" width="8" height="8" rx="2" stroke="currentColor" stroke-width="1.8" />
          <rect x="13" y="3" width="8" height="8" rx="2" stroke="currentColor" stroke-width="1.8" />
          <rect x="3" y="13" width="8" height="8" rx="2" stroke="currentColor" stroke-width="1.8" />
          <rect x="13" y="13" width="8" height="8" rx="2" stroke="currentColor" stroke-width="1.8" />
        </svg>
        Dashboard
      </RouterLink>

      <div v-if="auth.isAuthenticated" class="account">
        <span class="account-email">{{ auth.user?.email }}</span>
        <button type="button" class="cta-mini logout-btn" @click="handleLogout">Se déconnecter</button>
      </div>
      <RouterLink v-else :to="loginTarget" class="cta-mini">Se connecter</RouterLink>
    </div>

    <!-- Bouton hamburger : caché en desktop, seul visible sous 860px (voir
         média-requête). -->
    <button
      type="button"
      class="menu-toggle"
      :class="{ open: mobileMenuOpen }"
      :aria-expanded="mobileMenuOpen"
      aria-label="Ouvrir le menu"
      @click="toggleMobileMenu"
    >
      <span></span><span></span><span></span>
    </button>

    <!-- Panneau mobile : même contenu que nav-desktop + header-actions,
         affiché uniquement quand le hamburger est ouvert (et seulement sous
         860px, où nav-desktop/header-actions sont masqués en CSS). -->
    <Transition name="mobile-nav">
      <nav v-if="mobileMenuOpen" class="mobile-nav">
        <RouterLink to="/matchs" @click="closeMobileMenu">Analyse</RouterLink>
        <!-- Comparateur retiré du menu (voir le même commentaire dans
             nav-desktop ci-dessus). -->
        <RouterLink to="/fiabilite" @click="closeMobileMenu">Fiabilité</RouterLink>
        <RouterLink v-if="auth.isAdmin" to="/admin" class="mobile-dashboard" @click="closeMobileMenu">
          Dashboard admin
        </RouterLink>

        <div class="mobile-divider"></div>

        <div v-if="auth.isAuthenticated" class="mobile-account">
          <span class="account-email">{{ auth.user?.email }}</span>
          <button type="button" class="logout-btn" @click="handleLogout">Se déconnecter</button>
        </div>
        <RouterLink v-else :to="loginTarget" class="cta-mini mobile-login" @click="closeMobileMenu">Se connecter</RouterLink>
      </nav>
    </Transition>
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

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.dashboard-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  background: var(--green);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  padding: 9px 16px;
  border-radius: 999px;
}

.dashboard-btn:hover {
  background: var(--green2);
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

/* -- Menu mobile (hamburger) -- */
.menu-toggle {
  display: none;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 5px;
  width: 38px;
  height: 38px;
  border: none;
  background: none;
  cursor: pointer;
  flex: none;
}
.menu-toggle span {
  display: block;
  width: 20px;
  height: 2px;
  border-radius: 2px;
  background: var(--ink);
  transition:
    transform 0.25s ease,
    opacity 0.2s ease;
}
.menu-toggle.open span:nth-child(1) {
  transform: translateY(7px) rotate(45deg);
}
.menu-toggle.open span:nth-child(2) {
  opacity: 0;
}
.menu-toggle.open span:nth-child(3) {
  transform: translateY(-7px) rotate(-45deg);
}

.mobile-nav {
  display: none;
}

@media (max-width: 860px) {
  .topbar {
    padding: 16px 20px;
  }
  .nav-desktop,
  .header-actions {
    display: none;
  }
  .menu-toggle {
    display: flex;
  }
  .mobile-nav {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
    background: #fff;
    border-bottom: 1px solid var(--line);
    box-shadow: 0 16px 30px rgba(0, 0, 0, 0.08);
    padding: 10px 20px 18px;
  }
  .mobile-nav a {
    padding: 13px 4px;
    font-size: 15px;
    color: var(--ink);
    border-bottom: 1px solid var(--line);
  }
  .mobile-nav .mobile-dashboard {
    color: var(--green);
    font-weight: 700;
  }
  .mobile-divider {
    display: none;
  }
  .mobile-account {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 14px 4px 4px;
  }
  .mobile-account .account-email {
    font-size: 13px;
    color: var(--grey);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  /* Sélecteur ".mobile-nav a" (class + balise) ci-dessus est plus spécifique
     qu'un simple ".mobile-login" : son "color: var(--ink)" gagnait toujours
     sur le "color: #fff" voulu ici, et --ink vaut la même couleur presque
     noire que le fond --btn du bouton -> texte invisible sur fond sombre.
     On répète "a.mobile-login" pour égaler/dépasser cette spécificité. */
  .mobile-nav a.mobile-login {
    display: block;
    text-align: center;
    margin-top: 10px;
    padding: 12px;
    border-radius: 999px;
    background: var(--btn);
    color: #fff;
  }
  main {
    padding: 0 20px;
  }
}

@media (max-width: 480px) {
  .logo {
    font-size: 17px;
  }
  main {
    padding: 0 16px;
  }
}

.mobile-nav-enter-active,
.mobile-nav-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}
.mobile-nav-enter-from,
.mobile-nav-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>