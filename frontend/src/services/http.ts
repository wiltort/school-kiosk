const ADMIN_TOKEN_KEY = "school_kiosk_admin_token";

/** Токен админ-сессии из sessionStorage (null, если вход не выполнен). */
export function getAdminToken(): string | null {
  try {
    return sessionStorage.getItem(ADMIN_TOKEN_KEY);
  } catch {
    return null;
  }
}

/** Сохраняет или очищает токен админ-сессии. */
export function setAdminToken(token: string | null): void {
  try {
    if (token) {
      sessionStorage.setItem(ADMIN_TOKEN_KEY, token);
    } else {
      sessionStorage.removeItem(ADMIN_TOKEN_KEY);
    }
  } catch {
    /* ignore: sessionStorage может быть недоступен */
  }
}

/** Есть ли активная админ-сессия (токен в sessionStorage). */
export function isAdminLoggedIn(): boolean {
  return getAdminToken() !== null;
}

/** Заголовки авторизации Bearer для админ-запросов. */
export function bearerHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

/** Токен админа; бросает ошибку, если сессия не активна. */
export function requireAdminToken(): string {
  const token = getAdminToken();
  if (!token) {
    throw new Error("Нет авторизации");
  }
  return token;
}
