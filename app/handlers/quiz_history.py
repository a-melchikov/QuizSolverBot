from aiogram import types, Dispatcher
from aiogram.filters import Command
from sqlalchemy import select
from app.database import async_session_maker
from app.models import TestAttempt


async def view_test_history(message: types.Message):
    if hasattr(message, "via_bot"):
        user_id = message.chat.id
    else:
        user_id = message.from_user.id

    async with async_session_maker() as session:
        test_attempts = await session.execute(
            select(TestAttempt)
            .where(TestAttempt.user_id == user_id)
            .order_by(TestAttempt.end_time.desc())
        )
        test_attempts = test_attempts.scalars().all()

    if not test_attempts:
        await message.answer("🚫 История тестов отсутствует.")
        return

    history_message = "📜 <b>История ваших тестов:</b>\n"
    for i, attempt in enumerate(reversed(test_attempts), start=1):
        end_time_str = (
            attempt.end_time.strftime("%d.%m.%Y %H:%M")
            if attempt.end_time
            else "⏳ Тест не завершен"
        )
        correct_answers = attempt.score or 0
        total_questions = attempt.total_questions or 0

        if total_questions > 0:
            result = f"{correct_answers} из {total_questions}"
            percent = round((correct_answers / total_questions) * 100, 2)
        else:
            result = "Не завершен"
            percent = 0

        history_message += (
            f"📝 <b>Попытка #{i}</b>\n"
            f"📆 Дата завершения: <i>{end_time_str}</i>\n"
            f"✅ Результат: {result}\n"
            f"📊 Процент выполнения: {percent}%\n\n"
        )

    await message.answer(history_message, parse_mode="HTML")


def register_history_handler(dp: Dispatcher):
    dp.message.register(view_test_history, Command("history"))
