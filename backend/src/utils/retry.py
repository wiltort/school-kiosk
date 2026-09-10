import asyncio

from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession


async def with_retry_commit(
    session: AsyncSession, attempts: int = 5, base_delay: float = 0.1
):
    for i in range(attempts):
        try:
            await session.commit()
            return
        except OperationalError as e:
            await session.rollback()
            if "database is locked" not in str(e).lower() or i == attempts - 1:
                raise
            await asyncio.sleep(base_delay * (2**i))
