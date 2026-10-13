import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createAdminProfile,
  deleteAdminProfile,
  fetchAdminProfile,
  updateAdminProfile,
  type AdminProfile,
} from "../services/admin/profile";

/** Ключ кеша профиля админа. */
export const adminProfileKeys = {
  all: ["admin", "profile"] as const,
};

/** Профиль текущего админа (GET /admin/me). */
export function useAdminProfile() {
  return useQuery({
    queryKey: adminProfileKeys.all,
    queryFn: fetchAdminProfile,
    staleTime: 0,
  });
}

/** Обновление профиля (PATCH /admin/me). */
export function useUpdateAdminProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateAdminProfile,
    onSuccess: (saved) => {
      queryClient.setQueryData<AdminProfile>(adminProfileKeys.all, saved);
      void queryClient.invalidateQueries({ queryKey: adminProfileKeys.all });
    },
  });
}

/** Создание нового администратора (POST /admin/). */
export function useCreateAdminProfile() {
  return useMutation({
    mutationFn: createAdminProfile,
  });
}

/** Удаление собственного профиля (DELETE /admin/me). */
export function useDeleteAdminProfile() {
  return useMutation({
    mutationFn: deleteAdminProfile,
  });
}
