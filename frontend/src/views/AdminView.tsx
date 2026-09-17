import { useCallback, useEffect, useState } from "react";
import AdminPersonIcon from "../components/AdminPersonIcon";
import HomeButton from "../components/HomeButton";
import {
  fetchAdminSettings,
  loginAdmin,
  logoutAdmin,
  updateAdminSettings,
  type AdminSettings,
} from "../services/api";

interface AdminViewProps {
  /** Возврат на главный экран киоска. */
  onHome: () => void;
}

/** Пункты строки меню админки. Пока доступна только «Настройки», список расширится. */
type AdminPanel = "settings";

/** Экран админ-панели: вход по логину/паролю и настройки приложения. */
export default function AdminView({ onHome }: AdminViewProps) {
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState<string | null>(() => getStoredToken());
  const [authError, setAuthError] = useState<string | null>(null);
  const [loggingIn, setLoggingIn] = useState(false);

  const [activePanel, setActivePanel] = useState<AdminPanel>("settings");

  const [settings, setSettings] = useState<AdminSettings | null>(null);
  const [staticDir, setStaticDir] = useState("");
  const [autostart, setAutostart] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadSettings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAdminSettings();
      setSettings(data);
      setStaticDir(data.static_dir ?? "");
      setAutostart(data.autostart);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Не удалось загрузить настройки"
      );
      // Невалидный/протухший токен — возвращаем к форме входа.
      if (e instanceof Error && e.message === "Нет авторизации") {
        clearToken();
        setToken(null);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (token) {
      void loadSettings();
    }
  }, [token, loadSettings]);

  const handleLogin = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoggingIn(true);
    setAuthError(null);
    try {
      await loginAdmin(login, password);
      setToken(getStoredToken());
    } catch (e) {
      setAuthError(e instanceof Error ? e.message : "Ошибка входа");
    } finally {
      setLoggingIn(false);
    }
  };

  const handleSave = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setNotice(null);
    setError(null);
    try {
      const saved = await updateAdminSettings({
        static_dir: staticDir.trim() || null,
        autostart,
      });
      setSettings(saved);
      setStaticDir(saved.static_dir ?? "");
      setAutostart(saved.autostart);
      setNotice(
        "Настройки сохранены. Смена папки изображений вступит в силу после перезапуска."
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка сохранения");
    } finally {
      setSaving(false);
    }
  };

  /** Выход из режима админа: инвалидируем токен и возвращаемся на главный экран киоска. */
  const handleExit = async () => {
    await logoutAdmin();
    clearToken();
    setToken(null);
    setSettings(null);
    onHome();
  };

  return (
    <div className="admin-view">
      {!token ? (
        <>
          <div className="admin-header">
            <HomeButton onHome={onHome} label="Киоск" />
            <h1 className="admin-title">Админ-панель</h1>
          </div>

          <form className="admin-login" onSubmit={handleLogin}>
            <h2 className="admin-subtitle">Вход в админку</h2>
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
          </form>
        </>
      ) : (
        <>
          {/* Строка меню админки. Пункты добавляются слева, кнопка выхода прижата вправо. */}
          <nav className="admin-menu">
            <div className="admin-menu__nav">
              <button
                type="button"
                className={
                  activePanel === "settings"
                    ? "admin-menu__item admin-menu__item--active"
                    : "admin-menu__item"
                }
                onClick={() => setActivePanel("settings")}
              >
                Настройки
              </button>
              {/* В дальнейшем сюда добавятся новые пункты меню */}
            </div>
            <button
              type="button"
              className="admin-menu__exit"
              aria-label="Выйти из админки"
              title="Выйти из админки"
              onClick={handleExit}
            >
              <AdminPersonIcon size={30} title="Выйти из админки" />
            </button>
          </nav>

          <SettingsPanel
            loading={loading}
            saving={saving}
            staticDir={staticDir}
            autostart={autostart}
            autostartSupported={settings?.autostart_supported ?? false}
            error={error}
            notice={notice}
            onStaticDirChange={setStaticDir}
            onAutostartChange={setAutostart}
            onSave={handleSave}
          />
        </>
      )}
    </div>
  );
}

// ============================================================================
// Панель настроек (рендерится под строкой меню при активном пункте «Настройки»)
// ============================================================================

interface SettingsPanelProps {
  loading: boolean;
  saving: boolean;
  staticDir: string;
  autostart: boolean;
  autostartSupported: boolean;
  error: string | null;
  notice: string | null;
  onStaticDirChange: (value: string) => void;
  onAutostartChange: (checked: boolean) => void;
  onSave: (event: React.FormEvent) => void;
}

function SettingsPanel({
  loading,
  saving,
  staticDir,
  autostart,
  autostartSupported,
  error,
  notice,
  onStaticDirChange,
  onAutostartChange,
  onSave,
}: SettingsPanelProps) {
  return (
    <form className="admin-settings" onSubmit={onSave}>
      <h2 className="admin-subtitle">Настройки</h2>

      <label className="admin-field">
        <span>Папка для изображений расписания</span>
        <input
          type="text"
          value={staticDir}
          placeholder="Оставьте пустым — используется папка по умолчанию"
          onChange={(e) => onStaticDirChange(e.target.value)}
        />
        <small>
          Путь на диске киоска, например <code>D:\KioskStatic</code>. Пустое
          поле — значение по умолчанию.
        </small>
      </label>

      <label className="admin-check">
        <input
          type="checkbox"
          checked={autostart}
          disabled={!autostartSupported}
          onChange={(e) => onAutostartChange(e.target.checked)}
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

// --- Вспомогательные функции для токена (модульная обвязка над sessionStorage) ---

const ADMIN_TOKEN_KEY = "school_kiosk_admin_token";

function getStoredToken(): string | null {
  try {
    return sessionStorage.getItem(ADMIN_TOKEN_KEY);
  } catch {
    return null;
  }
}

function clearToken(): void {
  try {
    sessionStorage.removeItem(ADMIN_TOKEN_KEY);
  } catch {
    /* ignore */
  }
}
