import { getKioskConfig } from "../../config/kioskConfig";
import { bearerHeaders, getAdminToken, requireAdminToken } from "../http";
import type {
  ScheduleImage,
  ResetAllSchedulesResponse,
} from "../../types/schedule";

const SCHEDULE_IMAGES_ADMIN_PATH = "/schedule-images";

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
  const token = requireAdminToken();
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
    // Точное совпадение с маршрутом POST /schedule-images/create-local:
    // без завершающего слеша (старые версии бэкенда не выполняют redirect).
    url = `${apiBaseUrl}${SCHEDULE_IMAGES_ADMIN_PATH}/create-local`;
  } else {
    url = `${apiBaseUrl}${SCHEDULE_IMAGES_ADMIN_PATH}/`;
  }
  const response = await fetch(url, {
    method: "POST",
    headers: bearerHeaders(token),
    body: formData,
  });
  if (!response.ok) {
    let detail: string | null = null;
    try {
      const data = await response.json();
      detail = data.detail;
    } catch {
      // ignore
    }
    throw new Error(
      detail ?? `Ошибка добавления расписания: HTTP ${response.status}`
    );
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
  const token = requireAdminToken();
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
  const token = requireAdminToken();
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
  const token = requireAdminToken();
  const { apiBaseUrl } = getKioskConfig();
  const response = await fetch(
    `${apiBaseUrl}${SCHEDULE_IMAGES_ADMIN_PATH}/${id}/set-single-active`,
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

export async function resetAllSchedules(): Promise<ResetAllSchedulesResponse> {
  const token = requireAdminToken();
  const { apiBaseUrl } = getKioskConfig();
  const response = await fetch(
    `${apiBaseUrl}${SCHEDULE_IMAGES_ADMIN_PATH}/reset-schedules`,
    {
      method: "POST",
      headers: bearerHeaders(token),
    }
  );
  if (!response.ok) {
    throw new Error(`Ошибка активации расписания: HTTP ${response.status}`);
  }
  return (await response.json()) as ResetAllSchedulesResponse;
}
