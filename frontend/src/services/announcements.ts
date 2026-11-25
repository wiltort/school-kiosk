import { getKioskConfig } from "../config/kioskConfig";

/** Способ отображения объявления. */
export type AnnouncementKind = "ticker" | "feed" | "both";

/** Вид выборки для конкретного экрана. */
export type AnnouncementDisplayKind = "ticker" | "feed";

/** Объявление школы. */
export interface Announcement {
  id: string;
  title: string;
  body: string;
  kind: AnnouncementKind;
  priority: number;
  is_active: boolean;
  starts_at: string | null;
  expires_at: string | null;
  author_id: string | null;
  created_at: string;
  updated_at: string;
}

/**
 * Загружает активные объявления с публичного эндпоинта.
 *
 * @param kind Ограничение выборки: бегущая строка или лента.
 */
export async function fetchActiveAnnouncements(
  kind?: AnnouncementDisplayKind
): Promise<Announcement[]> {
  const { apiBaseUrl } = getKioskConfig();
  const query = kind ? `?kind=${kind}` : "";
  const response = await fetch(`${apiBaseUrl}/announcements/active${query}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Ошибка загрузки объявлений: HTTP ${response.status}`);
  }
  return (await response.json()) as Announcement[];
}
