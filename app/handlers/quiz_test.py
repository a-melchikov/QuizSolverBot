from datetime import datetime
from html import escape as html_escape

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    PollAnswer,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    WebAppInfo,
)
from sqlalchemy import func, select

from app.config import settings
from app.database import async_session_maker
from app.handlers.buttons import ButtonCallbackData
from app.models import AttemptAnswer, Bookmark, Option, Question, TestAttempt
from app.repositories.users import UserRepository


class TestStates(StatesGroup):
    waiting_for_questions_count = State()
    answering_questions = State()


class TestCountCallback(CallbackData, prefix="tcount"):
    count: int


def get_test_count_keyboard(total_questions: int) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text="5 вопросов", callback_data=TestCountCallback(count=5).pack()
            ),
            InlineKeyboardButton(
                text="10 вопросов", callback_data=TestCountCallback(count=10).pack()
            ),
        ],
        [
            InlineKeyboardButton(
                text="20 вопросов", callback_data=TestCountCallback(count=20).pack()
            ),
            InlineKeyboardButton(
                text="50 вопросов", callback_data=TestCountCallback(count=50).pack()
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"📚 Все вопросы ({total_questions})",
                callback_data=TestCountCallback(count=total_questions).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=ButtonCallbackData(action="main_menu").pack(),
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def start_test(event: Message | CallbackQuery, state: FSMContext):
    target_msg = event.message if isinstance(event, CallbackQuery) else event

    async with async_session_maker() as session:
        count_res = await session.execute(select(func.count(Question.id)))
        total_questions = count_res.scalar() or 0

    if total_questions == 0:
        await target_msg.answer("⚠️ В базе данных пока нет вопросов.")
        return

    text = (
        "🎯 <b>Настройка тестирования в чате</b>\n\n"
        "Выберите готовое количество вопросов или введите своё число (от 1 до "
        f"{total_questions}) в ответ на это сообщение:"
    )

    reply_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⏹ Завершить тест")]],
        resize_keyboard=True,
    )

    await target_msg.answer(
        text,
        reply_markup=get_test_count_keyboard(total_questions),
        parse_mode="HTML",
    )
    # Also provide persistent keyboard for convenience
    await target_msg.answer(
        "💡 <i>Вы можете в любой момент нажать «⏹ Завершить тест» для досрочного выхода.</i>",
        reply_markup=reply_kb,
        parse_mode="HTML",
    )

    await state.set_state(TestStates.waiting_for_questions_count)
    if isinstance(event, CallbackQuery):
        await event.answer()


async def process_count_callback(
    callback_query: CallbackQuery,
    callback_data: TestCountCallback,
    state: FSMContext,
):
    await callback_query.answer()
    await run_quiz_with_count(
        callback_query.message,
        state,
        callback_data.count,
        callback_query.from_user,
    )


async def process_questions_count(message: Message, state: FSMContext):
    if message.text in ["Завершить тест", "⏹ Завершить тест", "/cancel", "отмена"]:
        await finish_test(message, state)
        return

    if not message.text or not message.text.isdigit():
        await message.answer(
            "Пожалуйста, выберите количество кнопкой выше или введите число:"
        )
        return

    questions_count = int(message.text)
    if questions_count <= 0:
        await message.answer("Количество вопросов должно быть больше нуля:")
        return

    await run_quiz_with_count(message, state, questions_count, message.from_user)


async def run_quiz_with_questions(
    message: Message,
    state: FSMContext,
    questions: list[Question],
    user,
    title: str = "Тест",
):
    async with async_session_maker() as session:
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

    reply_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⏹ Завершить тест")]],
        resize_keyboard=True,
    )
    await message.answer(
        f"🚀 <b>{title} начат!</b> Всего вопросов: <b>{len(questions)}</b>\n\n"
        "Отвечайте на вопросы ниже:",
        reply_markup=reply_kb,
        parse_mode="HTML",
    )
    await show_next_question(message, state)
    await state.set_state(TestStates.answering_questions)


async def run_quiz_with_count(message: Message, state: FSMContext, count: int, from_user):
    user_repo = UserRepository()
    user = await user_repo.get_or_create_user(
        telegram_id=from_user.id,
        username=from_user.username,
        first_name=from_user.first_name,
        last_name=from_user.last_name,
    )

    async with async_session_maker() as session:
        query = select(Question).order_by(func.random()).limit(count)
        result = await session.execute(query)
        questions = list(result.scalars().all())

    if not questions:
        await message.answer("Не удалось загрузить вопросы из базы.")
        await state.clear()
        return

    await run_quiz_with_questions(message, state, questions, user, "Тест")


async def start_errors_test(event: Message | CallbackQuery, state: FSMContext):
    target_msg = event.message if isinstance(event, CallbackQuery) else event
    user_repo = UserRepository()
    user = await user_repo.get_or_create_user(
        telegram_id=event.from_user.id,
        username=event.from_user.username,
        first_name=event.from_user.first_name,
        last_name=event.from_user.last_name,
    )

    async with async_session_maker() as session:
        err_subq = (
            select(AttemptAnswer.question_id)
            .join(TestAttempt, TestAttempt.id == AttemptAnswer.test_attempt_id)
            .where(
                TestAttempt.user_id == user.id,
                AttemptAnswer.is_correct.is_(False),
            )
            .distinct()
        )
        query = (
            select(Question)
            .where(Question.id.in_(err_subq))
            .order_by(func.random())
            .limit(20)
        )
        res = await session.execute(query)
        questions = list(res.scalars().all())

    if not questions:
        from app.handlers.buttons import get_help_keyboard

        await target_msg.answer(
            "🎉 <b>У вас нет зафиксированных ошибок!</b>\n\n"
            "Вы отлично справляетесь. Пройдите общий тест или откройте приложение для закрепления.",
            reply_markup=get_help_keyboard(),
            parse_mode="HTML",
        )
        if isinstance(event, CallbackQuery):
            await event.answer()
        return

    await run_quiz_with_questions(
        target_msg, state, questions, user, "❌ Работа над ошибками"
    )
    if isinstance(event, CallbackQuery):
        await event.answer()


async def start_bookmarks_test(event: Message | CallbackQuery, state: FSMContext):
    target_msg = event.message if isinstance(event, CallbackQuery) else event
    user_repo = UserRepository()
    user = await user_repo.get_or_create_user(
        telegram_id=event.from_user.id,
        username=event.from_user.username,
        first_name=event.from_user.first_name,
        last_name=event.from_user.last_name,
    )

    async with async_session_maker() as session:
        bm_subq = select(Bookmark.question_id).where(Bookmark.user_id == user.id)
        query = (
            select(Question)
            .where(Question.id.in_(bm_subq))
            .order_by(func.random())
            .limit(20)
        )
        res = await session.execute(query)
        questions = list(res.scalars().all())

    if not questions:
        from app.handlers.buttons import get_help_keyboard

        await target_msg.answer(
            "⭐️ <b>В избранном пока нет вопросов.</b>\n\n"
            "Вы можете добавлять сложные вопросы в закладки в приложении, чтобы легко повторять их перед сдачей.",
            reply_markup=get_help_keyboard(),
            parse_mode="HTML",
        )
        if isinstance(event, CallbackQuery):
            await event.answer()
        return

    await run_quiz_with_questions(
        target_msg, state, questions, user, "⭐️ Тест по избранному"
    )
    if isinstance(event, CallbackQuery):
        await event.answer()


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

        total_q = len(questions)
        q_header = f"Вопрос {current_question + 1} из {total_q}"

        if question.has_options:
            options_res = await session.execute(
                select(Option).where(Option.question_id == question.id)
            )
            options = list(options_res.scalars().all())

            if len(options) < 2:
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
            if len(question_text) > 280:
                question_text = question_text[:277] + "..."

            poll = await message.answer_poll(
                question=f"[{q_header}]\n{question_text}",
                options=option_texts,
                type="regular",
                allows_multiple_answers=True,
                is_anonymous=False,
            )

            await state.update_data(current_poll_id=poll.poll.id)
        else:
            await message.answer(
                f"📝 <b>[{q_header}]</b>\n\n"
                f"{html_escape(question.text)}\n\n"
                "<i>Отправьте ваш ответ сообщением в чат:</i>",
                parse_mode="HTML",
            )


async def process_poll_answer(poll_answer: PollAnswer, state: FSMContext, bot: Bot):
    data = await state.get_data()
    if poll_answer.poll_id != data.get("current_poll_id"):
        return

    current_idx = data.get("current_question", 0)
    questions = data.get("questions", [])
    if current_idx >= len(questions):
        return

    question_id = questions[current_idx]
    user_id = poll_answer.user.id

    async with async_session_maker() as session:
        options_res = await session.execute(
            select(Option).where(Option.question_id == question_id)
        )
        options = list(options_res.scalars().all())

        correct_option_indices = [
            i for i, opt in enumerate(options) if opt.is_correct
        ]
        user_selected = poll_answer.option_ids
        is_correct = set(user_selected) == set(correct_option_indices)

        answer = AttemptAnswer(
            test_attempt_id=data["test_attempt_id"],
            question_id=question_id,
            is_correct=is_correct,
        )
        session.add(answer)
        await session.commit()

        correct_option_texts = [
            f"• {opt.option_text}" for opt in options if opt.is_correct
        ]

    if is_correct:
        await bot.send_message(user_id, "✅ <b>Верно!</b>", parse_mode="HTML")
    else:
        await bot.send_message(
            user_id,
            f"❌ <b>Неверно.</b>\n\n<b>Правильный вариант:</b>\n"
            f"{chr(10).join(correct_option_texts)}",
            parse_mode="HTML",
        )

    await state.update_data(current_question=current_idx + 1)
    next_msg = await bot.send_message(user_id, "⏳ Следующий вопрос...")
    await show_next_question(next_msg, state)


async def process_text_answer(message: Message, state: FSMContext):
    if message.text in ["Завершить тест", "⏹ Завершить тест", "/cancel", "отмена"]:
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
        expected = (question.answer_text or "").strip() if question else ""
        user_val = (message.text or "").strip()
        is_correct = user_val.lower() == expected.lower()

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
            f"❌ <b>Неверно.</b>\n\n<b>Правильный ответ:</b> <code>{html_escape(expected)}</code>\n",
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

    if percentage >= 80:
        praise = "🌟 <b>Отличный результат! Высокий уровень подготовки!</b>"
    elif percentage >= 50:
        praise = "👍 <b>Хороший результат, но есть над чем поработать.</b>"
    else:
        praise = "📚 <b>Рекомендуется повторить материал и пройти тренировку снова.</b>"

    result_message = (
        f"🏁 <b>Тестирование завершено!</b>\n\n"
        f"• Правильно: <b>{correct_answers} из {total_answers}</b>\n"
        f"• Результат: <b>{percentage:.1f}%</b>\n"
        f"• Время: <b>{duration_min} мин {duration_sec} сек</b>\n\n"
        f"{praise}"
    )

    buttons = []
    if settings.WEBAPP_URL:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🚀 Открыть ОП тесты (Разбор)",
                    web_app=WebAppInfo(url=settings.WEBAPP_URL),
                )
            ]
        )
    buttons.extend(
        [
            [
                InlineKeyboardButton(
                    text="🔄 Пройти ещё раз",
                    callback_data=ButtonCallbackData(action="start_test").pack(),
                ),
                InlineKeyboardButton(
                    text="📊 Моя история",
                    callback_data=ButtonCallbackData(action="history").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🏠 В главное меню",
                    callback_data=ButtonCallbackData(action="main_menu").pack(),
                )
            ],
        ]
    )

    await message.answer(
        result_message,
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
    )
    await message.answer(
        "Выберите следующее действие:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await state.clear()


def register_test_handlers(dp: Dispatcher):
    dp.message.register(start_test, Command("start_test"))
    dp.message.register(start_test, Command("test"))
    dp.message.register(start_errors_test, Command("errors"))
    dp.message.register(start_errors_test, Command("mistakes"))
    dp.message.register(start_bookmarks_test, Command("bookmarks"))
    dp.message.register(start_bookmarks_test, Command("favorites"))
    dp.callback_query.register(process_count_callback, TestCountCallback.filter())
    dp.message.register(process_questions_count, TestStates.waiting_for_questions_count)
    dp.message.register(process_text_answer, TestStates.answering_questions)
    dp.poll_answer.register(process_poll_answer, TestStates.answering_questions)
