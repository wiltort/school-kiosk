"""Простая HTTP-авторизация админ-панели.

Защищённые эндпоинты требуют заголовка
`Authorization: Bearer <token>`.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.admin.repositories import AdminTokenRepository
from src.apps.admin.schemas import AdminTokenSchema
from src.core.database import DBDependency, get_db_dependency
from src.core.security import generate_token, hash_token
from src.utils.retry import with_retry_commit


class AuthManager:
    TOKEN_TTL = timedelta(hours=24)

    def __init__(
        self,
        db: Annotated[DBDependency, Depends(get_db_dependency)],
        token_repo: Annotated[AdminTokenRepository, Depends()],
    ):
        self.db = db
        self.token_repo = token_repo

    async def create_admin_token(
        self,
        admin_id: uuid.UUID,
        session: AsyncSession | None = None,
    ) -> str:
        """Создаёт токен и возвращает сырое значение (не хеш!).

        Коммит (с ретраями при SQLite-локе) всегда выполняется здесь —
        независимо от того, передан ли внешний ``session``.
        """
        raw_token = generate_token()
        token_hash = hash_token(raw_token)
        expires_at = datetime.now(UTC) + self.TOKEN_TTL

        if session is None:
            async with self.db.db_session() as own_session:
                await self._create_and_commit(
                    own_session,
                    admin_id=admin_id,
                    token_hash=token_hash,
                    expires_at=expires_at,
                )
        else:
            await self._create_and_commit(
                session,
                admin_id=admin_id,
                token_hash=token_hash,
                expires_at=expires_at,
            )
        return raw_token

    async def _create_and_commit(
        self,
        session: AsyncSession,
        *,
        admin_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> None:
        """Создаёт токен в переданной сессии и коммитит с ретраями."""
        await self.token_repo.create(
            session,
            admin_id=admin_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        await with_retry_commit(session)

    async def get_current_admin(
        self,
        authorization: str | None = Header(default=None),
    ) -> AdminTokenSchema:
        """FastAPI-dependency: возвращает токен, если он валиден и не истёк."""
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Отсутствует токен авторизации",
            )

        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Недействительный формат токена",
            )

        token_hash = hash_token(token)

        async with self.db.db_session() as session:
            admin_token = await self.token_repo.get_valid_by_hash(session, token_hash)

        if admin_token is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Недействительный или истёкший токен",
            )

        return AdminTokenSchema.model_validate(admin_token)

    async def revoke_current_token(
        self,
        authorization: str | None,
    ) -> None:
        """Отзывает текущий токен (logout)."""
        if not authorization:
            return
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return
        token_hash = hash_token(token)
        async with self.db.db_session() as session:
            await self.token_repo.delete_by_hash(session, token_hash)
            await with_retry_commit(session)

    async def revoke_all_tokens_for_admin(
        self,
        admin_id: uuid.UUID,
    ) -> None:
        """Отзывает все токены админа (при смене пароля, удалении)."""
        async with self.db.db_session() as session:
            await self.token_repo.delete_by_admin(session, admin_id)
            await with_retry_commit(session)


async def get_current_admin_dependency(
    auth_manager: Annotated[AuthManager, Depends()],
    authorization: Annotated[str | None, Header()] = None,
) -> AdminTokenSchema:
    """FastAPI-dependency для получения токена."""
    return await auth_manager.get_current_admin(authorization)
