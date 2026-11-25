import type { AppUnit } from "../types/kiosk";
import type { ScheduleMode } from "../types/schedule";

/**
 * Настройки киоск-режима.
 *
 * Значения приходят с публичного эндпоинта `GET /api/v1/kiosk/config`
 * (настройки в БД и реестр сервисов). Локальные дефолты используются,
 * пока бэкенд недоступен.
 */

export interface KioskConfig {
  /** Время бездействия пользователя, после которого происходит возврат на главный экран. */
  inactivityTimeoutMs: number;
  /** Базовый URL API бэкенда. */
  apiBaseUrl: string;
  /** Приветственное сообщение на главном экране (пустая строка — стандартный подзаголовок). */
  welcomeMessage: string;
  /** Режим отображения расписания, заданный на бэкенде. */
  scheduleMode: ScheduleMode;
  /** Сервисы (плитки), включённые в реестре `app_units`. */
  units: AppUnit[];
  /** Включён ли сервис погоды в настройках. */
  weatherEnabled: boolean;
  /** Населённый пункт для прогноза погоды. */
  weatherLocation: string;
  /** Включён ли сервис объявлений. */
  announcementsEnabled: boolean;
  /** Показывать бегущую строку объявлений на главном экране. */
  announcementsTickerEnabled: boolean;
}

// Префикс API. В dev-режиме относительный путь проксируется Vite на бэкенд.
const DEV_API_PREFIX = "/api/v1";
// Бэкенд всегда поднят локально на этом адресе (совпадает с BACKEND_PORT в src-tauri/src/lib.rs).
const BACKEND_BASE_URL = "http://127.0.0.1:8765";
// В собранном приложении нет Vite-прокси, поэтому нужен абсолютный URL бэкенда.
const PROD_API_BASE_URL = `${BACKEND_BASE_URL}${DEV_API_PREFIX}`;

/** Плитки по умолчанию, если реестр сервисов недоступен. */
const DEFAULT_UNITS: AppUnit[] = [
  { key: "schedule", title: "Расписание", is_enabled: true, order: 1 },
  { key: "weather", title: "Погода", is_enabled: true, order: 2 },
];

const DEFAULT_CONFIG: KioskConfig = {
  // 2 минуты (по ТЗ). Значение станет настраиваемым из админки.
  inactivityTimeoutMs: 2 * 60 * 1000,
  apiBaseUrl: DEV_API_PREFIX,
  // По умолчанию приветствие не задано — главный экран показывает стандартный подзаголовок.
  welcomeMessage: "",
  // По умолчанию расписание показывается одним изображением.
  scheduleMode: "single",
  units: DEFAULT_UNITS,
  weatherEnabled: false,
  weatherLocation: "Москва",
  announcementsEnabled: false,
  announcementsTickerEnabled: false,
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

/** Ответ публичного эндпоинта `GET /api/v1/kiosk/config`. */
interface KioskPublicConfig {
  welcome_message: string | null;
  schedule_mode: "single" | "week";
  weather_enabled?: boolean;
  weather_location?: string;
  weather_refresh_interval_minutes?: number;
  announcements_enabled?: boolean;
  announcements_ticker_enabled?: boolean;
  units?: AppUnit[];
}

/**
 * Загружает актуальные настройки киоска с бэкенда.
 *
 * Публичный эндпоинт `GET /api/v1/kiosk/config` отдаёт параметры главного
 * экрана (приветствие, режим расписания, реестр сервисов) без авторизации.
 * Если бэкенд недоступен — возвращаем значения по умолчанию, чтобы киоск
 * продолжал работать автономно.
 *
 * @returns Копия актуальной конфигурации киоска.
 */
export async function loadKioskConfig(): Promise<KioskConfig> {
  const base = getKioskConfig();
  const url = `${base.apiBaseUrl}/kiosk/config`;
  // Диагностика: видно, что запрашиваем и что вернул бэкенд.
  console.info("[kiosk-config] fetch:", url);
  try {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) {
      console.warn(
        `[kiosk-config] HTTP ${response.status} — возвращаю локальные дефолты`
      );
      return { ...base };
    }
    const remote = (await response.json()) as KioskPublicConfig;
    console.info("[kiosk-config] ok:", remote);
    return {
      ...base,
      welcomeMessage: remote.welcome_message ?? "",
      scheduleMode: remote.schedule_mode,
      units:
        remote.units && remote.units.length > 0 ? remote.units : base.units,
      weatherEnabled: remote.weather_enabled ?? base.weatherEnabled,
      weatherLocation: remote.weather_location ?? base.weatherLocation,
      announcementsEnabled:
        remote.announcements_enabled ?? base.announcementsEnabled,
      announcementsTickerEnabled:
        remote.announcements_ticker_enabled ?? base.announcementsTickerEnabled,
    };
  } catch (e) {
    console.warn("[kiosk-config] fetch error — возвращаю локальные дефолты", e);
    return { ...base };
  }
}
