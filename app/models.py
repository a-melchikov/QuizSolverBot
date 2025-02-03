from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class User(Base):
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True)
    username: Mapped[str | None] = mapped_column(String(50))
    first_name: Mapped[str | None] = mapped_column(String(50))
    last_name: Mapped[str | None] = mapped_column(String(50))
