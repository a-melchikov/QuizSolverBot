from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)
from sqlalchemy import select

from app.config import settings
from app.database import async_session_maker
from app.handlers.buttons import ButtonCallbackData
from app.models import TestAttempt
from app.repositories.users import UserRepository


async def view_test_history(event: Message | CallbackQuery):
    target_msg = event.message if isinstance(event, CallbackQuery) else event
    telegram_user = event.from_user

    if not telegram_user:
        await target_msg.answer("Не удалось определить пользователя.")
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
            .limit(10)
        )
        result = await session.execute(query)
        test_attempts = list(result.scalars().all())

    if not test_attempts:
        buttons = [
            [
                InlineKeyboardButton(
                    text="🎯 Начать первый тест",
                    callback_data=ButtonCallbackData(action="start_test").pack(),
                )
            ]
        ]
        if settings.WEBAPP_URL:
            buttons.insert(
                0,
                [
                    InlineKeyboardButton(
                        text="🚀 Открыть ОП тесты",
                        web_app=WebAppInfo(url=settings.WEBAPP_URL),
                    )
                ],
            )
        await target_msg.answer(
            "📊 <b>История тестирования пуста</b>\n\n"
            "Вы пока не завершили ни одного теста. Начните прямо сейчас!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            parse_mode="HTML",
        )
        if isinstance(event, CallbackQuery):
            await event.answer()
        return

    completed = [a for a in test_attempts if a.end_time and a.total_questions > 0]
    avg_score = (
        round(sum((a.score or 0) / a.total_questions * 100 for a in completed) / len(completed), 1)
        if completed
        else 0.0
    )

    history_lines = [
        "📊 <b>Ваша статистика тестов</b>\n",
        f"• Пройдено тестов: <b>{len(completed)}</b>",
        f"• Средний результат: <b>{avg_score}%</b>\n",
        "<b>Последние попытки:</b>",
    ]

    for i, attempt in enumerate(test_attempts, start=1):
        date_str = (
            attempt.created_at.strftime("%d.%m %H:%M")
            if attempt.created_at
            else "—"
        )
        score = attempt.score or 0
        total = attempt.total_questions or 0
        pct = round((score / total * 100), 1) if total > 0 and attempt.end_time else 0.0

        if not attempt.end_time:
            icon = "⏳"
            status = "Не завершен"
        elif pct >= 80:
            icon = "🟢"
            status = f"{score}/{total} ({pct}%)"
        elif pct >= 50:
            icon = "🟡"
            status = f"{score}/{total} ({pct}%)"
        else:
            icon = "🔴"
            status = f"{score}/{total} ({pct}%)"

        history_lines.append(f"{icon} <b>Попытка #{i}</b> • {status} • <i>{date_str}</i>")

    buttons = []
    if settings.WEBAPP_URL:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🚀 Полный разбор в ОП тесты",
                    web_app=WebAppInfo(url=settings.WEBAPP_URL),
                )
            ]
        )
    buttons.extend(
        [
            [
                InlineKeyboardButton(
                    text="🎯 Пройти новый тест",
                    callback_data=ButtonCallbackData(action="start_test").pack(),
                ),
                InlineKeyboardButton(
                    text="🏠 Главное меню",
                    callback_data=ButtonCallbackData(action="main_menu").pack(),
                ),
            ]
        ]
    )

    await target_msg.answer(
        "\n".join(history_lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )
    if isinstance(event, CallbackQuery):
        await event.answer()


def register_history_handler(dp: Dispatcher):
    dp.message.register(view_test_history, Command("history"))
