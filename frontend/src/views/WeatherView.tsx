import HomeButton from "../components/HomeButton";

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
        <svg
          viewBox="0 0 24 24"
          width="128"
          height="128"
          fill="currentColor"
          aria-hidden="true"
        >
          <path d="M6.76 4.84l-1.8-1.79-1.41 1.41 1.79 1.79 1.42-1.41zM4 10.5H1v2h3v-2zm9-9.95h-2V3.5h2V.55zm7.45 3.91l-1.41-1.41-1.79 1.79 1.41 1.41 1.79-1.79zm-3.21 13.7l1.79 1.8 1.41-1.41-1.8-1.79-1.4 1.4zM20 10.5v2h3v-2h-3zm-8-5c-3.31 0-6 2.69-6 6s2.69 6 6 6 6-2.69 6-6-2.69-6-6-6zm-1 14h2v3h-2v-3z" />
        </svg>
        <p className="weather__message">Прогноз погоды скоро появится</p>
      </div>
    </section>
  );
}
