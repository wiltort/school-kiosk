from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any


@asynccontextmanager
async def maybe_lock(lock: Any | None, use_lock: bool) -> AsyncGenerator[None]:
    """Асинхронный контекстный менеджер опциональной блокировки.

    ``lock`` — любой объект, поддерживающий ``async with`` (например,
    ``asyncio.Lock`` или ``ProcessSafeLock`` из ``src.core.storage``).
    """
    if use_lock and lock:
        async with lock:
            yield
    else:
        yield
