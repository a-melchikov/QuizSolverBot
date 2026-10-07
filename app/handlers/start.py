from aiogram import Bot, html, types
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.config import settings
from app.logger_setup import get_logger
from app.repositories.users import UserRepository

logger = get_logger(__name__)


async def command_start_handler(message: Message, bot: Bot) -> None:
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

    reply_markup = None
    if settings.WEBAPP_URL:
        # Configure Chat Menu Button for Mini App
        try:
            await bot.set_chat_menu_button(
                chat_id=message.chat.id,
                menu_button=types.MenuButtonWebApp(
                    text="Quiz App",
                    web_app=types.WebAppInfo(url=settings.WEBAPP_URL),
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to set chat menu button: {e}")

        reply_markup = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="🚀 Открыть Quiz App",
                        web_app=types.WebAppInfo(url=settings.WEBAPP_URL),
                    )
                ]
            ]
        )

    await message.answer(
        f"Приветствую, {html.bold(message.from_user.full_name)}!\n\n"
        "Тренируйтесь и проходите тесты прямо в удобном приложении или через команды бота.\n"
        "Используйте /help для списка возможностей.",
        reply_markup=reply_markup,
    )


def register_start_handler(dp):
    dp.message.register(command_start_handler, CommandStart())
