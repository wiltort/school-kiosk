import { getKioskConfig } from "../../config/kioskConfig";
import { bearerHeaders, getAdminToken, setAdminToken } from "../http";

const ADMIN_API_PATH = "/admin";

/**
 * Вход в админку. При успехе сохраняет токен сессии.
 *
 * @throws Error с понятным сообщением при неверных данных.
 */
export async function loginAdmin(
  login: string,
  password: string
): Promise<void> {
  const { apiBaseUrl } = getKioskConfig();
  const response = await fetch(`${apiBaseUrl}${ADMIN_API_PATH}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ login, password }),
  });
  if (!response.ok) {
    throw new Error("Неверный логин или пароль");
  }
  const data = (await response.json()) as { token: string };
  setAdminToken(data.token);
}

/** Выход из админки (инвалидирует токен на сервере). */
export async function logoutAdmin(): Promise<void> {
  const token = getAdminToken();
  setAdminToken(null);
  if (!token) {
    return;
  }
  try {
    const { apiBaseUrl } = getKioskConfig();
    await fetch(`${apiBaseUrl}${ADMIN_API_PATH}/logout`, {
      method: "POST",
      headers: bearerHeaders(token),
    });
  } catch {
    /* токен уже очищен локально — выход считаем состоявшимся */
  }
}
