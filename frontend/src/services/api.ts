import { getKioskConfig } from "../config/kioskConfig";
import type { ScheduleImage } from "../types/schedule";

const SCHEDULE_IMAGES_PATH = "/schedule_images_local/";

const ADMIN_TOKEN_KEY = "school_kiosk_admin_token";

/**
 * Загружает список изображений расписания с бэкенда.
 *
 * @returns Изображение расписания.
 * @throws Ошибка при неудачном запросе.
 */
export async function fetchScheduleImage(): Promise<ScheduleImage> {
  const { apiBaseUrl } = getKioskConfig();
  const response = await fetch(`${apiBaseUrl}${SCHEDULE_IMAGES_PATH}`);
  if (!response.ok) {
    throw new Error(`Ошибка загрузки расписания: HTTP ${response.status}`);
  }
  return (await response.json()) as ScheduleImage;
}

/**
 * Преобразует относительный путь файла из БД в полный URL для отображения.
 *
 * @param path Относительный путь файла (например, "2026/09/uuid.png").
 * @returns URL изображения под статикой бэкенда (/uploads/...).
 */
export function scheduleImageUrl(path: string): string {
  const { apiBaseUrl } = getKioskConfig();
  // Статика раздаётся вне api-префикса: убираем "/api/v1" и подставляем "/uploads".
  const staticRoot = apiBaseUrl.replace(/\/api\/v1\/?$/, "") || "";
  return `${staticRoot}/uploads/${path.replace(/^\/+/, "")}`;
}

// ============================================================================
// Админ-панель
// ============================================================================

/** Настройки приложения, отдаваемые админ-API. */
export interface AdminSettings {
  /** Каталог изображений расписания; null — значение по умолчанию. */
  static_dir: string | null;
  /** Включена ли автозагрузка при входе в систему. */
  autostart: boolean;
  /** Поддерживает ли текущая платформа автозагрузку. */
  autostart_supported: boolean;
}

const ADMIN_API_PATH = "/admin";

function getAdminToken(): string | null {
  try {
    return sessionStorage.getItem(ADMIN_TOKEN_KEY);
  } catch {
    return null;
  }
}

function setAdminToken(token: string | null): void {
  try {
    if (token) {
      sessionStorage.setItem(ADMIN_TOKEN_KEY, token);
    } else {
      sessionStorage.removeItem(ADMIN_TOKEN_KEY);
    }
  } catch {
    /* ignore: sessionStorage может быть недоступен */
  }
}

function bearerHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

/**
 * Вход в админку. При успехе сохраняет токен сессии.
 *
 * @throws Error с понятным сообщением при неверных данных.
 */
export async function loginAdmin(
  login: string,
  password: string
): Promise<void> {
  const { apiBaseUrl } = getKioskConfig();
  const response = await fetch(`${apiBaseUrl}${ADMIN_API_PATH}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ login, password }),
  });
  if (!response.ok) {
    throw new Error("Неверный логин или пароль");
  }
  const data = (await response.json()) as { token: string };
  setAdminToken(data.token);
}

/** Выход из админки (инвалидирует токен на сервере). */
export async function logoutAdmin(): Promise<void> {
  const token = getAdminToken();
  setAdminToken(null);
  if (!token) {
    return;
  }
  try {
    const { apiBaseUrl } = getKioskConfig();
    await fetch(`${apiBaseUrl}${ADMIN_API_PATH}/logout`, {
      method: "POST",
      headers: bearerHeaders(token),
    });
  } catch {
    /* токен уже очищен локально — выход считаем состоявшимся */
  }
}

/** Возвращает текущие настройки админки. Требует действующий токен. */
export async function fetchAdminSettings(): Promise<AdminSettings> {
  const token = getAdminToken();
  if (!token) {
    throw new Error("Нет авторизации");
  }
  const { apiBaseUrl } = getKioskConfig();
  const response = await fetch(`${apiBaseUrl}${ADMIN_API_PATH}/settings`, {
    headers: bearerHeaders(token),
  });
  if (!response.ok) {
    throw new Error(`Ошибка загрузки настроек: HTTP ${response.status}`);
  }
  return (await response.json()) as AdminSettings;
}

/**
 * Сохраняет настройки админки. Требует действующий токен.
 *
 * @param staticDir Путь к папке изображений; пустая строка/null сбрасывает в дефолт.
 */
export async function updateAdminSettings(settings: {
  static_dir: string | null;
  autostart: boolean;
}): Promise<AdminSettings> {
  const token = getAdminToken();
  if (!token) {
    throw new Error("Нет авторизации");
  }
  const { apiBaseUrl } = getKioskConfig();
  const response = await fetch(`${apiBaseUrl}${ADMIN_API_PATH}/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...bearerHeaders(token) },
    body: JSON.stringify(settings),
  });
  if (!response.ok) {
    throw new Error(`Ошибка сохранения настроек: HTTP ${response.status}`);
  }
  return (await response.json()) as AdminSettings;
}
