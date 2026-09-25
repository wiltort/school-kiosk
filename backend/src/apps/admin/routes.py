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
from src.enums.schedule_modes import ScheduleMode

admin_router = APIRouter(prefix="/admin", tags=["admin"])


class LoginRequest(BaseModel):
    login: str
    password: str


class LoginResponse(BaseModel):
    token: str


class SettingsResponse(BaseModel):
    local_image_dir: str | None
    schedule_mode: ScheduleMode
    welcome_message: str | None
    autostart: bool
    autostart_supported: bool


class SettingsUpdate(BaseModel):
    local_image_dir: str | None = None
    schedule_mode: ScheduleMode = ScheduleMode.SINGLE
    welcome_message: str | None = None
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
        local_image_dir=store.local_image_dir(),
        schedule_mode=store.schedule_mode(),
        welcome_message=store.welcome_message(),
        autostart=store.autostart(),
        autostart_supported=autostart.is_supported(),
    )


@admin_router.put("/settings", response_model=SettingsResponse)
async def update_settings(
    payload: SettingsUpdate,
    _: str = Depends(get_current_admin),
) -> SettingsResponse:
    """Сохраняет настройки и применяет автозагрузку сразу.

    Смена ``local_image_dir`` (папка локальных расписаний) сохраняется
    и используется бэкендом сразу.
    """
    store = settings.app_settings
    store.update(
        local_image_dir=payload.local_image_dir,
        schedule_mode=payload.schedule_mode,
        welcome_message=payload.welcome_message,
        autostart=payload.autostart,
    )
    autostart.set_enabled(payload.autostart)

    return SettingsResponse(
        local_image_dir=store.local_image_dir(),
        schedule_mode=store.schedule_mode(),
        welcome_message=store.welcome_message(),
        autostart=store.autostart(),
        autostart_supported=autostart.is_supported(),
    )
