import asyncio
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.logger_setup import get_logger
from app.models import Option, Question

logger = get_logger(__name__)


def parse_questions_from_file(file_path: str | Path) -> list[dict]:
    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()

    questions = []
    current_question = None

    for line in lines:
        line = line.strip()

        if not line:
            if current_question:
                questions.append(current_question)
                current_question = None
            continue

        if current_question is None:
            current_question = {"text": line, "options": []}
        else:
            is_correct = line.startswith("-")
            option_text = line[1:].strip() if is_correct else line
            current_question["options"].append(
                {"text": option_text, "is_correct": is_correct}
            )

    if current_question:
        questions.append(current_question)

    return questions


async def save_questions_to_db(questions: list[dict], session: AsyncSession) -> int:
    count = 0
    for question_data in questions:
        options = question_data.get("options", [])
        has_options = len(options) > 1

        if has_options:
            question = Question(
                text=question_data["text"],
                has_options=True,
                answer_text=None,
            )
            for option_data in options:
                option = Option(
                    option_text=option_data["text"],
                    is_correct=option_data["is_correct"],
                )
                question.options.append(option)
        else:
            single_answer = options[0]["text"] if options else ""
            question = Question(
                text=question_data["text"],
                has_options=False,
                answer_text=single_answer,
            )

        session.add(question)
        count += 1

    await session.commit()
    return count


async def import_questions(file_path: str | Path = "questions.txt") -> int:
    path = Path(file_path)
    if not path.exists():
        logger.error(f"Файл {path} не найден.")
        return 0

    questions = parse_questions_from_file(path)
    logger.info(f"Распарсено вопросов: {len(questions)}")

    from app.database import Base, engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        count = await save_questions_to_db(questions, session)
        logger.info(f"Сохранено в базу данных: {count} вопросов")
        return count


if __name__ == "__main__":
    target_file = sys.argv[1] if len(sys.argv) > 1 else "questions.txt"
    asyncio.run(import_questions(target_file))
