import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Dev server proxies the control API and telemetry socket to the FastAPI backend.
const gateway = `127.0.0.1:${process.env.GATEWAY_PORT ?? 8000}`
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': `http://${gateway}`,
      '/ws': { target: `ws://${gateway}`, ws: true },
    },
  },
})
