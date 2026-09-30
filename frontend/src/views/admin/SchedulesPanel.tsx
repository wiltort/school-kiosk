import { useState } from "react";
import { useAdminSettings } from "../../hooks/useAdminSettings";
import {
  useCreateSchedule,
  useDeleteSchedule,
  useScheduleImages,
  useSetSingleActive,
  useUpdateSchedule,
} from "../../hooks/useScheduleImages";
import type { ScheduleFormValues } from "../../services/admin/schedules";
import type { ScheduleImage } from "../../types/schedule";
import { ConfirmDialog } from "./ConfirmDialog";
import { ScheduleCard } from "./ScheduleCard";
import { ScheduleFormDialog } from "./ScheduleFormDialog";

/** Состояние открытого диалога формы расписания. */
type ScheduleDialogState =
  { mode: "create" } | { mode: "edit"; schedule: ScheduleImage };

export function SchedulesPanel() {
  const {
    data: schedules = [],
    isLoading,
    isError,
    error,
  } = useScheduleImages();
  const { data: settings } = useAdminSettings();
  const scheduleMode = settings?.schedule_mode ?? "single";

  const createMutation = useCreateSchedule();
  const updateMutation = useUpdateSchedule();
  const deleteMutation = useDeleteSchedule();
  const activateMutation = useSetSingleActive();

  const [dialog, setDialog] = useState<ScheduleDialogState | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ScheduleImage | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const closeDialog = () => {
    setDialog(null);
    setFormError(null);
  };

  const handleFormSubmit = async (
    values: ScheduleFormValues,
    file: File | null
  ) => {
    setFormError(null);
    try {
      if (dialog?.mode === "create") {
        if (!values.is_local && !file) {
          setFormError("Выберите файл изображения.");
          return;
        }
        if (values.is_local && !values.filename.trim()) {
          setFormError("Укажите имя файла локального изображения.");
          return;
        }
        await createMutation.mutateAsync({ values, file });
      } else if (dialog?.mode === "edit") {
        await updateMutation.mutateAsync({ id: dialog.schedule.id, values });
      }
      closeDialog();
    } catch (e) {
      setFormError(
        e instanceof Error ? e.message : "Не удалось сохранить расписание"
      );
    }
  };

  const handleActivate = async (schedule: ScheduleImage) => {
    try {
      if (scheduleMode === "single") {
        await activateMutation.mutateAsync(schedule.id);
      } else {
        // В недельном режиме активация — обычный PATCH метаданных. Бэкенд
        // принимает только name/day_of_week/is_active, поэтому is_local
        // и filename в запрос не уходят (см. ScheduleUpdateValues).
        await updateMutation.mutateAsync({
          id: schedule.id,
          values: {
            name: schedule.name,
            day_of_week: schedule.day_of_week,
            is_active: true,
          },
        });
      }
    } catch {
      /* ошибка показывается через mutation.error ниже */
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
      /* ошибка показывается через deleteMutation.error ниже */
    }
  };

  return (
    <div className="schedule-admin">
      <div className="schedule-admin__toolbar">
        <button
          type="button"
          className="admin-button"
          onClick={() => setDialog({ mode: "create" })}
        >
          + Добавить расписание
        </button>
      </div>

      {isLoading && <p className="admin-hint">Загрузка расписаний…</p>}
      {isError && !isLoading && (
        <p className="admin-error">
          {error instanceof Error
            ? error.message
            : "Не удалось загрузить список расписаний"}
        </p>
      )}

      {!isLoading && !isError && schedules.length === 0 && (
        <p className="admin-text">
          Расписаний пока нет. Нажмите «Добавить расписание», чтобы загрузить
          первое.
        </p>
      )}

      {!isLoading && !isError && schedules.length > 0 && (
        <div className="schedule-admin__grid">
          {schedules.map((schedule) => (
            <ScheduleCard
              key={schedule.id}
              schedule={schedule}
              onActivate={() => handleActivate(schedule)}
              onEdit={() => setDialog({ mode: "edit", schedule })}
              onDelete={() => setDeleteTarget(schedule)}
            />
          ))}
        </div>
      )}

      {activateMutation.isError && (
        <p className="admin-error">
          {activateMutation.error instanceof Error
            ? activateMutation.error.message
            : "Не удалось активировать расписание"}
        </p>
      )}
      {updateMutation.isError && dialog === null && (
        <p className="admin-error">
          {updateMutation.error instanceof Error
            ? updateMutation.error.message
            : "Не удалось сохранить расписание"}
        </p>
      )}
      {deleteMutation.isError && (
        <p className="admin-error">
          {deleteMutation.error instanceof Error
            ? deleteMutation.error.message
            : "Не удалось удалить расписание"}
        </p>
      )}

      {dialog && (
        <ScheduleFormDialog
          key={dialog.mode === "edit" ? dialog.schedule.id : "create"}
          mode={dialog.mode}
          schedule={dialog.mode === "edit" ? dialog.schedule : undefined}
          scheduleMode={scheduleMode}
          submitting={createMutation.isPending || updateMutation.isPending}
          error={formError}
          onSubmit={handleFormSubmit}
          onCancel={closeDialog}
        />
      )}

      {deleteTarget && (
        <ConfirmDialog
          title="Удалить расписание?"
          text={
            deleteTarget.is_active
              ? `«${deleteTarget.name}» — сейчас активное расписание. После удаления киоск перестанет его показывать.`
              : `«${deleteTarget.name}» будет удалено вместе с файлом изображения.`
          }
          confirmLabel="Удалить"
          submitting={deleteMutation.isPending}
          onConfirm={handleDelete}
          onCancel={() => setDeleteTarget(null)}
        />
      )}
    </div>
  );
}
