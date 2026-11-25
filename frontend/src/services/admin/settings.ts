import { getKioskConfig } from "../../config/kioskConfig";
import { bearerHeaders, requireAdminToken } from "../http";
import type { ScheduleMode } from "../../types/schedule";

const ADMIN_API_PATH = "/admin";

/** Провайдер прогноза погоды. */
export type WeatherApi = "wttr.in";

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
  /** Включён ли сервис погоды. */
  weather_enabled: boolean;
  /** Провайдер прогноза погоды. */
  weather_api: WeatherApi;
  /** Населённый пункт для прогноза. */
  weather_location: string;
  /** Интервал обновления прогноза, минут. */
  weather_refresh_interval_minutes: number;
  /** Включён ли сервис объявлений. */
  announcements_enabled: boolean;
  /** Показывать бегущую строку объявлений. */
  announcements_ticker_enabled: boolean;
}

/** Значения настроек, отправляемые на сохранение (PUT). */
export interface AdminSettingsUpdate {
  local_image_dir: string | null;
  schedule_mode: ScheduleMode;
  welcome_message: string | null;
  autostart: boolean;
  weather_enabled: boolean;
  weather_api: WeatherApi;
  weather_location: string;
  weather_refresh_interval_minutes: number;
  announcements_enabled: boolean;
  announcements_ticker_enabled: boolean;
}

/** Возвращает текущие настройки админки. Требует действующий токен. */
export async function fetchAdminSettings(): Promise<AdminSettings> {
  const token = requireAdminToken();
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
export async function updateAdminSettings(
  settings: AdminSettingsUpdate
): Promise<AdminSettings> {
  const token = requireAdminToken();
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
