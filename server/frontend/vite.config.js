import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import Icons from 'unplugin-icons/vite'
import path from 'path'

export default defineConfig({
  plugins: [
    vue(),
    Icons({ compiler: 'vue3' })
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@components': path.resolve(__dirname, './src/components')
    }
  },
  server: {
    host: true,
    https: {
      key: '/app/key.pem',
      cert: '/app/cert.pem'
    }
  },
  test: {
    environment: 'jsdom',
    clearMocks: true,
    restoreMocks: true
  },
  base: '/',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        assetFileNames: 'static/[name]-[hash][extname]',
        // ✅ Separa Monaco in chunk dedicato per lazy loading
        manualChunks(id) {
          if (id.includes('@guolao/vue-monaco-editor')) {
            return 'monaco-editor'
          }
        }
      }
    }
  },
  optimizeDeps: {
    // ✅ Pre-bundle Monaco per dev mode veloce
    include: ['@guolao/vue-monaco-editor']
  }
})
