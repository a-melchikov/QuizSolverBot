from aiogram import Dispatcher
from app.handlers import (
    admin,
    quiz_answers,
    quiz_test,
    quiz_history,
    start,
    fallback,
    quiz,
    buttons,
)


def register_all_handlers(dp: Dispatcher) -> None:
    start.register_start_handler(dp)
    admin.register_admin_handlers(dp)
    quiz.register_quiz_handlers(dp)
    quiz_answers.register_answer_handlers(dp)
    quiz_test.register_test_handlers(dp)
    quiz_history.register_history_handler(dp)
    fallback.register_fallback_handler(dp)
    buttons.register_button_handlers(dp)
