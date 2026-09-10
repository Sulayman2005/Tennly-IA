<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '@/api/client'
import SurfaceRoseChart from '@/components/admin/SurfaceRoseChart.vue'

// Page publique "Fiabilité du modèle" — accessible sans connexion, contrairement
// à la fiche match détaillée. Le but est de convaincre un visiteur non-abonné
// avec des chiffres vérifiables (voir GET /api/model-reliability, backend
// ModelReliabilityProvider) plutôt qu'avec une promesse marketing. Aucune
// donnée ici n'est inventée : un agrégat non calculable (échantillon nul)
// vaut `null` et s'affiche comme "pas encore assez de données".
//
// Redesign "premium" (10/09/2026) : on ne montre plus le champ technique
// `modelVersion` (ex. "xgboost-v1") — un identifiant de build interne n'aide
// en rien un visiteur à juger la fiabilité, et l'ancienne carte KPI dédiée
// est retirée du template. Le champ reste renvoyé par l'API (aucun changement
// backend nécessaire), il n'est simplement plus affiché ici.
const summary = ref(null)
const loading = ref(true)
const error = ref(null)

// En dessous de ce seuil, on affiche quand même le vrai chiffre calculé mais
// avec une mention explicite "échantillon faible" — jamais en le masquant.
const LOW_SAMPLE_THRESHOLD = 5

// Révélation au scroll — même langage visuel (fondu + léger déplacement vers
// le haut + flou) que HomeView.vue et MatchesView.vue, pour que cette page
// s'inscrive dans la même passe "rendu premium" plutôt que de rester figée
// dans l'ancien style.
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
      { threshold: 0.15, rootMargin: '0px 0px -40px 0px' },
    )
    io.observe(el)
  },
}

function prefersReducedMotion() {
  return typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
}

// Compteurs animés (même utilitaire que HomeView.vue) : la cible est toujours
// exactement la valeur réelle reçue de l'API — jamais un chiffre inventé, on
// anime seulement l'ARRIVÉE de la vraie donnée.
function animateTo(targetRef, finalValue, duration = 1300) {
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
const animAccuracy = ref(0)
const animMatchesCount = ref(0)

const heroAccuracy = computed(() => {
  if (!summary.value || summary.value.overallAccuracy === null) return '—'
  return animAccuracy.value.toFixed(1).replace('.', ',') + ' %'
})
const heroMatchesCount = computed(() => {
  if (!summary.value) return '—'
  return new Intl.NumberFormat('fr-FR').format(Math.round(animMatchesCount.value))
})

onMounted(async () => {
  try {
    summary.value = await api.get('/api/model-reliability')
    // Léger décalage pour démarrer le compteur pile quand .hero-stats entre
    // en scène (voir animation-delay côté CSS) plutôt qu'avant, invisible.
    setTimeout(() => {
      animateTo(animAccuracy, summary.value.overallAccuracy)
      animateTo(animMatchesCount, summary.value.finishedMatchesWithPredictionCount, 1600)
    }, 300)
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="reliability">
    <div class="hero-glow" aria-hidden="true">
      <span class="blob blob-a"></span>
      <span class="blob blob-b"></span>
      <span class="blob blob-c"></span>
    </div>

    <section class="hero">
      <div class="eyebrow"><i></i>FIABILITÉ DU MODÈLE</div>
      <h1>Un modèle qu'on peut <span class="accent">vérifier</span>, pas une boîte noire</h1>
      <p class="lead">
        Chaque chiffre de cette page vient de la comparaison réelle entre ce que notre modèle a annoncé et ce qui
        s'est effectivement passé, sur les matchs déjà terminés. Pas d'exemple choisi, pas de moyenne habillée : soit
        l'échantillon existe et le chiffre est là, soit il n'existe pas encore et on l'affiche tel quel.
      </p>

      <div v-if="!loading && !error" class="hero-stats">
        <div class="hero-stat">
          <div class="hs-value">{{ heroAccuracy }}</div>
          <div class="hs-label">Taux de réussite global</div>
        </div>
        <div class="hero-stat-sep" aria-hidden="true"></div>
        <div class="hero-stat">
          <div class="hs-value">{{ heroMatchesCount }}</div>
          <div class="hs-label">Matchs terminés analysés</div>
        </div>
      </div>
    </section>

    <div v-if="loading" class="skeleton-block" aria-hidden="true">
      <div class="skeleton-tile skeleton-hero"></div>
      <div class="skeleton-row">
        <div class="skeleton-tile"></div>
        <div class="skeleton-tile"></div>
      </div>
    </div>
    <p v-else-if="error" class="state-msg error">Impossible de charger les statistiques de fiabilité pour le moment.</p>

    <template v-else>
      <p v-if="summary.finishedMatchesWithPredictionCount === 0" v-reveal class="empty-note">
        Aucun match terminé avec une analyse associée pour l'instant — ces statistiques apparaîtront dès les premiers
        résultats enregistrés.
      </p>

      <template v-else>
        <section class="block" v-reveal>
          <h2>Précision par surface</h2>
          <p class="sub">
            Le modèle est-il aussi fiable sur terre battue que sur dur ? Chaque surface a son propre historique, donc
            sa propre fiabilité mesurée séparément.
          </p>
          <SurfaceRoseChart :by-surface="summary.accuracyBySurface" :overall="summary.overallAccuracy" />
        </section>

        <section class="block" v-reveal="80">
          <h2>Calibration : la confiance annoncée correspond-elle au résultat réel ?</h2>
          <p class="sub">
            Quand le modèle annonce "70 % de confiance" pour un joueur, ce joueur devrait effectivement gagner
            environ 70 % du temps sur un grand nombre de cas. Ce tableau compare, tranche par tranche, la confiance
            moyenne annoncée à la victoire réelle du favori.
          </p>

          <div class="calibration">
            <div class="calibration-head">
              <span>Confiance annoncée</span>
              <span>Résultat réel</span>
              <span>Échantillon</span>
            </div>
            <div v-for="bucket in summary.calibrationBuckets" :key="bucket.rangeLabel" class="calibration-row">
              <span class="range-label">{{ bucket.rangeLabel }}</span>
              <div class="bars" v-if="bucket.sampleSize > 0">
                <div class="bar-track">
                  <div class="bar predicted" :style="{ width: bucket.predictedAvg + '%' }"></div>
                  <span class="bar-value">{{ bucket.predictedAvg }} %</span>
                </div>
                <div class="bar-track">
                  <div class="bar actual" :style="{ width: bucket.actualWinRate + '%' }"></div>
                  <span class="bar-value">{{ bucket.actualWinRate }} %</span>
                </div>
              </div>
              <span v-else class="no-data">Pas encore de match dans cette tranche</span>
              <span class="sample" :class="{ low: bucket.sampleSize > 0 && bucket.sampleSize < LOW_SAMPLE_THRESHOLD }">
                {{ bucket.sampleSize }} match(s)
                <template v-if="bucket.sampleSize > 0 && bucket.sampleSize < LOW_SAMPLE_THRESHOLD">— échantillon faible</template>
              </span>
            </div>
          </div>

          <div class="legend">
            <span><i class="dot predicted"></i>Confiance annoncée par le modèle</span>
            <span><i class="dot actual"></i>Victoire réelle du favori</span>
          </div>
        </section>
      </template>
    </template>

    <section class="method" v-reveal="120">
      <div class="method-head">
        <div class="eyebrow"><i></i>MÉTHODE</div>
        <h2>Comment ces analyses sont calculées</h2>
        <p class="sub">Trois principes, appliqués sans exception, pour que chaque chiffre plus haut reste vérifiable.</p>
      </div>

      <div class="pillar-row">
        <div class="pillar-card" v-reveal="0">
          <span class="pillar-icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M4 19V10M10 19V5M16 19V13M22 19V8" stroke="currentColor" stroke-width="2" stroke-linecap="round" /></svg>
          </span>
          <h3>Un Elo réel, par joueur et par surface</h3>
          <p>Recalculé chronologiquement sur l'historique ATP — jamais une estimation générique.</p>
        </div>
        <div class="pillar-card" v-reveal="90">
          <span class="pillar-icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M3 12h4l2.5 7L13 5l2.5 7H21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" /></svg>
          </span>
          <h3>De vraies statistiques de jeu</h3>
          <p>Aces, pourcentage de premier service, balles de break — extraites des scores réels, jamais de moyennes de circuit.</p>
        </div>
        <div class="pillar-card" v-reveal="180">
          <span class="pillar-icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M3 3l18 18M10.6 10.6a3 3 0 004.24 4.24M9.9 4.24A9.5 9.5 0 0112 4c5 0 9 4 10 8-.3 1.1-.86 2.2-1.6 3.2M6.1 6.1C4.1 7.5 2.6 9.6 2 12c.6 2 2 3.9 3.9 5.3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" /></svg>
          </span>
          <h3>Le silence plutôt que l'invention</h3>
          <p>Quand l'échantillon est trop petit pour un signal donné, il n'apparaît simplement pas dans l'analyse.</p>
        </div>
      </div>

      <p class="disclaimer">
        Ces analyses sont un outil d'aide à la compréhension du jeu, pas une garantie de résultat — aucune analyse,
        aussi fiable soit-elle historiquement, ne prédit un match individuel avec certitude.
      </p>
    </section>
  </div>
</template>

<style scoped>
.reliability {
  position: relative;
  max-width: 900px;
  margin: 0 auto;
  padding: 48px 0 80px;
  overflow-x: clip;
}

/* -- Halo décoratif du hero (même langage que MatchesView.vue) -- */
.hero-glow {
  position: absolute;
  top: -60px;
  left: -10%;
  right: -10%;
  height: 340px;
  z-index: 0;
  overflow: hidden;
  pointer-events: none;
}
.blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  opacity: 0.32;
  animation: drift 16s ease-in-out infinite;
}
.blob-a {
  width: 300px;
  height: 300px;
  top: -70px;
  left: 6%;
  background: radial-gradient(circle, var(--lime), transparent 70%);
  --drift-x: 26px;
  --drift-y: 12px;
}
.blob-b {
  width: 260px;
  height: 260px;
  top: -30px;
  right: 10%;
  background: radial-gradient(circle, var(--blue), transparent 70%);
  animation-duration: 20s;
  animation-delay: -4s;
  --drift-x: -22px;
  --drift-y: 18px;
}
.blob-c {
  width: 220px;
  height: 220px;
  top: 60px;
  left: 42%;
  background: radial-gradient(circle, var(--clay), transparent 70%);
  animation-duration: 18s;
  animation-delay: -9s;
  --drift-x: -16px;
  --drift-y: -14px;
}
@keyframes drift {
  0% {
    transform: translate(0, 0) scale(1);
  }
  50% {
    transform: translate(var(--drift-x, 24px), var(--drift-y, -18px)) scale(1.08);
  }
  100% {
    transform: translate(0, 0) scale(1);
  }
}

.hero {
  position: relative;
  z-index: 1;
  text-align: center;
  margin-bottom: 44px;
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--green);
  margin: 0 0 14px;
}
.eyebrow i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--lime);
  box-shadow: 0 0 0 3px rgba(199, 255, 60, 0.25);
  animation: pulse 2.4s ease-in-out infinite;
}
@keyframes pulse {
  0%,
  100% {
    box-shadow: 0 0 0 3px rgba(199, 255, 60, 0.25);
  }
  50% {
    box-shadow: 0 0 0 6px rgba(199, 255, 60, 0.12);
  }
}

.hero h1 {
  font-size: 34px;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.15;
  margin: 0 0 16px;
  text-wrap: balance;
}
.hero h1 .accent {
  background: linear-gradient(90deg, var(--green), #1f8a6b);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.lead {
  font-size: 15px;
  color: var(--grey);
  line-height: 1.7;
  max-width: 620px;
  margin: 0 auto;
}

.hero-stats {
  display: inline-flex;
  align-items: center;
  gap: 28px;
  margin-top: 36px;
  padding: 22px 40px;
  background: var(--card);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-soft);
  animation: fadeUp 0.7s var(--ease-premium) both;
  animation-delay: 0.15s;
}
.hero-stat {
  text-align: center;
}
.hs-value {
  font-size: 32px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.01em;
}
.hs-label {
  font-size: 12px;
  color: var(--grey);
  margin-top: 4px;
}
.hero-stat-sep {
  width: 1px;
  align-self: stretch;
  background: var(--line);
}

.state-msg {
  position: relative;
  z-index: 1;
  text-align: center;
  color: var(--grey);
  font-size: 14px;
  padding: 12px 0;
}
.state-msg.error {
  color: var(--red);
}

.empty-note {
  text-align: center;
  color: var(--grey);
  font-size: 14px;
  padding: 20px;
}

/* -- Squelette de chargement (même langage que MatchesView.vue) -- */
.skeleton-block {
  position: relative;
  z-index: 1;
}
.skeleton-tile {
  position: relative;
  overflow: hidden;
  border-radius: var(--radius-card);
  background: var(--card);
  animation: fadeUp 0.4s ease both;
}
.skeleton-tile.skeleton-hero {
  height: 96px;
  margin: 0 0 16px;
}
.skeleton-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.skeleton-row .skeleton-tile {
  height: 220px;
}
.skeleton-tile::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(100deg, transparent 30%, rgba(255, 255, 255, 0.7) 50%, transparent 70%);
  transform: translateX(-100%);
  animation: skeletonShimmer 1.6s ease-in-out infinite;
}
@keyframes skeletonShimmer {
  to {
    transform: translateX(100%);
  }
}

.block {
  position: relative;
  z-index: 1;
  background: var(--card);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-soft);
  padding: 28px;
  margin-bottom: 24px;
  transition:
    box-shadow 0.35s var(--ease-premium),
    transform 0.35s var(--ease-premium);
}
.block:hover {
  box-shadow: var(--shadow-elevated);
  transform: translateY(-2px);
}

.block h2 {
  font-size: 18px;
  margin: 0 0 6px;
}

.block .sub {
  font-size: 13px;
  color: var(--grey);
  line-height: 1.6;
  margin-bottom: 20px;
  max-width: 560px;
}

.calibration-head {
  display: grid;
  grid-template-columns: 90px 1fr 150px;
  gap: 16px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  color: var(--grey);
  padding-bottom: 10px;
  border-bottom: 1px solid var(--line);
}

.calibration-row {
  display: grid;
  grid-template-columns: 90px 1fr 150px;
  gap: 16px;
  align-items: center;
  padding: 14px 10px;
  margin: 0 -10px;
  border-radius: 12px;
  border-bottom: 1px solid var(--line);
  transition: background 0.25s ease;
}
.calibration-row:hover {
  background: rgba(15, 61, 62, 0.04);
}

.calibration-row:last-child {
  border-bottom: none;
}

.range-label {
  font-weight: 700;
  font-size: 13px;
}

.bars {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.bar-track {
  position: relative;
  height: 18px;
  background: var(--admin-bg, #f2f3f5);
  border-radius: 999px;
  overflow: hidden;
}

.bar {
  height: 100%;
  border-radius: 999px;
  transition: width 1s var(--ease-premium);
}

.bar.predicted {
  background: var(--blue);
}

.bar.actual {
  background: var(--green);
}

.bar-value {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 10px;
  font-weight: 700;
  color: #fff;
}

.no-data {
  font-size: 12px;
  color: var(--grey);
  font-style: italic;
}

.sample {
  font-size: 11px;
  color: var(--grey);
  text-align: right;
}

.sample.low {
  color: var(--amber);
}

.legend {
  display: flex;
  gap: 20px;
  margin-top: 16px;
  font-size: 12px;
  color: var(--grey);
}

.legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  display: inline-block;
}

.dot.predicted {
  background: var(--blue);
}

.dot.actual {
  background: var(--green);
}

.method {
  position: relative;
  z-index: 1;
  padding: 36px 0 0;
}

.method-head {
  text-align: center;
  max-width: 560px;
  margin: 0 auto 28px;
}
.method-head .eyebrow {
  justify-content: center;
}

.method h2 {
  font-size: 22px;
  margin: 0 0 8px;
  text-wrap: balance;
}

.method .sub {
  font-size: 13px;
  color: var(--grey);
  line-height: 1.6;
  margin: 0;
}

.pillar-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 28px;
}

.pillar-card {
  background: var(--card);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-soft);
  padding: 24px;
  transition:
    box-shadow 0.35s var(--ease-premium),
    transform 0.35s var(--ease-premium);
}
.pillar-card:hover {
  box-shadow: var(--shadow-elevated);
  transform: translateY(-3px);
}

.pillar-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(199, 255, 60, 0.22), rgba(15, 61, 62, 0.08));
  color: var(--green);
  margin-bottom: 14px;
}

.pillar-card h3 {
  font-size: 15px;
  margin: 0 0 6px;
  text-wrap: balance;
}

.pillar-card p {
  font-size: 13px;
  color: var(--grey);
  line-height: 1.6;
  margin: 0;
}

.disclaimer {
  font-style: italic;
  font-size: 12px;
  color: var(--grey);
  text-align: center;
  max-width: 620px;
  margin: 0 auto;
}

@keyframes fadeUp {
  from {
    opacity: 0;
    transform: translateY(18px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* -- Révélation au scroll (v-reveal) — même langage que HomeView.vue -- */
.reveal {
  opacity: 0;
  transform: translateY(26px);
  filter: blur(6px);
  transition:
    opacity 0.7s var(--ease-premium),
    transform 0.6s var(--ease-premium),
    filter 0.6s var(--ease-premium),
    box-shadow 0.3s ease,
    background 0.3s ease;
}
.reveal.is-visible {
  opacity: 1;
  transform: none;
  filter: blur(0);
}

@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.001ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.001ms !important;
  }
  .blob {
    animation: none !important;
  }
}

@media (max-width: 720px) {
  .reliability {
    padding: 32px 0 60px;
  }
  .hero h1 {
    font-size: 26px;
  }
  .hero-stats {
    width: 100%;
    padding: 20px 16px;
    gap: 16px;
  }
  .hs-value {
    font-size: 26px;
  }
  .block {
    padding: 22px 18px;
  }
  .calibration-head {
    display: none;
  }
  .calibration-row {
    grid-template-columns: 1fr;
    gap: 8px;
    padding: 16px 10px;
  }
  .sample {
    text-align: left;
  }
  .pillar-row {
    grid-template-columns: 1fr;
  }
  .skeleton-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 480px) {
  .hero-stats {
    flex-direction: column;
    gap: 14px;
  }
  .hero-stat-sep {
    display: none;
  }
}
</style>
