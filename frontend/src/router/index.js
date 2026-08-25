import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'
import MatchesView from '@/views/MatchesView.vue'
import MatchDetailView from '@/views/MatchDetailView.vue'
import ConnexionView from '@/views/ConnexionView.vue'
import AdminDashboardView from '@/views/admin/AdminDashboardView.vue'
import AdminMatchesView from '@/views/admin/AdminMatchesView.vue'
import AdminMatchAnalysisView from '@/views/admin/AdminMatchAnalysisView.vue'
import AdminSubscribersView from '@/views/admin/AdminSubscribersView.vue'

// Correspondance directe avec le parcours principal décrit en section 5.2.1
// du cahier des charges.
const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/matchs', name: 'matches', component: MatchesView },
    { path: '/matchs/:id', name: 'match-detail', component: MatchDetailView, props: true },
    // ?plan=classique|vip|vip-annuel : voir connexion.html et section 3.9.
    { path: '/connexion', name: 'connexion', component: ConnexionView },
    { path: '/inscription', name: 'inscription', component: ConnexionView },
    { path: '/profil', name: 'profil', component: ConnexionView },

    // Back-office (section 3.7) — réservé ROLE_ADMIN, voir le garde ci-dessous.
    // Les noms de route (admin-dashboard / admin-matches / admin-match-analysis /
    // admin-subscribers) doivent rester exactement ceux-ci : AdminLayout.vue et
    // AdminDashboardView.vue y font référence directement (RouterLink :to="{ name: ... }").
    {
      path: '/admin',
      name: 'admin-dashboard',
      component: AdminDashboardView,
      meta: { requiresAdmin: true },
    },
    {
      path: '/admin/matchs',
      name: 'admin-matches',
      component: AdminMatchesView,
      meta: { requiresAdmin: true },
    },
    {
      path: '/admin/matchs/:id',
      name: 'admin-match-analysis',
      component: AdminMatchAnalysisView,
      props: true,
      meta: { requiresAdmin: true },
    },
    {
      path: '/admin/abonnes',
      name: 'admin-subscribers',
      component: AdminSubscribersView,
      meta: { requiresAdmin: true },
    },
  ],
})

// Un accès direct à une route /admin/* (F5, favori, saisie d'URL) arrive ici
// avant que App.vue ait eu le temps d'appeler fetchCurrentUser() dans son
// onMounted — donc auth.user peut être vide même si un token existe déjà. On
// le recharge ici si besoin avant de trancher, pour ne pas éjecter à tort un
// admin qui vient juste de rafraîchir la page.
router.beforeEach(async (to) => {
  if (!to.meta.requiresAdmin) return true

  const { useAuthStore } = await import('@/stores/auth')
  const auth = useAuthStore()

  if (!auth.isAuthenticated) {
    return { name: 'connexion', query: { redirect: to.fullPath } }
  }

  if (!auth.user) {
    try {
      await auth.fetchCurrentUser()
    } catch {
      return { name: 'connexion', query: { redirect: to.fullPath } }
    }
  }

  if (!auth.isAdmin) {
    return { name: 'matches' }
  }

  return true
})

export default router