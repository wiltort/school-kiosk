from typing import Annotated

from fastapi import APIRouter, Depends

from src.apps.admin.auth import get_current_admin_dependency
from src.apps.admin.schemas import AdminTokenSchema
from src.apps.units.managers import AppUnitManager
from src.apps.units.schemas import (
    AppUnitResponse,
    AppUnitsOrderUpdate,
    AppUnitUpdate,
)

admin_units_router = APIRouter(prefix="/admin/units", tags=["admin_units"])


@admin_units_router.get("/", response_model=list[AppUnitResponse])
async def list_units(
    manager: Annotated[AppUnitManager, Depends()],
    _: Annotated[AdminTokenSchema, Depends(get_current_admin_dependency)],
) -> list[AppUnitResponse]:
    """Возвращает реестр сервисов киоска."""
    return await manager.list_all()


@admin_units_router.put("/order", response_model=list[AppUnitResponse])
async def reorder_units(
    payload: AppUnitsOrderUpdate,
    manager: Annotated[AppUnitManager, Depends()],
    _: Annotated[AdminTokenSchema, Depends(get_current_admin_dependency)],
) -> list[AppUnitResponse]:
    """Задаёт новый порядок плиток на главном экране."""
    return await manager.reorder(payload.keys)


@admin_units_router.patch("/{key}", response_model=AppUnitResponse)
async def update_unit(
    key: str,
    payload: AppUnitUpdate,
    manager: Annotated[AppUnitManager, Depends()],
    _: Annotated[AdminTokenSchema, Depends(get_current_admin_dependency)],
) -> AppUnitResponse:
    """Включает/выключает сервис или меняет его название."""
    return await manager.update(key, payload)
