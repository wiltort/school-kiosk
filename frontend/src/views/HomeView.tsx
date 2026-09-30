import AppIcon from "../components/AppIcon";
import LanInfoPanel from "../components/LanInfoPanel";
import ScheduleIcon from "../components/icons/ScheduleIcon";
import WeatherIcon from "../components/icons/WeatherIcon";
import kioskLogo from "../assets/kiosk-logo.png";

interface HomeViewProps {
  onSchedule: () => void;
  onWeather: () => void;
  /** Приветственное сообщение из настроек; пустая строка — стандартный подзаголовок. */
  welcomeMessage?: string;
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
