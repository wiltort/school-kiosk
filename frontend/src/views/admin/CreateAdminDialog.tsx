import { useState, type FormEvent } from "react";
import { useCreateAdminProfile } from "../../hooks/useAdminProfile";

interface CreateAdminDialogProps {
  /** Закрытие формы без создания. */
  onClose: () => void;
  /** Вызывается после успешного создания администратора. */
  onCreated: () => void;
}

/** Модальная форма создания нового администратора. */
export function CreateAdminDialog({
  onClose,
  onCreated,
}: CreateAdminDialogProps) {
  const createMutation = useCreateAdminProfile();
  const [login, setLogin] = useState("");
  const [fullname, setFullname] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError(null);
    if (password.length < 5) {
      setFormError("Пароль должен быть не короче 5 символов.");
      return;
    }
    if (password !== confirmPassword) {
      setFormError("Пароли не совпадают.");
      return;
    }
    try {
      await createMutation.mutateAsync({
        login: login.trim(),
        fullname: fullname.trim() || null,
        password,
      });
      onCreated();
    } catch {
      /* ошибка отображается через createMutation.error */
    }
  };

  return (
    <div className="admin-modal-overlay" role="dialog" aria-modal="true">
      <form className="admin-modal" onSubmit={handleSubmit}>
        <h2 className="admin-subtitle">Новый администратор</h2>

        <label className="admin-field">
          <span>Логин</span>
          <input
            type="text"
            value={login}
            onChange={(e) => setLogin(e.target.value)}
            required
            minLength={3}
            autoFocus
            autoComplete="username"
          />
        </label>

        <label className="admin-field">
          <span>Полное имя</span>
          <input
            type="text"
            value={fullname}
            onChange={(e) => setFullname(e.target.value)}
            placeholder="Например: Иванов Иван Иванович"
          />
        </label>

        <label className="admin-field">
          <span>Пароль</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={5}
            autoComplete="new-password"
          />
        </label>

        <label className="admin-field">
          <span>Повторите пароль</span>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            autoComplete="new-password"
          />
        </label>

        {formError && <p className="admin-error">{formError}</p>}
        {createMutation.error && (
          <p className="admin-error">
            {createMutation.error instanceof Error
              ? createMutation.error.message
              : "Ошибка создания администратора"}
          </p>
        )}

        <div className="admin-modal__actions">
          <button
            type="button"
            className="admin-button admin-button-ghost"
            onClick={onClose}
            disabled={createMutation.isPending}
          >
            Отмена
          </button>
          <button
            type="submit"
            className="admin-button"
            disabled={createMutation.isPending}
          >
            {createMutation.isPending ? "Создание..." : "Создать"}
          </button>
        </div>
      </form>
    </div>
  );
}
