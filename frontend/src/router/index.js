import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'
import MatchesView from '@/views/MatchesView.vue'
import MatchDetailView from '@/views/MatchDetailView.vue'
import ConnexionView from '@/views/ConnexionView.vue'
import ComparateurView from '@/views/ComparateurView.vue'
import AdminDashboardView from '@/views/admin/AdminDashboardView.vue'
import AdminMatchesView from '@/views/admin/AdminMatchesView.vue'
import AdminMatchAnalysisView from '@/views/admin/AdminMatchAnalysisView.vue'
import AdminSubscribersView from '@/views/admin/AdminSubscribersView.vue'
import ModelReliabilityView from '@/views/ModelReliabilityView.vue'
import CguView from '@/views/legal/CguView.vue'
import CgvView from '@/views/legal/CgvView.vue'
import LegalNoticeView from '@/views/legal/LegalNoticeView.vue'
import PrivacyView from '@/views/legal/PrivacyView.vue'

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
    { path: '/fiabilite', name: 'model-reliability', component: ModelReliabilityView },
    // Comparateur de joueurs : compare deux joueurs (classement, Elo global
    // + par surface, main dominante) hors contexte d'un match précis, et
    // propose une analyse complète à la demande — voir ComparateurView.vue.
    // Réservé à l'admin + aux abonnés (même règle que l'analyse complète
    // d'un match, voir le garde ci-dessous et Prediction.php côté backend).
    { path: '/comparateur', name: 'comparateur', component: ComparateurView, meta: { requiresSubscriptionOrAdmin: true } },
    { path: '/inscription', name: 'inscription', component: ConnexionView },
    { path: '/profil', name: 'profil', component: ConnexionView },

    // Pages légales (CGV, CGU, mentions légales, politique de confidentialité) :
    // les fichiers existaient déjà dans src/views/legal/ mais n'étaient
    // enregistrés sur aucune route — /cgv, /cgu, etc. renvoyaient une page
    // totalement blanche (aucune route ne matchait), et le lien "voir les
    // CGV" de PaywallModal.vue pointait donc dans le vide. Corrigé ici.
    { path: '/cgv', name: 'cgv', component: CgvView },
    { path: '/cgu', name: 'cgu', component: CguView },
    { path: '/mentions-legales', name: 'legal-notice', component: LegalNoticeView },
    { path: '/confidentialite', name: 'privacy', component: PrivacyView },

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
  if (!to.meta.requiresAdmin && !to.meta.requiresSubscriptionOrAdmin) return true

  const { useAuthStore } = await import('@/stores/auth.js')
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

  if (to.meta.requiresAdmin && !auth.isAdmin) {
    return { name: 'matches' }
  }

  // Comparateur : admin OU abonné actif (voir hasActiveSubscription() côté
  // backend, User.php) — un utilisateur connecté mais non-abonné est
  // redirigé vers /matchs plutôt que /connexion, il est déjà authentifié.
  if (to.meta.requiresSubscriptionOrAdmin && !auth.isAdmin && !auth.hasActiveSubscription) {
    return { name: 'matches' }
  }

  return true
})

export default router