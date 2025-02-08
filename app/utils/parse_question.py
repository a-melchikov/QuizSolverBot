import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session_maker
from app.models import Question, Option


async def parse_questions_from_file(file_path: str) -> list[dict]:
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


async def save_questions_to_db(questions: list[dict], session: AsyncSession):
    for question_data in questions:
        has_options = len(question_data["options"]) > 1

        question = Question(
            text=question_data["text"],
            has_options=has_options,
            answer_text=None if has_options else question_data["text"],
        )

        if question_data["options"]:
            for option_data in question_data["options"]:
                option = Option(
                    option_text=option_data["text"],
                    is_correct=option_data["is_correct"],
                )
                question.options.append(option)

        session.add(question)

    await session.commit()


async def main():
    file_path = "questions.txt"

    questions = await parse_questions_from_file(file_path)
    print(questions)

    async with async_session_maker() as session:
        await save_questions_to_db(questions, session)


# Запускаем главный асинхронный цикл
if __name__ == "__main__":
    asyncio.run(main())
