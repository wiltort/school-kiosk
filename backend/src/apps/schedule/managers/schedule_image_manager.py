import uuid
from logging import getLogger
from pathlib import Path

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
from src.utils.locking import maybe_lock
from src.utils.retry import with_retry_commit

logger = getLogger(__name__)


class ScheduleImageManager:
    @staticmethod
    def _same_content(meta_a: dict | None, meta_b: dict | None) -> bool:
        """Сравнивает метаданные файлов по содержимому (хеш и размер).

        ``mtime`` сознательно не участвует в сравнении: после синхронизации
        mtime статической копии всегда новее, чем у локального файла-источника,
        поэтому полное сравнение словарей приводило бы к бесконечной
        пересинхронизации на каждом цикле.
        """
        if not meta_a or not meta_b:
            return False
        return meta_a.get("file_hash") == meta_b.get("file_hash") and meta_a.get(
            "file_size"
        ) == meta_b.get("file_size")

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
        lock = self.storage.lock(lock_key) if is_local else None

        async with maybe_lock(lock, use_lock=is_local):
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
        self,
        id: uuid.UUID,
        schedule: ScheduleImageUpdate,
        is_local: bool = False,
        filename: str | None = None,
        file_data: bytes | None = None,
    ) -> ScheduleImageGet:
        """Обновляет расписание-изображение по идентификатору.

        Args:
            id: Уникальный идентификатор расписания.
            schedule: Поля, подлежащие обновлению (обновляются
                только переданные значения).
            is_local: При ``True`` выполняет синхронизацию с локальным
                каталогом изображений: если файл-источник изменился,
                перезаписывает статическую копию и обновляет метаданные
                изображения. Позволяет вызывать метод с пустым
                ``schedule`` (только синхронизация файла).

        Returns:
            Обновлённое расписание в виде схемы :class:`ScheduleImageGet`.

        Raises:
            HTTPException: с кодом 400, если не передано ни одного поля
                для обновления (и ``is_local=False``) или нарушена
                целостность данных;
                с кодом 404, если запись не найдена.
        """
        async with self.db.db_session() as session:
            data = schedule.model_dump(exclude_unset=True)
            if not data and not is_local and not (filename and file_data):
                raise HTTPException(status_code=400, detail="Нет данных для обновления")
            schedule_image = await self.image_repo.get(session, id)
            if not schedule_image:
                raise HTTPException(status_code=404, detail="Запись не найдена")
            image = data.get("image")
            lock_key = None
            locking = False
            if image:
                if is_local or schedule_image.is_local:
                    raise HTTPException(
                        400,
                        detail="Неверный запрос: поле 'image' не для локального расписания",
                    )
            elif is_local:
                if not schedule_image.is_local:
                    raise HTTPException(400, detail="Запись не является локальной")
                if filename:
                    raise HTTPException(
                        400, detail="Невозможно заменить файл у локального расписания"
                    )
                locking = True
                lock_key = schedule_image.image
            elif filename and file_data and (is_local or schedule_image.is_local):
                raise HTTPException(
                    400,
                    detail="Неверный запрос: передан файл и в запросе и локально",
                )
            lock = self.storage.lock(lock_key) if lock_key else None

            async with maybe_lock(lock, use_lock=locking):
                old_image = None
                new_image = None
                try:
                    # Перечитывание под локом. Обычный session.get() вернул бы
                    # объект из identity map текущей транзакции без запроса
                    # к БД, поэтому сначала завершаем read-транзакцию (записей
                    # ещё нет), а затем выполняем реальный SELECT с
                    # populate_existing — в обход кеша сессии.
                    await session.rollback()
                    schedule_image = await self.image_repo.get(
                        session, id, populate_existing=True
                    )
                    if not schedule_image:
                        raise HTTPException(404, detail="Запись не найдена")
                    # Состояние записи могло измениться между первым чтением
                    # и взятием лока — повторяем проверки инвариантов ветки.
                    if image and schedule_image.is_local:
                        raise HTTPException(
                            400,
                            detail="Неверный запрос: поле 'image' не для локального расписания",
                        )
                    if file_data and filename and schedule_image.is_local:
                        raise HTTPException(
                            400,
                            detail="Неверный запрос: передан файл и в запросе и локально",
                        )
                    if is_local and not schedule_image.is_local:
                        raise HTTPException(400, detail="Запись не является локальной")
                    if filename and schedule_image.is_local:
                        raise HTTPException(
                            400, detail="Невозможно заменить файл локального расписания"
                        )
                    old_image = schedule_image.image
                    new_image = None
                    meta = None
                    if image:
                        # Просто замена на существующий файл (не для локального расписания)
                        new_image = image
                        meta = self.storage.read_file_metadata(new_image)
                        if meta is None:
                            raise HTTPException(400, detail="Файл не найден")
                    elif file_data and filename:
                        # подгрузка нового файла (не для локального расписания)
                        new_image = self.storage.save(file_data, filename)
                        if new_image is None:
                            raise HTTPException(400, detail="Ошибка сохранения файла")
                        meta = self.storage.read_file_metadata(new_image)
                        if meta is None:
                            raise HTTPException(400, detail="Файл не найден")
                    elif is_local:
                        local_filename = Path(old_image).name
                        meta_local = self.storage.read_file_metadata(
                            local_filename, is_local=True
                        )
                        if meta_local is None:
                            raise HTTPException(
                                status_code=400,
                                detail="Локальный файл-источник не найден",
                            )
                        meta_static = self.storage.read_file_metadata(old_image)
                        if not self._same_content(meta_local, meta_static):
                            image_data = self.storage.read_file(
                                local_filename, is_local=True
                            )
                            if image_data is None:
                                raise HTTPException(
                                    status_code=400, detail="Ошибка чтения файла"
                                )
                            subdir, _, fname = old_image.rpartition("/")
                            new_image = self.storage.save(
                                image_data, fname, subdir, is_local=True
                            )
                            if new_image != old_image:
                                raise HTTPException(
                                    status_code=400,
                                    detail="Ошибка сохранения файла",
                                )
                            # Метаданные читаем из свежесохранённой статической
                            # копии — метаданные старой копии уже неактуальны.
                            meta = self.storage.read_file_metadata(new_image)
                        else:
                            meta = meta_static
                    if new_image is not None:
                        data["image"] = new_image
                    if meta:
                        data.update(meta)

                    updated_schedule = await self.image_repo.update(
                        session, schedule_image, data
                    )
                    await with_retry_commit(session)
                    return ScheduleImageGet.model_validate(updated_schedule)
                except Exception:
                    # Откат файловых операций: при перезаписи файла поверх себя
                    # восстанавливаем предыдущую версию из backup; при создании
                    # нового файла (переименование) удаляем его и не трогаем
                    # прежний. Если ни один файл не менялся — ничего не делаем.
                    if is_local and old_image and new_image and old_image == new_image:
                        self.storage.restore_file(old_image)
                    raise

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
