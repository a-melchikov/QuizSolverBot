from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    username: Mapped[str | None] = mapped_column(String(50))
    first_name: Mapped[str | None] = mapped_column(String(50))
    last_name: Mapped[str | None] = mapped_column(String(50))

    questions = relationship("Question", back_populates="user")
    test_attempts = relationship(
        "TestAttempt", back_populates="user", cascade="all, delete-orphan"
    )
    bookmarks = relationship(
        "Bookmark", back_populates="user", cascade="all, delete-orphan"
    )

    def __str__(self):
        return (
            f"{self.__class__.__name__}(id={self.telegram_id}, username={self.username}, "
            f"first_name={self.first_name}, last_name={self.last_name})"
        )

    def __repr__(self):
        return str(self)
