/** Режим отображения расписания (совпадает с backend ScheduleMode). */
export type ScheduleMode = "single" | "week";

/** Изображение расписания (ответ GET /api/v1/schedule-images/). */
export interface ScheduleImage {
  id: string;
  name: string;
  /** Относительный путь к файлу в хранилище (например, "2026/09/uuid.png"). */
  image: string;
  is_active: boolean;
  /** Локальное расписание (файл из каталога локальных расписаний). */
  is_local: boolean;
  day_of_week: number;
  created_at: string;
  updated_at: string;
}
