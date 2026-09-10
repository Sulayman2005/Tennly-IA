<script setup>
import { reactive } from 'vue'
import TourBadge from '@/components/TourBadge.vue'
import { initials, avatarGradient, flagUrl, surfaceCardVars, hasPhoto, surfaceLabel } from '@/utils/playerVisuals'

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

// Une URL Wikimedia en base ne garantit pas que l'image charge encore
// (page renommée, fichier supprimé côté Commons) : si <img> déclenche
// @error, on bascule sur l'avatar initiales pour CE joueur précis plutôt
// que de laisser un cadre cassé — voir showPhoto() ci-dessous.
const photoErrored = reactive(new Set())
function onPhotoError(playerId) {
  photoErrored.add(playerId)
}
function showPhoto(player) {
  return hasPhoto(player) && !photoErrored.has(player.id)
}

// Libellé de statut (11/09/2026, complété le 10/09/2026) : jusqu'ici tout
// match non 'scheduled' affichait juste "Terminé", y compris un forfait
// (status 'walkover') — pas faux, mais moins précis que ce qu'on sait déjà
// côté back (voir MatchStatus.php). 'winner'/'scoreText' sont exposés par
// l'API depuis le début (Groups 'match:read' sur TennisMatch.php) mais
// n'ont jamais été affichés nulle part côté frontend : ça n'avait aucun
// intérêt tant que import_upcoming_matches.py ne les renseignait jamais
// (voir update_match_results.py, qui vient combler ce trou côté données).
// Le cas 'live' manquait carrément ici (un match en cours retombait dans
// le "return 'Terminé'" par défaut — un match toujours en train de se
// jouer affiché comme terminé) — ajouté explicitement, voir aussi le badge
// dédié .mc-live dans le template.
function statusLabel(status) {
  if (status === 'scheduled') return 'À venir'
  if (status === 'live') return 'En direct'
  if (status === 'walkover') return 'Terminé (forfait)'
  return 'Terminé'
}

function isWinner(player) {
  return props.match.winner?.id === player.id
}
</script>

<template>
  <div class="match-card" :style="surfaceCardVars(match.surface)" @click="emit('open', match)">
    <div class="mc-top">
      <span class="mc-tag">
        <TourBadge :tour="match.playerA.tour" on-dark />
        {{ match.tournamentName }} · {{ match.round }}
      </span>
      <span class="mc-surface">{{ surfaceLabel(match.surface) }}</span>
      <!-- Badge "En direct" dédié (10/09/2026) : distinct de .mc-status pour
           qu'un match en cours ressorte visuellement (pastille rouge
           pulsante, convention universelle du direct) plutôt que de se
           fondre dans le même texte discret que "Terminé"/"À venir". -->
      <span v-if="match.status === 'live'" class="mc-live"><i></i>EN DIRECT</span>
      <span class="mc-time">
        {{ new Date(match.scheduledAt).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' }) }}
        · <span class="mc-status" :class="{ done: match.status !== 'scheduled' && match.status !== 'live' }">{{ statusLabel(match.status) }}</span>
      </span>
    </div>
    <div class="mc-body">
      <div class="mc-player">
        <div class="mc-avatar" :class="{ 'is-favorite': isFavorite(match.playerA) }" :style="!showPhoto(match.playerA) ? avatarGradient(match.playerA.fullName) : null">
          <img
            v-if="showPhoto(match.playerA)"
            :src="match.playerA.photoUrl"
            class="mc-photo"
            alt=""
            loading="lazy"
            @error="onPhotoError(match.playerA.id)"
          />
          <span v-else class="mc-initials">{{ initials(match.playerA.fullName) }}</span>
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
          <div class="mc-name">
            {{ match.playerA.fullName }}
            <svg v-if="isWinner(match.playerA)" class="mc-winner-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" aria-label="Vainqueur">
              <circle cx="12" cy="12" r="10" fill="currentColor" opacity="0.22" />
              <path d="M7 12.5l3 3 7-7" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </div>
          <div class="mc-rank">N°{{ match.playerA.atpWtaRank }} mondial</div>
        </div>
      </div>
      <div class="mc-vs">VS</div>
      <div class="mc-player mc-player-right">
        <div>
          <div class="mc-name">
            <svg v-if="isWinner(match.playerB)" class="mc-winner-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" aria-label="Vainqueur">
              <circle cx="12" cy="12" r="10" fill="currentColor" opacity="0.22" />
              <path d="M7 12.5l3 3 7-7" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            {{ match.playerB.fullName }}
          </div>
          <div class="mc-rank">N°{{ match.playerB.atpWtaRank }} mondial</div>
        </div>
        <div class="mc-avatar" :class="{ 'is-favorite': isFavorite(match.playerB) }" :style="!showPhoto(match.playerB) ? avatarGradient(match.playerB.fullName) : null">
          <img
            v-if="showPhoto(match.playerB)"
            :src="match.playerB.photoUrl"
            class="mc-photo"
            alt=""
            loading="lazy"
            @error="onPhotoError(match.playerB.id)"
          />
          <span v-else class="mc-initials">{{ initials(match.playerB.fullName) }}</span>
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
    <!-- Score réel (voir ml-service/update_match_results.py, 11/09/2026) :
         donnée publique, jamais réservée aux abonnés — contrairement à
         mc-bottom juste en dessous (confidenceLevel), on ne conditionne pas
         cet affichage à un quelconque statut d'abonnement. -->
    <div v-if="match.status !== 'scheduled' && match.scoreText" class="mc-result">
      <span class="mc-result-score">{{ match.scoreText }}</span>
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
    linear-gradient(135deg, var(--surface-from), var(--surface-to));
  color: #fff;
  border-radius: 20px;
  padding: 20px 24px;
  margin-bottom: 16px;
  cursor: pointer;
  transform: translateY(0) scale(1);
  transition:
    transform 0.4s var(--ease-premium),
    box-shadow 0.4s var(--ease-premium),
    background 0.5s ease;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.16);
}
/* Texture "lignes de court" très discrète — donne un peu de matière au
   dégradé sans jamais gêner la lecture (opacité 6%), plutôt qu'un aplat de
   couleur totalement plat. */
.match-card::after {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 0;
  opacity: 0.07;
  background-image: repeating-linear-gradient(115deg, #fff 0 1.5px, transparent 1.5px 26px);
  pointer-events: none;
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
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 6px 10px;
  font-size: 11px;
  opacity: 0.78;
  margin-bottom: 18px;
}
.mc-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.mc-surface {
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  font-size: 10px;
  padding: 3px 9px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.14);
  margin-right: auto;
}
/* Badge "En direct" (10/09/2026) : rouge + pastille pulsante, jamais la
   couleur de surface (déjà utilisée pour --surface-tint/--surface-glow
   partout ailleurs sur cette carte) ni le citron vert (réservé au positif —
   favori, confiance, victoire) — le rouge est la convention universelle du
   direct, personne ne doit avoir à deviner ce que ça veut dire. */
.mc-live {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 800;
  letter-spacing: 0.04em;
  font-size: 10px;
  padding: 3px 10px 3px 8px;
  border-radius: 999px;
  background: rgba(255, 69, 58, 0.22);
  color: #fff;
  border: 1px solid rgba(255, 69, 58, 0.5);
}
.mc-live i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--red);
  box-shadow: 0 0 0 2px rgba(255, 69, 58, 0.35);
  animation: mcLivePulse 1.6s ease-in-out infinite;
}
@keyframes mcLivePulse {
  0%,
  100% {
    opacity: 1;
    box-shadow: 0 0 0 2px rgba(255, 69, 58, 0.35);
  }
  50% {
    opacity: 0.55;
    box-shadow: 0 0 0 4px rgba(255, 69, 58, 0.16);
  }
}
@media (prefers-reduced-motion: reduce) {
  .mc-live i {
    animation: none;
  }
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
  overflow: hidden;
  box-shadow:
    inset 0 0 0 2px rgba(255, 255, 255, 0.22),
    0 6px 16px rgba(0, 0, 0, 0.28);
  transition:
    transform 0.4s var(--ease-premium),
    box-shadow 0.4s ease;
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
.mc-photo {
  width: 100%;
  height: 100%;
  object-fit: cover;
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
.mc-winner-icon {
  color: var(--lime);
  vertical-align: -1px;
}
.mc-result {
  position: relative;
  z-index: 2;
  margin-top: 10px;
  text-align: center;
}
.mc-result-score {
  display: inline-flex;
  padding: 5px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.02em;
  font-variant-numeric: tabular-nums;
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
  .mc-surface {
    order: 3;
    margin-right: 0;
  }
}
</style>
