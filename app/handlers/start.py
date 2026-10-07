from aiogram import Bot, html, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.config import settings
from app.handlers.buttons import ButtonCallbackData
from app.logger_setup import get_logger
from app.repositories.users import UserRepository

logger = get_logger(__name__)


def get_start_keyboard() -> InlineKeyboardMarkup:
    keyboard = []
    if settings.WEBAPP_URL:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="🚀 Открыть ОП тесты",
                    web_app=types.WebAppInfo(url=settings.WEBAPP_URL),
                )
            ]
        )

    keyboard.extend(
        [
            [
                InlineKeyboardButton(
                    text="🎯 Начать тест в чате",
                    callback_data=ButtonCallbackData(action="start_test").pack(),
                ),
                InlineKeyboardButton(
                    text="🔍 Найти вопрос",
                    callback_data=ButtonCallbackData(action="start_question").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📚 Список вопросов",
                    callback_data=ButtonCallbackData(action="list_questions").pack(),
                ),
                InlineKeyboardButton(
                    text="📊 Моя история",
                    callback_data=ButtonCallbackData(action="history").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="ℹ️ Справка и команды",
                    callback_data=ButtonCallbackData(action="help").pack(),
                ),
            ],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


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

    if settings.WEBAPP_URL:
        try:
            await bot.set_chat_menu_button(
                chat_id=message.chat.id,
                menu_button=types.MenuButtonWebApp(
                    text="ОП тесты",
                    web_app=types.WebAppInfo(url=settings.WEBAPP_URL),
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to set chat menu button: {e}")

    text = (
        f"👋 <b>Приветствую, {html.bold(message.from_user.full_name)}!</b>\n\n"
        "Бот для подготовки и тренировки по <b>огневой подготовке (ОП)</b>.\n\n"
        "📱 <b>Основной способ (рекомендуется):</b>\n"
        "Нажмите кнопку <b>«🚀 Открыть ОП тесты»</b> — откроется полноценное приложение с разбором ошибок, каталогом и статистикой.\n\n"
        "💬 <b>Или тренируйтесь прямо здесь в чате:</b>\n"
        "Выберите действие на клавиатуре ниже:"
    )

    await message.answer(
        text,
        reply_markup=get_start_keyboard(),
        parse_mode="HTML",
    )


def register_start_handler(dp):
    dp.message.register(command_start_handler, CommandStart())
