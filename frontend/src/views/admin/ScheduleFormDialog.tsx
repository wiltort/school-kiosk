import { useState, type FormEvent } from "react";
import type { ScheduleFormValues } from "../../services/admin/schedules";
import type { ScheduleImage, ScheduleMode } from "../../types/schedule";
import { DAY_OF_WEEK_LABELS } from "./constants";

interface ScheduleFormDialogProps {
  /** Режим диалога: создание или редактирование. */
  mode: "create" | "edit";
  /** Редактируемое расписание (только для mode="edit"). */
  schedule?: ScheduleImage;
  /** Режим отображения расписания (single/week). */
  scheduleMode: ScheduleMode;
  /** Идёт ли сохранение (блокирует кнопки). */
  submitting: boolean;
  /** Ошибка формы/сохранения. */
  error: string | null;
  /** Отправка формы: значения + выбранный файл (null при редактировании). */
  onSubmit: (values: ScheduleFormValues, file: File | null) => void;
  /** Закрытие диалога без сохранения. */
  onCancel: () => void;
}

/** Диалог добавления/редактирования расписания с кнопками «OK»/«Отмена». */
export function ScheduleFormDialog({
  mode,
  schedule,
  scheduleMode,
  submitting,
  error,
  onSubmit,
  onCancel,
}: ScheduleFormDialogProps) {
  const isCreate = mode === "create";
  const [name, setName] = useState(schedule?.name ?? "");
  const [dayOfWeek, setDayOfWeek] = useState(schedule?.day_of_week ?? 1);
  const [isActive, setIsActive] = useState(schedule?.is_active ?? false);
  const [isLocal, setIsLocal] = useState(schedule?.is_local ?? false);
  const [file, setFile] = useState<File | null>(null);
  const [filename, setFilename] = useState("");

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit(
      {
        name: name.trim(),
        day_of_week: dayOfWeek,
        is_active: isActive,
        is_local: isLocal,
        filename: filename.trim(),
      },
      file
    );
  };

  return (
    <div className="admin-modal-overlay" role="dialog" aria-modal="true">
      <form className="admin-modal" onSubmit={handleSubmit}>
        <h2 className="admin-subtitle">
          {isCreate ? "Добавить расписание" : "Редактировать расписание"}
        </h2>

        <label className="admin-field">
          <span>Название</span>
          <input
            type="text"
            value={name}
            maxLength={255}
            onChange={(e) => setName(e.target.value)}
            required
            autoFocus
          />
        </label>
        {isCreate && (
          <label className="admin-check">
            <input
              type="checkbox"
              checked={isLocal}
              onChange={(e) => setIsLocal(e.target.checked)}
            />
            <span>Сделать локальным</span>
          </label>
        )}
        <label className="admin-field">
          <span>День недели</span>
          <select
            value={dayOfWeek}
            onChange={(e) => setDayOfWeek(Number(e.target.value))}
          >
            {Object.entries(DAY_OF_WEEK_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>

        {isCreate && !isLocal && (
          <label className="admin-field">
            <span>Файл изображения</span>
            <input
              type="file"
              accept="image/*"
              required
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            <small>JPG или PNG — изображение, которое увидит киоск.</small>
          </label>
        )}

        {isCreate && isLocal && (
          <label className="admin-field">
            <span>Имя файла локального изображения</span>
            <input
              type="text"
              value={filename}
              maxLength={255}
              required
              placeholder="например: 1.jpg"
              onChange={(e) => setFilename(e.target.value)}
              autoFocus
            />
            <small>
              Имя файла в каталоге локальных расписаний, например 1.jpg.
            </small>
          </label>
        )}

        <label className="admin-check">
          <input
            type="checkbox"
            checked={isActive}
            disabled={scheduleMode === "single" || scheduleMode === "week"}
            onChange={(e) => setIsActive(e.target.checked)}
          />
          <span>Сделать активным</span>
        </label>
        {scheduleMode === "single" && (
          <small className="admin-hint">
            В режиме «одно расписание» активация выполняется кнопкой
            «Активировать».
          </small>
        )}
        {scheduleMode === "week" && (
          <small className="admin-hint">
            В режиме «расписание на неделю» активация выполняется кнопкой
            «Активировать».
          </small>
        )}
        {error && <p className="admin-error">{error}</p>}

        <div className="admin-modal__actions">
          <button
            type="button"
            className="admin-button admin-button-ghost"
            onClick={onCancel}
            disabled={submitting}
          >
            Отмена
          </button>
          <button type="submit" className="admin-button" disabled={submitting}>
            {submitting ? "Сохранение..." : "OK"}
          </button>
        </div>
      </form>
    </div>
  );
}
