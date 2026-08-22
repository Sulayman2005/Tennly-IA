import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'
import MatchesView from '@/views/MatchesView.vue'
import MatchDetailView from '@/views/MatchDetailView.vue'
import ConnexionView from '@/views/ConnexionView.vue'

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
  ],
})

export default router
