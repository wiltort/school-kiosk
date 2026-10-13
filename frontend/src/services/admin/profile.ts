import { getKioskConfig } from "../../config/kioskConfig";
import { bearerHeaders, requireAdminToken } from "../http";

const ADMIN_API_PATH = "/admin";

/** Профиль текущего администратора (GET /admin/me). */
export interface AdminProfile {
  id: string;
  login: string;
  fullname: string | null;
  email: string | null;
  is_active: boolean;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

/** Данные для обновления профиля (PATCH /admin/me). */
export interface AdminProfileUpdate {
  login?: string;
  password?: string;
  fullname?: string | null;
}

/** Данные для создания нового администратора (POST /admin/). */
export interface AdminProfileCreate {
  login: string;
  password: string;
  fullname?: string | null;
}

/** Возвращает профиль текущего админа. Требует действующий токен. */
export async function fetchAdminProfile(): Promise<AdminProfile> {
  const token = requireAdminToken();
  const { apiBaseUrl } = getKioskConfig();
  const response = await fetch(`${apiBaseUrl}${ADMIN_API_PATH}/me`, {
    headers: bearerHeaders(token),
  });
  if (!response.ok) {
    throw new Error(`Ошибка загрузки профиля: HTTP ${response.status}`);
  }
  return (await response.json()) as AdminProfile;
}

/** Обновляет профиль текущего админа. */
export async function updateAdminProfile(
  data: AdminProfileUpdate
): Promise<AdminProfile> {
  const token = requireAdminToken();
  const { apiBaseUrl } = getKioskConfig();
  const response = await fetch(`${apiBaseUrl}${ADMIN_API_PATH}/me`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...bearerHeaders(token) },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    throw new Error(`Ошибка сохранения профиля: HTTP ${response.status}`);
  }
  return (await response.json()) as AdminProfile;
}

/** Создаёт нового администратора (POST /admin/). */
export async function createAdminProfile(
  data: AdminProfileCreate
): Promise<AdminProfile> {
  const token = requireAdminToken();
  const { apiBaseUrl } = getKioskConfig();
  const response = await fetch(`${apiBaseUrl}${ADMIN_API_PATH}/`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...bearerHeaders(token) },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    throw new Error(`Ошибка создания администратора: HTTP ${response.status}`);
  }
  return (await response.json()) as AdminProfile;
}

/** Удаляет профиль текущего админа (DELETE /admin/me). */
export async function deleteAdminProfile(): Promise<void> {
  const token = requireAdminToken();
  const { apiBaseUrl } = getKioskConfig();
  const response = await fetch(`${apiBaseUrl}${ADMIN_API_PATH}/me`, {
    method: "DELETE",
    headers: bearerHeaders(token),
  });
  if (!response.ok) {
    throw new Error(`Ошибка удаления профиля: HTTP ${response.status}`);
  }
}
