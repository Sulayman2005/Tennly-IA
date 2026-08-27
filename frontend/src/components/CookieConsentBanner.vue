<script setup>
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useCookieConsentStore } from '@/stores/cookieConsent'

// Bannière RGPD : ne s'affiche que tant qu'aucun choix n'a été enregistré
// (voir cookieConsent store). "Refuser" doit être aussi simple qu'"Accepter"
// (recommandation CNIL) — les deux sont des boutons de même niveau visuel,
// pas un bouton principal contre un lien discret.
const consent = useCookieConsentStore()
const detailsOpen = ref(false)
</script>

<template>
  <div v-if="!consent.hasDecided" class="cookie-banner" role="dialog" aria-label="Consentement cookies">
    <div class="cookie-body">
      <p>
        On utilise des cookies strictement nécessaires au fonctionnement du site (connexion, préférences), et —
        seulement avec ton accord — des cookies de mesure d'audience pour comprendre l'usage du site.
        <button type="button" class="link-btn" @click="detailsOpen = !detailsOpen">
          {{ detailsOpen ? 'Masquer les détails' : 'En savoir plus' }}
        </button>
        <RouterLink to="/confidentialite">Politique de confidentialité</RouterLink>
      </p>
      <div v-if="detailsOpen" class="cookie-details">
        <p><b>Cookies nécessaires</b> — toujours actifs : maintien de ta session de connexion. Pas de choix possible,
        ils sont indispensables au fonctionnement du site.</p>
        <p><b>Cookies de mesure d'audience</b> — désactivés par défaut : nous aident à comprendre quelles pages sont
        consultées, de façon agrégée. Uniquement activés si tu cliques sur "Accepter".</p>
      </div>
    </div>
    <div class="cookie-actions">
      <button type="button" class="btn-ghost" @click="consent.refuseNonEssential()">Refuser</button>
      <button type="button" class="btn-primary" @click="consent.acceptAll()">Accepter</button>
    </div>
  </div>
</template>

<style scoped>
.cookie-banner {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 100;
  background: var(--ink);
  color: #fff;
  padding: 18px 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
  box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.15);
}

.cookie-body {
  flex: 1;
  min-width: 260px;
  font-size: 13px;
  line-height: 1.6;
}

.cookie-body p {
  margin: 0;
}

.cookie-body a,
.link-btn {
  color: var(--lime);
  font-weight: 600;
  margin-left: 10px;
  white-space: nowrap;
}

.link-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 13px;
  padding: 0;
  text-decoration: underline;
}

.cookie-details {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.15);
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  opacity: 0.85;
}

.cookie-actions {
  display: flex;
  gap: 10px;
  flex: none;
}

.btn-ghost,
.btn-primary {
  border-radius: 999px;
  padding: 10px 20px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
}

.btn-ghost {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.4);
  color: #fff;
}

.btn-ghost:hover {
  background: rgba(255, 255, 255, 0.1);
}

.btn-primary {
  background: var(--green);
  border: none;
  color: #fff;
}

.btn-primary:hover {
  background: var(--green2);
}

@media (max-width: 640px) {
  .cookie-banner {
    padding: 16px 20px;
  }
  .cookie-actions {
    width: 100%;
  }
  .btn-ghost,
  .btn-primary {
    flex: 1;
  }
}
</style>
