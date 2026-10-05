import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AdminAuth(BaseModel):
    login: str = Field(..., description="Логин", examples=["admin"], max_length=255)
    password: str = Field(
        ..., description="Пароль", examples=["password"], max_length=255
    )


class AdminProfileBase(AdminAuth):
    fullname: str | None = Field(
        ..., description="Полное имя", examples=["Иванов Иван Иванович"], max_length=255
    )


class AdminAuthResponse(BaseModel):
    token: str = Field(..., description="Токен", examples=["token"])


class AdminProfileResponse(BaseModel):
    id: uuid.UUID = Field(..., description="ID", examples=[uuid.uuid4()])
    login: str = Field(..., description="Логин", examples=["admin"], max_length=255)
    fullname: str | None = Field(
        None,
        description="Полное имя",
        examples=["Иванов Иван Иванович"],
        max_length=255,
    )
    email: str | None = Field(
        None, description="Email", examples=["email@example.com"], max_length=255
    )
    is_active: bool = Field(..., description="Активность", examples=[True])
    is_default: bool = Field(..., description="По умолчанию", examples=[True])
    created_at: datetime = Field(
        ..., description="Дата создания", examples=["2020-01-01 00:00:00"]
    )
    updated_at: datetime = Field(
        ..., description="Дата обновления", examples=["2020-01-01 00:00:00"]
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": str(uuid.uuid4()),
                "login": "admin",
                "fullname": "Иванов Иван Иванович",
                "email": "email@example.com",
                "is_active": True,
                "is_default": True,
                "created_at": "2020-01-01 00:00:00",
                "updated_at": "2020-01-01 00:00:00",
            },
            "description": "Профиль администратора",
        },
    )


class AdminProfileCreate(AdminProfileBase):
    pass


class AdminProfileUpdate(BaseModel):
    login: str | None = Field(
        None, description="Логин", examples=["admin"], max_length=255
    )
    password: str | None = Field(
        None, description="Пароль", examples=["password"], max_length=255
    )
    fullname: str | None = Field(
        None,
        description="Полное имя",
        examples=["Иванов Иван Иванович"],
        max_length=255,
    )
