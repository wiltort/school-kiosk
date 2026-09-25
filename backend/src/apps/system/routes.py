"""Публичные настройки киоска и сетевая информация для главного экрана."""

import socket

from fastapi import APIRouter
from src.core.config import settings

network_router = APIRouter(prefix="/network", tags=["network"])
kiosk_router = APIRouter(prefix="/kiosk", tags=["kiosk"])


@kiosk_router.get("/config")
async def get_kiosk_config() -> dict:
    """Публичные настройки главного экрана (без авторизации).

    Нужны киоск-интерфейсу при загрузке: приветственное сообщение и режим
    отображения расписания. Владелец значений — бэкенд (settings.json),
    редактируются через админ-панель.
    """
    store = settings.app_settings
    return {
        "welcome_message": store.welcome_message(),
        "schedule_mode": store.schedule_mode(),
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
