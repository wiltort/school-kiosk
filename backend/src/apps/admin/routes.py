"""HTTP-эндпоинты админ-панели (вход + настройки).

Используются и браузером по LAN, и десктопным WebView киоска (админ-режим),
т.к. оба загружают SPA с одного origin. Настройки хранит бэкенд без БД.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials

from src.apps.admin import autostart
from src.apps.admin.auth import AuthManager, bearer_scheme, get_current_admin_dependency
from src.apps.admin.managers import AdminProfileManager
from src.apps.admin.schemas import (
    AdminAuth,
    AdminAuthResponse,
    AdminProfileCreate,
    AdminProfileResponse,
    AdminProfileUpdate,
    AdminTokenSchema,
    SettingsResponse,
    SettingsUpdate,
)
from src.apps.schedule.managers.schedule_image_manager import ScheduleImageManager
from src.apps.settings.services.settings_service import SettingsService
from src.core.settings_schema import SettingsKey
from src.enums.schedule_modes import ScheduleMode
from src.enums.weather_api import WeatherAPIEnum

admin_router = APIRouter(prefix="/admin", tags=["admin"])


def _settings_response(data: dict[str, Any]) -> SettingsResponse:
    """Собирает ответ API из словаря настроек."""
    schedule_mode = data.get(SettingsKey.SCHEDULE_MODE.value)
    weather_api = data.get(SettingsKey.WEATHER_API.value)
    weather_location = data.get(SettingsKey.WEATHER_LOCATION.value)
    refresh_interval = data.get(SettingsKey.WEATHER_REFRESH_INTERVAL.value)
    return SettingsResponse(
        local_image_dir=data.get(SettingsKey.SYSTEM_LOCAL_IMAGE_DIR.value),
        schedule_mode=ScheduleMode(schedule_mode or ScheduleMode.SINGLE.value),
        welcome_message=data.get(SettingsKey.UI_WELCOME_MESSAGE.value),
        autostart=bool(data.get(SettingsKey.SYSTEM_AUTOSTART.value)),
        autostart_supported=autostart.is_supported(),
        weather_enabled=bool(data.get(SettingsKey.WEATHER_ENABLED.value)),
        weather_api=WeatherAPIEnum(weather_api or WeatherAPIEnum.WTTR.value),
        weather_location=str(weather_location or "Москва"),
        weather_refresh_interval_minutes=int(refresh_interval or 60),
        announcements_enabled=bool(data.get(SettingsKey.ANNOUNCEMENTS_ENABLED.value)),
        announcements_ticker_enabled=bool(
            data.get(SettingsKey.ANNOUNCEMENTS_TICKER_ENABLED.value)
        ),
    )


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
    service: Annotated[SettingsService, Depends()],
    _: Annotated[AdminTokenSchema, Depends(get_current_admin_dependency)],
) -> SettingsResponse:
    """Возвращает текущие настройки приложения из БД."""
    return _settings_response(await service.as_dict())


@admin_router.put("/settings", response_model=SettingsResponse)
async def update_settings(
    payload: SettingsUpdate,
    service: Annotated[SettingsService, Depends()],
    schedule_manager: Annotated[ScheduleImageManager, Depends()],
    _: Annotated[AdminTokenSchema, Depends(get_current_admin_dependency)],
) -> SettingsResponse:
    """Сохраняет настройки в БД и применяет их сразу.

    Смена ``local_image_dir`` (папка локальных расписаний) используется
    бэкендом сразу. При смене режима сбрасывает все активные расписания.
    """
    current_mode = await service.get(SettingsKey.SCHEDULE_MODE)
    values: dict[str, object] = {
        SettingsKey.SYSTEM_LOCAL_IMAGE_DIR.value: payload.local_image_dir,
        SettingsKey.SCHEDULE_MODE.value: payload.schedule_mode.value,
        SettingsKey.UI_WELCOME_MESSAGE.value: payload.welcome_message,
        SettingsKey.SYSTEM_AUTOSTART.value: payload.autostart,
    }
    optional_fields = {
        "weather_enabled": SettingsKey.WEATHER_ENABLED,
        "weather_api": SettingsKey.WEATHER_API,
        "weather_location": SettingsKey.WEATHER_LOCATION,
        "weather_refresh_interval_minutes": SettingsKey.WEATHER_REFRESH_INTERVAL,
        "announcements_enabled": SettingsKey.ANNOUNCEMENTS_ENABLED,
        "announcements_ticker_enabled": SettingsKey.ANNOUNCEMENTS_TICKER_ENABLED,
    }
    for field, key in optional_fields.items():
        if field in payload.model_fields_set:
            value = getattr(payload, field)
            if value is not None:
                values[key.value] = value

    data = await service.set_many(values)
    if current_mode != payload.schedule_mode.value:
        await schedule_manager.set_all_inactive()
    autostart.set_enabled(payload.autostart)
    return _settings_response(data)


@admin_router.get(
    "/me", response_model=AdminProfileResponse, status_code=status.HTTP_200_OK
)
async def get_me(
    token: Annotated[AdminTokenSchema, Depends(get_current_admin_dependency)],
    manager: Annotated[AdminProfileManager, Depends()],
) -> AdminProfileResponse:
    """Получает данные о текущем админе."""
    return await manager.get_by_token(token)


@admin_router.patch(
    "/me", response_model=AdminProfileResponse, status_code=status.HTTP_200_OK
)
async def update_me(
    token: Annotated[AdminTokenSchema, Depends(get_current_admin_dependency)],
    manager: Annotated[AdminProfileManager, Depends()],
    payload: AdminProfileUpdate,
) -> AdminProfileResponse:
    """Редактирует данные текущего админа."""
    return await manager.update(id=token.admin_id, admin=payload)


@admin_router.post(
    "/", response_model=AdminProfileResponse, status_code=status.HTTP_201_CREATED
)
async def create_admin_profile(
    _: Annotated[AdminTokenSchema, Depends(get_current_admin_dependency)],
    payload: AdminProfileCreate,
    manager: Annotated[AdminProfileManager, Depends()],
) -> AdminProfileResponse:
    return await manager.create(payload)


@admin_router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    token: Annotated[AdminTokenSchema, Depends(get_current_admin_dependency)],
    manager: Annotated[AdminProfileManager, Depends()],
) -> None:
    return await manager.delete(token.admin_id)
