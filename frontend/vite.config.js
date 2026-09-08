import { fileURLToPath, URL } from 'node:url'
// `vitest/config` réexporte exactement `defineConfig` de Vite (même
// comportement pour `vite`/`vite build`/`vite preview`), en ajoutant
// simplement la clé `test` ci-dessous comprise par Vitest — un seul fichier
// de config pour les deux outils, pas de doublon à maintenir.
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

// Cahier des charges section 4.5 : Vue 3 + Vite, consomme l'API Symfony
// (API Platform) exposée par défaut sur http://localhost:8000.
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
  },
})