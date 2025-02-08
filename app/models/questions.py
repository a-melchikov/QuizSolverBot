from sqlalchemy import Text, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, relationship, mapped_column

from app.database import Base


class Question(Base):
    text: Mapped[str] = mapped_column(Text, nullable=False)
    has_options: Mapped[bool] = mapped_column(Boolean, default=False)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    created_by_user = relationship("User", back_populates="questions", overlaps="user")
    user = relationship("User", back_populates="questions", overlaps="created_by_user")

    options = relationship(
        "Option",
        back_populates="question",
        cascade="all, delete-orphan",
    )
    attempt_answers = relationship(
        "AttemptAnswer",
        back_populates="question",
        cascade="all, delete-orphan",
    )
