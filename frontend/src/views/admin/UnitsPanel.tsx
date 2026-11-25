import {
  useAdminUnits,
  useReorderAdminUnits,
  useUpdateAdminUnit,
} from "../../hooks/useAdminUnits";

/** Управление реестром сервисов: видимость и порядок плиток. */
export function UnitsPanel() {
  const { data = [], isLoading, isError, error } = useAdminUnits();
  const updateMutation = useUpdateAdminUnit();
  const reorderMutation = useReorderAdminUnits();

  const toggle = (key: string, isEnabled: boolean) => {
    updateMutation.mutate({ key, input: { is_enabled: !isEnabled } });
  };

  const move = (index: number, delta: number) => {
    const target = index + delta;
    if (target < 0 || target >= data.length) {
      return;
    }
    const next = [...data];
    const [item] = next.splice(index, 1);
    next.splice(target, 0, item);
    reorderMutation.mutate(next.map((unit) => unit.key));
  };

  return (
    <div className="content-admin">
      <p className="admin-text">
        Включённые сервисы показываются плитками на главном экране в указанном
        порядке.
      </p>

      {isLoading && <p className="admin-hint">Загрузка сервисов…</p>}
      {isError && !isLoading && (
        <p className="admin-error">
          {error instanceof Error
            ? error.message
            : "Не удалось загрузить сервисы"}
        </p>
      )}

      {data.length > 0 && (
        <ul className="content-admin__list">
          {data.map((unit, index) => (
            <li key={unit.key} className="content-admin__item">
              <div className="content-admin__item-main">
                <div className="content-admin__item-head">
                  <strong>{unit.title}</strong>
                  <span className="content-admin__badge">{unit.key}</span>
                </div>
                <label className="admin-check">
                  <input
                    type="checkbox"
                    checked={unit.is_enabled}
                    disabled={updateMutation.isPending}
                    onChange={() => toggle(unit.key, unit.is_enabled)}
                  />
                  <span>Показывать на главном экране</span>
                </label>
              </div>
              <div className="content-admin__item-actions">
                <button
                  type="button"
                  className="admin-button admin-button-ghost admin-button--small"
                  aria-label="Переместить выше"
                  onClick={() => move(index, -1)}
                  disabled={index === 0 || reorderMutation.isPending}
                >
                  ↑
                </button>
                <button
                  type="button"
                  className="admin-button admin-button-ghost admin-button--small"
                  aria-label="Переместить ниже"
                  onClick={() => move(index, 1)}
                  disabled={
                    index === data.length - 1 || reorderMutation.isPending
                  }
                >
                  ↓
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {updateMutation.isError && (
        <p className="admin-error">
          {updateMutation.error instanceof Error
            ? updateMutation.error.message
            : "Не удалось сохранить сервис"}
        </p>
      )}
      {reorderMutation.isError && (
        <p className="admin-error">
          {reorderMutation.error instanceof Error
            ? reorderMutation.error.message
            : "Не удалось изменить порядок"}
        </p>
      )}
    </div>
  );
}
