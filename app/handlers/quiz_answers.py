from aiogram import Dispatcher, Bot
from aiogram.types import Message, PollAnswer
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from app.database import async_session_maker
from app.models import Question, Option


class AnswerState(StatesGroup):
    waiting_for_question_id = State()
    answering = State()


async def start_question(message: Message, state: FSMContext):
    await message.answer("Введите ID вопроса, чтобы начать.")
    await state.set_state(AnswerState.waiting_for_question_id)


async def process_question_id(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите число!")
        return

    question_id = int(message.text)

    await answer_question(message, state, question_id)


async def answer_question(message: Message, state: FSMContext, question_id: int):
    async with async_session_maker() as session:
        question = await session.get(Question, question_id)
        if not question:
            await message.answer("Вопрос с указанным ID не найден.")
            return

        await state.update_data(question_id=question_id)

        if question.has_options:
            options = await session.execute(
                select(Option).where(Option.question_id == question.id)
            )
            options = options.scalars().all()

            option_texts = [opt.option_text for opt in options]
            poll = await message.answer_poll(
                question=question.text,
                options=option_texts,
                type="regular",
                allows_multiple_answers=True,
                is_anonymous=False,
            )
            await state.update_data(current_poll_id=poll.poll.id)
        else:
            await message.answer(question.text)

        await state.set_state(AnswerState.answering)


async def process_poll_answer(poll_answer: PollAnswer, state: FSMContext, bot: Bot):
    data = await state.get_data()

    if poll_answer.poll_id != data.get("current_poll_id"):
        return

    async with async_session_maker() as session:
        question = await session.get(Question, data["question_id"])
        options = await session.execute(
            select(Option).where(Option.question_id == question.id)
        )
        options = options.scalars().all()

        option_mapping = {index: option.id for index, option in enumerate(options)}
        selected_option_ids = [
            option_mapping[index] for index in poll_answer.option_ids
        ]

        correct_options = [option for option in options if option.is_correct]
        correct_option_ids = [option.id for option in correct_options]
        is_correct = set(selected_option_ids) == set(correct_option_ids)

        result_message = (
            "✅ Верно!"
            if is_correct
            else f"❌ Неверно!\nПравильный ответ:\n{chr(10).join(opt.option_text for opt in correct_options)}"
        )
        await bot.send_message(poll_answer.user.id, result_message, parse_mode="HTML")
        await state.clear()


async def process_text_answer(message: Message, state: FSMContext):
    data = await state.get_data()

    async with async_session_maker() as session:
        question = await session.get(Question, data["question_id"])
        is_correct = message.text.lower() == question.answer_text.lower()

        result_message = (
            "✅ Верно!"
            if is_correct
            else f"❌ Неверно!\nПравильный ответ: {question.answer_text}"
        )
        await message.answer(result_message, parse_mode="HTML")
        await state.clear()


def register_answer_handlers(dp: Dispatcher):
    dp.message.register(start_question, Command("start_question"))
    dp.message.register(process_question_id, AnswerState.waiting_for_question_id)
    dp.message.register(process_text_answer, AnswerState.answering)
    dp.poll_answer.register(process_poll_answer)
