import { createApp } from 'vue'
import { createPinia } from 'pinia'
import * as Sentry from '@sentry/vue'
import App from './App.vue'
import router from './router'
import './assets/tokens.css'

const app = createApp(App)

// Monitoring d'erreurs (voir projet "tennly-frontend" sur sentry.io).
// VITE_SENTRY_DSN vient de .env.local, jamais commité (voir .gitignore) —
// laissé vide en développement local pour ne pas polluer Sentry avec du
// bruit de dev ; rempli uniquement sur le VPS juste avant `npm run build`
// (Vite fige sa valeur DANS le bundle au moment du build, ce n'est pas lu à
// l'exécution dans le navigateur).
if (import.meta.env.VITE_SENTRY_DSN) {
  Sentry.init({
    app,
    dsn: import.meta.env.VITE_SENTRY_DSN,
    environment: import.meta.env.MODE,
  })
}

app.use(createPinia())
app.use(router)
app.mount('#app')
