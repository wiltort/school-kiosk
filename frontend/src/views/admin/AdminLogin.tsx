import { useState, type FormEvent } from "react";
import HomeButton from "../../components/HomeButton";
import { loginAdmin } from "../../services/admin/auth";

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

  const handleLogin = async (event: FormEvent<HTMLFormElement>) => {
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
