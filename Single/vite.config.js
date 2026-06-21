import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 8302,
    proxy: {
      '/api': {
        target: 'http://localhost:8303',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8303',
        changeOrigin: true,
      },
    },
  },
})
