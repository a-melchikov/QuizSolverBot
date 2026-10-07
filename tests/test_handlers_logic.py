import pytest

from app.models import Option
from app.repositories.questions import QuestionRepository
from app.schemas.options import OptionCreate
from app.schemas.questions import QuestionCreate


@pytest.mark.asyncio
async def test_create_question_with_options_no_question_id():
    """Verify that OptionCreate with question_id=None succeeds end-to-end."""
    repo = QuestionRepository()
    q_schema = QuestionCreate(
        text="Какая планета четвёртая от Солнца?",
        has_options=True,
    )
    options = [
        OptionCreate(option_text="Венера", is_correct=False),
        OptionCreate(option_text="Марс", is_correct=True),
        OptionCreate(option_text="Юпитер", is_correct=False),
    ]

    question = await repo.create_question_with_options(q_schema, options)
    assert question.id is not None
    assert len(question.options) == 3

    for opt in question.options:
        assert opt.question_id == question.id
        if opt.option_text == "Марс":
            assert opt.is_correct is True
        else:
            assert opt.is_correct is False


def test_text_answer_comparison():
    expected = "инициирующие"
    user_input_exact = "инициирующие"
    user_input_upper = "ИНИЦИИРУЮЩИЕ"
    user_input_spaces = "  инициирующие  "
    user_input_wrong = "бризантные"

    assert user_input_exact.strip().lower() == expected.strip().lower()
    assert user_input_upper.strip().lower() == expected.strip().lower()
    assert user_input_spaces.strip().lower() == expected.strip().lower()
    assert user_input_wrong.strip().lower() != expected.strip().lower()


def test_poll_options_matching():
    # Options: index 0 (id 10), index 1 (id 20, correct), index 2 (id 30, correct)
    options = [
        Option(id=10, question_id=1, option_text="A", is_correct=False),
        Option(id=20, question_id=1, option_text="B", is_correct=True),
        Option(id=30, question_id=1, option_text="C", is_correct=True),
    ]
    option_mapping = {index: option.id for index, option in enumerate(options)}
    correct_option_ids = [option.id for option in options if option.is_correct]

    # User selected index 1 and 2
    user_selected_indices = [1, 2]
    selected_option_ids = [option_mapping[i] for i in user_selected_indices]
    assert set(selected_option_ids) == set(correct_option_ids)

    # User selected only index 1
    user_partial_indices = [1]
    partial_option_ids = [option_mapping[i] for i in user_partial_indices]
    assert set(partial_option_ids) != set(correct_option_ids)
