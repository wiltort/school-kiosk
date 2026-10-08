"""HTTP-эндпоинты админ-панели (вход + настройки).

Используются и браузером по LAN, и десктопным WebView киоска (админ-режим),
т.к. оба загружают SPA с одного origin. Настройки хранит бэкенд без БД.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials

from src.apps.admin import autostart
from src.apps.admin.auth import AuthManager, bearer_scheme, get_current_admin_dependency
from src.apps.admin.managers import AdminProfileManager
from src.apps.admin.schemas import (
    AdminAuth,
    AdminAuthResponse,
    AdminProfileResponse,
    AdminTokenSchema,
    SettingsResponse,
    SettingsUpdate,
)
from src.apps.schedule.managers.schedule_image_manager import ScheduleImageManager
from src.core.config import settings

admin_router = APIRouter(prefix="/admin", tags=["admin"])


@admin_router.post("/login", response_model=AdminAuthResponse)
async def login(
    payload: AdminAuth, manager: Annotated[AdminProfileManager, Depends()]
) -> AdminAuthResponse:
    """Вход в админку: проверяет логин/пароль и выдаёт Bearer-токен."""
    return await manager.authenticate(payload)


@admin_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    auth_manager: Annotated[AuthManager, Depends()],
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ] = None,
) -> None:
    """Выход: отзывает переданный Bearer-токен (если он есть)."""
    await auth_manager.revoke_current_token(
        credentials.credentials if credentials else None
    )


@admin_router.get("/settings", response_model=SettingsResponse)
async def get_settings(
    _: Annotated[AdminTokenSchema, Depends(get_current_admin_dependency)],
) -> SettingsResponse:
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
    schedule_manager: Annotated[ScheduleImageManager, Depends()],
    _: Annotated[AdminTokenSchema, Depends(get_current_admin_dependency)],
) -> SettingsResponse:
    """Сохраняет настройки и применяет автозагрузку сразу.

    Смена ``local_image_dir`` (папка локальных расписаний) сохраняется
    и используется бэкендом сразу. При смене режима сбрасывает все активные
    расписания.
    """
    store = settings.app_settings
    schedule_mode_changed = store.schedule_mode() != payload.schedule_mode
    store.update(
        local_image_dir=payload.local_image_dir,
        schedule_mode=payload.schedule_mode,
        welcome_message=payload.welcome_message,
        autostart=payload.autostart,
    )
    if schedule_mode_changed:
        await schedule_manager.set_all_inactive()
    autostart.set_enabled(payload.autostart)

    return SettingsResponse(
        local_image_dir=store.local_image_dir(),
        schedule_mode=store.schedule_mode(),
        welcome_message=store.welcome_message(),
        autostart=store.autostart(),
        autostart_supported=autostart.is_supported(),
    )


@admin_router.get(
    "/me", response_model=AdminProfileResponse, status_code=status.HTTP_200_OK
)
async def get_me(
    token: Annotated[AdminTokenSchema, Depends(get_current_admin_dependency)],
    manager: Annotated[AdminProfileManager, Depends()],
) -> AdminProfileResponse:
    return await manager.get_by_token(token)
