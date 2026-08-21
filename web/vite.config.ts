import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      // Online-only app — precache the app shell for installability, but
      // never cache API responses. The pantry/recipe data must always be
      // fetched fresh.
      workbox: {
        globPatterns: ['**/*.{js,css,html,png,svg,ico}'],
        navigateFallbackDenylist: [/^\/api\//, /^\/healthz$/],
      },
      manifest: {
        name: 'Kitchen',
        short_name: 'Kitchen',
        description: 'Personal cooking assistant',
        theme_color: '#c67139',
        background_color: '#f5ead8',
        display: 'standalone',
        orientation: 'portrait',
        start_url: '/',
        icons: [
          { src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: '/icon-512-maskable.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
    }),
  ],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8420',
      '/healthz': 'http://127.0.0.1:8420',
    },
  },
})
