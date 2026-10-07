from html import escape as html_escape

from aiogram import Dispatcher, types
from aiogram.filters import Command, CommandObject
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import async_session_maker
from app.handlers.buttons import get_help_keyboard
from app.logger_setup import get_logger
from app.models import Question
from app.repositories.questions import QuestionRepository

logger = get_logger(__name__)


async def list_questions_handler(message: types.Message, page: int = 0) -> None:
    QUESTIONS_PER_PAGE = 20
    question_repository = QuestionRepository()
    total_count = await question_repository.get_questions_count()

    if total_count == 0:
        await message.answer("📚 <b>Нет доступных вопросов.</b>", parse_mode="HTML")
        return

    total_pages = (total_count + QUESTIONS_PER_PAGE - 1) // QUESTIONS_PER_PAGE

    if page < 0 or page >= total_pages:
        await message.answer("❌ <b>Некорректная страница.</b>", parse_mode="HTML")
        return

    offset = page * QUESTIONS_PER_PAGE
    page_questions = await question_repository.get_questions_paginated(
        limit=QUESTIONS_PER_PAGE, offset=offset
    )

    response_lines = ["📋 <b>Список вопросов:</b>\n"]
    for q in page_questions:
        truncated_text = q.text if len(q.text) < 50 else q.text[:47] + "..."
        response_lines.append(
            f"└ <code>{q.id:03d}</code> • <i>{html_escape(truncated_text)}</i>"
        )

    footer = f"\n📌 Страница {page + 1} из {total_pages}"
    response = "\n".join(response_lines) + footer

    keyboard_buttons = []
    if page > 0:
        keyboard_buttons.append(
            InlineKeyboardButton(
                text="◀️ Назад", callback_data=f"questions_page:{page - 1}"
            )
        )
    if page < total_pages - 1:
        keyboard_buttons.append(
            InlineKeyboardButton(
                text="Вперед ▶️", callback_data=f"questions_page:{page + 1}"
            )
        )

    keyboard = (
        InlineKeyboardMarkup(inline_keyboard=[keyboard_buttons])
        if keyboard_buttons
        else None
    )
    await message.answer(response, reply_markup=keyboard, parse_mode="HTML")


async def questions_pagination(callback_query: types.CallbackQuery):
    try:
        page = int(callback_query.data.split(":")[1])
        await callback_query.message.delete()
        await list_questions_handler(callback_query.message, page)
    except Exception as e:
        logger.error(f"Ошибка пагинации: {e}")
    finally:
        await callback_query.answer()


async def delete_question_handler(
    message: types.Message, command: CommandObject
) -> None:
    if settings.ADMINS and message.from_user.id not in settings.ADMINS:
        await message.answer("❌ У вас нет прав для удаления вопросов.")
        return

    if not command.args:
        await message.answer("Укажите id вопроса. Например: /delete_question 1")
        return

    try:
        question_id = int(command.args.split()[0])
    except ValueError:
        await message.answer("Id вопроса должен быть числом.")
        return

    question_repository = QuestionRepository()
    try:
        if await question_repository.delete_question(question_id):
            await message.answer(f"✅ Вопрос с id {question_id} успешно удалён.")
        else:
            await message.answer(f"Вопрос с id {question_id} не найден.")
    except IntegrityError as e:
        logger.error(f"Ошибка при удалении вопроса: {e}")
        await message.answer("Произошла ошибка при удалении вопроса. Попробуйте позже.")


async def solve_question_handler(
    message: types.Message, command: CommandObject
) -> None:
    if not command.args:
        await message.answer("Укажите id вопроса. Например: /solve_question 1")
        return

    try:
        question_id = int(command.args.split()[0])
    except ValueError:
        await message.answer("Id вопроса должен быть числом.")
        return

    async with async_session_maker() as session:
        query = (
            select(Question)
            .options(selectinload(Question.options))
            .where(Question.id == question_id)
        )
        result = await session.execute(query)
        question = result.scalar()
        if not question:
            await message.answer(f"Вопрос с id {question_id} не найден.")
            return

        response = f"<b>Вопрос:</b> {html_escape(question.text)}\n\n"

        if question.has_options:
            options = question.options
            if options:
                for idx, option in enumerate(options, start=1):
                    if option.is_correct:
                        response += (
                            f"{idx}. <b>{html_escape(option.option_text)}</b> ✅\n"
                        )
                    else:
                        response += f"{idx}. {html_escape(option.option_text)}\n"
            else:
                response += "Варианты ответа не найдены."
        else:
            response += (
                f"<b>Ответ:</b> {html_escape(question.answer_text or 'Не указан')}"
            )

        await message.answer(response, parse_mode="HTML")


async def help_handler(message: types.Message) -> None:
    keyboard = get_help_keyboard()
    response = (
        "📖 <b>Справочник по боту «ОП тесты»</b>\n\n"
        "📱 <b>Приложение Web App (Рекомендуется):</b>\n"
        "Нажмите кнопку <b>«🚀 Открыть ОП тесты»</b> или кнопку меню слева внизу — для быстрого прохождения с разбором ошибок и каталогом.\n\n"
        "⌨️ <b>Команды в чате:</b>\n"
        "• /start — Главное меню\n"
        "• /test (или /start_test) — Начать тестирование в чате\n"
        "• /question — Найти и решить вопрос по номеру\n"
        "• /solve_question <code>&lt;id&gt;</code> — Показать правильный ответ на вопрос\n"
        "• /list_questions — Каталог вопросов базы данных\n"
        "• /history — История и процент ваших попыток\n"
        "• /help — Это справочное сообщение"
    )
    await message.answer(response, reply_markup=keyboard, parse_mode="HTML")


def register_quiz_handlers(dp: Dispatcher) -> None:
    dp.message.register(list_questions_handler, Command(commands=["list_questions"]))
    dp.message.register(solve_question_handler, Command(commands=["solve_question"]))
    dp.message.register(delete_question_handler, Command(commands=["delete_question"]))
    dp.message.register(help_handler, Command(commands=["help"]))
    dp.callback_query.register(
        questions_pagination, lambda c: c.data and c.data.startswith("questions_page:")
    )
