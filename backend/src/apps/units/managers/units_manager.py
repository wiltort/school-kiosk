from fastapi import Depends, HTTPException, status

from src.apps.units.repositories import AppUnitRepository
from src.apps.units.schemas import AppUnitResponse, AppUnitUpdate
from src.core.database import DBDependency, get_db_dependency
from src.utils.retry import with_retry_commit


class AppUnitManager:
    """Управляет реестром сервисов киоска."""

    def __init__(
        self,
        db: DBDependency = Depends(get_db_dependency),
        repo: AppUnitRepository = Depends(),
    ) -> None:
        self.db = db
        self.repo = repo

    async def list_all(self) -> list[AppUnitResponse]:
        """Возвращает все сервисы в порядке отображения."""
        async with self.db.db_session() as session:
            units = await self.repo.list_all(session)
        return [AppUnitResponse.model_validate(unit) for unit in units]

    async def list_enabled(self) -> list[AppUnitResponse]:
        """Возвращает только включённые сервисы (для публичного API)."""
        return [unit for unit in await self.list_all() if unit.is_enabled]

    async def update(self, key: str, payload: AppUnitUpdate) -> AppUnitResponse:
        """Частично обновляет сервис по ключу.

        Raises:
            HTTPException: 404, если сервис с таким ключом не найден.
        """
        data = payload.model_dump(exclude_unset=True, exclude_none=True)
        async with self.db.db_session() as session:
            unit = await self.repo.get_by_key(session, key)
            if unit is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Сервис {key!r} не найден",
                )
            if data:
                await self.repo.update(session, unit, data)
                await with_retry_commit(session)
        return AppUnitResponse.model_validate(unit)

    async def reorder(self, keys: list[str]) -> list[AppUnitResponse]:
        """Задаёт новый порядок плиток.

        Raises:
            HTTPException: 400, если список ключей не совпадает с реестром.
        """
        async with self.db.db_session() as session:
            units = await self.repo.list_all(session)
            by_key = {unit.key: unit for unit in units}
            if len(keys) != len(by_key) or set(keys) != set(by_key):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Список должен содержать все сервисы без повторов",
                )
            ordered = [by_key[key] for key in keys]
            await self.repo.set_orders(session, ordered)
            await with_retry_commit(session)
        return [AppUnitResponse.model_validate(unit) for unit in ordered]
