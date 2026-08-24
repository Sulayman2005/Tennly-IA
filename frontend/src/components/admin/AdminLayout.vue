<script setup>
import { ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const searchTerm = ref('')

function submitSearch() {
  const q = searchTerm.value.trim()
  if (!q) return
  // Renvoie vers la liste des matchs avec le filtre "tournoi" déjà appliqué
  // (voir AdminMatchesView, qui lit ?q= au chargement) — pas une barre de
  // recherche décorative.
  router.push({ name: 'admin-matches', query: { q } })
}

const initials = (str) =>
  (str || '')
    .split(' ')
    .filter(Boolean)
    .map((w) => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()

const ICONS = {
  'admin-dashboard':
    '<svg width="15" height="15" viewBox="0 0 24 24" fill="none"><rect x="3" y="3" width="8" height="8" rx="2" stroke="currentColor" stroke-width="1.8"/><rect x="13" y="3" width="8" height="8" rx="2" stroke="currentColor" stroke-width="1.8"/><rect x="3" y="13" width="8" height="8" rx="2" stroke="currentColor" stroke-width="1.8"/><rect x="13" y="13" width="8" height="8" rx="2" stroke="currentColor" stroke-width="1.8"/></svg>',
  'admin-matches':
    '<svg width="15" height="15" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="8.5" stroke="currentColor" stroke-width="1.8"/><path d="M12 7v5l3.2 3.2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
  'admin-subscribers':
    '<svg width="15" height="15" viewBox="0 0 24 24" fill="none"><circle cx="9" cy="8" r="3.2" stroke="currentColor" stroke-width="1.8"/><path d="M3.5 20c0-3.6 2.5-6 5.5-6s5.5 2.4 5.5 6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><circle cx="17" cy="9" r="2.4" stroke="currentColor" stroke-width="1.6"/><path d="M15.7 12.3c2.3.3 3.8 2.3 3.8 5.2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>',
}

const NAV = [
  { name: 'admin-dashboard', to: '/admin', label: 'Tableau de bord', match: ['admin-dashboard'] },
  { name: 'admin-matches', to: '/admin/matchs', label: 'Modèle IA', match: ['admin-matches', 'admin-match-analysis'] },
  { name: 'admin-subscribers', to: '/admin/abonnes', label: 'Abonnés', match: ['admin-subscribers'] },
]
</script>

<template>
  <div class="admin-shell">
    <div class="wrap">
      <header class="topnav">
        <RouterLink to="/admin" class="brand">
          <span class="mark">
            <svg viewBox="0 0 24 24" fill="none" style="width: 62%; height: 62%">
              <circle cx="12" cy="12" r="8.4" stroke="#fff" stroke-width="1.7" />
              <path d="M5.4 6C8.3 8.5 8.3 15.5 5.4 18" stroke="#fff" stroke-width="1.7" stroke-linecap="round" />
              <path d="M18.6 6C15.7 8.5 15.7 15.5 18.6 18" stroke="#fff" stroke-width="1.7" stroke-linecap="round" />
            </svg>
          </span>
          Tennly IA
        </RouterLink>

        <nav class="tabs">
          <RouterLink
            v-for="item in NAV"
            :key="item.name"
            :to="item.to"
            :class="{ active: item.match.includes(route.name) }"
          >
            <span class="tab-icon" v-html="ICONS[item.name]"></span>
            {{ item.label }}
          </RouterLink>
          <span class="tab-disabled" title="Pas encore de contenu éditorial à gérer — voir README">Contenu</span>
        </nav>

        <div class="navright">
          <form class="search" @submit.prevent="submitSearch">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <circle cx="11" cy="11" r="7" stroke="currentColor" stroke-width="2" />
              <path d="M20 20l-3.2-3.2" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
            </svg>
            <input v-model="searchTerm" type="text" placeholder="Rechercher un tournoi…" />
          </form>
          <RouterLink to="/matchs" class="site-link">
            Voir le site
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
              <path d="M7 17L17 7M9 7h8v8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </RouterLink>
          <div class="avatar-sm">{{ initials(auth.user ? `${auth.user.firstName} ${auth.user.lastName}` : 'AD') }}</div>
        </div>
      </header>

      <main>
        <slot />
      </main>
    </div>
  </div>
</template>

<style scoped>
/*
 * Reprend l'identité visuelle du reste de l'app (tokens.css : --green,
 * --lime, --blue, --ink, --grey, --line, --amber, --red) plutôt que de
 * dupliquer une palette maison — seuls --admin-bg/--admin-card sont propres
 * au back-office, qui inverse le fond (gris clair) et les cartes (blanc) par
 * rapport au site public.
 */
.admin-shell {
  --admin-bg: #f2f3f5;
  --admin-card: #ffffff;
  background: var(--admin-bg);
  min-height: 100vh;
}
.wrap {
  max-width: 1240px;
  margin: 0 auto;
  padding: 24px 28px 60px;
}

.topnav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--admin-card);
  border-radius: 20px;
  padding: 10px 12px 10px 18px;
  box-shadow: var(--shadow-soft);
  margin-bottom: 22px;
  gap: 18px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
  font-size: 15px;
  white-space: nowrap;
}
.brand .mark {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--green), var(--lime));
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}

.tabs {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}
.tabs a,
.tab-disabled {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 9px 16px;
  border-radius: 999px;
  font-size: 13px;
  color: var(--grey);
  font-weight: 600;
  transition: background 0.15s ease, color 0.15s ease;
}
.tab-icon {
  display: inline-flex;
  line-height: 0;
}
.tab-disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
.tabs a:hover:not(.active) {
  background: var(--admin-bg);
  color: var(--ink);
}
.tabs a.active {
  background: var(--ink);
  color: #fff;
}

.navright {
  display: flex;
  align-items: center;
  gap: 10px;
}
.search {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--admin-bg);
  border-radius: 999px;
  padding: 8px 14px;
  color: var(--grey);
}
.search input {
  border: none;
  background: transparent;
  font-size: 12px;
  font-family: inherit;
  color: var(--ink);
  width: 140px;
}
.search input:focus {
  outline: none;
}
.site-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--ink);
  font-weight: 600;
  white-space: nowrap;
  background: var(--admin-bg);
  padding: 9px 14px;
  border-radius: 999px;
}
.avatar-sm {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: var(--blue);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex: none;
}

main :deep(.card) {
  background: var(--admin-card);
  border-radius: 24px;
  padding: 24px;
  box-shadow: var(--shadow-soft);
}

@media (max-width: 900px) {
  .search {
    display: none;
  }
}
</style>