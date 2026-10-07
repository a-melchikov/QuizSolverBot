from datetime import datetime
from html import escape as html_escape

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    KeyboardButton,
    Message,
    PollAnswer,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from sqlalchemy import func, select

from app.database import async_session_maker
from app.models import AttemptAnswer, Option, Question, TestAttempt
from app.repositories.users import UserRepository


class TestStates(StatesGroup):
    waiting_for_questions_count = State()
    answering_questions = State()


async def start_test(message: Message, state: FSMContext):
    async with async_session_maker() as session:
        count_res = await session.execute(select(func.count(Question.id)))
        total_questions = count_res.scalar() or 0

    if total_questions == 0:
        await message.answer("В базе данных пока нет вопросов.")
        return

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

    if not message.text or not message.text.isdigit():
        await message.answer("Пожалуйста, введите положительное число:")
        return

    questions_count = int(message.text)
    if questions_count <= 0:
        await message.answer("Количество вопросов должно быть больше нуля:")
        return

    user_repo = UserRepository()
    user = await user_repo.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )

    async with async_session_maker() as session:
        query = select(Question).order_by(func.random()).limit(questions_count)
        result = await session.execute(query)
        questions = list(result.scalars().all())

        if not questions:
            await message.answer("Не удалось получить вопросы.")
            await state.clear()
            return

        test_attempt = TestAttempt(
            user_id=user.id,
            total_questions=len(questions),
        )
        session.add(test_attempt)
        await session.commit()
        await session.refresh(test_attempt)

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
    current_question = data.get("current_question", 0)
    questions = data.get("questions", [])

    if current_question >= len(questions):
        await finish_test(message, state)
        return

    async with async_session_maker() as session:
        question = await session.get(Question, questions[current_question])
        if not question:
            await state.update_data(current_question=current_question + 1)
            await show_next_question(message, state)
            return

        if question.has_options:
            options_res = await session.execute(
                select(Option).where(Option.question_id == question.id)
            )
            options = list(options_res.scalars().all())

            if len(options) < 2:
                await message.answer(
                    f"⚠️ Вопрос {current_question + 1} содержит менее 2 вариантов ответа, пропускаем."
                )
                await state.update_data(current_question=current_question + 1)
                await show_next_question(message, state)
                return

            option_texts = []
            for opt in options:
                text = opt.option_text
                if len(text) > 97:
                    text = text[:94] + "..."
                option_texts.append(text)

            question_text = question.text
            if len(question_text) > 290:
                question_text = question_text[:287] + "..."

            poll = await message.answer_poll(
                question=f"{current_question + 1}. {question_text}",
                options=option_texts,
                type="regular",
                allows_multiple_answers=True,
                is_anonymous=False,
            )

            await state.update_data(current_poll_id=poll.poll.id)
        else:
            await message.answer(
                f"<b>Вопрос {current_question + 1}:</b>\n{html_escape(question.text)}",
                parse_mode="HTML",
            )


async def process_poll_answer(poll_answer: PollAnswer, state: FSMContext, bot: Bot):
    data = await state.get_data()

    if poll_answer.poll_id != data.get("current_poll_id"):
        return

    selected_options = poll_answer.option_ids
    current_idx = data.get("current_question", 0)
    questions = data.get("questions", [])
    if current_idx >= len(questions):
        return
    question_id = questions[current_idx]

    async with async_session_maker() as session:
        options_res = await session.execute(
            select(Option).where(Option.question_id == question_id)
        )
        options = list(options_res.scalars().all())

        option_mapping = {index: option.id for index, option in enumerate(options)}
        correct_options = [option for option in options if option.is_correct]
        correct_option_ids = [option.id for option in correct_options]
        correct_option_texts = [
            html_escape(option.option_text) for option in correct_options
        ]

        selected_option_ids = [
            option_mapping[index]
            for index in selected_options
            if index in option_mapping
        ]
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
            "✅ <b>Верно!</b>",
            parse_mode="HTML",
        )
    else:
        await bot.send_message(
            user_id,
            f"❌ <b>Неверно!</b>\n\n"
            f"<b>Правильный ответ:</b>\n{chr(10).join(correct_option_texts)}",
            parse_mode="HTML",
        )

    await state.update_data(current_question=current_idx + 1)

    next_msg = await bot.send_message(user_id, "🔄 Переходим к следующему вопросу...")
    await show_next_question(next_msg, state)


async def process_text_answer(message: Message, state: FSMContext):
    if message.text == "Завершить тест":
        await finish_test(message, state)
        return

    data = await state.get_data()
    current_idx = data.get("current_question", 0)
    questions = data.get("questions", [])
    if current_idx >= len(questions):
        await finish_test(message, state)
        return
    question_id = questions[current_idx]

    async with async_session_maker() as session:
        question = await session.get(Question, question_id)
        expected_answer = (question.answer_text or "").strip() if question else ""
        user_answer = (message.text or "").strip()
        is_correct = user_answer.lower() == expected_answer.lower()

        answer = AttemptAnswer(
            test_attempt_id=data["test_attempt_id"],
            question_id=question_id,
            is_correct=is_correct,
        )
        session.add(answer)
        await session.commit()

    if is_correct:
        await message.answer("✅ <b>Верно!</b>", parse_mode="HTML")
    else:
        await message.answer(
            f"❌ <b>Неверно!</b>\n\n"
            f"<b>Правильный ответ:</b> {html_escape(expected_answer)}\n",
            parse_mode="HTML",
        )

    await state.update_data(current_question=current_idx + 1)
    await show_next_question(message, state)


async def finish_test(message: Message, state: FSMContext):
    data = await state.get_data()
    end_time = datetime.now()

    if "start_time" not in data or "test_attempt_id" not in data:
        await message.answer(
            "Тест завершен.",
            reply_markup=ReplyKeyboardRemove(),
        )
        await state.clear()
        return

    duration = end_time - data["start_time"]

    async with async_session_maker() as session:
        test_attempt = await session.get(TestAttempt, data["test_attempt_id"])
        if test_attempt:
            answers_res = await session.execute(
                select(AttemptAnswer).where(
                    AttemptAnswer.test_attempt_id == test_attempt.id
                )
            )
            answers = list(answers_res.scalars().all())

            correct_answers = sum(1 for a in answers if a.is_correct)
            total_answers = len(answers)

            test_attempt.end_time = end_time
            test_attempt.score = correct_answers
            await session.commit()
        else:
            correct_answers = 0
            total_answers = 0

    percentage = (correct_answers / total_answers * 100) if total_answers > 0 else 0
    duration_min = duration.seconds // 60
    duration_sec = duration.seconds % 60

    result_message = (
        f"🏁 <b>Тест завершен!</b>\n\n"
        f"⏳ <b>Время выполнения:</b> <i>{duration_min} мин {duration_sec} сек</i>\n"
        f"✅ <b>Правильных ответов:</b> <i>{correct_answers} из {total_answers}</i>\n"
        f"📊 <b>Процент правильных ответов:</b> <i>{percentage:.1f}%</i>\n\n"
        "Начать новый тест: /start_test"
    )

    await message.answer(
        result_message, reply_markup=ReplyKeyboardRemove(), parse_mode="HTML"
    )
    await state.clear()


def register_test_handlers(dp: Dispatcher):
    dp.message.register(start_test, Command("start_test"))
    dp.message.register(process_questions_count, TestStates.waiting_for_questions_count)
    dp.message.register(process_text_answer, TestStates.answering_questions)
    dp.poll_answer.register(process_poll_answer, TestStates.answering_questions)
