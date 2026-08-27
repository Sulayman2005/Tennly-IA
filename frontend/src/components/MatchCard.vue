<script setup>
import TourBadge from '@/components/TourBadge.vue'

defineProps({
  match: { type: Object, required: true },
})

const emit = defineEmits(['open'])

const confidenceLabel = {
  faible: 'Confiance faible',
  moyen: 'Confiance moyenne',
  eleve: 'Confiance élevée',
}
</script>

<template>
  <div class="match-card" @click="emit('open', match)">
    <div class="mc-top">
      <span class="mc-tag">
        <TourBadge :tour="match.playerA.tour" on-dark />
        {{ match.tournamentName }} · {{ match.round }}
      </span>
      <span class="mc-time">{{ new Date(match.scheduledAt).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' }) }}</span>
    </div>
    <div class="mc-body">
      <div class="mc-player">
        <div class="mc-photo"><span class="mc-initials">{{ match.playerA.fullName.split(' ').map((w) => w[0]).join('') }}</span></div>
        <div>
          <div class="mc-name">{{ match.playerA.fullName }}</div>
          <div class="mc-rank">N°{{ match.playerA.atpWtaRank }} mondial</div>
        </div>
      </div>
      <div class="mc-vs">VS</div>
      <div class="mc-player mc-player-right">
        <div>
          <div class="mc-name">{{ match.playerB.fullName }}</div>
          <div class="mc-rank">N°{{ match.playerB.atpWtaRank }} mondial</div>
        </div>
        <div class="mc-photo"><span class="mc-initials">{{ match.playerB.fullName.split(' ').map((w) => w[0]).join('') }}</span></div>
      </div>
    </div>
    <div class="mc-bottom" v-if="match.prediction">
      <span class="mc-confidence">{{ confidenceLabel[match.prediction.confidenceLevel] }}</span>
      <span class="mc-proba">{{ Math.round(match.prediction.probabilityFavorite * 100) }} % {{ match.prediction.favoritePlayer.fullName.split(' ').at(-1) }} favori</span>
    </div>
  </div>
</template>

<style scoped>
.match-card {
  background: linear-gradient(135deg, var(--green), var(--green2));
  color: #fff;
  border-radius: 20px;
  padding: 20px 24px;
  margin-bottom: 16px;
  cursor: pointer;
  transition: transform 0.15s ease;
}
.match-card:hover {
  transform: translateY(-2px);
}
.mc-top {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  opacity: 0.75;
  margin-bottom: 14px;
}
.mc-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.mc-body {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.mc-player {
  display: flex;
  align-items: center;
  gap: 10px;
}
.mc-player-right {
  flex-direction: row-reverse;
  text-align: right;
}
.mc-photo {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
}
.mc-name {
  font-weight: 700;
  font-size: 14px;
}
.mc-rank {
  font-size: 11px;
  opacity: 0.7;
}
.mc-vs {
  font-size: 12px;
  opacity: 0.6;
  font-style: italic;
}
.mc-bottom {
  display: flex;
  justify-content: space-between;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.14);
  font-size: 12px;
}
.mc-proba {
  font-weight: 700;
}
</style>