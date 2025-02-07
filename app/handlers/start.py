from aiogram import html
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.errors import UserNotFoundException
from app.logger_setup import get_logger
from app.repositories.users import UserRepository
from app.schemas.users import UserCreate

logger = get_logger(__name__)


async def command_start_handler(message: Message) -> None:
    logger.info(f"Received /start command from {message.from_user.full_name}")
    user_repository = UserRepository()
    try:
        user = await user_repository.get_user_by_telegram_id(message.from_user.id)
        logger.info(f"User {message.from_user.full_name} already exists.")
        await message.answer(
            f"Рад снова тебя здесь видеть, {html.bold(message.from_user.full_name)}!"
        )
    except UserNotFoundException:
        user_schema = UserCreate(
            telegram_id=message.from_user.id,
            username=message.from_user.username or "",
            first_name=message.from_user.first_name or "",
            last_name=message.from_user.last_name or "",
        )
        logger.info(f"Creating new user {user_schema}")
        await user_repository.create_user(user_schema)
        await message.answer(f"Приветствую, {html.bold(message.from_user.full_name)}!")


def register_start_handler(dp):
    dp.message.register(command_start_handler, CommandStart())
