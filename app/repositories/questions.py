import asyncio

from app.database import async_session_maker
from app.models import Question, Option
from app.schemas.options import OptionCreate
from app.schemas.questions import QuestionCreate


class QuestionRepository:
    async def create_question(self, question_schema: QuestionCreate) -> Question:
        async with async_session_maker() as session:
            question = Question(**question_schema.model_dump())
            session.add(question)
            await session.commit()
            return question

    async def create_question_with_options(
        self,
        question_schema: QuestionCreate,
        option_schemes: list[OptionCreate],
    ) -> Question:
        async with async_session_maker() as session:
            question = Question(**question_schema.model_dump())
            session.add(question)
            await session.flush()

            for option_schema in option_schemes:
                option = Option(**option_schema.model_dump())
                session.add(option)

            await session.commit()
            return question


async def main():
    question_schema = QuestionCreate(
        text="Вопрос 1",
        has_options=True,
        answer_text=None,
        created_by=None,
    )
    question = await QuestionRepository().create_question(question_schema)
    pass


if __name__ == "__main__":
    asyncio.run(main())
