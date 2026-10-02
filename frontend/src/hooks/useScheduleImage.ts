import { useQuery } from "@tanstack/react-query";
import {
  fetchNextSchedule,
  fetchScheduleImage,
  fetchTodaySchedule,
} from "../services/kiosk";

/** Ключ кеша активного изображения расписания (сингл-режим). */
export const scheduleImageKeys = {
  all: ["schedule", "image"] as const,
};

/** Ключ кеша расписания на сегодня (недельный режим). */
export const todayScheduleKeys = {
  all: ["schedule", "today"] as const,
};

/** Ключ кеша расписания на следующий день (недельный режим). */
export const nextScheduleKeys = {
  all: ["schedule", "next"] as const,
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

/**
 * Расписание на сегодня (GET /api/v1/schedule-images/get-today-schedule/).
 * Используется в недельном режиме; периодически опрашивается, как и сингл.
 */
export function useTodaySchedule() {
  return useQuery({
    queryKey: todayScheduleKeys.all,
    queryFn: fetchTodaySchedule,
    staleTime: 0,
    refetchOnMount: true,
    refetchOnWindowFocus: true,
    refetchInterval: 60_000,
  });
}

/**
 * Расписание на следующий учебный день (GET /api/v1/schedule-images/get-next-schedule/).
 * Запрос выполняется только после переключения на просмотр следующего дня.
 */
export function useNextSchedule(enabled: boolean) {
  return useQuery({
    queryKey: nextScheduleKeys.all,
    queryFn: fetchNextSchedule,
    staleTime: 0,
    refetchOnWindowFocus: true,
    enabled,
    // 404 (нет расписания на последующие дни) не должен ломать экран:
    // пользователь увидит сообщение и вернётся к расписанию на сегодня.
    retry: false,
  });
}
