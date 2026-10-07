from aiogram import Dispatcher, types
from aiogram.filters import Command
from sqlalchemy import select

from app.database import async_session_maker
from app.models import TestAttempt
from app.repositories.users import UserRepository


async def view_test_history(message: types.Message):
    telegram_user = message.from_user
    if not telegram_user:
        await message.answer("Не удалось определить пользователя.")
        return

    user_repo = UserRepository()
    user = await user_repo.get_or_create_user(
        telegram_id=telegram_user.id,
        username=telegram_user.username,
        first_name=telegram_user.first_name,
        last_name=telegram_user.last_name,
    )

    async with async_session_maker() as session:
        query = (
            select(TestAttempt)
            .where(TestAttempt.user_id == user.id)
            .order_by(TestAttempt.created_at.desc())
            .limit(20)
        )
        result = await session.execute(query)
        test_attempts = list(result.scalars().all())

    if not test_attempts:
        await message.answer("🚫 История тестов отсутствует.")
        return

    history_message = "📜 <b>История ваших тестов (последние попытки):</b>\n\n"
    for i, attempt in enumerate(reversed(test_attempts), start=1):
        end_time_str = (
            attempt.end_time.strftime("%d.%m.%Y %H:%M")
            if attempt.end_time
            else "⏳ Тест не завершен"
        )
        correct_answers = attempt.score or 0
        total_questions = attempt.total_questions or 0

        if total_questions > 0 and attempt.end_time:
            result_str = f"{correct_answers} из {total_questions}"
            percent = round((correct_answers / total_questions) * 100, 1)
        else:
            result_str = "Не завершен"
            percent = 0.0

        history_message += (
            f"📝 <b>Попытка #{i}</b>\n"
            f"📆 Дата: <i>{end_time_str}</i>\n"
            f"✅ Результат: {result_str}\n"
            f"📊 Процент: {percent}%\n\n"
        )

    await message.answer(history_message, parse_mode="HTML")


def register_history_handler(dp: Dispatcher):
    dp.message.register(view_test_history, Command("history"))
