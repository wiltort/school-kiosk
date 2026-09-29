import { useQuery } from "@tanstack/react-query";
import { getKioskConfig, loadKioskConfig } from "../config/kioskConfig";

/** Ключ кеша настроек киоска в React Query. */
export const kioskConfigKeys = {
  all: ["kiosk", "config"] as const,
};

/**
 * Настройки киоска из публичного эндпоинта GET /api/v1/kiosk/config
 */
export function useKioskConfig() {
  return useQuery({
    queryKey: kioskConfigKeys.all,
    queryFn: loadKioskConfig,
    initialData: () => getKioskConfig(),
    staleTime: 0,
    refetchInterval: 120_000,
    refetchIntervalInBackground: true,
  });
}
