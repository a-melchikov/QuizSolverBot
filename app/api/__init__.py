from pathlib import Path
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import settings
from app.logger_setup import get_logger

logger = get_logger(__name__)
STATIC_DIR = Path(__file__).parent.parent / "webapp" / "static"


def create_app(bot: Bot | None = None, dp: Dispatcher | None = None) -> FastAPI:
    app = FastAPI(title="QuizSolverBot Mini App", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    if bot and dp:

        @app.post(settings.WEBHOOK_PATH)
        async def telegram_webhook(
            request: Request,
            x_telegram_bot_api_secret_token: str | None = Header(None),
        ) -> dict[str, Any]:
            if (
                settings.WEBHOOK_SECRET
                and x_telegram_bot_api_secret_token != settings.WEBHOOK_SECRET
            ):
                logger.warning("Webhook request with invalid secret token rejected")
                raise HTTPException(status_code=403, detail="Invalid secret token")
            try:
                data = await request.json()
                update = Update.model_validate(data, context={"bot": bot})
                await dp.feed_update(bot=bot, update=update)
            except Exception as e:
                logger.error(
                    f"Error handling Telegram webhook update: {e}", exc_info=True
                )
            return {"ok": True}

    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

    return app
