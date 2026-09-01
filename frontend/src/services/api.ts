import { getKioskConfig } from "../config/kioskConfig";
import type { ScheduleImage } from "../types/schedule";

const SCHEDULE_IMAGES_PATH = "/schedule_images_local/";

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
