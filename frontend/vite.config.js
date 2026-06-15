import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Only proxy API paths under /f/{access_token}/... — the same prefix
      // is also used by the Capture SPA route (/f/:accessToken/capture/*),
      // so this must not match that or the page itself gets proxied away.
      '^/f/[^/]+/(family-members|book|stories)': {
        target: process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
