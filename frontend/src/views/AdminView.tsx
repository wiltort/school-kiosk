import { useCallback, useEffect, useState } from "react";
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

/** Экран админ-панели: вход по логину/паролю и настройки приложения. */
export default function AdminView({ onHome }: AdminViewProps) {
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState<string | null>(() => getStoredToken());
  const [authError, setAuthError] = useState<string | null>(null);
  const [loggingIn, setLoggingIn] = useState(false);

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

  const handleLogout = async () => {
    await logoutAdmin();
    clearToken();
    setToken(null);
    setSettings(null);
  };

  return (
    <div className="admin-view">
      <div className="admin-header">
        <HomeButton onHome={onHome} label="Киоск" />
        <h1 className="admin-title">Админ-панель</h1>
      </div>

      {!token ? (
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
      ) : (
        <form className="admin-settings" onSubmit={handleSave}>
          <h2 className="admin-subtitle">Настройки</h2>

          <label className="admin-field">
            <span>Папка для изображений расписания</span>
            <input
              type="text"
              value={staticDir}
              placeholder="Оставьте пустым — используется папка по умолчанию"
              onChange={(e) => setStaticDir(e.target.value)}
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
              disabled={!settings?.autostart_supported}
              onChange={(e) => setAutostart(e.target.checked)}
            />
            <span>Автозапуск программы при входе в систему</span>
          </label>
          {!settings?.autostart_supported && (
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
            <button
              type="button"
              className="admin-button admin-button-ghost"
              onClick={handleLogout}
            >
              Выйти
            </button>
          </div>
        </form>
      )}
    </div>
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
