import { useEffect, useRef } from "react";

/** Интервал опроса админ-режима на десктопе (Ctrl+Shift+A). */
const ADMIN_POLL_MS = 1000;

interface UseDesktopAdminPollOptions {
  /** Приложение запущено в Tauri (десктопный киоск). */
  desktop: boolean;
  /** Активна ли уже админ-сессия. */
  isAdmin: boolean;
  /** Открыт ли уже экран входа в админку. */
  onLoginView: boolean;
  /** Вызывается при активации админ-режима (Ctrl+Shift+A). */
  onAdminActivate: () => void;
  /** Вызывается при повторном Ctrl+Shift+A на экране входа (закрывает форму). */
  onAdminDeactivate: () => void;
}

/**
 * На десктопном киоске (Tauri) отслеживает админ-режим (Ctrl+Shift+A в
 * kiosk.rs). Основной канал — событие `admin-mode` от Rust (мгновенное),
 * резервный — опрос IPC `is_admin_active` раз в секунду. При активации
 * вызывает onAdminActivate / onAdminDeactivate и сбрасывает флаг командой
 * `clear_admin_mode`, чтобы одно нажатие не срабатывало повторно
 * (например, после выхода из админки флаг не остаётся «залипшим»).
 */
export function useDesktopAdminPoll({
  desktop,
  isAdmin,
  onLoginView,
  onAdminActivate,
  onAdminDeactivate,
}: UseDesktopAdminPollOptions): void {
  const isAdminRef = useRef(isAdmin);
  useEffect(() => {
    isAdminRef.current = isAdmin;
  }, [isAdmin]);

  const onLoginViewRef = useRef(onLoginView);
  useEffect(() => {
    onLoginViewRef.current = onLoginView;
  }, [onLoginView]);

  const onAdminActivateRef = useRef(onAdminActivate);
  useEffect(() => {
    onAdminActivateRef.current = onAdminActivate;
  }, [onAdminActivate]);

  const onAdminDeactivateRef = useRef(onAdminDeactivate);
  useEffect(() => {
    onAdminDeactivateRef.current = onAdminDeactivate;
  }, [onAdminDeactivate]);

  useEffect(() => {
    if (!desktop) {
      return undefined;
    }
    let cancelled = false;
    let busy = false;
    // Чтобы не заспамить консоль при недоступном IPC — логируем первую
    // ошибку и дальше молчим, пока IPC не восстановится.
    let loggedInvokeError = false;

    /** Реакция на активацию админ-режима (сброс флага + смена экрана). */
    const handleActive = async (active: boolean): Promise<void> => {
      if (cancelled || !active) {
        return;
      }
      const { invoke } = await import("@tauri-apps/api/core");
      // Флаг обработан — сбрасываем, иначе одно нажатие будет «висеть»
      // до следующего опроса (в т.ч. после выхода из админки).
      await invoke("clear_admin_mode");
      if (cancelled) {
        return;
      }
      if (isAdminRef.current) {
        // Уже в админке — горячая клавиша ничего не делает.
        return;
      }
      if (onLoginViewRef.current) {
        // Повторное Ctrl+Shift+A закрывает форму входа.
        onAdminDeactivateRef.current();
      } else {
        onAdminActivateRef.current();
      }
    };

    // Основной канал: мгновенное событие от Rust при переключении режима.
    let unlisten: (() => void) | undefined;
    void (async () => {
      try {
        const { listen } = await import("@tauri-apps/api/event");
        if (cancelled) {
          return;
        }
        unlisten = await listen<boolean>("admin-mode", (event) => {
          void handleActive(event.payload);
        });
      } catch (e) {
        console.warn("[admin-mode] не удалось подписаться на событие:", e);
      }
    })();

    // Резервный канал: опрос (на случай, если событие не дошло).
    const timerId = window.setInterval(async () => {
      if (cancelled || busy) {
        return;
      }
      busy = true;
      try {
        const { invoke } = await import("@tauri-apps/api/core");
        const active = await invoke<boolean>("is_admin_active");
        loggedInvokeError = false;
        await handleActive(active);
      } catch (e) {
        if (!loggedInvokeError) {
          loggedInvokeError = true;
          console.warn(
            "[admin-mode] invoke is_admin_active не работает " +
              "(проверьте capabilities/remote в src-tauri):",
            e
          );
        }
      } finally {
        busy = false;
      }
    }, ADMIN_POLL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(timerId);
      unlisten?.();
    };
  }, [desktop]);
}
