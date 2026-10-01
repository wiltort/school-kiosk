import { getKioskConfig } from "../config/kioskConfig";
import type { ScheduleImage } from "../types/schedule";

const GET_SINGLE_SCHEDULE_PATH = "/schedule-images/get-single-schedule";

/**
 * Загружает активное изображение расписания с бэкенда.
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
