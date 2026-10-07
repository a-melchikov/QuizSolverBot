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

    app = create_app(bot=bot, dp=dp)
    server_config = uvicorn.Config(
        app=app,
        host=settings.WEBAPP_HOST,
        port=settings.WEBAPP_PORT,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(server_config)

    webhook_url = settings.WEBHOOK_URL.strip().rstrip("/")
    if webhook_url:
        full_webhook_url = f"{webhook_url}{settings.WEBHOOK_PATH}"
        logger.info(f"Setting up Telegram Webhook: {full_webhook_url}")
        await bot.set_webhook(
            url=full_webhook_url,
            secret_token=settings.WEBHOOK_SECRET or None,
            drop_pending_updates=True,
            allowed_updates=dp.resolve_used_update_types(),
        )
        logger.info(
            f"Webhook registered. Running WebApp and Webhook server on http://{settings.WEBAPP_HOST}:{settings.WEBAPP_PORT}..."
        )
        try:
            await server.serve()
        finally:
            logger.info("Stopping bot... Deleting webhook.")
            try:
                await bot.delete_webhook()
            except Exception as e:
                logger.warning(f"Error deleting webhook on exit: {e}")
            await bot.session.close()
    else:
        logger.info("WEBHOOK_URL is not set. Running in Long Polling mode...")
        try:
            await bot.delete_webhook(drop_pending_updates=True)
        except Exception as e:
            logger.warning(f"Could not drop webhook before polling: {e}")

        logger.info(
            f"Starting bot polling and WebApp server on http://{settings.WEBAPP_HOST}:{settings.WEBAPP_PORT}..."
        )
        await asyncio.gather(
            server.serve(),
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
