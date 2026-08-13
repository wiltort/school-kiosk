import uuid

from fastapi import Depends, HTTPException
from sqlalchemy import case, delete, func, insert, select, update
from sqlalchemy.engine import Result
from sqlalchemy.exc import IntegrityError, NoResultFound

from src.apps.schedule.schemas import (
    ScheduleImageCreate,
    ScheduleImageGet,
    ScheduleImageUpdate,
    ScheduleTableCreate,
    ScheduleTableSchema,
    ScheduleTableUpdate,
)
from src.core.database import DBDependency, get_db_dependency
from src.enums.schedule import DayOfWeek
from src.models import Lesson, ScheduleImage, ScheduleRow, ScheduleTable


class ScheduleImageManager:
    def __init__(self, db: DBDependency = Depends(get_db_dependency)) -> None:
        self.db = db
        self.model = ScheduleImage

    async def create(self, schedule: ScheduleImageCreate) -> ScheduleImageGet:
        async with self.db.db_session() as session:
            query = (
                insert(self.model)
                .values(**schedule.model_dump(exclude_none=True))
                .returning(self.model)
            )

            try:
                result = await session.execute(query)
            except IntegrityError as e:
                raise HTTPException(status_code=400, detail=str(e)) from e
            await session.commit()
            schedule_data = result.scalar_one()
            return ScheduleImageGet.model_validate(schedule_data)

    async def get(self, id: uuid.UUID) -> ScheduleImageGet:
        async with self.db.db_session() as session:
            query = select(self.model).where(self.model.id == id)
            result = await session.execute(query)
            try:
                schedule_data = result.scalar_one()
            except NoResultFound:
                raise HTTPException(
                    status_code=404, detail="Расписание не найдено"
                ) from None
            return ScheduleImageGet.model_validate(schedule_data)

    async def get_all(self) -> list[ScheduleImageGet]:
        weekday_order = case(
            {day.name: index for index, day in enumerate(DayOfWeek, start=1)},
            value=self.model.day_of_week,
        )
        async with self.db.db_session() as session:
            query = select(self.model).order_by(weekday_order)
            result = await session.execute(query)
            schedule_data = result.scalars().all()
            return [ScheduleImageGet.model_validate(item) for item in schedule_data]

    async def update(
        self, id: uuid.UUID, schedule: ScheduleImageUpdate
    ) -> ScheduleImageGet:
        async with self.db.db_session() as session:
            data = schedule.model_dump(exclude_unset=True)
            if not data:
                raise HTTPException(status_code=400, detail="Нет данных для обновления")

            query = (
                update(self.model)
                .where(self.model.id == id)
                .values(**data)
                .returning(self.model)
            )
            try:
                result = await session.execute(query)
            except IntegrityError as e:
                raise HTTPException(status_code=400, detail=str(e)) from e
            try:
                schedule_data = result.scalar_one()
            except NoResultFound:
                raise HTTPException(
                    status_code=404, detail="Расписание не найдено"
                ) from None
            await session.commit()
            return ScheduleImageGet.model_validate(schedule_data)

    async def delete(self, id: uuid.UUID) -> None:
        async with self.db.db_session() as session:
            query = delete(self.model).where(self.model.id == id)
            result: Result = await session.execute(query)
            if hasattr(result, "rowcount"):
                if result.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Расписание не найдено")
            else:
                count = await session.scalar(
                    select(func.count())
                    .select_from(self.model)
                    .where(self.model.id == id)
                )
                if count == 0:
                    raise HTTPException(status_code=404, detail="Расписание не найдено")
            await session.commit()


class ScheduleTableManager:
    def __init__(self, db: DBDependency = Depends(get_db_dependency)) -> None:
        self.db = db
        self.model = ScheduleTable

    async def create(self, schedule: ScheduleTableCreate) -> ScheduleTableSchema:
        async with self.db.db_session() as session:
            query = (
                insert(self.model)
                .values(
                    **schedule.model_dump(exclude_none=True, exclude={"schedule_rows"})
                )
                .returning(self.model.id)
            )
            result = await session.execute(query)
            table_id = result.scalar_one()
            if schedule.schedule_rows:
                for row_data in schedule.schedule_rows:
                    row = row_data.model_dump(exclude_none=True, exclude={"lessons"})
                    row["schedule_table_id"] = table_id
                    row = ScheduleRow(**row)
                    session.add(row)
                    await session.flush()

                    if row_data.lessons:
                        for lesson_data in row_data.lessons:
                            lesson_data = lesson_data.model_dump()
                            lesson_data["schedule_row_id"] = row.id
                            lesson = Lesson(**lesson_data)
                            session.add(lesson)
            await session.flush()
            await session.commit()
            return await self.get(table_id)

    async def get(self, id: uuid.UUID) -> ScheduleTableSchema:
        async with self.db.db_session() as session:
            query = select(self.model).where(self.model.id == id)
            result = await session.execute(query)
            try:
                schedule_data = result.unique().scalar_one()
            except NoResultFound:
                raise HTTPException(
                    status_code=404, detail="Таблица расписания не найдена"
                ) from None
            return ScheduleTableSchema.model_validate(schedule_data)

    async def get_all(self) -> list[ScheduleTableSchema]:
        weekday_order = case(
            {day.name: index for index, day in enumerate(DayOfWeek, start=1)},
            value=self.model.day_of_week,
        )
        async with self.db.db_session() as session:
            query = select(self.model).order_by(weekday_order)
            result = await session.execute(query)
            schedule_data = result.unique().scalars().all()
            return [ScheduleTableSchema.model_validate(item) for item in schedule_data]

    async def update(
        self, id: uuid.UUID, schedule: ScheduleTableUpdate
    ) -> ScheduleTableSchema:
        pass
        # async with self.db.db_session() as session:
        # update_data = schedule.model_dump(execute_unset=True)
        # if not update_data:
        # raise HTTPException(status_code=400, detail="Нет данных для обновления")
        # query = select(self.model).where(self.model.id == id)
        # result = await session.execute(query)
        # table = result.unique().scalar_one()
