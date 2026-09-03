import { useCallback, useEffect, useRef, useState } from "react";
import {
  getKioskConfig,
  isDesktopApp,
  loadKioskConfig,
  type KioskConfig,
} from "./config/kioskConfig";
import { useIdleTimeout } from "./hooks/useIdleTimeout";
import AdminView from "./views/AdminView";
import HomeView from "./views/HomeView";
import ScheduleView from "./views/ScheduleView";
import WeatherView from "./views/WeatherView";

type View = "home" | "schedule" | "weather" | "admin";

/** Интервал опроса админ-режима на десктопе (Ctrl+Shift+A). */
const ADMIN_POLL_MS = 1000;

/**
 * Корневой компонент киоск-режима.
 *
 * Управляет навигацией между экранами и возвратом на главный экран
 * при бездействии пользователя (таймаут настраивается в конфиге киоска).
 *
 * Вход в админку:
 *   - браузер по LAN — иконка на главном экране (только не в Tauri);
 *   - десктопный киоск — сочетание Ctrl+Shift+A (админ-режим из kiosk.rs),
 *     фронтенд периодически опрашивает `is_admin_active`.
 */
export default function App() {
  const [view, setView] = useState<View>("home");
  const [config, setConfig] = useState<KioskConfig>(getKioskConfig());
  const desktop = isDesktopApp();

  const viewRef = useRef<View>(view);
  useEffect(() => {
    viewRef.current = view;
  }, [view]);

  // Загружаем актуальные настройки (пока значения по умолчанию;
  // в дальнейшем — из админки).
  useEffect(() => {
    let cancelled = false;
    loadKioskConfig().then((loaded) => {
      if (!cancelled) {
        setConfig(loaded);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  // Десктоп: если активен админ-режим (Ctrl+Shift+A) — открываем админку.
  useEffect(() => {
    if (!desktop) {
      return undefined;
    }
    let cancelled = false;
    const timerId = window.setInterval(async () => {
      if (cancelled || viewRef.current === "admin") {
        return;
      }
      try {
        const { invoke } = await import("@tauri-apps/api/core");
        const active = await invoke<boolean>("is_admin_active");
        if (active && !cancelled) {
          setView("admin");
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

  const goHome = useCallback(() => setView("home"), []);
  const openSchedule = useCallback(() => setView("schedule"), []);
  const openWeather = useCallback(() => setView("weather"), []);
  const openAdmin = useCallback(() => setView("admin"), []);

  // При бездействии дольше inactivityTimeoutMs возвращаемся домой
  // (но не выкидываем из админки во время работы в ней).
  useIdleTimeout(() => {
    if (viewRef.current !== "admin") {
      goHome();
    }
  }, config.inactivityTimeoutMs);

  return (
    <div className="app">
      {view === "home" && (
        <>
          <HomeView onSchedule={openSchedule} onWeather={openWeather} />
          {/* Иконка входа в админку — только в браузерной версии */}
          {!desktop && (
            <button
              type="button"
              className="admin-icon-button"
              aria-label="Войти в админку"
              onClick={openAdmin}
            >
              <svg
                viewBox="0 0 24 24"
                width="28"
                height="28"
                fill="currentColor"
                aria-hidden="true"
              >
                <path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58a.49.49 0 0 0 .12-.61l-1.92-3.32a.488.488 0 0 0-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54a.484.484 0 0 0-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58a.49.49 0 0 0-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z" />
              </svg>
            </button>
          )}
        </>
      )}
      {view === "schedule" && <ScheduleView onHome={goHome} />}
      {view === "weather" && <WeatherView onHome={goHome} />}
      {view === "admin" && <AdminView onHome={goHome} />}
    </div>
  );
}
