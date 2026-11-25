import { getKioskConfig } from "../../config/kioskConfig";
import type { Announcement, AnnouncementKind } from "../announcements";
import { bearerHeaders, requireAdminToken } from "../http";

const ADMIN_API_PATH = "/admin/announcements";

/** Значения формы объявления. */
export interface AnnouncementFormValues {
  title: string;
  body: string;
  kind: AnnouncementKind;
  priority: number;
  is_active: boolean;
  starts_at: string | null;
  expires_at: string | null;
}

/** Частичное обновление объявления. */
export type AnnouncementUpdateInput = Partial<AnnouncementFormValues>;

function adminUrl(path = ""): string {
  const { apiBaseUrl } = getKioskConfig();
  return `${apiBaseUrl}${ADMIN_API_PATH}${path}`;
}

/** Возвращает все объявления для админ-панели. */
export async function fetchAdminAnnouncements(): Promise<Announcement[]> {
  const token = requireAdminToken();
  const response = await fetch(`${adminUrl("/")}`, {
    headers: bearerHeaders(token),
  });
  if (!response.ok) {
    throw new Error(`Ошибка загрузки объявлений: HTTP ${response.status}`);
  }
  return (await response.json()) as Announcement[];
}

/** Создаёт объявление. */
export async function createAnnouncement(
  input: AnnouncementFormValues
): Promise<Announcement> {
  const token = requireAdminToken();
  const response = await fetch(`${adminUrl("/")}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...bearerHeaders(token) },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    throw new Error(`Ошибка создания объявления: HTTP ${response.status}`);
  }
  return (await response.json()) as Announcement;
}

/** Частично обновляет объявление. */
export async function updateAnnouncement(
  id: string,
  input: AnnouncementUpdateInput
): Promise<Announcement> {
  const token = requireAdminToken();
  const response = await fetch(adminUrl(`/${id}`), {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...bearerHeaders(token) },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    throw new Error(`Ошибка сохранения объявления: HTTP ${response.status}`);
  }
  return (await response.json()) as Announcement;
}

/** Удаляет объявление. */
export async function deleteAnnouncement(id: string): Promise<void> {
  const token = requireAdminToken();
  const response = await fetch(adminUrl(`/${id}`), {
    method: "DELETE",
    headers: bearerHeaders(token),
  });
  if (!response.ok) {
    throw new Error(`Ошибка удаления объявления: HTTP ${response.status}`);
  }
}
