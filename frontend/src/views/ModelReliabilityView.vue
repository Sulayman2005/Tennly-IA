<script setup>
import { ref, onMounted } from 'vue'
import { api } from '@/api/client'
import SurfaceRoseChart from '@/components/admin/SurfaceRoseChart.vue'

// Page publique "Fiabilité du modèle" — accessible sans connexion, contrairement
// à la fiche match détaillée. Le but est de convaincre un visiteur non-abonné
// avec des chiffres vérifiables (voir GET /api/model-reliability, backend
// ModelReliabilityProvider) plutôt qu'avec une promesse marketing. Aucune
// donnée ici n'est inventée : un agrégat non calculable (échantillon nul)
// vaut `null` et s'affiche comme "pas encore assez de données".
const summary = ref(null)
const loading = ref(true)
const error = ref(null)

// En dessous de ce seuil, on affiche quand même le vrai chiffre calculé mais
// avec une mention explicite "échantillon faible" — jamais en le masquant.
const LOW_SAMPLE_THRESHOLD = 5

onMounted(async () => {
  try {
    summary.value = await api.get('/api/model-reliability')
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="reliability">
    <section class="hero">
      <div class="eyebrow">Fiabilité du modèle</div>
      <h1>Une IA qu'on peut vérifier, pas une boîte noire</h1>
      <p class="lead">
        Chaque chiffre de cette page vient de la comparaison réelle entre ce que notre modèle a annoncé et ce qui
        s'est effectivement passé, sur les matchs déjà terminés. Pas d'exemple choisi, pas de moyenne habillée : soit
        l'échantillon existe et le chiffre est là, soit il n'existe pas encore et on l'affiche tel quel.
      </p>
    </section>

    <p v-if="loading" class="state">Chargement des statistiques…</p>
    <p v-else-if="error" class="state err">Impossible de charger les statistiques de fiabilité pour le moment.</p>

    <template v-else>
      <section class="kpis">
        <div class="kpi">
          <div class="kpi-value">{{ summary.overallAccuracy !== null ? summary.overallAccuracy + ' %' : '—' }}</div>
          <div class="kpi-label">Taux de réussite global</div>
        </div>
        <div class="kpi">
          <div class="kpi-value">{{ summary.finishedMatchesWithPredictionCount }}</div>
          <div class="kpi-label">Matchs terminés analysés</div>
        </div>
        <div class="kpi">
          <div class="kpi-value">{{ summary.modelVersion ?? '—' }}</div>
          <div class="kpi-label">Version du modèle</div>
        </div>
      </section>

      <p v-if="summary.finishedMatchesWithPredictionCount === 0" class="empty-note">
        Aucun match terminé avec une analyse associée pour l'instant — ces statistiques apparaîtront dès les premiers
        résultats enregistrés.
      </p>

      <template v-else>
        <section class="block">
          <h2>Précision par surface</h2>
          <p class="sub">
            Le modèle est-il aussi fiable sur terre battue que sur dur ? Chaque surface a son propre historique, donc
            sa propre fiabilité mesurée séparément.
          </p>
          <SurfaceRoseChart :by-surface="summary.accuracyBySurface" :overall="summary.overallAccuracy" />
        </section>

        <section class="block">
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

    <section class="method">
      <h2>Comment ces analyses sont calculées</h2>
      <p>
        Le modèle s'appuie sur un Elo réel par joueur et par surface, recalculé chronologiquement sur l'historique
        ATP, ainsi que sur de vraies statistiques de service et de retour (aces, pourcentage de premier service,
        balles de break) extraites des scores. Quand l'échantillon disponible est trop petit pour un signal donné
        (dynamique récente, habitude en intérieur, etc.), ce signal n'apparaît simplement pas dans l'analyse plutôt
        que d'être remplacé par une estimation.
      </p>
      <p class="disclaimer">
        Ces analyses sont un outil d'aide à la compréhension du jeu, pas une garantie de résultat — aucune analyse,
        aussi fiable soit-elle historiquement, ne prédit un match individuel avec certitude.
      </p>
    </section>
  </div>
</template>

<style scoped>
.reliability {
  max-width: 860px;
  margin: 0 auto;
  padding: 48px 0 80px;
}

.hero {
  text-align: center;
  margin-bottom: 44px;
}

.eyebrow {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--green);
  margin-bottom: 10px;
}

.hero h1 {
  font-size: 32px;
  margin: 0 0 16px;
  text-wrap: balance;
}

.lead {
  font-size: 15px;
  color: var(--grey);
  line-height: 1.7;
  max-width: 620px;
  margin: 0 auto;
}

.state {
  text-align: center;
  color: var(--grey);
}

.state.err {
  color: var(--red);
}

.kpis {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 36px;
}

.kpi {
  background: var(--card);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-soft);
  padding: 24px;
  text-align: center;
}

.kpi-value {
  font-size: 30px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}

.kpi-label {
  font-size: 12px;
  color: var(--grey);
  margin-top: 6px;
}

.empty-note {
  text-align: center;
  color: var(--grey);
  font-size: 14px;
  padding: 20px;
}

.block {
  background: var(--card);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-soft);
  padding: 28px;
  margin-bottom: 24px;
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
  padding: 14px 0;
  border-bottom: 1px solid var(--line);
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
  padding: 28px 4px 0;
}

.method h2 {
  font-size: 16px;
}

.method p {
  font-size: 13px;
  color: var(--grey);
  line-height: 1.7;
}

.disclaimer {
  font-style: italic;
  font-size: 12px;
}

@media (max-width: 720px) {
  .reliability {
    padding: 32px 0 60px;
  }
  .hero h1 {
    font-size: 26px;
  }
  .kpis {
    grid-template-columns: 1fr 1fr;
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
    padding: 16px 0;
  }
  .sample {
    text-align: left;
  }
}

@media (max-width: 480px) {
  .kpis {
    grid-template-columns: 1fr;
  }
  .kpi {
    padding: 20px;
  }
}
</style>