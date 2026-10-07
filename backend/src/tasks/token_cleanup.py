import logging

from src.apps.admin.repositories import AdminTokenRepository
from src.core.database import get_db_dependency
from src.utils.retry import with_retry_commit

logger = logging.getLogger(__name__)


async def run_expired_tokens_cleanup() -> None:
    """Периодическая чистка просроченных токенов."""
    logger.info("Starting periodic expired tokens cleanup")
    db = get_db_dependency()
    repo = AdminTokenRepository()

    try:
        async with db.db_session() as session:
            count = await repo.delete_expired(session)
            await with_retry_commit(session)
        if count:
            logger.info("Удалено %d просроченных токенов", count)
    except Exception:
        logger.exception("Ошибка при очистке токенов")
