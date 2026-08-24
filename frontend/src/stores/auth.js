import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api, ApiError } from '@/api/client'

/**
 * État d'authentification global. `hasActiveSubscription` reflète
 * `User::hasActiveSubscription()` côté backend (exposée via GET /api/me, voir
 * `activeSubscription` ci-dessous — le sérialiseur Symfony expose une méthode
 * `hasXxx()` sous le nom de propriété "xxx") et sert à afficher (ou non) la
 * popup paywall côté frontend — voir PaywallModal.vue et cahier des charges
 * section 3.2.1.
 */
export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const isAuthenticated = ref(api.isAuthenticated())

  const hasActiveSubscription = computed(() => Boolean(user.value?.activeSubscription))

  /**
   * Reflète User::getRoles() côté backend (exposé sur GET /api/me depuis
   * l'ajout du groupe "user:read" sur User::$roles). Sert uniquement à
   * afficher/masquer le lien "Back-office" (section 3.7) et à garder les
   * routes /admin/* côté client — la vraie sécurité reste imposée par les
   * `is_granted('ROLE_ADMIN')` côté API, jamais par cet état local.
   */
  const isAdmin = computed(() => Boolean(user.value?.roles?.includes('ROLE_ADMIN')))

  async function login(email, password) {
    await api.login(email, password)
    isAuthenticated.value = true
    await fetchCurrentUser()
  }

  /**
   * @param {{email: string, password: string, firstName: string, lastName: string}} payload
   *
   * Crée le compte puis connecte immédiatement l'utilisateur — ne déclenche
   * aucun paiement (voir api.createCheckoutSession(), appelé séparément
   * depuis ConnexionView.vue/PaywallModal.vue quand une formule est choisie).
   */
  async function register(payload) {
    await api.register(payload)
    await login(payload.email, payload.password)
  }

  async function fetchCurrentUser() {
    if (!isAuthenticated.value) {
      user.value = null
      return
    }

    try {
      // GET /api/me : renvoie toujours l'utilisateur du token courant (voir
      // CurrentUserProvider côté backend), jamais un id arbitraire.
      user.value = await api.get('/api/me')
    } catch (e) {
      // Token invalide/expiré et non rafraîchissable : on redevient déconnecté
      // plutôt que de laisser un `user` obsolète (et un hasActiveSubscription
      // potentiellement faux) trainer dans le store.
      if (e instanceof ApiError && (e.status === 401 || e.status === 403)) {
        isAuthenticated.value = false
        user.value = null
      } else {
        throw e
      }
    }
  }

  function logout() {
    api.logout()
    isAuthenticated.value = false
    user.value = null
  }

  return { user, isAuthenticated, hasActiveSubscription, isAdmin, login, register, logout, fetchCurrentUser }
})