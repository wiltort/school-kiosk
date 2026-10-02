import { useState } from "react";
import { useAdminSettings } from "../../hooks/useAdminSettings";
import {
  useCreateSchedule,
  useDeleteSchedule,
  useScheduleImages,
  useSetSingleActive,
  useUpdateSchedule,
  useResetAllSchedules,
  useSetActiveScheduleAtDay,
} from "../../hooks/useScheduleImages";
import type { ScheduleFormValues } from "../../services/admin/schedules";
import type { ScheduleImage } from "../../types/schedule";
import { ConfirmDialog } from "./ConfirmDialog";
import { ScheduleCard } from "./ScheduleCard";
import { ScheduleFormDialog } from "./ScheduleFormDialog";
import { WeekSchedulesBar } from "./WeekSchedules";

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
  const activateAtDayMutation = useSetActiveScheduleAtDay();
  const deactivateMutation = useResetAllSchedules();
  const [isDeactivating, setIsDeactivating] = useState(false);

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
      }
      if (scheduleMode === "week") {
        await activateAtDayMutation.mutateAsync(schedule.id);
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

  const handleDeactivate = async () => {
    try {
      await deactivateMutation.mutateAsync();
      setIsDeactivating(false);
    } catch {
      /* ошибка показывается через deactivateMutation.error ниже */
    }
  };

  return (
    <div className="schedule-admin">
      <div className="schedule-admin__toolbar">
        <button
          type="button"
          className="admin-button"
          onClick={() => setIsDeactivating(true)}
        >
          Выключить все расписания
        </button>
        <button
          type="button"
          className="admin-button"
          onClick={() => setDialog({ mode: "create" })}
        >
          + Добавить расписание
        </button>
      </div>

      {scheduleMode === "week" && !isLoading && !isError && (
        <WeekSchedulesBar schedules={schedules} />
      )}

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
      {deactivateMutation.isError && (
        <p className="admin-error">
          {deactivateMutation.error instanceof Error
            ? deactivateMutation.error.message
            : "Не удалось деактивировать расписания"}
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
      {isDeactivating && (
        <ConfirmDialog
          title="Деактивировать расписания?"
          text="Вы уверены, что хотите деактивировать все расписания? Киоск перестанет показывать их."
          confirmLabel="Деактивировать"
          submitting={deactivateMutation.isPending}
          onConfirm={handleDeactivate}
          onCancel={() => setIsDeactivating(false)}
        />
      )}
    </div>
  );
}
