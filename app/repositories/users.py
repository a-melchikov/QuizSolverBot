from sqlalchemy import select

from app.database import async_session_maker
from app.errors import UserNotFoundException
from app.models import User
from app.schemas.users import UserCreate


class UserRepository:
    async def get_user_by_telegram_id(self, telegram_id: int) -> User:
        async with async_session_maker() as session:
            query = select(User).where(User.telegram_id == telegram_id)
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            if not user:
                raise UserNotFoundException(
                    f"User with telegram_id {telegram_id} not found."
                )
            return user

    async def create_user(self, user_schema: UserCreate) -> User:
        async with async_session_maker() as session:
            user = User(**user_schema.model_dump())
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    async def get_or_create_user(
        self,
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> User:
        async with async_session_maker() as session:
            query = select(User).where(User.telegram_id == telegram_id)
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            if user:
                updated = False
                if user.username != username:
                    user.username = username
                    updated = True
                if user.first_name != first_name:
                    user.first_name = first_name
                    updated = True
                if user.last_name != last_name:
                    user.last_name = last_name
                    updated = True
                if updated:
                    await session.commit()
                    await session.refresh(user)
                return user

            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user
