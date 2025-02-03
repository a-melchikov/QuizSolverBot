from datetime import datetime
from sqlalchemy import Integer, func
from sqlalchemy.orm import DeclarativeBase, declared_attr, Mapped, mapped_column
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine,
)

from app.config import settings


DATABASE_URL = settings.get_db_url()

engine: AsyncEngine = create_async_engine(
    url=DATABASE_URL,
)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


class Base(AsyncAttrs, DeclarativeBase):
    __abstract__ = True
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower() + "s"
