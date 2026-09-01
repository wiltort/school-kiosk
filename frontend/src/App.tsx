import { useCallback, useEffect, useState } from "react";
import {
  getKioskConfig,
  loadKioskConfig,
  type KioskConfig,
} from "./config/kioskConfig";
import { useIdleTimeout } from "./hooks/useIdleTimeout";
import HomeView from "./views/HomeView";
import ScheduleView from "./views/ScheduleView";
import WeatherView from "./views/WeatherView";

type View = "home" | "schedule" | "weather";

/**
 * Корневой компонент киоск-режима.
 *
 * Управляет навигацией между экранами и возвратом на главный экран
 * при бездействии пользователя (таймаут настраивается в конфиге киоска).
 */
export default function App() {
  const [view, setView] = useState<View>("home");
  const [config, setConfig] = useState<KioskConfig>(getKioskConfig());

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

  const goHome = useCallback(() => setView("home"), []);
  const openSchedule = useCallback(() => setView("schedule"), []);
  const openWeather = useCallback(() => setView("weather"), []);

  // При бездействии дольше inactivityTimeoutMs возвращаемся домой.
  useIdleTimeout(goHome, config.inactivityTimeoutMs);

  return (
    <div className="app">
      {view === "home" && (
        <HomeView onSchedule={openSchedule} onWeather={openWeather} />
      )}
      {view === "schedule" && <ScheduleView onHome={goHome} />}
      {view === "weather" && <WeatherView onHome={goHome} />}
    </div>
  );
}
