import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 3003,
    host: true,
    proxy: {
      '/api': {
        target: 'http://api:8002',
        changeOrigin: true,
      },
      '/media': {
        target: 'http://api:8002',
        changeOrigin: true,
      },
      '/static': {
        target: 'http://api:8002',
        changeOrigin: true,
      },
    },
  },
})
