from aiogram import types, Dispatcher, html
from aiogram.filters import Command, CommandObject
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.database import async_session_maker
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

        response = f"Вопрос: {html.bold(question.text)}\n\n"

        if question.has_options:
            options = question.options
            if options:
                for idx, option in enumerate(options, start=1):
                    if option.is_correct:
                        response += f"{idx}. {html.bold(option.option_text)}\n"
                    else:
                        response += f"{idx}. {option.option_text}\n"
            else:
                response += "Варианты ответа не найдены."
        else:
            response += f"Ответ: {question.answer_text or 'Не указан'}"

        await message.answer(response, parse_mode="HTML")


def register_quiz_handlers(dp: Dispatcher) -> None:
    dp.message.register(list_questions_handler, Command(commands=["list_questions"]))
    dp.message.register(solve_question_handler, Command(commands=["solve_question"]))
