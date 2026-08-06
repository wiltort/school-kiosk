from datetime import datetime

from pydantic import BaseModel, Field
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
    create_at: datetime = Field(
        ..., description="Дата создания", examples=[datetime.now()]
    )
    update_at: datetime = Field(
        ..., description="Дата обновления", examples=[datetime.now()]
    )


class ScheduleImageCreate(ScheduleImageBase):
    pass


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
