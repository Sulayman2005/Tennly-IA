<script setup>
import { ref, watch } from 'vue'
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
  mobileNavOpen.value = false
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
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none"><rect x="3" y="3" width="8" height="8" rx="2" stroke="currentColor" stroke-width="1.8"/><rect x="13" y="3" width="8" height="8" rx="2" stroke="currentColor" stroke-width="1.8"/><rect x="3" y="13" width="8" height="8" rx="2" stroke="currentColor" stroke-width="1.8"/><rect x="13" y="13" width="8" height="8" rx="2" stroke="currentColor" stroke-width="1.8"/></svg>',
  'admin-matches':
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="8.5" stroke="currentColor" stroke-width="1.8"/><path d="M12 7v5l3.2 3.2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
  'admin-subscribers':
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none"><circle cx="9" cy="8" r="3.2" stroke="currentColor" stroke-width="1.8"/><path d="M3.5 20c0-3.6 2.5-6 5.5-6s5.5 2.4 5.5 6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><circle cx="17" cy="9" r="2.4" stroke="currentColor" stroke-width="1.6"/><path d="M15.7 12.3c2.3.3 3.8 2.3 3.8 5.2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>',
}

const NAV = [
  { name: 'admin-dashboard', to: '/admin', label: 'Tableau de bord', match: ['admin-dashboard'] },
  { name: 'admin-matches', to: '/admin/matchs', label: 'Modèle', match: ['admin-matches', 'admin-match-analysis'] },
  { name: 'admin-subscribers', to: '/admin/abonnes', label: 'Abonnés', match: ['admin-subscribers'] },
]

// Refonte "sidebar" (15/09/2026) : la navigation admin passe d'une barre de
// pilules flottante en haut à un panneau latéral persistant façon console
// d'exploitation — direction visuelle demandée explicitement, en rupture
// avec le style "premium" du site public. Sur mobile, ce même panneau devient
// un tiroir qui se referme automatiquement après un changement de page.
const mobileNavOpen = ref(false)
watch(
  () => route.fullPath,
  () => {
    mobileNavOpen.value = false
  },
)
</script>

<template>
  <div class="admin-shell">
    <aside class="sidebar" :class="{ open: mobileNavOpen }">
      <RouterLink to="/admin" class="brand" @click="mobileNavOpen = false">
        <span class="mark">
          <svg viewBox="0 0 24 24" fill="none" style="width: 62%; height: 62%">
            <circle cx="12" cy="12" r="8.4" stroke="#fff" stroke-width="1.7" />
            <path d="M5.4 6C8.3 8.5 8.3 15.5 5.4 18" stroke="#fff" stroke-width="1.7" stroke-linecap="round" />
            <path d="M18.6 6C15.7 8.5 15.7 15.5 18.6 18" stroke="#fff" stroke-width="1.7" stroke-linecap="round" />
          </svg>
        </span>
        Tennly
      </RouterLink>

      <div class="nav-label">Administration</div>
      <nav class="nav-list">
        <RouterLink
          v-for="item in NAV"
          :key="item.name"
          :to="item.to"
          class="nav-item"
          :class="{ active: item.match.includes(route.name) }"
          @click="mobileNavOpen = false"
        >
          <span class="nav-icon" v-html="ICONS[item.name]"></span>
          {{ item.label }}
        </RouterLink>
        <span class="nav-item disabled" title="Pas encore de contenu éditorial à gérer — voir README">
          <span class="nav-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><rect x="4" y="4" width="16" height="16" rx="3" stroke="currentColor" stroke-width="1.6" /><path d="M8 9h8M8 13h5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" /></svg>
          </span>
          Contenu
        </span>
      </nav>

      <div class="sidebar-foot">
        <form class="search" @submit.prevent="submitSearch">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <circle cx="11" cy="11" r="7" stroke="currentColor" stroke-width="2" />
            <path d="M20 20l-3.2-3.2" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
          </svg>
          <input v-model="searchTerm" type="text" placeholder="Rechercher un tournoi…" />
        </form>
        <RouterLink to="/matchs" class="site-link" @click="mobileNavOpen = false">
          <span>Voir le site</span>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
            <path d="M7 17L17 7M9 7h8v8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </RouterLink>
        <div class="who">
          <div class="avatar-sm">{{ initials(auth.user ? `${auth.user.firstName} ${auth.user.lastName}` : 'AD') }}</div>
          <div class="who-name">{{ auth.user ? `${auth.user.firstName} ${auth.user.lastName}` : 'Administrateur' }}</div>
        </div>
      </div>
    </aside>

    <button
      v-if="mobileNavOpen"
      class="backdrop"
      aria-label="Fermer le menu"
      @click="mobileNavOpen = false"
    ></button>

    <div class="content-col">
      <header class="topbar">
        <button class="burger" aria-label="Ouvrir le menu" @click="mobileNavOpen = !mobileNavOpen">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" stroke-width="2" stroke-linecap="round" /></svg>
        </button>
        <RouterLink to="/admin" class="topbar-brand">Tennly — Administration</RouterLink>
      </header>

      <main>
        <slot />
      </main>
    </div>
  </div>
</template>

<style scoped>
/*
 * Refonte "console" (15/09/2026) : nouvelle identité visuelle propre au
 * back-office, en rupture volontaire avec le style "premium" (fond gris
 * doux, ombres généreuses, coins très arrondis) du site public — demandé
 * explicitement plutôt que d'être un simple ajustement du style précédent.
 * Structure : panneau latéral persistant + cartes à bordure fine plutôt
 * qu'à ombre portée, densité d'information plus élevée, chiffres clés en
 * police monospace (voir --mono) pour un rendu "outil de données" sobre.
 * Les composants graphiques partagés (SurfaceRoseChart, GrowthAreaChart)
 * lisent ces mêmes tokens (--admin-bg/--admin-card/--ink/--grey/--green/
 * --blue) : ils héritent du nouveau thème sans être modifiés eux-mêmes.
 */
.admin-shell {
  --admin-bg: #f7f7f4;
  --admin-card: #ffffff;
  --grey: #6b7178;
  --line: #e3e3df;
  --adm-radius: 12px;
  --adm-radius-sm: 8px;
  --mono: 'JetBrains Mono', ui-monospace, 'SFMono-Regular', Menlo, Consolas, monospace;

  display: flex;
  align-items: stretch;
  min-height: 100vh;
  background: var(--admin-bg);
}

/* ---------------------------------------------------------------- */
/* SIDEBAR                                                            */
/* ---------------------------------------------------------------- */
.sidebar {
  flex: none;
  width: 236px;
  display: flex;
  flex-direction: column;
  background: var(--admin-card);
  border-right: 1px solid var(--line);
  padding: 20px 16px;
  position: sticky;
  top: 0;
  height: 100vh;
  overflow-y: auto;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
  font-size: 15px;
  padding: 4px 6px 20px;
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

.nav-label {
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--grey);
  padding: 0 10px 8px;
}

.nav-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border-radius: var(--adm-radius-sm);
  font-size: 13.5px;
  font-weight: 600;
  color: var(--grey);
  border-left: 2px solid transparent;
  transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}
.nav-icon {
  display: inline-flex;
  line-height: 0;
  flex: none;
}
.nav-item.disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
.nav-item:hover:not(.active):not(.disabled) {
  background: var(--admin-bg);
  color: var(--ink);
}
.nav-item.active {
  background: rgba(199, 255, 60, 0.14);
  color: var(--ink);
  border-left-color: var(--green);
}

.sidebar-foot {
  margin-top: auto;
  padding-top: 16px;
  border-top: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.search {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--admin-bg);
  border: 1px solid var(--line);
  border-radius: var(--adm-radius-sm);
  padding: 8px 10px;
  color: var(--grey);
}
.search input {
  border: none;
  background: transparent;
  font-size: 12px;
  font-family: inherit;
  color: var(--ink);
  width: 100%;
  min-width: 0;
}
.search input:focus {
  outline: none;
}
.site-link {
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  font-size: 12px;
  color: var(--ink);
  font-weight: 600;
  padding: 8px 10px;
  border-radius: var(--adm-radius-sm);
  border: 1px solid var(--line);
}
.site-link:hover {
  background: var(--admin-bg);
}
.who {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 2px 4px;
}
.avatar-sm {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--blue);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  flex: none;
}
.who-name {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.backdrop {
  display: none;
}

/* ---------------------------------------------------------------- */
/* CONTENU                                                             */
/* ---------------------------------------------------------------- */
.content-col {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.topbar {
  display: none;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  background: var(--admin-card);
  border-bottom: 1px solid var(--line);
  position: sticky;
  top: 0;
  z-index: 5;
}
.burger {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: var(--adm-radius-sm);
  border: 1px solid var(--line);
  background: var(--admin-card);
  color: var(--ink);
  flex: none;
}
.topbar-brand {
  font-weight: 700;
  font-size: 14px;
}

main {
  flex: 1;
  max-width: 1240px;
  width: 100%;
  margin: 0 auto;
  padding: 28px 32px 60px;
}

main :deep(.card) {
  background: var(--admin-card);
  border: 1px solid var(--line);
  border-radius: var(--adm-radius);
  padding: 22px;
  box-shadow: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}
main :deep(.card:hover) {
  border-color: #cfd6d2;
  box-shadow: 0 10px 28px -18px rgba(20, 24, 26, 0.28);
}

@media (max-width: 900px) {
  .sidebar {
    position: fixed;
    inset: 0 auto 0 0;
    z-index: 40;
    transform: translateX(-100%);
    transition: transform 0.28s var(--ease-premium, ease);
    box-shadow: 0 0 0 rgba(0, 0, 0, 0);
  }
  .sidebar.open {
    transform: translateX(0);
    box-shadow: 24px 0 48px -24px rgba(0, 0, 0, 0.35);
  }
  .backdrop {
    display: block;
    position: fixed;
    inset: 0;
    z-index: 30;
    background: rgba(10, 14, 12, 0.32);
    border: none;
    padding: 0;
    cursor: pointer;
  }
  .topbar {
    display: flex;
  }
  main {
    padding: 22px 18px 48px;
  }
}

@media (max-width: 480px) {
  .sidebar {
    width: 84vw;
    max-width: 300px;
  }
  main {
    padding: 18px 14px 44px;
  }
}
</style>
