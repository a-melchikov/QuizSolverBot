from aiogram import Dispatcher, types
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton

from app.config import settings


class ButtonCallbackData(CallbackData, prefix="menu"):
    action: str


async def process_button_click(
    callback_query: types.CallbackQuery,
    callback_data: ButtonCallbackData,
    state: FSMContext,
):
    try:
        if callback_data.action == "help":
            from app.handlers.quiz import help_handler

            await help_handler(callback_query.message)

        elif callback_data.action == "list_questions":
            from app.handlers.quiz import list_questions_handler

            await list_questions_handler(callback_query.message)

        elif callback_data.action == "start_question":
            from app.handlers.quiz_answers import start_question

            await start_question(callback_query.message, state)

        elif callback_data.action == "start_test":
            from app.handlers.quiz_test import start_test

            await start_test(callback_query.message, state)

        elif callback_data.action == "errors":
            from app.handlers.quiz_test import start_errors_test

            await start_errors_test(callback_query, state)

        elif callback_data.action == "bookmarks":
            from app.handlers.quiz_test import start_bookmarks_test

            await start_bookmarks_test(callback_query, state)

        elif callback_data.action == "history":
            from app.handlers.quiz_history import view_test_history

            await view_test_history(callback_query.message)

        elif callback_data.action == "main_menu":
            from app.handlers.start import get_start_keyboard

            await callback_query.message.answer(
                "🏠 <b>Главное меню «ОП тесты»</b>\n\n"
                "Выберите интересующий раздел:",
                reply_markup=get_start_keyboard(),
                parse_mode="HTML",
            )

        else:
            await callback_query.message.answer("Неизвестное действие.")

    except Exception as e:
        await callback_query.message.answer(f"Произошла ошибка: {str(e)}")

    await callback_query.answer()


def get_help_keyboard() -> types.InlineKeyboardMarkup:
    keyboard = []

    if settings.WEBAPP_URL:
        keyboard.append(
            [
                types.InlineKeyboardButton(
                    text="🚀 Открыть ОП тесты",
                    web_app=types.WebAppInfo(url=settings.WEBAPP_URL),
                )
            ]
        )

    keyboard.extend(
        [
            [
                types.InlineKeyboardButton(
                    text="🎯 Начать тест",
                    callback_data=ButtonCallbackData(action="start_test").pack(),
                ),
                InlineKeyboardButton(
                    text="❌ Ошибки",
                    callback_data=ButtonCallbackData(action="errors").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⭐️ Избранное",
                    callback_data=ButtonCallbackData(action="bookmarks").pack(),
                ),
                InlineKeyboardButton(
                    text="🔍 Найти вопрос",
                    callback_data=ButtonCallbackData(action="start_question").pack(),
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text="📚 Список вопросов",
                    callback_data=ButtonCallbackData(action="list_questions").pack(),
                ),
                InlineKeyboardButton(
                    text="📊 Моя история",
                    callback_data=ButtonCallbackData(action="history").pack(),
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text="🏠 Главное меню",
                    callback_data=ButtonCallbackData(action="main_menu").pack(),
                ),
            ],
        ]
    )

    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)


def register_button_handlers(dp: Dispatcher):
    dp.callback_query.register(process_button_click, ButtonCallbackData.filter())
