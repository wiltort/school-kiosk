import { useEffect, useState } from "react";
import AdminPersonIcon from "../components/AdminPersonIcon";
import HomeButton from "../components/HomeButton";
import {
  useAdminSettings,
  useUpdateAdminSettings,
} from "../hooks/useAdminSettings";
import {
  useCreateSchedule,
  useDeleteSchedule,
  useScheduleImages,
  useSetSingleActive,
  useUpdateSchedule,
} from "../hooks/useScheduleImages";
import {
  loginAdmin,
  scheduleImageUrl,
  type ScheduleFormValues,
  type ScheduleMode,
} from "../services/api";
import type { ScheduleImage } from "../types/schedule";

/** Раздел админ-панели, открываемый из строки меню. */
export type AdminSection = "settings" | "schedules" | "about";

const SECTION_TITLES: Record<AdminSection, string> = {
  settings: "Настройки",
  schedules: "Расписания",
  about: "О проекте",
};

// ============================================================================
// Экран входа в админку (логин/пароль)
// ============================================================================

interface AdminLoginProps {
  /** Возврат на главный экран киоска без входа. */
  onHome: () => void;
  /** Успешный вход: возвращаемся на главный экран, админ-режим активен. */
  onSuccess: () => void;
}

/** Форма входа в админку. После успеха не открывает панель, а возвращает на главный экран. */
export function AdminLogin({ onHome, onSuccess }: AdminLoginProps) {
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState<string | null>(null);
  const [loggingIn, setLoggingIn] = useState(false);

  const handleLogin = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoggingIn(true);
    setAuthError(null);
    try {
      await loginAdmin(login, password);
      onSuccess();
    } catch (e) {
      setAuthError(e instanceof Error ? e.message : "Ошибка входа");
    } finally {
      setLoggingIn(false);
    }
  };

  return (
    <div className="admin-view">
      <div className="admin-header">
        <HomeButton onHome={onHome} label="Киоск" />
        <h1 className="admin-title">Вход в админку</h1>
      </div>

      <form className="admin-login" onSubmit={handleLogin}>
        <h2 className="admin-subtitle">Авторизация</h2>
        <label className="admin-field">
          <span>Логин</span>
          <input
            type="text"
            value={login}
            autoComplete="username"
            onChange={(e) => setLogin(e.target.value)}
            required
          />
        </label>
        <label className="admin-field">
          <span>Пароль</span>
          <input
            type="password"
            value={password}
            autoComplete="current-password"
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>
        {authError && <p className="admin-error">{authError}</p>}
        <button type="submit" className="admin-button" disabled={loggingIn}>
          {loggingIn ? "Вход..." : "Войти"}
        </button>
        <small className="admin-hint">
          После входа вы останетесь на главном экране — сверху появится строка
          меню администратора.
        </small>
      </form>
    </div>
  );
}

// ============================================================================
// Строка меню администратора (показывается на всех экранах после входа)
// ============================================================================

interface AdminMenuBarProps {
  /** Активный раздел (подсвечивается); null — на главном экране. */
  activeSection: AdminSection | null;
  /** Открытие раздела. */
  onSectionChange: (section: AdminSection) => void;
  /** Выход из режима админа. */
  onExit: () => void;
}

/** Верхняя строка меню админки: «Настройки», «Расписания», «О проекте» и выход. */
export function AdminMenuBar({
  activeSection,
  onSectionChange,
  onExit,
}: AdminMenuBarProps) {
  const items: { id: AdminSection; label: string }[] = [
    { id: "settings", label: "Настройки" },
    { id: "schedules", label: "Расписания" },
    { id: "about", label: "О проекте" },
  ];

  return (
    <nav className="admin-menu admin-menu--top">
      <div className="admin-menu__nav">
        {items.map((item) => (
          <button
            key={item.id}
            type="button"
            className={
              activeSection === item.id
                ? "admin-menu__item admin-menu__item--active"
                : "admin-menu__item"
            }
            onClick={() => onSectionChange(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>
      <button
        type="button"
        className="admin-menu__exit"
        aria-label="Выйти из админки"
        title="Выйти из админки"
        onClick={onExit}
      >
        <AdminPersonIcon size={30} isAdmin title="Выйти из админки" />
      </button>
    </nav>
  );
}

// ============================================================================
// Панель администратора (раздел выбран в строке меню)
// ============================================================================

interface AdminPanelProps {
  /** Выбранный раздел. */
  section: AdminSection;
  /** Возврат на главный экран киоска. */
  onHome: () => void;
  /** Вызывается после сохранения настроек (для обновления главного экрана). */
  onSettingsSaved?: () => void;
}

/** Контейнер выбранного раздела админки под строкой меню. */
export function AdminPanel({
  section,
  onHome,
  onSettingsSaved,
}: AdminPanelProps) {
  return (
    <div className="admin-view">
      <div className="admin-header">
        <HomeButton onHome={onHome} label="Киоск" />
        <h1 className="admin-title">{SECTION_TITLES[section]}</h1>
      </div>

      {section === "settings" && <SettingsPanel onSaved={onSettingsSaved} />}
      {section === "schedules" && <SchedulesPanel />}
      {section === "about" && <AboutPanel />}
    </div>
  );
}

// ============================================================================
// Раздел «Настройки»
// ============================================================================

interface SettingsPanelProps {
  /** Вызывается после успешного сохранения. */
  onSaved?: () => void;
}

function SettingsPanel({ onSaved }: SettingsPanelProps) {
  const { data: settings, isLoading, error: loadError } = useAdminSettings();
  const updateMutation = useUpdateAdminSettings();

  const [localImageDir, setLocalImageDir] = useState("");
  const [scheduleMode, setScheduleMode] = useState<ScheduleMode>("single");
  const [welcomeMessage, setWelcomeMessage] = useState("");
  const [autostart, setAutostart] = useState(false);
  const [autostartSupported, setAutostartSupported] = useState(true);
  const [notice, setNotice] = useState<string | null>(null);

  // Синхронизируем поля формы с настройками из React Query-кеша.
  useEffect(() => {
    if (!settings) {
      return;
    }
    setLocalImageDir(settings.local_image_dir ?? "");
    setScheduleMode(settings.schedule_mode);
    setWelcomeMessage(settings.welcome_message ?? "");
    setAutostart(settings.autostart);
    setAutostartSupported(settings.autostart_supported);
  }, [settings]);

  const handleSave = async (event: React.FormEvent) => {
    event.preventDefault();
    setNotice(null);
    try {
      await updateMutation.mutateAsync({
        local_image_dir: localImageDir.trim() || null,
        schedule_mode: scheduleMode,
        welcome_message: welcomeMessage.trim() || null,
        autostart,
      });
      setNotice("Настройки сохранены.");
      onSaved?.();
    } catch {
      /* ошибка отображается через updateMutation.error */
    }
  };

  return (
    <form className="admin-settings" onSubmit={handleSave}>
      <h2 className="admin-subtitle">Настройки</h2>

      {isLoading && <p className="admin-hint">Загрузка настроек…</p>}
      {loadError && !isLoading && (
        <p className="admin-error">
          {loadError instanceof Error
            ? loadError.message
            : "Не удалось загрузить настройки"}
        </p>
      )}

      <label className="admin-field">
        <span>Папка локальных расписаний</span>
        <input
          type="text"
          value={localImageDir}
          placeholder="Оставьте пустым — используется папка по умолчанию"
          onChange={(e) => setLocalImageDir(e.target.value)}
        />
        <small>
          Путь на диске киоска, например <code>D:\KioskLocal</code>. Пустое поле
          — значение по умолчанию.
        </small>
      </label>

      <label className="admin-field">
        <span>Режим расписания</span>
        <select
          value={scheduleMode}
          onChange={(e) => setScheduleMode(e.target.value as ScheduleMode)}
        >
          <option value="single">Одно изображение</option>
          <option value="week">Неделя (по дням)</option>
        </select>
        <small>
          Как киоск показывает расписание: одним изображением или недельным
          набором.
        </small>
      </label>

      <label className="admin-field">
        <span>Приветственное сообщение</span>
        <input
          type="text"
          value={welcomeMessage}
          placeholder="Например: Добро пожаловать в школу!"
          onChange={(e) => setWelcomeMessage(e.target.value)}
        />
        <small>Показывается на главном экране под заголовком.</small>
      </label>

      <label className="admin-check">
        <input
          type="checkbox"
          checked={autostart}
          disabled={!autostartSupported}
          onChange={(e) => setAutostart(e.target.checked)}
        />
        <span>Автозапуск программы при входе в систему</span>
      </label>
      {!autostartSupported && (
        <small className="admin-hint">
          Автозагрузка не поддерживается на этой системе.
        </small>
      )}

      {updateMutation.error && (
        <p className="admin-error">
          {updateMutation.error instanceof Error
            ? updateMutation.error.message
            : "Ошибка сохранения"}
        </p>
      )}
      {notice && <p className="admin-notice">{notice}</p>}

      <div className="admin-actions">
        <button
          type="submit"
          className="admin-button"
          disabled={updateMutation.isPending || isLoading}
        >
          {updateMutation.isPending ? "Сохранение..." : "Сохранить"}
        </button>
      </div>
    </form>
  );
}

// ============================================================================
// Раздел «Расписания»
// ============================================================================

const DAY_OF_WEEK_LABELS: Record<number, string> = {
  1: "Понедельник",
  2: "Вторник",
  3: "Среда",
  4: "Четверг",
  5: "Пятница",
  6: "Суббота",
  7: "Воскресенье",
};

function dayOfWeekLabel(day: number): string {
  return DAY_OF_WEEK_LABELS[day] ?? `День ${day}`;
}

/** Состояние открытого диалога формы расписания. */
type ScheduleDialogState =
  { mode: "create" } | { mode: "edit"; schedule: ScheduleImage };

function SchedulesPanel() {
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
            <article key={schedule.id} className="schedule-card">
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
                  onClick={() => handleActivate(schedule)}
                >
                  Активировать
                </button>
                <button
                  type="button"
                  className="admin-button admin-button--small admin-button-ghost"
                  onClick={() => setDialog({ mode: "edit", schedule })}
                >
                  Редактировать
                </button>
                <button
                  type="button"
                  className="admin-button admin-button--small admin-button-danger"
                  onClick={() => setDeleteTarget(schedule)}
                >
                  Удалить
                </button>
              </div>
            </article>
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
function ScheduleFormDialog({
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

  const handleSubmit = (event: React.FormEvent) => {
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
            disabled={scheduleMode === "single"}
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

interface ConfirmDialogProps {
  title: string;
  text: string;
  confirmLabel: string;
  submitting: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/** Диалог подтверждения деструктивного действия (например, удаления). */
function ConfirmDialog({
  title,
  text,
  confirmLabel,
  submitting,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  return (
    <div className="admin-modal-overlay" role="alertdialog" aria-modal="true">
      <div className="admin-modal">
        <h2 className="admin-subtitle">{title}</h2>
        <p className="admin-text">{text}</p>
        <div className="admin-modal__actions">
          <button
            type="button"
            className="admin-button admin-button-ghost"
            onClick={onCancel}
            disabled={submitting}
          >
            Отмена
          </button>
          <button
            type="button"
            className="admin-button admin-button-danger"
            onClick={onConfirm}
            disabled={submitting}
          >
            {submitting ? "Удаление..." : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Раздел «О проекте»
// ============================================================================

function AboutPanel() {
  return (
    <div className="admin-settings">
      <h2 className="admin-subtitle">О проекте</h2>
      <p className="admin-text">
        «Школьный киоск» — информационный терминал для школ. На главном экране
        посетители видят расписание и погоду, а администратор может управлять
        содержимым через эту панель.
      </p>
      <p className="admin-text">
        Версия приложения показана внизу экрана. Обновления устанавливаются
        автоматически через сервер обновлений.
      </p>
    </div>
  );
}
