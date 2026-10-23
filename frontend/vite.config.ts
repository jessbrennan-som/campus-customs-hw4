import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// While developing, the browser talks only to the Vite server (port 5173). Vite forwards
// anything starting with /api or /images to the FastAPI backend (port 8000), so the two
// programs feel like one website.
const backend = process.env.API_URL ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': backend,
      '/images': backend,
    },
  },
})
