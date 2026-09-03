/**
 * Копирует собранный фронтенд (frontend/dist) в каталог,
 * из которого бэкенд будет раздавать SPA по HTTP.
 *
 * Запускается как часть `beforeBuildCommand` Tauri (см. tauri.conf.json)
 * сразу после `npm run build` во фронтенде. Результат — `src-tauri/web/dist`,
 * который затем `bundle.resources` кладёт рядом с `kiosk.exe`
 * (в `$INSTDIR/web/dist`) при установке.
 *
 * В рантайме Rust-оболочка передаёт этот путь бэкенду через
 * `SCHOOL_KIOSK_FRONTEND_DIR` (см. src-tauri/src/process.rs), а Python-бэкенд
 * раздаёт оттуда index.html и ассеты (см. backend/src/core/config.py).
 */
import { cpSync, mkdirSync, rmSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const src = path.join(root, "frontend", "dist");
const dest = path.join(root, "src-tauri", "web", "dist");

rmSync(dest, { recursive: true, force: true });
mkdirSync(dest, { recursive: true });
cpSync(src, dest, { recursive: true });

console.log(`[copy-web] Web assets: ${path.relative(root, src)} -> ${path.relative(root, dest)}`);
