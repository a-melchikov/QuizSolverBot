from aiogram import html
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.logger_setup import get_logger
from app.repositories.users import UserRepository

logger = get_logger(__name__)


async def command_start_handler(message: Message) -> None:
    if not message.from_user:
        return
    logger.info(f"Received /start command from {message.from_user.full_name}")
    user_repository = UserRepository()
    await user_repository.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )
    await message.answer(
        f"Приветствую, {html.bold(message.from_user.full_name)}!\n\n"
        "Используйте /help для списка возможностей."
    )


def register_start_handler(dp):
    dp.message.register(command_start_handler, CommandStart())
