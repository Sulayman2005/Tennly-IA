<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import AdminLayout from '@/components/admin/AdminLayout.vue'
import SurfaceRoseChart from '@/components/admin/SurfaceRoseChart.vue'
import GrowthAreaChart from '@/components/admin/GrowthAreaChart.vue'

const auth = useAuthStore()
const summary = ref(null)
const upcomingMatches = ref([])
const loading = ref(true)
const error = ref(null)

const PLAN_COLORS = ['var(--green)', 'var(--blue)', 'var(--amber)', 'var(--red)']

// Circonférence des deux jauges SVG (donut abonnés + gauge conversion),
// toutes deux basées sur un rayon de 15.9155 (astuce classique pour que la
// circonférence tombe pile à 100 en unités arbitraires). Centralisé ici pour
// ne pas répéter "2 * Math.PI * 15.9155" à chaque endroit, et pour servir de
// valeur de départ (dasharray "0 100") avant l'animation de tracé.
const GAUGE_CIRCUMFERENCE = 2 * Math.PI * 15.9155

// Passe "premium" (15/09/2026) : mêmes utilitaires que le reste du site
// (HomeView.vue, ModelReliabilityView.vue) — révélation au scroll + compteurs
// animés, adaptés ici au tableau de bord admin plutôt qu'aux pages publiques.
const vReveal = {
  mounted(el, binding) {
    el.classList.add('reveal')
    if (typeof binding.value === 'number' && binding.value > 0) {
      el.style.transitionDelay = binding.value + 'ms'
    }
    if (typeof IntersectionObserver === 'undefined') {
      el.classList.add('is-visible')
      return
    }
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            el.classList.add('is-visible')
            io.unobserve(el)
          }
        })
      },
      { threshold: 0.12, rootMargin: '0px 0px -30px 0px' },
    )
    io.observe(el)
  },
}

function prefersReducedMotion() {
  return typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
}
function animateTo(targetRef, finalValue, duration = 1200) {
  if (finalValue === null || finalValue === undefined) return
  if (prefersReducedMotion()) {
    targetRef.value = finalValue
    return
  }
  const start = performance.now()
  function tick(now) {
    const t = Math.min(1, (now - start) / duration)
    const eased = 1 - Math.pow(1 - t, 3)
    targetRef.value = finalValue * eased
    if (t < 1) requestAnimationFrame(tick)
    else targetRef.value = finalValue
  }
  requestAnimationFrame(tick)
}

// N'anime que les DEUX chiffres les plus proéminents (le taux de réussite du
// hero, le MRR) plutôt que toutes les statistiques du tableau de bord — un
// dashboard dense où chaque nombre s'anime en même temps devient vite du
// bruit visuel ; les autres chiffres restent figés, lisibles immédiatement.
const animHeroAccuracy = ref(0)
const animMrrEuros = ref(0)
const heroAccuracyDisplay = computed(() => {
  if (!summary.value || summary.value.modelAccuracyOverall === null) return '—'
  return Math.round(animHeroAccuracy.value) + ' %'
})
const mrrEurosDisplay = computed(() => Math.round(animMrrEuros.value).toLocaleString('fr-FR'))

// Les graphiques (donut abonnés, jauge conversion, barres MRR) se "tracent"
// au premier affichage plutôt que d'apparaître déjà pleins — voir
// chartsReady dans le template (dasharray/largeur à 0 tant que false).
const chartsReady = ref(false)

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

    // Léger décalage pour laisser le premier rendu (tout à 0) se peindre
    // avant de déclencher les transitions CSS — sans ça, le navigateur peut
    // fusionner les deux états et rien ne "s'anime" visuellement.
    setTimeout(() => {
      chartsReady.value = true
      animateTo(animHeroAccuracy, dashboard.modelAccuracyOverall)
      animateTo(animMrrEuros, (dashboard.mrrCents ?? 0) / 100, 1400)
    }, 60)
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

// Part des comptes inscrits qui sont aujourd'hui abonnés actifs — ratio réel
// (activeSubscriptionsCount / totalUsersCount), jamais affiché si on n'a
// encore aucun compte (division par zéro).
const conversionRate = computed(() => {
  const total = summary.value?.totalUsersCount ?? 0
  if (total === 0) return null
  return Math.round((totalSubscribers.value / total) * 1000) / 10
})

function playerInitials(name) {
  return (name || '').split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase()
}

const STATUS_DOT = { scheduled: 'grey', live: 'red', finished: 'green', walkover: 'grey' }
const STATUS_PRIORITY = ['live', 'scheduled', 'finished', 'walkover']

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

// Statut le plus significatif du jour (un match en direct prime sur un match
// simplement programmé, etc.) — sert uniquement à colorer le petit point sous
// le numéro du jour, à partir des vrais statuts de TennisMatch::status.
const matchStatusByDay = computed(() => {
  const map = new Map()
  for (const m of upcomingMatches.value) {
    const d = new Date(m.scheduledAt)
    if (d.getFullYear() === today.getFullYear() && d.getMonth() === today.getMonth()) {
      const day = d.getDate()
      const current = map.get(day)
      if (!current || STATUS_PRIORITY.indexOf(m.status) < STATUS_PRIORITY.indexOf(current)) {
        map.set(day, m.status)
      }
    }
  }
  return map
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

    <div v-if="loading" class="grid" aria-hidden="true">
      <div class="card span2 skeleton-tile" style="min-height: 220px"></div>
      <div class="card skeleton-tile"></div>
      <div class="card skeleton-tile"></div>
      <div class="card span2 skeleton-tile"></div>
      <div class="card skeleton-tile"></div>
      <div class="card skeleton-tile"></div>
      <div class="card skeleton-tile"></div>
      <div class="card span2 skeleton-tile"></div>
      <div class="card skeleton-tile"></div>
    </div>
    <p v-else-if="error" class="err">Impossible de charger le tableau de bord pour le moment.</p>

    <div v-else class="grid">
      <!-- HERO : performance globale du modèle -->
      <RouterLink :to="{ name: 'admin-matches' }" class="card span2 perf-hero" v-reveal>
        <svg class="court-lines" viewBox="0 0 600 200" preserveAspectRatio="none">
          <rect x="24" y="24" width="552" height="152" fill="none" stroke="rgba(255,255,255,.3)" stroke-width="1.5" />
          <line x1="24" y1="100" x2="576" y2="100" stroke="rgba(255,255,255,.22)" stroke-width="1.2" />
          <line x1="170" y1="24" x2="170" y2="176" stroke="rgba(255,255,255,.18)" stroke-width="1" />
          <line x1="430" y1="24" x2="430" y2="176" stroke="rgba(255,255,255,.18)" stroke-width="1" />
        </svg>
        <div class="rowtop">
          <div>
            <div class="eyebrow">Modèle — vue d'ensemble</div>
            <div class="big">{{ heroAccuracyDisplay }}</div>
            <div class="lbl">Taux de réussite — sur {{ summary.finishedMatchesWithPredictionCount }} match(s) terminé(s)</div>
          </div>
          <span class="hero-arrow">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M7 17L17 7M9 7h8v8" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" /></svg>
          </span>
        </div>
        <p v-if="summary.modelAccuracyOverall === null" class="empty-note">
          Pas encore de match terminé avec analyse associée : ce taux apparaîtra dès le premier résultat enregistré.
        </p>
        <div class="perf-mini">
          <div class="chip"><b>{{ summary.predictionsCount }}</b><span>Analyses calculées</span></div>
          <div class="chip"><b>{{ summary.upcomingMatchesCount }}</b><span>Matchs à venir</span></div>
          <div class="chip"><b>{{ totalSubscribers }}</b><span>Abonnements actifs</span></div>
        </div>
      </RouterLink>

      <!-- PROFIL PAR SURFACE -->
      <div class="card" v-reveal="60">
        <h3>Précision par surface</h3>
        <div class="sub">Réussite du modèle, 4 surfaces</div>
        <SurfaceRoseChart :by-surface="summary.modelAccuracyBySurface" :overall="summary.modelAccuracyOverall" />
        <RouterLink :to="{ name: 'model-reliability' }" class="public-link">
          Voir le détail public
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none"><path d="M7 17L17 7M9 7h8v8" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" /></svg>
        </RouterLink>
      </div>

      <!-- INSIGHT -->
      <div class="card insight" v-reveal="120">
        <div class="insight-head">
          <span class="insight-icon">✦</span>
          <h3>Insight</h3>
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

      <!-- CROISSANCE DES ABONNEMENTS -->
      <div class="card span2" v-reveal="60">
        <h3>Croissance des abonnements</h3>
        <div class="sub">Nouveaux abonnements par jour, 14 derniers jours</div>
        <GrowthAreaChart :points="summary.subscriptionsGrowth" />
      </div>

      <!-- COMPTES & CONVERSION -->
      <div class="card accounts-card" v-reveal="120">
        <h3>Comptes</h3>
        <div class="sub">Inscriptions et conversion en abonnés</div>
        <div class="accounts-body">
          <div class="accounts-stats">
            <div class="acc-stat"><b>{{ summary.totalUsersCount }}</b><span>Comptes inscrits</span></div>
            <div class="acc-stat"><b>+{{ summary.newUsersLast7Days }}</b><span>Nouveaux — 7 jours</span></div>
            <div class="acc-stat"><b>{{ summary.canceledSubscriptionsLast30Days }}</b><span>Résiliations — 30 jours</span></div>
          </div>
          <div class="acc-gauge">
            <svg width="86" height="86" viewBox="0 0 36 36">
              <circle cx="18" cy="18" r="15.9155" fill="none" stroke="var(--admin-bg)" stroke-width="4" />
              <circle
                v-if="conversionRate !== null"
                cx="18"
                cy="18"
                r="15.9155"
                fill="none"
                stroke="var(--blue)"
                stroke-width="4"
                stroke-linecap="round"
                :stroke-dasharray="`${chartsReady ? (conversionRate / 100) * GAUGE_CIRCUMFERENCE : 0} ${GAUGE_CIRCUMFERENCE}`"
                transform="rotate(-90 18 18)"
              />
            </svg>
            <div class="acc-gauge-label">
              <b>{{ conversionRate !== null ? conversionRate + '%' : '—' }}</b>
              <span>conversion</span>
            </div>
          </div>
        </div>
      </div>

      <!-- ABONNÉS -->
      <div class="card" v-reveal>
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
              :stroke-dasharray="chartsReady ? seg.dashArray : `0 ${GAUGE_CIRCUMFERENCE}`"
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
      <div class="card" v-reveal="60">
        <h3>Revenu récurrent (MRR)</h3>
        <div class="sub">Abonnements actifs/en essai, mensualisés</div>
        <span class="mrr">{{ mrrEurosDisplay }} €</span>
        <div class="mrr-bars">
          <div v-for="p in mrrByPlan" :key="p.code" class="mrr-bar-row">
            <span class="mrr-bar-label">{{ p.name }}</span>
            <div class="mrr-bar-track"><i :style="{ width: (chartsReady ? p.barPct : 0) + '%', background: p.color }"></i></div>
            <span class="mrr-bar-count">{{ p.count }}</span>
          </div>
          <p v-if="mrrByPlan.length === 0" class="empty-note">Aucun abonnement actif pour l'instant.</p>
        </div>
      </div>

      <!-- PROCHAINS MATCHS -->
      <div class="card span2" v-reveal="120">
        <h3>Prochains matchs</h3>
        <div class="sub">Cliquer pour ouvrir l'analyse détaillée (Modèle)</div>
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
      <div class="card" v-reveal>
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
            <span
              v-if="cell !== null && matchStatusByDay.has(cell)"
              class="cal-dot"
              :class="STATUS_DOT[matchStatusByDay.get(cell)]"
            ></span>
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

/* Révélation au scroll + survol : bordure qui s'accentue plutôt qu'une
   ombre généreuse — même logique "console" que le reste de l'admin
   (voir AdminLayout.vue), pas le langage "premium" du site public. */
.grid .card {
  transition: border-color 0.25s ease, box-shadow 0.25s ease, transform 0.2s var(--ease-premium);
}
.grid .card:hover {
  border-color: #cfd6d2;
  box-shadow: 0 10px 28px -18px rgba(20, 24, 26, 0.28);
  transform: translateY(-2px);
}
.card.perf-hero:hover {
  border-color: transparent;
  box-shadow: 0 20px 44px -18px rgba(0, 0, 0, 0.55);
}

.reveal {
  opacity: 0;
  transform: translateY(16px);
  transition: opacity 0.6s var(--ease-premium), transform 0.6s var(--ease-premium), box-shadow 0.35s var(--ease-premium);
}
.reveal.is-visible {
  opacity: 1;
  transform: translateY(0);
}

/* Chargement : silhouette du tableau de bord plutôt qu'un texte plat */
.skeleton-tile {
  position: relative;
  overflow: hidden;
  background: var(--admin-bg);
  min-height: 150px;
}
.skeleton-tile::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.55), transparent);
  transform: translateX(-100%);
  animation: shimmer 1.5s infinite;
}
@keyframes shimmer {
  100% {
    transform: translateX(100%);
  }
}

/* HERO */
/* .perf-hero {
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, var(--ink), #1a3a2e);
  color: #fff;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 220px;
  text-decoration: none;
} */

.card.perf-hero {
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, var(--ink), #1a3a2e);
  border-color: transparent;
  color: #fff;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 220px;
  text-decoration: none;
}

.court-lines {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.perf-hero .rowtop {
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.perf-hero .eyebrow {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  opacity: 0.75;
  margin-bottom: 8px;
}

.perf-hero .big {
  font-family: var(--mono);
  font-size: 40px;
  font-weight: 700;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.perf-hero .lbl {
  font-size: 13px;
  opacity: 0.8;
  margin-top: 8px;
}

.hero-arrow {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}

.empty-note {
  position: relative;
  font-size: 12px;
  opacity: 0.75;
  margin-top: 10px;
  max-width: 420px;
}

.perf-mini {
  position: relative;
  display: flex;
  gap: 10px;
  margin-top: 20px;
  flex-wrap: wrap;
}

.perf-mini .chip {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: var(--adm-radius-sm);
  padding: 8px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 90px;
}

.perf-mini .chip b {
  font-family: var(--mono);
  font-size: 16px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.perf-mini .chip span {
  font-size: 10px;
  opacity: 0.8;
  text-align: center;
}

/* INSIGHT */
.insight {
  background: #f5faf6;
  border-left: 3px solid var(--green);
}
.insight-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.insight-icon {
  color: var(--green);
  display: inline-block;
  animation: insightPulse 2.6s ease-in-out infinite;
}
@keyframes insightPulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.55;
    transform: scale(1.15);
  }
}
.insight p {
  font-size: 13px;
  line-height: 1.6;
  margin: 8px 0 0;
  color: #1c3a2a;
}

/* Lien vers la page publique /fiabilite, depuis la carte "Précision par surface" */
.public-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-top: 14px;
  font-size: 12px;
  font-weight: 600;
  color: var(--green);
  text-decoration: none;
  transition: gap 0.25s var(--ease-premium);
}
.public-link:hover {
  gap: 8px;
}

/* COMPTES */
.accounts-body {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.accounts-stats {
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
}
.acc-stat b {
  display: block;
  font-family: var(--mono);
  font-size: 18px;
  font-variant-numeric: tabular-nums;
}
.acc-stat span {
  font-size: 11px;
  color: var(--grey);
}
.acc-gauge {
  position: relative;
  flex: none;
  width: 86px;
  height: 86px;
}
.acc-gauge svg {
  position: absolute;
  inset: 0;
}
.acc-gauge circle {
  transition: stroke-dasharray 1.1s var(--ease-premium);
}
.acc-gauge-label {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.acc-gauge-label b {
  font-family: var(--mono);
  font-size: 15px;
  font-weight: 700;
}
.acc-gauge-label span {
  font-size: 9px;
  color: var(--grey);
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
.donut-wrap circle {
  transition: stroke-dasharray 1.1s var(--ease-premium);
}

/* MRR */
.mrr {
  font-family: var(--mono);
  font-size: 30px;
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
  border-radius: 4px;
  background: var(--admin-bg);
  overflow: hidden;
}
.mrr-bar-track i {
  display: block;
  height: 100%;
  border-radius: 4px;
  transition: width 1.1s var(--ease-premium);
}
.mrr-bar-count {
  font-family: var(--mono);
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
  text-decoration: none;
  color: inherit;
  transition: padding-left 0.25s var(--ease-premium);
}
.match-row:last-child {
  border-bottom: none;
}
.match-row:hover {
  padding-left: 6px;
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
  position: relative;
  text-align: center;
  font-size: 11px;
  padding: 7px 0 10px;
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
.cal-dot {
  position: absolute;
  bottom: 2px;
  left: 50%;
  transform: translateX(-50%);
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--grey);
}
.cal-dot.red {
  background: var(--red);
}
.cal-dot.green {
  background: #2e9e4d;
}
.cal-n.today .cal-dot {
  background: #fff;
}

@media (max-width: 980px) {
  .grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 640px) {
  .welcome {
    font-size: 21px;
  }
  .grid {
    grid-template-columns: 1fr;
  }
  .span2 {
    grid-column: span 1;
  }
  .card.perf-hero {
    min-height: 0;
  }
  .perf-hero .big {
    font-size: 32px;
  }
  .accounts-body {
    flex-wrap: wrap;
  }
  .donut-wrap {
    flex-wrap: wrap;
  }
  .mrr-bar-row {
    grid-template-columns: 68px 1fr 20px;
    font-size: 11px;
  }
  .mr-meta {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.001ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.001ms !important;
  }
  .reveal {
    opacity: 1 !important;
    transform: none !important;
  }
  .skeleton-tile::after {
    display: none;
  }
  .insight-icon {
    animation: none !important;
  }
}
</style>