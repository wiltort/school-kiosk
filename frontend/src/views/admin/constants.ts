/** Раздел админ-панели, открываемый из строки меню. */
export type AdminSection = "settings" | "schedules" | "about";

export const SECTION_TITLES: Record<AdminSection, string> = {
  settings: "Настройки",
  schedules: "Расписания",
  about: "О проекте",
};

export const DAY_OF_WEEK_LABELS: Record<number, string> = {
  1: "Понедельник",
  2: "Вторник",
  3: "Среда",
  4: "Четверг",
  5: "Пятница",
  6: "Суббота",
  7: "Воскресенье",
};

export function dayOfWeekLabel(day: number): string {
  return DAY_OF_WEEK_LABELS[day] ?? `День ${day}`;
}
