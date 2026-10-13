import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.admin import AdminToken


class AdminTokenRepository:
    """Репозиторий токенов администраторов."""

    model = AdminToken

    async def create(
        self,
        session: AsyncSession,
        *,
        admin_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> AdminToken:
        """Создать токен."""
        token = self.model(
            admin_id=admin_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        session.add(token)
        await session.flush()
        return token

    async def get_valid_by_hash(
        self, session: AsyncSession, token_hash: str
    ) -> AdminToken | None:
        """Получить токен по хешу, если он не истёк."""
        query = select(self.model).where(
            self.model.token_hash == token_hash,
            self.model.expires_at > datetime.now(UTC),
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def delete_by_hash(self, session: AsyncSession, token_hash: str) -> None:
        """Удалить токен по хешу (logout)."""
        await session.execute(
            delete(self.model).where(self.model.token_hash == token_hash)
        )
        await session.flush()

    async def delete_by_admin(self, session: AsyncSession, admin_id: uuid.UUID) -> None:
        """Удалить все токены админа (при удалении или смене пароля)."""
        await session.execute(delete(self.model).where(self.model.admin_id == admin_id))
        await session.flush()

    async def delete_expired(self, session: AsyncSession) -> int:
        """Удалить все просроченные токены. Возвращает количество удалённых."""
        result = await session.execute(
            delete(self.model).where(self.model.expires_at < datetime.now(UTC))
        )
        await session.flush()
        return result.rowcount or 0
