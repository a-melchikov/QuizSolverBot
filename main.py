import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from alembic.config import Config

from alembic import command
from app.config import BASE_DIR, settings
from app.handlers import register_all_handlers
from app.logger_setup import get_logger

logger = get_logger(__name__)
dp = Dispatcher()


def run_migrations() -> None:
    logger.info("Applying database migrations...")
    alembic_cfg = Config(BASE_DIR / "alembic.ini")
    command.upgrade(alembic_cfg, "head")
    logger.info("Database migrations applied successfully.")


async def main() -> None:
    logger.info("Initializing the bot...")
    bot = Bot(
        token=settings.TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    register_all_handlers(dp)
    logger.info("Starting bot polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    logger.info("Starting main process...")
    if not settings.TOKEN:
        logger.error("BOT TOKEN is not set! Please configure TOKEN in .env.")
        sys.exit(1)

    try:
        run_migrations()
    except Exception as e:
        logger.error(f"Migration error: {e}")
        sys.exit(1)

    asyncio.run(main())
