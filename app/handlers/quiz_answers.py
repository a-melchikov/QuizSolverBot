from html import escape as html_escape

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    PollAnswer,
)
from sqlalchemy import select

from app.database import async_session_maker
from app.handlers.buttons import ButtonCallbackData
from app.models import Option, Question


class AnswerState(StatesGroup):
    waiting_for_question_id = State()
    answering = State()


def get_after_question_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔍 Другой вопрос",
                    callback_data=ButtonCallbackData(action="start_question").pack(),
                ),
                InlineKeyboardButton(
                    text="🎯 Начать тест",
                    callback_data=ButtonCallbackData(action="start_test").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🏠 Главное меню",
                    callback_data=ButtonCallbackData(action="main_menu").pack(),
                )
            ],
        ]
    )


async def start_question(event: Message | CallbackQuery, state: FSMContext):
    target_msg = event.message if isinstance(event, CallbackQuery) else event

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=ButtonCallbackData(action="main_menu").pack(),
                )
            ]
        ]
    )
    await target_msg.answer(
        "🔍 <b>Решение отдельного вопроса</b>\n\n"
        "Отправьте номер (ID) вопроса из базы:\n"
        "<i>Например: <code>15</code></i>",
        reply_markup=kb,
        parse_mode="HTML",
    )
    await state.set_state(AnswerState.waiting_for_question_id)
    if isinstance(event, CallbackQuery):
        await event.answer()


async def process_question_id(message: Message, state: FSMContext):
    if message.text in ["/cancel", "отмена", "Отмена"]:
        await state.clear()
        from app.handlers.start import get_start_keyboard

        await message.answer(
            "Действие отменено.", reply_markup=get_start_keyboard(), parse_mode="HTML"
        )
        return

    if not message.text or not message.text.isdigit():
        await message.answer("Пожалуйста, введите корректный числовой ID (например: <code>10</code>):", parse_mode="HTML")
        return

    question_id = int(message.text)
    await answer_question(message, state, question_id)


async def answer_question(message: Message, state: FSMContext, question_id: int):
    async with async_session_maker() as session:
        question = await session.get(Question, question_id)
        if not question:
            await message.answer(
                f"❌ Вопрос с ID <code>{question_id}</code> не найден в базе.",
                reply_markup=get_after_question_keyboard(),
                parse_mode="HTML",
            )
            await state.clear()
            return

        await state.update_data(question_id=question_id)

        if question.has_options:
            options_result = await session.execute(
                select(Option).where(Option.question_id == question.id)
            )
            options = list(options_result.scalars().all())

            option_texts = []
            for opt in options:
                text = opt.option_text
                if len(text) > 97:
                    text = text[:94] + "..."
                option_texts.append(text)

            q_text = question.text
            if len(q_text) > 280:
                q_text = q_text[:277] + "..."

            poll = await message.answer_poll(
                question=f"[Вопрос #{question_id}]\n{q_text}",
                options=option_texts,
                type="regular",
                allows_multiple_answers=True,
                is_anonymous=False,
            )
            await state.update_data(current_poll_id=poll.poll.id)
        else:
            await message.answer(
                f"📝 <b>Вопрос #{question_id}:</b>\n\n{html_escape(question.text)}\n\n"
                "<i>Отправьте ваш ответ текстом в чат:</i>",
                parse_mode="HTML",
            )

        await state.set_state(AnswerState.answering)


async def process_poll_answer(poll_answer: PollAnswer, state: FSMContext, bot: Bot):
    data = await state.get_data()

    if poll_answer.poll_id != data.get("current_poll_id"):
        return

    async with async_session_maker() as session:
        question = await session.get(Question, data["question_id"])
        if not question:
            await state.clear()
            return

        options_result = await session.execute(
            select(Option).where(Option.question_id == question.id)
        )
        options = list(options_result.scalars().all())

        option_mapping = {index: option.id for index, option in enumerate(options)}
        selected_option_ids = [
            option_mapping[index]
            for index in poll_answer.option_ids
            if index in option_mapping
        ]

        correct_options = [option for option in options if option.is_correct]
        correct_option_ids = [option.id for option in correct_options]
        is_correct = set(selected_option_ids) == set(correct_option_ids)

        correct_text = "\n".join(
            f"• {html_escape(opt.option_text)}" for opt in correct_options
        )
        result_message = (
            "✅ <b>Верно! Отличный ответ.</b>"
            if is_correct
            else f"❌ <b>Неверно.</b>\n\n<b>Правильный вариант:</b>\n{correct_text}"
        )
        await bot.send_message(
            poll_answer.user.id,
            result_message,
            reply_markup=get_after_question_keyboard(),
            parse_mode="HTML",
        )
        await state.clear()


async def process_text_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    question_id = data.get("question_id")
    if not question_id:
        await state.clear()
        return

    async with async_session_maker() as session:
        question = await session.get(Question, question_id)
        if not question:
            await message.answer("Вопрос не найден.")
            await state.clear()
            return

        expected_answer = (question.answer_text or "").strip()
        user_answer = (message.text or "").strip()
        is_correct = user_answer.lower() == expected_answer.lower()

        result_message = (
            "✅ <b>Верно! Точный ответ.</b>"
            if is_correct
            else f"❌ <b>Неверно.</b>\n\n<b>Правильный ответ:</b> <code>{html_escape(expected_answer)}</code>"
        )
        await message.answer(
            result_message,
            reply_markup=get_after_question_keyboard(),
            parse_mode="HTML",
        )
        await state.clear()


def register_answer_handlers(dp: Dispatcher):
    dp.message.register(start_question, Command("start_question"))
    dp.message.register(start_question, Command("question"))
    dp.message.register(process_question_id, AnswerState.waiting_for_question_id)
    dp.message.register(process_text_answer, AnswerState.answering)
    dp.poll_answer.register(process_poll_answer, AnswerState.answering)
