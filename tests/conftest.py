import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.database import Base


@pytest_asyncio.fixture
async def async_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def session_maker(async_engine):
    return async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture(autouse=True)
def override_session_maker(session_maker, monkeypatch):
    import app.api.routes
    import app.database
    import app.repositories.questions
    import app.repositories.users
    import app.utils.parse_question

    monkeypatch.setattr(app.database, "async_session_maker", session_maker)
    monkeypatch.setattr(app.api.routes, "async_session_maker", session_maker)
    monkeypatch.setattr(
        app.repositories.questions, "async_session_maker", session_maker
    )
    monkeypatch.setattr(app.repositories.users, "async_session_maker", session_maker)
    monkeypatch.setattr(app.utils.parse_question, "async_session_maker", session_maker)
