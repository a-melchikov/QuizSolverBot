import asyncio

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.future import select

from app.config import settings
from app.database import async_session_maker
from app.logger_setup import get_logger
from app.models import User

logger = get_logger(__name__)
dp = Dispatcher()


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    logger.info(f"Received /start command from {message.from_user.full_name}")
    async with async_session_maker() as session:
        existing_user = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = existing_user.scalar()
        if not user:
            user = User(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
            )
            session.add(user)
            await session.commit()
            logger.info(f"User {message.from_user.full_name} added to the database.")
            await message.answer(
                f"Приветствую, {html.bold(message.from_user.full_name)}!"
            )
        else:
            logger.info(f"User {message.from_user.full_name} already exists.")
            await message.answer(
                f"Рад снова тебя здесь видеть, {html.bold(message.from_user.full_name)}!"
            )


@dp.message()
async def echo_handler(message: Message) -> None:
    try:
        await message.send_copy(chat_id=message.chat.id)
    except TypeError:
        await message.answer("Nice try!")


async def main() -> None:
    logger.info("Initializing the bot...")
    bot = Bot(
        token=settings.TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    logger.info("Starting bot polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    logger.info("Starting main function...")
    asyncio.run(main())
