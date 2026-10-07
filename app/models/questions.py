from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Question(Base):
    text: Mapped[str] = mapped_column(Text, nullable=False)
    has_options: Mapped[bool] = mapped_column(Boolean, default=False)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(
        String(100), nullable=True, default=None
    )

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
    bookmarks = relationship(
        "Bookmark",
        back_populates="question",
        cascade="all, delete-orphan",
    )
