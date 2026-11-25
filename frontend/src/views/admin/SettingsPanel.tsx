import { useEffect, useState, type FormEvent } from "react";
import {
  useAdminSettings,
  useUpdateAdminSettings,
} from "../../hooks/useAdminSettings";
import type { WeatherApi } from "../../services/admin/settings";
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
  const [weatherEnabled, setWeatherEnabled] = useState(false);
  const [weatherApi, setWeatherApi] = useState<WeatherApi>("wttr.in");
  const [weatherLocation, setWeatherLocation] = useState("Москва");
  const [weatherRefreshInterval, setWeatherRefreshInterval] = useState(60);
  const [announcementsEnabled, setAnnouncementsEnabled] = useState(true);
  const [announcementsTickerEnabled, setAnnouncementsTickerEnabled] =
    useState(true);
  const [notice, setNotice] = useState<string | null>(null);
  const [oldScheduleMode, setOldScheduleMode] =
    useState<ScheduleMode>("single");

  // Синхронизируем поля формы с настройками из React Query-кеша.
  useEffect(() => {
    if (!settings) {
      return;
    }
    setLocalImageDir(settings.local_image_dir ?? "");
    setScheduleMode(settings.schedule_mode);
    setOldScheduleMode(settings.schedule_mode);
    setWelcomeMessage(settings.welcome_message ?? "");
    setAutostart(settings.autostart);
    setAutostartSupported(settings.autostart_supported);
    setWeatherEnabled(settings.weather_enabled);
    setWeatherApi(settings.weather_api);
    setWeatherLocation(settings.weather_location);
    setWeatherRefreshInterval(settings.weather_refresh_interval_minutes);
    setAnnouncementsEnabled(settings.announcements_enabled);
    setAnnouncementsTickerEnabled(settings.announcements_ticker_enabled);
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
        weather_enabled: weatherEnabled,
        weather_api: weatherApi,
        weather_location: weatherLocation.trim() || "Москва",
        weather_refresh_interval_minutes: weatherRefreshInterval,
        announcements_enabled: announcementsEnabled,
        announcements_ticker_enabled: announcementsTickerEnabled,
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
        {oldScheduleMode !== scheduleMode && (
          <small className="admin-hint admin-hint--accent">
            Будут деактивированы все расписания.
          </small>
        )}
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

      <h3 className="admin-subtitle">Погода</h3>

      <label className="admin-check">
        <input
          type="checkbox"
          checked={weatherEnabled}
          onChange={(e) => setWeatherEnabled(e.target.checked)}
        />
        <span>Показывать погоду на киоске</span>
      </label>

      <label className="admin-field">
        <span>Сервис прогноза</span>
        <select
          value={weatherApi}
          onChange={(e) => setWeatherApi(e.target.value as WeatherApi)}
        >
          <option value="wttr.in">wttr.in</option>
        </select>
      </label>

      <label className="admin-field">
        <span>Населённый пункт</span>
        <input
          type="text"
          value={weatherLocation}
          placeholder="Москва"
          onChange={(e) => setWeatherLocation(e.target.value)}
        />
        <small>Используется для запроса прогноза погоды.</small>
      </label>

      <label className="admin-field">
        <span>Интервал обновления, минут</span>
        <input
          type="number"
          min={5}
          max={1440}
          value={weatherRefreshInterval}
          onChange={(e) =>
            setWeatherRefreshInterval(Number(e.target.value) || 60)
          }
        />
        <small>
          От 5 до 1440 минут. Кеш используется при недоступности сети.
        </small>
      </label>

      <h3 className="admin-subtitle">Объявления</h3>

      <label className="admin-check">
        <input
          type="checkbox"
          checked={announcementsEnabled}
          onChange={(e) => setAnnouncementsEnabled(e.target.checked)}
        />
        <span>Показывать объявления на киоске</span>
      </label>

      <label className="admin-check">
        <input
          type="checkbox"
          checked={announcementsTickerEnabled}
          disabled={!announcementsEnabled}
          onChange={(e) => setAnnouncementsTickerEnabled(e.target.checked)}
        />
        <span>Бегущая строка на главном экране</span>
      </label>

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
