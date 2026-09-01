import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Tauri dev-сервер по умолчанию работает на http://localhost:5173
// (совпадает с devUrl в src-tauri/tauri.conf.json).
export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  server: {
    port: 5173,
    strictPort: true,
    watch: {
      ignored: ["**/src-tauri/**"],
    },
  },
});
