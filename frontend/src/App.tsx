import { useCallback, useEffect, useRef, useState } from "react";
import {
  getKioskConfig,
  isDesktopApp,
  loadKioskConfig,
  type KioskConfig,
} from "./config/kioskConfig";
import { useIdleTimeout } from "./hooks/useIdleTimeout";
import AdminPersonIcon from "./components/AdminPersonIcon";
import HomeView from "./views/HomeView";
import ScheduleView from "./views/ScheduleView";
import VersionBadge from "./components/VersionBadge";
import WeatherView from "./views/WeatherView";
import {
  AdminLogin,
  AdminMenuBar,
  AdminPanel,
  type AdminSection,
} from "./views/AdminView";
import { isAdminLoggedIn, logoutAdmin } from "./services/api";

type View = "home" | "schedule" | "weather" | "login" | "admin";

/** Интервал опроса админ-режима на десктопе (Ctrl+Shift+A). */
const ADMIN_POLL_MS = 1000;

/**
 * Корневой компонент киоск-режима.
 *
 * Логика входа:
 *   - иконка на главном экране (браузер по LAN) открывает форму входа;
 *   - после успешного входа киоск остаётся на главном экране, но сверху
 *     появляется строка меню администратора («Настройки», «Расписания»,
 *     «О проекте»), а иконка меняет красный крестик на зелёную галочку;
 *   - повторное нажатие на иконку (или кнопка в строке меню) выходит
 *     из режима администратора;
 *   - десктопный киоск: сочетание Ctrl+Shift+A открывает форму входа
 *     (админ-режим из kiosk.rs опрашивается через `is_admin_active`).
 */
export default function App() {
  const [view, setView] = useState<View>("home");
  const [adminSection, setAdminSection] = useState<AdminSection>("settings");
  const [isAdmin, setIsAdmin] = useState<boolean>(() => isAdminLoggedIn());
  const [config, setConfig] = useState<KioskConfig>(getKioskConfig());
  const desktop = isDesktopApp();

  const viewRef = useRef<View>(view);
  useEffect(() => {
    viewRef.current = view;
  }, [view]);

  const isAdminRef = useRef(isAdmin);
  useEffect(() => {
    isAdminRef.current = isAdmin;
  }, [isAdmin]);

  // Загружаем актуальные настройки киоска с бэкенда (приветственное сообщение).
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

  // Десктоп: Ctrl+Shift+A переключает админ-режим (kiosk.rs) — открываем форму входа.
  useEffect(() => {
    if (!desktop) {
      return undefined;
    }
    let cancelled = false;
    const timerId = window.setInterval(async () => {
      if (cancelled || isAdminRef.current || viewRef.current === "login") {
        return;
      }
      try {
        const { invoke } = await import("@tauri-apps/api/core");
        const active = await invoke<boolean>("is_admin_active");
        if (active && !cancelled) {
          setView("login");
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
  const openLogin = useCallback(() => setView("login"), []);

  const openAdminSection = useCallback((section: AdminSection) => {
    setAdminSection(section);
    setView("admin");
  }, []);

  /** Успешный вход: остаёмся на главном экране, включаем режим администратора. */
  const handleLoginSuccess = useCallback(() => {
    setIsAdmin(true);
    setView("home");
  }, []);

  /** Выход из режима администратора. */
  const handleLogout = useCallback(async () => {
    await logoutAdmin();
    setIsAdmin(false);
    setAdminSection("settings");
    setView("home");
  }, []);

  /** Перезагрузка настроек киоска (например, после сохранения в админке). */
  const reloadConfig = useCallback(async () => {
    const loaded = await loadKioskConfig();
    setConfig(loaded);
  }, []);

  // При бездействии дольше inactivityTimeoutMs возвращаемся на главный экран
  // (админ-сессия при этом сохраняется — строка меню остаётся видимой).
  useIdleTimeout(() => {
    goHome();
  }, config.inactivityTimeoutMs);

  return (
    <div className="app">
      {isAdmin && (
        <AdminMenuBar
          activeSection={view === "admin" ? adminSection : null}
          onSectionChange={openAdminSection}
          onExit={handleLogout}
        />
      )}

      {view === "home" && (
        <>
          <HomeView
            onSchedule={openSchedule}
            onWeather={openWeather}
            welcomeMessage={config.welcomeMessage}
          />
          {/*
            Иконка входа в админку — только в браузерной версии и только пока
            вход не выполнен: красный крестик. После входа вместо неё в правом
            верхнем углу видна зелёная галочка в строке меню администратора.
          */}
          {!desktop && !isAdmin && (
            <button
              type="button"
              className="admin-icon-button admin-icon-button--guest"
              aria-label="Войти в админку"
              title="Войти в админку"
              onClick={openLogin}
            >
              <AdminPersonIcon size={28} title="Войти в админку" />
            </button>
          )}
        </>
      )}

      {view === "schedule" && <ScheduleView onHome={goHome} />}
      {view === "weather" && <WeatherView onHome={goHome} />}
      {view === "login" && (
        <AdminLogin onHome={goHome} onSuccess={handleLoginSuccess} />
      )}
      {view === "admin" && (
        <AdminPanel
          section={adminSection}
          onHome={goHome}
          onSettingsSaved={reloadConfig}
        />
      )}

      {/* Строка с версией приложения — видна на всех экранах */}
      <VersionBadge />
    </div>
  );
}
