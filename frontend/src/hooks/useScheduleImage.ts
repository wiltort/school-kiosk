import { useQuery } from "@tanstack/react-query";
import { fetchScheduleImage } from "../services/kiosk";

/** Ключ кеша активного изображения расписания. */
export const scheduleImageKeys = {
  all: ["schedule", "image"] as const,
};

/**
 * Активное изображение расписания (GET /api/v1/schedule-images/get-single-schedule/).
 */
export function useScheduleImage() {
  return useQuery({
    queryKey: scheduleImageKeys.all,
    queryFn: fetchScheduleImage,
    staleTime: 0,
    refetchOnMount: true,
    refetchOnWindowFocus: true,
    // Киоск работает в полноэкранном режиме без смены фокуса: чтобы изменения,
    // сделанные админом с другого устройства, подхватывались автоматически,
    // периодически опрашиваем активное расписание.
    refetchInterval: 60_000,
  });
}
