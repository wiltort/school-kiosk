import { getKioskConfig } from "../config/kioskConfig";
import type { ScheduleImage, ScheduleMode } from "../types/schedule";

// const SCHEDULE_IMAGES_PATH = "/schedule_images_local/";
const GET_SINGLE_SCHEDULE_PATH = "/schedule_images/get_single_schedule";

const ADMIN_TOKEN_KEY = "school_kiosk_admin_token";

/**
 * Загружает список изображений расписания с бэкенда.
 *
 * @returns Изображение расписания.
 * @throws Ошибка при неудачном запросе.
 */
export async function fetchScheduleImage(): Promise<ScheduleImage> {
  const { apiBaseUrl } = getKioskConfig();
  // Не брать метаданные из кеша: расписание могло измениться.
  const response = await fetch(`${apiBaseUrl}${GET_SINGLE_SCHEDULE_PATH}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Ошибка загрузки расписания: HTTP ${response.status}`);
  }
  return (await response.json()) as ScheduleImage;
}

/**
 * Преобразует относительный путь файла из БД в полный URL для отображения.
 *
 * Локальное расписание всегда живёт под одним и тем же именем (например,
 * "1.jpg"), поэтому URL сам по себе не меняется при замене файла. Чтобы
 * браузер/WebView не отдавал устаревшую картинку из HTTP-кеша, добавляем
 * query-параметр cache-buster (обычно — timestamp `updated_at` расписания).
 *
 * @param path Относительный путь файла (например, "2026/09/uuid.png").
 * @param cacheBust Строка/число для инвалидации кеша (например, updated_at).
 * @returns URL изображения под статикой бэкенда (/uploads/...).
 */
export function scheduleImageUrl(
  path: string,
  cacheBust?: string | number
): string {
  const { apiBaseUrl } = getKioskConfig();
  // Статика раздаётся вне api-префикса: убираем "/api/v1" и подставляем "/uploads".
  // Завершающий слэш тоже убираем, чтобы не получить двойной слеш в URL.
  const staticRoot = (apiBaseUrl.replace(/\/api\/v1\/?$/, "") || "").replace(
    /\/+$/,
    ""
  );
  const base = `${staticRoot}/uploads/schedule_images/${path.replace(/^\/+/, "")}`;
  if (cacheBust !== undefined && cacheBust !== null && cacheBust !== "") {
    return `${base}?v=${encodeURIComponent(String(cacheBust))}`;
  }
  return base;
}

// ============================================================================
// Админ-панель
// ============================================================================

export type { ScheduleMode };

/** Настройки приложения, отдаваемые админ-API. */
export interface AdminSettings {
  /** Каталог локальных расписаний; null — значение по умолчанию. */
  local_image_dir: string | null;
  /** Режим отображения расписания. */
  schedule_mode: ScheduleMode;
  /** Приветственное сообщение на главном экране; null — значение по умолчанию. */
  welcome_message: string | null;
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

/** Есть ли активная админ-сессия (токен в sessionStorage). */
export function isAdminLoggedIn(): boolean {
  return getAdminToken() !== null;
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
 * Пустая строка/null для папки локальных расписаний и приветственного
 * сообщения сбрасывает значение в дефолт.
 */
export async function updateAdminSettings(settings: {
  local_image_dir: string | null;
  schedule_mode: ScheduleMode;
  welcome_message: string | null;
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

// ============================================================================
// Расписания (админ-панель)
// ============================================================================

const SCHEDULE_IMAGES_ADMIN_PATH = "/schedule_images";

/** Значения формы расписания (создание/редактирование). */
export interface ScheduleFormValues {
  name: string;
  day_of_week: number;
  is_active: boolean;
  is_local: boolean;
  filename: string;
}

/** Поля метаданных, допустимые при обновлении (PATCH) расписания. */
export interface ScheduleUpdateValues {
  name: string;
  day_of_week: number;
  is_active: boolean;
}

/**
 * Возвращает список всех расписаний. Используется в админ-разделе «Расписания».
 *
 * @throws Error с понятным сообщением при неудачном запросе.
 */
export async function fetchSchedules(): Promise<ScheduleImage[]> {
  const token = getAdminToken();
  const { apiBaseUrl } = getKioskConfig();
  const response = await fetch(`${apiBaseUrl}${SCHEDULE_IMAGES_ADMIN_PATH}/`, {
    headers: token ? bearerHeaders(token) : undefined,
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(
      `Ошибка загрузки списка расписаний: HTTP ${response.status}`
    );
  }
  return (await response.json()) as ScheduleImage[];
}

/**
 * Создаёт расписание: multipart-форма с метаданными и файлом изображения.
 *
 * @throws Error с понятным сообщением при неудачном запросе.
 */
export async function createSchedule(
  values: ScheduleFormValues,
  file: File | null
): Promise<ScheduleImage> {
  const token = getAdminToken();
  if (!token) {
    throw new Error("Нет авторизации");
  }
  const formData = new FormData();
  formData.append("name", values.name);
  formData.append("day_of_week", String(values.day_of_week));
  formData.append("is_active", String(values.is_active));
  if (values.is_local) {
    formData.append("filename", String(values.filename));
  } else {
    if (!file) {
      throw new Error("Файл изображения не выбран");
    }
    formData.append("image", file);
  }

  const { apiBaseUrl } = getKioskConfig();
  let url: string;
  if (values.is_local) {
    // Точное совпадение с маршрутом POST /schedule_images/create_local:
    // без завершающего слеша (старые версии бэкенда не выполняют redirect).
    url = `${apiBaseUrl}${SCHEDULE_IMAGES_ADMIN_PATH}/create_local`;
  } else {
    url = `${apiBaseUrl}${SCHEDULE_IMAGES_ADMIN_PATH}/`;
  }
  const response = await fetch(url, {
    method: "POST",
    headers: bearerHeaders(token),
    body: formData,
  });
  if (!response.ok) {
    throw new Error(`Ошибка добавления расписания: HTTP ${response.status}`);
  }
  return (await response.json()) as ScheduleImage;
}

/**
 * Обновляет метаданные расписания (JSON-патч).
 *
 * @throws Error с понятным сообщением при неудачном запросе.
 */
export async function updateSchedule(
  id: string,
  values: ScheduleUpdateValues
): Promise<ScheduleImage> {
  const token = getAdminToken();
  if (!token) {
    throw new Error("Нет авторизации");
  }
  const { apiBaseUrl } = getKioskConfig();
  const response = await fetch(
    `${apiBaseUrl}${SCHEDULE_IMAGES_ADMIN_PATH}/${id}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ...bearerHeaders(token) },
      body: JSON.stringify(values),
    }
  );
  if (!response.ok) {
    throw new Error(`Ошибка сохранения расписания: HTTP ${response.status}`);
  }
  return (await response.json()) as ScheduleImage;
}

/** Удаляет расписание вместе с файлом изображения. */
export async function deleteSchedule(id: string): Promise<void> {
  const token = getAdminToken();
  if (!token) {
    throw new Error("Нет авторизации");
  }
  const { apiBaseUrl } = getKioskConfig();
  const response = await fetch(
    `${apiBaseUrl}${SCHEDULE_IMAGES_ADMIN_PATH}/${id}`,
    {
      method: "DELETE",
      headers: bearerHeaders(token),
    }
  );
  if (!response.ok) {
    throw new Error(`Ошибка удаления расписания: HTTP ${response.status}`);
  }
}

/**
 * Активирует единственное расписание в сингл-режиме: деактивирует остальные
 * одной транзакцией на бэкенде.
 *
 * @throws Error с понятным сообщением при неудачном запросе.
 */
export async function setSingleActiveSchedule(
  id: string
): Promise<ScheduleImage> {
  const token = getAdminToken();
  if (!token) {
    throw new Error("Нет авторизации");
  }
  const { apiBaseUrl } = getKioskConfig();
  const response = await fetch(
    `${apiBaseUrl}${SCHEDULE_IMAGES_ADMIN_PATH}/${id}/set_single_active`,
    {
      method: "POST",
      headers: bearerHeaders(token),
    }
  );
  if (!response.ok) {
    throw new Error(`Ошибка активации расписания: HTTP ${response.status}`);
  }
  return (await response.json()) as ScheduleImage;
}
