import uuid
from logging import getLogger
from typing import Annotated

from fastapi import Depends, HTTPException

from src.apps.admin.auth import create_token
from src.apps.admin.repositories import AdminRepository
from src.apps.admin.schemas import (
    AdminAuth,
    AdminAuthResponse,
    AdminProfileCreate,
    AdminProfileResponse,
    AdminProfileUpdate,
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
        repository: Annotated[AdminRepository, Depends()],
    ) -> None:
        self.db = db
        self.admin_repo = repository

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
            from src.apps.admin.auth import _tokens

            _tokens.clear()

    @handle_db_errors
    async def authenticate(self, admin: AdminAuth) -> AdminAuthResponse:
        """Аутентифицировать администратора."""
        async with self.db.db_session() as session:
            if not admin.login:
                raise HTTPException(status_code=400, detail="Логин не передан")
            admin_profile = await self.admin_repo.get_by_login(session, admin.login)
            if not admin_profile:
                raise HTTPException(status_code=404, detail="Администратор не найден")
            if not verify_password(admin.password, admin_profile.password_hash):
                raise HTTPException(status_code=401, detail="Неверный пароль")
            return AdminAuthResponse(token=create_token())
