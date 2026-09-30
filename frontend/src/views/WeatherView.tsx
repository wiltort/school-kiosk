import HomeButton from "../components/HomeButton";
import WeatherIcon from "../components/icons/WeatherIcon";

interface WeatherViewProps {
  onHome: () => void;
}

/**
 * Экран погоды (заглушка).
 * Данные и интеграция с сервисом прогноза появятся позже.
 */
export default function WeatherView({ onHome }: WeatherViewProps) {
  return (
    <section className="weather">
      <header className="weather__topbar">
        <HomeButton onHome={onHome} />
      </header>

      <div className="weather__body">
        <WeatherIcon size={128} />
        <p className="weather__message">Прогноз погоды скоро появится</p>
      </div>
    </section>
  );
}
