import { useQuery } from "@tanstack/react-query";
import {
  fetchActiveAnnouncements,
  type AnnouncementDisplayKind,
} from "../services/announcements";

/** Ключи кеша объявлений. */
export const announcementKeys = {
  active: (kind?: AnnouncementDisplayKind) =>
    ["announcements", "active", kind ?? "all"] as const,
};

/**
 * Активные объявления для киоска.
 *
 * @param kind Ограничение: бегущая строка или лента.
 */
export function useActiveAnnouncements(kind?: AnnouncementDisplayKind) {
  return useQuery({
    queryKey: announcementKeys.active(kind),
    queryFn: () => fetchActiveAnnouncements(kind),
    staleTime: 60_000,
    refetchInterval: 60_000,
    refetchIntervalInBackground: true,
  });
}
