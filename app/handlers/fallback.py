from aiogram import types, Dispatcher
from app.logger_setup import get_logger
from app.handlers.quiz import help_handler

logger = get_logger(__name__)


async def fallback_handler(message: types.Message) -> None:
    logger.info(
        f"Неизвестная команда от пользователя {message.from_user.full_name}: {message.text}"
    )
    await help_handler(message)


def register_fallback_handler(dp: Dispatcher) -> None:
    dp.message.register(fallback_handler)
