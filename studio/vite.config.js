import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/workflow': 'http://localhost:8000',
      '/api': 'http://localhost:8000',
      '/auth': 'http://localhost:8000'
    }
  }
})
