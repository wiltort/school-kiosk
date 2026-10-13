import { useEffect, useState, type FormEvent } from "react";
import {
  useAdminProfile,
  useDeleteAdminProfile,
  useUpdateAdminProfile,
} from "../../hooks/useAdminProfile";
import { ConfirmDialog } from "./ConfirmDialog";
import { CreateAdminDialog } from "./CreateAdminDialog";

interface ProfilePanelProps {
  /** Вызывается после удаления собственного профиля или смены пароля
   *  (бэкенд отзывает токены — нужен выход из админки). */
  onDeleted: () => void;
  /** Автоматически открыть форму создания администратора при монтировании. */
  autoOpenCreate?: boolean;
  /** Вызывается после обработки autoOpenCreate (для сброса флага). */
  onAutoOpenConsumed?: () => void;
}

/** Профиль текущего администратора: редактирование данных, смена пароля,
 *  создание нового админа и удаление собственного профиля (кроме дефолтного). */
export function ProfilePanel({
  onDeleted,
  autoOpenCreate = false,
  onAutoOpenConsumed,
}: ProfilePanelProps) {
  const { data: profile, isLoading, error: loadError } = useAdminProfile();
  const updateMutation = useUpdateAdminProfile();
  const deleteMutation = useDeleteAdminProfile();

  const [login, setLogin] = useState("");
  const [fullname, setFullname] = useState("");
  const [changingPassword, setChangingPassword] = useState(false);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  // Синхронизируем поля формы с профилем из React Query-кеша.
  useEffect(() => {
    if (!profile) {
      return;
    }
    setLogin(profile.login);
    setFullname(profile.fullname ?? "");
  }, [profile]);

  // Автоматически открываем форму создания администратора (например, после
  // нажатия «Создать администратора» в напоминании о дефолтной учётке).
  useEffect(() => {
    if (autoOpenCreate) {
      setCreateOpen(true);
      onAutoOpenConsumed?.();
    }
  }, [autoOpenCreate, onAutoOpenConsumed]);

  const handleSave = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setNotice(null);
    try {
      await updateMutation.mutateAsync({
        login: login.trim(),
        fullname: fullname.trim() || null,
      });
      setNotice("Профиль сохранён.");
    } catch {
      /* ошибка отображается через updateMutation.error */
    }
  };

  const handleChangePassword = async () => {
    setNotice(null);
    if (newPassword.length < 5) {
      setNotice("Пароль должен быть не короче 5 символов.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setNotice("Пароли не совпадают.");
      return;
    }
    try {
      await updateMutation.mutateAsync({ password: newPassword });
      // Смена пароля отзывает все токены — сессия завершается.
      onDeleted();
    } catch {
      /* ошибка отображается через updateMutation.error */
    }
  };

  const handleDelete = async () => {
    setDeleteOpen(false);
    try {
      await deleteMutation.mutateAsync();
      onDeleted();
    } catch {
      /* ошибка отображается через deleteMutation.error */
    }
  };

  return (
    <div className="admin-profile">
      <h2 className="admin-subtitle">Профиль</h2>

      {isLoading && <p className="admin-hint">Загрузка профиля…</p>}
      {loadError && !isLoading && (
        <p className="admin-error">
          {loadError instanceof Error
            ? loadError.message
            : "Не удалось загрузить профиль"}
        </p>
      )}

      {profile && (
        <form className="admin-profile__form" onSubmit={handleSave}>
          <label className="admin-field">
            <span>Логин</span>
            <input
              type="text"
              value={login}
              onChange={(e) => setLogin(e.target.value)}
              required
              minLength={3}
              autoComplete="username"
              disabled={profile.is_default}
            />
          </label>

          <label className="admin-field">
            <span>Полное имя</span>
            <input
              type="text"
              value={fullname}
              onChange={(e) => setFullname(e.target.value)}
              placeholder="Например: Иванов Иван Иванович"
              disabled={profile.is_default}
            />
          </label>

          <div className="admin-field">
            <span>Пароль</span>
            {changingPassword ? (
              <div className="admin-profile__password-change">
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Новый пароль"
                  required
                  minLength={5}
                  autoComplete="new-password"
                />
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Повторите пароль"
                  required
                  autoComplete="new-password"
                />
                <div className="admin-actions">
                  <button
                    type="button"
                    className="admin-button admin-button--small"
                    onClick={handleChangePassword}
                    disabled={updateMutation.isPending}
                  >
                    {updateMutation.isPending
                      ? "Сохранение..."
                      : "Сохранить пароль"}
                  </button>
                  <button
                    type="button"
                    className="admin-button admin-button-ghost admin-button--small"
                    onClick={() => {
                      setChangingPassword(false);
                      setNewPassword("");
                      setConfirmPassword("");
                    }}
                    disabled={updateMutation.isPending}
                  >
                    Отмена
                  </button>
                </div>
              </div>
            ) : (
              <div className="admin-profile__password">
                <span
                  className="admin-profile__password-value"
                  aria-hidden="true"
                >
                  ••••••••
                </span>
                {!profile.is_default && (
                  <button
                    type="button"
                    className="admin-button admin-button-ghost admin-button--small"
                    onClick={() => setChangingPassword(true)}
                  >
                    Сменить пароль
                  </button>
                )}
              </div>
            )}
          </div>

          {updateMutation.error && (
            <p className="admin-error">
              {updateMutation.error instanceof Error
                ? updateMutation.error.message
                : "Ошибка сохранения"}
            </p>
          )}
          {notice && <p className="admin-notice">{notice}</p>}

          <div className="admin-actions">
            {!profile.is_default && (
              <button
                type="submit"
                className="admin-button"
                disabled={updateMutation.isPending || isLoading}
              >
                {updateMutation.isPending ? "Сохранение..." : "Сохранить"}
              </button>
            )}
            <button
              type="button"
              className="admin-button admin-button-ghost"
              onClick={() => setCreateOpen(true)}
            >
              Создать
            </button>
            {!profile.is_default && (
              <button
                type="button"
                className="admin-button admin-button-danger"
                onClick={() => setDeleteOpen(true)}
                disabled={deleteMutation.isPending}
              >
                Удалить
              </button>
            )}
          </div>

          {profile.is_default && (
            <small className="admin-hint">
              Дефолтный администратор не может быть удалён или изменен.
              Рекомендуется создать отдельный профиль администратора.
            </small>
          )}
        </form>
      )}

      {createOpen && (
        <CreateAdminDialog
          onClose={() => setCreateOpen(false)}
          onCreated={() => {
            setCreateOpen(false);
            setNotice("Администратор создан.");
          }}
        />
      )}

      {deleteOpen && (
        <ConfirmDialog
          title="Удалить профиль?"
          text="Профиль будет удалён, а текущая сессия завершена. Восстановить его будет невозможно."
          confirmLabel="Удалить"
          submitting={deleteMutation.isPending}
          onConfirm={handleDelete}
          onCancel={() => setDeleteOpen(false)}
        />
      )}
    </div>
  );
}
