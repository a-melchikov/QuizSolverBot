from sqlalchemy import delete, func, select

from app.database import async_session_maker
from app.models import Option, Question
from app.schemas.options import OptionCreate
from app.schemas.questions import QuestionCreate


class QuestionRepository:
    async def create_question(self, question_schema: QuestionCreate) -> Question:
        async with async_session_maker() as session:
            question = Question(**question_schema.model_dump())
            session.add(question)
            await session.commit()
            await session.refresh(question)
            return question

    async def create_question_with_options(
        self,
        question_schema: QuestionCreate,
        option_schemes: list[OptionCreate],
    ) -> Question:
        async with async_session_maker() as session:
            question = Question(**question_schema.model_dump())
            for option_schema in option_schemes:
                opt_data = option_schema.model_dump(exclude={"question_id"})
                question.options.append(Option(**opt_data))
            session.add(question)
            await session.commit()
            await session.refresh(question, attribute_names=["options"])
            return question

    async def get_questions(self) -> list[Question]:
        async with async_session_maker() as session:
            query = select(Question).order_by(Question.id.asc())
            result = await session.execute(query)
            return list(result.scalars().all())

    async def get_questions_paginated(
        self, limit: int = 20, offset: int = 0
    ) -> list[Question]:
        async with async_session_maker() as session:
            query = (
                select(Question).order_by(Question.id.asc()).limit(limit).offset(offset)
            )
            result = await session.execute(query)
            return list(result.scalars().all())

    async def get_questions_count(self) -> int:
        async with async_session_maker() as session:
            query = select(func.count(Question.id))
            result = await session.execute(query)
            return result.scalar() or 0

    async def delete_question(self, question_id: int) -> bool:
        async with async_session_maker() as session:
            query = delete(Question).where(Question.id == question_id)
            result = await session.execute(query)
            await session.commit()
            return (result.rowcount or 0) > 0
