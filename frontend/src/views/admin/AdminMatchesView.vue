<script setup>
import { ref, reactive, watch, onMounted } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { api } from '@/api/client'
import AdminLayout from '@/components/admin/AdminLayout.vue'

const route = useRoute()
const matches = ref([])
const loading = ref(true)
const error = ref(null)

// Filtres réellement supportés côté API (voir #[ApiFilter(SearchFilter::class,
// properties: ['surface' => 'exact', 'status' => 'exact', 'tournamentName' => 'partial'])]
// sur TennisMatch) — pas de filtre inventé côté client. `?q=` (venant de la
// recherche dans AdminLayout) préremplit le filtre tournoi.
const filters = reactive({ surface: '', status: '', tournamentName: route.query.q ?? '' })

function playerInitials(name) {
  return (name || '').split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase()
}

async function load() {
  loading.value = true
  error.value = null
  try {
    const params = new URLSearchParams({ itemsPerPage: '30' })
    if (filters.surface) params.set('surface', filters.surface)
    if (filters.status) params.set('status', filters.status)
    if (filters.tournamentName) params.set('tournamentName', filters.tournamentName)

    const data = await api.get(`/api/tennis_matches?${params.toString()}`)
    matches.value = data['hydra:member'] ?? data['member'] ?? data
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}

onMounted(load)
let debounce
watch(filters, () => {
  clearTimeout(debounce)
  debounce = setTimeout(load, 300)
})

const STATUS_LABELS = { scheduled: 'à venir', live: 'en direct', finished: 'terminé', walkover: 'forfait' }
const SURFACE_LABELS = { dur: 'dur', terre_battue: 'terre battue', gazon: 'gazon', indoor: 'indoor' }
</script>

<template>
  <AdminLayout>
    <div class="head">
      <h1>Modèle IA — matchs</h1>
      <p class="sub">{{ matches.length }} match(s) affiché(s)</p>
    </div>

    <div class="card filters">
      <label>
        Surface
        <select v-model="filters.surface">
          <option value="">Toutes</option>
          <option v-for="(label, key) in SURFACE_LABELS" :key="key" :value="key">{{ label }}</option>
        </select>
      </label>
      <label>
        Statut
        <select v-model="filters.status">
          <option value="">Tous</option>
          <option v-for="(label, key) in STATUS_LABELS" :key="key" :value="key">{{ label }}</option>
        </select>
      </label>
      <label>
        Tournoi
        <input v-model="filters.tournamentName" type="text" placeholder="Rechercher…" />
      </label>
    </div>

    <p v-if="loading">Chargement…</p>
    <p v-else-if="error" class="err">Impossible de charger les matchs.</p>
    <p v-else-if="matches.length === 0" class="card empty">Aucun match ne correspond à ces filtres.</p>

    <RouterLink
      v-for="m in matches"
      :key="m.id"
      :to="{ name: 'admin-match-analysis', params: { id: m.id } }"
      class="card match-row"
    >
      <div class="mr-players">
        <span class="mr-avatar">{{ playerInitials(m.playerA.fullName) }}</span>
        <b>{{ m.playerA.fullName }}</b> vs <b>{{ m.playerB.fullName }}</b>
        <span class="mr-avatar blue">{{ playerInitials(m.playerB.fullName) }}</span>
      </div>
      <div class="mr-meta">
        <span>{{ m.tournamentName }} · {{ m.round }}</span>
        <span>{{ SURFACE_LABELS[m.surface] ?? m.surface }}</span>
        <span class="badge" :class="m.status">{{ STATUS_LABELS[m.status] ?? m.status }}</span>
        <span v-if="m.prediction">Favori : {{ m.prediction.favoritePlayer.fullName }} ({{ Math.round(m.prediction.probabilityFavorite * 100) }} %)</span>
      </div>
    </RouterLink>
  </AdminLayout>
</template>

<style scoped>
.head {
  margin: 10px 4px 20px;
}
h1 {
  font-size: 26px;
  font-weight: 700;
  margin: 0;
}
.sub {
  color: var(--grey);
  font-size: 13px;
  margin-top: 4px;
}
.err {
  color: var(--red);
}
.empty {
  color: var(--grey);
  font-size: 14px;
}

.filters {
  display: flex;
  gap: 18px;
  margin-bottom: 18px;
  flex-wrap: wrap;
}
.filters label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--grey);
}
.filters select,
.filters input {
  border: 1px solid var(--line);
  background: var(--admin-bg);
  border-radius: 10px;
  padding: 8px 12px;
  font-size: 13px;
  font-family: inherit;
  color: var(--ink);
  min-width: 160px;
}

.match-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 12px;
  flex-wrap: wrap;
  cursor: pointer;
}
.mr-players {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}
.mr-avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: var(--green);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}
.mr-avatar.blue {
  background: var(--blue);
}
.mr-meta {
  display: flex;
  gap: 14px;
  align-items: center;
  font-size: 12px;
  color: var(--grey);
  flex-wrap: wrap;
}
.badge {
  padding: 3px 10px;
  border-radius: 999px;
  font-weight: 700;
  font-size: 11px;
  background: var(--admin-bg);
  color: var(--ink);
}
.badge.finished {
  background: #e6f9ea;
  color: #1f7d33;
}
.badge.live {
  background: #fdecea;
  color: #b3261e;
}

@media (max-width: 640px) {
  .filters {
    gap: 12px;
  }
  .filters label {
    flex: 1 1 100%;
  }
  .filters select,
  .filters input {
    width: 100%;
    min-width: 0;
    box-sizing: border-box;
  }
}

@media (max-width: 480px) {
  h1 {
    font-size: 21px;
  }
  .match-row {
    padding: 16px 18px;
    gap: 8px;
  }
  .mr-players {
    font-size: 13px;
  }
  .mr-meta {
    gap: 8px;
  }
}
</style>