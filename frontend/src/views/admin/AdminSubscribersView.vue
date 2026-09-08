<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '@/api/client'
import AdminLayout from '@/components/admin/AdminLayout.vue'

const subscriptions = ref([])
const loading = ref(true)
const error = ref(null)
const statusFilter = ref('')

const STATUS_LABELS = { trialing: 'essai', active: 'actif', past_due: 'paiement en retard', canceled: 'résilié' }
const PERIOD_LABELS = { month: '/ mois', quarter: '/ trimestre', year: '/ an' }

onMounted(async () => {
  try {
    // GET /api/subscriptions : un admin voit la collection complète grâce à
    // CurrentUserSubscriptionExtension (voir backend), qui ne filtre par
    // utilisateur courant que pour un non-admin.
    const data = await api.get('/api/subscriptions?itemsPerPage=50')
    subscriptions.value = data['hydra:member'] ?? data['member'] ?? data
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
})

const filtered = computed(() => {
  if (!statusFilter.value) return subscriptions.value
  return subscriptions.value.filter((s) => s.status === statusFilter.value)
})

function priceLabel(plan) {
  const amount = (plan.priceCents / 100).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return `${amount} ${plan.currency} ${PERIOD_LABELS[plan.billingPeriod] ?? ''}`
}

function dateLabel(iso) {
  return iso ? new Date(iso).toLocaleDateString('fr-FR', { dateStyle: 'medium' }) : '—'
}
</script>

<template>
  <AdminLayout>
    <div class="head">
      <h1>Abonnés</h1>
      <p class="sub">{{ subscriptions.length }} abonnement(s) au total</p>
    </div>

    <div class="card filters">
      <label>
        Statut
        <select v-model="statusFilter">
          <option value="">Tous</option>
          <option v-for="(label, key) in STATUS_LABELS" :key="key" :value="key">{{ label }}</option>
        </select>
      </label>
    </div>

    <p v-if="loading">Chargement…</p>
    <p v-else-if="error" class="err">Impossible de charger les abonnés.</p>
    <p v-else-if="filtered.length === 0" class="card empty">Aucun abonnement ne correspond.</p>

    <div v-for="s in filtered" :key="s.id" class="card sub-row">
      <div class="who">
        <div class="avatar">{{ s.user ? (s.user.firstName?.[0] ?? '') + (s.user.lastName?.[0] ?? '') : '?' }}</div>
        <div>
          <!-- s.user peut être absent si le compte associé a été supprimé
               entre-temps (ou n'a jamais été correctement lié) — on l'affiche
               explicitement plutôt que de laisser planter tout le rendu de la
               liste sur un seul abonnement orphelin. -->
          <template v-if="s.user">
            <div class="name">{{ s.user.firstName }} {{ s.user.lastName }}</div>
            <div class="email">{{ s.user.email }}</div>
          </template>
          <div v-else class="name orphan">Compte supprimé (abonnement #{{ s.id }})</div>
        </div>
      </div>
      <div class="plan">
        <div class="plan-name">{{ s.plan.name }}</div>
        <div class="plan-price">{{ priceLabel(s.plan) }}</div>
      </div>
      <span class="badge" :class="s.status">{{ STATUS_LABELS[s.status] ?? s.status }}</span>
      <div class="period">
        <span>Fin de période : {{ dateLabel(s.currentPeriodEnd) }}</span>
        <span v-if="s.canceledAt">Résilié le {{ dateLabel(s.canceledAt) }}</span>
      </div>
    </div>
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
.name.orphan {
  color: var(--grey);
  font-style: italic;
  font-weight: 600;
}
.empty {
  color: var(--grey);
  font-size: 14px;
}

.filters {
  display: flex;
  gap: 18px;
  margin-bottom: 18px;
}
.filters label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--grey);
}
.filters select {
  border: 1px solid var(--line);
  background: var(--admin-bg);
  border-radius: 10px;
  padding: 8px 12px;
  font-size: 13px;
  font-family: inherit;
  color: var(--ink);
  min-width: 180px;
}

.sub-row {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.who {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 220px;
}
.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--blue);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}
.name {
  font-weight: 700;
  font-size: 14px;
}
.email {
  font-size: 12px;
  color: var(--grey);
}
.plan {
  min-width: 160px;
}
.plan-name {
  font-weight: 600;
  font-size: 13px;
}
.plan-price {
  font-size: 12px;
  color: var(--grey);
}
.badge {
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  background: var(--admin-bg);
}
.badge.active,
.badge.trialing {
  background: #e6f9ea;
  color: #1f7d33;
}
.badge.past_due {
  background: #fff3cd;
  color: #8a6100;
}
.badge.canceled {
  background: #fdecea;
  color: #b3261e;
}
.period {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 12px;
  color: var(--grey);
  margin-left: auto;
}

@media (max-width: 640px) {
  .filters select {
    width: 100%;
    min-width: 0;
    box-sizing: border-box;
  }
  .sub-row {
    gap: 12px;
    padding: 16px 18px;
  }
  .period {
    margin-left: 0;
  }
}

@media (max-width: 480px) {
  h1 {
    font-size: 21px;
  }
  .who {
    min-width: 0;
    flex: 1 1 100%;
  }
  .plan {
    min-width: 0;
  }
}
</style>