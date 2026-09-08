<script setup>
import TourBadge from '@/components/TourBadge.vue'
import { initials, avatarGradient, flagUrl, surfaceCardVars } from '@/utils/playerVisuals'

const props = defineProps({
  match: { type: Object, required: true },
})

const emit = defineEmits(['open'])

const confidenceLabel = {
  faible: 'Confiance faible',
  moyen: 'Confiance moyenne',
  eleve: 'Confiance élevée',
}

function isFavorite(player) {
  return props.match.prediction?.favoritePlayer?.id === player.id
}
</script>

<template>
  <div class="match-card" :style="surfaceCardVars(match.surface)" @click="emit('open', match)">
    <div class="mc-top">
      <span class="mc-tag">
        <TourBadge :tour="match.playerA.tour" on-dark />
        {{ match.tournamentName }} · {{ match.round }}
      </span>
      <span class="mc-time">
        {{ new Date(match.scheduledAt).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' }) }}
        · <span class="mc-status" :class="{ done: match.status !== 'scheduled' }">{{ match.status === 'scheduled' ? 'À venir' : 'Terminé' }}</span>
      </span>
    </div>
    <div class="mc-body">
      <div class="mc-player">
        <div class="mc-avatar" :class="{ 'is-favorite': isFavorite(match.playerA) }" :style="avatarGradient(match.playerA.fullName)">
          <span class="mc-initials">{{ initials(match.playerA.fullName) }}</span>
          <img
            v-if="flagUrl(match.playerA.countryCode)"
            :src="flagUrl(match.playerA.countryCode)"
            class="mc-flag"
            alt=""
            loading="lazy"
            @error="$event.target.style.display = 'none'"
          />
        </div>
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
        <div class="mc-avatar" :class="{ 'is-favorite': isFavorite(match.playerB) }" :style="avatarGradient(match.playerB.fullName)">
          <span class="mc-initials">{{ initials(match.playerB.fullName) }}</span>
          <img
            v-if="flagUrl(match.playerB.countryCode)"
            :src="flagUrl(match.playerB.countryCode)"
            class="mc-flag"
            alt=""
            loading="lazy"
            @error="$event.target.style.display = 'none'"
          />
        </div>
      </div>
    </div>
    <!-- match.prediction existe pour tout le monde (au moins { id }, voir
         TennisMatch::$prediction côté backend) mais confidenceLevel n'est
         présent que pour un ROLE_ADMIN ou un abonné actif (groupe
         'match:read:prediction', décision produit du 02/09/2026) — d'où le
         test sur confidenceLevel et non sur match.prediction seul, sinon
         cette pastille tenterait de s'afficher avec des données absentes
         pour un non-abonné. -->
    <div class="mc-bottom" v-if="match.prediction?.confidenceLevel">
      <span class="mc-confidence">{{ confidenceLabel[match.prediction.confidenceLevel] }}</span>
      <span class="mc-proba">{{ Math.round(match.prediction.probabilityFavorite * 100) }} % {{ match.prediction.favoritePlayer.fullName.split(' ').at(-1) }} favori</span>
    </div>
  </div>
</template>

<style scoped>
.match-card {
  position: relative;
  overflow: hidden;
  isolation: isolate;
  background:
    radial-gradient(130% 160% at 105% -10%, var(--surface-glow) 0%, transparent 55%),
    linear-gradient(135deg, var(--green), var(--green2));
  color: #fff;
  border-radius: 20px;
  padding: 20px 24px;
  margin-bottom: 16px;
  cursor: pointer;
  transform: translateY(0) scale(1);
  transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.16);
}
/* Sweep lumineux au survol : un seul passage, jamais en boucle. */
.match-card::before {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 1;
  background: linear-gradient(115deg, transparent 42%, rgba(255, 255, 255, 0.16) 50%, transparent 58%);
  transform: translateX(-130%);
  transition: transform 0.85s ease;
  pointer-events: none;
}
.match-card:hover {
  transform: translateY(-6px) scale(1.012);
  box-shadow:
    0 22px 44px -14px var(--surface-shadow),
    0 0 0 1px rgba(255, 255, 255, 0.08);
}
.match-card:hover::before {
  transform: translateX(130%);
}
@media (prefers-reduced-motion: reduce) {
  .match-card,
  .match-card::before {
    transition: none;
  }
}

.mc-top {
  position: relative;
  z-index: 2;
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 11px;
  opacity: 0.78;
  margin-bottom: 18px;
}
.mc-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.mc-body {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.mc-player {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}
.mc-player-right {
  flex-direction: row-reverse;
  text-align: right;
}

.mc-avatar {
  position: relative;
  flex: none;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow:
    inset 0 0 0 2px rgba(255, 255, 255, 0.22),
    0 6px 16px rgba(0, 0, 0, 0.28);
  transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.4s ease;
}
.match-card:hover .mc-avatar {
  transform: translateY(-2px) scale(1.04);
}
.mc-avatar.is-favorite {
  box-shadow:
    inset 0 0 0 2px rgba(255, 255, 255, 0.3),
    0 0 0 3px var(--lime),
    0 6px 18px rgba(199, 255, 60, 0.32);
}
.mc-initials {
  font-size: 15px;
  font-weight: 800;
  letter-spacing: 0.01em;
  color: #fff;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
}
.mc-flag {
  position: absolute;
  bottom: -2px;
  right: -2px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #fff;
  object-fit: cover;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.4);
}
.mc-player-right .mc-flag {
  right: auto;
  left: -2px;
}

.mc-name {
  font-weight: 700;
  font-size: 15px;
  letter-spacing: -0.01em;
}
.mc-rank {
  font-size: 11px;
  opacity: 0.7;
  font-variant-numeric: tabular-nums;
}
.mc-vs {
  flex: none;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.18);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.04em;
  color: rgba(255, 255, 255, 0.8);
}
.mc-status {
  font-weight: 700;
  opacity: 0.9;
}
.mc-status.done {
  opacity: 0.65;
}
.mc-status {
  font-weight: 700;
  opacity: 0.9;
}
.mc-status.done {
  opacity: 0.65;
}
.mc-bottom {
  position: relative;
  z-index: 2;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.14);
  font-size: 12px;
}
.mc-confidence {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--surface-tint);
  color: #fff;
  font-weight: 600;
  font-size: 11px;
}
.mc-proba {
  font-weight: 800;
  color: var(--lime);
  font-variant-numeric: tabular-nums;
}

@media (max-width: 480px) {
  .match-card {
    padding: 16px 18px;
  }
  .mc-body {
    gap: 8px;
  }
  .mc-avatar {
    width: 44px;
    height: 44px;
  }
  .mc-initials {
    font-size: 13px;
  }
  .mc-name {
    font-size: 13px;
  }
  .mc-vs {
    width: 28px;
    height: 28px;
    font-size: 9px;
  }
}

@media (max-width: 480px) {
  .match-card {
    padding: 16px 18px;
  }
  .mc-body {
    gap: 8px;
  }
  .mc-photo {
    width: 30px;
    height: 30px;
    font-size: 11px;
  }
  .mc-name {
    font-size: 13px;
  }
  .mc-vs {
    font-size: 10px;
  }
}
</style>