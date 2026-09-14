from logging import getLogger

from fastapi import Depends, HTTPException
from sqlalchemy import insert, select
from sqlalchemy.engine import Result
from sqlalchemy.exc import IntegrityError

from src.apps.schedule.schemas import (
    AddColumnToScheduleTable,
    AddLessonToScheduleColumn,
    LessonSchema,
    LessonUpdate,
    ScheduleColumnSchema,
    ScheduleColumnUpdate,
)
from src.core.database import DBDependency, get_db_dependency
from src.models import Lesson, ScheduleColumn, ScheduleTable

logger = getLogger(__name__)


class ScheduleContentManager:
    """Менеджер содержимого табличного расписания.

    Отвечает за CRUD-операции над столбцами (:class:`ScheduleColumn`)
    и уроками (:class:`Lesson`) внутри табличного расписания.
    Отдельные операции (создание столбца/урока, обновление столбца/урока)
    выполняются независимо от самого расписания.

    Raises:
        HTTPException: с кодом 400 при нарушении целостности данных
            или отсутствии данных для обновления; с кодом 404, когда
            столбец или урок не найден.
    """

    def __init__(
        self,
        db: DBDependency = Depends(get_db_dependency),
        model: type[ScheduleTable] = ScheduleTable,
        column_model: type[ScheduleColumn] = ScheduleColumn,
        lesson_model: type[Lesson] = Lesson,
    ) -> None:
        """Инициализирует менеджер.

        Args:
            db: Зависимость для доступа к сессии базы данных.
                По умолчанию подставляется через FastAPI.
            model: Модель табличного расписания.
            column_model: Модель столбца табличного расписания.
            lesson_model: Модель урока табличного расписания.
        """
        self.db = db
        self.model = model
        self.column_model = column_model
        self.lesson_model = lesson_model

    async def create_column(
        self, column: AddColumnToScheduleTable
    ) -> ScheduleColumnSchema:
        """Создает новый столбец в таблице расписания.

        Args:
            column: Данные для создания столбца.

        Returns:
            Созданный столбец в виде схемы :class:`ScheduleColumnSchema`.
        """
        async with self.db.db_session() as session:
            query = (
                insert(self.column_model)
                .values(**column.model_dump(exclude_none=True))
                .returning(self.column_model)
            )
            try:
                result: Result = await session.execute(query)
            except IntegrityError as e:
                logger.warning("Integrity error при создании колонки %s", e)
                raise HTTPException(
                    status_code=400, detail="Нарушение целостности данных"
                ) from e
            await session.commit()
            column_data = result.unique().scalar_one()
            return ScheduleColumnSchema(
                id=column_data.id,
                schedule_table_id=column_data.schedule_table_id,
                number=column_data.number,
                header=column_data.header,
                lessons=[],
            )

    async def create_lesson(self, lesson: AddLessonToScheduleColumn) -> LessonSchema:
        """Создает новый урок в столбце расписания.

        Args:
            lesson: Данные для создания урока.

        Returns:
            Созданный урок в виде схемы :class:`LessonSchema`.
        """
        async with self.db.db_session() as session:
            query = (
                insert(self.lesson_model)
                .values(**lesson.model_dump(exclude_none=True))
                .returning(self.lesson_model)
            )
            try:
                result: Result = await session.execute(query)
            except IntegrityError as e:
                logger.warning("Integrity error при создании урока %s", e)
                raise HTTPException(
                    status_code=400, detail="Нарушение целостности данных"
                ) from e
            await session.commit()
            lesson_data = result.unique().scalar_one()
            return LessonSchema.model_validate(lesson_data)

    async def update_column(self, column: ScheduleColumnUpdate) -> ScheduleColumnSchema:
        """Обновляет столбец в таблице расписания.

        Args:
            column: Данные для обновления столбца.

        Returns:
            Обновленный столбец в виде схемы :class:`ScheduleColumnSchema`.
        """
        async with self.db.db_session() as session:
            update_data = column.model_dump(exclude_unset=True, exclude={"id"})
            if not update_data:
                raise HTTPException(
                    status_code=400, detail="Не указаны данные для обновления"
                )
            query = select(self.column_model).where(self.column_model.id == column.id)
            result: Result = await session.execute(query)

            column = result.unique().scalar_one_or_none()
            if not column:
                raise HTTPException(status_code=404, detail="Столбец не найден")
            for key, value in update_data.items():
                if hasattr(column, key):
                    setattr(column, key, value)
            try:
                await session.commit()
            except IntegrityError as e:
                logger.warning("Integrity error при обновлении столбца %s", e)
                logger.warning("Rollback")
                raise HTTPException(
                    status_code=400, detail="Нарушение целостности данных"
                ) from e
            result: Result = await session.execute(
                select(self.column_model).where(self.column_model.id == column.id)
            )
            column = result.unique().scalar_one()
            return ScheduleColumnSchema.model_validate(column)

    async def update_lesson(self, lesson: LessonUpdate) -> LessonSchema:
        """Обновляет урок в столбце расписания.

        Args:
            lesson: Данные для обновления урока.

        Returns:
            Обновленный урок в виде схемы :class:`LessonSchema`.
        """
        async with self.db.db_session() as session:
            update_data = lesson.model_dump(exclude_unset=True, exclude={"id"})
            if not update_data:
                raise HTTPException(
                    status_code=400, detail="Не указаны данные для обновления"
                )
            query = select(self.lesson_model).where(self.lesson_model.id == lesson.id)
            result: Result = await session.execute(query)

            lesson = result.unique().scalar_one_or_none()
            if not lesson:
                raise HTTPException(status_code=404, detail="Урок не найден")
            for key, value in update_data.items():
                if hasattr(lesson, key):
                    setattr(lesson, key, value)
            try:
                await session.commit()
            except IntegrityError as e:
                logger.warning("Integrity error при обновлении урока %s", e)
                raise HTTPException(
                    status_code=400, detail="Нарушение целостности данных"
                ) from e
            result: Result = await session.execute(
                select(self.lesson_model).where(self.lesson_model.id == lesson.id)
            )
            lesson = result.unique().scalar_one()
            return LessonSchema.model_validate(lesson)
