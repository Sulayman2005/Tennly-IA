<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'
import AdminLayout from '@/components/admin/AdminLayout.vue'
import ProbabilityGauge from '@/components/ProbabilityGauge.vue'
import RadarChart from '@/components/RadarChart.vue'

const props = defineProps({ id: { type: [String, Number], required: true } })
const router = useRouter()

const match = ref(null)
const prediction = ref(null)
const loading = ref(true)
const error = ref(null)

// Un match terminé peut toujours être consulté sous son angle "avant match"
// (l'analyse IA ne change pas rétroactivement) — le tableau ci-dessous ne
// s'affiche que si le match est réellement terminé, pas de bascule vers un
// écran "après match" vide pour un match à venir.
const tab = ref('pre')

const CONFIDENCE_LABELS = { faible: 'Confiance faible', moyen: 'Confiance moyenne', eleve: 'Confiance élevée' }
const SURFACE_LABELS = { dur: 'Dur', terre_battue: 'Terre battue', gazon: 'Gazon', indoor: 'Indoor' }

onMounted(async () => {
  try {
    match.value = await api.get(`/api/tennis_matches/${props.id}`)
    if (match.value.prediction) {
      // GET /api/predictions/{id} : sécurité `is_granted('ROLE_ADMIN') or (...)`
      // sur Prediction — un admin voit toujours l'analyse complète, sans
      // dépendre d'un abonnement (voir Prediction::class côté backend).
      prediction.value = await api.get(`/api/predictions/${match.value.prediction.id}`)
    }
    if (match.value.status === 'finished') {
      tab.value = 'post'
    }
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
})

const isFinished = computed(() => match.value?.status === 'finished' && Boolean(match.value?.winner))

const factorScale = computed(() => {
  if (!prediction.value?.explanationFactors?.length) return 1
  return Math.max(...prediction.value.explanationFactors.map((f) => Math.abs(f.impactPoints)), 1)
})

const predictionWasCorrect = computed(() => {
  if (!isFinished.value || !prediction.value) return null
  return match.value.winner.id === prediction.value.favoritePlayer.id
})

function scheduledLabel(iso) {
  return new Date(iso).toLocaleString('fr-FR', { dateStyle: 'long', timeStyle: 'short' })
}
</script>

<template>
  <AdminLayout>
    <a class="back" @click="router.push({ name: 'admin-matches' })">← Retour aux matchs</a>

    <p v-if="loading">Chargement…</p>
    <p v-else-if="error" class="err">Impossible de charger ce match.</p>

    <template v-else-if="match">
      <div class="match-head" :class="{ 'is-finished': isFinished }">
        <div class="mh-left">
          <h1 v-if="isFinished">{{ match.winner.fullName }} bat {{ match.winner.id === match.playerA.id ? match.playerB.fullName : match.playerA.fullName }}</h1>
          <h1 v-else>{{ match.playerA.fullName }} — {{ match.playerB.fullName }}</h1>
          <div class="mh-meta">
            <span>{{ match.tournamentName }} · {{ match.round }}</span>
            <span>{{ SURFACE_LABELS[match.surface] ?? match.surface }}</span>
            <span>{{ scheduledLabel(match.scheduledAt) }}</span>
            <span v-if="match.scoreText">{{ match.scoreText }}</span>
          </div>
        </div>
        <div v-if="prediction" class="mh-badge">🎯 {{ CONFIDENCE_LABELS[prediction.confidenceLevel] ?? prediction.confidenceLevel }}</div>
      </div>

      <div v-if="isFinished" class="tabswitch">
        <button :class="{ active: tab === 'pre' }" @click="tab = 'pre'">Avant le match</button>
        <button :class="{ active: tab === 'post' }" @click="tab = 'post'">Après le match</button>
      </div>

      <p v-if="!prediction" class="card empty">Aucune analyse IA calculée pour ce match.</p>

      <div v-else-if="tab === 'pre'" class="grid">
        <div class="card">
          <h3>Probabilité du modèle</h3>
          <div class="sub">Favori : {{ prediction.favoritePlayer.fullName }}</div>
          <ProbabilityGauge :probability="prediction.probabilityFavorite" :label="prediction.favoritePlayer.fullName" />
        </div>

        <div class="card">
          <h3>Profil comparatif</h3>
          <div class="sub">6 dimensions clés, normalisées sur 100</div>
          <RadarChart :profile="prediction.radarProfile" :label-a="match.playerA.fullName" :label-b="match.playerB.fullName" />
        </div>

        <div class="card">
          <h3>Marché</h3>
          <div class="sub">Cote / value bet</div>
          <template v-if="prediction.marketOddsFavorite !== null && prediction.marketOddsFavorite !== undefined">
            <div class="stat"><b>{{ prediction.marketOddsFavorite.toFixed(2) }}</b><span>Cote implicite du favori</span></div>
            <div class="stat" v-if="prediction.valueEdge !== null && prediction.valueEdge !== undefined">
              <b :class="prediction.valueEdge >= 0 ? 'pos' : 'neg'">{{ prediction.valueEdge >= 0 ? '+' : '' }}{{ (prediction.valueEdge * 100).toFixed(1) }} pt</b>
              <span>Écart probabilité modèle / marché</span>
            </div>
          </template>
          <p v-else class="empty-note">Pas de cote de marché disponible pour ce match.</p>
        </div>

        <div class="card span2">
          <h3>Contribution de chaque facteur à la décision</h3>
          <div class="sub">
            Écart en points de probabilité par rapport à une base neutre de 50 % (vert = favorise {{ match.playerA.fullName }}, bleu = favorise {{ match.playerB.fullName }})
          </div>
          <div class="tornado">
            <div v-for="(f, i) in prediction.explanationFactors" :key="i" class="trow">
              <div class="tlab">{{ f.label }}</div>
              <div class="ttrack">
                <div class="mid"></div>
                <div
                  class="fill"
                  :class="f.favors === 'A' ? 'pos' : 'neg'"
                  :style="{ width: (Math.abs(f.impactPoints) / factorScale / 2) * 100 + '%', [f.favors === 'A' ? 'left' : 'right']: '50%' }"
                ></div>
              </div>
              <div class="tval">{{ f.impactPoints >= 0 ? '+' : '' }}{{ f.impactPoints }}</div>
            </div>
          </div>
        </div>

        <div class="card">
          <h3>Pourquoi cette analyse ?</h3>
          <ul class="ins-list">
            <li v-for="(factor, i) in prediction.explanationFactors" :key="i" :class="factor.tone">
              <span class="tag" :class="factor.tone">{{ factor.tone === 'warn' ? '!' : '✓' }}</span>
              {{ factor.label }} ({{ factor.favors === 'A' ? match.playerA.fullName : match.playerB.fullName }}, {{ factor.impactPoints >= 0 ? '+' : '' }}{{ factor.impactPoints }} pt)
            </li>
          </ul>
        </div>
      </div>

      <div v-else class="grid">
        <div class="card">
          <h3>Résultat</h3>
          <div class="sub">{{ match.scoreText ?? 'Score non renseigné' }}</div>
          <p><b>{{ match.winner.fullName }}</b> remporte le match.</p>
        </div>

        <div class="card">
          <h3>Analyse IA vs réalité</h3>
          <div class="sub">Probabilité annoncée avant match</div>
          <div class="compare-line">
            <b>{{ prediction.favoritePlayer.fullName }}</b>
            <div class="cbar"><i :style="{ width: prediction.probabilityFavorite * 100 + '%' }"></i></div>
            <b>{{ Math.round(prediction.probabilityFavorite * 100) }} %</b>
          </div>
          <div class="result-badge" :class="predictionWasCorrect ? 'ok' : 'bad'">
            {{ predictionWasCorrect ? '✓ Analyse confirmée' : '✗ Le favori du modèle n’a pas gagné' }}
          </div>
        </div>
      </div>
    </template>
  </AdminLayout>
</template>

<style scoped>
.back {
  color: var(--grey);
  font-size: 13px;
  cursor: pointer;
  display: inline-block;
  margin-bottom: 20px;
}
.err {
  color: var(--red);
}
.empty {
  color: var(--grey);
  font-size: 14px;
}
.empty-note {
  font-size: 13px;
  color: var(--grey);
}

.match-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: linear-gradient(120deg, var(--green), var(--green2) 60%, #051616);
  color: #fff;
  border-radius: 24px;
  padding: 26px 30px;
  margin-bottom: 20px;
  box-shadow: var(--shadow-soft);
  flex-wrap: wrap;
}
.mh-left h1 {
  margin: 0 0 6px;
  font-size: 22px;
  font-weight: 700;
}
.mh-meta {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 12px;
  opacity: 0.8;
}
.mh-meta span {
  background: rgba(255, 255, 255, 0.12);
  padding: 4px 10px;
  border-radius: 999px;
}
.mh-badge {
  background: rgba(199, 255, 60, 0.18);
  border: 1px solid rgba(199, 255, 60, 0.5);
  color: var(--lime);
  padding: 8px 16px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}

.tabswitch {
  display: inline-flex;
  gap: 4px;
  background: var(--admin-card);
  padding: 4px;
  border-radius: 999px;
  margin-bottom: 20px;
  box-shadow: var(--shadow-soft);
}
.tabswitch button {
  border: none;
  background: transparent;
  color: var(--grey);
  font-size: 13px;
  font-weight: 600;
  padding: 8px 18px;
  border-radius: 999px;
  cursor: pointer;
  font-family: inherit;
}
.tabswitch button.active {
  background: var(--ink);
  color: #fff;
}

.grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 18px;
}
.span2 {
  grid-column: span 2;
}
.card h3 {
  margin: 0 0 4px;
  font-size: 15px;
  font-weight: 700;
}
.card .sub {
  font-size: 12px;
  color: var(--grey);
  margin-bottom: 16px;
}

.stat {
  margin-bottom: 14px;
}
.stat b {
  display: block;
  font-size: 22px;
}
.stat b.pos {
  color: #1f7d33;
}
.stat b.neg {
  color: var(--red);
}
.stat span {
  font-size: 11px;
  color: var(--grey);
}

.tornado {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.trow {
  display: grid;
  grid-template-columns: 130px 1fr 50px;
  align-items: center;
  gap: 10px;
  font-size: 12px;
}
.tlab {
  color: #444;
}
.ttrack {
  position: relative;
  height: 16px;
  background: var(--admin-bg);
  border-radius: 6px;
}
.ttrack .mid {
  position: absolute;
  left: 50%;
  top: -3px;
  bottom: -3px;
  width: 1px;
  background: var(--line);
}
.ttrack .fill {
  position: absolute;
  top: 0;
  bottom: 0;
  border-radius: 5px;
}
.ttrack .fill.pos {
  background: linear-gradient(90deg, var(--green), #1f8a6b);
}
.ttrack .fill.neg {
  background: linear-gradient(270deg, var(--blue), #3ba7ff);
}
.tval {
  font-weight: 700;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.ins-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.ins-list li {
  display: flex;
  gap: 10px;
  font-size: 13px;
  line-height: 1.55;
}
.tag {
  flex: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  margin-top: 1px;
}
.tag.ok {
  background: #e6f9ea;
  color: #1f7d33;
}
.tag.warn {
  background: #fff3cd;
  color: #8a6100;
}

.compare-line {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  margin-bottom: 14px;
}
.compare-line b {
  font-size: 13px;
  white-space: nowrap;
}
.cbar {
  height: 8px;
  border-radius: 99px;
  background: var(--admin-bg);
  position: relative;
  overflow: hidden;
}
.cbar i {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  border-radius: 99px;
  background: var(--green);
}
.result-badge {
  display: inline-block;
  padding: 8px 16px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
}
.result-badge.ok {
  background: #e6f9ea;
  color: #1f7d33;
}
.result-badge.bad {
  background: #fdecea;
  color: #b3261e;
}

@media (max-width: 980px) {
  .grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 720px) {
  .match-head {
    padding: 22px 20px;
  }
  .mh-left h1 {
    font-size: 19px;
  }
  .grid {
    grid-template-columns: 1fr;
  }
  .span2 {
    grid-column: span 1;
  }
  .trow {
    grid-template-columns: 100px 1fr 42px;
    gap: 6px;
  }
}

@media (max-width: 480px) {
  .match-head {
    padding: 18px 16px;
  }
  .mh-meta span {
    font-size: 11px;
  }
  .tabswitch {
    width: 100%;
  }
  .tabswitch button {
    flex: 1;
    padding: 8px 10px;
  }
  .trow {
    grid-template-columns: 1fr;
    gap: 4px;
    padding: 8px 0;
    border-bottom: 1px solid var(--line);
  }
  .tval {
    text-align: left;
  }
  .compare-line {
    grid-template-columns: 1fr;
    text-align: left;
  }
}
</style>