import { scheduleImageUrl } from "../../services/kiosk";
import type { ScheduleImage } from "../../types/schedule";
import { dayOfWeekLabel, scheduleCardId } from "./constants";

interface ScheduleCardProps {
  schedule: ScheduleImage;
  onActivate: () => void;
  onEdit: () => void;
  onDelete: () => void;
}

/** Карточка расписания в админ-разделе «Расписания». */
export function ScheduleCard({
  schedule,
  onActivate,
  onEdit,
  onDelete,
}: ScheduleCardProps) {
  return (
    <article className="schedule-card" id={scheduleCardId(schedule.id)}>
      <div className="schedule-card__preview">
        <img
          className="schedule-card__image"
          src={scheduleImageUrl(schedule.image, schedule.updated_at)}
          alt={schedule.name}
        />
      </div>
      <div className="schedule-card__body">
        <h3 className="schedule-card__name">{schedule.name}</h3>
        <p className="schedule-card__meta">
          {dayOfWeekLabel(schedule.day_of_week)}
        </p>
        <div className="schedule-card__badges">
          {schedule.is_active ? (
            <span className="schedule-badge schedule-badge--active">
              Активно
            </span>
          ) : (
            <span className="schedule-badge">Неактивно</span>
          )}
          {schedule.is_local && (
            <span className="schedule-badge">Локальное</span>
          )}
        </div>
      </div>
      <div className="schedule-card__actions">
        <button
          type="button"
          className="admin-button admin-button--small"
          disabled={schedule.is_active}
          onClick={onActivate}
        >
          Активировать
        </button>
        <button
          type="button"
          className="admin-button admin-button--small admin-button-ghost"
          onClick={onEdit}
        >
          Редактировать
        </button>
        <button
          type="button"
          className="admin-button admin-button--small admin-button-danger"
          onClick={onDelete}
        >
          Удалить
        </button>
      </div>
    </article>
  );
}
