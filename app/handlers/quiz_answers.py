from aiogram import types, Dispatcher
from aiogram.filters import StateFilter, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.database import async_session_maker
from app.models import Question


class AnswerQuestionStates(StatesGroup):
    waiting_for_question_id = State()
    waiting_for_answer = State()


async def answer_question_start(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Введите ID вопроса, который нужно решить:")
    await state.set_state(AnswerQuestionStates.waiting_for_question_id)


async def process_question_id(message: types.Message, state: FSMContext) -> None:
    try:
        question_id = int(message.text.strip())
    except ValueError:
        await message.answer("ID должен быть числом. Попробуйте снова:")
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
        await message.answer(f"Вопрос с ID {question_id} не найден. Попробуйте снова:")
        return

    await state.update_data(question_id=question_id, selected_answers=[])

    if question.has_options:
        keyboard_buttons = [
            [
                InlineKeyboardButton(
                    text=f"{option.option_text}",
                    callback_data=f"toggle:{question_id}:{option.id}",
                )
            ]
            for option in question.options
        ]

        keyboard_buttons.append(
            [InlineKeyboardButton(text="Готово", callback_data=f"submit:{question_id}")]
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        await message.answer(
            f"Вопрос: {question.text}\n\nВыберите правильные варианты:",
            reply_markup=keyboard,
        )
    else:
        await message.answer(f"Вопрос: {question.text}\n\nВведите ваш ответ текстом:")
        await state.set_state(AnswerQuestionStates.waiting_for_answer)


async def process_answer_callback(
    callback_query: types.CallbackQuery, state: FSMContext
) -> None:
    callback_data = callback_query.data

    parts = callback_data.split(":")
    if len(parts) < 2 or len(parts) > 3:
        await callback_query.message.answer("Ошибка: неверный формат данных.")
        await callback_query.answer()
        return

    action = parts[0]
    question_id_str = parts[1]
    option_id = None if len(parts) == 2 else parts[2]

    async with async_session_maker() as session:
        data = await state.get_data()
        question_id = data.get("question_id")
        selected_answers = data.get("selected_answers", [])

        try:
            question_id = int(question_id_str)
            option_id = int(option_id) if option_id else None
        except ValueError:
            await callback_query.message.answer("Ошибка: данные неверного формата.")
            await callback_query.answer()
            return

        question_query = (
            select(Question)
            .options(selectinload(Question.options))
            .where(Question.id == question_id)
        )
        result = await session.execute(question_query)
        question = result.scalar()

        if not question:
            await callback_query.message.answer("Ошибка: вопрос не найден.")
            await state.clear()
            return

        if action == "toggle":
            if option_id is None:
                await callback_query.message.answer("Ошибка: неверный формат данных.")
                await callback_query.answer()
                return

            if option_id in selected_answers:
                selected_answers.remove(option_id)
            else:
                selected_answers.append(option_id)

            # Сохраняем новое состояние выбора
            await state.update_data(selected_answers=selected_answers)

            keyboard_buttons = [
                [
                    InlineKeyboardButton(
                        text=f"{'✅' if option.id in selected_answers else ''} {option.option_text}",
                        callback_data=f"toggle:{question.id}:{option.id}",
                    )
                ]
                for option in question.options
            ]

            keyboard_buttons.append(
                [
                    InlineKeyboardButton(
                        text="Готово", callback_data=f"submit:{question_id}"
                    )
                ]
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            await callback_query.message.edit_reply_markup(reply_markup=keyboard)

        elif action == "submit":
            correct_answers = {
                option.id for option in question.options if option.is_correct
            }
            selected_answers_set = set(selected_answers)

            if selected_answers_set == correct_answers:
                await callback_query.message.answer("Верный ответ! 🎉")
            else:
                correct_options = [
                    opt.option_text for opt in question.options if opt.is_correct
                ]
                correct_text = ", ".join(correct_options)
                await callback_query.message.answer(
                    f"Неверно. Правильные варианты: {correct_text}"
                )

            await state.clear()

        await callback_query.answer()


async def process_textual_answer(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    question_id = data["question_id"]

    async with async_session_maker() as session:
        query = select(Question).where(Question.id == question_id)
        result = await session.execute(query)
        question = result.scalar()

    if not question:
        await message.answer("Ошибка: вопрос не найден.")
        await state.clear()
        return

    user_answer = message.text.strip()

    if user_answer.lower() == (question.answer_text or "").lower():
        await message.answer("Верный ответ! 🎉")
    else:
        await message.answer(
            f"Неверно. Правильный ответ: {question.answer_text or 'Не указан'}"
        )

    await state.clear()


def register_answer_handlers(dp: Dispatcher) -> None:
    dp.message.register(answer_question_start, Command(commands=["answer_question"]))
    dp.message.register(
        process_question_id, StateFilter(AnswerQuestionStates.waiting_for_question_id)
    )
    dp.message.register(
        process_textual_answer, StateFilter(AnswerQuestionStates.waiting_for_answer)
    )
    dp.callback_query.register(
        process_answer_callback,
        lambda c: c.data.startswith("toggle:") or c.data.startswith("submit:"),
    )
