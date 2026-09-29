import HomeButton from "../components/HomeButton";
import { useScheduleImage } from "../hooks/useScheduleImage";
import { scheduleImageUrl } from "../services/api";

interface ScheduleViewProps {
  onHome: () => void;
}

/** Экран расписания: отображает изображение(я) расписания и кнопку «Домой». */
export default function ScheduleView({ onHome }: ScheduleViewProps) {
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
        <figure key={schedule.id} className="schedule__figure">
          <img
            className="schedule__image"
            src={scheduleImageUrl(schedule.image, schedule.updated_at)}
            alt={schedule.name}
          />
          <figcaption className="schedule__caption">{schedule.name}</figcaption>
        </figure>
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
