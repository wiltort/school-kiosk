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

/** Короткие подписи дней недели для бара недельного режима. */
export const DAY_OF_WEEK_SHORT_LABELS: Record<number, string> = {
  1: "ПН",
  2: "ВТ",
  3: "СР",
  4: "ЧТ",
  5: "ПТ",
  6: "СБ",
  7: "ВС",
};

export function dayOfWeekLabel(day: number): string {
  return DAY_OF_WEEK_LABELS[day] ?? `День ${day}`;
}

export function dayOfWeekShortLabel(day: number): string {
  return DAY_OF_WEEK_SHORT_LABELS[day] ?? `День ${day}`;
}

/** Идентификатор карточки расписания в списке расписаний (см. ScheduleCard). */
export function scheduleCardId(id: string): string {
  return `schedule-card-${id}`;
}
