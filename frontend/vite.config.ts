import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Версия приложения берётся из src-tauri/tauri.conf.json — это единый источник
// истины, который проставляет scripts/set_release_version.py перед сборкой.
const __dirname = fileURLToPath(new URL(".", import.meta.url));
const tauriConf = JSON.parse(
  readFileSync(
    new URL("../src-tauri/tauri.conf.json", `file://${__dirname}`),
    "utf-8"
  )
);

// Tauri dev-сервер по умолчанию работает на http://localhost:5173
// (совпадает с devUrl в src-tauri/tauri.conf.json).
export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  // Прокидываем версию в код фронтенда (используется в VersionBadge).
  define: {
    __APP_VERSION__: JSON.stringify(tauriConf.version),
  },
  server: {
    port: 5173,
    strictPort: true,
    watch: {
      ignored: ["**/src-tauri/**"],
    },
    proxy: {
      // Проксируем API-запросы и статику на бэкенд (FastAPI).
      "/api": {
        target: "http://localhost:8765",
        changeOrigin: true,
      },
      "/uploads": {
        target: "http://localhost:8765",
        changeOrigin: true,
      },
    },
  },
});
