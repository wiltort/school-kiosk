import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createSchedule,
  deleteSchedule,
  fetchSchedules,
  setSingleActiveSchedule,
  updateSchedule,
  type ScheduleFormValues,
  type ScheduleUpdateValues,
} from "../services/admin/schedules";
import { scheduleImageKeys } from "./useScheduleImage";

/** Ключ кеша списка расписаний (админ-раздел «Расписания»). */
export const scheduleImagesKeys = {
  all: ["schedule", "images"] as const,
};

/**
 * Список всех расписаний (GET /api/v1/schedule-images/).
 * Панель рендерится только в админ-режиме, поэтому запрос безопасен.
 */
export function useScheduleImages() {
  return useQuery({
    queryKey: scheduleImagesKeys.all,
    queryFn: fetchSchedules,
    staleTime: 0,
  });
}

/** Создание расписания (multipart: метаданные + файл изображения). */
export function useCreateSchedule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      values,
      file,
    }: {
      values: ScheduleFormValues;
      file: File | null;
    }) => createSchedule(values, file),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: scheduleImagesKeys.all });
      void queryClient.invalidateQueries({ queryKey: scheduleImageKeys.all });
    },
  });
}

/** Обновление метаданных расписания. */
export function useUpdateSchedule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      values,
    }: {
      id: string;
      values: ScheduleUpdateValues;
    }) => updateSchedule(id, values),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: scheduleImagesKeys.all });
      void queryClient.invalidateQueries({ queryKey: scheduleImageKeys.all });
    },
  });
}

/** Удаление расписания. */
export function useDeleteSchedule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteSchedule,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: scheduleImagesKeys.all });
      void queryClient.invalidateQueries({ queryKey: scheduleImageKeys.all });
    },
  });
}

/** Активация единственного активного расписания в сингл-режиме. */
export function useSetSingleActive() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: setSingleActiveSchedule,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: scheduleImagesKeys.all });
      void queryClient.invalidateQueries({ queryKey: scheduleImageKeys.all });
    },
  });
}
