/**
 * Настройки киоск-режима.
 *
 * Здесь собраны параметры, которые в будущем должны управляться через админку
 * (например, таймаут возврата на главный экран). Пока значения берутся из
 * значений по умолчанию, но архитектура уже готова к загрузке настроек
 * с бэкенда через `loadKioskConfig`.
 */

export interface KioskConfig {
  /** Время бездействия пользователя, после которого происходит возврат на главный экран. */
  inactivityTimeoutMs: number;
  /** Базовый URL API бэкенда. */
  apiBaseUrl: string;
}

// Префикс API. В dev-режиме относительный путь проксируется Vite на бэкенд.
const DEV_API_PREFIX = "/api/v1";
// Бэкенд всегда поднят локально на этом адресе (совпадает с BACKEND_PORT в src-tauri/src/lib.rs).
const BACKEND_BASE_URL = "http://127.0.0.1:8765";
// В собранном приложении нет Vite-прокси, поэтому нужен абсолютный URL бэкенда.
const PROD_API_BASE_URL = `${BACKEND_BASE_URL}${DEV_API_PREFIX}`;

const DEFAULT_CONFIG: KioskConfig = {
  // 2 минуты (по ТЗ). Значение станет настраиваемым из админки.
  inactivityTimeoutMs: 2 * 60 * 1000,
  apiBaseUrl: DEV_API_PREFIX,
};

const config: KioskConfig = { ...DEFAULT_CONFIG };

/**
 * Истинно, если приложение запущено внутри Tauri (десктопный киоск).
 *
 * Tauri v2 всегда инжектит `window.__TAURI_INTERNALS__`, независимо от того,
 * из какого origin грузится SPA (WebView киоска и браузеры по LAN используют
 * один HTTP-сервер). Поэтому это — надёжный признак десктопа, в отличие от
 * проверки origin на префикс `tauri:`.
 */
export function isDesktopApp(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

/**
 * Истинно, если фронтенд раздаётся протоколом Tauri (`tauri://`).
 * Это устаревший режим: после перехода на единый HTTP-origin и WebView киоска,
 * и браузеры по LAN грузят SPA с того же сервера, что и API.
 */
function isTauriProtocol(): boolean {
  const origin = window.location.origin;
  return origin.startsWith("tauri:") || origin.includes("tauri.localhost");
}

export function getKioskConfig(): KioskConfig {
  // В штатном режиме страница и API отдаются одним HTTP-сервером (бэкенд),
  // поэтому используем относительные пути — они работают и для WebView киоска,
  // и для браузера по LAN (одинаковый origin, CORS не нужен).
  // Фолбэк на абсолютный URL — только для легаси WebView с протокола tauri://,
  // где относительный путь ушёл бы в SPA-fallback Tauri, а не на бэкенд.
  const apiBaseUrl = isTauriProtocol() ? PROD_API_BASE_URL : DEV_API_PREFIX;
  return { ...config, apiBaseUrl };
}

/**
 * Загружает актуальные настройки киоска.
 *
 * Сейчас это "плейсхолдер": возвращает значения по умолчанию. В дальнейшем
 * здесь будет запрос к админ-API (например, GET /api/v1/settings) с подменой
 * сохранённых параметров.
 *
 * @returns Копия актуальной конфигурации киоска.
 */
export async function loadKioskConfig(): Promise<KioskConfig> {
  // TODO(admin): заменить на реальную загрузку настроек с бэкенда.
  return { ...DEFAULT_CONFIG };
}
