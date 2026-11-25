import { useQuery } from "@tanstack/react-query";
import { fetchWeatherForecast } from "../services/weather";

/** Ключи кеша погоды. */
export const weatherKeys = {
  forecast: ["weather", "forecast"] as const,
};

/** Прогноз погоды для экрана «Погода». */
export function useWeatherForecast() {
  return useQuery({
    queryKey: weatherKeys.forecast,
    queryFn: fetchWeatherForecast,
    staleTime: 5 * 60_000,
    refetchInterval: 10 * 60_000,
    refetchIntervalInBackground: true,
    retry: 1,
  });
}
