import { useEffect, useState } from "react";

/**
 * Строка внизу экрана с версией приложения и статусом автообновления.
 *
 * Версия подставляется на этапе сборки Vite из `src-tauri/tauri.conf.json`
 * (константа `__APP_VERSION__` определена в vite.config.ts). Она совпадает
 * с версией релиза, которую проставляет scripts/set_release_version.py
 * перед сборкой, поэтому работает одинаково и в десктопном киоске (Tauri),
 * и в браузере по LAN.
 *
 * На десктопе (Tauri) компонент дополнительно:
 *   1) запрашивает начальный статус через IPC `get_update_status`;
 *   2) подписывается на событие `update-status`, которое шлёт Rust-бэкенд.
 * Это позволяет показывать актуальную версию, прогресс загрузки и ошибки
 * обновления. В браузере по LAN события недоступны — показываем только версию.
 */

/** Фаза обновления, совпадает с `UpdatePhase` в src-tauri/src/updater.rs. */
type UpdatePhase =
  "checking" | "downloading" | "installing" | "up_to_date" | "error";

/** Статус обновления, соответствует структуре `UpdateStatus` в updater.rs. */
interface UpdateStatus {
  phase: UpdatePhase;
  current_version: string;
  latest_version: string | null;
  downloaded: number | null;
  total: number | null;
  message: string | null;
}

/** Признак того, что процесс — десктопный киоск (доступен Tauri IPC). */
function isDesktop(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

/** Форматирует прогресс загрузки: «12,3 МБ из 45,6 МБ». */
function formatProgress(downloaded: number, total: number | null): string {
  const toMb = (bytes: number) => (bytes / (1024 * 1024)).toFixed(1);
  return total
    ? `${toMb(downloaded)} МБ из ${toMb(total)} МБ`
    : `${toMb(downloaded)} МБ`;
}

export default function VersionBadge() {
  const [status, setStatus] = useState<UpdateStatus | null>(null);

  // Версия для отображения. На десктопе предпочитаем живую current_version из
  // Rust (она берётся из package_info() и актуальна сразу после обновления,
  // даже если бандл ещё не перезагружен). Фолбэк на константу сборки
  // __APP_VERSION__ — для браузера по LAN и до первого статуса.
  const version = status?.current_version ?? __APP_VERSION__;

  // На десктопе: запрашиваем текущий статус и слушаем событие обновления.
  useEffect(() => {
    if (!isDesktop()) {
      return undefined;
    }

    let unlisten: (() => void) | undefined;
    let cancelled = false;

    (async () => {
      try {
        const [{ invoke }, { listen }] = await Promise.all([
          import("@tauri-apps/api/core"),
          import("@tauri-apps/api/event"),
        ]);
        // Начальный статус, чтобы строка не «мигала» до первого события.
        const initial = await invoke<UpdateStatus>("get_update_status");
        if (!cancelled) {
          setStatus(initial);
        }
        unlisten = await listen<UpdateStatus>("update-status", (event) => {
          if (!cancelled) {
            setStatus(event.payload);
          }
        });
      } catch {
        /* Tauri API недоступен — показываем только версию */
      }
    })();

    return () => {
      cancelled = true;
      unlisten?.();
    };
  }, []);

  // Собираем текстовую часть статусной строки (если она есть).
  let statusText: string | null = null;
  let statusKind = "";
  if (status) {
    switch (status.phase) {
      case "checking":
        statusText = status.message ?? "Проверка обновлений…";
        statusKind = "busy";
        break;
      case "downloading":
        statusText =
          status.downloaded != null
            ? `Обновление до ${status.latest_version ?? ""}: ${formatProgress(
                status.downloaded,
                status.total
              )}`
            : `Загрузка обновления до ${status.latest_version ?? ""}…`;
        statusKind = "busy";
        break;
      case "installing":
        statusText = "Установка обновления, приложение перезапустится…";
        statusKind = "busy";
        break;
      case "up_to_date":
        statusText = "Актуальная версия";
        statusKind = "ok";
        break;
      case "error":
        statusText = status.message ?? "Ошибка обновления";
        statusKind = "error";
        break;
    }
  }

  const classes = [
    "version-badge",
    statusKind ? `version-badge--${statusKind}` : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={classes}>
      <span>v{version}</span>
      {statusText && (
        <span className="version-badge__status">{statusText}</span>
      )}
    </div>
  );
}
