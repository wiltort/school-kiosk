from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import settings


class DBDependency:
    def __init__(self) -> None:
        self._engine = create_async_engine(
            url=settings.database_url, echo=settings.db_echo
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine, expire_on_commit=False, autocommit=False
        )

    @property
    def db_session(self) -> async_sessionmaker[AsyncSession]:
        return self._session_factory

    @property
    def db_engine(self) -> AsyncEngine:
        return self._engine


_db: DBDependency | None = None


def get_db_dependency() -> DBDependency:
    """Возвращает единственный экземпляр DBDependency (синглтон).

    Используется как FastAPI-зависимость и внутри lifespan, чтобы все
    потребители работали с одним и тем же AsyncEngine.
    """
    global _db
    if _db is None:
        _db = DBDependency()
    return _db


def reset_db_dependency() -> None:
    """Сброс синглтона."""
    global _db
    _db = None
