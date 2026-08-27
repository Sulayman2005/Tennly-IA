import { defineStore } from 'pinia'

const STORAGE_KEY = 'tennly.cookieConsent'

/**
 * Consentement cookies (RGPD) — un seul choix stocké en local, jamais envoyé
 * au backend (pas besoin de compte pour naviguer). Tant qu'aucun outil
 * d'analytics n'est réellement branché, `analytics` ne sert à rien de plus
 * que d'être lu plus tard : le jour où Google Analytics (ou équivalent) est
 * ajouté, son script ne doit être injecté que si `analytics === true` —
 * jamais avant que l'utilisateur ait donné son accord.
 */
export const useCookieConsentStore = defineStore('cookieConsent', {
  state: () => ({
    // null = aucun choix fait pour l'instant (la bannière doit s'afficher).
    choice: loadChoice(),
  }),
  getters: {
    hasDecided: (state) => state.choice !== null,
    analyticsAllowed: (state) => state.choice?.analytics === true,
  },
  actions: {
    acceptAll() {
      this.setChoice({ analytics: true })
    },
    refuseNonEssential() {
      this.setChoice({ analytics: false })
    },
    setChoice(choice) {
      this.choice = { ...choice, decidedAt: new Date().toISOString() }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.choice))
    },
    reset() {
      this.choice = null
      localStorage.removeItem(STORAGE_KEY)
    },
  },
})

function loadChoice() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}
