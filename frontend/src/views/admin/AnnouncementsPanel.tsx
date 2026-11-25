import { useState } from "react";
import {
  useAdminAnnouncements,
  useCreateAnnouncement,
  useDeleteAnnouncement,
  useUpdateAnnouncement,
} from "../../hooks/useAdminAnnouncements";
import type { AnnouncementFormValues } from "../../services/admin/announcements";
import type {
  Announcement,
  AnnouncementKind,
} from "../../services/announcements";
import { AnnouncementFormDialog } from "./AnnouncementFormDialog";
import { ConfirmDialog } from "./ConfirmDialog";

/** Состояние открытого диалога формы объявления. */
type AnnouncementDialogState =
  { mode: "create" } | { mode: "edit"; announcement: Announcement };

const KIND_LABELS: Record<AnnouncementKind, string> = {
  both: "Везде",
  ticker: "Бегущая строка",
  feed: "Лента",
};

function formatDateTime(value: string | null): string {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatWindow(item: Announcement): string {
  const parts: string[] = [];
  if (item.starts_at) {
    parts.push(`с ${formatDateTime(item.starts_at)}`);
  }
  if (item.expires_at) {
    parts.push(`до ${formatDateTime(item.expires_at)}`);
  }
  return parts.join(" ");
}

export function AnnouncementsPanel() {
  const { data = [], isLoading, isError, error } = useAdminAnnouncements();
  const createMutation = useCreateAnnouncement();
  const updateMutation = useUpdateAnnouncement();
  const deleteMutation = useDeleteAnnouncement();

  const [dialog, setDialog] = useState<AnnouncementDialogState | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Announcement | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const closeDialog = () => {
    setDialog(null);
    setFormError(null);
  };

  const handleSubmit = async (values: AnnouncementFormValues) => {
    setFormError(null);
    try {
      if (dialog?.mode === "create") {
        await createMutation.mutateAsync(values);
      } else if (dialog?.mode === "edit") {
        await updateMutation.mutateAsync({
          id: dialog.announcement.id,
          input: values,
        });
      }
      closeDialog();
    } catch (e) {
      setFormError(
        e instanceof Error ? e.message : "Не удалось сохранить объявление"
      );
    }
  };

  const handleToggle = async (item: Announcement) => {
    try {
      await updateMutation.mutateAsync({
        id: item.id,
        input: { is_active: !item.is_active },
      });
    } catch {
      /* ошибка показывается через updateMutation.error */
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) {
      return;
    }
    try {
      await deleteMutation.mutateAsync(deleteTarget.id);
      setDeleteTarget(null);
    } catch {
      /* ошибка показывается через deleteMutation.error */
    }
  };

  return (
    <div className="content-admin">
      <div className="content-admin__toolbar">
        <button
          type="button"
          className="admin-button"
          onClick={() => setDialog({ mode: "create" })}
        >
          + Добавить объявление
        </button>
      </div>

      {isLoading && <p className="admin-hint">Загрузка объявлений…</p>}
      {isError && !isLoading && (
        <p className="admin-error">
          {error instanceof Error
            ? error.message
            : "Не удалось загрузить объявления"}
        </p>
      )}

      {!isLoading && !isError && data.length === 0 && (
        <p className="admin-text">
          Объявлений пока нет. Нажмите «Добавить объявление», чтобы создать
          первое.
        </p>
      )}

      {data.length > 0 && (
        <ul className="content-admin__list">
          {data.map((item) => (
            <li key={item.id} className="content-admin__item">
              <div className="content-admin__item-main">
                <div className="content-admin__item-head">
                  <strong>{item.title}</strong>
                  <span
                    className={
                      item.is_active
                        ? "content-admin__badge content-admin__badge--on"
                        : "content-admin__badge"
                    }
                  >
                    {item.is_active ? "Активно" : "Выключено"}
                  </span>
                  <span className="content-admin__badge">
                    {KIND_LABELS[item.kind]}
                  </span>
                </div>
                <p className="content-admin__item-text">{item.body}</p>
                {formatWindow(item) && (
                  <small className="admin-hint">{formatWindow(item)}</small>
                )}
              </div>
              <div className="content-admin__item-actions">
                <button
                  type="button"
                  className="admin-button admin-button-ghost admin-button--small"
                  onClick={() => handleToggle(item)}
                  disabled={updateMutation.isPending}
                >
                  {item.is_active ? "Выключить" : "Включить"}
                </button>
                <button
                  type="button"
                  className="admin-button admin-button-ghost admin-button--small"
                  onClick={() =>
                    setDialog({ mode: "edit", announcement: item })
                  }
                >
                  Изменить
                </button>
                <button
                  type="button"
                  className="admin-button admin-button-danger admin-button--small"
                  onClick={() => setDeleteTarget(item)}
                >
                  Удалить
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {updateMutation.isError && (
        <p className="admin-error">
          {updateMutation.error instanceof Error
            ? updateMutation.error.message
            : "Не удалось сохранить объявление"}
        </p>
      )}
      {deleteMutation.isError && (
        <p className="admin-error">
          {deleteMutation.error instanceof Error
            ? deleteMutation.error.message
            : "Не удалось удалить объявление"}
        </p>
      )}

      {dialog && (
        <AnnouncementFormDialog
          key={dialog.mode === "edit" ? dialog.announcement.id : "create"}
          mode={dialog.mode}
          announcement={
            dialog.mode === "edit" ? dialog.announcement : undefined
          }
          submitting={createMutation.isPending || updateMutation.isPending}
          error={formError}
          onSubmit={handleSubmit}
          onCancel={closeDialog}
        />
      )}

      {deleteTarget && (
        <ConfirmDialog
          title="Удалить объявление?"
          text={`«${deleteTarget.title}» будет удалено с киоска.`}
          confirmLabel="Удалить"
          submitting={deleteMutation.isPending}
          onConfirm={handleDelete}
          onCancel={() => setDeleteTarget(null)}
        />
      )}
    </div>
  );
}
