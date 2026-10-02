import { useMemo, useState } from "react";
import HomeButton from "../components/HomeButton";
import {
  useNextSchedule,
  useScheduleImage,
  useTodaySchedule,
} from "../hooks/useScheduleImage";
import { scheduleImageUrl } from "../services/kiosk";
import type { ScheduleImage, ScheduleMode } from "../types/schedule";

interface ScheduleViewProps {
  onHome: () => void;
  /** Режим отображения расписания (single | week), заданный на бэкенде. */
  scheduleMode: ScheduleMode;
}

/** Названия дней недели в именительном падеже (ISO: 1 — понедельник … 7 — воскресенье). */
const WEEKDAY_NAMES = [
  "понедельник",
  "вторник",
  "среда",
  "четверг",
  "пятница",
  "суббота",
  "воскресенье",
];

/** ISO-день недели (1 — понедельник … 7 — воскресенье) из Date. */
function isoWeekday(date: Date): number {
  return date.getDay() === 0 ? 7 : date.getDay();
}

/**
 * Ближайшая к `from` дата с заданным ISO-днём недели (в пределах ±3 дней).
 * Используется для шапки «сегодня»: дата подбирается по дню недели
 * полученного расписания, чтобы заголовок всегда совпадал с картинкой.
 */
function nearestDateWithWeekday(from: Date, weekday: number): Date {
  const result = new Date(from);
  let diff = weekday - isoWeekday(result);
  if (diff > 3) diff -= 7;
  if (diff < -3) diff += 7;
  result.setDate(result.getDate() + diff);
  return result;
}

/** Первая дата строго после `from` с заданным ISO-днём недели. */
function nextDateWithWeekday(from: Date, weekday: number): Date {
  const result = new Date(from);
  let diff = weekday - isoWeekday(result);
  if (diff <= 0) diff += 7;
  result.setDate(result.getDate() + diff);
  return result;
}

/** Форматирует шапку экрана: «Пятница, 2 октября». */
function formatDayHeader(date: Date): string {
  const weekday = WEEKDAY_NAMES[isoWeekday(date) - 1];
  const dayText = new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "long",
  }).format(date);
  const capitalized = weekday.charAt(0).toUpperCase() + weekday.slice(1);
  return `${capitalized}, ${dayText}`;
}

/** Карточка одного расписания-изображения. */
function ScheduleFigure({ schedule }: { schedule: ScheduleImage }) {
  return (
    <figure className="schedule__figure">
      <img
        className="schedule__image"
        src={scheduleImageUrl(schedule.image, schedule.updated_at)}
        alt={schedule.name}
      />
      <figcaption className="schedule__caption">{schedule.name}</figcaption>
    </figure>
  );
}

/** Сингл-режим: одно активное расписание, без переключения дней. */
function SingleScheduleView({ onHome }: { onHome: () => void }) {
  const { data: schedule, isLoading, isError, error } = useScheduleImage();

  const renderBody = () => {
    if (isLoading) {
      return <p className="schedule__hint">Загрузка расписания…</p>;
    }

    if (isError) {
      return (
        <div className="schedule__empty">
          <p>Не удалось загрузить расписание.</p>
          <p className="schedule__error">
            {error instanceof Error ? error.message : "Неизвестная ошибка"}
          </p>
        </div>
      );
    }

    if (!schedule) {
      return (
        <p className="schedule__hint">Активное расписание не загружено.</p>
      );
    }

    return (
      <div className="schedule__images">
        <ScheduleFigure key={schedule.id} schedule={schedule} />
      </div>
    );
  };

  return (
    <section className="schedule">
      <header className="schedule__topbar">
        <HomeButton onHome={onHome} />
      </header>

      <div className="schedule__body">{renderBody()}</div>
    </section>
  );
}

/**
 * Недельный режим: расписание на сегодня с возможностью переключиться на
 * следующий учебный день (и обратно). Вверху — день недели и дата.
 */
function WeekScheduleView({ onHome }: { onHome: () => void }) {
  const [view, setView] = useState<"today" | "next">("today");
  const todayQuery = useTodaySchedule();
  const nextQuery = useNextSchedule(view === "next");

  const isNext = view === "next";
  const query = isNext ? nextQuery : todayQuery;
  const { data: schedule, isLoading, isError, error } = query;

  // Дата заголовка всегда соответствует дню недели показанного расписания:
  // для «сегодня» — ближайший к текущей дате день, для «следующего дня» —
  // первый день после сегодняшнего с нужным днём недели.
  const headerDate = useMemo(() => {
    if (!schedule) return null;
    const now = new Date();
    return isNext
      ? nextDateWithWeekday(now, schedule.day_of_week)
      : nearestDateWithWeekday(now, schedule.day_of_week);
  }, [schedule, isNext]);

  const renderBody = () => {
    if (isLoading) {
      return <p className="schedule__hint">Загрузка расписания…</p>;
    }

    if (isError) {
      return (
        <div className="schedule__empty">
          <p>
            {isNext
              ? "Расписание на следующие дни не найдено."
              : "Не удалось загрузить расписание."}
          </p>
          <p className="schedule__error">
            {error instanceof Error ? error.message : "Неизвестная ошибка"}
          </p>
        </div>
      );
    }

    if (!schedule) {
      return (
        <p className="schedule__hint">Активное расписание не загружено.</p>
      );
    }

    return (
      <div className="schedule__images">
        <ScheduleFigure key={schedule.id} schedule={schedule} />
      </div>
    );
  };

  return (
    <section className="schedule schedule--week">
      <header className="schedule__topbar">
        <HomeButton onHome={onHome} />
      </header>

      {headerDate && (
        <div className="schedule__day-header">
          <span className="schedule__day" role="heading" aria-level={1}>
            {formatDayHeader(headerDate)}
          </span>
        </div>
      )}

      <div className="schedule__body">{renderBody()}</div>

      <footer className="schedule__footer">
        {isNext ? (
          <button
            type="button"
            className="schedule__toggle-btn"
            onClick={() => setView("today")}
          >
            Расписание на сегодня
          </button>
        ) : (
          <button
            type="button"
            className="schedule__toggle-btn"
            onClick={() => setView("next")}
          >
            Расписание на следующий день
          </button>
        )}
      </footer>
    </section>
  );
}

/**
 * Экран расписания.
 *
 * В режиме «single» показывает единственное активное расписание (как раньше).
 * В режиме «week» показывает расписание на сегодня с заголовком «день недели,
 * число» и кнопкой «Расписание на следующий день» (и обратно на сегодня).
 */
export default function ScheduleView({
  onHome,
  scheduleMode,
}: ScheduleViewProps) {
  return scheduleMode === "week" ? (
    <WeekScheduleView onHome={onHome} />
  ) : (
    <SingleScheduleView onHome={onHome} />
  );
}
