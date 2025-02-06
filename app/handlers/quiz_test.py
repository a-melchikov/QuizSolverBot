from datetime import datetime
from aiogram import Dispatcher, Bot, F
from aiogram.types import (
    Message,
    PollAnswer,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func
from app.database import async_session_maker
from app.models import Question, TestAttempt, AttemptAnswer, Option


class TestStates(StatesGroup):
    waiting_for_questions_count = State()
    answering_questions = State()


async def start_test(message: Message, state: FSMContext):
    async with async_session_maker() as session:
        total_questions = await session.execute(select(func.count(Question.id)))
        total_questions = total_questions.scalar()

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Завершить тест")]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )
    await message.answer(
        f"Сколько вопросов вы хотите решить? (от 1 до {total_questions})",
        reply_markup=kb,
    )
    await state.set_state(TestStates.waiting_for_questions_count)


async def process_questions_count(message: Message, state: FSMContext):
    if message.text == "Завершить тест":
        await finish_test(message, state)
        return

    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите число!")
        return

    questions_count = int(message.text)
    async with async_session_maker() as session:
        questions = await session.execute(
            select(Question).order_by(func.random()).limit(questions_count)
        )
        questions = questions.scalars().all()

        test_attempt = TestAttempt(
            user_id=message.from_user.id, total_questions=len(questions)
        )
        session.add(test_attempt)
        await session.commit()

        await state.update_data(
            current_question=0,
            questions=[q.id for q in questions],
            test_attempt_id=test_attempt.id,
            start_time=datetime.now(),
        )

    await show_next_question(message, state)
    await state.set_state(TestStates.answering_questions)


async def show_next_question(message: Message, state: FSMContext):
    data = await state.get_data()
    current_question = data["current_question"]
    questions = data["questions"]

    if current_question >= len(questions):
        await finish_test(message, state)
        return

    async with async_session_maker() as session:
        question = await session.get(Question, questions[current_question])

        if question.has_options:
            options = await session.execute(
                select(Option).where(Option.question_id == question.id)
            )
            options = options.scalars().all()

            if len(options) < 2:
                await message.answer(
                    f"Ошибка: Вопрос {current_question + 1} не имеет достаточного количества вариантов ответа."
                )
                data["current_question"] += 1
                await state.update_data(data)
                await show_next_question(message, state)
                return

            option_texts = [opt.option_text for opt in options]

            poll = await message.answer_poll(
                question=f"{current_question + 1}. {question.text}",
                options=option_texts,
                type="regular",
                allows_multiple_answers=True,
                is_anonymous=False,
            )

            await state.update_data(current_poll_id=poll.poll.id)
        else:
            await message.answer(f"Вопрос {current_question + 1}: {question.text}")


async def process_poll_answer(poll_answer: PollAnswer, state: FSMContext, bot: Bot):
    data = await state.get_data()

    if poll_answer.poll_id != data.get("current_poll_id"):
        return

    selected_options = poll_answer.option_ids

    async with async_session_maker() as session:
        question_id = data["questions"][data["current_question"]]

        options = await session.execute(
            select(Option).where(Option.question_id == question_id)
        )
        options = options.scalars().all()

        option_mapping = {index: option.id for index, option in enumerate(options)}

        correct_options = [option for option in options if option.is_correct]
        correct_option_ids = [option.id for option in correct_options]
        correct_option_texts = [option.option_text for option in correct_options]

        selected_option_ids = [option_mapping[index] for index in selected_options]
        is_correct = set(selected_option_ids) == set(correct_option_ids)

        answer = AttemptAnswer(
            test_attempt_id=data["test_attempt_id"],
            question_id=question_id,
            is_correct=is_correct,
        )
        session.add(answer)

        await session.commit()

    user_id = poll_answer.user.id

    if is_correct:
        await bot.send_message(
            user_id,
            f"✅ <b>Верно!</b>",
            parse_mode="HTML",
        )
    else:
        await bot.send_message(
            user_id,
            f"❌ <b>Неверно!</b>\n\n"
            f"<b>Правильный ответ:</b>\n{'\n'.join(correct_option_texts)}",
            parse_mode="HTML",
        )

    data["current_question"] += 1
    await state.update_data(data)

    next_question_message = await bot.send_message(
        user_id, "🔄 Переходим к следующему вопросу..."
    )
    await show_next_question(next_question_message, state)


async def process_text_answer(message: Message, state: FSMContext):
    if message.text == "Завершить тест":
        await finish_test(message, state)
        return

    data = await state.get_data()
    async with async_session_maker() as session:
        question_id = data["questions"][data["current_question"]]
        question = await session.get(Question, question_id)

        answer = AttemptAnswer(
            test_attempt_id=data["test_attempt_id"],
            question_id=question_id,
            given_answer=message.text,
            is_correct=message.text.lower() == question.answer_text.lower(),
        )
        session.add(answer)
        await session.commit()

    data["current_question"] += 1
    await state.update_data(data)
    await show_next_question(message, state)


async def finish_test(message: Message, state: FSMContext):
    data = await state.get_data()
    end_time = datetime.now()

    if "start_time" not in data:
        await message.answer(
            "Тест завершен",
            reply_markup=ReplyKeyboardRemove(),
        )
        await state.clear()
        return

    duration = end_time - data["start_time"]

    async with async_session_maker() as session:
        test_attempt = await session.get(TestAttempt, data["test_attempt_id"])
        answers = await session.execute(
            select(AttemptAnswer).where(
                AttemptAnswer.test_attempt_id == test_attempt.id
            )
        )
        answers = answers.scalars().all()

        correct_answers = sum(1 for answer in answers if answer.is_correct)
        total_answers = len(answers)

        test_attempt.end_time = end_time
        test_attempt.score = correct_answers
        await session.commit()

        percentage = (correct_answers / total_answers * 100) if total_answers > 0 else 0

        result_message = (
            f"🏁 <b>Тест завершен!</b>\n\n"
            f"⏳ <b>Время выполнения:</b> <i>{duration.seconds // 60} мин {duration.seconds % 60} сек</i>\n"
            f"✅ <b>Правильных ответов:</b> <i>{correct_answers} из {total_answers}</i>\n"
            f"📊 <b>Процент правильных ответов:</b> <i>{percentage:.1f}%</i>\n\n"
            "Начать новый тест - /start_test."
        )

        await message.answer(result_message, reply_markup=ReplyKeyboardRemove())
        await state.clear()


def register_test_handlers(dp: Dispatcher):
    dp.message.register(start_test, Command("start_test"))
    dp.message.register(process_questions_count, TestStates.waiting_for_questions_count)
    dp.message.register(process_text_answer, TestStates.answering_questions)
    dp.poll_answer.register(process_poll_answer, TestStates.answering_questions)
