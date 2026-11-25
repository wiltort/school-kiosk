import { useState, type FormEvent } from "react";
import type { AnnouncementFormValues } from "../../services/admin/announcements";
import type {
  Announcement,
  AnnouncementKind,
} from "../../services/announcements";

interface AnnouncementFormDialogProps {
  mode: "create" | "edit";
  announcement?: Announcement;
  submitting: boolean;
  error: string | null;
  onSubmit: (values: AnnouncementFormValues) => void;
  onCancel: () => void;
}

/** Преобразует ISO-дату в значение для input[type="datetime-local"]. */
function toLocalInput(value: string | null): string {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  const pad = (part: number) => String(part).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(
    date.getDate()
  )}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/** Преобразует значение datetime-local в ISO-строку (или null). */
function toIso(value: string): string | null {
  if (!value) {
    return null;
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

export function AnnouncementFormDialog({
  mode,
  announcement,
  submitting,
  error,
  onSubmit,
  onCancel,
}: AnnouncementFormDialogProps) {
  const [title, setTitle] = useState(announcement?.title ?? "");
  const [body, setBody] = useState(announcement?.body ?? "");
  const [kind, setKind] = useState<AnnouncementKind>(
    announcement?.kind ?? "both"
  );
  const [priority, setPriority] = useState(announcement?.priority ?? 0);
  const [isActive, setIsActive] = useState(announcement?.is_active ?? true);
  const [startsAt, setStartsAt] = useState(
    toLocalInput(announcement?.starts_at ?? null)
  );
  const [expiresAt, setExpiresAt] = useState(
    toLocalInput(announcement?.expires_at ?? null)
  );

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit({
      title: title.trim(),
      body: body.trim(),
      kind,
      priority,
      is_active: isActive,
      starts_at: toIso(startsAt),
      expires_at: toIso(expiresAt),
    });
  };

  return (
    <div className="admin-modal-overlay" role="dialog" aria-modal="true">
      <form className="admin-modal admin-modal--wide" onSubmit={handleSubmit}>
        <h2 className="admin-subtitle">
          {mode === "create" ? "Новое объявление" : "Редактировать объявление"}
        </h2>

        <label className="admin-field">
          <span>Заголовок</span>
          <input
            type="text"
            value={title}
            maxLength={255}
            required
            onChange={(e) => setTitle(e.target.value)}
          />
        </label>

        <label className="admin-field">
          <span>Текст объявления</span>
          <textarea
            value={body}
            rows={5}
            required
            onChange={(e) => setBody(e.target.value)}
          />
        </label>

        <div className="admin-field-row">
          <label className="admin-field">
            <span>Отображение</span>
            <select
              value={kind}
              onChange={(e) => setKind(e.target.value as AnnouncementKind)}
            >
              <option value="both">Везде</option>
              <option value="ticker">Бегущая строка</option>
              <option value="feed">Лента</option>
            </select>
          </label>

          <label className="admin-field">
            <span>Приоритет</span>
            <input
              type="number"
              value={priority}
              onChange={(e) => setPriority(Number(e.target.value) || 0)}
            />
            <small>Больше значение — выше в списке.</small>
          </label>
        </div>

        <div className="admin-field-row">
          <label className="admin-field">
            <span>Начало показа</span>
            <input
              type="datetime-local"
              value={startsAt}
              onChange={(e) => setStartsAt(e.target.value)}
            />
          </label>

          <label className="admin-field">
            <span>Окончание показа</span>
            <input
              type="datetime-local"
              value={expiresAt}
              onChange={(e) => setExpiresAt(e.target.value)}
            />
          </label>
        </div>

        <label className="admin-check">
          <input
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
          />
          <span>Активно</span>
        </label>

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
            {submitting ? "Сохранение..." : "Сохранить"}
          </button>
        </div>
      </form>
    </div>
  );
}
