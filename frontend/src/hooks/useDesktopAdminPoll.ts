import { useEffect, useRef } from "react";

/** Интервал опроса админ-режима на десктопе (Ctrl+Shift+A). */
const ADMIN_POLL_MS = 1000;

interface UseDesktopAdminPollOptions {
  /** Приложение запущено в Tauri (десктопный киоск). */
  desktop: boolean;
  /** Активна ли уже админ-сессия (опрос не нужен). */
  isAdmin: boolean;
  /** Открыт ли уже экран входа в админку. */
  onLoginView: boolean;
  /** Вызывается при активации админ-режима (Ctrl+Shift+A). */
  onAdminActivate: () => void;
}

/**
 * На десктопном киоске (Tauri) опрашивает Rust-бэкенд через IPC `is_admin_active`
 * (сочетание Ctrl+Shift+A в kiosk.rs). При активации вызывает onAdminActivate.
 */
export function useDesktopAdminPoll({
  desktop,
  isAdmin,
  onLoginView,
  onAdminActivate,
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

  useEffect(() => {
    if (!desktop) {
      return undefined;
    }
    let cancelled = false;
    const timerId = window.setInterval(async () => {
      if (cancelled || isAdminRef.current || onLoginViewRef.current) {
        return;
      }
      try {
        const { invoke } = await import("@tauri-apps/api/core");
        const active = await invoke<boolean>("is_admin_active");
        if (active && !cancelled) {
          onAdminActivateRef.current();
        }
      } catch {
        /* Tauri invoke недоступен — игнорируем */
      }
    }, ADMIN_POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timerId);
    };
  }, [desktop]);
}
