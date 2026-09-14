import uuid
from logging import getLogger

from fastapi import Depends, HTTPException

from src.apps.schedule.repositories import ScheduleImageRepository
from src.apps.schedule.schemas import (
    ScheduleImageCreate,
    ScheduleImageGet,
    ScheduleImageUpdate,
)
from src.core.database import DBDependency, get_db_dependency
from src.core.storage import ImageStorage
from src.utils.decorators import handle_db_errors
from src.utils.retry import with_retry_commit

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
        storage: ImageStorage = Depends(),
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
        self.storage = storage

    async def _create(
        self,
        *,
        data: bytes,
        filename: str,
        subdir: str,
        payload: dict,
        is_local: bool,
    ) -> ScheduleImageGet:
        lock_key = f"{subdir}/{filename}".lstrip("/")
        lock = self.storage.lock(lock_key)

        async with lock:
            stored_path = self.storage.save(
                data, filename, subdir=subdir, is_local=is_local
            )
            try:
                meta = self.storage.read_file_metadata(stored_path)
                if meta is None:
                    raise HTTPException(500, "Не удалось прочитать файл")
                payload = {**payload, "image": stored_path, **meta}

                async with self.db.db_session() as session:
                    if is_local:
                        existing = await self.image_repo.get_local_by_name(
                            session, payload["name"]
                        )
                        if existing:
                            payload = {"image": stored_path, **meta}
                            obj = await self.image_repo.update(
                                session, existing, payload
                            )
                            await with_retry_commit(session)
                            return ScheduleImageGet.model_validate(obj)
                    obj = await self.image_repo.create(session, payload)
                    await with_retry_commit(session)
                    return ScheduleImageGet.model_validate(obj)
            except Exception:
                if is_local:
                    self.storage.restore_file(stored_path)
                else:
                    self.storage.delete(stored_path)
                raise

    @handle_db_errors
    async def create(
        self, schedule: ScheduleImageCreate, data: bytes, filename: str
    ) -> ScheduleImageGet:
        """Создаёт новое расписание-изображение.

        Args:
            schedule: Данные для создания расписания.
            data: Изображение.
            filename: имя файла изображения.

        Returns:
            Созданное расписание в виде схемы :class:`ScheduleImageGet`.

        Raises:
            HTTPException: с кодом 400 при нарушении ограничений
                целостности базы данных (например, дубликат).
        """
        payload = schedule.model_dump(exclude_none=True)
        payload["is_local"] = False
        return await self._create(
            data=data, filename=filename, subdir="", payload=payload, is_local=False
        )

    @handle_db_errors
    async def create_local(
        self,
        filename: str,
        schedule: ScheduleImageCreate,
    ) -> ScheduleImageGet:
        """Создает новое локальное расписание-изображение.

        Args:
            filename: Имя файла расписания.
            schedule: Данные для создания расписания.

        Returns:
            Созданное расписание в виде схемы :class: `ScheduleImageGet`.

        Raises:
            HTTPException: с кодом 400 при нарушении ограничений целостности
                базы данных.
            HTTPException: с кодом 500 при проблемах с чтением файла.
        """
        data = self.storage.read_file(path=filename, is_local=True)
        if data is None:
            raise HTTPException(500, detail=f"Файл расписания {filename} не найден")
        payload = schedule.model_dump(exclude_none=True)
        payload["is_local"] = True
        return await self._create(
            data=data,
            filename=filename,
            subdir="local",
            payload=payload,
            is_local=True,
        )

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
            images = await self.image_repo.list(session)
            return [ScheduleImageGet.model_validate(item) for item in images]

    @handle_db_errors
    async def update(
        self, id: uuid.UUID, schedule: ScheduleImageUpdate, is_local: bool = False
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
            if not data and not is_local:
                raise HTTPException(status_code=400, detail="Нет данных для обновления")
            schedule_image = await self.image_repo.get(session, id)
            if not schedule_image:
                raise HTTPException(status_code=404, detail="Запись не найдена")
            image = data.get("image")
            if image:
                meta = self.storage.read_file_metadata(image)
                data = {**data, **meta}
            if is_local:
                data["is_local"] = True
                if not image:
                    meta = self.storage.read_file_metadata(
                        schedule_image.image, is_local=True
                    )
                    data = {**data, **meta}
            updated_schedule = await self.image_repo.update(
                session, schedule_image, data
            )
            await with_retry_commit(session)
            return ScheduleImageGet.model_validate(updated_schedule)

    async def delete(self, id: uuid.UUID) -> None:
        """Удаляет расписание-изображение по идентификатору.

        Args:
            id: Уникальный идентификатор расписания.

        Raises:
            HTTPException: с кодом 404, если запись не найдена.
        """
        async with self.db.db_session() as session:
            schedule = await self.image_repo.get(session, id)
            if not schedule:
                raise HTTPException(status_code=404, detail="Расписание не найдено")
            await self.image_repo.delete(session, schedule)
            await with_retry_commit(session)
