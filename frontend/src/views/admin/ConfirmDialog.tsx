interface ConfirmDialogProps {
  title: string;
  text: string;
  confirmLabel: string;
  submitting: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/** Диалог подтверждения деструктивного действия (например, удаления). */
export function ConfirmDialog({
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
