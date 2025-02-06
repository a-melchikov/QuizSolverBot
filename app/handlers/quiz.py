from html import escape
from aiogram import types, Dispatcher, html
from aiogram.filters import Command, CommandObject
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.database import async_session_maker
from app.handlers.buttons import get_help_keyboard
from app.models import Question
from app.logger_setup import get_logger

logger = get_logger(__name__)


async def list_questions_handler(message: types.Message) -> None:
    async with async_session_maker() as session:
        result = await session.execute(select(Question))
        questions = result.scalars().all()

    if not questions:
        await message.answer("Нет доступных вопросов.")
        return

    response_lines = []
    for q in questions:
        truncated_text = q.text if len(q.text) < 50 else q.text[:50] + "..."
        response_lines.append(f"{q.id}. {truncated_text}")
    response = "\n".join(response_lines)
    await message.answer(f"Список вопросов:\n{html.pre(response)}", parse_mode="HTML")


async def delete_question_handler(
    message: types.Message, command: CommandObject
) -> None:
    if not command.args:
        await message.answer("Укажите id вопроса. Например: /delete_question 1")
        return

    try:
        question_id = int(command.args.split()[0])
    except ValueError:
        await message.answer("Id вопроса должен быть числом.")
        return

    async with async_session_maker() as session:
        try:
            query = delete(Question).where(Question.id == question_id)
            result = await session.execute(query)
            await session.commit()

            if result.rowcount == 0:  # Если в запросе ничего не удалилось
                await message.answer(f"Вопрос с id {question_id} не найден.")
            else:
                await message.answer(f"Вопрос с id {question_id} успешно удалён.")
        except IntegrityError as e:
            await session.rollback()
            logger.error(f"Ошибка при удалении вопроса: {e}")
            await message.answer(
                "Произошла ошибка при удалении вопроса. Попробуйте позже."
            )


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

        response = f"Вопрос: {escape(question.text)}\n\n"

        if question.has_options:
            options = question.options
            if options:
                for idx, option in enumerate(options, start=1):
                    if option.is_correct:
                        response += f"{idx}. <b>{escape(option.option_text)}</b>\n"
                    else:
                        response += f"{idx}. {escape(option.option_text)}\n"
            else:
                response += "Варианты ответа не найдены."
        else:
            response += f"Ответ: {escape(question.answer_text or 'Не указан')}"

        await message.answer(response, parse_mode="HTML")


async def help_handler(message: types.Message) -> None:
    keyboard = get_help_keyboard()

    response = "Доступные команды:"
    await message.answer(response, reply_markup=keyboard)


def register_quiz_handlers(dp: Dispatcher) -> None:
    dp.message.register(list_questions_handler, Command(commands=["list_questions"]))
    dp.message.register(solve_question_handler, Command(commands=["solve_question"]))
    dp.message.register(delete_question_handler, Command(commands=["delete_question"]))
    dp.message.register(help_handler, Command(commands=["help"]))
