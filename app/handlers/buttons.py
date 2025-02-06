from aiogram import types, Dispatcher
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext


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

        elif callback_data.action == "history":
            from app.handlers.quiz_history import view_test_history

            await view_test_history(callback_query.message)

        else:
            await callback_query.message.answer("Неизвестное действие.")

    except Exception as e:
        await callback_query.message.answer(f"Произошла ошибка: {str(e)}")

    await callback_query.answer()


def get_help_keyboard() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Помощь",
                    callback_data=ButtonCallbackData(action="help").pack(),
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Список вопросов",
                    callback_data=ButtonCallbackData(action="list_questions").pack(),
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Решить один вопрос",
                    callback_data=ButtonCallbackData(action="start_question").pack(),
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Решить тест",
                    callback_data=ButtonCallbackData(action="start_test").pack(),
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="История",
                    callback_data=ButtonCallbackData(action="history").pack(),
                )
            ],
        ]
    )


def register_button_handlers(dp: Dispatcher):
    dp.callback_query.register(process_button_click, ButtonCallbackData.filter())
