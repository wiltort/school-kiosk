interface DefaultAdminReminderProps {
  /** Закрыть напоминание без перехода. */
  onClose: () => void;
  /** Перейти к созданию нового (недефолтного) администратора. */
  onCreateAdmin: () => void;
}

/**
 * Напоминание о необходимости создать недефолтного администратора.
 * Показывается при каждом входе под дефолтной учётной записью.
 */
export function DefaultAdminReminder({
  onClose,
  onCreateAdmin,
}: DefaultAdminReminderProps) {
  return (
    <div className="admin-modal-overlay" role="alertdialog" aria-modal="true">
      <div className="admin-modal">
        <h2 className="admin-subtitle">Дефолтный администратор</h2>
        <p className="admin-text">
          Вы вошли под дефолтной учётной записью администратора. Для безопасной
          работы рекомендуется создать отдельного администратора с собственным
          логином и паролем, а дефолтную учётку использовать только для
          первоначальной настройки.
        </p>
        <div className="admin-modal__actions">
          <button
            type="button"
            className="admin-button admin-button-ghost"
            onClick={onClose}
          >
            Позже
          </button>
          <button
            type="button"
            className="admin-button"
            onClick={onCreateAdmin}
          >
            Создать администратора
          </button>
        </div>
      </div>
    </div>
  );
}
