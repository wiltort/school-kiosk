from sqlalchemy import NullPool, event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import settings


class DBDependency:
    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession] | None = None
    ) -> None:
        if session_factory is None:
            self._engine = create_async_engine(
                url=settings.database_url,
                echo=settings.db_echo,
                poolclass=NullPool,
                connect_args={"timeout": 30},
            )
            self._session_factory = async_sessionmaker(
                bind=self._engine, expire_on_commit=False, autocommit=False
            )
        else:
            self._engine = None
            self._session_factory = session_factory

    @property
    def db_session(self) -> async_sessionmaker[AsyncSession]:
        return self._session_factory

    @property
    def db_engine(self) -> AsyncEngine | None:
        return self._engine

    @staticmethod
    def _attach_sqlite_pragmas(engine: AsyncEngine) -> None:
        @event.listens_for(engine.sync_engine, "connect")
        def _set_pragmas(dbapi_connection, connection_record):  # noqa: ARG001
            cur = dbapi_connection.cursor()
            cur.execute("PRAGMA busy_timeout=30000")
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA synchronous=NORMAL")
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()


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
