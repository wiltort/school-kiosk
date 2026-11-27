import { getKioskConfig } from "../config/kioskConfig";

/** Дневной прогноз. */
export interface DailyForecast {
  date: string | null;
  highest_temperature: number | null;
  lowest_temperature: number | null;
  temperature: number | null;
}

/** Текущий прогноз и дневной ряд. */
export interface Forecast {
  location: string | null;
  description: string | null;
  kind: string | null;
  temperature: number | null;
  feels_like: number | null;
  humidity: number | null;
  cloud_cover: number | null;
  wind_speed: number | null;
  wind_direction: string | null;
  precipitation: number | null;
  pressure: number | null;
  visibility: number | null;
  ultraviolet: string | null;
  daily_forecasts: DailyForecast[];
}

/** Ответ API прогноза погоды. */
export interface WeatherResponse {
  forecast: Forecast;
  fetched_at: string;
  expires_at: string;
  is_stale: boolean;
  source: string;
}

/** Загружает прогноз погоды с публичного эндпоинта. */
export async function fetchWeatherForecast(): Promise<WeatherResponse> {
  const { apiBaseUrl } = getKioskConfig();
  const url = `${apiBaseUrl}/weather/forecast`;
  // Диагностика: видно фактический URL (origin + префикс) и ответ бэкенда.
  console.info("[weather] fetch:", url, "origin:", window.location.origin);
  const response = await fetch(url, {
    cache: "no-store",
  });
  if (!response.ok) {
    let body = "";
    try {
      body = await response.text();
    } catch {
      /* ignore */
    }
    console.warn("[weather] HTTP", response.status, "body:", body);
    throw new Error(`Ошибка загрузки прогноза погоды: HTTP ${response.status}`);
  }
  return (await response.json()) as WeatherResponse;
}
