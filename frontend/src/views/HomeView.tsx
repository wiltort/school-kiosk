import type { ReactNode } from "react";
import AppIcon from "../components/AppIcon";
import LanInfoPanel from "../components/LanInfoPanel";
import kioskLogo from "../assets/kiosk-logo.png";

interface HomeViewProps {
  onSchedule: () => void;
  onWeather: () => void;
  /** Приветственное сообщение из настроек; пустая строка — стандартный подзаголовок. */
  welcomeMessage?: string;
}

function ScheduleIcon(): ReactNode {
  return (
    <svg viewBox="0 0 24 24" width="96" height="96" fill="currentColor">
      <path d="M19 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2zM7 7h10v2H7V7zm0 4h10v2H7v-2zm0 4h10v2H7v-2z" />
    </svg>
  );
}

function WeatherIcon(): ReactNode {
  return (
    <svg viewBox="0 0 24 24" width="96" height="96" fill="currentColor">
      <path d="M6.76 4.84l-1.8-1.79-1.41 1.41 1.79 1.79 1.42-1.41zM4 10.5H1v2h3v-2zm9-9.95h-2V3.5h2V.55zm7.45 3.91l-1.41-1.41-1.79 1.79 1.41 1.41 1.79-1.79zm-3.21 13.7l1.79 1.8 1.41-1.41-1.8-1.79-1.4 1.4zM20 10.5v2h3v-2h-3zm-8-5c-3.31 0-6 2.69-6 6s2.69 6 6 6 6-2.69 6-6-2.69-6-6-6zm-1 14h2v3h-2v-3z" />
    </svg>
  );
}

/**
 * Главный экран киоска: сетка иконок приложений.
 * Сейчас доступны «Расписание» и «Погода», в будущем список расширится.
 */
export default function HomeView({
  onSchedule,
  onWeather,
  welcomeMessage = "",
}: HomeViewProps) {
  const subtitle = welcomeMessage.trim() || "Информационный киоск школы";
  return (
    <section className="home">
      <header className="home__header">
        <img
          src={kioskLogo}
          alt="Логотип школы"
          className="home__logo"
          draggable={false}
        />
        <h1 className="home__title">Школьный киоск</h1>
        <p className="home__subtitle">{subtitle}</p>
      </header>

      <div className="home__grid">
        <AppIcon
          label="Расписание"
          icon={<ScheduleIcon />}
          onClick={onSchedule}
        />
        <AppIcon label="Погода" icon={<WeatherIcon />} onClick={onWeather} />
      </div>

      <LanInfoPanel />
    </section>
  );
}
