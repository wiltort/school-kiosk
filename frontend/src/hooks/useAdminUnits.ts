import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchAdminUnits,
  reorderAdminUnits,
  updateAdminUnit,
} from "../services/admin/units";
import type { AppUnit } from "../types/kiosk";
import { kioskConfigKeys } from "./useKioskConfig";

/** Ключ кеша админского реестра сервисов. */
export const adminUnitKeys = {
  all: ["admin", "units"] as const,
};

/** Реестр сервисов киоска. */
export function useAdminUnits() {
  return useQuery({
    queryKey: adminUnitKeys.all,
    queryFn: fetchAdminUnits,
    staleTime: 0,
  });
}

function useInvalidateUnits() {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: adminUnitKeys.all });
    void queryClient.invalidateQueries({ queryKey: kioskConfigKeys.all });
  };
}

/** Обновление видимости/названия сервиса. */
export function useUpdateAdminUnit() {
  const invalidate = useInvalidateUnits();
  return useMutation({
    mutationFn: ({
      key,
      input,
    }: {
      key: string;
      input: Partial<Pick<AppUnit, "title" | "is_enabled">>;
    }) => updateAdminUnit(key, input),
    onSuccess: invalidate,
  });
}

/** Изменение порядка плиток. */
export function useReorderAdminUnits() {
  const invalidate = useInvalidateUnits();
  return useMutation({
    mutationFn: (keys: string[]) => reorderAdminUnits(keys),
    onSuccess: invalidate,
  });
}
