from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, relationship, mapped_column

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
