from sqlalchemy import Boolean, ForeignKey, Integer
from sqlalchemy.orm import Mapped, relationship, mapped_column

from app.database import Base


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
