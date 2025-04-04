import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/search': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        // No rewrite needed if the route is exactly the same
      }
    }
  }
})