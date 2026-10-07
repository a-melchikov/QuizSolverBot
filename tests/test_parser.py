import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import Question
from app.utils.parse_question import parse_questions_from_file, save_questions_to_db


@pytest.mark.asyncio
async def test_parse_and_save_questions(tmp_path, session_maker):
    content = """Вопрос без вариантов:
Правильный ответ

Вопрос с вариантами:
- Правильный вариант
Неправильный вариант 1
Неправильный вариант 2
"""
    file = tmp_path / "sample.txt"
    file.write_text(content, encoding="utf-8")

    parsed = parse_questions_from_file(file)
    assert len(parsed) == 2

    assert parsed[0]["text"] == "Вопрос без вариантов:"
    assert len(parsed[0]["options"]) == 1
    assert parsed[0]["options"][0]["text"] == "Правильный ответ"

    assert parsed[1]["text"] == "Вопрос с вариантами:"
    assert len(parsed[1]["options"]) == 3
    assert parsed[1]["options"][0]["is_correct"] is True
    assert parsed[1]["options"][1]["is_correct"] is False

    async with session_maker() as session:
        saved_count = await save_questions_to_db(parsed, session)
        assert saved_count == 2

    async with session_maker() as session:
        result = await session.execute(
            select(Question)
            .options(selectinload(Question.options))
            .order_by(Question.id.asc())
        )
        questions = list(result.scalars().all())
        assert len(questions) == 2

        # First question: no options, answer_text is populated
        assert questions[0].has_options is False
        assert questions[0].answer_text == "Правильный ответ"
        assert len(questions[0].options) == 0

        # Second question: has options, answer_text is None
        assert questions[1].has_options is True
        assert questions[1].answer_text is None
        assert len(questions[1].options) == 3
        correct_opts = [o for o in questions[1].options if o.is_correct]
        assert len(correct_opts) == 1
        assert correct_opts[0].option_text == "Правильный вариант"
