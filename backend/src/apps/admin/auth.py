"""Простая HTTP-авторизация админ-панели.

Логин проверяется по значениям по умолчанию из конфига
(`BACKEND_DEFAULT_ADMIN_LOGIN` / `BACKEND_DEFAULT_ADMIN_PASSWORD`). После
успешного входа создаётся случайный токен, который хранится в оперативной
памяти процесса (без БД). Защищённые эндпоинты требуют заголовка
`Authorization: Bearer <token>`.
"""

import secrets

from fastapi import Header, HTTPException, status

# Действующие токены сессий (in-memory). Теряются при перезапуске бэкенда —
# для киоск-сценария это приемлемо и безопасно.
_tokens: set[str] = set()


def create_token() -> str:
    """Создаёт новый действующий токен сессии."""
    token = secrets.token_urlsafe(32)
    _tokens.add(token)
    return token


def revoke_token(token: str) -> None:
    """Инвалидирует токен (выход из админки)."""
    _tokens.discard(token)


async def get_current_admin(
    authorization: str | None = Header(default=None),
) -> str:
    """FastAPI-dependency: возвращает токен, если он валиден."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Отсутствует токен авторизации",
        )
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or token not in _tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный или истёкший токен",
        )
    return token
