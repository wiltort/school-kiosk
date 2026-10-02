import { useCallback, useState } from "react";
import { isDesktopApp } from "./config/kioskConfig";
import { useIdleTimeout } from "./hooks/useIdleTimeout";
import { useKioskConfig } from "./hooks/useKioskConfig";
import { useDesktopAdminPoll } from "./hooks/useDesktopAdminPoll";
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
} from "./views/admin";
import { isAdminLoggedIn } from "./services/http";
import { logoutAdmin } from "./services/admin/auth";

type View = "home" | "schedule" | "weather" | "login" | "admin";

/**
 * Корневой компонент киоск-режима.
 *   - десктопный киоск: сочетание Ctrl+Shift+A открывает форму входа
 *     (админ-режим из kiosk.rs опрашивается через `is_admin_active`).
 */
export default function App() {
  const [view, setView] = useState<View>("home");
  const [adminSection, setAdminSection] = useState<AdminSection>("settings");
  const [isAdmin, setIsAdmin] = useState<boolean>(() => isAdminLoggedIn());
  const desktop = isDesktopApp();

  const { data: config, refetch: refetchConfig } = useKioskConfig();

  // Десктоп: Ctrl+Shift+A переключает админ-режим (kiosk.rs) — открываем форму входа.
  useDesktopAdminPoll({
    desktop,
    isAdmin,
    onLoginView: view === "login",
    onAdminActivate: () => setView("login"),
  });

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
  const reloadConfig = useCallback(() => {
    void refetchConfig();
  }, [refetchConfig]);

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

      {view === "schedule" && (
        <ScheduleView onHome={goHome} scheduleMode={config.scheduleMode} />
      )}
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
