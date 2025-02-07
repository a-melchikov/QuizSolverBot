import asyncio

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
            return user


async def main():
    # Test create_user
    # user_schema = UserCreate(
    #     telegram_id=1000,
    #     username="test_user",
    #     first_name="Test",
    #     last_name="User",
    # )

    # user = await UserRepository.create_user(user_schema)
    # Test get_user
    # user = await UserRepository.get_user_by_telegram_id(1000)
    # print(user)
    pass


if __name__ == "__main__":
    asyncio.run(main())
