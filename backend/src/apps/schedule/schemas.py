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
    created_at: datetime = Field(
        ..., description="Дата создания", examples=[datetime.now()]
    )
    updated_at: datetime = Field(
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


class LessonBase(BaseModel):
    name: str = Field(..., description="Название урока", examples=["Математика"])
    number: int = Field(..., description="Номер урока", examples=[1])


class LessonSchema(LessonBase):
    id: uuid.UUID = Field(..., description="ID урока", examples=[uuid.uuid4()])
    model_config = ConfigDict(
        from_attributes=True,
    )


class LessonCreate(LessonBase):
    pass


class ScheduleColumnBase(BaseModel):
    number: int = Field(..., description="Номер столбца", examples=[1])
    header: str = Field(..., description="Заголовок столбца", examples=["5 класс"])


class ScheduleColumnSchema(ScheduleColumnBase):
    id: uuid.UUID = Field(..., description="ID столбца", examples=[uuid.uuid4()])
    lessons: list[LessonSchema] = Field(
        ...,
        description="Уроки",
        examples=[LessonSchema(id=uuid.uuid4(), name="Математика", number=1)],
    )
    model_config = ConfigDict(
        from_attributes=True,
    )


class ScheduleColumnCreate(ScheduleColumnBase):
    lessons: list[LessonCreate] = Field(
        ..., description="Уроки", examples=[LessonCreate(name="Математика", number=1)]
    )


class ScheduleTableBase(BaseModel):
    name: str = Field(..., description="Название расписания", examples=["Расписание 1"])
    is_active: bool = Field(..., description="Активное расписание", examples=[True])
    day_of_week: DayOfWeek = Field(
        ..., description="День недели", examples=[DayOfWeek.MONDAY]
    )


class ScheduleTableSchema(ScheduleTableBase):
    id: uuid.UUID = Field(..., description="ID расписания", examples=[uuid.uuid4()])
    schedule_columns: list[ScheduleColumnSchema] = Field(
        ...,
        description="Столбцы расписания",
        examples=[
            ScheduleColumnSchema(
                id=uuid.uuid4(),
                number=1,
                header="5 класс",
                lessons=[LessonSchema(id=uuid.uuid4(), name="Математика", number=1)],
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        ],
    )
    created_at: datetime = Field(
        ..., description="Дата создания", examples=[datetime.now()]
    )
    updated_at: datetime = Field(
        ..., description="Дата обновления", examples=[datetime.now()]
    )
    model_config = ConfigDict(
        from_attributes=True,
    )


class ScheduleTableCreate(BaseModel):
    name: str | None = Field(
        default=None,
        description="Название расписания",
        examples=["Расписание 1"],
        max_length=255,
    )
    is_active: bool | None = Field(
        default=None, description="Активное расписание", examples=[True]
    )
    day_of_week: DayOfWeek | None = Field(
        default=None, description="День недели", examples=[DayOfWeek.MONDAY]
    )
    schedule_columns: list[ScheduleColumnCreate] = Field(
        ...,
        description="Столбцы расписания",
        examples=[
            ScheduleColumnCreate(
                number=1,
                header="5 класс",
                lessons=[LessonCreate(name="Математика", number=1)],
            )
        ],
    )


class LessonUpdate(BaseModel):
    name: str | None = Field(
        None, description="Название урока", examples=["Математика"]
    )
    number: int | None = Field(None, description="Номер урока", examples=[1])


class ScheduleColumnUpdate(BaseModel):
    number: int | None = Field(None, description="Номер столбца", examples=[1])
    header: str | None = Field(
        None, description="Заголовок столбца", examples=["5 класс"]
    )
    lessons: list[LessonUpdate] | None = Field(
        None, description="Уроки", examples=[LessonCreate(name="Математика", number=1)]
    )


class ScheduleTableUpdate(BaseModel):
    name: str | None = Field(
        None, description="Название расписания", examples=["Расписание 1"]
    )
    is_active: bool | None = Field(
        default=None, description="Активное расписание", examples=[True]
    )
    day_of_week: DayOfWeek | None = Field(
        default=None, description="День недели", examples=[DayOfWeek.MONDAY]
    )


class AddColumnToScheduleTable(BaseModel):
    schedule_table_id: uuid.UUID = Field(
        ..., description="ID расписания", examples=[uuid.uuid4()]
    )
    number: int = Field(..., description="Номер столбца", examples=[1])
