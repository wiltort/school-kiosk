"""HTTP-эндпоинты админ-панели (вход + настройки).

Используются и браузером по LAN, и десктопным WebView киоска (админ-режим),
т.к. оба загружают SPA с одного origin. Настройки хранит бэкенд без БД.
"""

import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.apps.admin import autostart
from src.apps.admin.auth import create_token, get_current_admin, revoke_token
from src.core.config import settings

admin_router = APIRouter(prefix="/admin", tags=["admin"])


class LoginRequest(BaseModel):
    login: str
    password: str


class LoginResponse(BaseModel):
    token: str


class SettingsResponse(BaseModel):
    static_dir: str | None
    autostart: bool
    autostart_supported: bool


class SettingsUpdate(BaseModel):
    static_dir: str | None = None
    autostart: bool = False


@admin_router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest) -> LoginResponse:
    """Вход в админку: проверяет логин/пароль и выдаёт Bearer-токен."""
    login_ok = secrets.compare_digest(payload.login or "", settings.default_admin_login)
    password_ok = secrets.compare_digest(
        payload.password or "", settings.default_admin_password
    )
    if not (login_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )
    return LoginResponse(token=create_token())


@admin_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(token: str = Depends(get_current_admin)) -> None:
    """Выход из админки: инвалидирует текущий токен."""
    revoke_token(token)


@admin_router.get("/settings", response_model=SettingsResponse)
async def get_settings(_: str = Depends(get_current_admin)) -> SettingsResponse:
    """Возвращает текущие настройки приложения."""
    store = settings.app_settings
    return SettingsResponse(
        static_dir=store.static_dir(),
        autostart=store.autostart(),
        autostart_supported=autostart.is_supported(),
    )


@admin_router.put("/settings", response_model=SettingsResponse)
async def update_settings(
    payload: SettingsUpdate,
    _: str = Depends(get_current_admin),
) -> SettingsResponse:
    """Сохраняет настройки и применяет автозагрузку сразу.

    Смена ``static_dir`` сохраняется и вступает в силу при следующем
    перезапуске бэкенда (монтаж `/uploads` происходит на старте).
    """
    store = settings.app_settings
    store.update(
        static_dir=payload.static_dir,
        autostart=payload.autostart,
    )
    autostart.set_enabled(payload.autostart)

    return SettingsResponse(
        static_dir=store.static_dir(),
        autostart=store.autostart(),
        autostart_supported=autostart.is_supported(),
    )
