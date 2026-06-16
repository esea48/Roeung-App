import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Proxy only the specific API path segments. The /book prefix is shared
      // with the Book SPA route, so the book proxy must anchor precisely:
      //   GET /f/{token}/book              → API (book home data)
      //   GET /f/{token}/book/uncategorised → API
      //   GET /f/{token}/book/             → SPA (must NOT proxy)
      //   GET /f/{token}/book/chapter/…   → SPA (must NOT proxy)
      '^/f/[^/]+/book(/uncategorised.*)?$': {
        target: process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
      },
      '^/f/[^/]+/(family-members|stories|chapters)': {
        target: process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
      },
      // Keeper API routes — matched precisely to avoid conflicting with the
      // Keeper SPA routes at /keeper and /keeper/story/:id.
      // 'stories' (plural) is the API path; 'story' (singular) is the SPA.
      '^/keeper/(queue|stories|family-members|chapters|stats)((/|\\?).*)?$': {
        target: process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
