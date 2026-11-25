import { getKioskConfig } from "../../config/kioskConfig";
import type { AppUnit } from "../../types/kiosk";
import { bearerHeaders, requireAdminToken } from "../http";

const ADMIN_API_PATH = "/admin/units";

function adminUrl(path = "/"): string {
  const { apiBaseUrl } = getKioskConfig();
  return `${apiBaseUrl}${ADMIN_API_PATH}${path}`;
}

/** Возвращает реестр сервисов киоска. */
export async function fetchAdminUnits(): Promise<AppUnit[]> {
  const token = requireAdminToken();
  const response = await fetch(adminUrl("/"), {
    headers: bearerHeaders(token),
  });
  if (!response.ok) {
    throw new Error(`Ошибка загрузки сервисов: HTTP ${response.status}`);
  }
  return (await response.json()) as AppUnit[];
}

/** Обновляет видимость или название сервиса. */
export async function updateAdminUnit(
  key: string,
  input: Partial<Pick<AppUnit, "title" | "is_enabled">>
): Promise<AppUnit> {
  const token = requireAdminToken();
  const response = await fetch(adminUrl(`/${key}`), {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...bearerHeaders(token) },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    throw new Error(`Ошибка сохранения сервиса: HTTP ${response.status}`);
  }
  return (await response.json()) as AppUnit;
}

/** Задаёт новый порядок плиток. */
export async function reorderAdminUnits(keys: string[]): Promise<AppUnit[]> {
  const token = requireAdminToken();
  const response = await fetch(adminUrl("/order"), {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...bearerHeaders(token) },
    body: JSON.stringify({ keys }),
  });
  if (!response.ok) {
    throw new Error(`Ошибка изменения порядка: HTTP ${response.status}`);
  }
  return (await response.json()) as AppUnit[];
}
