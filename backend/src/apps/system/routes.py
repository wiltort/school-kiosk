"""Сетевая информация киоска для панели «подключиться по локальной сети»."""

import socket

from fastapi import APIRouter
from src.core.config import settings

network_router = APIRouter(prefix="/network", tags=["network"])


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
