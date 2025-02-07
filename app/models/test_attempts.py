from datetime import datetime

from sqlalchemy import ForeignKey, Integer, DateTime, func
from sqlalchemy.orm import Mapped, relationship, mapped_column

from app.database import Base


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
