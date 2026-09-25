import { useCallback, useEffect, useState } from "react";
import AdminPersonIcon from "../components/AdminPersonIcon";
import HomeButton from "../components/HomeButton";
import {
  fetchAdminSettings,
  loginAdmin,
  updateAdminSettings,
  type ScheduleMode,
} from "../services/api";

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
  const [localImageDir, setLocalImageDir] = useState("");
  const [scheduleMode, setScheduleMode] = useState<ScheduleMode>("single");
  const [welcomeMessage, setWelcomeMessage] = useState("");
  const [autostart, setAutostart] = useState(false);
  const [autostartSupported, setAutostartSupported] = useState(true);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadSettings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAdminSettings();
      setLocalImageDir(data.local_image_dir ?? "");
      setScheduleMode(data.schedule_mode);
      setWelcomeMessage(data.welcome_message ?? "");
      setAutostart(data.autostart);
      setAutostartSupported(data.autostart_supported);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Не удалось загрузить настройки"
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadSettings();
  }, [loadSettings]);

  const handleSave = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setNotice(null);
    setError(null);
    try {
      const saved = await updateAdminSettings({
        local_image_dir: localImageDir.trim() || null,
        schedule_mode: scheduleMode,
        welcome_message: welcomeMessage.trim() || null,
        autostart,
      });
      setLocalImageDir(saved.local_image_dir ?? "");
      setScheduleMode(saved.schedule_mode);
      setWelcomeMessage(saved.welcome_message ?? "");
      setAutostart(saved.autostart);
      setNotice("Настройки сохранены.");
      onSaved?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка сохранения");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="admin-settings" onSubmit={handleSave}>
      <h2 className="admin-subtitle">Настройки</h2>

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

      {error && <p className="admin-error">{error}</p>}
      {notice && <p className="admin-notice">{notice}</p>}

      <div className="admin-actions">
        <button
          type="submit"
          className="admin-button"
          disabled={saving || loading}
        >
          {saving ? "Сохранение..." : "Сохранить"}
        </button>
      </div>
    </form>
  );
}

// ============================================================================
// Раздел «Расписания»
// ============================================================================

function SchedulesPanel() {
  return (
    <div className="admin-settings">
      <h2 className="admin-subtitle">Расписания</h2>
      <p className="admin-text">
        Управление загруженными изображениями расписания появится здесь в
        ближайшем обновлении.
      </p>
      <p className="admin-text">
        Сейчас киоск показывает активное расписание из папки локальных
        расписаний. Саму папку и режим отображения можно задать в разделе
        «Настройки».
      </p>
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
