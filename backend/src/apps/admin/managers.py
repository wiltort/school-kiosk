import uuid
from logging import getLogger
from typing import Annotated

from fastapi import Depends, HTTPException

from src.apps.admin.auth import AuthManager
from src.apps.admin.repositories import AdminRepository, AdminTokenRepository
from src.apps.admin.schemas import (
    AdminAuth,
    AdminAuthResponse,
    AdminProfileCreate,
    AdminProfileResponse,
    AdminProfileUpdate,
    AdminTokenSchema,
)
from src.core.database import DBDependency, get_db_dependency
from src.core.security import hash_password, verify_password
from src.utils.decorators import handle_db_errors
from src.utils.retry import with_retry_commit

logger = getLogger(__name__)


class AdminProfileManager:
    """Менеджер профилей администраторов."""

    def __init__(
        self,
        db: Annotated[DBDependency, Depends(get_db_dependency)],
        admin_repo: Annotated[AdminRepository, Depends()],
        token_repo: Annotated[AdminTokenRepository, Depends()],
        auth_manager: Annotated[AuthManager, Depends()],
    ) -> None:
        self.db = db
        self.admin_repo = admin_repo
        self.token_repo = token_repo
        self.auth_manager = auth_manager

    @handle_db_errors
    async def create(self, admin: AdminProfileCreate) -> AdminProfileResponse:
        """Создать профиль администратора."""
        async with self.db.db_session() as session:
            payload = admin.model_dump(exclude_none=True)
            password = payload.pop("password")
            if not password:
                raise HTTPException(status_code=400, detail="Пароль не передан")
            payload["password_hash"] = hash_password(password)
            admin_profile = await self.admin_repo.create(session, payload)
            await with_retry_commit(session)
            return AdminProfileResponse.model_validate(admin_profile)

    @handle_db_errors
    async def update(
        self, id: uuid.UUID, admin: AdminProfileUpdate
    ) -> AdminProfileResponse:
        """Обновить профиль администратора."""
        async with self.db.db_session() as session:
            admin_existing = await self.admin_repo.get(session, id)
            if not admin_existing:
                raise HTTPException(status_code=404, detail="Админ не найден")
            payload = admin.model_dump(exclude_unset=True)
            if not payload:
                raise HTTPException(status_code=400, detail="Нет данных для обновления")
            if "password" in payload:
                payload["password_hash"] = hash_password(payload.pop("password"))
                await self.token_repo.delete_by_admin(session, id)
            admin_profile = await self.admin_repo.update(
                session, admin=admin_existing, data=payload
            )
            await with_retry_commit(session)
            return AdminProfileResponse.model_validate(admin_profile)

    # TODO метод смены почты

    @handle_db_errors
    async def delete(self, id: uuid.UUID) -> None:
        """Удалить профиль администратора."""
        async with self.db.db_session() as session:
            admin = await self.admin_repo.get(session, id)
            if not admin:
                raise HTTPException(404, detail="Админ не найден")
            await self.admin_repo.delete(session, admin)
            await with_retry_commit(session)

    @handle_db_errors
    async def authenticate(self, admin: AdminAuth) -> AdminAuthResponse:
        """Аутентифицировать администратора."""
        async with self.db.db_session() as session:
            if not admin.login:
                raise HTTPException(status_code=400, detail="Логин не передан")
            admin_profile = await self.admin_repo.get_by_login(session, admin.login)
            if not admin_profile:
                raise HTTPException(status_code=401, detail="Неверный логин или пароль")
            if not verify_password(admin.password, admin_profile.password_hash):
                raise HTTPException(status_code=401, detail="Неверный логин или пароль")
            raw_token = await self.auth_manager.create_admin_token(
                session=session, admin_id=admin_profile.id
            )
        return AdminAuthResponse(token=raw_token)

    @handle_db_errors
    async def get_by_token(self, admin_token: AdminTokenSchema) -> AdminProfileResponse:
        """Получить пользователя по токену."""
        async with self.db.db_session() as session:
            admin = await self.admin_repo.get(session, admin_token.admin_id)
            if not admin:
                raise HTTPException(
                    status_code=404, detail="Админ с таким токеном не найден"
                )
            return AdminProfileResponse.model_validate(admin)
