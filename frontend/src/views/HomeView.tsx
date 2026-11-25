import type { ReactNode } from "react";
import AppIcon from "../components/AppIcon";
import AnnouncementTicker from "../components/AnnouncementTicker";
import LanInfoPanel from "../components/LanInfoPanel";
import AnnouncementsIcon from "../components/icons/AnnouncementsIcon";
import ScheduleIcon from "../components/icons/ScheduleIcon";
import WeatherIcon from "../components/icons/WeatherIcon";
import kioskLogo from "../assets/kiosk-logo.png";
import type { AppUnit } from "../types/kiosk";

interface HomeViewProps {
  onSchedule: () => void;
  onWeather: () => void;
  onAnnouncements: () => void;
  /** Приветственное сообщение из настроек; пустая строка — стандартный подзаголовок. */
  welcomeMessage?: string;
  /** Реестр сервисов из настроек; пустой список — локальный фолбэк. */
  units?: AppUnit[];
  /** Показывать бегущую строку объявлений. */
  tickerEnabled?: boolean;
}

/** Плитки по умолчанию, если реестр сервисов недоступен. */
const FALLBACK_UNITS: AppUnit[] = [
  { key: "schedule", title: "Расписание", is_enabled: true, order: 1 },
  { key: "weather", title: "Погода", is_enabled: true, order: 2 },
];

/** Иконки известных сервисов. */
const UNIT_ICONS: Record<string, ReactNode> = {
  schedule: <ScheduleIcon />,
  weather: <WeatherIcon />,
  announcements: <AnnouncementsIcon />,
};

/**
 * Главный экран киоска: сетка плиток из реестра сервисов.
 * Порядок и видимость плиток управляются в админ-панели.
 */
export default function HomeView({
  onSchedule,
  onWeather,
  onAnnouncements,
  welcomeMessage = "",
  units = FALLBACK_UNITS,
  tickerEnabled = false,
}: HomeViewProps) {
  const subtitle = welcomeMessage.trim() || "Информационный киоск школы";
  const actions: Record<string, () => void> = {
    schedule: onSchedule,
    weather: onWeather,
    announcements: onAnnouncements,
  };
  const visibleUnits = (units.length > 0 ? units : FALLBACK_UNITS)
    .filter((unit) => unit.is_enabled)
    .sort((a, b) => a.order - b.order);

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
        {visibleUnits.map((unit) => (
          <AppIcon
            key={unit.key}
            label={unit.title}
            icon={UNIT_ICONS[unit.key] ?? <ScheduleIcon />}
            onClick={actions[unit.key] ?? (() => {})}
          />
        ))}
      </div>

      {tickerEnabled && <AnnouncementTicker />}

      <LanInfoPanel />
    </section>
  );
}
