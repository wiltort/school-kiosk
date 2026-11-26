"""Публичные настройки киоска и сетевая информация для главного экрана."""

import socket
from typing import Annotated

from fastapi import APIRouter, Depends
from src.apps.settings.managers import SettingsManager
from src.apps.units.managers import AppUnitManager
from src.core.config import settings
from src.core.settings_schema import SettingsKey

network_router = APIRouter(prefix="/network", tags=["network"])
kiosk_router = APIRouter(prefix="/kiosk", tags=["kiosk"])


@kiosk_router.get("/config")
async def get_kiosk_config(
    settings_manager: Annotated[SettingsManager, Depends()],
    units_manager: Annotated[AppUnitManager, Depends()],
) -> dict:
    """Публичные настройки главного экрана (без авторизации).

    Нужны киоск-интерфейсу при загрузке: приветственное сообщение, режим
    расписания, доступные сервисы и параметры погоды/объявлений. Владелец
    значений — БД (``app_settings`` и ``app_units``), редактируются через
    админ-панель.
    """
    data = await settings_manager.as_dict()
    units = await units_manager.list_enabled()
    return {
        "welcome_message": data.get(SettingsKey.UI_WELCOME_MESSAGE.value),
        "schedule_mode": data.get(SettingsKey.SCHEDULE_MODE.value),
        "weather_enabled": bool(data.get(SettingsKey.WEATHER_ENABLED.value)),
        "weather_location": data.get(SettingsKey.WEATHER_LOCATION.value),
        "weather_refresh_interval_minutes": data.get(
            SettingsKey.WEATHER_REFRESH_INTERVAL.value
        ),
        "announcements_enabled": bool(
            data.get(SettingsKey.ANNOUNCEMENTS_ENABLED.value)
        ),
        "announcements_ticker_enabled": bool(
            data.get(SettingsKey.ANNOUNCEMENTS_TICKER_ENABLED.value)
        ),
        "units": [unit.model_dump() for unit in units],
    }


@network_router.get("/info")
async def get_network_info() -> dict:
    """Возвращает имя хоста и локальные IPv4-адреса киоска.

    Нужно фронтенду, чтобы показать на экране URL для доступа по локальной
    сети (и QR-код). Адреса loopback (127.x) исключаются — они бесполезны
    для других устройств.
    """
    hostname = socket.gethostname()
    addresses: list[str] = []
    try:
        _, _, ips = socket.gethostbyname_ex(hostname)
        addresses = [ip for ip in ips if not ip.startswith("127.")]
    except OSError:
        # Имя хоста не резолвится — вернём пустой список адресов.
        pass

    return {
        "hostname": hostname,
        "port": settings.server_port,
        "addresses": addresses,
    }
