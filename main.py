import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import settings
from app.logger_setup import get_logger
from app.handlers import register_all_handlers

logger = get_logger(__name__)
dp = Dispatcher()


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
    logger.info("Starting main function...")
    asyncio.run(main())
