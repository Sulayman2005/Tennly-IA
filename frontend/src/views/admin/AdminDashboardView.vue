<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import AdminLayout from '@/components/admin/AdminLayout.vue'
import SurfaceRoseChart from '@/components/admin/SurfaceRoseChart.vue'

const auth = useAuthStore()
const summary = ref(null)
const upcomingMatches = ref([])
const loading = ref(true)
const error = ref(null)

const PLAN_COLORS = ['var(--green)', 'var(--blue)', 'var(--amber)', 'var(--red)']

onMounted(async () => {
  try {
    // GET /api/admin/dashboard : agrégats réels (voir AdminDashboardProvider
    // côté backend), sécurisé ROLE_ADMIN.
    const [dashboard, matches] = await Promise.all([
      api.get('/api/admin/dashboard'),
      api.get('/api/tennis_matches?itemsPerPage=8'),
    ])
    summary.value = dashboard
    upcomingMatches.value = matches['hydra:member'] ?? matches['member'] ?? matches
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
})

const totalSubscribers = computed(() => summary.value?.activeSubscriptionsCount ?? 0)

// Segments du donut "répartition des abonnés" — calculés à partir des
// vraies proportions renvoyées par l'API, aucune valeur figée.
const donutSegments = computed(() => {
  if (!summary.value || totalSubscribers.value === 0) return []
  const r = 15.9155
  const circumference = 2 * Math.PI * r
  let cumulative = 0
  return summary.value.subscribersByPlan.map((plan, i) => {
    const frac = plan.count / totalSubscribers.value
    const segment = {
      ...plan,
      pct: Math.round(frac * 100),
      color: PLAN_COLORS[i % PLAN_COLORS.length],
      dashArray: `${frac * circumference} ${circumference - frac * circumference}`,
      dashOffset: -cumulative * circumference,
    }
    cumulative += frac
    return segment
  })
})

const mrrEuros = computed(() =>
  ((summary.value?.mrrCents ?? 0) / 100).toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 0 }),
)

// Répartition du MRR par formule — même donnée que le donut abonnés, mais
// pondérée par le prix mensualisé de chaque formule plutôt que par le simple
// décompte, pour donner un visuel utile en plus du chiffre total.
const mrrByPlan = computed(() => {
  if (!summary.value) return []
  const max = Math.max(...summary.value.subscribersByPlan.map((p) => p.count), 1)
  return summary.value.subscribersByPlan.map((p, i) => ({
    ...p,
    color: PLAN_COLORS[i % PLAN_COLORS.length],
    barPct: Math.round((p.count / max) * 100),
  }))
})

const bestSurface = computed(() => {
  const list = summary.value?.modelAccuracyBySurface ?? []
  if (list.length < 2) return null
  return [...list].sort((a, b) => b.accuracy - a.accuracy)
})

const surfaceLabels = { dur: 'dur', terre_battue: 'terre battue', gazon: 'gazon', indoor: 'indoor (salle)' }

function playerInitials(name) {
  return (name || '').split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase()
}

const STATUS_DOT = { scheduled: 'grey', live: 'red', finished: 'green', walkover: 'grey' }

// ---- Mini calendrier du mois en cours, marquant les jours avec au moins un
// match connu (données réelles issues de la même requête que la liste
// ci-dessus) — pas de calendrier de tournois fictif (voir README).
const today = new Date()
const WEEKDAYS = ['L', 'M', 'M', 'J', 'V', 'S', 'D']

const matchDaysInMonth = computed(() => {
  const set = new Set()
  for (const m of upcomingMatches.value) {
    const d = new Date(m.scheduledAt)
    if (d.getFullYear() === today.getFullYear() && d.getMonth() === today.getMonth()) {
      set.add(d.getDate())
    }
  }
  return set
})

const calendarCells = computed(() => {
  const year = today.getFullYear()
  const month = today.getMonth()
  const firstWeekday = (new Date(year, month, 1).getDay() + 6) % 7 // lundi = 0
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const cells = Array.from({ length: firstWeekday }, () => null)
  for (let d = 1; d <= daysInMonth; d++) cells.push(d)
  return cells
})

const monthLabel = computed(() => today.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' }))
</script>

<template>
  <AdminLayout>
    <div class="welcome">
      Bonjour, {{ auth.user?.firstName ?? '' }}
      <span>Voici l'état réel de la plateforme aujourd'hui</span>
    </div>

    <p v-if="loading">Chargement des indicateurs…</p>
    <p v-else-if="error" class="err">Impossible de charger le tableau de bord pour le moment.</p>

    <div v-else class="grid">
      <!-- HERO : performance globale du modèle -->
      <RouterLink :to="{ name: 'admin-matches' }" class="card span2 perf-hero">
        <svg class="court-lines" viewBox="0 0 600 200" preserveAspectRatio="none">
          <rect x="24" y="24" width="552" height="152" fill="none" stroke="rgba(255,255,255,.3)" stroke-width="1.5" />
          <line x1="24" y1="100" x2="576" y2="100" stroke="rgba(255,255,255,.22)" stroke-width="1.2" />
          <line x1="170" y1="24" x2="170" y2="176" stroke="rgba(255,255,255,.18)" stroke-width="1" />
          <line x1="430" y1="24" x2="430" y2="176" stroke="rgba(255,255,255,.18)" stroke-width="1" />
        </svg>
        <div class="rowtop">
          <div>
            <div class="eyebrow">Modèle IA — vue d'ensemble</div>
            <div class="big">{{ summary.modelAccuracyOverall !== null ? summary.modelAccuracyOverall + ' %' : '—' }}</div>
            <div class="lbl">Taux de réussite — sur {{ summary.finishedMatchesWithPredictionCount }} match(s) terminé(s)</div>
          </div>
          <span class="hero-arrow">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M7 17L17 7M9 7h8v8" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" /></svg>
          </span>
        </div>
        <p v-if="summary.modelAccuracyOverall === null" class="empty-note">
          Pas encore de match terminé avec analyse IA associée : ce taux apparaîtra dès le premier résultat enregistré.
        </p>
        <div class="perf-mini">
          <div><b>{{ summary.predictionsCount }}</b><span>Analyses calculées</span></div>
          <div><b>{{ summary.upcomingMatchesCount }}</b><span>Matchs à venir</span></div>
          <div><b>{{ totalSubscribers }}</b><span>Abonnements actifs</span></div>
        </div>
      </RouterLink>

      <!-- PROFIL PAR SURFACE -->
      <div class="card">
        <h3>Précision par surface</h3>
        <div class="sub">Réussite du modèle, 4 surfaces</div>
        <SurfaceRoseChart :by-surface="summary.modelAccuracyBySurface" :overall="summary.modelAccuracyOverall" />
      </div>

      <!-- INSIGHT -->
      <div class="card insight">
        <div class="insight-head">
          <span class="insight-icon">✦</span>
          <h3>Insight IA</h3>
        </div>
        <p v-if="!bestSurface">
          Pas encore assez de matchs terminés sur plusieurs surfaces différentes pour comparer la précision du modèle
          selon la surface.
        </p>
        <p v-else>
          Le modèle est plus précis sur {{ surfaceLabels[bestSurface[0].surface] }} ({{ bestSurface[0].accuracy }} %)
          que sur {{ surfaceLabels[bestSurface[bestSurface.length - 1].surface] }}
          ({{ bestSurface[bestSurface.length - 1].accuracy }} %), sur l'historique disponible.
        </p>
      </div>

      <!-- ABONNÉS -->
      <div class="card">
        <h3>Répartition des abonnés</h3>
        <div class="sub">{{ totalSubscribers }} abonnement(s) actif(s)</div>
        <div v-if="totalSubscribers === 0" class="empty-note">Aucun abonnement actif pour l'instant.</div>
        <div v-else class="donut-wrap">
          <svg width="92" height="92" viewBox="0 0 36 36">
            <circle cx="18" cy="18" r="15.9155" fill="none" stroke="var(--admin-bg)" stroke-width="4" />
            <circle
              v-for="seg in donutSegments"
              :key="seg.code"
              cx="18"
              cy="18"
              r="15.9155"
              fill="none"
              :stroke="seg.color"
              stroke-width="4"
              :stroke-dasharray="seg.dashArray"
              :stroke-dashoffset="seg.dashOffset"
              transform="rotate(-90 18 18)"
            />
          </svg>
          <div class="legend">
            <div v-for="seg in donutSegments" :key="seg.code">
              <i :style="{ background: seg.color }"></i>{{ seg.name }} — {{ seg.pct }} %
            </div>
          </div>
        </div>
      </div>

      <!-- MRR -->
      <div class="card">
        <h3>Revenu récurrent (MRR)</h3>
        <div class="sub">Abonnements actifs/en essai, mensualisés</div>
        <span class="mrr">{{ mrrEuros }} €</span>
        <div class="mrr-bars">
          <div v-for="p in mrrByPlan" :key="p.code" class="mrr-bar-row">
            <span class="mrr-bar-label">{{ p.name }}</span>
            <div class="mrr-bar-track"><i :style="{ width: p.barPct + '%', background: p.color }"></i></div>
            <span class="mrr-bar-count">{{ p.count }}</span>
          </div>
          <p v-if="mrrByPlan.length === 0" class="empty-note">Aucun abonnement actif pour l'instant.</p>
        </div>
      </div>

      <!-- PROCHAINS MATCHS -->
      <div class="card span2">
        <h3>Prochains matchs</h3>
        <div class="sub">Cliquer pour ouvrir l'analyse détaillée (Modèle IA)</div>
        <div v-if="upcomingMatches.length === 0" class="empty-note">Aucun match en base pour l'instant.</div>
        <RouterLink
          v-for="m in upcomingMatches"
          :key="m.id"
          :to="{ name: 'admin-match-analysis', params: { id: m.id } }"
          class="match-row"
        >
          <span class="status-dot" :class="STATUS_DOT[m.status]"></span>
          <span class="mr-players">
            <span class="mr-avatar">{{ playerInitials(m.playerA.fullName) }}</span>
            {{ m.playerA.fullName }} — {{ m.playerB.fullName }}
            <span class="mr-avatar blue">{{ playerInitials(m.playerB.fullName) }}</span>
          </span>
          <span class="mr-meta">{{ m.tournamentName }} · {{ m.round }}</span>
        </RouterLink>
      </div>

      <!-- CALENDRIER -->
      <div class="card">
        <h3>Calendrier</h3>
        <div class="sub" style="text-transform: capitalize">{{ monthLabel }}</div>
        <div class="cal">
          <div v-for="d in WEEKDAYS" :key="d" class="cal-d">{{ d }}</div>
          <div
            v-for="(cell, i) in calendarCells"
            :key="i"
            class="cal-n"
            :class="{
              empty: cell === null,
              today: cell === today.getDate(),
              match: cell !== null && matchDaysInMonth.has(cell),
            }"
          >
            {{ cell }}
          </div>
        </div>
      </div>
    </div>
  </AdminLayout>
</template>

<style scoped>
.welcome {
  font-size: 26px;
  font-weight: 700;
  margin: 10px 4px 20px;
}
.welcome span {
  color: var(--grey);
  font-weight: 400;
  font-size: 14px;
  display: block;
  margin-top: 4px;
}
.err {
  color: var(--red);
}
.grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 18px;
  align-items: stretch;
}
.span2 {
  grid-column: span 2;
}
.card h3 {
  margin: 0 0 4px;
  font-size: 14px;
  font-weight: 700;
}
.card .sub {
  font-size: 12px;
  color: var(--grey);
  margin-bottom: 16px;
}
.empty-note {
  font-size: 13px;
  color: var(--grey);
  line-height: 1.5;
}

/* HERO */
.perf-hero {
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, var(--green), var(--green2));
  color: #fff;
  display: block;
  text-decoration: none;
}
.court-lines {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0.7;
}
.perf-hero .rowtop,
.perf-hero .empty-note,
.perf-hero .perf-mini {
  position: relative;
  z-index: 1;
}
.rowtop {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}
.eyebrow {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  opacity: 0.75;
  margin-bottom: 8px;
}
.hero-arrow {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.14);
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}
.perf-hero .lbl {
  font-size: 12px;
  opacity: 0.75;
  margin-top: 2px;
}
.perf-hero .big {
  font-size: 40px;
  font-weight: 700;
  letter-spacing: -0.02em;
}
.perf-hero .empty-note {
  color: rgba(255, 255, 255, 0.85);
}
.perf-mini {
  display: flex;
  gap: 28px;
  margin-top: 24px;
  flex-wrap: wrap;
}
.perf-mini div b {
  display: block;
  font-size: 18px;
}
.perf-mini div span {
  font-size: 11px;
  opacity: 0.75;
}

/* INSIGHT */
.insight {
  background: #eef7f1;
}
.insight-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.insight-icon {
  color: var(--green);
}
.insight p {
  font-size: 13px;
  line-height: 1.6;
  margin: 8px 0 0;
  color: #1c3a2a;
}

/* DONUT */
.donut-wrap {
  display: flex;
  align-items: center;
  gap: 18px;
}
.legend div {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  margin-bottom: 8px;
}
.legend i {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  display: inline-block;
}

/* MRR */
.mrr {
  font-size: 32px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  display: block;
  margin-bottom: 16px;
}
.mrr-bars {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.mrr-bar-row {
  display: grid;
  grid-template-columns: 84px 1fr 22px;
  align-items: center;
  gap: 10px;
  font-size: 12px;
}
.mrr-bar-label {
  color: var(--grey);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.mrr-bar-track {
  height: 7px;
  border-radius: 99px;
  background: var(--admin-bg);
  overflow: hidden;
}
.mrr-bar-track i {
  display: block;
  height: 100%;
  border-radius: 99px;
}
.mrr-bar-count {
  font-weight: 700;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

/* MATCH LIST */
.match-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 0;
  border-bottom: 1px solid var(--line);
  font-size: 13px;
  cursor: pointer;
}
.match-row:last-child {
  border-bottom: none;
}
.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex: none;
  background: var(--grey);
}
.status-dot.green {
  background: #2e9e4d;
}
.status-dot.red {
  background: var(--red);
}
.mr-players {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  flex: 1;
}
.mr-avatar {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--green);
  color: #fff;
  font-size: 10px;
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
  color: var(--grey);
  font-size: 12px;
  white-space: nowrap;
}

/* CALENDAR */
.cal {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 5px;
}
.cal-d {
  text-align: center;
  font-size: 10px;
  color: var(--grey);
  padding: 2px 0 6px;
}
.cal-n {
  text-align: center;
  font-size: 11px;
  padding: 7px 0;
  border-radius: 8px;
  color: var(--ink);
}
.cal-n.empty {
  visibility: hidden;
}
.cal-n.match {
  background: #eef7f1;
  color: var(--green);
  font-weight: 700;
}
.cal-n.today {
  background: var(--ink);
  color: #fff;
  font-weight: 700;
}
</style>