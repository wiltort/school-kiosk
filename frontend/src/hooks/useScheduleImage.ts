import { useQuery } from "@tanstack/react-query";
import { fetchScheduleImage } from "../services/api";

/** Ключ кеша активного изображения расписания. */
export const scheduleImageKeys = {
  all: ["schedule", "image"] as const,
};

/**
 * Активное изображение расписания (GET /api/v1/schedule_images_local/).
 */
export function useScheduleImage() {
  return useQuery({
    queryKey: scheduleImageKeys.all,
    queryFn: fetchScheduleImage,
    staleTime: 0,
    refetchOnMount: true,
    refetchOnWindowFocus: true,
  });
}
