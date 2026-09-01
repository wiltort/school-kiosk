import { useCallback, useEffect, useState } from "react";
import HomeButton from "../components/HomeButton";
import { fetchScheduleImage, scheduleImageUrl } from "../services/api";
import type { ScheduleImage } from "../types/schedule";

interface ScheduleViewProps {
  onHome: () => void;
}

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; schedule: ScheduleImage };

/** Экран расписания: отображает изображение(я) расписания и кнопку «Домой». */
export default function ScheduleView({ onHome }: ScheduleViewProps) {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;

    fetchScheduleImage()
      .then((schedule) => {
        if (!cancelled) {
          setState({ status: "ready", schedule });
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          const message =
            error instanceof Error ? error.message : "Неизвестная ошибка";
          setState({ status: "error", message });
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const activeSchedule = state.status === "ready"
    ? state.schedule
    : null;

  const renderBody = useCallback(() => {
    if (state.status === "loading") {
      return <p className="schedule__hint">Загрузка расписания…</p>;
    }

    if (state.status === "error") {
      return (
        <div className="schedule__empty">
          <p>Не удалось загрузить расписание.</p>
          <p className="schedule__error">{state.message}</p>
        </div>
      );
    }

    if (!activeSchedule) {
      return (
        <p className="schedule__hint">Активное расписание не загружено.</p>
      );
    }

    return (
      <div className="schedule__images">
          <figure key={activeSchedule.id} className="schedule__figure">
            <img
              className="schedule__image"
              src={scheduleImageUrl(activeSchedule.image)}
              alt={activeSchedule.name}
            />
            <figcaption className="schedule__caption">{activeSchedule.name}</figcaption>
          </figure>
      </div>
    );
  }, [state, activeSchedule]);

  return (
    <section className="schedule">
      <header className="schedule__topbar">
        <HomeButton onHome={onHome} />
      </header>

      <div className="schedule__body">{renderBody()}</div>
    </section>
  );
}
