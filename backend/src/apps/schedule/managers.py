import uuid
from logging import getLogger

from fastapi import Depends, HTTPException
from sqlalchemy import case, delete, insert, select
from sqlalchemy.engine import Result
from sqlalchemy.exc import IntegrityError, NoResultFound

from src.apps.schedule.repositories import ScheduleImageRepository
from src.apps.schedule.schemas import (
    AddColumnToScheduleTable,
    AddLessonToScheduleColumn,
    LessonSchema,
    LessonUpdate,
    ScheduleColumnSchema,
    ScheduleColumnUpdate,
    ScheduleImageCreate,
    ScheduleImageGet,
    ScheduleImageUpdate,
    ScheduleTableCreate,
    ScheduleTableSchema,
    ScheduleTableUpdate,
)
from src.core.database import DBDependency, get_db_dependency
from src.enums.schedule import DayOfWeek
from src.models import Lesson, ScheduleColumn, ScheduleTable
from src.utils.decorators import handle_db_errors

logger = getLogger(__name__)


class ScheduleImageManager:
    """Менеджер операций над расписаниями в виде изображений.

    Отвечает за CRUD-операции над сущностью :class:`ScheduleImage`.
    Все методы работают в рамках отдельной сессии базы данных,
    открываемой через ``self.db.db_session()``.

    Raises:
        HTTPException: с кодом 400 при нарушении целостности данных
            и с кодом 404, когда запись не найдена.
    """

    def __init__(
        self,
        db: DBDependency = Depends(get_db_dependency),
        image_repo: ScheduleImageRepository = Depends(),
    ) -> None:
        """Инициализирует менеджер.

        Args:
            db: Зависимость для доступа к сессии базы данных.
                По умолчанию подставляется через FastAPI.
            image_repo: Репозиторий для выполнения CRUD-операций
                над сущностью :class:`ScheduleImage`.
        """
        self.db = db
        self.image_repo = image_repo

    @handle_db_errors
    async def create(self, schedule: ScheduleImageCreate) -> ScheduleImageGet:
        """Создаёт новое расписание-изображение.

        Args:
            schedule: Данные для создания расписания.

        Returns:
            Созданное расписание в виде схемы :class:`ScheduleImageGet`.

        Raises:
            HTTPException: с кодом 400 при нарушении ограничений
                целостности базы данных (например, дубликат).
        """
        async with self.db.db_session() as session:
            image = await self.image_repo.create(
                session, schedule.model_dump(exclude_none=True)
            )
            await session.commit()
            return ScheduleImageGet.model_validate(image)

    @handle_db_errors
    async def get(self, id: uuid.UUID) -> ScheduleImageGet:
        """Возвращает расписание-изображение по идентификатору.

        Args:
            id: Уникальный идентификатор расписания.

        Returns:
            Расписание в виде схемы :class:`ScheduleImageGet`.

        Raises:
            HTTPException: с кодом 404, если запись не найдена.
        """
        async with self.db.db_session() as session:
            image = await self.image_repo.get(session, id)

            if not image:
                raise HTTPException(status_code=404, detail="Расписание не найдено")
            return ScheduleImageGet.model_validate(image)

    @handle_db_errors
    async def get_all(self) -> list[ScheduleImageGet]:
        """Возвращает все расписания-изображения.

        Результат сортируется по дню недели (порядок определяется
        перечислением :class:`DayOfWeek`).

        Returns:
            Список всех расписаний в виде схем :class:`ScheduleImageGet`.
        """
        async with self.db.db_session() as session:
            images = await self.image_repo.get_all(session)
            return [ScheduleImageGet.model_validate(item) for item in images]

    @handle_db_errors
    async def update(
        self, id: uuid.UUID, schedule: ScheduleImageUpdate
    ) -> ScheduleImageGet:
        """Обновляет расписание-изображение по идентификатору.

        Args:
            id: Уникальный идентификатор расписания.
            schedule: Поля, подлежащие обновлению (обновляются
                только переданные значения).

        Returns:
            Обновлённое расписание в виде схемы :class:`ScheduleImageGet`.

        Raises:
            HTTPException: с кодом 400, если не передано ни одного поля
                для обновления или нарушена целостность данных;
                с кодом 404, если запись не найдена.
        """
        async with self.db.db_session() as session:
            data = schedule.model_dump(exclude_unset=True)
            if not data:
                raise HTTPException(status_code=400, detail="Нет данных для обновления")
            result = await self.image_repo.update(session, id, data)
            await session.commit()
            return ScheduleImageGet.model_validate(result)

    async def delete(self, id: uuid.UUID) -> None:
        """Удаляет расписание-изображение по идентификатору.

        Args:
            id: Уникальный идентификатор расписания.

        Raises:
            HTTPException: с кодом 404, если запись не найдена.
        """
        async with self.db.db_session() as session:
            result = await self.image_repo.delete(session, id)
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Расписание не найдено")
            await session.commit()


class ScheduleTableManager:
    """Менеджер операций над табличными расписаниями.

    Отвечает за CRUD-операции над сущностью :class:`ScheduleTable`,
    а также за каскадное создание столбцов (:class:`ScheduleColumn`) и
    уроков (:class:`Lesson`), входящих в состав расписания.

    Raises:
        HTTPException: с кодом 404, когда запись не найдена.
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

    async def create(self, schedule: ScheduleTableCreate) -> ScheduleTableSchema:
        """Создаёт новое табличное расписание.

        Помимо самой таблицы создаёт связанные столбцы и уроки,
        если они переданы во входных данных.

        Args:
            schedule: Данные для создания расписания, включая столбцы
                и уроки.

        Returns:
            Созданное расписание в виде схемы :class:`ScheduleTableSchema`.
        """
        async with self.db.db_session() as session:
            query = (
                insert(self.model)
                .values(
                    **schedule.model_dump(
                        exclude_none=True, exclude={"schedule_columns"}
                    )
                )
                .returning(self.model.id)
            )
            try:
                result: Result = await session.execute(query)
            except IntegrityError as e:
                logger.warning("Integrity error при создании расписания %s", e)
                raise HTTPException(
                    status_code=400, detail="Нарушение целостности данных"
                ) from e
            table_id = result.scalar_one()
            if schedule.schedule_columns:
                for column_data in schedule.schedule_columns:
                    column = column_data.model_dump(
                        exclude_none=True, exclude={"lessons"}
                    )
                    column["schedule_table_id"] = table_id
                    column = self.column_model(**column)
                    try:
                        session.add(column)
                        await session.flush()
                    except IntegrityError as e:
                        logger.warning("Integrity error при создании столбца %s", e)
                        raise HTTPException(
                            status_code=400, detail="Нарушение целостности данных"
                        ) from e

                    if column_data.lessons:
                        for lesson_data in column_data.lessons:
                            lesson_data = lesson_data.model_dump()
                            lesson_data["schedule_column_id"] = column.id
                            lesson = self.lesson_model(**lesson_data)
                            session.add(lesson)
            try:
                await session.flush()
            except IntegrityError as e:
                logger.warning("Integrity error при создании столбца %s", e)
                raise HTTPException(
                    status_code=400, detail="Нарушение целостности данных"
                ) from e
            await session.commit()
            return await self.get(table_id)

    async def get(self, id: uuid.UUID) -> ScheduleTableSchema:
        """Возвращает табличное расписание по идентификатору.

        Args:
            id: Уникальный идентификатор расписания.

        Returns:
            Расписание вместе со столбцами и уроками в виде схемы
            :class:`ScheduleTableSchema`.

        Raises:
            HTTPException: с кодом 404, если запись не найдена.
        """
        async with self.db.db_session() as session:
            query = select(self.model).where(self.model.id == id)
            result: Result = await session.execute(query)
            try:
                schedule_data = result.unique().scalar_one()
            except NoResultFound:
                raise HTTPException(
                    status_code=404, detail="Таблица расписания не найдена"
                ) from None
            return ScheduleTableSchema.model_validate(schedule_data)

    async def get_all(self) -> list[ScheduleTableSchema]:
        """Возвращает все табличные расписания.

        Результат сортируется по дню недели (порядок определяется
        перечислением :class:`DayOfWeek`).

        Returns:
            Список всех расписаний в виде схем :class:`ScheduleTableSchema`.
        """
        weekday_order = case(
            {day.name: index for index, day in enumerate(DayOfWeek, start=1)},
            value=self.model.day_of_week,
        )
        async with self.db.db_session() as session:
            query = select(self.model).order_by(weekday_order)
            result: Result = await session.execute(query)
            schedule_data = result.unique().scalars().all()
            return [ScheduleTableSchema.model_validate(item) for item in schedule_data]

    async def update(
        self, id: uuid.UUID, schedule: ScheduleTableUpdate
    ) -> ScheduleTableSchema:
        """Обновляет данные табличного расписания.

        Обновляет только скалярные поля расписания (без столбцов).

        Args:
            id: Уникальный идентификатор расписания.
            schedule: Поля, подлежащие обновлению.

        Returns:
            Обновлённое расписание в виде схемы :class:`ScheduleTableSchema`.

        Raises:
            HTTPException: с кодом 400, если не передано ни одного поля
                для обновления; с кодом 404, если запись не найдена.
        """
        async with self.db.db_session() as session:
            update_data = schedule.model_dump(exclude_none=True)
            if not update_data:
                raise HTTPException(status_code=400, detail="Нет данных для обновления")
            query = select(self.model).where(self.model.id == id)

            result: Result = await session.execute(query)

            table = result.unique().scalar_one_or_none()
            if not table:
                raise HTTPException(status_code=404, detail="Таблица не найдена")

            for key, value in update_data.items():
                if hasattr(table, key):
                    setattr(table, key, value)
            try:
                await session.commit()
            except IntegrityError as e:
                logger.warning("Integrity error при обновлении расписания: %s", e)
                logger.warning("Rollback")
                raise HTTPException(
                    status_code=400, detail="Нарушение целостности данных"
                ) from e
            return await self.get(id)

    async def delete(self, id: uuid.UUID) -> None:
        """Удаляет табличное расписание.

        Args:
            id: Уникальный идентификатор расписания.

        Raises:
            HTTPException: с кодом 404, если запись не найдена.
        """
        async with self.db.db_session() as session:
            query = delete(self.model).where(self.model.id == id)
            result: Result = await session.execute(query)
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Таблица не найдена")
            await session.commit()


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
