import asyncio
import os
import sys

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from alembic.config import Config

from alembic import command
from app.api import create_app
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


async def start_web_server() -> None:
    app = create_app()
    config = uvicorn.Config(
        app=app,
        host=settings.WEBAPP_HOST,
        port=settings.WEBAPP_PORT,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)
    logger.info(
        f"Starting WebApp server on http://{settings.WEBAPP_HOST}:{settings.WEBAPP_PORT}"
    )
    await server.serve()


async def main() -> None:
    logger.info("Initializing the bot...")
    proxy = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
    session = AiohttpSession(proxy=proxy) if proxy else None
    bot = Bot(
        token=settings.TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    register_all_handlers(dp)
    logger.info("Starting bot polling and WebApp server...")
    await asyncio.gather(
        start_web_server(),
        dp.start_polling(bot),
    )


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
