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
//
// Refonte "sombre / technique" (15/09/2026) : nouvelle direction visuelle
// demandée explicitement (thème sombre façon terminal/dashboard de données,
// typographie monospace pour les chiffres et libellés) — même contenu et
// mêmes données, présentation entièrement revue. Les autres pages du site
// restent en thème clair ; cette page seule bascule en sombre (tokens CSS
// redéfinis localement, voir <style>).
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
    // Léger décalage pour démarrer le compteur pile quand .readout entre
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
  <div class="reliability-page">
    <div class="rb-grid" aria-hidden="true"></div>
    <div class="rb-glow" aria-hidden="true"></div>

    <div class="reliability">
      <section class="hero">
        <div class="term-tag"><span class="prompt">&gt;</span>fiabilite_du_modele<span class="cursor">_</span></div>
        <h1>Un modèle qu'on peut <span class="accent">vérifier</span>, pas une boîte noire</h1>
        <p class="lead">
          Chaque chiffre de cette page vient de la comparaison réelle entre ce que notre modèle a annoncé et ce qui
          s'est effectivement passé, sur les matchs déjà terminés. Pas d'exemple choisi, pas de moyenne habillée : soit
          l'échantillon existe et le chiffre est là, soit il n'existe pas encore et on l'affiche tel quel.
        </p>

        <div v-if="!loading && !error" class="readout">
          <div class="readout-bar">
            <span class="readout-live"><i></i>live</span>
            <span class="readout-path">reliability_report.log</span>
          </div>
          <div class="readout-body">
            <div class="readout-stat">
              <div class="rs-value">{{ heroAccuracy }}</div>
              <div class="rs-label"># taux_de_reussite_global</div>
            </div>
            <div class="readout-sep" aria-hidden="true"></div>
            <div class="readout-stat">
              <div class="rs-value">{{ heroMatchesCount }}</div>
              <div class="rs-label"># matchs_termines_analyses</div>
            </div>
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
            <div class="block-head">
              <span class="block-tag">surface_matrix</span>
              <h2>Précision par surface</h2>
            </div>
            <p class="sub">
              Le modèle est-il aussi fiable sur terre battue que sur dur ? Chaque surface a son propre historique, donc
              sa propre fiabilité mesurée séparément.
            </p>
            <SurfaceRoseChart :by-surface="summary.accuracyBySurface" :overall="summary.overallAccuracy" />
          </section>

          <section class="block" v-reveal="80">
            <div class="block-head">
              <span class="block-tag">calibration_log</span>
              <h2>Calibration : la confiance annoncée correspond-elle au résultat réel ?</h2>
            </div>
            <p class="sub">
              Quand le modèle annonce "70 % de confiance" pour un joueur, ce joueur devrait effectivement gagner
              environ 70 % du temps sur un grand nombre de cas. Ce tableau compare, tranche par tranche, la confiance
              moyenne annoncée à la victoire réelle du favori.
            </p>

            <div class="calibration">
              <div class="calibration-head">
                <span>confiance</span>
                <span>résultat réel</span>
                <span>échantillon</span>
              </div>
              <div v-for="bucket in summary.calibrationBuckets" :key="bucket.rangeLabel" class="calibration-row">
                <span class="range-label">{{ bucket.rangeLabel }}</span>
                <div class="bars" v-if="bucket.sampleSize > 0">
                  <div class="bar-track">
                    <div class="bar predicted" :style="{ width: bucket.predictedAvg + '%' }"></div>
                    <span class="bar-value">{{ bucket.predictedAvg }}%</span>
                  </div>
                  <div class="bar-track">
                    <div class="bar actual" :style="{ width: bucket.actualWinRate + '%' }"></div>
                    <span class="bar-value">{{ bucket.actualWinRate }}%</span>
                  </div>
                </div>
                <span v-else class="no-data">pas encore de match</span>
                <span class="sample" :class="{ low: bucket.sampleSize > 0 && bucket.sampleSize < LOW_SAMPLE_THRESHOLD }">
                  {{ bucket.sampleSize }}
                  <span v-if="bucket.sampleSize > 0 && bucket.sampleSize < LOW_SAMPLE_THRESHOLD" class="warn-tag">faible</span>
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
          <div class="term-tag"><span class="prompt">&gt;</span>methode<span class="cursor">_</span></div>
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
          // ces analyses sont un outil d'aide à la compréhension du jeu, pas une garantie de résultat — aucune
          analyse, aussi fiable soit-elle historiquement, ne prédit un match individuel avec certitude.
        </p>
      </section>
    </div>
  </div>
</template>

<style scoped>
/* ------------------------------------------------------------------
   Thème local "sombre / technique" — tokens redéfinis uniquement pour
   cette page (aucun impact sur le reste du site, qui reste en thème
   clair). SurfaceRoseChart.vue (composant partagé) lit ses couleurs via
   ces mêmes tokens (--ink, --grey, --admin-bg, --admin-card...), donc
   il hérite automatiquement du thème sombre ici sans être modifié.
   ------------------------------------------------------------------ */
.reliability-page {
  --ink: #eef6f3;
  --grey: #7e948f;
  --line: rgba(255, 255, 255, 0.1);
  --card: #10171a;
  --admin-bg: rgba(255, 255, 255, 0.12);
  --admin-card: #10171a;
  --green: #8dffc9;
  --blue: #4da8ff;
  --amber: #ffb545;
  --red: #ff6b5e;
  --mono: 'JetBrains Mono', ui-monospace, 'SFMono-Regular', Menlo, Consolas, monospace;

  position: relative;
  width: 100vw;
  left: 50%;
  right: 50%;
  margin-left: -50vw;
  margin-right: -50vw;
  margin-top: -1px;
  background: #05090a;
  overflow-x: clip;
}

/* Texture de fond : grille pointillée très discrète, façon papier
   millimétré, pour renforcer la lecture "outil de données". */
.rb-grid {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background-image: radial-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px);
  background-size: 24px 24px;
  mask-image: linear-gradient(to bottom, rgba(0, 0, 0, 0.9), transparent 85%);
}
.rb-glow {
  position: absolute;
  top: -120px;
  left: 50%;
  transform: translateX(-50%);
  width: 900px;
  max-width: 140vw;
  height: 460px;
  z-index: 0;
  pointer-events: none;
  background: radial-gradient(circle, rgba(199, 255, 60, 0.16), transparent 68%);
  filter: blur(10px);
}

.reliability {
  position: relative;
  z-index: 1;
  max-width: 900px;
  margin: 0 auto;
  padding: 64px 32px 90px;
  color: var(--ink);
}

/* -- Étiquette façon invite de terminal ("> texte_") -- */
.term-tag {
  display: inline-flex;
  align-items: baseline;
  gap: 2px;
  font-family: var(--mono);
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.01em;
  color: var(--grey);
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 7px 12px;
  margin: 0 0 22px;
}
.term-tag .prompt {
  color: var(--lime);
  margin-right: 7px;
  font-weight: 700;
}
.term-tag .cursor {
  color: var(--lime);
  animation: blink 1.1s step-end infinite;
}
@keyframes blink {
  50% {
    opacity: 0;
  }
}

.hero {
  position: relative;
  text-align: center;
  margin-bottom: 48px;
}
.hero .term-tag {
  justify-content: center;
}

.hero h1 {
  font-size: 34px;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.15;
  margin: 0 0 16px;
  text-wrap: balance;
  color: var(--ink);
}
.hero h1 .accent {
  background: linear-gradient(90deg, var(--lime), #34e8b0);
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

/* -- Bloc "readout" du hero : cadre façon terminal, chiffres en mono -- */
.readout {
  display: inline-block;
  text-align: left;
  margin-top: 36px;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 24px 48px -16px rgba(0, 0, 0, 0.55);
  animation: fadeUp 0.7s var(--ease-premium) both;
  animation-delay: 0.15s;
}
.readout-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 9px 16px;
  background: rgba(255, 255, 255, 0.03);
  border-bottom: 1px solid var(--line);
  font-family: var(--mono);
  font-size: 11px;
}
.readout-live {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--lime);
  text-transform: uppercase;
  font-weight: 700;
  letter-spacing: 0.06em;
}
.readout-live i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--lime);
  box-shadow: 0 0 0 3px rgba(199, 255, 60, 0.22);
  animation: pulse 2.4s ease-in-out infinite;
}
@keyframes pulse {
  0%,
  100% {
    box-shadow: 0 0 0 3px rgba(199, 255, 60, 0.22);
  }
  50% {
    box-shadow: 0 0 0 6px rgba(199, 255, 60, 0.1);
  }
}
.readout-path {
  color: var(--grey);
}

.readout-body {
  display: flex;
  align-items: center;
  gap: 30px;
  padding: 22px 30px;
}
.readout-stat {
  text-align: center;
}
.rs-value {
  font-family: var(--mono);
  font-size: 34px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.01em;
  color: var(--ink);
  text-shadow: 0 0 24px rgba(199, 255, 60, 0.18);
}
.rs-label {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--grey);
  margin-top: 6px;
}
.readout-sep {
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

/* -- Squelette de chargement -- */
.skeleton-block {
  position: relative;
  z-index: 1;
}
.skeleton-tile {
  position: relative;
  overflow: hidden;
  border-radius: 14px;
  background: var(--card);
  border: 1px solid var(--line);
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
  background: linear-gradient(100deg, transparent 30%, rgba(255, 255, 255, 0.06) 50%, transparent 70%);
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
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 28px;
  margin-bottom: 24px;
  transition:
    box-shadow 0.35s var(--ease-premium),
    transform 0.35s var(--ease-premium),
    border-color 0.35s ease;
}
.block:hover {
  box-shadow: 0 24px 48px -16px rgba(0, 0, 0, 0.6);
  transform: translateY(-2px);
  border-color: rgba(255, 255, 255, 0.18);
}

.block-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}
.block-tag {
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--lime);
  background: rgba(199, 255, 60, 0.1);
  border: 1px solid rgba(199, 255, 60, 0.25);
  border-radius: 6px;
  padding: 3px 8px;
  text-transform: lowercase;
}

.block h2 {
  font-size: 18px;
  margin: 0;
  color: var(--ink);
}

.block .sub {
  font-size: 13px;
  color: var(--grey);
  line-height: 1.6;
  margin: 10px 0 20px;
  max-width: 560px;
}

.calibration-head {
  display: grid;
  grid-template-columns: 90px 1fr 100px;
  gap: 16px;
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--grey);
  padding-bottom: 10px;
  border-bottom: 1px solid var(--line);
}

.calibration-row {
  display: grid;
  grid-template-columns: 90px 1fr 100px;
  gap: 16px;
  align-items: center;
  padding: 14px 10px;
  margin: 0 -10px;
  border-radius: 10px;
  border-bottom: 1px solid var(--line);
  transition: background 0.25s ease;
}
.calibration-row:hover {
  background: rgba(255, 255, 255, 0.035);
}

.calibration-row:last-child {
  border-bottom: none;
}

.range-label {
  font-family: var(--mono);
  font-weight: 600;
  font-size: 13px;
  color: var(--ink);
}

.bars {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.bar-track {
  position: relative;
  height: 18px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 4px;
  overflow: hidden;
}

.bar {
  height: 100%;
  border-radius: 4px;
  transition: width 1s var(--ease-premium);
}

.bar.predicted {
  background: var(--blue);
}

.bar.actual {
  background: var(--lime);
}

.bar-value {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 700;
  color: #04110b;
}

.no-data {
  font-family: var(--mono);
  font-size: 12px;
  color: var(--grey);
  font-style: italic;
}

.sample {
  font-family: var(--mono);
  font-size: 12px;
  color: var(--grey);
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.warn-tag {
  display: inline-block;
  margin-left: 6px;
  font-family: var(--mono);
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--amber);
  background: rgba(255, 181, 69, 0.14);
  border: 1px solid rgba(255, 181, 69, 0.3);
  border-radius: 5px;
  padding: 1px 5px;
}

.legend {
  display: flex;
  gap: 20px;
  margin-top: 16px;
  font-family: var(--mono);
  font-size: 11px;
  color: var(--grey);
  flex-wrap: wrap;
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
  background: var(--lime);
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
.method-head .term-tag {
  justify-content: center;
}

.method h2 {
  font-size: 22px;
  margin: 0 0 8px;
  text-wrap: balance;
  color: var(--ink);
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
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 24px;
  transition:
    box-shadow 0.35s var(--ease-premium),
    transform 0.35s var(--ease-premium),
    border-color 0.35s ease;
}
.pillar-card:hover {
  box-shadow: 0 24px 48px -16px rgba(0, 0, 0, 0.6);
  transform: translateY(-3px);
  border-color: rgba(199, 255, 60, 0.3);
}

.pillar-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: rgba(199, 255, 60, 0.12);
  color: var(--lime);
  margin-bottom: 14px;
}

.pillar-card h3 {
  font-size: 15px;
  margin: 0 0 6px;
  text-wrap: balance;
  color: var(--ink);
}

.pillar-card p {
  font-size: 13px;
  color: var(--grey);
  line-height: 1.6;
  margin: 0;
}

.disclaimer {
  font-family: var(--mono);
  font-size: 12px;
  color: var(--grey);
  text-align: center;
  max-width: 640px;
  margin: 0 auto;
  line-height: 1.6;
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

/* -- Révélation au scroll (v-reveal) -- */
.reveal {
  opacity: 0;
  transform: translateY(26px);
  filter: blur(6px);
  transition:
    opacity 0.7s var(--ease-premium),
    transform 0.6s var(--ease-premium),
    filter 0.6s var(--ease-premium),
    box-shadow 0.3s ease,
    border-color 0.3s ease;
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
  .term-tag .cursor {
    animation: none !important;
    opacity: 1 !important;
  }
}

@media (max-width: 860px) {
  .reliability {
    padding: 56px 20px 70px;
  }
}

@media (max-width: 720px) {
  .hero h1 {
    font-size: 26px;
  }
  .readout {
    width: 100%;
  }
  .readout-body {
    padding: 20px 18px;
    gap: 18px;
  }
  .rs-value {
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
  .reliability {
    padding: 40px 16px 60px;
  }
  .readout-body {
    flex-direction: column;
    gap: 14px;
  }
  .readout-sep {
    display: none;
  }
}
</style>
