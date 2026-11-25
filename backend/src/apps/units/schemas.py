from pydantic import BaseModel, ConfigDict, Field


class AppUnitResponse(BaseModel):
    """Сервис киоска в публичном и админском API."""

    key: str = Field(..., description="Стабильный ключ сервиса", examples=["weather"])
    title: str = Field(..., description="Название плитки", examples=["Погода"])
    is_enabled: bool = Field(..., description="Показывать сервис на киоске")
    order: int = Field(..., description="Порядок плитки на главном экране")

    model_config = ConfigDict(from_attributes=True)


class AppUnitUpdate(BaseModel):
    """Частичное обновление сервиса."""

    title: str | None = Field(None, min_length=1, max_length=255)
    is_enabled: bool | None = None


class AppUnitsOrderUpdate(BaseModel):
    """Новый порядок плиток: ключи в нужной последовательности."""

    keys: list[str] = Field(..., min_length=1, description="Ключи в нужном порядке")
