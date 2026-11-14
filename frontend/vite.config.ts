import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// 後端位址；埠和後端一樣用 YIQUNREN_PORT 覆寫。
const BACKEND = `http://127.0.0.1:${process.env.YIQUNREN_PORT ?? '8420'}`

export default defineConfig({
  plugins: [react()],
  build: {
    // 打包結果放進後端的套件目錄，由後端提供（不進 Git）。
    outDir: '../app/web/static',
    emptyOutDir: true,
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    // 開發伺服器預設會替本機其他埠的網頁回應 CORS 預檢，自訂標頭那一層防護就沒用了；關掉後預檢會轉給後端並被擋下。
    cors: false,
    proxy: {
      '/api': {
        target: BACKEND,
        // 後端只接受自己的 Host 與同源的 Origin（NFR-3）。開發時瀏覽器連的是這個開發伺服器，
        // 所以轉送時把兩者改成後端的位址；這個改寫只存在開發設定裡，打包後的正式版不經過它。
        changeOrigin: true,
        configure(proxy) {
          proxy.on('proxyReq', (proxyReq) => {
            if (proxyReq.getHeader('origin') !== undefined) {
              proxyReq.setHeader('origin', BACKEND)
            }
          })
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['src/test-setup.ts'],
    restoreMocks: true,
    unstubGlobals: true,
  },
})
