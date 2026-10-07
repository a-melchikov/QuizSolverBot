import pytest

from app.errors import UserNotFoundException
from app.repositories.questions import QuestionRepository
from app.repositories.users import UserRepository
from app.schemas.options import OptionCreate
from app.schemas.questions import QuestionCreate


@pytest.mark.asyncio
async def test_user_repository_create_and_get():
    repo = UserRepository()

    user = await repo.get_or_create_user(
        telegram_id=12345678901,
        username="testuser",
        first_name="Test",
        last_name="User",
    )
    assert user.id is not None
    assert user.telegram_id == 12345678901
    assert user.username == "testuser"

    # Fetch existing
    fetched = await repo.get_user_by_telegram_id(12345678901)
    assert fetched.id == user.id
    assert fetched.username == "testuser"

    # get_or_create existing with updated username
    updated_user = await repo.get_or_create_user(
        telegram_id=12345678901,
        username="newname",
        first_name="Test",
        last_name="User",
    )
    assert updated_user.id == user.id
    assert updated_user.username == "newname"


@pytest.mark.asyncio
async def test_user_repository_not_found():
    repo = UserRepository()
    with pytest.raises(UserNotFoundException):
        await repo.get_user_by_telegram_id(999999999)


@pytest.mark.asyncio
async def test_question_repository():
    repo = QuestionRepository()

    # Create simple question
    q_schema = QuestionCreate(
        text="Простой вопрос",
        has_options=False,
        answer_text="Ответ",
    )
    question = await repo.create_question(q_schema)
    assert question.id is not None
    assert question.text == "Простой вопрос"
    assert question.has_options is False
    assert question.answer_text == "Ответ"

    # Create question with options
    q_with_opts = QuestionCreate(
        text="Вопрос с вариантами",
        has_options=True,
    )
    options = [
        OptionCreate(option_text="Вариант 1", is_correct=False),
        OptionCreate(option_text="Вариант 2", is_correct=True),
    ]
    created_q = await repo.create_question_with_options(q_with_opts, options)
    assert created_q.id is not None

    # Count and pagination
    count = await repo.get_questions_count()
    assert count == 2

    paginated = await repo.get_questions_paginated(limit=1, offset=0)
    assert len(paginated) == 1
    assert paginated[0].id == question.id

    paginated_page2 = await repo.get_questions_paginated(limit=1, offset=1)
    assert len(paginated_page2) == 1
    assert paginated_page2[0].id == created_q.id

    # Delete question
    deleted = await repo.delete_question(question.id)
    assert deleted is True

    new_count = await repo.get_questions_count()
    assert new_count == 1
