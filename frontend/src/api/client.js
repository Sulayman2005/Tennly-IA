/**
 * Client HTTP minimal pour l'API Symfony/API Platform.
 * Pas de dépendance externe (axios, etc.) — fetch natif suffit pour ce MVP.
 */

const ACCESS_TOKEN_KEY = 'tennly.accessToken'
const REFRESH_TOKEN_KEY = 'tennly.refreshToken'

function getAccessToken() {
  return sessionStorage.getItem(ACCESS_TOKEN_KEY)
}

function setTokens({ token, refresh_token }) {
  if (token) sessionStorage.setItem(ACCESS_TOKEN_KEY, token)
  if (refresh_token) sessionStorage.setItem(REFRESH_TOKEN_KEY, refresh_token)
}

function clearTokens() {
  sessionStorage.removeItem(ACCESS_TOKEN_KEY)
  sessionStorage.removeItem(REFRESH_TOKEN_KEY)
}

/**
 * Appel générique à l'API. `path` commence par /api/... (proxifié vers
 * Symfony en dev, voir vite.config.js).
 */
async function request(path, { method = 'GET', body, headers = {}, auth = true } = {}) {
  const finalHeaders = {
    'Content-Type': 'application/ld+json',
    Accept: 'application/ld+json',
    ...headers,
  }

  if (auth) {
    const token = getAccessToken()
    if (token) finalHeaders.Authorization = `Bearer ${token}`
  }

  const response = await fetch(path, {
    method,
    headers: finalHeaders,
    body: body ? JSON.stringify(body) : undefined,
  })

  if (response.status === 401 && auth) {
    // Le JWT a expiré : on tente un rafraîchissement silencieux une seule fois.
    const refreshed = await tryRefreshToken()
    if (refreshed) {
      return request(path, { method, body, headers, auth })
    }
    clearTokens()
  }

  if (!response.ok) {
    const problem = await response.json().catch(() => null)
    throw new ApiError(response.status, problem?.detail || problem?.message || response.statusText, problem)
  }

  if (response.status === 204) return null

  return response.json()
}

async function tryRefreshToken() {
  const refreshToken = sessionStorage.getItem(REFRESH_TOKEN_KEY)
  if (!refreshToken) return false

  try {
    const res = await fetch('/api/token/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
    if (!res.ok) return false
    const data = await res.json()
    setTokens(data)
    return true
  } catch {
    return false
  }
}

export class ApiError extends Error {
  constructor(status, message, problem) {
    super(message)
    this.status = status
    this.problem = problem
  }
}

export const api = {
  get: (path) => request(path),
  post: (path, body, opts = {}) => request(path, { method: 'POST', body, ...opts }),
  patch: (path, body) => request(path, { method: 'PATCH', body, headers: { 'Content-Type': 'application/merge-patch+json' } }),

  /** POST /api/login_check — email/mot de passe, voir section 3.9. */
  async login(email, password) {
    const data = await request('/api/login_check', {
      method: 'POST',
      body: { email, password },
      headers: { 'Content-Type': 'application/json' },
      auth: false,
    })
    setTokens(data)
    return data
  },

  /**
   * POST /api/register — crée un compte, sans déclencher aucun paiement (voir
   * UserRegistrationProcessor côté backend). Le paiement se démarre
   * séparément via createCheckoutSession(), au moment où l'utilisateur choisit
   * une formule depuis la popup paywall d'un match précis.
   */
  async register({ email, password, firstName, lastName }) {
    return request('/api/register', {
      method: 'POST',
      body: { email, plainPassword: password, firstName, lastName },
      auth: false,
    })
  },

  /**
   * POST /api/checkout-sessions — démarre un paiement Stripe pour
   * l'utilisateur courant (déjà connecté) et une formule donnée.
   * `redirectPath` est le chemin du match qui a déclenché le paiement (voir
   * PaywallModal.vue) : Stripe y renvoie l'utilisateur une fois le paiement
   * confirmé, au lieu d'une page générique.
   */
  async createCheckoutSession(planCode, redirectPath, withdrawalWaiverAccepted) {
    return request('/api/checkout-sessions', {
      method: 'POST',
      body: { planCode, redirectPath, withdrawalWaiverAccepted },
    })
  },

  logout() {
    clearTokens()
  },

  isAuthenticated() {
    return Boolean(getAccessToken())
  },
}