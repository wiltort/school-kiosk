import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager


@asynccontextmanager
async def maybe_lock(lock: asyncio.Lock | None, use_lock: bool) -> AsyncGenerator[None]:
    if use_lock and lock:
        async with lock:
            yield
    else:
        yield
