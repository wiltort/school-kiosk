import type { ScheduleImage } from "../../types/schedule";
import { dayOfWeekShortLabel, scheduleCardId } from "./constants";

/** Плавно прокручивает список к карточке расписания. */
function scrollToSchedule(id: ScheduleImage["id"]): void {
  document
    .getElementById(scheduleCardId(id))
    ?.scrollIntoView({ behavior: "smooth", block: "center" });
}

interface ScheduleAtDayOfWeekProps {
  /** Номер дня недели (1 = Пн … 7 = Вс). */
  dayOfWeek: number;
  /** Расписания, назначенные на этот день. */
  schedules: ScheduleImage[];
}

/** Ячейка дня недели в баре недельного режима. */
export function ScheduleAtDayOfWeek({
  dayOfWeek,
  schedules,
}: ScheduleAtDayOfWeekProps) {
  const hasSchedule = schedules.length > 0;

  return (
    <div
      className={
        hasSchedule
          ? "week-schedules__cell week-schedules__cell--filled"
          : "week-schedules__cell week-schedules__cell--empty"
      }
    >
      <button
        type="button"
        className="week-schedules__day"
        disabled={!hasSchedule}
        title={
          hasSchedule
            ? `Перейти к расписанию «${schedules[0].name}»`
            : "Расписания нет"
        }
        onClick={() => hasSchedule && scrollToSchedule(schedules[0].id)}
      >
        {dayOfWeekShortLabel(dayOfWeek)}
      </button>
      <div className="week-schedules__names">
        {hasSchedule ? (
          schedules.map((schedule) => (
            <a
              key={schedule.id}
              className="week-schedules__name"
              href={`#${scheduleCardId(schedule.id)}`}
              title={schedule.name}
              onClick={(event) => {
                event.preventDefault();
                scrollToSchedule(schedule.id);
              }}
            >
              {schedule.name}
            </a>
          ))
        ) : (
          <span className="week-schedules__name week-schedules__name--empty" />
        )}
      </div>
    </div>
  );
}

interface WeekSchedulesBarProps {
  /** Все расписания; группируются по дню недели. */
  schedules: ScheduleImage[];
}

/**
 * Бар дней недели для режима «неделя».
 * Фиксирован на экране: слева (альбомная ориентация) или внизу (портретная),
 * не смещается при прокрутке страницы.
 */
export function WeekSchedulesBar({ schedules }: WeekSchedulesBarProps) {
  const byDay = new Map<number, ScheduleImage[]>();
  for (const schedule of schedules.filter((s) => s.is_active)) {
    const list = byDay.get(schedule.day_of_week) ?? [];
    list.push(schedule);
    byDay.set(schedule.day_of_week, list);
  }

  return (
    <nav className="week-schedules" aria-label="Расписания по дням недели">
      {[1, 2, 3, 4, 5, 6, 7].map((day) => (
        <ScheduleAtDayOfWeek
          key={day}
          dayOfWeek={day}
          schedules={byDay.get(day) ?? []}
        />
      ))}
    </nav>
  );
}
