import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
    plugins: [react()],
    server: {
        // Ключевые настройки для Docker
        host: '0.0.0.0',     // Слушать на всех интерфейсах
        port: 3000,          // Явно указать порт
        strictPort: true,    // Не менять порт если занят

        // Настройки HMR для работы через внешний IP
        hmr: {
            host: '158.160.117.3',  // Ваш публичный IP
            clientPort: 3000        // Порт для WebSocket
        },

        // CORS для разработки
        cors: true,

        // Proxy для API запросов (если нужно)
        proxy: {
            '/api': {
                target: 'http://backend:8000',  // Внутреннее имя контейнера!
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api/, '')
            }
        }
    },

    // Важно для правильных путей
    base: './'
})