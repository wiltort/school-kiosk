import HomeButton from "../components/HomeButton";
import WeatherIcon from "../components/icons/WeatherIcon";
import { useWeatherForecast } from "../hooks/useWeather";

interface WeatherViewProps {
  onHome: () => void;
}

/** Эмодзи для известных типов погоды (python-weather Kind). */
const KIND_EMOJI: Record<string, string> = {
  SUNNY: "☀️",
  PARTLY_CLOUDY: "⛅",
  CLOUDY: "☁️",
  VERY_CLOUDY: "☁️",
  FOG: "🌫️",
  LIGHT_RAIN: "🌦️",
  HEAVY_RAIN: "🌧️",
  LIGHT_SNOW: "🌨️",
  HEAVY_SNOW: "❄️",
  THUNDERY_SHOWERS: "⛈️",
};

function formatDate(value: string | null): string {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleDateString("ru-RU", {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}

function formatTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleTimeString("ru-RU", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function temperature(value: number | null): string {
  return value === null ? "—" : `${Math.round(value)}°C`;
}

/** Экран прогноза погоды с офлайн-фолбэком на кеш бэкенда. */
export default function WeatherView({ onHome }: WeatherViewProps) {
  const { data, isLoading, isError } = useWeatherForecast();
  const forecast = data?.forecast;

  return (
    <section className="weather">
      <header className="weather__topbar">
        <HomeButton onHome={onHome} />
      </header>

      <div className="weather__body">
        {isLoading && <p className="weather__message">Загрузка прогноза…</p>}

        {isError && !isLoading && (
          <>
            <WeatherIcon size={96} />
            <p className="weather__message">
              Не удалось загрузить прогноз погоды
            </p>
            <p className="weather__hint">Проверьте подключение к интернету.</p>
          </>
        )}

        {data && forecast && (
          <>
            <div className="weather__current">
              <span className="weather__emoji" aria-hidden="true">
                {KIND_EMOJI[forecast.kind ?? ""] ?? "🌡️"}
              </span>
              <div className="weather__current-text">
                <p className="weather__location">
                  {forecast.location ?? "Погода"}
                </p>
                <p className="weather__temperature">
                  {temperature(forecast.temperature)}
                </p>
                <p className="weather__description">
                  {forecast.description ?? ""}
                </p>
              </div>
            </div>

            <dl className="weather__details">
              <div className="weather__detail">
                <dt>Ощущается</dt>
                <dd>{temperature(forecast.feels_like)}</dd>
              </div>
              <div className="weather__detail">
                <dt>Влажность</dt>
                <dd>
                  {forecast.humidity === null ? "—" : `${forecast.humidity}%`}
                </dd>
              </div>
              <div className="weather__detail">
                <dt>Ветер</dt>
                <dd>
                  {forecast.wind_speed === null
                    ? "—"
                    : `${Math.round(forecast.wind_speed)} км/ч`}
                </dd>
              </div>
            </dl>

            {forecast.daily_forecasts.length > 0 && (
              <ul className="weather__daily">
                {forecast.daily_forecasts.slice(0, 5).map((day, index) => (
                  <li key={day.date ?? `day-${index}`} className="weather__day">
                    <span className="weather__day-date">
                      {formatDate(day.date)}
                    </span>
                    <span className="weather__day-temp">
                      {day.lowest_temperature === null
                        ? "—"
                        : `${Math.round(day.lowest_temperature)}°`}{" "}
                      /{" "}
                      {day.highest_temperature === null
                        ? "—"
                        : `${Math.round(day.highest_temperature)}°`}
                    </span>
                  </li>
                ))}
              </ul>
            )}

            <p className="weather__updated">
              {data.is_stale ? "Данные могли устареть · " : ""}
              Обновлено: {formatTime(data.fetched_at)}
            </p>
          </>
        )}
      </div>
    </section>
  );
}
