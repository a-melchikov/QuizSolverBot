from sqlalchemy import Text, Boolean, ForeignKey, Integer
from sqlalchemy.orm import Mapped, relationship, mapped_column

from app.database import Base


class Option(Base):
    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("questions.id"), nullable=False
    )
    option_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)

    question = relationship("Question", back_populates="options")
