import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from src.enums.schedule import DayOfWeek


class ScheduleImageBase(BaseModel):
    name: str = Field(
        ...,
        description="Название расписания",
        examples=["Расписание 1"],
        max_length=255,
    )
    image: str = Field(
        ...,
        description="Изображение расписания",
        examples=["image.png"],
        max_length=255,
    )
    is_active: bool = Field(..., description="Активное расписание", examples=[True])
    day_of_week: DayOfWeek = Field(
        ..., description="День недели", examples=[DayOfWeek.MONDAY]
    )


class ScheduleImageCreate(BaseModel):
    name: str | None = Field(
        default=None,
        description="Название расписания",
        examples=["Расписание 1"],
        max_length=255,
    )
    image: str = Field(
        ...,
        description="Изображение расписания",
        examples=["image.png"],
        max_length=255,
    )
    is_active: bool | None = Field(
        default=None, description="Активное расписание", examples=[True]
    )
    day_of_week: DayOfWeek | None = Field(
        default=None, description="День недели", examples=[DayOfWeek.MONDAY]
    )


class ScheduleImageUpdate(BaseModel):
    name: str | None = Field(
        None,
        description="Название расписания",
        examples=["Расписание 1"],
        max_length=255,
    )
    image: str | None = Field(
        None,
        description="Изображение расписания",
        examples=["image.png"],
        max_length=255,
    )
    is_active: bool | None = Field(
        None, description="Активное расписание", examples=[True]
    )
    day_of_week: DayOfWeek | None = Field(
        None, description="День недели", examples=[DayOfWeek.MONDAY]
    )


class ScheduleImageGet(ScheduleImageBase):
    id: uuid.UUID = Field(..., description="ID расписания", examples=[uuid.uuid4()])
    create_at: datetime = Field(
        ..., description="Дата создания", examples=[datetime.now()]
    )
    update_at: datetime = Field(
        ..., description="Дата обновления", examples=[datetime.now()]
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": str(uuid.uuid4()),
                "name": "Расписание 1",
                "image": "image.png",
                "is_active": True,
                "day_of_week": DayOfWeek.MONDAY.value,
            },
            "description": "Схема расписания",
        },
    )
