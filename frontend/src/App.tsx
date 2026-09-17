import { useCallback, useEffect, useRef, useState } from "react";
import {
  getKioskConfig,
  isDesktopApp,
  loadKioskConfig,
  type KioskConfig,
} from "./config/kioskConfig";
import { useIdleTimeout } from "./hooks/useIdleTimeout";
import AdminPersonIcon from "./components/AdminPersonIcon";
import AdminView from "./views/AdminView";
import HomeView from "./views/HomeView";
import ScheduleView from "./views/ScheduleView";
import VersionBadge from "./components/VersionBadge";
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
              title="Войти в админку"
              onClick={openAdmin}
            >
              <AdminPersonIcon size={28} title="Войти в админку" />
            </button>
          )}
        </>
      )}
      {view === "schedule" && <ScheduleView onHome={goHome} />}
      {view === "weather" && <WeatherView onHome={goHome} />}
      {view === "admin" && <AdminView onHome={goHome} />}
      {/* Строка с версией приложения — видна на всех экранах */}
      <VersionBadge />
    </div>
  );
}
