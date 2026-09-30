import { useEffect, useState, type FormEvent } from "react";
import {
  useAdminSettings,
  useUpdateAdminSettings,
} from "../../hooks/useAdminSettings";
import type { ScheduleMode } from "../../types/schedule";

interface SettingsPanelProps {
  /** Вызывается после успешного сохранения. */
  onSaved?: () => void;
}

export function SettingsPanel({ onSaved }: SettingsPanelProps) {
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

  const handleSave = async (event: FormEvent<HTMLFormElement>) => {
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
