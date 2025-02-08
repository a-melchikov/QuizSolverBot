"""add total_questions to TestAttempt, and delete unused fields in AttemptAnswer

Revision ID: b1350ac60957
Revises: 7da86547537f
Create Date: 2025-02-05 22:34:18.646407

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b1350ac60957"
down_revision: Union[str, None] = "7da86547537f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Шаг 1: Создаём новую таблицу с нужной структурой для `attemptanswers`
    op.create_table(
        "new_attemptanswers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("question_id", sa.Integer, nullable=False),
        sa.Column("test_attempt_id", sa.Integer, nullable=False),
        # Удалённые столбцы "given_answer" и "given_option_id" отсутствуют
    )

    # Шаг 2: Копируем данные из старой таблицы в новую таблицу
    op.execute(
        """
        INSERT INTO new_attemptanswers (id, question_id, test_attempt_id)
        SELECT id, question_id, test_attempt_id
        FROM attemptanswers
        """
    )

    # Шаг 3: Удаляем старую таблицу
    op.drop_table("attemptanswers")

    # Шаг 4: Даем новой таблице прежнее имя
    op.rename_table("new_attemptanswers", "attemptanswers")

    # Шаг 5: Добавляем поле `total_questions` в таблицу `testattempts`
    # SQLite требует значение по умолчанию для NOT NULL
    op.add_column(
        "testattempts",
        sa.Column("total_questions", sa.Integer(), nullable=False, server_default="0"),
    )

    # Шаг 6: Убираем `server_default`, если для других СУБД он не нужен
    op.alter_column(
        "testattempts",
        "total_questions",
        server_default=None,
    )


def downgrade() -> None:
    # Шаг 1: Удаляем поле `total_questions` из таблицы `testattempts`
    op.drop_column("testattempts", "total_questions")

    # Шаг 2: Создаём новую таблицу с восстановленными полями
    op.create_table(
        "old_attemptanswers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("question_id", sa.Integer, nullable=False),
        sa.Column("test_attempt_id", sa.Integer, nullable=False),
        sa.Column("given_answer", sa.TEXT(), nullable=True),  # Восстанавливаем столбец
        sa.Column(
            "given_option_id", sa.INTEGER(), nullable=True
        ),  # Восстанавливаем столбец
    )

    # Шаг 3: Восстанавливаем данные с добавлением значения NULL для удалённых столбцов
    op.execute(
        """
        INSERT INTO old_attemptanswers (id, question_id, test_attempt_id, given_answer, given_option_id)
        SELECT id, question_id, test_attempt_id, NULL, NULL
        FROM attemptanswers
        """
    )

    # Шаг 4: Удаляем текущую таблицу
    op.drop_table("attemptanswers")

    # Шаг 5: Переименовываем новую таблицу в старое имя
    op.rename_table("old_attemptanswers", "attemptanswers")
