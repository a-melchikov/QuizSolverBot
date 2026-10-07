import hashlib
import hmac
import json
from urllib.parse import parse_qsl, unquote

from fastapi import Header, HTTPException, status

from app.config import settings
from app.models import User
from app.repositories.users import UserRepository


def validate_telegram_data(init_data: str, bot_token: str) -> dict | None:
    if not init_data:
        return None

    try:
        parsed_data = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed_data.pop("hash", None)
        if not received_hash or not bot_token:
            return None

        # Build data_check_string
        data_check_list = [f"{k}={v}" for k, v in sorted(parsed_data.items())]
        data_check_string = "\n".join(data_check_list)

        # Secret key: HMAC-SHA256 of bot_token with "WebAppData"
        secret_key = hmac.new(
            b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256
        ).digest()

        # Calculate HMAC-SHA256 of data_check_string
        calculated_hash = hmac.new(
            secret_key, data_check_string.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        if calculated_hash != received_hash:
            return None

        if "user" in parsed_data:
            user_data = json.loads(unquote(parsed_data["user"]))
            return user_data
        return parsed_data
    except Exception:
        return None


async def get_current_user(
    authorization: str | None = Header(None),
) -> User:
    user_repo = UserRepository()

    # 1. Check Authorization: tma <initData> or InitData header
    if authorization and authorization.startswith("tma "):
        init_data = authorization[4:].strip()
        user_info = validate_telegram_data(init_data, settings.TOKEN)
        if user_info and "id" in user_info:
            user = await user_repo.get_or_create_user(
                telegram_id=user_info["id"],
                username=user_info.get("username"),
                first_name=user_info.get("first_name"),
                last_name=user_info.get("last_name"),
            )
            return user

    # 2. Local/Dev fallback for previewing in desktop browser without Telegram
    if not settings.TOKEN or settings.TOKEN == "your_telegram_bot_token":
        # Fallback for dev mode
        return await user_repo.get_or_create_user(
            telegram_id=999999999,
            username="demo_user",
            first_name="Demo",
            last_name="User",
        )

    # 3. If running with token, but opened directly in browser for testing
    # Fallback to demo user if authorization not provided
    if not authorization:
        return await user_repo.get_or_create_user(
            telegram_id=999999999,
            username="browser_preview",
            first_name="Browser",
            last_name="Preview",
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Неверная или отсутствующая подпись Telegram WebApp",
    )
