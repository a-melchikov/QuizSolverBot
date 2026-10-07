"""add_category_and_bookmarks_table

Revision ID: 804c45655c9d
Revises: b1350ac60957
Create Date: 2026-10-07 23:18:49.698700

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.utils.categories import determine_category


# revision identifiers, used by Alembic.
revision: str = "804c45655c9d"
down_revision: Union[str, None] = "b1350ac60957"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "questions",
        sa.Column("category", sa.String(length=100), nullable=True),
    )

    op.create_table(
        "bookmarks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "question_id",
            sa.Integer(),
            sa.ForeignKey("questions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "user_id", "question_id", name="uq_user_question_bookmark"
        ),
    )

    # Заполнение категорий для существующих вопросов
    bind = op.get_bind()
    questions_table = sa.table(
        "questions",
        sa.column("id", sa.Integer),
        sa.column("text", sa.Text),
        sa.column("category", sa.String),
    )
    rows = bind.execute(
        sa.select(questions_table.c.id, questions_table.c.text)
    ).fetchall()
    for row in rows:
        q_id, q_text = row[0], row[1]
        cat = determine_category(q_text or "")
        bind.execute(
            questions_table.update()
            .where(questions_table.c.id == q_id)
            .values(category=cat)
        )


def downgrade() -> None:
    op.drop_table("bookmarks")
    with op.batch_alter_table("questions") as batch_op:
        batch_op.drop_column("category")
