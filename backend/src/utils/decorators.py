from collections.abc import Callable
from functools import wraps
from logging import getLogger

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, NoResultFound

logger = getLogger(__name__)


def handle_db_errors(func: Callable):
    """Декоратор для обработки ошибок БД."""

    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        try:
            return await func(self, *args, **kwargs)
        except IntegrityError as e:
            logger.warning("Ошибка целостности данных: %s", e)
            raise HTTPException(400, "Нарушение целостности данных") from e
        except NoResultFound:
            raise HTTPException(404, "Запись не найдена") from None
        except HTTPException as e:
            logger.warning("Ошибка HTTP: %s", e)
            raise HTTPException(e.status_code, e.detail) from e
        except Exception as e:
            logger.error("Неожиданная ошибка: %s", e)
            raise HTTPException(500, "Внутренняя ошибка сервера") from e

    return wrapper
