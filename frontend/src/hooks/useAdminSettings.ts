import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchAdminSettings,
  updateAdminSettings,
  type AdminSettings,
} from "../services/api";
import { kioskConfigKeys } from "./useKioskConfig";

/** Ключ кеша настроек админки. */
export const adminSettingsKeys = {
  all: ["admin", "settings"] as const,
};

/**
 * Настройки админки (GET /api/v1/admin/settings). Требуют действующий токен.
 * Панель рендерится только в админ-режиме, поэтому запрос безопасен.
 */
export function useAdminSettings() {
  return useQuery({
    queryKey: adminSettingsKeys.all,
    queryFn: fetchAdminSettings,
    staleTime: 0,
  });
}

/**
 * Сохранение настроек админки (PUT /api/v1/admin/settings).
 *
 * После успеха обновляет кеш настроек и инвалидирует публичный конфиг киоска,
 * чтобы главный экран (welcome_message, schedule_mode) перерисовался сразу.
 */
export function useUpdateAdminSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateAdminSettings,
    onSuccess: (saved) => {
      queryClient.setQueryData<AdminSettings>(adminSettingsKeys.all, saved);
      void queryClient.invalidateQueries({ queryKey: adminSettingsKeys.all });
      void queryClient.invalidateQueries({ queryKey: kioskConfigKeys.all });
    },
  });
}
