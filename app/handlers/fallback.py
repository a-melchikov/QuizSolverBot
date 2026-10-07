from aiogram import Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.handlers.buttons import ButtonCallbackData
from app.logger_setup import get_logger

logger = get_logger(__name__)


async def fallback_handler(message: types.Message) -> None:
    if message.from_user:
        logger.info(
            f"Нераспознанное сообщение от {message.from_user.full_name}: {message.text}"
        )

    text = (
        "🤔 <b>Команда не распознана.</b>\n\n"
        "Воспользуйтесь кнопками ниже или отправьте /help для просмотра списка команд."
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎯 Начать тест",
                    callback_data=ButtonCallbackData(action="start_test").pack(),
                ),
                InlineKeyboardButton(
                    text="🏠 Главное меню",
                    callback_data=ButtonCallbackData(action="main_menu").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="ℹ️ Справка по командам",
                    callback_data=ButtonCallbackData(action="help").pack(),
                ),
            ],
        ]
    )
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


def register_fallback_handler(dp: Dispatcher) -> None:
    dp.message.register(fallback_handler)
