import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createAnnouncement,
  deleteAnnouncement,
  fetchAdminAnnouncements,
  updateAnnouncement,
  type AnnouncementFormValues,
  type AnnouncementUpdateInput,
} from "../services/admin/announcements";

/** Ключ кеша админского списка объявлений. */
export const adminAnnouncementKeys = {
  all: ["admin", "announcements"] as const,
};

/** Все объявления для админ-панели. */
export function useAdminAnnouncements() {
  return useQuery({
    queryKey: adminAnnouncementKeys.all,
    queryFn: fetchAdminAnnouncements,
    staleTime: 0,
  });
}

function useInvalidateAnnouncements() {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: adminAnnouncementKeys.all });
    void queryClient.invalidateQueries({ queryKey: ["announcements"] });
  };
}

/** Создание объявления. */
export function useCreateAnnouncement() {
  const invalidate = useInvalidateAnnouncements();
  return useMutation({
    mutationFn: (input: AnnouncementFormValues) => createAnnouncement(input),
    onSuccess: invalidate,
  });
}

/** Обновление объявления. */
export function useUpdateAnnouncement() {
  const invalidate = useInvalidateAnnouncements();
  return useMutation({
    mutationFn: ({
      id,
      input,
    }: {
      id: string;
      input: AnnouncementUpdateInput;
    }) => updateAnnouncement(id, input),
    onSuccess: invalidate,
  });
}

/** Удаление объявления. */
export function useDeleteAnnouncement() {
  const invalidate = useInvalidateAnnouncements();
  return useMutation({
    mutationFn: (id: string) => deleteAnnouncement(id),
    onSuccess: invalidate,
  });
}
