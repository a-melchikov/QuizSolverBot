from datetime import datetime

from sqlalchemy import Integer, String, Text, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class User(Base):
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True)
    username: Mapped[str | None] = mapped_column(String(50))
    first_name: Mapped[str | None] = mapped_column(String(50))
    last_name: Mapped[str | None] = mapped_column(String(50))

    questions = relationship("Question", back_populates="user")
    test_attempts = relationship(
        "TestAttempt", back_populates="user", cascade="all, delete-orphan"
    )


class Question(Base):
    text: Mapped[str] = mapped_column(Text, nullable=False)
    has_options: Mapped[bool] = mapped_column(Boolean, default=False)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    created_by_user = relationship("User", back_populates="questions")

    user = relationship("User", back_populates="questions")
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


class Option(Base):
    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("questions.id"), nullable=False
    )
    option_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)

    question = relationship("Question", back_populates="options")


class TestAttempt(Base):
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    start_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False)

    user = relationship("User", back_populates="test_attempts")
    answers = relationship(
        "AttemptAnswer", back_populates="test_attempt", cascade="all, delete-orphan"
    )


class AttemptAnswer(Base):
    test_attempt_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("testattempts.id"), nullable=False
    )
    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("questions.id"), nullable=False
    )
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    test_attempt = relationship("TestAttempt", back_populates="answers")
    question = relationship("Question", back_populates="attempt_answers")
