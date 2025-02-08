from aiogram import types, Dispatcher
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.database import async_session_maker
from app.models import Question, Option
from app.logger_setup import get_logger
from app.repositories.questions import QuestionRepository
from app.schemas.options import OptionCreate
from app.schemas.questions import QuestionCreate

logger = get_logger(__name__)


class AddQuestionStates(StatesGroup):
    waiting_for_question_text = State()
    waiting_for_has_options = State()
    waiting_for_answer = State()
    waiting_for_options = State()
    waiting_for_correct_options = State()


async def add_question_start(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Введите текст вопроса:")
    await state.set_state(AddQuestionStates.waiting_for_question_text)


async def process_question_text(message: types.Message, state: FSMContext) -> None:
    question_text = message.text.strip()
    if not question_text:
        await message.answer("Введите непустой вопрос:")
        return
    await state.update_data(question_text=question_text)
    await message.answer("Вопрос с вариантами ответа? (да/нет)")
    await state.set_state(AddQuestionStates.waiting_for_has_options)


async def process_has_options(message: types.Message, state: FSMContext) -> None:
    answer = message.text.strip().lower()
    if answer not in ("да", "нет"):
        await message.answer("Пожалуйста, ответьте 'да' или 'нет'.")
        return

    has_options = answer == "да"
    await state.update_data(has_options=has_options)

    if has_options:
        await message.answer("Введите варианты ответа, каждый вариант с новой строки:")
        await state.set_state(AddQuestionStates.waiting_for_options)
    else:
        await message.answer("Введите ответ:")
        await state.set_state(AddQuestionStates.waiting_for_answer)


async def process_answer(message: types.Message, state: FSMContext) -> None:
    answer_text = message.text.strip()
    if not answer_text:
        await message.answer("Ответ не может быть пустым. Введите ответ:")
        return
    await state.update_data(answer_text=answer_text)
    data = await state.get_data()
    question_repository = QuestionRepository()
    if not data.get("has_options"):
        question_schema = QuestionCreate(
            text=data["question_text"],
            has_options=False,
            answer_text=answer_text,
            created_by=message.from_user.id,
        )
        await question_repository.create_question(question_schema)
        await message.answer("Вопрос успешно добавлен!")
        await state.clear()
    else:
        await message.answer("Введите варианты ответа, каждый вариант с новой строки:")
        await state.set_state(AddQuestionStates.waiting_for_options)


async def process_options(message: types.Message, state: FSMContext) -> None:
    raw_text = message.text.strip()
    options = [line.strip() for line in raw_text.splitlines() if line.strip()]

    if not options:
        await message.answer(
            "Вы не ввели ни одного варианта. Пожалуйста, введите варианты ответа:"
        )
        return

    await state.update_data(options=options)
    await message.answer(
        "Введите номера правильных вариантов через пробел (например, 1 3 4):"
    )
    await state.set_state(AddQuestionStates.waiting_for_correct_options)


async def process_correct_options(message: types.Message, state: FSMContext) -> None:
    raw_input = message.text.strip()
    try:
        correct_indices = [int(x) - 1 for x in raw_input.split()]
    except ValueError:
        await message.answer(
            "Пожалуйста, введите корректные числа, разделённые пробелами."
        )
        return

    data = await state.get_data()
    options = data.get("options")
    if not options:
        await message.answer("Ошибка: варианты ответа не найдены.")
        await state.clear()
        return

    if any(index < 0 or index >= len(options) for index in correct_indices):
        await message.answer(
            "Один или несколько номеров некорректны. Попробуйте ещё раз:"
        )
        return

    question_schema = QuestionCreate(
        text=data["question_text"],
        has_options=True,
        answer_text=data.get("answer_text"),
        created_by=message.from_user.id,
    )

    option_schemes = [
        OptionCreate(option_text=option_text, is_correct=(idx in correct_indices))
        for idx, option_text in enumerate(options)
    ]

    question_repository = QuestionRepository()
    await question_repository.create_question_with_options(
        question_schema, option_schemes
    )

    await message.answer("Вопрос успешно добавлен!")
    await state.clear()

def register_admin_handlers(dp: Dispatcher) -> None:
    dp.message.register(add_question_start, Command(commands=["add_question"]))
    dp.message.register(
        process_question_text, StateFilter(AddQuestionStates.waiting_for_question_text)
    )
    dp.message.register(
        process_has_options, StateFilter(AddQuestionStates.waiting_for_has_options)
    )
    dp.message.register(
        process_answer, StateFilter(AddQuestionStates.waiting_for_answer)
    )
    dp.message.register(
        process_options, StateFilter(AddQuestionStates.waiting_for_options)
    )
    dp.message.register(
        process_correct_options,
        StateFilter(AddQuestionStates.waiting_for_correct_options),
    )
